"""Campos personalizados de vehículo (RF-19, RF-20).

Wialon expone un campo por llamada y no tiene operación por lote. Lo que se
verifica aquí es que el servicio escriba **lo mínimo**: con quince campos y un
valor editado debe hacer una llamada, no quince. Y que no renombre los campos
del cliente, que es donde un descuido corrompe datos reales.
"""

from typing import Any

import pytest

from app.domain.exceptions import NotFoundError, ValidationError
from app.services.vehicle_service import VehicleService

ID_UNIDAD = 500
ID_RECURSO = 27668776


class ProveedorFalso:
    """Doble de prueba con estado. Registra cada llamada de escritura.

    No hereda nada: `FleetProvider` es un `Protocol`, así que basta tener los
    mismos métodos. Ese es el pago concreto de la inversión de dependencias.
    """

    def __init__(self, campos: dict[int, tuple[str, str]]) -> None:
        # id -> (nombre, valor)
        self.campos = dict(campos)
        self.siguiente_id = max(campos, default=0) + 1
        self.llamadas: list[tuple[str, Any]] = []

    # ───── lecturas ─────

    def _unidad(self) -> dict[str, Any]:
        return {
            "id": ID_UNIDAD,
            "nm": "863238077731893",
            "flds": {
                str(i): {"id": i, "n": n, "v": v} for i, (n, v) in self.campos.items()
            },
            "pos": {"y": 4.65, "x": -74.1, "s": 0, "t": 2_000_000_000},
        }

    async def list_units(self) -> list[dict[str, Any]]:
        return [self._unidad()]

    async def get_unit(self, unit_id: int) -> dict[str, Any] | None:
        return self._unidad() if unit_id == ID_UNIDAD else None

    async def list_drivers(self, resource_id: int) -> list[dict[str, Any]]:
        return []

    # ───── escrituras ─────

    async def create_unit_custom_field(
        self, unit_id: int, *, name: str, value: str
    ) -> dict[str, Any]:
        self.llamadas.append(("create", (name, value)))
        nuevo = self.siguiente_id
        self.siguiente_id += 1
        self.campos[nuevo] = (name, value)
        return {"id": nuevo, "n": name, "v": value}

    async def update_unit_custom_field(
        self, unit_id: int, *, field_id: int, name: str, value: str
    ) -> dict[str, Any]:
        self.llamadas.append(("update", (field_id, name, value)))
        self.campos[field_id] = (name, value)
        return {"id": field_id, "n": name, "v": value}

    async def delete_unit_custom_field(self, unit_id: int, field_id: int) -> None:
        self.llamadas.append(("delete", field_id))
        self.campos.pop(field_id, None)


def _servicio(proveedor: ProveedorFalso) -> VehicleService:
    servicio = VehicleService(proveedor, resource_id=ID_RECURSO)
    # La confirmación de propagación no aporta nada contra un doble en memoria,
    # que es consistente de inmediato. Se deja un sondeo mínimo.
    servicio._ESPERA_PROPAGACION = 0.2
    servicio._INTERVALO_SONDEO = 0.05
    return servicio


async def test_solo_escribe_el_campo_que_cambio() -> None:
    """Un valor editado entre varios campos es una llamada, no varias."""
    proveedor = ProveedorFalso(
        {
            1: ("PLACA", "ABC123"),
            2: ("LINEA", "Troncal"),
            3: ("COLOR", "Blanco"),
            4: ("PROPIETARIO", "GPS Control"),
        }
    )
    servicio = _servicio(proveedor)

    await servicio.replace_custom_fields(
        ID_UNIDAD,
        {
            "PLACA": "ABC123",
            "LINEA": "Alimentador",  # el único cambio
            "COLOR": "Blanco",
            "PROPIETARIO": "GPS Control",
        },
    )

    assert proveedor.llamadas == [("update", (2, "LINEA", "Alimentador"))]


async def test_crea_y_elimina_segun_el_conjunto_enviado() -> None:
    """Conjunto completo: lo que no viene, se elimina (RF-20)."""
    proveedor = ProveedorFalso({1: ("PLACA", "ABC123"), 2: ("COLORE", "Blanco")})
    servicio = _servicio(proveedor)

    await servicio.replace_custom_fields(
        ID_UNIDAD, {"PLACA": "ABC123", "CAPACIDAD": "40"}
    )

    acciones = [a for a, _ in proveedor.llamadas]
    assert acciones.count("create") == 1
    assert acciones.count("delete") == 1
    assert ("create", ("CAPACIDAD", "40")) in proveedor.llamadas
    assert ("delete", 2) in proveedor.llamadas
    assert {n for n, _ in proveedor.campos.values()} == {"PLACA", "CAPACIDAD"}


async def test_no_renombra_el_campo_del_cliente() -> None:
    """Si el nombre coincide salvo acento o caja, se actualiza el valor y nada más.

    Los datos reales de la cuenta traen LINEA y LÍNEA, COLOR y COLORE. Cambiar
    la grafía del campo al cliente sería corromper su dato, incluso si la
    nuestra parece la correcta.
    """
    proveedor = ProveedorFalso({7: ("LÍNEA", "Troncal")})
    servicio = _servicio(proveedor)

    await servicio.replace_custom_fields(ID_UNIDAD, {"linea": "Alimentador"})

    # Se escribió con el nombre original, no con el que llegó.
    assert proveedor.llamadas == [("update", (7, "LÍNEA", "Alimentador"))]
    assert proveedor.campos[7] == ("LÍNEA", "Alimentador")


async def test_sin_cambios_no_escribe_nada() -> None:
    """Idempotencia: reenviar el mismo conjunto no toca Wialon."""
    proveedor = ProveedorFalso({1: ("PLACA", "ABC123"), 2: ("COLOR", "Blanco")})
    servicio = _servicio(proveedor)

    await servicio.replace_custom_fields(
        ID_UNIDAD, {"PLACA": "ABC123", "COLOR": "Blanco"}
    )

    assert proveedor.llamadas == []


async def test_conjunto_vacio_elimina_todo() -> None:
    proveedor = ProveedorFalso({1: ("PLACA", "ABC123"), 2: ("COLOR", "Blanco")})
    servicio = _servicio(proveedor)

    await servicio.replace_custom_fields(ID_UNIDAD, {})

    assert sorted(a for a, _ in proveedor.llamadas) == ["delete", "delete"]
    assert proveedor.campos == {}


async def test_rechaza_dos_nombres_que_wialon_ve_iguales() -> None:
    """LINEA y LÍNEA son el mismo campo: aceptarlos dejaría un valor perdido."""
    proveedor = ProveedorFalso({})
    servicio = _servicio(proveedor)

    with pytest.raises(ValidationError) as exc:
        await servicio.replace_custom_fields(
            ID_UNIDAD, {"LINEA": "Troncal", "línea": "Alimentador"}
        )

    assert "mismo campo" in str(exc.value.detail)
    assert proveedor.llamadas == []


async def test_rechaza_nombre_vacio() -> None:
    proveedor = ProveedorFalso({})
    servicio = _servicio(proveedor)

    with pytest.raises(ValidationError):
        await servicio.replace_custom_fields(ID_UNIDAD, {"   ": "algo"})

    assert proveedor.llamadas == []


async def test_valida_antes_de_escribir_nada() -> None:
    """Un conjunto inválido no debe dejar escrituras a medias."""
    proveedor = ProveedorFalso({1: ("PLACA", "ABC123")})
    servicio = _servicio(proveedor)

    with pytest.raises(ValidationError):
        await servicio.replace_custom_fields(
            ID_UNIDAD,
            {"PLACA": "XYZ789", "CAPACIDAD": "x" * 300},
        )

    assert proveedor.llamadas == []
    assert proveedor.campos == {1: ("PLACA", "ABC123")}


async def test_vehiculo_inexistente() -> None:
    proveedor = ProveedorFalso({})
    servicio = _servicio(proveedor)

    with pytest.raises(NotFoundError):
        await servicio.replace_custom_fields(99999, {"PLACA": "ABC123"})
