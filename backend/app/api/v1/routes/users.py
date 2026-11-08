"""Endpoints de gestión de usuarios (RF-06). Solo Admin."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import SessionDep, VerifiedUser, require_permission, verify_csrf
from app.api.v1.schemas.common import PagedResponse, PageMeta
from app.api.v1.schemas.users import (
    RoleOption,
    TemporaryPassword,
    UserActiveUpdate,
    UserCreate,
    UserOut,
    UserRoleUpdate,
)
from app.domain.permissions import Permission
from app.services import audit_service
from app.services.user_service import UserService
from fastapi import APIRouter, Depends, Query, Request

router = APIRouter(prefix="/users", tags=["usuarios"])

Gestionar = Depends(require_permission(Permission.USERS_MANAGE))
Csrf = Depends(verify_csrf)


def get_user_service(session: SessionDep) -> UserService:
    return UserService(session)


ServiceDep = Annotated[UserService, Depends(get_user_service)]


# Esta ruta va antes que /{user_id}: si no, "roles" se intenta leer como UUID.
@router.get("/roles", response_model=list[RoleOption], dependencies=[Gestionar],
            summary="Roles disponibles")
async def list_roles(service: ServiceDep) -> list[RoleOption]:
    return [
        RoleOption(
            id=r.id,
            name=r.name,
            description=r.description,
            permissions=sorted(p.code for p in r.permissions),
        )
        for r in await service.list_roles()
    ]


@router.get("", response_model=PagedResponse[UserOut], dependencies=[Gestionar],
            summary="Listar usuarios")
async def list_users(
    service: ServiceDep,
    search: Annotated[str | None, Query(max_length=80)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> PagedResponse[UserOut]:
    ahora = UserService.ahora()
    resultado = await service.list_page(search=search, page=page, page_size=page_size)
    return PagedResponse(
        items=[UserOut.from_domain(u, ahora=ahora) for u in resultado.items],
        meta=PageMeta(
            total=resultado.total,
            page=resultado.page,
            page_size=resultado.page_size,
            pages=resultado.pages,
        ),
    )


@router.post("", response_model=TemporaryPassword, status_code=201,
             dependencies=[Gestionar, Csrf], summary="Crear usuario")
async def create_user(
    payload: UserCreate,
    request: Request,
    session: SessionDep,
    actor: VerifiedUser,
    service: ServiceDep,
) -> TemporaryPassword:
    usuario, temporal = await service.create_user(
        email=payload.email, full_name=payload.full_name, role_id=payload.role_id
    )
    await audit_service.record(
        session,
        action="user.created",
        request=request,
        user_id=actor.id,
        user_email=actor.email,
        entity_type="user",
        entity_id=str(usuario.id),
        # El detalle nunca lleva la contraseña.
        detail={"email": usuario.email, "rol": usuario.role.name},
    )
    return TemporaryPassword(
        user_id=usuario.id, email=usuario.email, temporary_password=temporal
    )


@router.patch("/{user_id}/role", response_model=UserOut,
              dependencies=[Gestionar, Csrf], summary="Cambiar rol")
async def change_role(
    user_id: uuid.UUID,
    payload: UserRoleUpdate,
    request: Request,
    session: SessionDep,
    actor: VerifiedUser,
    service: ServiceDep,
) -> UserOut:
    usuario = await service.change_role(user_id, payload.role_id, actor=actor)
    await audit_service.record(
        session,
        action="user.role_changed",
        request=request,
        user_id=actor.id,
        user_email=actor.email,
        entity_type="user",
        entity_id=str(user_id),
        detail={"rol_nuevo": usuario.role.name},
    )
    return UserOut.from_domain(usuario, ahora=UserService.ahora())


@router.patch("/{user_id}/active", response_model=UserOut,
              dependencies=[Gestionar, Csrf], summary="Activar o desactivar")
async def set_active(
    user_id: uuid.UUID,
    payload: UserActiveUpdate,
    request: Request,
    session: SessionDep,
    actor: VerifiedUser,
    service: ServiceDep,
) -> UserOut:
    usuario = await service.set_active(user_id, payload.is_active, actor=actor)
    await audit_service.record(
        session,
        action="user.activated" if payload.is_active else "user.deactivated",
        request=request,
        user_id=actor.id,
        user_email=actor.email,
        entity_type="user",
        entity_id=str(user_id),
    )
    return UserOut.from_domain(usuario, ahora=UserService.ahora())


@router.post("/{user_id}/reset-password", response_model=TemporaryPassword,
             dependencies=[Gestionar, Csrf], summary="Restablecer credenciales")
async def reset_password(
    user_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    actor: VerifiedUser,
    service: ServiceDep,
) -> TemporaryPassword:
    usuario, temporal = await service.reset_credentials(user_id)
    await audit_service.record(
        session,
        action="user.password_reset",
        request=request,
        user_id=actor.id,
        user_email=actor.email,
        entity_type="user",
        entity_id=str(user_id),
    )
    return TemporaryPassword(
        user_id=usuario.id, email=usuario.email, temporary_password=temporal
    )
