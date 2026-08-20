from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_and_verify_password_roundtrip():
    hashed = hash_password("hunter2222")
    assert verify_password("hunter2222", hashed) is True


def test_verify_password_rejects_wrong_password():
    hashed = hash_password("hunter2222")
    assert verify_password("wrong-password", hashed) is False


def test_access_token_roundtrip():
    token = create_access_token("user-123")
    assert decode_access_token(token) == "user-123"


def test_decode_access_token_rejects_garbage():
    assert decode_access_token("not-a-real-token") is None
