from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from pwdlib import PasswordHash

from .config import get_settings

password_hasher = PasswordHash.recommended()
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def create_access_token(*, user_id: int, session_id: str, expires_at: datetime) -> str:
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "sid": session_id,
        "exp": expires_at,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, get_settings().secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, get_settings().secret_key, algorithms=[ALGORITHM])


def expiry_from_now() -> datetime:
    return datetime.utcnow() + timedelta(minutes=get_settings().access_token_expire_minutes)
