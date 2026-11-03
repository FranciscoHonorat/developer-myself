"""Contexto genérico `identity`: usuário e sessão autenticada (ADR-0002, ADR-0009)."""

import hashlib
import re
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta


class IdentityError(Exception):
    pass


class InvalidEmailError(IdentityError):
    pass


class WeakPasswordError(IdentityError):
    pass


class EmailAlreadyRegisteredError(IdentityError):
    pass


class InvalidCredentialsError(IdentityError):
    """Mensagem genérica: nunca confirma se o e-mail existe (ADR-0009)."""

    def __init__(self) -> None:
        super().__init__("E-mail ou senha inválidos.")


class NotAuthenticatedError(IdentityError):
    pass


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
EMAIL_MAX = 254
PASSWORD_MIN = 10
PASSWORD_MAX = 256


@dataclass(frozen=True, slots=True)
class UserId:
    value: uuid.UUID

    @classmethod
    def new(cls) -> UserId:
        return cls(uuid.uuid7())


@dataclass(frozen=True, slots=True)
class Email:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if len(normalized) > EMAIL_MAX or not _EMAIL_RE.match(normalized):
            raise InvalidEmailError("E-mail inválido.")
        object.__setattr__(self, "value", normalized)


def validate_password(password: str) -> None:
    if len(password) < PASSWORD_MIN:
        raise WeakPasswordError(f"A senha precisa ter pelo menos {PASSWORD_MIN} caracteres.")
    if len(password) > PASSWORD_MAX:
        raise WeakPasswordError("Senha longa demais.")


@dataclass(frozen=True, slots=True)
class User:
    id: UserId
    email: Email
    password_hash: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class SessionToken:
    """Token opaco. Só o hash vai para o banco; o valor cru só existe no cookie."""

    raw: str

    @classmethod
    def generate(cls) -> SessionToken:
        return cls(secrets.token_urlsafe(32))

    @property
    def hashed(self) -> str:
        return hashlib.sha256(self.raw.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class AuthSession:
    token_hash: str
    user_id: UserId
    created_at: datetime
    expires_at: datetime

    @classmethod
    def open(
        cls, token: SessionToken, user_id: UserId, now: datetime, ttl: timedelta
    ) -> AuthSession:
        return cls(token.hashed, user_id, now, now + ttl)

    def is_valid(self, now: datetime) -> bool:
        return now < self.expires_at
