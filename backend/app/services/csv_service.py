"""Generación de CSV con protección contra inyección de fórmulas (SEG-03).

Una celda que empieza por `=`, `+`, `-` o `@` la interpretan Excel, LibreOffice
y Google Sheets como fórmula al abrir el archivo. Un pasajero llamado
`=HYPERLINK("http://malo","Haz clic")` se convierte en un enlace ejecutable en
la máquina de quien abra el export. Se neutraliza anteponiendo una comilla
simple, que los tres programas tratan como «esto es texto».
"""

import csv
import io
from collections.abc import Iterable, Sequence
from datetime import datetime
from zoneinfo import ZoneInfo

BOGOTA = ZoneInfo("America/Bogota")

# Caracteres que convierten una celda en fórmula, más los de control que
# permiten romper el formato del archivo.
PREFIJOS_PELIGROSOS = ("=", "+", "-", "@", "\t", "\r", "\n")


def sanitizar(valor: object) -> str:
    """Neutraliza una celda sin alterar su contenido legible."""
    if valor is None:
        return ""
    if isinstance(valor, datetime):
        return valor.astimezone(BOGOTA).strftime("%Y-%m-%d %H:%M:%S")
    texto = str(valor)
    if texto and texto[0] in PREFIJOS_PELIGROSOS:
        return "'" + texto
    return texto


def generar_csv(encabezados: Sequence[str], filas: Iterable[Sequence[object]]) -> bytes:
    """Devuelve el archivo con BOM UTF-8 para que Excel lea bien las tildes."""
    buffer = io.StringIO(newline="")
    escritor = csv.writer(buffer, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    escritor.writerow([sanitizar(h) for h in encabezados])
    for fila in filas:
        escritor.writerow([sanitizar(c) for c in fila])
    # Excel en español espera punto y coma y necesita el BOM para UTF-8.
    return b"\xef\xbb\xbf" + buffer.getvalue().encode("utf-8")


def nombre_archivo(base: str) -> str:
    marca = datetime.now(BOGOTA).strftime("%Y%m%d-%H%M")
    return f"{base}-{marca}.csv"
