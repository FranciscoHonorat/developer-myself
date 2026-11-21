"""Contexto genérico `identity`: usuário e sessão autenticada (ADR-0002, ADR-0009)."""

import hashlib
import re
import secrets
import uuid
from collections.abc import Callable
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
        super().__init__("Username ou senha inválidos.")


class NotAuthenticatedError(IdentityError):
    pass


class InvalidUsernameError(IdentityError):
    def __init__(self) -> None:
        super().__init__("Use de 3 a 30 caracteres: letras minúsculas, números, ponto, _ ou -.")


class UsernameTakenError(IdentityError):
    def __init__(self) -> None:
        super().__init__("Este username já está em uso.")


class NotAdminError(IdentityError):
    def __init__(self) -> None:
        super().__init__("Você não tem acesso à área de admin.")


class RegistrationClosedError(IdentityError):
    def __init__(self) -> None:
        super().__init__("Novos cadastros estão fechados no momento.")


class CannotDeleteSelfError(IdentityError):
    def __init__(self) -> None:
        super().__init__("Para excluir a própria conta, use a página Conta.")


class UserNotFoundError(IdentityError):
    def __init__(self) -> None:
        super().__init__("Conta não encontrada.")


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


USERNAME_MIN = 3
USERNAME_MAX = 30
_USERNAME_RE = re.compile(rf"^[a-z0-9._-]{{{USERNAME_MIN},{USERNAME_MAX}}}$")
_USERNAME_BAD_CHAR = re.compile(r"[^a-z0-9._-]")


@dataclass(frozen=True, slots=True)
class Username:
    """Identificador de login. Comparado sem diferenciar maiúsculas: guarda minúsculo."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if not _USERNAME_RE.fullmatch(normalized):
            raise InvalidUsernameError
        object.__setattr__(self, "value", normalized)


def username_from_email(email: Email, taken: Callable[[str], bool]) -> Username:
    """Username de conta antiga: parte do e-mail antes do @, adaptada à regra.

    Caractere fora da regra vira `_`; curto demais ganha `-1`; colisão ganha `-2`, `-3`…
    (cortando a base para o total caber em 30).
    """
    base = _USERNAME_BAD_CHAR.sub("_", email.value.split("@", 1)[0])[:USERNAME_MAX]
    if len(base) < USERNAME_MIN:
        base = f"{base}-1"
    candidate, n = base, 1
    while taken(candidate):
        n += 1
        suffix = f"-{n}"
        candidate = base[: USERNAME_MAX - len(suffix)] + suffix
    return Username(candidate)


def parse_admin_emails(raw: str) -> frozenset[Email]:
    """`DM_ADMIN_EMAILS`: e-mails separados por vírgula. Itens vazios são ignorados;
    um e-mail inválido derruba o boot (melhor que um admin silenciosamente ausente)."""
    return frozenset(Email(item) for item in raw.split(",") if item.strip())


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
    # None só em conta antiga até a migração do boot (`assign_missing_usernames`).
    username: Username | None = None


@dataclass(frozen=True, slots=True)
class UserCursor:
    """Última conta vista na listagem do admin. Keyset: (created_at, id), decrescente."""

    created_at: datetime
    user_id: uuid.UUID

    @classmethod
    def of(cls, user: User) -> UserCursor:
        return cls(user.created_at, user.id.value)

    def is_after(self, user: User) -> bool:
        return (user.created_at, user.id.value) < (self.created_at, self.user_id)


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
