from datetime import datetime
from typing import Annotated

import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from .config import get_settings
from .database import Base, engine, get_db
from .dependencies import CurrentUser
from .models import User, UserRole, UserSession, UserStatus
from .schemas import LoginRequest, LoginResponse, RegisterRequest, RegisterResponse, ResetPasswordRequest, UserResponse
from .security import create_access_token, decode_access_token, expiry_from_now, hash_password, verify_password
import secrets

settings = get_settings()
app = FastAPI(title="Taller Mecánico API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
bearer = HTTPBearer(auto_error=False)


@app.on_event("startup")
def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
    # Migración ligera para instalaciones creadas antes de la recuperación por código.
    if "recovery_code_hash" not in {column["name"] for column in inspect(engine).get_columns("users")}:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE users ADD COLUMN recovery_code_hash VARCHAR(255) NULL"))


def user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        status=user.status,
        active_session=user.active_session_id is not None,
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/auth/login", response_model=LoginResponse)
def login(data: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> LoginResponse:
    # El bloqueo de fila evita que dos solicitudes simultáneas creen sesiones distintas.
    with db.begin():
        user = db.execute(select(User).where(User.username == data.username).with_for_update()).scalar_one_or_none()
        if user is None or not verify_password(data.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o contraseña incorrectos.")
        if user.status != UserStatus.ACTIVO:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tu usuario está inactivo. Contacta al administrador.")

        if user.active_session_id:
            active = db.get(UserSession, user.active_session_id)
            if active and active.ended_at is None and active.expires_at > datetime.utcnow():
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tu cuenta ya tiene una sesión iniciada. Ciérrala antes de volver a acceder.")
            user.active_session_id = None

        expires_at = expiry_from_now()
        new_session = UserSession(user_id=user.id, expires_at=expires_at)
        db.add(new_session)
        db.flush()
        user.active_session_id = new_session.id
        token = create_access_token(user_id=user.id, session_id=new_session.id, expires_at=expires_at)
        response_user = user_response(user)
    return LoginResponse(access_token=token, expires_at=expires_at, user=response_user)


@app.post("/api/auth/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, db: Annotated[Session, Depends(get_db)]) -> RegisterResponse:
    if data.role == UserRole.ADMINISTRADOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="El rol administrador solo puede ser asignado por un administrador existente.")

    recovery_code = secrets.token_urlsafe(12)
    with db.begin():
        if db.execute(select(User).where(User.username == data.username).with_for_update()).scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ese nombre de usuario ya está registrado.")
        user = User(
            username=data.username,
            full_name=data.full_name.strip(),
            password_hash=hash_password(data.password),
            recovery_code_hash=hash_password(recovery_code),
            role=data.role,
            status=UserStatus.ACTIVO,
        )
        db.add(user)
        db.flush()
        response_user = user_response(user)
    return RegisterResponse(user=response_user, recovery_code=recovery_code)


@app.post("/api/auth/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(data: ResetPasswordRequest, db: Annotated[Session, Depends(get_db)]) -> None:
    with db.begin():
        user = db.execute(select(User).where(User.username == data.username).with_for_update()).scalar_one_or_none()
        if user is None or not user.recovery_code_hash or not verify_password(data.recovery_code, user.recovery_code_hash):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuario o código de recuperación incorrecto.")
        if user.status != UserStatus.ACTIVO:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tu usuario está inactivo. Contacta al administrador.")
        current_session = db.get(UserSession, user.active_session_id) if user.active_session_id else None
        if current_session and current_session.ended_at is None:
            current_session.ended_at = datetime.utcnow()
        user.active_session_id = None
        user.password_hash = hash_password(data.new_password)


@app.get("/api/auth/me", response_model=UserResponse)
def me(user: CurrentUser) -> UserResponse:
    return user_response(user)


@app.post("/api/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    if credentials is None:
        return
    try:
        payload = decode_access_token(credentials.credentials)
        user_id, session_id = int(payload["sub"]), str(payload["sid"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        return
    with db.begin():
        user = db.execute(select(User).where(User.id == user_id).with_for_update()).scalar_one_or_none()
        session = db.get(UserSession, session_id)
        if session and session.user_id == user_id and session.ended_at is None:
            session.ended_at = datetime.utcnow()
        if user and user.active_session_id == session_id:
            user.active_session_id = None
