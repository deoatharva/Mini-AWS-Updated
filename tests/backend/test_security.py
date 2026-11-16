import pytest

from app.core.security import (
    BCRYPT_MAX_BYTES,
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)


def test_password_hash_verifies_without_storing_plaintext() -> None:
    password = "correct-horse-battery-staple"
    password_hash = hash_password(password)

    assert password not in password_hash
    assert password_hash.startswith("$2")
    assert verify_password(password, password_hash) is True
    assert verify_password("wrong-password", password_hash) is False


def test_malformed_password_hash_fails_closed() -> None:
    assert verify_password("anything", "not-a-bcrypt-hash") is False


def test_password_longer_than_bcrypt_limit_is_rejected() -> None:
    with pytest.raises(ValueError):
        hash_password("a" * (BCRYPT_MAX_BYTES + 1))


def test_session_tokens_are_random_and_hashed() -> None:
    first = generate_session_token()
    second = generate_session_token()

    assert first != second
    assert first not in hash_session_token(first)
    assert hash_session_token(first) == hash_session_token(first)
    assert hash_session_token(first) != hash_session_token(second)
