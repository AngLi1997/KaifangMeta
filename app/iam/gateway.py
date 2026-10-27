"""认证模块经 APISIX Admin API 下发平台自身路由（docs/gateway.md「平台自身的路由」），固定资源 ID，幂等"""

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
