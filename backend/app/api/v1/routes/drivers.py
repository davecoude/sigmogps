"""Endpoints de conductores (RF-16, RF-17, RF-18)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.deps import SessionDep, VerifiedUser, require_permission, verify_csrf
from app.api.v1.schemas.common import PagedResponse, PageMeta
from app.api.v1.schemas.drivers import BindRequest, DriverOut, DriverWrite
from app.core.config import get_settings
from app.domain.permissions import Permission
from app.infrastructure.wialon.client import get_wialon_client
from app.infrastructure.wialon.repository import WialonFleetRepository
from app.services import audit_service
from app.services.driver_service import DriverInput, DriverService

router = APIRouter(prefix="/drivers", tags=["conductores"])

Leer = Depends(require_permission(Permission.DRIVERS_READ))
Escribir = Depends(require_permission(Permission.DRIVERS_WRITE))
Vincular = Depends(require_permission(Permission.BINDINGS_WRITE))
Csrf = Depends(verify_csrf)


def get_driver_service() -> DriverService:
    settings = get_settings()
    return DriverService(
        WialonFleetRepository(get_wialon_client()),
        resource_id=settings.wialon_resource_id,
    )


ServiceDep = Annotated[DriverService, Depends(get_driver_service)]


def _a_input(payload: DriverWrite) -> DriverInput:
    return DriverInput(
        name=payload.name,
        code=payload.code,
        phone=payload.phone,
        description=payload.description,
        custom_fields=payload.custom_fields,
    )


@router.get("", response_model=PagedResponse[DriverOut], dependencies=[Leer],
            summary="Listar conductores")
async def list_drivers(
    service: ServiceDep,
    search: Annotated[str | None, Query(max_length=80)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> PagedResponse[DriverOut]:
    resultado = await service.list_page(search=search, page=page, page_size=page_size)
    return PagedResponse(
        items=[DriverOut.from_domain(d) for d in resultado.items],
        meta=PageMeta(
            total=resultado.total,
            page=resultado.page,
            page_size=resultado.page_size,
            pages=resultado.pages,
        ),
    )


@router.get("/{driver_id}", response_model=DriverOut, dependencies=[Leer], summary="Detalle")
async def get_driver(driver_id: int, service: ServiceDep) -> DriverOut:
    return DriverOut.from_domain(await service.get_driver(driver_id))


@router.post(
    "",
    response_model=DriverOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Escribir, Csrf],
    summary="Crear conductor",
)
async def create_driver(
    payload: DriverWrite,
    request: Request,
    session: SessionDep,
    user: VerifiedUser,
    service: ServiceDep,
) -> DriverOut:
    creado = await service.create_driver(_a_input(payload))
    await audit_service.record(
        session,
        action="driver.created",
        request=request,
        user_id=user.id,
        user_email=user.email,
        entity_type="driver",
        entity_id=str(creado.id),
        detail={"nombre": creado.name},
    )
    return DriverOut.from_domain(creado)


@router.put(
    "/{driver_id}",
    response_model=DriverOut,
    dependencies=[Escribir, Csrf],
    summary="Editar conductor",
)
async def update_driver(
    driver_id: int,
    payload: DriverWrite,
    request: Request,
    session: SessionDep,
    user: VerifiedUser,
    service: ServiceDep,
) -> DriverOut:
    actualizado = await service.update_driver(driver_id, _a_input(payload))
    await audit_service.record(
        session,
        action="driver.updated",
        request=request,
        user_id=user.id,
        user_email=user.email,
        entity_type="driver",
        entity_id=str(driver_id),
        detail={"nombre": actualizado.name},
    )
    return DriverOut.from_domain(actualizado)


@router.delete(
    "/{driver_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Escribir, Csrf],
    summary="Eliminar conductor",
)
async def delete_driver(
    driver_id: int,
    request: Request,
    session: SessionDep,
    user: VerifiedUser,
    service: ServiceDep,
) -> None:
    await service.delete_driver(driver_id)
    await audit_service.record(
        session,
        action="driver.deleted",
        request=request,
        user_id=user.id,
        user_email=user.email,
        entity_type="driver",
        entity_id=str(driver_id),
    )


@router.post(
    "/{driver_id}/bind",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Vincular, Csrf],
    summary="Vincular a un vehículo",
)
async def bind_driver(
    driver_id: int,
    payload: BindRequest,
    request: Request,
    session: SessionDep,
    user: VerifiedUser,
    service: ServiceDep,
) -> None:
    await service.bind(driver_id=driver_id, unit_id=payload.unit_id)
    await audit_service.record(
        session,
        action="driver.bound",
        request=request,
        user_id=user.id,
        user_email=user.email,
        entity_type="driver",
        entity_id=str(driver_id),
        detail={"unit_id": payload.unit_id},
    )


@router.post(
    "/{driver_id}/unbind",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Vincular, Csrf],
    summary="Desvincular de un vehículo",
)
async def unbind_driver(
    driver_id: int,
    payload: BindRequest,
    request: Request,
    session: SessionDep,
    user: VerifiedUser,
    service: ServiceDep,
) -> None:
    await service.unbind(driver_id=driver_id, unit_id=payload.unit_id)
    await audit_service.record(
        session,
        action="driver.unbound",
        request=request,
        user_id=user.id,
        user_email=user.email,
        entity_type="driver",
        entity_id=str(driver_id),
        detail={"unit_id": payload.unit_id},
    )
