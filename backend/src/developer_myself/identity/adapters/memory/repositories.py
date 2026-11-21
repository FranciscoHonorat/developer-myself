import dataclasses
from dataclasses import dataclass, field

from developer_myself.identity.domain.model import (
    AuthSession,
    Email,
    EmailAlreadyRegisteredError,
    User,
    UserCursor,
    UserId,
    Username,
    UsernameTakenError,
)


@dataclass(slots=True)
class InMemoryUserRepository:
    _users: dict[UserId, User] = field(default_factory=dict)

    async def add(self, user: User) -> None:
        if await self.get_by_email(user.email) is not None:
            raise EmailAlreadyRegisteredError("Não foi possível concluir o cadastro.")
        if user.username is not None and await self.get_by_username(user.username) is not None:
            raise UsernameTakenError
        self._users[user.id] = user

    async def get_by_username(self, username: Username) -> User | None:
        return next((u for u in self._users.values() if u.username == username), None)

    async def without_username(self) -> list[User]:
        legacy = [u for u in self._users.values() if u.username is None]
        return sorted(legacy, key=lambda u: (u.created_at, u.id.value))

    async def assign_username_if_missing(self, user_id: UserId, username: Username) -> bool:
        user = self._users.get(user_id)
        if user is None or user.username is not None:
            return False
        await self.set_username(user_id, username)
        return True

    async def set_username(self, user_id: UserId, username: Username) -> None:
        other = await self.get_by_username(username)
        if other is not None and other.id != user_id:
            raise UsernameTakenError
        user = self._users.get(user_id)
        if user is not None:
            self._users[user_id] = dataclasses.replace(user, username=username)

    async def get_by_email(self, email: Email) -> User | None:
        return next((u for u in self._users.values() if u.email == email), None)

    async def get(self, user_id: UserId) -> User | None:
        return self._users.get(user_id)

    async def delete(self, user_id: UserId) -> None:
        self._users.pop(user_id, None)

    async def page(self, limit: int, after: UserCursor | None = None) -> list[User]:
        found = [u for u in self._users.values() if after is None or after.is_after(u)]
        return sorted(found, key=lambda u: (u.created_at, u.id.value), reverse=True)[:limit]


@dataclass(slots=True)
class InMemoryAuthSessionRepository:
    _sessions: dict[str, AuthSession] = field(default_factory=dict)

    async def add(self, session: AuthSession) -> None:
        self._sessions[session.token_hash] = session

    async def get(self, token_hash: str) -> AuthSession | None:
        return self._sessions.get(token_hash)

    async def delete(self, token_hash: str) -> None:
        self._sessions.pop(token_hash, None)

    async def delete_all_for(self, user_id: UserId) -> None:
        for key in [k for k, s in self._sessions.items() if s.user_id == user_id]:
            del self._sessions[key]


@dataclass(slots=True)
class InMemoryRegistrationGate:
    _open: bool = True

    async def is_open(self) -> bool:
        return self._open

    async def set_open(self, open: bool) -> None:
        self._open = open


@dataclass(slots=True)
class PlainTextHasherForTests:
    """Só para testes: evita o custo do Argon2 nos cenários."""

    async def hash(self, password: str) -> str:
        return f"plain${password}"

    async def verify(self, password_hash: str, password: str) -> bool:
        return password_hash == f"plain${password}"
