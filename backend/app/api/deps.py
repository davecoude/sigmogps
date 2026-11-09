"""Dependencias compartidas: sesión, usuario actual y permisos.

`require_permission` es el único punto donde se decide el acceso. Deniega por
defecto: un endpoint sin la dependencia no queda abierto, queda sin montar.
"""

import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import Cookie, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tokens import decode_token
from app.domain.exceptions import AuthenticationError, PermissionDeniedError
from app.domain.permissions import Permission
from app.infrastructure.db.models import User
from app.infrastructure.db.session import get_session
from app.services import auth_service

ACCESS_COOKIE = "sigmogps_access"
REFRESH_COOKIE = "sigmogps_refresh"
CSRF_COOKIE = "sigmogps_csrf"
CSRF_HEADER = "X-CSRF-Token"

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    session: SessionDep,
    access_token: Annotated[str | None, Cookie(alias=ACCESS_COOKIE)] = None,
) -> User:
    if not access_token:
        raise AuthenticationError("No autenticado.")
    payload = decode_token(access_token, expected_type="access")
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise AuthenticationError("Credenciales inválidas.") from exc
    return await auth_service.get_active_user(session, user_id)


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_verified_user(user: CurrentUser) -> User:
    """Bloquea toda la app hasta que el usuario cambie su contraseña inicial (RF-06)."""
    if user.must_change_password:
        raise PermissionDeniedError("Debes cambiar tu contraseña antes de continuar.")
    return user


VerifiedUser = Annotated[User, Depends(get_verified_user)]


def user_permissions(user: User) -> set[str]:
    return {p.code for p in user.role.permissions}


def require_permission(*required: Permission) -> Callable:
    """Exige todos los permisos indicados. Se aplica en el backend, siempre."""

    async def _checker(user: VerifiedUser) -> User:
        concedidos = user_permissions(user)
        faltantes = [p.value for p in required if p.value not in concedidos]
        if faltantes:
            raise PermissionDeniedError(
                "No tienes permiso para realizar esta acción.",
                permisos_faltantes=faltantes,
                rol=user.role.name,
            )
        return user

    # El requisito queda declarado en el propio objeto, no escondido en el
    # cierre. Así `tests/test_authorization.py` puede recorrer todas las rutas
    # y demostrar que ninguna quedó sin permiso, en vez de confiar en que
    # alguien se acuerde de revisarlo endpoint por endpoint.
    _checker.permisos_requeridos = required  # type: ignore[attr-defined]
    return _checker


def verify_csrf(request: Request) -> None:
    """Doble envío: la cookie debe coincidir con la cabecera (SEG-11)."""
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    cookie = request.cookies.get(CSRF_COOKIE)
    header = request.headers.get(CSRF_HEADER)
    if not cookie or not header or cookie != header:
        raise PermissionDeniedError("Token CSRF ausente o inválido.")
