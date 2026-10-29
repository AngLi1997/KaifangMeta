"""认证模块经 APISIX Admin API 下发平台自身路由与接入应用路由（docs/gateway.md「平台自身的路由」、
docs/platform/auth/app-onboarding.md「平台期望状态与下发」），固定资源 ID，幂等；APISIX 把配置存入 etcd"""

import asyncio
import re
import time
from datetime import datetime, timezone

import httpx

from app.log import logger
from app.settings import settings

from .models import Client


def _limit_count(count: int, window: int, key: str, key_type: str = "var") -> dict:
    # 多节点共享计数（docs/deployment.md）；本地单 Redis 用 redis 策略，生产 Redis 集群用 redis-cluster
    return {
        "count": count,
        "time_window": window,
        "key_type": key_type,
        "key": key,
        "policy": "redis",
        "redis_host": "redis",
        "redis_port": 6379,
        "rejected_code": 429,
        "rejected_msg": "请求过于频繁",
    }


def _auth_plugins(aud: str, secret: str, **identity) -> dict:
    """模式 A 插件组合：openid-connect 按 JWKS 验签，km-identity 做 aud / 吊销 / 租户 / scope 与签名身份头"""
    # 网关容器内 9080 即自身，discovery / JWKS 经 km-iam 路由回到平台
    discovery = "http://127.0.0.1:9080/kaifang-meta/iam/.well-known/openid-configuration"
    return {
        "openid-connect": {
            "client_id": aud,
            "client_secret": "unused-bearer-only",
            "discovery": discovery,
            "bearer_only": True,
            "use_jwks": True,
        },
        "km-identity": {"aud": aud, "secret": secret, "redis_host": "redis", "redis_port": 6379, **identity},
    }


def _resources(console: Client) -> list[tuple[str, dict]]:
    return [
        (
            "upstreams/km-platform",
            {
                "type": "roundrobin",
                "nodes": {node.strip(): 1 for node in settings.PLATFORM_UPSTREAM_NODES.split(",") if node.strip()},
            },
        ),
        (
            "routes/km-iam",
            {"uri": "/kaifang-meta/iam/*", "upstream_id": "km-platform"},
        ),
        (
            # 登录接口单独限流防撞库（按来源 IP）
            "routes/km-iam-login",
            {
                "uri": "/kaifang-meta/iam/login",
                "methods": ["POST"],
                "priority": 10,
                "upstream_id": "km-platform",
                "plugins": {"limit-count": _limit_count(settings.IAM_LOGIN_RATE_LIMIT_PER_MIN, 60, "remote_addr")},
            },
        ),
        (
            "routes/km-console",
            {
                "uri": f"{settings.CONSOLE_GATEWAY_PREFIX}/api/*",
                "upstream_id": "km-platform",
                "plugins": {
                    **_auth_plugins(console.client_id, settings.CONSOLE_GATEWAY_SECRET, tenants=console.tenants),
                    # 按 应用 × 租户 限流：km-identity 在 rewrite 阶段注入租户头，limit-count 在 access 阶段计数
                    "limit-count": _limit_count(settings.CONSOLE_RATE_LIMIT_QPS, 1, "http_x_km_tenant_id"),
                },
            },
        ),
        (
            "routes/km-platform-iam",
            {
                "uri": "/kaifang-meta/platform/iam/v1/*",
                "upstream_id": "km-platform",
                "plugins": _auth_plugins(
                    settings.PLATFORM_CLIENT_ID,
                    settings.PLATFORM_GATEWAY_SECRET,
                    scopes=["directory:read"],
                    allow_on_behalf_of=True,
                ),
            },
        ),
    ]


def _admin() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=f"{settings.APISIX_ADMIN_URL}/apisix/admin", timeout=5, headers={"X-API-KEY": settings.APISIX_ADMIN_KEY}
    )


# ---- 接入应用（docs/platform/auth/onboarding-unified-build.md「APISIX 与 etcd」）----

APP_PREFIX = "km-app-"
DISABLED = {"fault-injection": {"abort": {"http_status": 503, "body": '{"code":503,"msg":"应用维护中"}\n'}}}


def _app_id(client_id: str, n: int, suffix: str = "") -> str:
    return f"{APP_PREFIX}{client_id}-{n}{suffix}"


def _upstream(route: dict) -> dict:
    body = {"type": "roundrobin", "nodes": {node: 1 for node in route["nodes"]}}
    if route.get("health"):
        body["checks"] = {
            "active": {
                "http_path": route["health"],
                "healthy": {"interval": 5, "successes": 1},
                "unhealthy": {"interval": 5, "http_failures": 2, "tcp_failures": 2},
            }
        }
    return body


def app_resources(client: Client) -> list[tuple[str, dict]]:
    """应用的期望网关配置：每条子路由一个上游 + 鉴权路由，公开路径单独路由；去掉应用前缀后转发"""
    gw = client.gateway or {}
    prefix, routes = gw.get("prefix", "").rstrip("/"), gw.get("routes") or []
    if not prefix or not routes:
        return []
    rewrite = {"proxy-rewrite": {"regex_uri": [f"^{re.escape(prefix)}(/.*)$", "$1"]}}
    online = client.status == "online"
    resources = []
    for n, route in enumerate(routes, 1):
        resources.append((f"upstreams/{_app_id(client.client_id, n)}", _upstream(route)))
        base = f"{prefix}{route['path'].rstrip('/')}"
        plugins = {
            **_auth_plugins(client.client_id, client.gateway_secret or "", tenants=client.tenants),
            **rewrite,
            "limit-count": _limit_count(gw.get("rate_limit") or 200, 1, "http_x_km_tenant_id"),
        }
        resources.append(
            (
                f"routes/{_app_id(client.client_id, n)}",
                {
                    "name": f"{client.name} {route['path']}",
                    "uris": [base, f"{base}/*"],
                    "upstream_id": _app_id(client.client_id, n),
                    "plugins": plugins if online else DISABLED,
                },
            )
        )
    for m, public in enumerate(gw.get("public_paths") or [], 1):
        # 公开路径归属路径前缀最长的子路由
        owner = max(
            (n for n, r in enumerate(routes, 1) if public.startswith(r["path"].rstrip("/") + "/") or public == r["path"]),
            key=lambda n: len(routes[n - 1]["path"]),
            default=None,
        )
        if owner is None:
            continue
        resources.append(
            (
                f"routes/{_app_id(client.client_id, owner, f'-public-{m}')}",
                {
                    "name": f"{client.name} {public}",
                    "uri": f"{prefix}{public}",
                    "priority": 10,
                    "upstream_id": _app_id(client.client_id, owner),
                    "plugins": rewrite if online else DISABLED,
                },
            )
        )
    return resources


async def _app_ids(api: httpx.AsyncClient, kind: str, client_id: str) -> set[str]:
    resp = await api.get(f"/{kind}")
    resp.raise_for_status()
    ids = {item["value"]["id"] for item in resp.json().get("list") or []}
    return {i for i in ids if i.startswith(f"{APP_PREFIX}{client_id}-")}


async def sync_app(client: Client) -> None:
    """下发应用路由并删除多余资源；失败记「待下发」后抛出 httpx.HTTPError"""
    if not settings.APISIX_ADMIN_KEY:
        raise httpx.HTTPError("未配置 APISIX_ADMIN_KEY")
    resources = app_resources(client)
    try:
        async with _admin() as api:
            for path, body in resources:
                (await api.put(f"/{path}", json=body)).raise_for_status()
            wanted = {path for path, _ in resources}
            # 先删路由再删上游：上游被路由引用时不能删除
            for kind in ("routes", "upstreams"):
                for rid in await _app_ids(api, kind, client.client_id):
                    if f"{kind}/{rid}" not in wanted:
                        (await api.delete(f"/{kind}/{rid}")).raise_for_status()
    except httpx.HTTPError:
        client.sync_status = "pending"
        await client.save(update_fields=["sync_status"])
        raise
    client.sync_status = "synced" if resources else None
    client.synced_at = datetime.now(timezone.utc)
    await client.save(update_fields=["sync_status", "synced_at"])


def _covers(expected, actual) -> bool:
    """APISIX 返回的配置会补默认值：期望的每个字段在实际中一致即视为未漂移"""
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(_covers(v, actual.get(k)) for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(expected) == len(actual) and all(map(_covers, expected, actual))
    return expected == actual


async def gateway_states(clients: list[Client]) -> dict[str, str | None]:
    """synced / pending / drift / None（未配置）；APISIX 不可达时保留数据库中的状态"""
    states = {c.client_id: c.sync_status for c in clients}
    if not settings.APISIX_ADMIN_KEY:
        return states
    try:
        async with _admin() as api:
            actual = {}
            for kind in ("routes", "upstreams"):
                resp = await api.get(f"/{kind}")
                resp.raise_for_status()
                actual |= {f"{kind}/{i['value']['id']}": i["value"] for i in resp.json().get("list") or []}
    except httpx.HTTPError:
        return states
    for c in clients:
        if c.sync_status != "synced":
            continue
        expected = app_resources(c)
        extra = {k for k in actual if k.split("/", 1)[1].startswith(f"{APP_PREFIX}{c.client_id}-")} - {
            p for p, _ in expected
        }
        if extra or not all(_covers(body, actual.get(path)) for path, body in expected):
            states[c.client_id] = "drift"
    return states


_health_cache: dict[str, tuple[float, bool]] = {}


async def _probe(node: str, path: str) -> bool:
    key = f"{node}{path}"
    cached = _health_cache.get(key)
    if cached and time.monotonic() - cached[0] < 30:
        return cached[1]
    try:
        async with httpx.AsyncClient(timeout=2) as http:
            ok = (await http.get(f"http://{node}{path}")).status_code < 500
    except httpx.HTTPError:
        ok = False
    _health_cache[key] = (time.monotonic(), ok)
    return ok


async def instance_health(client: Client) -> dict | None:
    """平台直接探测各上游节点的健康检查路径；没有配置健康检查时返回 None"""
    targets = [(node, r["health"]) for r in (client.gateway or {}).get("routes") or [] if r.get("health") for node in r["nodes"]]
    if not targets:
        return None
    results = await asyncio.gather(*(_probe(node, path) for node, path in targets))
    return {"healthy": sum(results), "total": len(results)}


async def sync_platform_routes() -> None:
    """下发失败抛出 httpx.HTTPError：启动时由调用方告警，新建租户时随请求失败回滚"""
    # shortcut: 无「待下发」状态与定时对账；应用接入落地后改为退避重试 + 定时对账
    console = await Client.get(client_id=settings.CONSOLE_CLIENT_ID)
    redirect_uris = [uri.strip() for uri in settings.CONSOLE_REDIRECT_URIS.split(",") if uri.strip()]
    post_logout_redirect_uris = [
        uri.strip() for uri in settings.CONSOLE_POST_LOGOUT_REDIRECT_URIS.split(",") if uri.strip()
    ]
    if console.redirect_uris != redirect_uris or console.post_logout_redirect_uris != post_logout_redirect_uris:
        console.redirect_uris = redirect_uris
        console.post_logout_redirect_uris = post_logout_redirect_uris
        await console.save(update_fields=["redirect_uris", "post_logout_redirect_uris"])
    if not settings.APISIX_ADMIN_KEY:
        logger.warning("未配置 APISIX_ADMIN_KEY，跳过网关路由下发")
        return
    headers = {"X-API-KEY": settings.APISIX_ADMIN_KEY}
    async with httpx.AsyncClient(base_url=f"{settings.APISIX_ADMIN_URL}/apisix/admin", timeout=5) as client:
        for path, body in _resources(console):
            resp = await client.put(f"/{path}", json=body, headers=headers)
            resp.raise_for_status()
    logger.info("网关路由已下发：km-iam、km-iam-login、km-console、km-platform-iam")
    for client in await Client.filter(sync_status__isnull=False).exclude(client_id=settings.CONSOLE_CLIENT_ID):
        try:
            await sync_app(client)
        except httpx.HTTPError as e:
            logger.warning(f"应用 {client.client_id} 网关路由下发失败，已标记待下发：{e!r}")
