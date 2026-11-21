"""Username: regra de formato e derivação a partir do e-mail (contas antigas)."""

import pytest

from developer_myself.identity.domain.model import (
    Email,
    InvalidUsernameError,
    Username,
    username_from_email,
)


def never(_: str) -> bool:
    return False


def test_username_is_normalized() -> None:
    assert Username(" Jose ") == Username("jose")


@pytest.mark.parametrize("raw", ["ab", "a" * 31, "jo se", "josé", "", "a/b"])
def test_invalid_usernames(raw: str) -> None:
    with pytest.raises(InvalidUsernameError):
        Username(raw)


@pytest.mark.parametrize(
    ("email", "expected"),
    [
        ("jose.silva+app@x.com", "jose.silva_app"),
        ("ÁNGELA@x.com", "_ngela"),
        ("x@x.com", "x-1"),
        ("a" * 40 + "@x.com", "a" * 30),
        ("Ana-B_2@x.com", "ana-b_2"),
    ],
)
def test_username_from_email(email: str, expected: str) -> None:
    assert username_from_email(Email(email), never).value == expected


def test_collision_gets_numeric_suffix() -> None:
    taken = {"jose", "jose-2"}
    assert username_from_email(Email("jose@x.com"), taken.__contains__).value == "jose-3"


def test_suffix_still_fits_30_chars() -> None:
    base = "a" * 30
    result = username_from_email(Email(f"{base}@x.com"), {base}.__contains__)
    assert len(result.value) <= 30
    assert result.value.endswith("-2")
