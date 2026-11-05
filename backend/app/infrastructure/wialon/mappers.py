"""Traducción de la respuesta cruda de Wialon a modelos propios (INT-04, sección 4.4).

Único lugar del sistema donde aparecen `nm`, `pos`, `flds` o `jp`.
"""

import unicodedata
from datetime import UTC, datetime
from typing import Any

from app.core.config import get_settings
from app.domain.models import (
    CustomField,
    Driver,
    Passenger,
    Position,
    Vehicle,
    VehicleStatus,
    grados_a_cardinal,
)

CAMPO_PLACA = "PLACA"


def normalizar_nombre_campo(nombre: str) -> str:
    """Para comparar, no para guardar.

    Los datos reales traen LINEA y LÍNEA, COLOR y COLORE, PROPIETARIO y
    PROPOIETARIO. Se normaliza acento y caja para buscar, pero al escribir de
    vuelta se usa el nombre original: renombrar el campo del cliente en
    silencio sería corromper su dato.
    """
    sin_acentos = unicodedata.normalize("NFKD", nombre)
    sin_acentos = "".join(c for c in sin_acentos if not unicodedata.combining(c))
    return sin_acentos.strip().upper()


def _entero(valor: Any) -> int | None:
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _decimal(valor: Any) -> float | None:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def map_position(pos: dict[str, Any] | None) -> Position | None:
    """Valida coordenadas: Wialon entrega 0,0 cuando no tiene arreglo de GPS."""
    if not pos:
        return None

    lat = _decimal(pos.get("y"))
    lon = _decimal(pos.get("x"))
    marca = _entero(pos.get("t"))

    if lat is None or lon is None or marca is None:
        return None
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        return None
    if lat == 0 and lon == 0:
        return None

    rumbo = _entero(pos.get("c"))
    return Position(
        latitude=lat,
        longitude=lon,
        speed_kmh=max(0.0, _decimal(pos.get("s")) or 0.0),
        course_degrees=rumbo,
        cardinal=grados_a_cardinal(rumbo),
        altitude_m=_entero(pos.get("z")),
        satellites=_entero(pos.get("sc")),
        reported_at=datetime.fromtimestamp(marca, tz=UTC),
    )


def derive_status(position: Position | None) -> VehicleStatus:
    """Dos umbrales configurables, ningún número suelto por el código.

    - Sin posición o reporte viejo -> sin señal.
    - Con reporte fresco, la velocidad decide. El mínimo de 3 km/h existe
      porque un GPS detenido reporta deriva de uno o dos km/h.
    """
    settings = get_settings()
    if position is None:
        return VehicleStatus.OFFLINE

    minutos = (datetime.now(UTC) - position.reported_at).total_seconds() / 60
    if minutos >= settings.vehicle_stale_minutes:
        return VehicleStatus.OFFLINE

    if position.speed_kmh > settings.vehicle_moving_min_kmh:
        return VehicleStatus.MOVING
    return VehicleStatus.STOPPED


def map_custom_fields(flds: dict[str, Any] | None) -> list[CustomField]:
    if not flds:
        return []
    salida: list[CustomField] = []
    for bruto in flds.values():
        identificador = _entero(bruto.get("id"))
        nombre = (bruto.get("n") or "").strip()
        if identificador is None or not nombre:
            continue
        salida.append(
            CustomField(id=identificador, name=nombre, value=str(bruto.get("v") or ""))
        )
    return sorted(salida, key=lambda c: c.name)


def buscar_campo(campos: list[CustomField], nombre: str) -> CustomField | None:
    objetivo = normalizar_nombre_campo(nombre)
    for campo in campos:
        if normalizar_nombre_campo(campo.name) == objetivo:
            return campo
    return None


def map_vehicle(item: dict[str, Any]) -> Vehicle:
    identificador = _entero(item.get("id"))
    if identificador is None:
        raise ValueError("La unidad de Wialon no trae id")

    campos = map_custom_fields(item.get("flds"))
    placa = buscar_campo(campos, CAMPO_PLACA)
    posicion = map_position(item.get("pos"))

    return Vehicle(
        id=identificador,
        name=(item.get("nm") or f"Unidad {identificador}").strip(),
        plate=(placa.value.strip() or None) if placa else None,
        status=derive_status(posicion),
        position=posicion,
        custom_fields=campos,
    )


def map_vehicles(payload: dict[str, Any]) -> list[Vehicle]:
    return [map_vehicle(i) for i in (payload.get("items") or []) if i]


def map_driver(bruto: dict[str, Any], *, resource_id: int) -> Driver:
    identificador = _entero(bruto.get("id"))
    if identificador is None:
        raise ValueError("El conductor de Wialon no trae id")

    # `bu` es la unidad a la que está vinculado; 0 significa ninguna (RF-13).
    unidad = _entero(bruto.get("bu")) or None

    return Driver(
        id=identificador,
        resource_id=resource_id,
        name=(bruto.get("n") or "").strip(),
        code=(bruto.get("c") or "").strip() or None,
        phone=(bruto.get("p") or "").strip() or None,
        description=(bruto.get("ds") or "").strip() or None,
        bound_unit_id=unidad,
        custom_fields={k: str(v) for k, v in (bruto.get("jp") or {}).items()},
    )


def map_passenger(bruto: dict[str, Any], *, resource_id: int) -> Passenger:
    identificador = _entero(bruto.get("id"))
    if identificador is None:
        raise ValueError("El pasajero de Wialon no trae id")

    return Passenger(
        id=identificador,
        resource_id=resource_id,
        name=(bruto.get("n") or "").strip(),
        code=(bruto.get("c") or "").strip() or None,
        phone=(bruto.get("p") or "").strip() or None,
        description=(bruto.get("ds") or "").strip() or None,
        custom_fields={k: str(v) for k, v in (bruto.get("jp") or {}).items()},
    )
