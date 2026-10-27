import re
from typing import Any


_SENSITIVE_KEYS = {
    "auth",
    "pwd",
    "sign",
    "xkmsign",
    "xkmeventsign",
    "sub",
    "file",
    "files",
    "filename",
}
_SENSITIVE_KEY_PARTS = (
    "password",
    "passwd",
    "passcode",
    "token",
    "secret",
    "authorization",
    "cookie",
    "credential",
    "signature",
    "privatekey",
    "apikey",
    "accesskey",
    "csrf",
    "username",
    "alias",
    "email",
    "phone",
    "mobile",
    "avatar",
    "session",
    "nonce",
    "verifier",
)


def redact_sensitive_data(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: redact_sensitive_data(item)
            for key, item in value.items()
            if not _is_sensitive_key(key)
        }
    if isinstance(value, list):
        return [redact_sensitive_data(item) for item in value]
    if isinstance(value, str) and re.match(r"^https?://", value, re.I):
        return value.split("?", 1)[0].split("#", 1)[0]
    return value


def _is_sensitive_key(key: Any) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", str(key).lower())
    return (
        normalized in _SENSITIVE_KEYS
        or normalized.endswith("sub")
        or any(part in normalized for part in _SENSITIVE_KEY_PARTS)
    )
