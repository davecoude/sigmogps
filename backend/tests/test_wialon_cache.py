"""Caché de lecturas de Wialon y su cuarentena tras escribir.

Regresión de un error medido: al escribir se limpiaba el caché, pero la
lectura inmediata siguiente llegaba antes de que Wialon propagara el cambio
(~2.3 s), traía el valor anterior y lo dejaba fijado durante todo el TTL.
El usuario veía su propio cambio recién 15 s después.
"""

import asyncio

import httpx
import pytest
import respx

from app.infrastructure.wialon.client import WialonClient

HOST = "wialon.test"
URL = f"https://{HOST}/wialon/ajax.html"

SPEC_UNIDADES = {
    "spec": {
        "itemsType": "avl_unit",
        "propName": "sys_name",
        "propValueMask": "*",
        "sortType": "sys_name",
    },
    "force": 1,
    "flags": 1,
    "from": 0,
    "to": 0,
}


def _responder(peticion: httpx.Request) -> httpx.Response:
    """Responde según el servicio pedido, contando cada llamada real."""
    cuerpo = peticion.content.decode()
    if "token%2Flogin" in cuerpo or "token/login" in cuerpo:
        return httpx.Response(200, json={"eid": "sesion-de-prueba", "user": {"nm": "test"}})
    return httpx.Response(200, json={"items": [], "totalItemsCount": 0})


@pytest.fixture
async def cliente():
    c = WialonClient(
        host=HOST,
        token="token-de-prueba",
        timeout=5.0,
        cache_ttl=30,
        write_quarantine=0.4,
    )
    yield c
    await c.aclose()


@respx.mock
async def test_una_lectura_repetida_usa_el_cache(cliente: WialonClient) -> None:
    ruta = respx.post(URL).mock(side_effect=_responder)

    await cliente.call("core/search_items", SPEC_UNIDADES)
    llamadas_tras_la_primera = ruta.call_count

    await cliente.call("core/search_items", SPEC_UNIDADES)

    assert ruta.call_count == llamadas_tras_la_primera, (
        "La segunda lectura idéntica debió servirse del caché"
    )


@respx.mock
async def test_una_escritura_fuerza_relectura(cliente: WialonClient) -> None:
    ruta = respx.post(URL).mock(side_effect=_responder)

    await cliente.call("core/search_items", SPEC_UNIDADES)
    antes = ruta.call_count

    await cliente.call(
        "resource/bind_unit_driver",
        {"resourceId": 1, "unitId": 2, "driverId": 3, "time": 0, "mode": 1},
        usar_cache=False,
    )
    llamadas_de_escritura = ruta.call_count - antes

    await cliente.call("core/search_items", SPEC_UNIDADES)

    assert ruta.call_count == antes + llamadas_de_escritura + 1, (
        "Tras escribir, la lectura debió ir a Wialon y no al caché"
    )


@respx.mock
async def test_la_cuarentena_impide_cachear_un_dato_obsoleto(cliente: WialonClient) -> None:
    """El corazón del error: durante la cuarentena nada se guarda en caché."""
    ruta = respx.post(URL).mock(side_effect=_responder)

    await cliente.call(
        "resource/bind_unit_driver",
        {"resourceId": 1, "unitId": 2, "driverId": 3, "time": 0, "mode": 1},
        usar_cache=False,
    )
    antes = ruta.call_count

    # Dos lecturas dentro de la ventana: ambas deben ir a la fuente.
    await cliente.call("core/search_items", SPEC_UNIDADES)
    await cliente.call("core/search_items", SPEC_UNIDADES)

    assert ruta.call_count == antes + 2, (
        "Dentro de la cuarentena ninguna lectura debe servirse ni guardarse en caché"
    )


@respx.mock
async def test_el_cache_vuelve_al_vencer_la_cuarentena(cliente: WialonClient) -> None:
    ruta = respx.post(URL).mock(side_effect=_responder)

    await cliente.call(
        "resource/bind_unit_driver",
        {"resourceId": 1, "unitId": 2, "driverId": 3, "time": 0, "mode": 1},
        usar_cache=False,
    )
    await asyncio.sleep(0.5)  # cuarentena de 0.4 s

    await cliente.call("core/search_items", SPEC_UNIDADES)
    antes = ruta.call_count

    await cliente.call("core/search_items", SPEC_UNIDADES)

    assert ruta.call_count == antes, "Pasada la cuarentena, el caché debe volver a servir"
