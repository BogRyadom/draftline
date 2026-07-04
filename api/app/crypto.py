"""Symmetric encryption for OAuth refresh tokens at rest (Fernet).

Tokens are encrypted before they touch the database and decrypted only when we
need to mint a fresh access token. The key comes from `FERNET_KEY`.
"""

from functools import lru_cache

from cryptography.fernet import Fernet

from app.config import get_settings


class TokenCipher:
    """Thin wrapper over Fernet that works with `str` in and out."""

    def __init__(self, key: str | bytes) -> None:
        self._fernet = Fernet(key.encode() if isinstance(key, str) else key)

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, token: str) -> str:
        return self._fernet.decrypt(token.encode()).decode()


@lru_cache
def get_cipher() -> TokenCipher:
    """Return the app-wide cipher, built from FERNET_KEY."""
    key = get_settings().fernet_key
    if not key:
        raise RuntimeError("FERNET_KEY is not configured.")
    return TokenCipher(key)
