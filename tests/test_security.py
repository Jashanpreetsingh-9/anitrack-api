import pytest

from app.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_round_trip():
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert verify_password("correct horse battery staple", hashed)
    assert not verify_password("wrong password", hashed)


def test_same_password_gives_different_hashes():
    assert hash_password("same") != hash_password("same")


def test_token_round_trip():
    token = create_access_token(42)
    assert decode_access_token(token) == 42


@pytest.mark.parametrize("bad", ["", "not.a.token", "a.b.c"])
def test_invalid_tokens_return_none(bad):
    assert decode_access_token(bad) is None
