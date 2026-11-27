"""Regras puras do domínio `identity`: e-mail, senha e validade de sessão."""

from datetime import UTC, datetime, timedelta

import pytest

from developer_myself.identity.domain.model import (
    PASSWORD_MAX,
    PASSWORD_MIN,
    AuthSession,
    Email,
    InvalidEmailError,
    SessionToken,
    UserId,
    WeakPasswordError,
    validate_password,
)


@pytest.mark.parametrize("raw", ["", "sem-arroba", "a@b", "a b@c.com", f"{'a' * 250}@x.com"])
def test_invalid_email_is_rejected(raw: str) -> None:
    with pytest.raises(InvalidEmailError):
        Email(raw)


def test_password_length_boundaries() -> None:
    with pytest.raises(WeakPasswordError):
        validate_password("a" * (PASSWORD_MIN - 1))
    validate_password("a" * PASSWORD_MIN)
    validate_password("a" * PASSWORD_MAX)
    with pytest.raises(WeakPasswordError):
        validate_password("a" * (PASSWORD_MAX + 1))


def test_session_validity_expires_at_deadline() -> None:
    start = datetime(2026, 11, 20, 12, tzinfo=UTC)
    session = AuthSession.open(SessionToken.generate(), UserId.new(), start, timedelta(hours=1))
    assert session.is_valid(start + timedelta(minutes=59))
    assert not session.is_valid(start + timedelta(hours=1))
