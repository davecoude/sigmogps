"""Gateway de Wialon (INT-01 a INT-06).

Encapsula por completo la API remota: fuera de este paquete nadie conoce
`ajax.html`, los flags ni los códigos de error. El resto del sistema recibe
diccionarios ya validados y excepciones de dominio.
"""

import asyncio
import json
import time
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.domain.exceptions import ExternalServiceError
from app.infrastructure.wialon.errors import WialonSessionExpired, traducir

logger = get_logger(__name__)

# Servicios que solo leen: se pueden cachear y reintentar sin efectos.
SERVICIOS_DE_LECTURA = frozenset(
    {
        "core/search_items",
        "core/search_item",
        "resource/get_unit_drivers",
        "resource/get_driver_bindings",
        "resource/get_tag_bindings",
        "messages/load_interval",
    }
)


def _normalizar_url(host: str) -> str:
    """Acepta "hst-api.wialon.com", "https://hst-api.wialon.com" o la URL
    completa con /wialon/ajax.html, que es como suele llegar por correo."""
    valor = host.strip().rstrip("/")
    for prefijo in ("https://", "http://"):
        if valor.lower().startswith(prefijo):
            valor = valor[len(prefijo) :]
            break
    nombre = valor.split("/", 1)[0]
    if not nombre:
        raise ExternalServiceError("WIALON_HOST no es un host válido")
    return f"https://{nombre}/wialon/ajax.html"


class _CacheTTL:
    """Caché en memoria con expiración corta (INT-06).

    Suficiente para un proceso: el objetivo es absorber el polling del mapa,
    no compartir estado entre instancias.
    """

    def __init__(self, ttl_segundos: int) -> None:
        self._ttl = ttl_segundos
        self._datos: dict[str, tuple[float, Any]] = {}

    def get(self, clave: str) -> Any | None:
        entrada = self._datos.get(clave)
        if entrada is None:
            return None
        guardado_en, valor = entrada
        if time.monotonic() - guardado_en > self._ttl:
            del self._datos[clave]
            return None
        return valor

    def set(self, clave: str, valor: Any) -> None:
        self._datos[clave] = (time.monotonic(), valor)

    def clear(self) -> None:
        self._datos.clear()


class WialonClient:
    """Mantiene viva la sesión y traduce errores. No interpreta datos de negocio."""

    def __init__(
        self,
        *,
        host: str,
        token: str,
        timeout: float = 10.0,
        cache_ttl: int = 15,
        max_reintentos: int = 2,
    ) -> None:
        self._base_url = _normalizar_url(host)
        self._token = token
        self._max_reintentos = max_reintentos
        self._sid: str | None = None
        # Serializa la renovación: si diez peticiones ven la sesión muerta a la
        # vez, solo una hace login y las demás esperan ese resultado.
        self._lock = asyncio.Lock()
        self._cache = _CacheTTL(cache_ttl)
        self._http = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=5.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            headers={"User-Agent": "sigmoGPS/0.1"},
        )

    # ─────────────────────────── ciclo de vida ───────────────────────────

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> "WialonClient":
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    # ─────────────────────────────── sesión ──────────────────────────────

    async def _login(self) -> str:
        """Abre sesión. El token viaja en el cuerpo, nunca en la URL (SEG-02)."""
        datos = await self._post(
            "token/login", {"token": self._token}, sid=None, servicio_log="token/login"
        )
        sid = datos.get("eid")
        if not sid:
            raise ExternalServiceError("Wialon no devolvió identificador de sesión")
        logger.info("wialon_sesion_abierta", usuario=datos.get("user", {}).get("nm"))
        return sid

    async def _asegurar_sesion(self, *, forzar: bool = False) -> str:
        async with self._lock:
            if forzar or self._sid is None:
                if forzar:
                    self._cache.clear()
                self._sid = await self._login()
            return self._sid

    # ──────────────────────────── transporte ─────────────────────────────

    async def _post(
        self, servicio: str, params: dict[str, Any], *, sid: str | None, servicio_log: str
    ) -> dict[str, Any]:
        """Un intento. POST y no GET: evita el límite de longitud de la URL y
        mantiene el token fuera de los logs de acceso del proxy."""
        cuerpo = {"svc": servicio, "params": json.dumps(params, separators=(",", ":"))}
        if sid:
            cuerpo["sid"] = sid

        try:
            respuesta = await self._http.post(self._base_url, data=cuerpo)
            respuesta.raise_for_status()
        except httpx.TimeoutException as exc:
            raise ExternalServiceError(
                "Wialon no respondió a tiempo", servicio=servicio_log
            ) from exc
        except httpx.HTTPError as exc:
            raise ExternalServiceError(
                "No se pudo contactar a Wialon", servicio=servicio_log
            ) from exc

        try:
            datos = respuesta.json()
        except ValueError as exc:
            raise ExternalServiceError(
                "Wialon devolvió una respuesta ilegible", servicio=servicio_log
            ) from exc

        # Wialon responde 200 incluso en error: el fallo viene en el cuerpo.
        if isinstance(datos, dict) and "error" in datos and datos["error"] != 0:
            raise traducir(int(datos["error"]), servicio=servicio_log)

        return datos

    # ───────────────────────────── API pública ───────────────────────────

    async def call(
        self, servicio: str, params: dict[str, Any] | None = None, *, usar_cache: bool = True
    ) -> Any:
        """Ejecuta un servicio renovando la sesión de forma transparente (INT-01)."""
        params = params or {}
        es_lectura = servicio in SERVICIOS_DE_LECTURA

        clave_cache = ""
        if es_lectura and usar_cache:
            clave_cache = f"{servicio}:{json.dumps(params, sort_keys=True, separators=(',', ':'))}"
            en_cache = self._cache.get(clave_cache)
            if en_cache is not None:
                return en_cache

        ultimo_error: Exception | None = None

        for intento in range(self._max_reintentos + 1):
            sid = await self._asegurar_sesion()
            try:
                datos = await self._post(servicio, params, sid=sid, servicio_log=servicio)
                if clave_cache:
                    self._cache.set(clave_cache, datos)
                return datos

            except WialonSessionExpired as exc:
                # El usuario final no se entera: se renueva y se repite.
                ultimo_error = exc
                logger.info("wialon_sesion_renovando", servicio=servicio, intento=intento)
                await self._asegurar_sesion(forzar=True)

            except ExternalServiceError as exc:
                # Un error de red o de disponibilidad sí se reintenta;
                # uno de negocio (validación, permisos) no, y sale aquí.
                ultimo_error = exc
                if intento == self._max_reintentos or not es_lectura:
                    raise
                espera = 0.4 * (2**intento)
                logger.warning(
                    "wialon_reintento", servicio=servicio, intento=intento, espera=espera
                )
                await asyncio.sleep(espera)

        raise ultimo_error or ExternalServiceError("Wialon no disponible", servicio=servicio)

    async def ping(self) -> bool:
        """Para el endpoint de salud: confirma que la sesión responde."""
        try:
            await self.call("core/get_hw_types", {}, usar_cache=False)
            return True
        except Exception:
            return False


_cliente: WialonClient | None = None


def get_wialon_client() -> WialonClient:
    """Una sola instancia por proceso: comparte sesión, caché y pool de conexiones."""
    global _cliente
    if _cliente is None:
        settings = get_settings()
        if not settings.wialon_host or not settings.wialon_token.get_secret_value():
            raise ExternalServiceError("Wialon no está configurado")
        _cliente = WialonClient(
            host=settings.wialon_host,
            token=settings.wialon_token.get_secret_value(),
            timeout=settings.wialon_timeout_seconds,
            cache_ttl=settings.wialon_cache_ttl_seconds,
        )
    return _cliente


async def close_wialon_client() -> None:
    global _cliente
    if _cliente is not None:
        await _cliente.aclose()
        _cliente = None
