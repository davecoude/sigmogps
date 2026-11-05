"""Registro de auditoría (RF-26, SEG-09). Nunca guarda contraseñas ni tokens."""

import uuid

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import AuditLog


async def record(
    session: AsyncSession,
    *,
    action: str,
    request: Request | None = None,
    user_id: uuid.UUID | None = None,
    user_email: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    success: bool = True,
    detail: dict | None = None,
) -> None:
    session.add(
        AuditLog(
            action=action,
            user_id=user_id,
            user_email=user_email,
            entity_type=entity_type,
            entity_id=entity_id,
            success=success,
            detail=detail,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent") if request else None,
        )
    )


def _client_ip(request: Request | None) -> str | None:
    if request is None:
        return None
    # Render va detrás de proxy: el primer salto de X-Forwarded-For es el cliente.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:45]
    return request.client.host if request.client else None
