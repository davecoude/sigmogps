"""Autorización (TST-02, SEG-01).

Estas pruebas verifican lo contrario de lo habitual: no que un rol **pueda**
hacer su trabajo, sino que **no pueda** hacer lo que no le toca. Ocultar un
botón en la interfaz no es seguridad; la denegación vive en el backend.

Las dos primeras recorren toda la superficie del API en vez de revisar
endpoint por endpoint. Esa es la diferencia entre una prueba que pasa hoy y
una que sigue protegiendo cuando alguien agregue un endpoint en seis meses:
si lo agrega sin permiso o sin CSRF, estas fallan solas.
"""

import pytest

from app.api.deps import require_permission, user_permissions, verify_csrf
from app.api.v1.router import api_router
from app.domain.exceptions import PermissionDeniedError
from app.domain.permissions import ROLE_PERMISSIONS, Permission, RoleName

# Rutas que no exigen permiso, con la razón por la que no lo exigen.
SIN_PERMISO_A_PROPOSITO = {
    "/health": "sonda de disponibilidad, sin datos",
    "/auth/login": "es el endpoint que crea la sesión",
    "/auth/refresh": "se autentica con la cookie de renovación",
    "/auth/logout": "cerrar sesión no puede exigir permisos",
    "/auth/me": "cualquier usuario autenticado consulta lo suyo",
    "/auth/change-password": "RF-06: se usa antes de poder hacer nada más",
}


def _recorrer(router, prefijo: str = ""):
    """Aplana el árbol de routers.

    FastAPI no copia las rutas al incluir un router: deja un envoltorio que
    las resuelve en el momento de la petición. Hay que bajar por
    `original_router` para llegar a las `APIRoute` reales.
    """
    for entrada in router.routes:
        interno = getattr(entrada, "original_router", None)
        if interno is not None:
            contexto = getattr(entrada, "include_context", None)
            propio = getattr(contexto, "prefix", "") or ""
            yield from _recorrer(interno, prefijo + propio)
        elif hasattr(entrada, "methods"):
            yield prefijo + entrada.path, entrada


def _rutas():
    """Todas las rutas del API con sus dependencias declaradas."""
    for path, ruta in _recorrer(api_router):
        for metodo in sorted(ruta.methods or []):
            if metodo in ("HEAD", "OPTIONS"):
                continue
            yield metodo, path, ruta


def _permisos_exigidos(ruta) -> tuple[Permission, ...]:
    exigidos: list[Permission] = []
    for dep in ruta.dependencies:
        requeridos = getattr(dep.dependency, "permisos_requeridos", None)
        if requeridos:
            exigidos.extend(requeridos)
    return tuple(exigidos)


def _exige_csrf(ruta) -> bool:
    return any(dep.dependency is verify_csrf for dep in ruta.dependencies)


# ───────────────────────── barridos de superficie ─────────────────────────


def test_el_barrido_encuentra_las_rutas() -> None:
    """Guarda contra una prueba que pasa sin probar nada.

    Si `_rutas()` dejara de encontrar rutas --porque FastAPI cambie cómo
    representa los routers incluidos-- los dos barridos de abajo pasarían
    vacíos y dejarían de proteger en silencio. Esta prueba lo impide.
    """
    rutas = list(_rutas())
    assert len(rutas) >= 25, f"El barrido solo encontró {len(rutas)} rutas"

    paths = {p for _, p, _ in rutas}
    # Un ancla por módulo: si un prefijo se arma mal, esto lo delata.
    for esperada in (
        "/health",
        "/auth/login",
        "/vehicles",
        "/vehicles/{vehicle_id}/custom-fields",
        "/drivers/{driver_id}/bind",
        "/passengers/{passenger_id}/assign",
        "/users/{user_id}/role",
        "/audit",
        "/exports/vehicles.csv",
    ):
        assert esperada in paths, f"El barrido no encontró {esperada}"


def test_ninguna_ruta_queda_sin_permiso() -> None:
    """Denegación por defecto: si no está en la lista de excepciones, exige permiso."""
    descubiertas = []
    for metodo, path, ruta in _rutas():
        if path in SIN_PERMISO_A_PROPOSITO:
            continue
        if not _permisos_exigidos(ruta):
            descubiertas.append(f"{metodo} {path}")

    assert not descubiertas, (
        "Rutas sin require_permission. Si alguna debe ser pública, declárala en "
        f"SIN_PERMISO_A_PROPOSITO con su razón: {descubiertas}"
    )


def test_toda_escritura_exige_csrf() -> None:
    """SEG-11: POST, PUT, PATCH y DELETE verifican el doble envío."""
    descubiertas = []
    for metodo, path, ruta in _rutas():
        if metodo == "GET":
            continue
        if path in SIN_PERMISO_A_PROPOSITO:
            continue  # login y logout manejan sus propias cookies
        if not _exige_csrf(ruta):
            descubiertas.append(f"{metodo} {path}")

    assert not descubiertas, f"Escrituras sin verify_csrf: {descubiertas}"


def test_las_excepciones_siguen_existiendo() -> None:
    """Si una ruta exenta se renombra, la lista deja de proteger y hay que saberlo."""
    existentes = {path for _, path, _ in _rutas()}
    fantasmas = set(SIN_PERMISO_A_PROPOSITO) - existentes
    assert not fantasmas, f"Excepciones que ya no corresponden a ninguna ruta: {fantasmas}"


# ───────────────────────── matriz de roles ─────────────────────────

ESCRITURAS = {
    Permission.VEHICLES_WRITE,
    Permission.DRIVERS_WRITE,
    Permission.PASSENGERS_WRITE,
    Permission.BINDINGS_WRITE,
    Permission.USERS_MANAGE,
}


def test_visualizador_no_puede_escribir_nada() -> None:
    concedidos = ROLE_PERMISSIONS[RoleName.VIEWER]
    assert not (concedidos & ESCRITURAS)
    assert Permission.EXPORT_CSV not in concedidos
    assert Permission.AUDIT_READ not in concedidos


def test_operador_no_gestiona_usuarios_ni_ve_auditoria() -> None:
    """Opera la flota, no el sistema. Es la separación que pide el enunciado."""
    concedidos = ROLE_PERMISSIONS[RoleName.OPERATOR]
    assert Permission.USERS_MANAGE not in concedidos
    assert Permission.AUDIT_READ not in concedidos
    # Pero sí hace su trabajo.
    assert Permission.DRIVERS_WRITE in concedidos
    assert Permission.BINDINGS_WRITE in concedidos
    assert Permission.EXPORT_CSV in concedidos


def test_admin_tiene_todo_el_catalogo() -> None:
    assert ROLE_PERMISSIONS[RoleName.ADMIN] == frozenset(Permission)


def test_todo_permiso_del_catalogo_tiene_descripcion() -> None:
    """El catálogo es la fuente de verdad; un permiso sin descripción es un olvido."""
    from app.domain.permissions import PERMISSION_DESCRIPTIONS

    faltantes = [p for p in Permission if p not in PERMISSION_DESCRIPTIONS]
    assert not faltantes, f"Permisos sin descripción: {faltantes}"


def test_cada_permiso_lo_usa_alguna_ruta() -> None:
    """Un permiso que nadie exige es letra muerta en la matriz de roles."""
    usados: set[Permission] = set()
    for _, _, ruta in _rutas():
        usados.update(_permisos_exigidos(ruta))

    # HISTORY_READ cubre RF-24, declarado fuera de alcance en el README.
    esperados = set(Permission) - {Permission.HISTORY_READ}
    sin_usar = esperados - usados
    assert not sin_usar, f"Permisos declarados que ninguna ruta exige: {sin_usar}"


# ───────────────────────── el guardia en sí ─────────────────────────


class RolFalso:
    def __init__(self, nombre: str, permisos: frozenset[Permission]) -> None:
        self.name = nombre
        self.permissions = [type("P", (), {"code": p.value})() for p in permisos]


class UsuarioFalso:
    def __init__(self, rol: RoleName) -> None:
        self.role = RolFalso(rol.value, ROLE_PERMISSIONS[rol])


@pytest.mark.parametrize(
    ("rol", "permiso", "permitido"),
    [
        (RoleName.ADMIN, Permission.USERS_MANAGE, True),
        (RoleName.ADMIN, Permission.AUDIT_READ, True),
        (RoleName.OPERATOR, Permission.DRIVERS_WRITE, True),
        (RoleName.OPERATOR, Permission.USERS_MANAGE, False),
        (RoleName.OPERATOR, Permission.AUDIT_READ, False),
        (RoleName.VIEWER, Permission.VEHICLES_READ, True),
        (RoleName.VIEWER, Permission.DRIVERS_WRITE, False),
        (RoleName.VIEWER, Permission.BINDINGS_WRITE, False),
        (RoleName.VIEWER, Permission.EXPORT_CSV, False),
        (RoleName.VIEWER, Permission.USERS_MANAGE, False),
    ],
)
async def test_el_guardia_concede_y_deniega(
    rol: RoleName, permiso: Permission, permitido: bool
) -> None:
    checker = require_permission(permiso)
    usuario = UsuarioFalso(rol)

    if permitido:
        assert await checker(usuario) is usuario
    else:
        with pytest.raises(PermissionDeniedError) as exc:
            await checker(usuario)
        assert permiso.value in exc.value.context["permisos_faltantes"]


async def test_exige_todos_los_permisos_no_solo_uno() -> None:
    """`require_permission(a, b)` es una conjunción, no una disyunción."""
    checker = require_permission(Permission.VEHICLES_READ, Permission.USERS_MANAGE)

    with pytest.raises(PermissionDeniedError):
        await checker(UsuarioFalso(RoleName.VIEWER))

    assert await checker(UsuarioFalso(RoleName.ADMIN)) is not None


def test_user_permissions_lee_del_rol() -> None:
    usuario = UsuarioFalso(RoleName.VIEWER)
    assert user_permissions(usuario) == {
        p.value for p in ROLE_PERMISSIONS[RoleName.VIEWER]
    }
