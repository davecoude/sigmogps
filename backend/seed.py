"""Comando de siembra: python seed.py"""

from app.core.logging import configurar_logging
from app.core.runtime import run_async
from app.infrastructure.db.seed import run_seed
from app.infrastructure.db.session import get_session_factory


async def main() -> None:
    async with get_session_factory()() as session:
        await run_seed(session)


if __name__ == "__main__":
    configurar_logging(nivel="INFO", salida_json=False)
    run_async(main())
