from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import User, UserSession
from .security import decode_access_token

session_bearer = HTTPBearer(
    scheme_name="SessionBearer",
    bearerFormat="JWT",
    description="Inicia sesión en POST /api/auth/login y pega solo el access_token.",
    auto_error=False,
)
DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(session_bearer)], db: DbSession,
) -> User:
    if credentials is None:
        raise HTTPException(401, "Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    credentials_error = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión no válida o expirada.")
    try:
        payload = decode_access_token(credentials.credentials)
        user_id, session_id = int(payload["sub"]), str(payload["sid"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        raise credentials_error

    user = db.get(User, user_id)
    session = db.get(UserSession, session_id)
    if (
        user is None
        or user.bin_status != 1
        or user.assigned_role.bin_status != 1
        or user.active_session_id != session_id
        or session is None
        or session.ended_at is not None
    ):
        raise credentials_error
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
