"""Modelos propios. No contienen nada de Wialon: ni flags, ni claves de una letra.

Son `frozen` porque representan una lectura en un instante. Cambiar un vehículo
significa escribir en Wialon y volver a leer, no mutar el objeto.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class VehicleStatus(StrEnum):
    """Estado derivado por el backend (sección 4.4). Wialon no lo entrega."""

    MOVING = "en_movimiento"
    STOPPED = "detenido"
    OFFLINE = "sin_senal"


# Ocho rumbos: más divisiones no ayudan a nadie que mira un mapa.
_CARDINALES = ("N", "NE", "E", "SE", "S", "SO", "O", "NO")


def grados_a_cardinal(grados: float | None) -> str | None:
    if grados is None:
        return None
    indice = int((grados % 360) / 45 + 0.5) % 8
    return _CARDINALES[indice]


@dataclass(frozen=True, slots=True)
class Position:
    latitude: float
    longitude: float
    speed_kmh: float
    course_degrees: int | None
    cardinal: str | None
    altitude_m: int | None
    satellites: int | None
    reported_at: datetime  # siempre UTC; la UI la pasa a America/Bogota


@dataclass(frozen=True, slots=True)
class CustomField:
    """`name` es el nombre tal cual lo tiene el cliente, con erratas incluidas."""

    id: int
    name: str
    value: str


@dataclass(frozen=True, slots=True)
class Vehicle:
    id: int
    name: str  # `nm` de Wialon, p. ej. "957."
    plate: str | None  # del campo personalizado PLACA, si existe
    status: VehicleStatus
    position: Position | None
    custom_fields: list[CustomField] = field(default_factory=list)
    driver_id: int | None = None
    driver_name: str | None = None

    @property
    def display_name(self) -> str:
        """Lo que se muestra en lista, mapa y detalle."""
        return self.plate or self.name

    @property
    def minutes_since_report(self) -> float | None:
        if self.position is None:
            return None
        from datetime import UTC

        return (datetime.now(UTC) - self.position.reported_at).total_seconds() / 60


@dataclass(frozen=True, slots=True)
class Driver:
    id: int
    resource_id: int
    name: str
    code: str | None
    phone: str | None
    description: str | None
    bound_unit_id: int | None
    custom_fields: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Passenger:
    """En Wialon se llaman *tags*. El nombre del dominio es el del negocio."""

    id: int
    resource_id: int
    name: str
    code: str | None
    phone: str | None
    description: str | None
    custom_fields: dict[str, str] = field(default_factory=dict)
