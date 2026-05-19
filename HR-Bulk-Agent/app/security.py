import hashlib
import hmac
import secrets
import os
import re
from typing import Any

from app.config import settings


SENSITIVE_KEYS = {
    "name",
    "phone",
    "email",
    "birth_date",
    "client_secret",
    "api_key",
    "token",
}


def digest(value: str) -> str:
    return hmac.new(settings.secret_key.encode(), value.encode(), hashlib.sha256).hexdigest()[:16]


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120000)
    return f"pbkdf2_sha256${salt}${derived.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, salt, expected = password_hash.split("$", 2)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    candidate = hash_password(password, salt).split("$", 2)[2]
    return hmac.compare_digest(candidate, expected)


def make_token() -> str:
    return secrets.token_urlsafe(32)


def mask_name(value: str | None) -> str | None:
    if not value:
        return value
    if len(value) <= 1:
        return "*"
    return value[0] + "*" * (len(value) - 1)


def mask_phone(value: str | None) -> str | None:
    if not value:
        return value
    digits = re.sub(r"\D", "", value)
    if len(digits) < 7:
        return "***"
    return f"{digits[:3]}****{digits[-4:]}"


def mask_email(value: str | None) -> str | None:
    if not value or "@" not in value:
        return value
    local, domain = value.split("@", 1)
    return f"{local[:2]}***@{domain}"


def mask_birth_date(value: str | None) -> str | None:
    if not value:
        return value
    return value[:4] + "-**-**" if len(value) >= 4 else "****"


def mask_payload(payload: dict[str, Any]) -> dict[str, Any]:
    masked: dict[str, Any] = {}
    for key, value in payload.items():
        key_lower = key.lower()
        if isinstance(value, dict):
            masked[key] = mask_payload(value)
        elif isinstance(value, list):
            masked[key] = [mask_payload(item) if isinstance(item, dict) else item for item in value]
        elif key == "name" or key_lower.endswith("name"):
            masked[key] = mask_name(str(value) if value is not None else None)
        elif key == "phone" or "phone" in key_lower:
            masked[key] = mask_phone(str(value) if value is not None else None)
        elif key == "email" or "email" in key_lower:
            masked[key] = mask_email(str(value) if value is not None else None)
        elif key == "birth_date" or "birth" in key_lower:
            masked[key] = mask_birth_date(str(value) if value is not None else None)
        elif key_lower in SENSITIVE_KEYS:
            masked[key] = "***"
        else:
            masked[key] = value
    return masked
