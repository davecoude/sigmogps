"""Gestión de usuarios, exclusiva del Admin (RF-06).

Dos reglas que no son obvias y protegen de quedarse sin administrador:
un Admin no puede desactivarse a sí mismo ni quitarse su propio rol.
Sin ellas, un clic deja la plataforma sin nadie que pueda gobernarla.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import generate_password, hash_password
from app.domain.exceptions import ConflictError, NotFoundError, ValidationError
from app.domain.pagination import Page, paginar
from app.domain.permissions import RoleName
from app.infrastructure.db.models import Role, User


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_roles(self) -> list[Role]:
        filas = await self._session.scalars(select(Role).order_by(Role.id))
        return list(filas.all())

    async def list_users(self, *, search: str | None = None) -> list[User]:
        consulta = select(User).order_by(User.created_at.desc())
        filas = list((await self._session.scalars(consulta)).all())
        if search:
            aguja = search.strip().lower()
            filas = [
                u for u in filas if aguja in u.email.lower() or aguja in u.full_name.lower()
            ]
        return filas

    async def list_page(
        self, *, search: str | None = None, page: int = 1, page_size: int = 25
    ) -> Page[User]:
        return paginar(await self.list_users(search=search), page=page, page_size=page_size)

    async def _get(self, user_id: uuid.UUID) -> User:
        usuario = await self._session.get(User, user_id)
        if usuario is None:
            raise NotFoundError("El usuario no existe.")
        return usuario

    async def _get_role(self, role_id: int) -> Role:
        rol = await self._session.get(Role, role_id)
        if rol is None:
            raise ValidationError("El rol indicado no existe.")
        return rol

    async def create_user(
        self, *, email: str, full_name: str, role_id: int
    ) -> tuple[User, str]:
        """Devuelve el usuario y su contraseña temporal, que solo se ve aquí."""
        correo = email.strip().lower()
        if await self._session.scalar(select(User).where(User.email == correo)):
            raise ConflictError("Ya existe un usuario con ese correo.")

        rol = await self._get_role(role_id)
        temporal = generate_password(16)

        usuario = User(
            email=correo,
            full_name=full_name.strip(),
            password_hash=hash_password(temporal),
            role_id=rol.id,
            is_active=True,
            must_change_password=True,  # obligatorio en el primer ingreso
        )
        self._session.add(usuario)
        await self._session.flush()
        await self._session.refresh(usuario, ["role"])
        return usuario, temporal

    async def change_role(
        self, user_id: uuid.UUID, role_id: int, *, actor: User
    ) -> User:
        usuario = await self._get(user_id)
        rol = await self._get_role(role_id)

        if usuario.id == actor.id and rol.name != RoleName.ADMIN.value:
            raise ConflictError(
                "No puedes quitarte tu propio rol de Admin. Pídeselo a otro administrador."
            )

        usuario.role_id = rol.id
        # El rol cambió: las sesiones abiertas llevan permisos viejos.
        usuario.token_version += 1
        await self._session.flush()
        await self._session.refresh(usuario, ["role"])
        return usuario

    async def set_active(
        self, user_id: uuid.UUID, activo: bool, *, actor: User
    ) -> User:
        usuario = await self._get(user_id)

        if usuario.id == actor.id and not activo:
            raise ConflictError("No puedes desactivar tu propia cuenta.")

        usuario.is_active = activo
        if not activo:
            usuario.token_version += 1  # cierra sus sesiones
        else:
            usuario.failed_login_attempts = 0
            usuario.locked_until = None
        await self._session.flush()
        await self._session.refresh(usuario, ["role"])
        return usuario

    async def reset_credentials(self, user_id: uuid.UUID) -> tuple[User, str]:
        usuario = await self._get(user_id)
        temporal = generate_password(16)

        usuario.password_hash = hash_password(temporal)
        usuario.must_change_password = True
        usuario.failed_login_attempts = 0
        usuario.locked_until = None
        usuario.token_version += 1  # invalida todo lo emitido

        await self._session.flush()
        await self._session.refresh(usuario, ["role"])
        return usuario, temporal

    @staticmethod
    def ahora() -> datetime:
        return datetime.now(UTC)
