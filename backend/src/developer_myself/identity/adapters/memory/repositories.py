from dataclasses import dataclass, field

from developer_myself.identity.domain.model import (
    AuthSession,
    Email,
    EmailAlreadyRegisteredError,
    User,
    UserId,
)


@dataclass(slots=True)
class InMemoryUserRepository:
    _users: dict[UserId, User] = field(default_factory=dict)

    async def add(self, user: User) -> None:
        if await self.get_by_email(user.email) is not None:
            raise EmailAlreadyRegisteredError("Não foi possível concluir o cadastro.")
        self._users[user.id] = user

    async def get_by_email(self, email: Email) -> User | None:
        return next((u for u in self._users.values() if u.email == email), None)

    async def get(self, user_id: UserId) -> User | None:
        return self._users.get(user_id)

    async def delete(self, user_id: UserId) -> None:
        self._users.pop(user_id, None)


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
class PlainTextHasherForTests:
    """Só para testes: evita o custo do Argon2 nos cenários."""

    async def hash(self, password: str) -> str:
        return f"plain${password}"

    async def verify(self, password_hash: str, password: str) -> bool:
        return password_hash == f"plain${password}"
