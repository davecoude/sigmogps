"""Casos de uso de pasajeros (RF-08, RF-09, RF-27, RF-28).

En Wialon los pasajeros son *tags*. La documentación de `resource/update_tag`
advierte de forma explícita: **si se omite `jp`, los campos personalizados se
borran**. No es un efecto secundario sutil, es el comportamiento documentado.

Por eso toda escritura sigue el patrón leer-mezclar-escribir: se lee el tag
completo, se mezcla lo que cambia y se reenvía entero. Editar el nombre de un
pasajero nunca debe costarle su cédula.
"""

from dataclasses import dataclass

from app.core.logging import get_logger
from app.domain.exceptions import ConflictError, NotFoundError, ValidationError
from app.domain.models import Passenger
from app.domain.pagination import Page, paginar
from app.infrastructure.wialon.mappers import map_passenger
from app.infrastructure.wialon.repository import WialonFleetRepository

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class PassengerInput:
    name: str
    code: str | None = None
    # None significa «conserva los que ya tiene»; un dict los reemplaza.
    custom_fields: dict[str, str] | None = None


class PassengerService:
    def __init__(self, repo: WialonFleetRepository, *, resource_id: int) -> None:
        self._repo = repo
        self._resource_id = resource_id

    # ───────────────────────── lectura ─────────────────────────

    async def list_passengers(self, *, search: str | None = None) -> list[Passenger]:
        """Lista completa. Para la interfaz usa `list_page`."""
        crudos = await self._repo.list_tags(self._resource_id)
        vinculos = await self._bindings_seguros()

        pasajeros: list[Passenger] = []
        for bruto in crudos:
            p = map_passenger(bruto, resource_id=self._resource_id)
            pasajeros.append(
                Passenger(
                    id=p.id,
                    resource_id=p.resource_id,
                    name=p.name,
                    code=p.code,
                    phone=p.phone,
                    description=p.description,
                    custom_fields=p.custom_fields,
                    bound_unit_id=vinculos.get(p.id),
                )
            )

        if search:
            aguja = search.strip().lower()
            pasajeros = [
                p
                for p in pasajeros
                if aguja in p.name.lower()
                or (p.code and aguja in p.code.lower())
                or any(aguja in v.lower() for v in p.custom_fields.values())
            ]

        pasajeros.sort(key=lambda p: p.name.lower())
        return pasajeros

    async def list_page(
        self, *, search: str | None = None, page: int = 1, page_size: int = 25
    ) -> Page[Passenger]:
        """Wialon entrega los tags del recurso completos, sin paginar, y el
        filtro por campo personalizado no existe de su lado. Por eso se pagina
        aquí, sobre la lista ya traída y absorbida por el caché."""
        return paginar(
            await self.list_passengers(search=search), page=page, page_size=page_size
        )

    async def _bindings_seguros(self) -> dict[int, int]:
        """Un fallo leyendo vínculos no debe tumbar el listado completo."""
        try:
            return await self._repo.tag_bindings(self._resource_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("wialon_tag_bindings_fallo", error=str(exc))
            return {}

    async def get_passenger(self, passenger_id: int) -> Passenger:
        bruto = await self._repo.get_tag(self._resource_id, passenger_id)
        if bruto is None:
            raise NotFoundError("El pasajero no existe.")
        p = map_passenger(bruto, resource_id=self._resource_id)
        vinculos = await self._bindings_seguros()
        return Passenger(
            id=p.id,
            resource_id=p.resource_id,
            name=p.name,
            code=p.code,
            phone=p.phone,
            description=p.description,
            custom_fields=p.custom_fields,
            bound_unit_id=vinculos.get(p.id),
        )

    async def passengers_of_unit(self, unit_id: int) -> list[Passenger]:
        """Pasajeros asignados a un vehículo (RF-09)."""
        vinculos = await self._bindings_seguros()
        ids = {t for t, u in vinculos.items() if u == unit_id}
        if not ids:
            return []
        return [p for p in await self.list_passengers() if p.id in ids]

    # ───────────────────────── escritura ─────────────────────────

    def _validar(self, datos: PassengerInput) -> None:
        if not datos.name or not datos.name.strip():
            raise ValidationError("El nombre es obligatorio.")
        if len(datos.name.strip()) > 120:
            raise ValidationError("El nombre no puede superar los 120 caracteres.")
        for clave, valor in (datos.custom_fields or {}).items():
            if not clave.strip():
                raise ValidationError("Un campo personalizado no puede tener nombre vacío.")
            if len(clave) > 64 or len(valor) > 255:
                raise ValidationError(f"El campo «{clave}» excede el largo permitido.")

    async def _codigo_duplicado(self, codigo: str, *, excepto: int | None = None) -> bool:
        if not codigo.strip():
            return False
        objetivo = codigo.strip().lower()
        for p in await self.list_passengers():
            if p.id != excepto and p.code and p.code.lower() == objetivo:
                return True
        return False

    async def create_passenger(self, datos: PassengerInput) -> Passenger:
        self._validar(datos)
        if datos.code and await self._codigo_duplicado(datos.code):
            raise ConflictError(f"Ya existe un pasajero con el código {datos.code}.")

        guardado = await self._repo.save_tag(
            self._resource_id,
            {
                "id": 0,
                "callMode": "create",
                "n": datos.name.strip(),
                "c": (datos.code or "").strip(),
                "jp": datos.custom_fields or {},
            },
        )
        return map_passenger(guardado, resource_id=self._resource_id)

    async def update_passenger(self, passenger_id: int, datos: PassengerInput) -> Passenger:
        self._validar(datos)

        # Leer. Sin esto se pierden los campos que el formulario no envía.
        actual = await self._repo.get_tag(self._resource_id, passenger_id)
        if actual is None:
            raise NotFoundError("El pasajero no existe.")

        if datos.code and await self._codigo_duplicado(datos.code, excepto=passenger_id):
            raise ConflictError(f"Ya existe un pasajero con el código {datos.code}.")

        # Mezclar: si no vienen campos personalizados, se conservan los actuales.
        campos = (
            datos.custom_fields
            if datos.custom_fields is not None
            else {k: str(v) for k, v in (actual.get("jp") or {}).items()}
        )

        guardado = await self._repo.save_tag(
            self._resource_id,
            {
                "id": passenger_id,
                "callMode": "update",
                "n": datos.name.strip(),
                "c": (datos.code or "").strip(),
                # `f` y `art` se reenvían tal cual: tampoco hay que perderlos.
                "f": int(actual.get("f") or 0),
                "art": int(actual.get("art") or 36000),
                "jp": campos,
            },
        )
        return map_passenger(guardado, resource_id=self._resource_id)

    async def replace_custom_fields(
        self, passenger_id: int, campos: dict[str, str]
    ) -> Passenger:
        """Crear, editar y eliminar campos personalizados (RF-27).

        Recibe el conjunto completo deseado: lo que no venga, se elimina. Es
        intencional y es lo que permite borrar un campo desde la interfaz.
        """
        actual = await self._repo.get_tag(self._resource_id, passenger_id)
        if actual is None:
            raise NotFoundError("El pasajero no existe.")

        self._validar(PassengerInput(name=str(actual.get("n") or "x"), custom_fields=campos))

        guardado = await self._repo.save_tag(
            self._resource_id,
            {
                "id": passenger_id,
                "callMode": "update",
                # El resto del tag se reenvía sin tocar.
                "n": str(actual.get("n") or ""),
                "c": str(actual.get("c") or ""),
                "f": int(actual.get("f") or 0),
                "art": int(actual.get("art") or 36000),
                "jp": campos,
            },
        )
        return map_passenger(guardado, resource_id=self._resource_id)

    async def delete_passenger(self, passenger_id: int) -> None:
        if await self._repo.get_tag(self._resource_id, passenger_id) is None:
            raise NotFoundError("El pasajero no existe.")
        await self._repo.delete_tag(self._resource_id, passenger_id)

    # ───────────────────────── asignación ─────────────────────────

    async def assign(self, *, passenger_id: int, unit_id: int) -> None:
        actual = await self.get_passenger(passenger_id)
        if actual.bound_unit_id == unit_id:
            raise ConflictError("El pasajero ya está asignado a ese vehículo.")
        await self._repo.bind_tag(
            self._resource_id, unit_id=unit_id, tag_id=passenger_id, bind=True
        )

    async def unassign(self, *, passenger_id: int, unit_id: int) -> None:
        await self._repo.bind_tag(
            self._resource_id, unit_id=unit_id, tag_id=passenger_id, bind=False
        )
