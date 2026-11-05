"""Arranque para desarrollo local.

Windows usa ProactorEventLoop por defecto y psycopg no funciona sobre él.
La política se fija a nivel de módulo (no dentro del guard) para que el
proceso hijo del recargador también la herede.

En producción Render ejecuta uvicorn directamente: Linux no necesita esto.
"""

import asyncio
import sys
import warnings

if sys.platform == "win32":
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn  # noqa: E402

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
