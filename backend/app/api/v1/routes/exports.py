"""Exportación a CSV (RF-25). Exige permiso propio: el Visualizador no exporta."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from app.api.deps import SessionDep, VerifiedUser, require_permission
from app.core.config import get_settings
from app.domain.permissions import Permission
from app.infrastructure.wialon.client import get_wialon_client
from app.infrastructure.wialon.repository import WialonFleetRepository
from app.services import audit_service
from app.services.csv_service import generar_csv, nombre_archivo
from app.services.driver_service import DriverService
from app.services.passenger_service import PassengerService
from app.services.vehicle_service import VehicleService

router = APIRouter(prefix="/exports", tags=["exportación"])

Exportar = Depends(require_permission(Permission.EXPORT_CSV))


def _repo() -> WialonFleetRepository:
    return WialonFleetRepository(get_wialon_client())


def _respuesta(datos: bytes, base: str) -> Response:
    return Response(
        content=datos,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo(base)}"'},
    )


async def _registrar(session: SessionDep, request: Request, user: VerifiedUser, que: str) -> None:
    await audit_service.record(
        session,
        action="export.csv",
        request=request,
        user_id=user.id,
        user_email=user.email,
        entity_type="export",
        entity_id=que,
    )


@router.get("/vehicles.csv", dependencies=[Exportar], summary="Exportar vehículos")
async def export_vehicles(
    request: Request, session: SessionDep, user: VerifiedUser
) -> Response:
    settings = get_settings()
    servicio = VehicleService(_repo(), resource_id=settings.wialon_resource_id)
    pagina = await servicio.list_vehicles(page=1, page_size=100_000)

    filas = [
        (
            v.id,
            v.plate or "",
            v.name,
            v.status.value,
            v.position.speed_kmh if v.position else "",
            v.position.cardinal if v.position else "",
            v.position.latitude if v.position else "",
            v.position.longitude if v.position else "",
            v.position.reported_at if v.position else "",
            v.driver_name or "",
        )
        for v in pagina.items
    ]
    datos = generar_csv(
        [
            "id", "placa", "unidad", "estado", "velocidad_kmh", "rumbo",
            "latitud", "longitud", "ultimo_reporte", "conductor",
        ],
        filas,
    )
    await _registrar(session, request, user, "vehicles")
    return _respuesta(datos, "vehiculos")


@router.get("/drivers.csv", dependencies=[Exportar], summary="Exportar conductores")
async def export_drivers(
    request: Request, session: SessionDep, user: VerifiedUser
) -> Response:
    settings = get_settings()
    servicio = DriverService(_repo(), resource_id=settings.wialon_resource_id)
    conductores = await servicio.list_drivers()

    filas = [
        (d.id, d.name, d.code or "", d.phone or "", d.description or "", d.bound_unit_id or "")
        for d in conductores
    ]
    datos = generar_csv(
        ["id", "nombre", "codigo", "telefono", "descripcion", "unidad_vinculada"], filas
    )
    await _registrar(session, request, user, "drivers")
    return _respuesta(datos, "conductores")


@router.get("/passengers.csv", dependencies=[Exportar], summary="Exportar pasajeros")
async def export_passengers(
    request: Request, session: SessionDep, user: VerifiedUser
) -> Response:
    settings = get_settings()
    servicio = PassengerService(_repo(), resource_id=settings.wialon_resource_id)
    pasajeros = await servicio.list_passengers()

    # Los campos personalizados varían por pasajero: se recoge la unión de
    # todos los nombres para que cada uno tenga su columna.
    nombres_campos = sorted({c for p in pasajeros for c in p.custom_fields})

    filas = [
        (p.id, p.name, p.code or "", p.bound_unit_id or "")
        + tuple(p.custom_fields.get(c, "") for c in nombres_campos)
        for p in pasajeros
    ]
    datos = generar_csv(
        ["id", "nombre", "codigo", "unidad_asignada", *nombres_campos], filas
    )
    await _registrar(session, request, user, "passengers")
    return _respuesta(datos, "pasajeros")
