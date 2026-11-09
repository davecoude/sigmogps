"""Configuración por variables de entorno (ARQ-05)."""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Aplicación
    app_name: str = "sigmoGPS API"
    app_env: Literal["development", "production"] = "development"
    app_debug: bool = False
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"

    # Base de datos
    database_url: str = ""

    # Sesión
    secret_key: SecretStr = SecretStr("")
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 7
    cookie_secure: bool = True
    cookie_samesite: Literal["lax", "strict", "none"] = "none"
    cors_allowed_origins: str = "http://localhost:3000"

    # Admin inicial (RF-07)
    admin_email: str = ""
    admin_password: SecretStr = SecretStr("")
    # Con true, el seed reescribe la clave del Admin aunque ya exista.
    # Se usa una vez y se vuelve a poner en false.
    admin_password_force: bool = False

    # Wialon
    wialon_host: str = ""
    wialon_token: SecretStr = SecretStr("")
    wialon_timeout_seconds: float = 10.0
    wialon_cache_ttl_seconds: int = 15
    # Tras una escritura, Wialon tarda ~2 s en propagar el cambio.
    # Durante este lapso las lecturas no usan ni llenan el caché, para
    # no guardar un dato obsoleto por todo el TTL.
    wialon_write_quarantine_seconds: float = 6.0
    wialon_resource_id: int = 27668776

    # Umbrales del estado derivado (sección 4.4)
    vehicle_stale_minutes: int = 10
    vehicle_moving_min_kmh: float = 3.0

    # Login (SEG-07)
    login_max_attempts: int = 5
    login_lockout_minutes: int = 15

    # Limitador de peticiones por IP (SEG-06). Amortigua el volumen; el control
    # principal contra fuerza bruta sigue siendo el bloqueo por usuario.
    #
    # Los umbrales son holgados a propósito. La interfaz llega al API a través
    # del proxy de Vercel, y si ese salto no propaga la IP del cliente hasta
    # Render, todas las peticiones caen en un mismo cubo. Con umbrales
    # estrechos eso convertiría el limitador en una caída de servicio para
    # usuarios legítimos, que es peor que el abuso que previene.
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 600
    rate_limit_login_per_minute: int = 40

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def docs_url(self) -> str | None:
        """Swagger deshabilitado en producción (SEG-05)."""
        return None if self.is_production else "/docs"

    @property
    def openapi_url(self) -> str | None:
        return None if self.is_production else "/openapi.json"

    def assert_production_ready(self) -> None:
        """Falla al arrancar, no en la primera petición."""
        if not self.is_production:
            return
        faltantes = [
            nombre
            for nombre, valor in (
                ("SECRET_KEY", self.secret_key.get_secret_value()),
                ("DATABASE_URL", self.database_url),
                ("WIALON_HOST", self.wialon_host),
                ("WIALON_TOKEN", self.wialon_token.get_secret_value()),
            )
            if not valor
        ]
        if faltantes:
            raise RuntimeError(
                f"Variables obligatorias sin definir en producción: {', '.join(faltantes)}"
            )
        if self.app_debug:
            raise RuntimeError("APP_DEBUG debe ser false en producción")


@lru_cache
def get_settings() -> Settings:
    return Settings()
