"""Crear y administrar roles y asignarlos a cuentas: exclusivo del administrador."""
import re
import unicodedata

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import contains_eager

from .dependencies import CurrentUser, DbSession
from .models import AdministrationAudit, Role, Status, User, UserRole
from .schemas import RegisterRequest, UserResponse
from .security import hash_password

router = APIRouter(prefix='/api/admin', tags=['Administración de roles'])


def authorize_admin(user: User) -> None:
    if user.role != UserRole.ADMINISTRADOR:
        raise HTTPException(403, 'Solo el administrador puede crear, administrar o asignar roles.')


class RoleInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    name: str = Field(min_length=3, max_length=50)
    description: str = Field(default='', max_length=200)

    @field_validator('name', 'description')
    @classmethod
    def normalize(cls, value: str) -> str:
        if any(unicodedata.category(c) == 'Cc' for c in value):
            raise ValueError('No uses caracteres de control.')
        return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', value.strip()))


class RoleUpdate(RoleInput):
    version: int = Field(ge=1)
    bin_status: int = Field(ge=1, le=2)


class VersionRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    version: int = Field(ge=1)


class AssignRole(BaseModel):
    model_config = ConfigDict(extra='forbid')
    role_id: int = Field(ge=1)


class StaffAccount(RegisterRequest):
    role_id: int = Field(ge=1)


def role_response(role: Role) -> dict:
    return dict(id=role.id, code=role.code, name=role.name, description=role.description,
                bin_status=role.bin_status, status=role.state.value, version=role.version)


def audit(db, user: User, entity: str, entity_id: int, action: str) -> None:
    db.add(AdministrationAudit(actor_id=user.id, entity=entity, entity_id=entity_id, action=action))


def save(db, detail: str) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, detail)


def locked_role(db, role_id: int) -> Role:
    role = db.execute(select(Role).where(Role.id == role_id).with_for_update()).scalar_one_or_none()
    if role is None or role.bin_status == 3:
        raise HTTPException(404, 'El rol no existe o fue dado de baja.')
    return role


def check_change(db, role: Role, version: int, next_status: int) -> None:
    if role.version != version:
        raise HTTPException(409, 'El rol cambió. Actualiza el listado antes de continuar.')
    if next_status != 1:
        if role.code in ('ADMINISTRADOR', 'INVITADO'):
            raise HTTPException(409, 'Este rol es necesario para el acceso y el registro; debe permanecer activo.')
        # Las cuentas conservan su asociación. CurrentUser bloquea su acceso
        # mientras el rol esté suspendido, incluso con una sesión ya abierta.


@router.get('/status')
def list_status(user: CurrentUser, db: DbSession) -> list[dict]:
    authorize_admin(user)
    return [dict(id=s.id, value=s.value, description=s.description) for s in db.scalars(select(Status).order_by(Status.id))]


@router.get('/roles')
def list_roles(user: CurrentUser, db: DbSession) -> list[dict]:
    authorize_admin(user)
    query = select(Role).join(Role.state).options(contains_eager(Role.state)).where(Role.bin_status.in_((1, 2))).order_by(Role.name)
    return [role_response(role) for role in db.scalars(query)]


@router.post('/roles', status_code=201)
def create_role(data: RoleInput, user: CurrentUser, db: DbSession) -> dict:
    authorize_admin(user)
    ascii_name = ''.join(c for c in unicodedata.normalize('NFKD', data.name) if not unicodedata.combining(c))
    code = re.sub(r'[^A-Z0-9]+', '_', ascii_name.upper()).strip('_')
    if len(code) < 3 or len(code) > 50:
        raise HTTPException(422, 'El nombre debe incluir entre 3 y 50 letras o números.')
    role = Role(code=code, name=data.name, description=data.description, bin_status=1)
    db.add(role)
    try:
        db.flush()
        audit(db, user, 'roles', role.id, 'CREAR_ROL')
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Ya existe un rol con ese nombre, incluso si fue dado de baja.')
    return role_response(role)


@router.put('/roles/{role_id}')
def update_role(role_id: int, data: RoleUpdate, user: CurrentUser, db: DbSession) -> dict:
    authorize_admin(user)
    role = locked_role(db, role_id)
    check_change(db, role, data.version, data.bin_status)
    role.name, role.description, role.bin_status = data.name, data.description, data.bin_status
    role.version += 1
    audit(db, user, 'roles', role.id, 'ACTUALIZAR_ROL')
    save(db, 'Ya existe un rol con ese nombre.')
    return role_response(role)


@router.delete('/roles/{role_id}')
def delete_role(role_id: int, data: VersionRequest, user: CurrentUser, db: DbSession) -> dict:
    authorize_admin(user)
    role = locked_role(db, role_id)
    check_change(db, role, data.version, 2)
    if role.bin_status == 2:
        raise HTTPException(409, 'El rol ya está suspendido. Su registro se conserva.')
    role.bin_status = 2
    role.version += 1
    audit(db, user, 'roles', role.id, 'BAJA_LOGICA_ROL')
    db.commit()
    return {'message': 'Rol suspendido. Su registro se conserva.', 'bin_status': 2}


@router.get('/users')
def list_users(user: CurrentUser, db: DbSession) -> list[dict]:
    authorize_admin(user)
    query = select(User).join(User.state).options(contains_eager(User.state)).where(User.bin_status != 3).order_by(User.username)
    return [dict(id=u.id, username=u.username, full_name=u.full_name, role=u.role,
                 role_id=u.assigned_role.id, role_name=u.assigned_role.name, status=u.state.value)
            for u in db.scalars(query)]


@router.put('/users/{user_id}/role')
def assign_role(user_id: int, data: AssignRole, user: CurrentUser, db: DbSession) -> dict:
    authorize_admin(user)
    role = locked_role(db, data.role_id)
    if role.bin_status != 1:
        raise HTTPException(409, 'Solo se pueden asignar roles activos.')
    target = db.execute(select(User).where(User.id == user_id, User.bin_status != 3).with_for_update()).scalar_one_or_none()
    if target is None:
        raise HTTPException(404, 'La cuenta no existe.')
    if target.id == user.id and role.code != 'ADMINISTRADOR':
        raise HTTPException(409, 'No puedes quitarte el rol administrador de tu sesión actual.')
    target.role = role.code
    audit(db, user, 'users', target.id, 'ASIGNAR_ROL')
    db.commit()
    return {'message': f'Rol {role.name} asignado a {target.username}.'}


@router.post('/users', response_model=UserResponse, status_code=201)
def create_staff(data: StaffAccount, user: CurrentUser, db: DbSession) -> UserResponse:
    authorize_admin(user)
    role = locked_role(db, data.role_id)
    if role.bin_status != 1:
        raise HTTPException(409, 'Solo se pueden asignar roles activos.')
    if len(data.full_name.strip()) < 3:
        raise HTTPException(422, 'El nombre completo debe tener al menos 3 caracteres.')
    target = User(username=data.username, full_name=data.full_name.strip(), email=str(data.email).lower(),
                  password_hash=hash_password(data.password), role=role.code, bin_status=1)
    db.add(target)
    try:
        db.flush()
        audit(db, user, 'users', target.id, 'CREAR_CUENTA_PERSONAL')
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'El usuario o correo ya está registrado.')
    return UserResponse(id=target.id, username=target.username, full_name=target.full_name, email=target.email,
                        role=role.code, role_name=role.name, status='ACTIVO', bin_status=1, active_session=False)
