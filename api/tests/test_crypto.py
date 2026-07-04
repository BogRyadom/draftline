"""Fernet token cipher tests."""

import pytest
from cryptography.fernet import Fernet, InvalidToken

from app.crypto import TokenCipher


def test_encrypt_decrypt_round_trip():
    cipher = TokenCipher(Fernet.generate_key())
    secret = "1//refresh-token-value"

    encrypted = cipher.encrypt(secret)

    assert encrypted != secret
    assert cipher.decrypt(encrypted) == secret


def test_decrypt_with_wrong_key_fails():
    encrypted = TokenCipher(Fernet.generate_key()).encrypt("secret")
    other = TokenCipher(Fernet.generate_key())

    with pytest.raises(InvalidToken):
        other.decrypt(encrypted)
