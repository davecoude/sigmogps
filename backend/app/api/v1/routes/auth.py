"""Endpoints de sesión (RF-04, RF-06, SEG-07, SEG-11)."""

import secrets
import uuid
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, Response, status

from app.api.deps import (
    ACCESS_COOKIE,
    CSRF_COOKIE,
    REFRESH_COOKIE,
    CurrentUser,
    SessionDep,
    user_permissions,
    verify_csrf,
)
from app.api.v1.schemas.auth import ChangePasswordRequest, LoginRequest, MeResponse
from app.core.config import get_settings
from app.core.tokens import create_access_token, create_refresh_token, decode_token
from app.domain.exceptions import AuthenticationError
from app.infrastructure.db.models import User
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["autenticación"])


def _set_session_cookies(response: Response, user: User) -> None:
    settings = get_settings()
    comun = {
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
        "path": "/",
    }
    response.set_cookie(
        ACCESS_COOKIE,
        create_access_token(user.id),
        max_age=settings.access_token_ttl_minutes * 60,
        **comun,
    )
    response.set_cookie(
        REFRESH_COOKIE,
        create_refresh_token(user.id, user.token_version),
        max_age=settings.refresh_token_ttl_days * 86400,
        **comun,
    )
    # Esta sí la lee el JavaScript: es la mitad del doble envío CSRF.
    response.set_cookie(
        CSRF_COOKIE,
        secrets.token_urlsafe(32),
        httponly=False,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
        max_age=settings.refresh_token_ttl_days * 86400,
    )


def _clear_session_cookies(response: Response) -> None:
    for nombre in (ACCESS_COOKIE, REFRESH_COOKIE, CSRF_COOKIE):
        response.delete_cookie(nombre, path="/")


def _me(user: User) -> MeResponse:
    return MeResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        permissions=sorted(user_permissions(user)),
        must_change_password=user.must_change_password,
    )


@router.post("/login", response_model=MeResponse, summary="Iniciar sesión")
async def login(
    payload: LoginRequest, request: Request, response: Response, session: SessionDep
) -> MeResponse:
    user = await auth_service.authenticate(
        session, email=payload.email, password=payload.password, request=request
    )
    await session.refresh(user, ["role"])
    _set_session_cookies(response, user)
    return _me(user)


@router.post("/refresh", response_model=MeResponse, summary="Renovar la sesión")
async def refresh(
    request: Request,
    response: Response,
    session: SessionDep,
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
) -> MeResponse:
    if not refresh_token:
        raise AuthenticationError("No autenticado.")
    payload = decode_token(refresh_token, expected_type="refresh")
    user = await auth_service.get_active_user(session, uuid.UUID(payload["sub"]))

    # Rotación por versión: tras un logout o un cambio de clave, el refresh muere.
    if payload.get("ver") != user.token_version:
        _clear_session_cookies(response)
        raise AuthenticationError("La sesión fue cerrada. Inicia sesión de nuevo.")

    _set_session_cookies(response, user)
    return _me(user)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(verify_csrf)],
    summary="Cerrar sesión",
)
async def logout(
    request: Request, response: Response, session: SessionDep, user: CurrentUser
) -> None:
    await auth_service.revoke_sessions(session, user=user, request=request)
    _clear_session_cookies(response)


@router.get("/me", response_model=MeResponse, summary="Usuario y permisos efectivos")
async def me(user: CurrentUser) -> MeResponse:
    return _me(user)


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(verify_csrf)],
    summary="Cambiar contraseña",
)
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    response: Response,
    session: SessionDep,
    user: CurrentUser,
) -> None:
    await auth_service.change_password(
        session,
        user=user,
        current_password=payload.current_password,
        new_password=payload.new_password,
        request=request,
    )
    # La contraseña cambió: las cookies actuales ya no sirven.
    _clear_session_cookies(response)
