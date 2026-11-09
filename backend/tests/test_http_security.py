"""Cabeceras de seguridad y limitador de peticiones (SEG-05, SEG-06).

Lo que se verifica aquí no es que el middleware exista, sino que proteja
también los caminos de error: un 404 y un 429 deben salir con las mismas
cabeceras que un 200. Es justo donde este tipo de middleware se suele colar.
"""

import httpx
import pytest

from app.core.config import get_settings
from app.core.http_security import CSP_API

CABECERAS_ESPERADAS = {
    "Content-Security-Policy": CSP_API,
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cache-Control": "no-store",
}


def _construir_app(monkeypatch: pytest.MonkeyPatch, **entorno: str):
    """Arma una aplicación nueva con el entorno dado.

    `get_settings` está memorizado con lru_cache, así que hay que limpiarlo
    antes y después para no contaminar otras pruebas.
    """
    for clave, valor in entorno.items():
        monkeypatch.setenv(clave, valor)
    get_settings.cache_clear()

    from app.main import create_app

    return create_app()


@pytest.fixture(autouse=True)
def _limpiar_settings():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _cliente(app) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://pruebas",
    )


async def test_cabeceras_en_respuesta_exitosa(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _construir_app(monkeypatch, RATE_LIMIT_ENABLED="false")

    async with _cliente(app) as cliente:
        r = await cliente.get("/api/v1/health")

    assert r.status_code == 200
    for cabecera, valor in CABECERAS_ESPERADAS.items():
        assert r.headers.get(cabecera) == valor, f"falta o difiere {cabecera}"


async def test_cabeceras_tambien_en_un_404(monkeypatch: pytest.MonkeyPatch) -> None:
    """Un camino de error no puede quedar sin cabeceras de seguridad."""
    app = _construir_app(monkeypatch, RATE_LIMIT_ENABLED="false")

    async with _cliente(app) as cliente:
        r = await cliente.get("/api/v1/ruta-que-no-existe")

    assert r.status_code == 404
    for cabecera, valor in CABECERAS_ESPERADAS.items():
        assert r.headers.get(cabecera) == valor, f"falta o difiere {cabecera}"


async def test_hsts_solo_en_produccion(monkeypatch: pytest.MonkeyPatch) -> None:
    """En local no hay HTTPS: fijar HSTS rompería el acceso a localhost."""
    app = _construir_app(monkeypatch, RATE_LIMIT_ENABLED="false", APP_ENV="development")

    async with _cliente(app) as cliente:
        r = await cliente.get("/api/v1/health")
    assert "Strict-Transport-Security" not in r.headers

    app_prod = _construir_app(
        monkeypatch,
        RATE_LIMIT_ENABLED="false",
        APP_ENV="production",
        APP_DEBUG="false",
        SECRET_KEY="x" * 40,
        DATABASE_URL="postgresql+psycopg://u:p@h/d",
        WIALON_HOST="wialon.test",
        WIALON_TOKEN="token-de-prueba",
    )

    async with _cliente(app_prod) as cliente:
        r = await cliente.get("/api/v1/health")

    assert r.headers.get("Strict-Transport-Security") == "max-age=31536000; includeSubDomains"


async def test_swagger_no_existe_en_produccion(monkeypatch: pytest.MonkeyPatch) -> None:
    """SEG-05: el inventario de endpoints no se publica."""
    app = _construir_app(
        monkeypatch,
        RATE_LIMIT_ENABLED="false",
        APP_ENV="production",
        APP_DEBUG="false",
        SECRET_KEY="x" * 40,
        DATABASE_URL="postgresql+psycopg://u:p@h/d",
        WIALON_HOST="wialon.test",
        WIALON_TOKEN="token-de-prueba",
    )

    async with _cliente(app) as cliente:
        assert (await cliente.get("/docs")).status_code == 404
        assert (await cliente.get("/openapi.json")).status_code == 404


async def test_limitador_responde_429_con_retry_after(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _construir_app(
        monkeypatch,
        RATE_LIMIT_ENABLED="true",
        RATE_LIMIT_PER_MINUTE="3",
        RATE_LIMIT_LOGIN_PER_MINUTE="2",
    )

    async with _cliente(app) as cliente:
        for _ in range(3):
            assert (await cliente.get("/api/v1/health")).status_code == 200

        r = await cliente.get("/api/v1/health")

    assert r.status_code == 429
    assert r.headers["Retry-After"].isdigit()
    assert r.headers["content-type"].startswith("application/problem+json")

    cuerpo = r.json()
    assert cuerpo["status"] == 429
    assert cuerpo["trace_id"]

    # La cabecera de seguridad envuelve también al rechazo del limitador.
    assert r.headers.get("X-Content-Type-Options") == "nosniff"


async def test_el_cubo_de_login_es_independiente(monkeypatch: pytest.MonkeyPatch) -> None:
    """El ingreso tiene su propio contador, más estrecho que el general.

    Se fija el límite de login en cero para que el rechazo ocurra en el
    middleware y la prueba no dependa de la base de datos: lo que se verifica
    es qué cubo decide, no qué responde el endpoint.
    """
    app = _construir_app(
        monkeypatch,
        RATE_LIMIT_ENABLED="true",
        RATE_LIMIT_PER_MINUTE="5",
        RATE_LIMIT_LOGIN_PER_MINUTE="0",
    )

    async with _cliente(app) as cliente:
        # El cubo general sigue con espacio.
        assert (await cliente.get("/api/v1/health")).status_code == 200

        # El de login está agotado por su cuenta.
        r = await cliente.post(
            "/api/v1/auth/login",
            json={"email": "nadie@ejemplo.com", "password": "Clave-Invalida-1!"},
        )
        assert r.status_code == 429

        # Y agotarlo no cerró el resto del API.
        assert (await cliente.get("/api/v1/health")).status_code == 200


def test_ventana_deslizante_cuenta_y_libera() -> None:
    """La ventana permite hasta el límite y luego informa cuánto esperar."""
    from app.core.http_security import VentanaDeslizante

    ventana = VentanaDeslizante()

    for _ in range(3):
        permitido, espera = ventana.permitir("clave", 3)
        assert permitido is True
        assert espera == 0

    permitido, espera = ventana.permitir("clave", 3)
    assert permitido is False
    assert 0 < espera <= 61

    # Otra clave no se ve afectada por la primera.
    assert ventana.permitir("otra", 3) == (True, 0)


async def test_ip_del_cliente_toma_el_primer_valor_reenviado() -> None:
    """Detrás de Render y Vercel, X-Forwarded-For trae la cadena de proxies."""
    from starlette.requests import Request

    from app.core.http_security import ip_del_cliente

    peticion = Request(
        {
            "type": "http",
            "headers": [(b"x-forwarded-for", b"203.0.113.9, 10.0.0.1, 10.0.0.2")],
            "client": ("10.0.0.2", 1234),
        }
    )
    assert ip_del_cliente(peticion) == "203.0.113.9"
