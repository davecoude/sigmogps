"""Endpoints de vehículos (RF-10 a RF-13, RF-23)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.api.deps import SessionDep, VerifiedUser, require_permission, verify_csrf
from app.api.v1.schemas.common import PagedResponse, PageMeta
from app.api.v1.schemas.passengers import PassengerOut
from app.api.v1.schemas.vehicles import (
    CustomFieldsWrite,
    FleetSummary,
    VehicleDetail,
    VehicleListItem,
)
from app.core.config import get_settings
from app.domain.exceptions import NotFoundError
from app.domain.models import VehicleStatus
from app.domain.permissions import Permission
from app.infrastructure.wialon.client import get_wialon_client
from app.infrastructure.wialon.repository import WialonFleetRepository
from app.services import audit_service
from app.services.passenger_service import PassengerService
from app.services.vehicle_service import VehicleService

router = APIRouter(prefix="/vehicles", tags=["vehículos"])

LeerVehiculos = Depends(require_permission(Permission.VEHICLES_READ))
EscribirVehiculos = Depends(require_permission(Permission.VEHICLES_WRITE))
Csrf = Depends(verify_csrf)


def get_vehicle_service() -> VehicleService:
    settings = get_settings()
    return VehicleService(
        WialonFleetRepository(get_wialon_client()),
        resource_id=settings.wialon_resource_id,
    )


ServiceDep = Annotated[VehicleService, Depends(get_vehicle_service)]


@router.get(
    "",
    response_model=PagedResponse[VehicleListItem],
    dependencies=[LeerVehiculos],
    summary="Listar vehículos",
)
async def list_vehicles(
    service: ServiceDep,
    search: Annotated[str | None, Query(max_length=80, description="Placa, unidad o conductor")] = None,
    status: Annotated[VehicleStatus | None, Query(description="Filtrar por estado derivado")] = None,
    without_driver: Annotated[bool, Query(description="Solo sin conductor vinculado")] = False,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PagedResponse[VehicleListItem]:
    resultado = await service.list_vehicles(
        search=search,
        status=status,
        only_without_driver=without_driver,
        page=page,
        page_size=page_size,
    )
    return PagedResponse(
        items=[VehicleListItem.from_domain(v) for v in resultado.items],
        meta=PageMeta(
            total=resultado.total,
            page=resultado.page,
            page_size=resultado.page_size,
            pages=resultado.pages,
        ),
    )


@router.get(
    "/summary",
    response_model=FleetSummary,
    dependencies=[LeerVehiculos],
    summary="KPIs de la flota",
)
async def summary(service: ServiceDep) -> FleetSummary:
    return FleetSummary(**await service.summary())


@router.get(
    "/{vehicle_id}",
    response_model=VehicleDetail,
    dependencies=[LeerVehiculos],
    summary="Detalle de vehículo",
)
async def get_vehicle(vehicle_id: int, service: ServiceDep) -> VehicleDetail:
    vehiculo = await service.get_vehicle(vehicle_id)
    if vehiculo is None:
        raise NotFoundError("El vehículo no existe o no es visible para esta cuenta.")
    return VehicleDetail.from_domain(vehiculo)


@router.get(
    "/{vehicle_id}/passengers",
    response_model=list[PassengerOut],
    dependencies=[LeerVehiculos],
    summary="Pasajeros asignados al vehículo",
)
async def passengers_of_vehicle(vehicle_id: int) -> list[PassengerOut]:
    """RF-09. Endpoint aparte y no dentro del detalle: la interfaz lo pide en
    paralelo y un fallo leyendo las asignaciones no deja sin datos al vehículo."""
    settings = get_settings()
    servicio = PassengerService(
        WialonFleetRepository(get_wialon_client()),
        resource_id=settings.wialon_resource_id,
    )
    return [
        PassengerOut.from_domain(p) for p in await servicio.passengers_of_unit(vehicle_id)
    ]


@router.put(
    "/{vehicle_id}/custom-fields",
    response_model=VehicleDetail,
    dependencies=[EscribirVehiculos, Csrf],
    summary="Reemplazar campos personalizados del vehículo",
)
async def replace_custom_fields(
    vehicle_id: int,
    payload: CustomFieldsWrite,
    request: Request,
    session: SessionDep,
    user: VerifiedUser,
    service: ServiceDep,
) -> VehicleDetail:
    """RF-19 y RF-20.

    Wialon expone un campo por llamada, así que el servicio calcula la
    diferencia contra el estado actual y escribe solo lo que cambió.
    """
    actualizado = await service.replace_custom_fields(vehicle_id, payload.custom_fields)
    await audit_service.record(
        session,
        action="vehicle.custom_fields_updated",
        request=request,
        user_id=user.id,
        user_email=user.email,
        entity_type="vehicle",
        entity_id=str(vehicle_id),
        detail={"campos": sorted(payload.custom_fields)},
    )
    return VehicleDetail.from_domain(actualizado)
