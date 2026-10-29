"""OIDC 端点，经网关公开路由 /kaifang-meta/iam/* 访问（docs/auth-flow.md）"""

import base64
from urllib.parse import unquote, urlencode

import jwt
from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.settings import settings

from . import keys, service, sessions
from .models import Client
from .page import login_page, message_page, tenant_page

PREFIX = "/kaifang-meta/iam"
COOKIE = "km_sso"


def _https(request: Request) -> bool:
    return request.headers.get("x-forwarded-proto", request.url.scheme) == "https"


def _cookie(request: Request) -> str:
    # HTTP 访问用另一个名字：同主机已有 Secure 的 km_sso 时，浏览器不允许 HTTP 页面写同名 Cookie
    return COOKIE if _https(request) else f"{COOKIE}_http"


TOKEN_EXCHANGE = "urn:ietf:params:oauth:grant-type:token-exchange"
ACCESS_TOKEN_TYPE = "urn:ietf:params:oauth:token-type:access_token"

router = APIRouter(prefix=PREFIX, tags=["认证模块"])


def _redirect(uri: str, **params) -> RedirectResponse:
    sep = "&" if "?" in uri else "?"
    return RedirectResponse(f"{uri}{sep}{urlencode({k: v for k, v in params.items() if v})}", status_code=302)


def _token_error(error: str, status_code: int = 400) -> JSONResponse:
    return JSONResponse({"error": error}, status_code=status_code, headers={"Cache-Control": "no-store"})


async def _active_client(client_id: str) -> Client | None:
    return await Client.get_or_none(client_id=client_id, status="online")


@router.get("/.well-known/openid-configuration", summary="OIDC 发现")
async def discovery():
    issuer = settings.IAM_ISSUER
    return {
        "issuer": issuer,
        "authorization_endpoint": f"{issuer}/authorize",
        "token_endpoint": f"{issuer}/token",
        "jwks_uri": f"{issuer}/jwks",
        "end_session_endpoint": f"{issuer}/logout",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token", "client_credentials", TOKEN_EXCHANGE],
        "code_challenge_methods_supported": ["S256"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": [keys.ALGORITHM],
        "token_endpoint_auth_methods_supported": ["none", "client_secret_post", "client_secret_basic"],
    }


@router.get("/jwks", summary="JWKS 公钥")
async def jwks():
    return await keys.jwks()


@router.get("/authorize", summary="授权码 + PKCE")
async def authorize(
    request: Request,
    client_id: str,
    redirect_uri: str,
    response_type: str = "code",
    code_challenge: str = "",
    code_challenge_method: str = "S256",
    state: str = "",
    prompt: str = "",
    tenant: str = "",
):
    client = await _active_client(client_id)
    if not client or redirect_uri not in client.redirect_uris:
        return message_page("认证失败", "无效的应用或回调地址")
    if response_type != "code" or code_challenge_method != "S256" or not code_challenge:
        return _redirect(redirect_uri, error="invalid_request", state=state)

    sid = request.cookies.get(_cookie(request))
    session = await sessions.get_sso_session(sid)
    if session:
        # 一个 Token 只含一个 tid：单租户直接进入；多租户首次登录或 prompt=select_tenant 时选择，否则沿用会话上次的租户
        tenants = await service.account_tenants(session["sub"])
        if tenants:
            enabled = [t for t in tenants if t in client.tenants]
            if tenant:
                if tenant not in enabled:
                    return message_page("认证失败", "当前租户未开通该应用", status_code=403)
                tid = tenant
            elif not enabled:
                return message_page("认证失败", "当前租户未开通该应用", status_code=403)
            elif len(enabled) == 1:
                tid = enabled[0]
            elif session["tid"] in enabled and prompt != "select_tenant":
                tid = session["tid"]
            else:
                return tenant_page(dict(request.query_params), await service.tenant_names(enabled), session["tid"])
            if tid != session["tid"]:
                await sessions.set_sso_tenant(sid, tid)
            code = await sessions.issue_code(
                {
                    "client_id": client_id,
                    "redirect_uri": redirect_uri,
                    "code_challenge": code_challenge,
                    "sub": session["sub"],
                    "tid": tid,
                    "sid": sid,
                }
            )
            return _redirect(redirect_uri, code=code, state=state)
    if prompt == "none":
        return _redirect(redirect_uri, error="login_required", state=state)
    return login_page(query=request.url.query)


@router.post("/login", summary="账号密码登录，建立 SSO 会话")
async def login(request: Request, username: str = Form(...), password: str = Form(...), q: str = Form("")):
    try:
        account = await service.authenticate(username, password)
    except service.AccountError as e:
        return login_page(query=q, username=username, error=str(e))
    if not account:
        return login_page(query=q, username=username, error="账号或密码错误")
    # 租户在 /authorize 按应用开通情况确定，会话先不绑定
    sid = await sessions.create_sso_session(account["sub"], "")
    response = RedirectResponse(f"{PREFIX}/authorize?{q}", status_code=303)
    response.set_cookie(
        _cookie(request),
        sid,
        max_age=settings.IAM_SSO_SESSION_TTL,
        path=PREFIX,
        httponly=True,
        # 跟随访问协议：HTTPS 访问才加 Secure，HTTP 局域网访问也能保存会话
        secure=_https(request),
        samesite="lax",
    )
    return response


def _basic_auth(request: Request) -> tuple[str, str] | None:
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("basic "):
        return None
    try:
        client_id, _, secret = base64.b64decode(header[6:]).decode().partition(":")
    except ValueError:
        return None
    return unquote(client_id), unquote(secret)


@router.post("/token", summary="换取 / 续期 Token")
async def token(
    request: Request,
    grant_type: str = Form(...),
    client_id: str = Form(""),
    client_secret: str = Form(""),
    code: str = Form(""),
    redirect_uri: str = Form(""),
    code_verifier: str = Form(""),
    refresh_token: str = Form(""),
    tenant: str = Form(""),
    scope: str = Form(""),
    subject_token: str = Form(""),
    subject_token_type: str = Form(""),
    actor_token: str = Form(""),
    audience: str = Form(""),
):
    if basic := _basic_auth(request):
        client_id, client_secret = basic
    client = await _active_client(client_id)
    if not client:
        return _token_error("invalid_client", 401)
    if grant_type not in client.grant_types:
        return _token_error("unauthorized_client")

    if grant_type == "client_credentials":
        if not await service.authenticate_client(client_id, client_secret):
            return _token_error("invalid_client", 401)
        tid = tenant or settings.IAM_SYSTEM_TENANT
        if tid not in client.tenants or not await service.tenant_is_active(tid):
            return _token_error("invalid_target")
        requested = scope.split() or client.scopes
        if not set(requested) <= set(client.scopes):
            return _token_error("invalid_scope")
        return JSONResponse(
            await sessions.issue_service_token(client_id, tid, requested), headers={"Cache-Control": "no-store"}
        )

    if grant_type == TOKEN_EXCHANGE:
        return await _token_exchange(client, client_secret, subject_token, subject_token_type, actor_token, audience)

    if grant_type == "authorization_code":
        ctx = await sessions.consume_code(code)
        if (
            not ctx
            or ctx["client_id"] != client_id
            or ctx["redirect_uri"] != redirect_uri
            or not sessions.verify_pkce(code_verifier, ctx["code_challenge"])
        ):
            return _token_error("invalid_grant")
    elif grant_type == "refresh_token":
        ctx = await sessions.rotate_refresh_token(refresh_token, client_id)
        if not ctx:
            return _token_error("invalid_grant")
    else:
        return _token_error("unsupported_grant_type")

    if not await service.account_in_tenant(ctx["sub"], ctx["tid"]):
        return _token_error("invalid_grant")

    tokens = await sessions.issue_tokens(ctx["sub"], ctx["tid"], ctx["sid"], client_id)
    return JSONResponse(tokens, headers={"Cache-Control": "no-store"})


async def _token_exchange(
    client: Client, client_secret: str, subject_token: str, subject_token_type: str, actor_token: str, audience: str
) -> JSONResponse:
    """模式 B 代表用户：subject_token = 用户 Token，actor_token = 调用方 Service Token（docs/auth-flow.md「代表用户调用」）"""
    if subject_token_type != ACCESS_TOKEN_TYPE:
        return _token_error("invalid_request")
    if not await service.authenticate_client(client.client_id, client_secret):
        return _token_error("invalid_client", 401)
    try:
        # 用户 Token 必须是发给调用方应用的，调用方不能拿别的应用的用户 Token 来换
        subject = await keys.verify(subject_token, audience=client.client_id)
        actor = await keys.verify(actor_token, audience=settings.PLATFORM_CLIENT_ID) if actor_token else None
    except jwt.PyJWTError:
        return _token_error("invalid_grant")
    if actor and actor["sub"] != client.client_id:
        return _token_error("invalid_grant")
    if await sessions.is_revoked(subject.get("sid"), subject["sub"]):
        return _token_error("invalid_grant")
    if not await service.account_in_tenant(subject["sub"], subject.get("tid", "")):
        return _token_error("invalid_grant")
    if subject["tid"] not in client.tenants:
        return _token_error("invalid_target")
    target = audience or settings.PLATFORM_CLIENT_ID
    # shortcut: 只允许换到平台；业务间换 Token 需按目标应用 callers 校验，应用接入落地后放开
    if target != settings.PLATFORM_CLIENT_ID:
        return _token_error("invalid_target")
    tokens = await sessions.issue_exchanged_token(subject, client.client_id, target, client.scopes)
    return JSONResponse(tokens, headers={"Cache-Control": "no-store"})


@router.get("/logout", summary="退出：吊销 sid 与全部 Refresh Token")
async def logout(request: Request, client_id: str = "", post_logout_redirect_uri: str = ""):
    sid = request.cookies.get(_cookie(request))
    if sid:
        await sessions.revoke_sid(sid)
    client = await _active_client(client_id) if client_id else None
    if client and post_logout_redirect_uri in client.post_logout_redirect_uris:
        response = RedirectResponse(post_logout_redirect_uri, status_code=302)
    else:
        response = message_page("已退出登录", status_code=200)
    response.delete_cookie(_cookie(request), path=PREFIX)
    return response
