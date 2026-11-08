"""DTOs de gestión de usuarios (RF-06). Nunca exponen el hash."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.infrastructure.db.models import User


class RoleOption(BaseModel):
    id: int
    name: str
    description: str
    permissions: list[str]


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role_name: str
    is_active: bool
    must_change_password: bool
    is_locked: bool
    last_login_at: datetime | None
    created_at: datetime

    @classmethod
    def from_domain(cls, u: User, *, ahora: datetime) -> "UserOut":
        return cls(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role_name=u.role.name,
            is_active=u.is_active,
            must_change_password=u.must_change_password,
            is_locked=bool(u.locked_until and u.locked_until > ahora),
            last_login_at=u.last_login_at,
            created_at=u.created_at,
        )


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    role_id: int


class UserRoleUpdate(BaseModel):
    role_id: int


class UserActiveUpdate(BaseModel):
    is_active: bool


class TemporaryPassword(BaseModel):
    """La contraseña generada viaja una sola vez, en la respuesta.

    No se guarda en claro ni se registra en los logs: el Admin la copia y se
    la entrega al usuario, que debe cambiarla en su primer ingreso.
    """

    user_id: uuid.UUID
    email: str
    temporary_password: str
