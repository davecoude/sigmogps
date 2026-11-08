"""Hashing de contraseñas y política mínima (SEG-02, SEG-07)."""

import re
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.domain.exceptions import ValidationError

# Argon2id con la configuración principal del OWASP Password Storage Cheat
# Sheet: 19 MiB de memoria, 2 iteraciones y paralelismo 1.
#
# No son los valores por defecto de argon2-cffi (64 MiB, 3 iteraciones,
# 4 hilos), que asumen un servidor dedicado. En el plan gratuito de Render,
# con una fracción de vCPU, pedir cuatro hilos los hace competir por el mismo
# núcleo: el login tardaba 2,3 s de CPU. Las cuatro combinaciones que publica
# OWASP usan paralelismo 1 justamente por eso.
#
# El costo sigue siendo el recomendado para producción; lo que cambia es que
# está dimensionado al hardware real donde corre.
# https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
_hasher = PasswordHasher(
    memory_cost=19456,  # 19 MiB
    time_cost=2,
    parallelism=1,
)

MIN_PASSWORD_LENGTH = 12


def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Devuelve False en vez de lanzar: el llamador decide qué responder."""
    try:
        _hasher.verify(hashed, plain)
        return True
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    """True si el hash quedó con parámetros viejos tras subir el costo."""
    try:
        return _hasher.check_needs_rehash(hashed)
    except InvalidHashError:
        return True


def validate_password_policy(plain: str) -> None:
    fallos: list[str] = []
    if len(plain) < MIN_PASSWORD_LENGTH:
        fallos.append(f"al menos {MIN_PASSWORD_LENGTH} caracteres")
    if not re.search(r"[a-z]", plain):
        fallos.append("una minúscula")
    if not re.search(r"[A-Z]", plain):
        fallos.append("una mayúscula")
    if not re.search(r"\d", plain):
        fallos.append("un dígito")
    if not re.search(r"[^\w\s]", plain):
        fallos.append("un símbolo")
    if fallos:
        raise ValidationError("La contraseña debe tener " + ", ".join(fallos) + ".")


def generate_password(length: int = 16) -> str:
    """Para el restablecimiento de credenciales que hace el Admin (RF-06)."""
    alfabeto = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789@#$%&*-_"
    while True:
        candidata = "".join(secrets.choice(alfabeto) for _ in range(length))
        try:
            validate_password_policy(candidata)
            return candidata
        except ValidationError:
            continue
