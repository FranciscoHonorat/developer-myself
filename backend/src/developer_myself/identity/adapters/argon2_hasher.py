"""Argon2id (ADR-0009). Chamada bloqueante vai para `asyncio.to_thread` (ADR-0004)."""

import asyncio

from argon2 import PasswordHasher as Argon2
from argon2.exceptions import InvalidHashError, VerificationError


class Argon2PasswordHasher:
    def __init__(self) -> None:
        self._argon = Argon2()

    async def hash(self, password: str) -> str:
        return await asyncio.to_thread(self._argon.hash, password)

    async def verify(self, password_hash: str, password: str) -> bool:
        try:
            return await asyncio.to_thread(self._argon.verify, password_hash, password)
        except VerificationError, InvalidHashError:
            return False
