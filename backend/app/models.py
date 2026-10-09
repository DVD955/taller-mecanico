import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, LargeBinary, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class UserRole(str, enum.Enum):
    ADMINISTRADOR = "ADMINISTRADOR"
    RECEPCIONISTA = "RECEPCIONISTA"
    MECANICO = "MECANICO"
    INVITADO = "INVITADO"


class Status(Base):
    __tablename__ = "status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    value: Mapped[str] = mapped_column("valor", String(20), unique=True)
    description: Mapped[str] = mapped_column("descripcion", String(150))


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    description: Mapped[str] = mapped_column(String(200))
    bin_status: Mapped[int] = mapped_column(ForeignKey("status.id"), default=1)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    state: Mapped[Status] = relationship()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    role: Mapped[str] = mapped_column(ForeignKey("roles.code"), default=UserRole.INVITADO.value)
    bin_status: Mapped[int] = mapped_column(ForeignKey("status.id"), default=1)
    state: Mapped[Status] = relationship()
    assigned_role: Mapped[Role] = relationship()
    recovery_code_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recovery_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    active_session_id: Mapped[str | None] = mapped_column(String(36), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    sessions: Mapped[list["UserSession"]] = relationship(back_populates="user", cascade="all, delete-orphan", passive_deletes=True)


class Workshop(Base):
    __tablename__ = "workshops"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    rfc: Mapped[str] = mapped_column(String(13), unique=True)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    street: Mapped[str] = mapped_column(String(150))
    number: Mapped[str] = mapped_column(String(20))
    postal_code: Mapped[str] = mapped_column(String(5))
    neighborhood: Mapped[str] = mapped_column(String(100))
    municipality: Mapped[str] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(100))
    identity_fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    image: Mapped[bytes | None] = mapped_column(LargeBinary(length=16_777_215), nullable=True)
    image_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    bin_status: Mapped[int] = mapped_column(ForeignKey("status.id"), default=1)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status_record: Mapped[Status] = relationship()


class AdministrationAudit(Base):
    __tablename__ = "administration_audit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[int] = mapped_column(Integer)
    entity: Mapped[str] = mapped_column(String(30))
    entity_id: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(50))
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PostalState(Base):
    __tablename__ = 'postal_states'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)


class PostalMunicipality(Base):
    __tablename__ = 'postal_municipalities'
    __table_args__ = (UniqueConstraint('state_id', 'name', name='uq_postal_municipality'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    state_id: Mapped[int] = mapped_column(ForeignKey('postal_states.id'), index=True)
    name: Mapped[str] = mapped_column(String(100))
    state_record: Mapped[PostalState] = relationship()


class PostalSettlement(Base):
    __tablename__ = "postal_settlements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    postal_code: Mapped[str] = mapped_column(String(5), index=True)
    state: Mapped[str] = mapped_column(String(100), index=True)
    municipality: Mapped[str] = mapped_column(String(100))
    neighborhood: Mapped[str] = mapped_column(String(100))
    municipality_id: Mapped[int | None] = mapped_column(ForeignKey('postal_municipalities.id'), index=True, nullable=True)
    municipality_record: Mapped[PostalMunicipality] = relationship()


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    user: Mapped[User] = relationship(back_populates="sessions")
