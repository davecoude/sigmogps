"""Siembra de roles, permisos y Admin inicial (RF-07). Idempotente."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import hash_password, validate_password_policy
from app.domain.permissions import (
    PERMISSION_DESCRIPTIONS,
    ROLE_DESCRIPTIONS,
    ROLE_PERMISSIONS,
    RoleName,
)
from app.infrastructure.db.models import Permission, Role, User

logger = get_logger(__name__)


async def _sync_permissions(session: AsyncSession) -> dict[str, Permission]:
    existentes = {p.code: p for p in (await session.scalars(select(Permission))).all()}
    for code, description in PERMISSION_DESCRIPTIONS.items():
        fila = existentes.get(code.value)
        if fila is None:
            fila = Permission(code=code.value, description=description)
            session.add(fila)
            existentes[code.value] = fila
        else:
            fila.description = description
    await session.flush()
    return existentes


async def _sync_roles(session: AsyncSession, permisos: dict[str, Permission]) -> dict[str, Role]:
    existentes = {r.name: r for r in (await session.scalars(select(Role))).all()}
    for role_name, codes in ROLE_PERMISSIONS.items():
        fila = existentes.get(role_name.value)
        if fila is None:
            fila = Role(name=role_name.value, description=ROLE_DESCRIPTIONS[role_name])
            session.add(fila)
            existentes[role_name.value] = fila
        else:
            fila.description = ROLE_DESCRIPTIONS[role_name]
        # Reemplaza la lista completa: quitar un permiso del catálogo lo quita del rol.
        fila.permissions = [permisos[c.value] for c in sorted(codes)]
    await session.flush()
    return existentes


async def _ensure_admin(session: AsyncSession, roles: dict[str, Role]) -> None:
    settings = get_settings()
    email = settings.admin_email.strip().lower()
    password = settings.admin_password.get_secret_value()

    if not email or not password:
        logger.warning("seed_admin_omitido", motivo="ADMIN_EMAIL o ADMIN_PASSWORD sin definir")
        return

    validate_password_policy(password)

    existente = await session.scalar(select(User).where(User.email == email))
    if existente is not None:
        if not settings.admin_password_force:
            logger.info("seed_admin_existente", email=email)
            return
        # Reinicio explícito: sube token_version para cerrar las sesiones vivas.
        existente.password_hash = hash_password(password)
        existente.must_change_password = False
        existente.is_active = True
        existente.failed_login_attempts = 0
        existente.locked_until = None
        existente.token_version += 1
        logger.warning("seed_admin_clave_reiniciada", email=email)
        return

    session.add(
        User(
            email=email,
            password_hash=hash_password(password),
            full_name="Administrador",
            role_id=roles[RoleName.ADMIN.value].id,
            is_active=True,
            # El Admin sembrado no cambia contraseña: sus credenciales se
            # entregan al evaluador y deben funcionar tal cual (sección 10.3).
            must_change_password=False,
        )
    )
    logger.info("seed_admin_creado", email=email)


async def run_seed(session: AsyncSession) -> None:
    permisos = await _sync_permissions(session)
    roles = await _sync_roles(session, permisos)
    await _ensure_admin(session, roles)
    await session.commit()
    logger.info("seed_completado", permisos=len(permisos), roles=len(roles))
