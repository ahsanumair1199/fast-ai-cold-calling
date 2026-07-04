import jwt
import pytest

from src.utils.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_round_trip():
    hashed = hash_password("supersecret1")
    assert hashed != "supersecret1"
    assert verify_password("supersecret1", hashed)
    assert not verify_password("wrongpassword", hashed)


def test_password_hashes_are_salted():
    a = hash_password("samepassword")
    b = hash_password("samepassword")
    assert a != b


def test_access_token_round_trip():
    token = create_access_token({"user_id": 42})
    payload = decode_access_token(token)
    assert payload["user_id"] == 42


def test_access_token_rejects_tampering():
    token = create_access_token({"user_id": 1}) + "tampered"
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(token)
