import secrets

import bcrypt


def generate_api_key() -> tuple[str, str, str]:
    full_key = f"tw_{secrets.token_urlsafe(32)}"
    prefix = full_key[:11]
    key_hash = bcrypt.hashpw(full_key.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    return full_key, prefix, key_hash


def verify_api_key(raw_key: str, key_hash: str) -> bool:
    return bcrypt.checkpw(raw_key.encode("utf-8"), key_hash.encode("utf-8"))
