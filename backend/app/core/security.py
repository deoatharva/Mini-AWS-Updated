import hashlib
import hmac
import secrets

import bcrypt

from app.config import settings

# bcrypt hashes at most 72 bytes; request schemas reject longer passwords.
BCRYPT_MAX_BYTES = 72
BCRYPT_ROUNDS = 12


def hash_password(password: str) -> str:
    """Return a salted bcrypt hash. Raised errors never expose the password."""
    encoded = password.encode("utf-8")
    if len(encoded) > BCRYPT_MAX_BYTES:
        raise ValueError(f"Password must be at most {BCRYPT_MAX_BYTES} bytes.")
    return bcrypt.hashpw(encoded, bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    """Compare a password with a stored hash; malformed input is a failed login."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except (ValueError, TypeError):
        return False


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hmac.new(
        settings.secret_key.encode("utf-8"), token.encode("utf-8"), hashlib.sha256
    ).hexdigest()
