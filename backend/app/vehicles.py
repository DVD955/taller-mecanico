"""Pasarela de vehículos: permisos, formularios y fotografías privadas verificadas."""
import base64
import io
import json
import warnings
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from starlette.datastructures import UploadFile
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.formparsers import MultiPartException

from .customers import ADMIN_ONLY, CUSTOMER_READ, CUSTOMER_WRITE, AuthorizationHeader, forward
from .dependencies import CurrentUser
from .openapi_contracts import (
    GATEWAY_ERRORS, VEHICLE_EXAMPLE, ChangeVehicleOwner, SavedVehicle, VehicleDetails, VehiclePage,
    VehicleRevision, image_result, json_body, result,
)

router = APIRouter(prefix='/api/vehicles', tags=['Administración de vehículos'])
MAX_PHOTO_BYTES = 15_000_000
MAX_PHOTOS = 10
MAX_UPLOAD_BYTES = 151_000_000


def vehicle_form_doc(*, editing: bool = False) -> dict:
    payload = {"vehicle": VEHICLE_EXAMPLE, "confirmed": True}
    if editing:
        payload["recordVersion"] = 1
    schema = {
        "type": "object",
        "required": ["payload"],
        "properties": {
            "payload": {"type": "string", "description": "Texto JSON con los datos y la confirmación.",
                        "example": json.dumps(payload)},
            "photos": {"type": "array", "maxItems": MAX_PHOTOS, "description": "Archivos JPG, PNG o WebP de hasta 15 MB cada uno.",
                       "items": {"type": "string", "format": "binary"}},
        },
    }
    multipart = {"schema": schema, "encoding": {"photos": {"style": "form", "explode": True}}}
    return {"requestBody": {"required": True, "content": {"multipart/form-data": multipart}}}


class VehicleEditInput(BaseModel):
    """Datos completos de edición. El servicio de clientes verifica el VIN registrado."""
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    vin: str = Field(min_length=1, max_length=17)
    plate: str = Field(min_length=2, max_length=20)
    make: str = Field(min_length=1, max_length=60)
    model: str = Field(min_length=1, max_length=60)
    year: int = Field(ge=1900, strict=True)
    version: str = Field(min_length=1, max_length=60)
    color: str = Field(min_length=1, max_length=40)
    mileage: int = Field(ge=0, le=10_000_000, strict=True)

    @field_validator('vin', 'plate', 'make', 'model', 'version', 'color', mode='before')
    @classmethod
    def reject_controls(cls, value: object) -> object:
        if isinstance(value, str) and any(ord(char) < 32 or 127 <= ord(char) <= 159 for char in value):
            raise ValueError('No uses caracteres de control.')
        return value

    @field_validator('year')
    @classmethod
    def validate_year(cls, value: int) -> int:
        if value > datetime.now(timezone.utc).year + 1:
            raise ValueError('El año supera el límite permitido.')
        return value


@asynccontextmanager
async def vehicle_form(request: Request):
    received = 0
    limit_message = 'La carga de fotografías supera el límite permitido.'

    async def receive():
        nonlocal received
        message = await request.receive()
        received += len(message.get('body', b''))
        if received > MAX_UPLOAD_BYTES:
            # MultiPartException también cierra los archivos temporales del parser.
            raise MultiPartException(limit_message)
        return message

    bounded = Request(request.scope, receive=receive)
    try:
        async with bounded.form(max_files=MAX_PHOTOS, max_fields=1, max_part_size=16_384) as form:
            yield form
    except StarletteHTTPException as error:
        if error.status_code == 400:
            if error.detail == limit_message:
                raise HTTPException(413, limit_message)
            raise HTTPException(422, 'Formulario inválido: utiliza un campo de datos y hasta 10 fotos.')
        raise


def authorize_write(user) -> None:
    if user.role not in {'ADMINISTRADOR', 'RECEPCIONISTA'}:
        raise HTTPException(403, 'Solo administrador y recepcionista pueden registrar o actualizar vehículos.')


async def validate_photo(photo: UploadFile) -> dict:
    data = await photo.read(MAX_PHOTO_BYTES + 1)
    if len(data) > MAX_PHOTO_BYTES:
        raise HTTPException(413, 'Cada foto debe pesar como máximo 15 MB.')
    if not data:
        raise HTTPException(422, 'La foto está vacía.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as decoded:
                mime = {'JPEG': 'image/jpeg', 'PNG': 'image/png', 'WEBP': 'image/webp'}.get(decoded.format or '')
                if mime is None or photo.content_type != mime or getattr(decoded, 'n_frames', 1) != 1:
                    raise HTTPException(422, 'Adjunta fotos reales JPG, PNG o WebP, sin animación.')
                decoded.verify()
            # verify comprueba la estructura; load detecta imágenes truncadas.
            with Image.open(io.BytesIO(data)) as decoded:
                decoded.load()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(422, 'El archivo no es una fotografía válida.')
    return {'content': base64.b64encode(data).decode('ascii'), 'contentType': mime}


async def parse_upload(request: Request, editing: bool = False) -> dict:
    length = request.headers.get('content-length')
    if length and (not length.isdigit() or int(length) > MAX_UPLOAD_BYTES):
        raise HTTPException(413, 'La carga de fotografías supera el límite permitido.')
    # Se autoriza antes de analizar archivos; el formulario cierra temporales incluso ante errores.
    async with vehicle_form(request) as form:
        payload = form.get('payload')
        if not isinstance(payload, str) or len(payload) > 16_384:
            raise HTTPException(422, 'Los datos del vehículo son obligatorios o exceden el tamaño permitido.')
        try:
            data = json.loads(payload)
        except (ValueError, TypeError):
            raise HTTPException(422, 'Los datos del vehículo no tienen un formato válido.')
        allowed = {'vehicle', 'confirmed', 'recordVersion'} if editing else {'vehicle', 'confirmed'}
        if not isinstance(data, dict) or set(data) - allowed or not isinstance(data.get('vehicle'), dict):
            raise HTTPException(422, 'Envía únicamente los datos del vehículo y la confirmación.')
        if data.get('confirmed') is not True:
            raise HTTPException(422, 'Confirma la operación del vehículo.')
        if editing and (type(data.get('recordVersion')) is not int or data['recordVersion'] < 1):
            raise HTTPException(422, 'La revisión vigente del vehículo es obligatoria.')
        if editing:
            try:
                data['vehicle'] = VehicleEditInput.model_validate(data['vehicle']).model_dump()
            except ValidationError as error:
                labels = {'vin': 'VIN', 'plate': 'placa', 'make': 'marca', 'model': 'modelo', 'year': 'año',
                          'version': 'versión', 'color': 'color', 'mileage': 'kilometraje'}
                fields = dict.fromkeys(labels.get(str(item['loc'][0]), 'datos no admitidos') for item in error.errors())
                raise HTTPException(422, 'Completa correctamente todos los datos del vehículo. Revisa: ' + ', '.join(fields) + '.')
        photos = []
        for key, value in form.multi_items():
            if key == 'payload':
                continue
            if key != 'photos' or not isinstance(value, UploadFile):
                raise HTTPException(422, 'El formulario solo admite datos del vehículo y fotografías.')
            photos.append(await validate_photo(value))
        data['photos'] = photos
        return data


@router.get('', summary="Buscar y paginar vehículos", description=CUSTOMER_READ,
            responses=result(VehiclePage, *GATEWAY_ERRORS, 422))
def list_vehicles(user: CurrentUser, authorization: AuthorizationHeader,
                  page: int = Query(1, ge=1, le=100_000), page_size: int = Query(10, ge=1, le=100),
                  search: str = Query('', max_length=120), status: str = Query('all', pattern='^(all|active|inactive)$')):
    query = urlencode({'page': page, 'pageSize': page_size, 'search': search, 'status': status})
    return forward('/vehicles?' + query, None, user, authorization, 'GET', 'read')


@router.post('/customer/{customer_id}', status_code=201, summary="Registrar vehículo con fotos opcionales",
             description=f"{CUSTOMER_WRITE} Envía payload como texto JSON y adjunta las fotos como archivos.",
             responses=result(SavedVehicle, *GATEWAY_ERRORS, 404, 409, 413, 422, status=201),
             openapi_extra=vehicle_form_doc())
async def register_vehicle(customer_id: int, request: Request, user: CurrentUser, authorization: AuthorizationHeader):
    authorize_write(user)
    data = await parse_upload(request)
    return await run_in_threadpool(forward, f'/customers/{customer_id}/vehicles', data, user, authorization, operation='vehicle')


@router.get('/{vehicle_id}', summary="Consultar expediente de vehículo",
            description=f"{CUSTOMER_READ} Incluye versión, cliente, metadatos de fotos e historial.",
            responses=result(VehicleDetails, *GATEWAY_ERRORS, 404, 422))
def get_vehicle(vehicle_id: int, user: CurrentUser, authorization: AuthorizationHeader):
    return forward(f'/vehicles/{vehicle_id}', None, user, authorization, 'GET', 'read')


@router.get('/{vehicle_id}/photos/{photo_id}', summary="Obtener una foto privada del vehículo", description=CUSTOMER_READ,
            response_class=Response, responses=image_result(*GATEWAY_ERRORS, 404, 422))
def vehicle_photo(vehicle_id: int, photo_id: int, user: CurrentUser, authorization: AuthorizationHeader):
    return forward(f'/vehicles/{vehicle_id}/photos/{photo_id}', None, user, authorization, 'GET', 'read')


@router.put('/{vehicle_id}', summary="Actualizar los datos y fotos de un vehículo",
            description=(f"{CUSTOMER_WRITE} Incluye la revisión vigente, el VIN registrado y todos los campos, incluido "
                         "el kilometraje. Debe quedar al menos una foto entre las existentes y las nuevas."),
            responses=result(SavedVehicle, *GATEWAY_ERRORS, 404, 409, 413, 422),
            openapi_extra=vehicle_form_doc(editing=True))
async def update_vehicle(vehicle_id: int, request: Request, user: CurrentUser, authorization: AuthorizationHeader):
    authorize_write(user)
    data = await parse_upload(request, editing=True)
    return await run_in_threadpool(forward, f'/vehicles/{vehicle_id}', data, user, authorization, 'PUT', 'vehicle')


@router.delete('/{vehicle_id}', summary="Desactivar un vehículo",
               description=f"{ADMIN_ONLY} Conserva el expediente y el historial.",
               responses=result(SavedVehicle, *GATEWAY_ERRORS, 404, 409, 422),
               openapi_extra=json_body(VehicleRevision, {"recordVersion": 1, "confirmed": True}))
def deactivate_vehicle(vehicle_id: int, data: dict, user: CurrentUser, authorization: AuthorizationHeader):
    return forward(f'/vehicles/{vehicle_id}', data, user, authorization, 'DELETE', 'deactivate')


@router.put('/{vehicle_id}/owner', summary="Cambiar el cliente asociado",
            description=f"{CUSTOMER_WRITE} Envía el ID del nuevo cliente activo y la revisión vigente.",
            responses=result(SavedVehicle, *GATEWAY_ERRORS, 404, 409, 422),
            openapi_extra=json_body(ChangeVehicleOwner, {"customerId": 2, "recordVersion": 1, "confirmed": True}))
def change_owner(vehicle_id: int, data: dict, user: CurrentUser, authorization: AuthorizationHeader):
    return forward(f'/vehicles/{vehicle_id}/owner', data, user, authorization, 'PUT', 'vehicle')
