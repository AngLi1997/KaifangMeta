"""认证模块运维命令（应用接入页面落地前的最小入口）

  python -m app.iam.cli create-client --client-id kaifang-meta-archive-room --name 智慧档案室 \\
      --scopes directory:read,delegate:user [--redirect-uris URL] [--event-endpoint URL --subscribe 'user.*'] \\
      [--portal-entry URL --portal-icon 档 --portal-description '著录 · 检索 · 问答']
  python -m app.iam.cli rotate-key          # 新增签名密钥，各节点在 IAM_KEY_CACHE_TTL 内切换
  python -m app.iam.cli retire-key <kid>    # 旧 Token 全部过期后（≥ 2 个 Access Token 有效期）退役旧密钥
"""

import argparse
import asyncio
import secrets

from tortoise import Tortoise

from app.settings import settings
from app.utils.password import get_password_hash

from .api import TOKEN_EXCHANGE
from .keys import generate_key
from .models import Client, SigningKey


PORTAL_FIELDS = {"portal_entry": "entry", "portal_icon": "icon", "portal_description": "description"}


def _split(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


async def create_client(args) -> None:
    client_secret = secrets.token_urlsafe(32)
    event_secret = secrets.token_hex(32) if args.event_endpoint else None
    redirect_uris = _split(args.redirect_uris)
    # 有回调地址即 web 应用（前端 + 后端），否则为纯后端 service 应用
    web_grants = ["authorization_code", "refresh_token"] if redirect_uris else []
    await Client.create(
        client_id=args.client_id,
        name=args.name,
        type="web" if redirect_uris else "service",
        redirect_uris=redirect_uris,
        grant_types=web_grants + ["client_credentials", TOKEN_EXCHANGE],
        client_secret_hash=get_password_hash(client_secret),
        scopes=_split(args.scopes),
        tenants=_split(args.tenants),
        event_endpoint=args.event_endpoint,
        event_secret=event_secret,
        event_subscribe=_split(args.subscribe),
        portal={PORTAL_FIELDS[k]: v for k, v in vars(args).items() if k in PORTAL_FIELDS and v},
    )
    # 密钥仅显示一次（docs/platform/auth/app-onboarding.md「接入流程」）
    print(f"client_id={args.client_id}\nclient_secret={client_secret}")
    if event_secret:
        print(f"event_secret={event_secret}")


async def rotate_key(_) -> None:
    kid, private_pem, public_jwk = generate_key()
    await SigningKey.create(kid=kid, private_pem=private_pem, public_jwk=public_jwk)
    print(f"新签名密钥 {kid} 已生效（各节点 {settings.IAM_KEY_CACHE_TTL} 秒内切换）")


async def retire_key(args) -> None:
    if await SigningKey.filter(active=True).count() <= 1:
        raise SystemExit("至少保留一把有效签名密钥")
    updated = await SigningKey.filter(kid=args.kid, active=True).update(active=False)
    print(f"已退役 {args.kid}" if updated else f"未找到有效密钥 {args.kid}")


async def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.iam.cli")
    sub = parser.add_subparsers(required=True)

    p = sub.add_parser("create-client", help="注册机密客户端（服务应用）")
    p.add_argument("--client-id", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--scopes", default="")
    p.add_argument("--tenants", default=settings.IAM_SYSTEM_TENANT)
    p.add_argument("--redirect-uris", default="")
    p.add_argument("--event-endpoint")
    p.add_argument("--subscribe", default="")
    p.add_argument("--portal-entry", help="门户入口地址，不填则不在门户显示")
    p.add_argument("--portal-icon", help="门户磁贴图标：1–2 个字")
    p.add_argument("--portal-description")
    p.set_defaults(func=create_client)

    sub.add_parser("rotate-key", help="新增签名密钥").set_defaults(func=rotate_key)
    p = sub.add_parser("retire-key", help="退役签名密钥")
    p.add_argument("kid")
    p.set_defaults(func=retire_key)

    args = parser.parse_args()
    await Tortoise.init(config=settings.TORTOISE_ORM)
    try:
        await args.func(args)
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
