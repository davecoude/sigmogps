"""Endpoints de vehículos (RF-10 a RF-13, RF-23)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import require_permission
from app.api.v1.schemas.common import PagedResponse, PageMeta
from app.api.v1.schemas.vehicles import FleetSummary, VehicleDetail, VehicleListItem
from app.core.config import get_settings
from app.domain.exceptions import NotFoundError
from app.domain.models import VehicleStatus
from app.domain.permissions import Permission
from app.infrastructure.wialon.client import get_wialon_client
from app.infrastructure.wialon.repository import WialonFleetRepository
from app.services.vehicle_service import VehicleService

router = APIRouter(prefix="/vehicles", tags=["vehículos"])

LeerVehiculos = Depends(require_permission(Permission.VEHICLES_READ))


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
