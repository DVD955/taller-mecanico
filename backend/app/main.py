from datetime import datetime, timedelta
import hashlib
import secrets
import smtplib
from typing import Annotated

import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import get_settings
from .database import Base, engine, get_db
from .dependencies import CurrentUser
from .models import Role, User, UserRole, UserSession
from .migrations import initialize_database
from .schemas import ForgotPasswordRequest, LoginRequest, LoginResponse, RegisterRequest, ResetPasswordRequest, UpdateEmailRequest, UserResponse
from .security import create_access_token, decode_access_token, expiry_from_now, hash_password, verify_password
from .mailer import send_recovery_email
from .customers import router as customers_router
from .administration import router as administration_router
from .postal import router as postal_router
from .workshops import router as workshops_router

settings = get_settings()
app = FastAPI(title="Taller Mecánico API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
bearer = HTTPBearer(auto_error=False)
app.include_router(customers_router)
app.include_router(administration_router)
app.include_router(postal_router)
app.include_router(workshops_router)


@app.on_event("startup")
def create_tables() -> None:
    initialize_database()


def user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        role_name=user.assigned_role.name,
        status=user.state.value.upper(),
        bin_status=user.bin_status,
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
        if user.bin_status != 1 or user.assigned_role.bin_status != 1:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tu usuario o rol está suspendido. Contacta al administrador.")

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


@app.post("/api/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, db: Annotated[Session, Depends(get_db)]) -> UserResponse:
    if db.execute(select(User.id).where((User.username == data.username) | (User.email == str(data.email).lower()))).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El usuario o correo ya está registrado.")
    if len(data.full_name.strip()) < 3:
        raise HTTPException(422, "El nombre completo debe tener al menos 3 caracteres.")
    guest = db.execute(select(Role).where(Role.code == 'INVITADO').with_for_update()).scalar_one()
    if guest.bin_status != 1:
        raise HTTPException(503, "El registro de invitados no está disponible.")
    user = User(username=data.username, full_name=data.full_name.strip(), email=str(data.email).lower(),
                password_hash=hash_password(data.password), role=UserRole.INVITADO.value,
                bin_status=1)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El usuario o correo ya está registrado.")
    db.refresh(user)
    return user_response(user)


@app.post("/api/auth/forgot-password", status_code=status.HTTP_202_ACCEPTED)
def forgot_password(data: ForgotPasswordRequest, db: Annotated[Session, Depends(get_db)]) -> dict[str, str]:
    message = {"message": "Si el correo está registrado, recibirás un enlace para restablecer tu contraseña."}
    if not settings.smtp_host or not settings.smtp_from or not settings.smtp_password:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="El envío de correo aún no está configurado.")
    with db.begin():
        user = db.execute(select(User).where(User.email == str(data.email).lower()).with_for_update()).scalar_one_or_none()
        if user is None or user.bin_status != 1:
            return message
        token = secrets.token_urlsafe(32)
        user.recovery_code_hash = hashlib.sha256(token.encode()).hexdigest()
        user.recovery_expires_at = datetime.utcnow() + timedelta(minutes=15)
        try:
            send_recovery_email(user.email, token)
        except (smtplib.SMTPException, OSError, RuntimeError):
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="No se pudo enviar el correo. Inténtalo más tarde.")
    return message


@app.post("/api/auth/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(data: ResetPasswordRequest, db: Annotated[Session, Depends(get_db)]) -> None:
    with db.begin():
        digest = hashlib.sha256(data.token.encode()).hexdigest()
        user = db.execute(select(User).where(User.recovery_code_hash == digest).with_for_update()).scalar_one_or_none()
        if user is None or user.recovery_expires_at is None or user.recovery_expires_at <= datetime.utcnow():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El enlace de recuperación no es válido o ha expirado.")
        if user.bin_status != 1:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tu usuario está inactivo. Contacta al administrador.")
        current_session = db.get(UserSession, user.active_session_id) if user.active_session_id else None
        if current_session and current_session.ended_at is None:
            current_session.ended_at = datetime.utcnow()
        user.active_session_id = None
        user.password_hash = hash_password(data.new_password)
        user.recovery_code_hash = None
        user.recovery_expires_at = None


@app.put("/api/auth/email", response_model=UserResponse)
def update_email(data: UpdateEmailRequest, user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> UserResponse:
    email = str(data.email).lower()
    if db.execute(select(User.id).where(User.email == email, User.id != user.id)).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ese correo ya está registrado.")
    user.email = email
    db.commit()
    db.refresh(user)
    return user_response(user)


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
