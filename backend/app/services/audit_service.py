"""Registro de auditoría (RF-26, SEG-09). Nunca guarda contraseñas ni tokens."""

import uuid

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from app.infrastructure.db.models import AuditLog
from app.domain.pagination import Page


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

async def list_entries(
    session: AsyncSession,
    *,
    action: str | None = None,
    search: str | None = None,
    only_failures: bool = False,
    page: int = 1,
    page_size: int = 25,
) -> Page[AuditLog]:
    """Listado paginado en la base, no en memoria: esta tabla solo crece."""
    condiciones = []
    if action:
        condiciones.append(AuditLog.action == action)
    if only_failures:
        condiciones.append(AuditLog.success.is_(False))
    if search:
        patron = f"%{search.strip().lower()}%"
        condiciones.append(
            func.lower(func.coalesce(AuditLog.user_email, "")).like(patron)
            | func.lower(func.coalesce(AuditLog.entity_id, "")).like(patron)
            | func.lower(AuditLog.action).like(patron)
        )

    base = select(AuditLog)
    if condiciones:
        for c in condiciones:
            base = base.where(c)

    total = await session.scalar(
        select(func.count()).select_from(base.subquery())
    ) or 0

    filas = await session.scalars(
        base.order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return Page(items=list(filas.all()), total=total, page=page, page_size=page_size)


async def list_actions(session: AsyncSession) -> list[str]:
    """Acciones distintas presentes, para alimentar el filtro."""
    filas = await session.scalars(select(AuditLog.action).distinct().order_by(AuditLog.action))
    return list(filas.all())
