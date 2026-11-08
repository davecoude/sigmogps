"""Paginación compartida por los servicios (ARQ-04)."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Page[T]:
    items: list[T]
    total: int
    page: int
    page_size: int

    @property
    def pages(self) -> int:
        return max(1, -(-self.total // self.page_size))


def paginar[T](items: list[T], *, page: int, page_size: int) -> Page[T]:
    inicio = (page - 1) * page_size
    return Page(
        items=items[inicio : inicio + page_size],
        total=len(items),
        page=page,
        page_size=page_size,
    )
