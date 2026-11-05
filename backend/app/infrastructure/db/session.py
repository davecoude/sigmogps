"""Motor y sesión asíncrona. Unidad de trabajo por petición."""

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    """Perezoso: importar este módulo no debe exigir DATABASE_URL."""
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL no está definida")
    return create_async_engine(
        settings.database_url,
        echo=settings.app_debug,
        pool_pre_ping=True,  # Neon cierra conexiones ociosas
        pool_size=5,
        max_overflow=5,
        pool_recycle=300,
    )


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Dependencia de FastAPI: confirma al terminar bien, revierte al fallar."""
    async with get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
