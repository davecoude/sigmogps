"""DTOs de autenticación. Nunca exponen el hash ni campos internos."""

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    description: str


class MeResponse(BaseModel):
    """El frontend arma su menú y sus guards con `permissions` (UX-05)."""

    id: uuid.UUID
    email: str
    full_name: str
    role: RoleOut
    permissions: list[str]
    must_change_password: bool
