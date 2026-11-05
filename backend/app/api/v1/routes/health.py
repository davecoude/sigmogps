"""Endpoint de salud (ARQ-07, DEP-04)."""

from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import Settings, get_settings

router = APIRouter(tags=["sistema"])


class HealthResponse(BaseModel):
    status: str
    app: str
    env: str
    version: str
    timestamp: datetime


@router.get("/health", response_model=HealthResponse, summary="Estado del servicio")
async def health() -> HealthResponse:
    """El frontend lo consulta para detectar el arranque en frío de Render."""
    settings: Settings = get_settings()
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        env=settings.app_env,
        version="0.1.0",
        timestamp=datetime.now(UTC),
    )
