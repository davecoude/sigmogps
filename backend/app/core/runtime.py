"""Ejecutar corrutinas desde scripts, con el parche de Windows en un solo lugar."""

import asyncio
import sys
from collections.abc import Coroutine
from typing import Any, TypeVar

T = TypeVar("T")


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """psycopg no soporta ProactorEventLoop, predeterminado en Windows."""
    if sys.platform == "win32":
        return asyncio.run(coro, loop_factory=asyncio.SelectorEventLoop)
    return asyncio.run(coro)
