"""DTOs de vehículos. Nombres explícitos y unidades declaradas."""

from dataclasses import asdict
from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.models import Vehicle, VehicleStatus


class PositionOut(BaseModel):
    latitude: float
    longitude: float
    speed_kmh: float = Field(description="Velocidad en kilómetros por hora")
    course_degrees: int | None = Field(default=None, description="Rumbo en grados, 0 a 359")
    cardinal: str | None = Field(default=None, description="Punto cardinal del rumbo")
    altitude_m: int | None = None
    satellites: int | None = None
    reported_at: datetime = Field(description="ISO-8601 en UTC")


class CustomFieldOut(BaseModel):
    id: int
    name: str
    value: str


class VehicleListItem(BaseModel):
    id: int
    name: str
    plate: str | None
    display_name: str
    status: VehicleStatus
    position: PositionOut | None
    driver_id: int | None
    driver_name: str | None
    minutes_since_report: float | None

    @classmethod
    def from_domain(cls, v: Vehicle) -> "VehicleListItem":
        return cls(
            id=v.id,
            name=v.name,
            plate=v.plate,
            display_name=v.display_name,
            status=v.status,
            position=PositionOut(**asdict(v.position)) if v.position else None,
            driver_id=v.driver_id,
            driver_name=v.driver_name,
            minutes_since_report=(
                round(v.minutes_since_report, 1) if v.minutes_since_report is not None else None
            ),
        )


class VehicleDetail(VehicleListItem):
    custom_fields: list[CustomFieldOut]

    @classmethod
    def from_domain(cls, v: Vehicle) -> "VehicleDetail":
        base = VehicleListItem.from_domain(v).model_dump()
        return cls(
            **base,
            custom_fields=[CustomFieldOut(**asdict(c)) for c in v.custom_fields],
        )


class FleetSummary(BaseModel):
    total: int
    en_movimiento: int
    detenidos: int
    sin_senal: int
    con_conductor: int
    sin_conductor: int
