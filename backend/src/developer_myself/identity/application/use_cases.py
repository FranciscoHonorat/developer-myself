"""Casos de uso de identidade."""

from dataclasses import dataclass, field
from datetime import timedelta

from developer_myself.identity.application.ports import (
    AuthSessionRepository,
    PasswordHasher,
    RegistrationGate,
    UserRepository,
)
from developer_myself.identity.domain.model import (
    AuthSession,
    CannotDeleteSelfError,
    Email,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidEmailError,
    NotAdminError,
    NotAuthenticatedError,
    RegistrationClosedError,
    SessionToken,
    User,
    UserCursor,
    UserId,
    UserNotFoundError,
    validate_password,
)
from developer_myself.shared.clock import Clock

DEFAULT_SESSION_TTL = timedelta(days=14)


@dataclass(frozen=True, slots=True)
class UserPage:
    items: list[User]
    next: UserCursor | None


class _AlwaysOpen:
    """Padrão quando ninguém injeta um gate (testes e chamadas antigas): cadastro aberto."""

    async def is_open(self) -> bool:
        return True

    async def set_open(self, open: bool) -> None:
        raise NotImplementedError("injete um RegistrationGate para abrir/fechar o cadastro")


@dataclass(slots=True)
class IdentityUseCases:
    users: UserRepository
    sessions: AuthSessionRepository
    hasher: PasswordHasher
    clock: Clock
    session_ttl: timedelta = DEFAULT_SESSION_TTL
    registration: RegistrationGate = field(default_factory=_AlwaysOpen)
    admin_emails: frozenset[Email] = frozenset()
    _dummy_hash: str | None = field(default=None, repr=False)

    async def register(self, email: str, password: str) -> User:
        address = Email(email)
        validate_password(password)
        if not await self.registration.is_open():
            # Exceção só para o admin que ainda não tem conta (não se trancar para fora).
            # Admin já cadastrado recebe o mesmo 403: a resposta não revela quem é admin.
            is_new_admin = (
                address in self.admin_emails and await self.users.get_by_email(address) is None
            )
            if not is_new_admin:
                raise RegistrationClosedError
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

    # ------------------------------------------------------------------ admin
    async def is_admin(self, user_id: UserId) -> bool:
        user = await self.users.get(user_id)
        return user is not None and user.email in self.admin_emails

    async def require_admin(self, user_id: UserId) -> User:
        user = await self.users.get(user_id)
        if user is None or user.email not in self.admin_emails:
            raise NotAdminError
        return user

    async def admin_emails_without_account(self) -> int:
        """Quantos admins configurados ainda não se cadastraram (risco: quem chegar antes)."""
        return sum([await self.users.get_by_email(e) is None for e in self.admin_emails])

    async def registration_open(self) -> bool:
        return await self.registration.is_open()

    async def set_registration(self, admin_id: UserId, open: bool) -> None:
        await self.require_admin(admin_id)
        await self.registration.set_open(open)

    async def list_accounts(
        self, admin_id: UserId, limit: int, after: UserCursor | None = None
    ) -> UserPage:
        await self.require_admin(admin_id)
        found = await self.users.page(limit + 1, after)
        items = found[:limit]
        return UserPage(items, UserCursor.of(items[-1]) if len(found) > limit else None)

    async def admin_delete(self, admin_id: UserId, account_id: UserId) -> None:
        """Só a conta e as sessões; trilha/histórico/caderno ficam com quem compõe (a rota)."""
        await self.require_admin(admin_id)
        if account_id == admin_id:
            raise CannotDeleteSelfError
        if await self.users.get(account_id) is None:
            raise UserNotFoundError
        await self.sessions.delete_all_for(account_id)
        await self.users.delete(account_id)

    async def _dummy(self) -> str:
        if self._dummy_hash is None:
            self._dummy_hash = await self.hasher.hash("senha-que-ninguem-usa-0000")
        return self._dummy_hash
