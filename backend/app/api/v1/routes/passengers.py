"""Endpoints de pasajeros (RF-08, RF-09, RF-27, RF-28)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.deps import SessionDep, VerifiedUser, require_permission, verify_csrf
from app.api.v1.schemas.passengers import (
    AssignRequest,
    CustomFieldsWrite,
    PassengerOut,
    PassengerWrite,
)
from app.api.v1.schemas.common import PagedResponse, PageMeta
from app.core.config import get_settings
from app.domain.permissions import Permission
from app.infrastructure.wialon.client import get_wialon_client
from app.infrastructure.wialon.repository import WialonFleetRepository
from app.services import audit_service
from app.services.passenger_service import PassengerInput, PassengerService

router = APIRouter(prefix="/passengers", tags=["pasajeros"])

Leer = Depends(require_permission(Permission.PASSENGERS_READ))
Escribir = Depends(require_permission(Permission.PASSENGERS_WRITE))
Asignar = Depends(require_permission(Permission.BINDINGS_WRITE))
Csrf = Depends(verify_csrf)


def get_passenger_service() -> PassengerService:
    settings = get_settings()
    return PassengerService(
        WialonFleetRepository(get_wialon_client()),
        resource_id=settings.wialon_resource_id,
    )


ServiceDep = Annotated[PassengerService, Depends(get_passenger_service)]


@router.get("", response_model=PagedResponse[PassengerOut], dependencies=[Leer],
            summary="Listar pasajeros")
async def list_passengers(
    service: ServiceDep,
    search: Annotated[str | None, Query(max_length=80, description="Nombre, código o campo personalizado")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> PagedResponse[PassengerOut]:
    resultado = await service.list_page(search=search, page=page, page_size=page_size)
    return PagedResponse(
        items=[PassengerOut.from_domain(p) for p in resultado.items],
        meta=PageMeta(
            total=resultado.total,
            page=resultado.page,
            page_size=resultado.page_size,
            pages=resultado.pages,
        ),
    )


@router.post("", response_model=PassengerOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Escribir, Csrf], summary="Crear pasajero")
async def create_passenger(
    payload: PassengerWrite,
    request: Request,
    session: SessionDep,
    user: VerifiedUser,
    service: ServiceDep,
) -> PassengerOut:
    creado = await service.create_passenger(
        PassengerInput(name=payload.name, code=payload.code, custom_fields=payload.custom_fields)
    )
    await audit_service.record(
        session, action="passenger.created", request=request, user_id=user.id,
        user_email=user.email, entity_type="passenger", entity_id=str(creado.id),
        detail={"nombre": creado.name},
    )
    return PassengerOut.from_domain(creado)


@router.put("/{passenger_id}", response_model=PassengerOut,
            dependencies=[Escribir, Csrf], summary="Editar pasajero")
async def update_passenger(
    passenger_id: int,
    payload: PassengerWrite,
    request: Request,
    session: SessionDep,
    user: VerifiedUser,
    service: ServiceDep,
) -> PassengerOut:
    actualizado = await service.update_passenger(
        passenger_id,
        PassengerInput(name=payload.name, code=payload.code, custom_fields=payload.custom_fields),
    )
    await audit_service.record(
        session, action="passenger.updated", request=request, user_id=user.id,
        user_email=user.email, entity_type="passenger", entity_id=str(passenger_id),
        detail={"nombre": actualizado.name},
    )
    return PassengerOut.from_domain(actualizado)


@router.put("/{passenger_id}/custom-fields", response_model=PassengerOut,
            dependencies=[Escribir, Csrf], summary="Reemplazar campos personalizados")
async def replace_custom_fields(
    passenger_id: int,
    payload: CustomFieldsWrite,
    request: Request,
    session: SessionDep,
    user: VerifiedUser,
    service: ServiceDep,
) -> PassengerOut:
    actualizado = await service.replace_custom_fields(passenger_id, payload.custom_fields)
    await audit_service.record(
        session, action="passenger.custom_fields_updated", request=request, user_id=user.id,
        user_email=user.email, entity_type="passenger", entity_id=str(passenger_id),
        detail={"campos": sorted(payload.custom_fields)},
    )
    return PassengerOut.from_domain(actualizado)


@router.delete("/{passenger_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Escribir, Csrf], summary="Eliminar pasajero")
async def delete_passenger(
    passenger_id: int,
    request: Request,
    session: SessionDep,
    user: VerifiedUser,
    service: ServiceDep,
) -> None:
    await service.delete_passenger(passenger_id)
    await audit_service.record(
        session, action="passenger.deleted", request=request, user_id=user.id,
        user_email=user.email, entity_type="passenger", entity_id=str(passenger_id),
    )


@router.post("/{passenger_id}/assign", status_code=status.HTTP_204_NO_CONTENT,
             dependencies=[Asignar, Csrf], summary="Asignar a un vehículo")
async def assign(
    passenger_id: int,
    payload: AssignRequest,
    request: Request,
    session: SessionDep,
    user: VerifiedUser,
    service: ServiceDep,
) -> None:
    await service.assign(passenger_id=passenger_id, unit_id=payload.unit_id)
    await audit_service.record(
        session, action="passenger.assigned", request=request, user_id=user.id,
        user_email=user.email, entity_type="passenger", entity_id=str(passenger_id),
        detail={"unit_id": payload.unit_id},
    )


@router.post("/{passenger_id}/unassign", status_code=status.HTTP_204_NO_CONTENT,
             dependencies=[Asignar, Csrf], summary="Desasignar de un vehículo")
async def unassign(
    passenger_id: int,
    payload: AssignRequest,
    request: Request,
    session: SessionDep,
    user: VerifiedUser,
    service: ServiceDep,
) -> None:
    await service.unassign(passenger_id=passenger_id, unit_id=payload.unit_id)
    await audit_service.record(
        session, action="passenger.unassigned", request=request, user_id=user.id,
        user_email=user.email, entity_type="passenger", entity_id=str(passenger_id),
        detail={"unit_id": payload.unit_id},
    )
