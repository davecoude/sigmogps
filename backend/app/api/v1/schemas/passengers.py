"""DTOs de pasajeros."""

from pydantic import BaseModel, Field

from app.domain.models import Passenger


class PassengerOut(BaseModel):
    id: int
    name: str
    code: str | None
    custom_fields: dict[str, str]
    bound_unit_id: int | None

    @classmethod
    def from_domain(cls, p: Passenger) -> "PassengerOut":
        return cls(
            id=p.id,
            name=p.name,
            code=p.code,
            custom_fields=p.custom_fields,
            bound_unit_id=p.bound_unit_id,
        )


class PassengerWrite(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str | None = Field(default=None, max_length=64)
    # Omitirlo conserva los campos actuales; enviarlo los reemplaza.
    custom_fields: dict[str, str] | None = None


class CustomFieldsWrite(BaseModel):
    """Conjunto completo de campos. Lo que no venga, se elimina (RF-27)."""

    custom_fields: dict[str, str]


class AssignRequest(BaseModel):
    unit_id: int
