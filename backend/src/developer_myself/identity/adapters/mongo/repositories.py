from datetime import UTC
from typing import Any

from pymongo.asynchronous.collection import AsyncCollection
from pymongo.errors import DuplicateKeyError

from developer_myself.identity.domain.model import (
    AuthSession,
    Email,
    EmailAlreadyRegisteredError,
    User,
    UserCursor,
    UserId,
)

Doc = dict[str, Any]


def _user(doc: Doc) -> User:
    return User(
        id=UserId(doc["_id"]),
        email=Email(doc["email"]),
        password_hash=doc["password_hash"],
        created_at=doc["created_at"].astimezone(UTC),
    )


class MongoUserRepository:
    def __init__(self, collection: AsyncCollection[Doc]) -> None:
        self._col = collection

    async def add(self, user: User) -> None:
        try:
            await self._col.insert_one(
                {
                    "_id": user.id.value,
                    "email": user.email.value,
                    "password_hash": user.password_hash,
                    "created_at": user.created_at,
                }
            )
        except DuplicateKeyError as exc:
            raise EmailAlreadyRegisteredError("Não foi possível concluir o cadastro.") from exc

    async def get_by_email(self, email: Email) -> User | None:
        # `email.value` já é um VO validado: nunca vira um operador ($ne, $gt...).
        doc = await self._col.find_one({"email": email.value})
        return _user(doc) if doc else None

    async def get(self, user_id: UserId) -> User | None:
        doc = await self._col.find_one({"_id": user_id.value})
        return _user(doc) if doc else None

    async def delete(self, user_id: UserId) -> None:
        await self._col.delete_one({"_id": user_id.value})

    async def page(self, limit: int, after: UserCursor | None = None) -> list[User]:
        query: Doc = {}
        if after is not None:
            query["$or"] = [
                {"created_at": {"$lt": after.created_at}},
                {"created_at": after.created_at, "_id": {"$lt": after.user_id}},
            ]
        cursor = self._col.find(query).sort([("created_at", -1), ("_id", -1)]).limit(limit)
        return [_user(doc) async for doc in cursor]


class MongoAuthSessionRepository:
    def __init__(self, collection: AsyncCollection[Doc]) -> None:
        self._col = collection

    async def add(self, session: AuthSession) -> None:
        await self._col.insert_one(
            {
                "_id": session.token_hash,
                "user_id": session.user_id.value,
                "created_at": session.created_at,
                "expires_at": session.expires_at,
            }
        )

    async def get(self, token_hash: str) -> AuthSession | None:
        doc = await self._col.find_one({"_id": token_hash})
        if doc is None:
            return None
        return AuthSession(
            token_hash=doc["_id"],
            user_id=UserId(doc["user_id"]),
            created_at=doc["created_at"].astimezone(UTC),
            expires_at=doc["expires_at"].astimezone(UTC),
        )

    async def delete(self, token_hash: str) -> None:
        await self._col.delete_one({"_id": token_hash})

    async def delete_all_for(self, user_id: UserId) -> None:
        await self._col.delete_many({"user_id": user_id.value})


class MongoRegistrationGate:
    """Documento único `{_id: "registration", open: bool}` em `app_settings`; ausente = aberto."""

    _ID = "registration"

    def __init__(self, collection: AsyncCollection[Doc]) -> None:
        self._col = collection

    async def is_open(self) -> bool:
        doc = await self._col.find_one({"_id": self._ID})
        return True if doc is None else bool(doc["open"])

    async def set_open(self, open: bool) -> None:
        await self._col.update_one({"_id": self._ID}, {"$set": {"open": open}}, upsert=True)
