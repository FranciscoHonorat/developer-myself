"""Casos de uso de identidade."""

from dataclasses import dataclass, field
from datetime import timedelta

from developer_myself.identity.application.ports import (
    AuthSessionRepository,
    PasswordHasher,
    UserRepository,
)
from developer_myself.identity.domain.model import (
    AuthSession,
    Email,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidEmailError,
    NotAuthenticatedError,
    SessionToken,
    User,
    UserId,
    validate_password,
)
from developer_myself.shared.clock import Clock

DEFAULT_SESSION_TTL = timedelta(days=14)


@dataclass(slots=True)
class IdentityUseCases:
    users: UserRepository
    sessions: AuthSessionRepository
    hasher: PasswordHasher
    clock: Clock
    session_ttl: timedelta = DEFAULT_SESSION_TTL
    _dummy_hash: str | None = field(default=None, repr=False)

    async def register(self, email: str, password: str) -> User:
        address = Email(email)
        validate_password(password)
        if await self.users.get_by_email(address) is not None:
            raise EmailAlreadyRegisteredError("Não foi possível concluir o cadastro.")
        user = User(UserId.new(), address, await self.hasher.hash(password), self.clock.now())
        await self.users.add(user)
        return user

    async def login(self, email: str, password: str) -> tuple[SessionToken, AuthSession]:
        try:
            address = Email(email)
        except InvalidEmailError:
            raise InvalidCredentialsError from None
        user = await self.users.get_by_email(address)
        if user is None:
            # Gasta o mesmo tempo de um login real: não revela se o e-mail existe.
            await self.hasher.verify(await self._dummy(), password)
            raise InvalidCredentialsError
        if not await self.hasher.verify(user.password_hash, password):
            raise InvalidCredentialsError
        token = SessionToken.generate()
        session = AuthSession.open(token, user.id, self.clock.now(), self.session_ttl)
        await self.sessions.add(session)
        return token, session

    async def authenticate(self, raw_token: str | None) -> UserId:
        if not raw_token:
            raise NotAuthenticatedError("Não autenticado.")
        session = await self.sessions.get(SessionToken(raw_token).hashed)
        if session is None or not session.is_valid(self.clock.now()):
            raise NotAuthenticatedError("Sessão expirada.")
        return session.user_id

    async def logout(self, raw_token: str | None) -> None:
        if raw_token:
            await self.sessions.delete(SessionToken(raw_token).hashed)

    async def me(self, user_id: UserId) -> User:
        user = await self.users.get(user_id)
        if user is None:
            raise NotAuthenticatedError("Usuário não encontrado.")
        return user

    async def delete_account(self, user_id: UserId, password: str) -> None:
        user = await self.me(user_id)
        if not await self.hasher.verify(user.password_hash, password):
            raise InvalidCredentialsError
        await self.sessions.delete_all_for(user_id)
        await self.users.delete(user_id)

    async def _dummy(self) -> str:
        if self._dummy_hash is None:
            self._dummy_hash = await self.hasher.hash("senha-que-ninguem-usa-0000")
        return self._dummy_hash
