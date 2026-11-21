from typing import Protocol

from developer_myself.identity.domain.model import (
    AuthSession,
    Email,
    User,
    UserCursor,
    UserId,
    Username,
)


class UserRepository(Protocol):
    async def add(self, user: User) -> None:
        """Levanta `EmailAlreadyRegisteredError` se o e-mail já existe."""
        ...

    async def get_by_email(self, email: Email) -> User | None: ...

    async def get(self, user_id: UserId) -> User | None: ...

    async def get_by_username(self, username: Username) -> User | None: ...

    async def without_username(self) -> list[User]:
        """Contas antigas ainda sem username, mais antigas primeiro."""
        ...

    async def assign_username_if_missing(self, user_id: UserId, username: Username) -> bool:
        """Migração: grava só se a conta ainda não tem username. False = já tinha (outra
        instância chegou antes). Levanta `UsernameTakenError` se outro usuário já usa."""
        ...

    async def set_username(self, user_id: UserId, username: Username) -> None:
        """Levanta `UsernameTakenError` se outro usuário já usa esse username."""
        ...

    async def delete(self, user_id: UserId) -> None: ...

    async def page(self, limit: int, after: UserCursor | None = None) -> list[User]:
        """Mais recentes primeiro (`created_at`, depois id), estritamente após `after`."""
        ...


class AuthSessionRepository(Protocol):
    async def add(self, session: AuthSession) -> None: ...

    async def get(self, token_hash: str) -> AuthSession | None: ...

    async def delete(self, token_hash: str) -> None: ...

    async def delete_all_for(self, user_id: UserId) -> None: ...


class PasswordHasher(Protocol):
    async def hash(self, password: str) -> str: ...

    async def verify(self, password_hash: str, password: str) -> bool: ...


class RegistrationGate(Protocol):
    """Se novas contas podem ser criadas. Persistente: sobrevive a reinícios."""

    async def is_open(self) -> bool: ...

    async def set_open(self, open: bool) -> None: ...
