from datetime import datetime, timedelta
import hashlib
import secrets
import smtplib
from typing import Annotated

import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import get_settings
from .api_docs import install_api_docs
from .database import Base, engine, get_db
from .dependencies import CurrentUser, session_bearer
from .openapi_contracts import Message, errors, result
from .models import Role, User, UserRole, UserSession
from .migrations import initialize_database
from .schemas import ForgotPasswordRequest, LoginRequest, LoginResponse, RegisterRequest, ResetPasswordRequest, UpdateEmailRequest, UserResponse
from .security import create_access_token, decode_access_token, expiry_from_now, hash_password, verify_password
from .mailer import send_recovery_email
from .customers import router as customers_router
from .administration import router as administration_router
from .postal import router as postal_router
from .workshops import router as workshops_router
from .vehicles import router as vehicles_router

settings = get_settings()
app = FastAPI(
    title="Taller Mecánico API",
    version="1.0.0",
    description=(
        "Ejecuta **POST /api/auth/login** con una cuenta de prueba y copia el "
        "**access_token**. Pulsa **Authorize** y pega solo el token. "
        "Cada operación mantiene sus permisos de usuario. Al terminar, ejecuta "
        "**POST /api/auth/logout** para liberar la sesión."
    ),
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(customers_router)
app.include_router(administration_router)
app.include_router(postal_router)
app.include_router(workshops_router)
app.include_router(vehicles_router)


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


@app.get("/api/health", tags=["Estado"], summary="Comprobar que FastAPI está en ejecución")
def health() -> dict[str, str]:
    """Comprueba la respuesta del proceso de la API."""
    return {"status": "ok"}


@app.post("/api/auth/login", tags=["Autenticación"], response_model=LoginResponse,
          summary="Iniciar sesión y obtener un JWT", responses=errors(401, 403, 409, 422))
def login(data: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> LoginResponse:
    """Envía usuario y contraseña en JSON. Solo se admite una sesión activa por cuenta."""
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


@app.post("/api/auth/register", tags=["Autenticación"], response_model=UserResponse,
          status_code=status.HTTP_201_CREATED, summary="Registrar una cuenta de invitado",
          responses=errors(409, 422, 503))
def register(data: RegisterRequest, db: Annotated[Session, Depends(get_db)]) -> UserResponse:
    """Crea una cuenta Invitado con un nombre de usuario y correo únicos."""
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


@app.post("/api/auth/forgot-password", tags=["Autenticación"], status_code=status.HTTP_202_ACCEPTED,
          summary="Solicitar recuperación por correo", responses=result(Message, 422, 503, status=202))
def forgot_password(data: ForgotPasswordRequest, db: Annotated[Session, Depends(get_db)]) -> dict[str, str]:
    """Solicita un enlace válido por 15 minutos. Requiere SMTP y puede enviar un correo real."""
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


@app.post("/api/auth/reset-password", tags=["Autenticación"], status_code=status.HTTP_204_NO_CONTENT,
          summary="Restablecer contraseña", responses=errors(400, 403, 422))
def reset_password(data: ResetPasswordRequest, db: Annotated[Session, Depends(get_db)]) -> None:
    """Usa el token del enlace de recuperación una sola vez e invalida la sesión previa."""
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


@app.put("/api/auth/email", tags=["Autenticación"], response_model=UserResponse,
         summary="Actualizar el correo de mi cuenta", responses=errors(401, 409, 422))
def update_email(data: UpdateEmailRequest, user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> UserResponse:
    """Actualiza el correo de la cuenta autenticada. El correo debe ser único."""
    email = str(data.email).lower()
    if db.execute(select(User.id).where(User.email == email, User.id != user.id)).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ese correo ya está registrado.")
    user.email = email
    db.commit()
    db.refresh(user)
    return user_response(user)


@app.get("/api/auth/me", tags=["Autenticación"], response_model=UserResponse,
         summary="Consultar mi perfil", responses=errors(401))
def me(user: CurrentUser) -> UserResponse:
    """Devuelve el perfil, rol y estado de la sesión del JWT enviado."""
    return user_response(user)


@app.post("/api/auth/logout", tags=["Autenticación"], status_code=status.HTTP_204_NO_CONTENT,
          summary="Cerrar mi sesión", openapi_extra={"security": [{}]})
def logout(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(session_bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Invalida la sesión del JWT. Devuelve 204 también si no hay un token válido."""
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


install_api_docs(app, settings)
