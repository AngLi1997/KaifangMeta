"""接入应用的维护接口：控制台「应用接入」与 CLI 共用（docs/platform/auth/app-onboarding.md）

密钥只在注册与轮换时返回一次；client_secret 存哈希，gateway_secret 需参与网关 HMAC 存明文。
"""

import secrets

import httpx

from app.settings import settings
from app.utils.password import get_password_hash

from . import gateway
from .api import TOKEN_EXCHANGE
from .models import Client, Tenant
from .service import AccountError


def _public(client: Client) -> dict:
    return {
        "client_id": client.client_id,
        "name": client.name,
        "type": client.type,
        "owner": client.owner,
        "status": client.status,
        "tenants": client.tenants,
        "scopes": client.scopes,
        "redirect_uris": client.redirect_uris,
        "post_logout_redirect_uris": client.post_logout_redirect_uris,
        "gateway": client.gateway,
        "portal": client.portal,
        "sync_status": client.sync_status,
        "synced_at": client.synced_at.strftime(settings.DATETIME_FORMAT) if client.synced_at else None,
        "created_at": client.created_at.strftime(settings.DATETIME_FORMAT),
    }


async def _check_tenants(tenants: list[str]) -> None:
    if await Tenant.filter(id__in=tenants).count() != len(set(tenants)):
        raise AccountError("开通租户不存在")


def _grant_types(redirect_uris: list[str]) -> list[str]:
    # 有回调地址即 web 应用（前端 + 后端），否则为纯后端 service 应用
    web = ["authorization_code", "refresh_token"] if redirect_uris else []
    return web + ["client_credentials", TOKEN_EXCHANGE]


async def list_apps(keyword: str = "") -> list[dict]:
    """业务应用列表（不含内置控制台），附网关下发状态与实例健康"""
    clients = await Client.exclude(client_id=settings.CONSOLE_CLIENT_ID).order_by("created_at")
    if keyword:
        clients = [c for c in clients if keyword in c.client_id or keyword in c.name]
    states = await gateway.gateway_states(clients)
    tenants = dict(await Tenant.all().values_list("id", "name"))
    rows = []
    for c in clients:
        rows.append(
            _public(c)
            | {
                "gateway_state": states[c.client_id],
                "instances": await gateway.instance_health(c),
                "tenant_names": [tenants.get(t, t) for t in c.tenants],
            }
        )
    return rows


async def get_app(client_id: str) -> dict | None:
    client = await Client.get_or_none(client_id=client_id)
    return _public(client) if client else None


async def create_app(data: dict) -> tuple[dict, dict]:
    """注册应用并下发网关；返回（应用，一次性密钥）。下发失败不回滚，应用标记待下发"""
    if data["client_id"] == settings.CONSOLE_CLIENT_ID or await Client.exists(client_id=data["client_id"]):
        raise AccountError("client_id 已存在")
    await _check_tenants(data["tenants"])
    secrets_once = {"client_secret": secrets.token_urlsafe(32)}
    if data.get("gateway"):
        secrets_once["gateway_secret"] = secrets.token_hex(32)
    client = await Client.create(
        **data,
        type="web" if data["redirect_uris"] else "service",
        grant_types=_grant_types(data["redirect_uris"]),
        client_secret_hash=get_password_hash(secrets_once["client_secret"]),
        gateway_secret=secrets_once.get("gateway_secret"),
    )
    await _sync_quietly(client)
    return _public(client), secrets_once


async def update_app(client_id: str, data: dict) -> dict:
    client = await Client.get_or_none(client_id=client_id)
    if not client or client_id == settings.CONSOLE_CLIENT_ID:
        raise AccountError("应用不存在")
    await _check_tenants(data["tenants"])
    for key, value in data.items():
        setattr(client, key, value)
    client.type = "web" if client.redirect_uris else "service"
    client.grant_types = _grant_types(client.redirect_uris)
    once = {}
    if client.gateway and not client.gateway_secret:
        once["gateway_secret"] = client.gateway_secret = secrets.token_hex(32)
    await client.save()
    await _sync_quietly(client)
    return once


async def set_status(client_id: str, status: str) -> None:
    client = await Client.get_or_none(client_id=client_id)
    if not client or client_id == settings.CONSOLE_CLIENT_ID:
        raise AccountError("应用不存在")
    client.status = status
    # 停用后网关返回 503；授权与续期只认 online 应用，已签发的 Token 无法再续期
    await client.save(update_fields=["status"])
    await _sync_quietly(client)


async def sync(client_id: str) -> None:
    client = await Client.get_or_none(client_id=client_id)
    if not client or client_id == settings.CONSOLE_CLIENT_ID:
        raise AccountError("应用不存在")
    try:
        await gateway.sync_app(client)
    except httpx.HTTPError as e:
        raise AccountError(f"网关下发失败：{e!r}")


async def rotate_secret(client_id: str, kind: str) -> dict:
    """首版不做重叠期：轮换后旧密钥立即失效，业务需同步更新配置"""
    client = await Client.get_or_none(client_id=client_id)
    if not client or client_id == settings.CONSOLE_CLIENT_ID:
        raise AccountError("应用不存在")
    if kind == "client":
        value = secrets.token_urlsafe(32)
        client.client_secret_hash = get_password_hash(value)
        await client.save(update_fields=["client_secret_hash"])
        return {"client_secret": value}
    if not client.gateway:
        raise AccountError("应用未配置网关")
    client.gateway_secret = secrets.token_hex(32)
    await client.save(update_fields=["gateway_secret"])
    await _sync_quietly(client)
    return {"gateway_secret": client.gateway_secret}


async def _sync_quietly(client: Client) -> None:
    try:
        await gateway.sync_app(client)
    except httpx.HTTPError:
        pass  # sync_app 已标记「待下发」，启动时与「重新下发」重试
