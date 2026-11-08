"""Registro de auditoría (RF-26, SEG-09). Solo Admin."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import SessionDep, require_permission
from app.api.v1.schemas.audit import AuditEntry
from app.api.v1.schemas.common import PagedResponse, PageMeta
from app.domain.permissions import Permission
from app.services import audit_service

router = APIRouter(prefix="/audit", tags=["auditoría"])

Leer = Depends(require_permission(Permission.AUDIT_READ))


@router.get("/actions", response_model=list[str], dependencies=[Leer],
            summary="Acciones registradas")
async def list_actions(session: SessionDep) -> list[str]:
    return await audit_service.list_actions(session)


@router.get("", response_model=PagedResponse[AuditEntry], dependencies=[Leer],
            summary="Listar eventos")
async def list_entries(
    session: SessionDep,
    action: Annotated[str | None, Query(max_length=64)] = None,
    search: Annotated[str | None, Query(max_length=80)] = None,
    only_failures: Annotated[bool, Query(description="Solo eventos fallidos")] = False,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> PagedResponse[AuditEntry]:
    resultado = await audit_service.list_entries(
        session,
        action=action,
        search=search,
        only_failures=only_failures,
        page=page,
        page_size=page_size,
    )
    return PagedResponse(
        items=[AuditEntry.from_domain(a) for a in resultado.items],
        meta=PageMeta(
            total=resultado.total,
            page=resultado.page,
            page_size=resultado.page_size,
            pages=resultado.pages,
        ),
    )
