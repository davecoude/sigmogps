"""Hashing de contraseñas y política mínima (SEG-02, SEG-07)."""

import re
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.domain.exceptions import ValidationError

# Argon2id con los parámetros por defecto de argon2-cffi, que siguen la
# recomendación de OWASP. Se elige sobre bcrypt por resistencia a GPU.
_hasher = PasswordHasher()

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
