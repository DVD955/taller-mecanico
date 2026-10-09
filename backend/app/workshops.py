"""Alta y administración de talleres, con dirección SEPOMEX e imagen validada."""
from datetime import datetime
import hashlib
import io
import json
import re
import unicodedata
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, EmailStr, Field, ValidationError, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .administration import VersionRequest, audit, save
from .dependencies import CurrentUser, DbSession
from .models import PostalSettlement, Workshop
from .postal import authorize

router = APIRouter(prefix='/api/workshops', tags=['Administración de talleres'])
MAX_IMAGE_BYTES = 10_000_000
RFC_PATTERN = r'^[A-ZÑ&]{3,4}\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])[A-Z0-9]{3}$'


class WorkshopInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    name: str = Field(min_length=3, max_length=120)
    rfc: str = Field(min_length=12, max_length=13)
    email: EmailStr
    street: str = Field(min_length=1, max_length=150)
    number: str = Field(min_length=1, max_length=20)
    postal_code: str = Field(pattern=r'^\d{5}$')
    neighborhood: str = Field(min_length=1, max_length=100)
    municipality: str = Field(min_length=1, max_length=100)
    state: str = Field(min_length=1, max_length=100)
    version: int | None = Field(default=None, ge=1)

    @field_validator('email')
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()

    @field_validator('name', 'street', 'number', 'neighborhood', 'municipality', 'state')
    @classmethod
    def normalize(cls, value: str) -> str:
        if any(unicodedata.category(c) == 'Cc' for c in value):
            raise ValueError('No uses caracteres de control.')
        return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', value))

    @field_validator('rfc')
    @classmethod
    def validate_rfc(cls, value: str) -> str:
        value = value.upper()
        if not re.fullmatch(RFC_PATTERN, value):
            raise ValueError('RFC inválido: utiliza 12 o 13 caracteres con homoclave.')
        date = value[-9:-3]
        try:
            datetime(2000 + int(date[:2]), int(date[2:4]), int(date[4:]))
        except ValueError:
            raise ValueError('La fecha incluida en el RFC no es válida.')
        return value


def parse_payload(payload: str) -> WorkshopInput:
    if len(payload) > 10_000:
        raise HTTPException(422, 'Los datos del taller exceden el tamaño permitido.')
    try:
        return WorkshopInput.model_validate_json(payload)
    except ValidationError as error:
        messages = [f'{".".join(str(x) for x in item["loc"])}: {item["msg"]}' for item in error.errors()]
        raise HTTPException(422, '; '.join(messages))


async def validate_image(image: UploadFile | None) -> tuple[bytes | None, str | None]:
    if image is None:
        return None, None
    try:
        data = await image.read(MAX_IMAGE_BYTES + 1)
        if len(data) > MAX_IMAGE_BYTES:
            raise HTTPException(413, 'La imagen no debe superar 10 MB.')
        if not data:
            raise HTTPException(422, 'La imagen está vacía.')
        with Image.open(io.BytesIO(data)) as decoded:
            formats = {'JPEG': 'image/jpeg', 'PNG': 'image/png', 'WEBP': 'image/webp'}
            mime = formats.get(decoded.format or '')
            if mime is None or image.content_type != mime:
                raise HTTPException(422, 'Sube una imagen real JPG, PNG o WebP.')
            decoded.verify()
        return data, mime
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise HTTPException(422, 'El archivo no es una imagen válida.')
    finally:
        await image.close()


def validate_address(db, data: WorkshopInput) -> None:
    exists = db.scalar(select(PostalSettlement.id).where(
        PostalSettlement.postal_code == data.postal_code, PostalSettlement.state == data.state,
        PostalSettlement.municipality == data.municipality, PostalSettlement.neighborhood == data.neighborhood).limit(1))
    if exists is None:
        raise HTTPException(422, 'El código postal no coincide con el estado, municipio y colonia seleccionados.')


def fingerprint(data: WorkshopInput) -> str:
    values = [data.name, data.street, data.number, data.postal_code]
    normalized = [unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode().upper() for value in values]
    return hashlib.sha256(json.dumps(normalized, ensure_ascii=True).encode()).hexdigest()


def workshop_response(workshop: Workshop) -> dict:
    return dict(id=workshop.id, name=workshop.name, rfc=workshop.rfc, email=workshop.email or '', street=workshop.street,
                number=workshop.number, postal_code=workshop.postal_code, neighborhood=workshop.neighborhood,
                municipality=workshop.municipality, state=workshop.state, bin_status=workshop.bin_status,
                status=workshop.status_record.value, version=workshop.version, has_image=workshop.image is not None)


def get_workshop(db, workshop_id: int, lock: bool = False) -> Workshop:
    query = select(Workshop).where(Workshop.id == workshop_id, Workshop.bin_status != 3)
    if lock:
        query = query.with_for_update()
    workshop = db.scalar(query)
    if workshop is None:
        raise HTTPException(404, 'El taller no existe o fue dado de baja.')
    return workshop


@router.get('')
def list_workshops(user: CurrentUser, db: DbSession) -> list[dict]:
    authorize(user)
    return [workshop_response(row) for row in db.scalars(select(Workshop).where(Workshop.bin_status != 3).order_by(Workshop.name))]


@router.post('', status_code=201)
async def register_workshop(user: CurrentUser, db: DbSession,
                            payload: Annotated[str, Form()], image: Annotated[UploadFile | None, File()] = None) -> dict:
    authorize(user)
    data = parse_payload(payload)
    if data.version is not None:
        raise HTTPException(422, 'El alta no utiliza una versión anterior.')
    validate_address(db, data)
    if image is None:
        raise HTTPException(422, 'Adjunta una imagen del taller de hasta 10 MB.')
    image_data, image_type = await validate_image(image)
    workshop = Workshop(**data.model_dump(exclude={'version'}), identity_fingerprint=fingerprint(data),
                        image=image_data, image_type=image_type, bin_status=1)
    db.add(workshop)
    try:
        db.flush()
        audit(db, user, 'workshops', workshop.id, 'REGISTRAR_TALLER')
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'El RFC o el taller con esa dirección ya está registrado, incluso si fue dado de baja.')
    return workshop_response(workshop)


@router.put('/{workshop_id}')
async def update_workshop(workshop_id: int, user: CurrentUser, db: DbSession,
                          payload: Annotated[str, Form()], image: Annotated[UploadFile | None, File()] = None) -> dict:
    authorize(user)
    data = parse_payload(payload)
    workshop = get_workshop(db, workshop_id, True)
    if data.version != workshop.version:
        raise HTTPException(409, 'El taller cambió. Actualiza el listado antes de guardar.')
    validate_address(db, data)
    image_data, image_type = await validate_image(image)
    for key, value in data.model_dump(exclude={'version'}).items():
        setattr(workshop, key, value)
    workshop.identity_fingerprint = fingerprint(data)
    workshop.version += 1
    if image_data is not None:
        workshop.image, workshop.image_type = image_data, image_type
    audit(db, user, 'workshops', workshop.id, 'ACTUALIZAR_TALLER')
    save(db, 'El RFC o el taller con esa dirección ya está registrado.')
    return workshop_response(workshop)


@router.delete('/{workshop_id}')
def delete_workshop(workshop_id: int, data: VersionRequest, user: CurrentUser, db: DbSession) -> dict:
    authorize(user)
    workshop = get_workshop(db, workshop_id, True)
    if data.version != workshop.version:
        raise HTTPException(409, 'El taller cambió. Actualiza el listado.')
    workshop.bin_status = 3
    workshop.version += 1
    audit(db, user, 'workshops', workshop.id, 'BAJA_LOGICA_TALLER')
    db.commit()
    return {'message': 'Taller dado de baja. Sus datos se conservan.', 'bin_status': 3}


@router.get('/{workshop_id}/image')
def workshop_image(workshop_id: int, user: CurrentUser, db: DbSession) -> Response:
    authorize(user)
    workshop = get_workshop(db, workshop_id)
    if workshop.image is None:
        raise HTTPException(404, 'El taller no tiene imagen.')
    return Response(workshop.image, media_type=workshop.image_type,
                    headers={'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff'})
