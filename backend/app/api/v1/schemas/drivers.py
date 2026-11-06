"""DTOs de conductores."""

from pydantic import BaseModel, Field

from app.domain.models import Driver


class DriverOut(BaseModel):
    id: int
    name: str
    code: str | None
    phone: str | None
    description: str | None
    bound_unit_id: int | None
    custom_fields: dict[str, str]

    @classmethod
    def from_domain(cls, d: Driver) -> "DriverOut":
        return cls(
            id=d.id,
            name=d.name,
            code=d.code,
            phone=d.phone,
            description=d.description,
            bound_unit_id=d.bound_unit_id,
            custom_fields=d.custom_fields,
        )


class DriverWrite(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str | None = Field(default=None, max_length=64)
    phone: str | None = Field(default=None, max_length=32)
    description: str | None = Field(default=None, max_length=255)
    # Si se omite, el servicio conserva los campos existentes en Wialon.
    custom_fields: dict[str, str] | None = None


class BindRequest(BaseModel):
    unit_id: int
