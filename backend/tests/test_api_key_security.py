from app.core.api_key_security import generate_api_key, verify_api_key


def test_generate_api_key_shape():
    full_key, prefix, key_hash = generate_api_key()
    assert full_key.startswith("tw_")
    assert prefix == full_key[:11]
    assert key_hash != full_key


def test_verify_api_key_accepts_matching_key():
    full_key, _prefix, key_hash = generate_api_key()
    assert verify_api_key(full_key, key_hash) is True


def test_verify_api_key_rejects_wrong_key():
    _full_key, _prefix, key_hash = generate_api_key()
    assert verify_api_key("tw_not-the-right-key", key_hash) is False


def test_generate_api_key_is_unique_per_call():
    key_one, _, _ = generate_api_key()
    key_two, _, _ = generate_api_key()
    assert key_one != key_two
