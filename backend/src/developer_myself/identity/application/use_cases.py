"""Casos de uso de identidade."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

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
    InvalidUsernameError,
    NotAdminError,
    NotAuthenticatedError,
    RegistrationClosedError,
    SessionToken,
    User,
    UserCursor,
    UserId,
    Username,
    UsernameTakenError,
    UserNotFoundError,
    username_from_email,
    validate_password,
)
from developer_myself.shared.clock import Clock

DEFAULT_SESSION_TTL = timedelta(days=14)
LEGACY_CHECK_COOLDOWN = timedelta(minutes=5)


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
    _login_migration_checked_at: datetime | None = field(default=None, repr=False)

    async def register(self, username: str, email: str, password: str) -> User:
        handle = Username(username)
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
        if await self.users.get_by_username(handle) is not None:
            raise UsernameTakenError
        user = User(
            UserId.new(), address, await self.hasher.hash(password), self.clock.now(), handle
        )
        await self.users.add(user)
        return user

    async def login(self, username: str, password: str) -> tuple[SessionToken, AuthSession]:
        try:
            handle = Username(username)
        except InvalidUsernameError:
            raise InvalidCredentialsError from None
        user = await self.users.get_by_username(handle)
        if user is None and self._should_check_legacy():
            # Conta criada sem username depois do boot (instância antiga no meio do deploy):
            # migra na hora, mas com cooldown quando não há legados (evita full-scan).
            if await self.assign_missing_usernames():
                user = await self.users.get_by_username(handle)
            else:
                self._login_migration_checked_at = self.clock.now()
        if user is None:
            # Gasta o mesmo tempo de um login real: não revela se o username existe.
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

    async def verify_password(self, user_id: UserId, password: str) -> None:
        user = await self.me(user_id)
        if not await self.hasher.verify(user.password_hash, password):
            raise InvalidCredentialsError

    async def finalize_delete_account(self, user_id: UserId) -> None:
        await self.sessions.delete_all_for(user_id)
        await self.users.delete(user_id)

    async def delete_account(self, user_id: UserId, password: str) -> None:
        await self.verify_password(user_id, password)
        await self.finalize_delete_account(user_id)

    async def change_username(self, user_id: UserId, new: str, password: str) -> User:
        user = await self.me(user_id)
        if not await self.hasher.verify(user.password_hash, password):
            raise InvalidCredentialsError
        handle = Username(new)
        if handle != user.username:
            await self.users.set_username(user_id, handle)
        return await self.me(user_id)

    async def assign_missing_usernames(self) -> int:
        """Migração do boot: conta antiga ganha a parte do e-mail antes do @. Idempotente."""
        legacy = await self.users.without_username()
        taken: set[str] = set()
        assigned = 0
        for user in legacy:
            while True:
                candidate = username_from_email(user.email, taken.__contains__)
                taken.add(candidate.value)
                if await self.users.get_by_username(candidate) is not None:
                    continue
                try:
                    # Condicional: se outra instância já deu um username, não sobrescreve.
                    assigned += await self.users.assign_username_if_missing(user.id, candidate)
                    break
                except UsernameTakenError:  # outro processo pegou o nome no meio do caminho
                    continue
        return assigned

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

    def _should_check_legacy(self) -> bool:
        return (
            self._login_migration_checked_at is None
            or self.clock.now() - self._login_migration_checked_at >= LEGACY_CHECK_COOLDOWN
        )

    async def _dummy(self) -> str:
        if self._dummy_hash is None:
            self._dummy_hash = await self.hasher.hash("senha-que-ninguem-usa-0000")
        return self._dummy_hash
