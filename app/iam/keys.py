import json
import secrets
import time

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.settings import settings

from .models import SigningKey

ALGORITHM = "RS256"


# 进程内缓存签名密钥，按 IAM_KEY_CACHE_TTL 重载：轮换后各节点在一个周期内切到新 kid，旧公钥在退役前仍在 JWKS
_cache: list[SigningKey] | None = None
_loaded_at = 0.0


def generate_key() -> tuple[str, str, dict]:
    """生成 (kid, 私钥 PEM, 公钥 JWK)，供 alembic seed 与密钥轮换使用"""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    kid = "k_" + secrets.token_hex(6)
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ).decode()
    public_jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key()))
    public_jwk.update(kid=kid, use="sig", alg=ALGORITHM)
    return kid, private_pem, public_jwk


async def _keys() -> list[SigningKey]:
    global _cache, _loaded_at
    if _cache is None or time.monotonic() - _loaded_at > settings.IAM_KEY_CACHE_TTL:
        _cache = await SigningKey.filter(active=True).order_by("-created_at")
        _loaded_at = time.monotonic()
        if not _cache:
            raise RuntimeError("iam.signing_key 为空，请先执行 alembic upgrade head")
    return _cache


async def jwks() -> dict:
    # 直接读库：新公钥先公布、各节点缓存到期后才用它签名，保证网关总能找到 kid
    keys = await SigningKey.filter(active=True).order_by("-created_at")
    return {"keys": [k.public_jwk for k in keys]}


async def sign(claims: dict) -> str:
    key = (await _keys())[0]
    return jwt.encode(claims, key.private_pem, algorithm=ALGORITHM, headers={"kid": key.kid})


async def verify(token: str, audience: str | None = None) -> dict:
    """校验本模块签发的 JWT（签名、iss、exp，可选 aud），失败抛 jwt.PyJWTError"""
    kid = jwt.get_unverified_header(token).get("kid")
    key = next((k for k in await _keys() if k.kid == kid), None)
    if key is None:
        raise jwt.InvalidKeyError("unknown kid")
    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key.public_jwk))
    return jwt.decode(
        token,
        public_key,
        algorithms=[ALGORITHM],
        issuer=settings.IAM_ISSUER,
        audience=audience,
        options={"verify_aud": audience is not None},
    )
