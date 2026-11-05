"""Emisión y verificación de JWT (SEG-07)."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt

from app.core.config import get_settings
from app.domain.exceptions import AuthenticationError

ALGORITHM = "HS256"
TokenType = Literal["access", "refresh"]


def _encode(payload: dict[str, Any]) -> str:
    settings = get_settings()
    return jwt.encode(payload, settings.secret_key.get_secret_value(), algorithm=ALGORITHM)


def create_access_token(user_id: uuid.UUID) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    return _encode(
        {
            "sub": str(user_id),
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=settings.access_token_ttl_minutes),
        }
    )


def create_refresh_token(user_id: uuid.UUID, token_version: int) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    return _encode(
        {
            "sub": str(user_id),
            "type": "refresh",
            "ver": token_version,
            "iat": now,
            "exp": now + timedelta(days=settings.refresh_token_ttl_days),
        }
    )


def decode_token(token: str, expected_type: TokenType) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[ALGORITHM],
            options={"require": ["exp", "sub", "type"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("La sesión expiró.") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError("Credenciales inválidas.") from exc

    if payload.get("type") != expected_type:
        # Un refresh usado como access es un intento de abuso, no un descuido.
        raise AuthenticationError("Credenciales inválidas.")
    return payload
