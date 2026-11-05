"""Casos de uso de autenticación. No sabe de HTTP ni de cookies."""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    hash_password,
    needs_rehash,
    validate_password_policy,
    verify_password,
)
from app.domain.exceptions import AuthenticationError, ValidationError
from app.infrastructure.db.models import User
from app.services import audit_service

# Mensaje único: no revela si el correo existe (SEG-07).
CREDENCIALES_INVALIDAS = "Correo o contraseña incorrectos."


async def _get_by_email(session: AsyncSession, email: str) -> User | None:
    return await session.scalar(select(User).where(User.email == email.strip().lower()))


async def authenticate(
    session: AsyncSession, *, email: str, password: str, request: Request | None = None
) -> User:
    settings = get_settings()
    email_norm = email.strip().lower()
    user = await _get_by_email(session, email_norm)

    if user is None:
        # Se calcula un hash igual para que el tiempo de respuesta no delate
        # si el correo existe.
        hash_password(password)
        await audit_service.record(
            session,
            action="login.failed",
            request=request,
            user_email=email_norm,
            success=False,
            detail={"motivo": "usuario_inexistente"},
        )
        await session.commit()
        raise AuthenticationError(CREDENCIALES_INVALIDAS)

    ahora = datetime.now(UTC)
    if user.locked_until and user.locked_until > ahora:
        restantes = int((user.locked_until - ahora).total_seconds() // 60) + 1
        await audit_service.record(
            session,
            action="login.blocked",
            request=request,
            user_id=user.id,
            user_email=user.email,
            success=False,
        )
        await session.commit()
        raise AuthenticationError(f"Cuenta bloqueada temporalmente. Reintenta en {restantes} min.")

    if not verify_password(password, user.password_hash):
        user.failed_login_attempts += 1
        motivo = "clave_incorrecta"
        if user.failed_login_attempts >= settings.login_max_attempts:
            user.locked_until = ahora + timedelta(minutes=settings.login_lockout_minutes)
            user.failed_login_attempts = 0
            motivo = "bloqueo_por_intentos"
        await audit_service.record(
            session,
            action="login.failed",
            request=request,
            user_id=user.id,
            user_email=user.email,
            success=False,
            detail={"motivo": motivo},
        )
        await session.commit()
        raise AuthenticationError(CREDENCIALES_INVALIDAS)

    if not user.is_active:
        await audit_service.record(
            session,
            action="login.failed",
            request=request,
            user_id=user.id,
            user_email=user.email,
            success=False,
            detail={"motivo": "usuario_inactivo"},
        )
        await session.commit()
        raise AuthenticationError(CREDENCIALES_INVALIDAS)

    # Éxito
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = ahora
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)

    await audit_service.record(
        session, action="login.success", request=request, user_id=user.id, user_email=user.email
    )
    await session.commit()
    return user


async def change_password(
    session: AsyncSession,
    *,
    user: User,
    current_password: str,
    new_password: str,
    request: Request | None = None,
) -> None:
    if not verify_password(current_password, user.password_hash):
        raise AuthenticationError("La contraseña actual no coincide.")
    if current_password == new_password:
        raise ValidationError("La nueva contraseña debe ser distinta de la actual.")

    validate_password_policy(new_password)

    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    user.token_version += 1  # cierra las demás sesiones

    await audit_service.record(
        session,
        action="password.changed",
        request=request,
        user_id=user.id,
        user_email=user.email,
        entity_type="user",
        entity_id=str(user.id),
    )
    await session.commit()


async def revoke_sessions(
    session: AsyncSession, *, user: User, request: Request | None = None
) -> None:
    user.token_version += 1
    await audit_service.record(
        session, action="logout", request=request, user_id=user.id, user_email=user.email
    )
    await session.commit()


async def get_active_user(session: AsyncSession, user_id: uuid.UUID) -> User:
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("Credenciales inválidas.")
    return user
