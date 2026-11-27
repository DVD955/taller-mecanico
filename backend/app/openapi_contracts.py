"""Contratos de documentación para respuestas y cuerpos que se pasan sin transformar."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ApiError(BaseModel):
    detail: str


class ValidationIssue(BaseModel):
    loc: list[str | int]
    msg: str
    type: str


class ValidationFailure(BaseModel):
    detail: str | list[ValidationIssue]


ERRORS = {
    400: "Solicitud inválida o enlace de recuperación vencido.",
    401: "Credenciales incorrectas o sesión ausente, inválida o expirada.",
    403: "El usuario no tiene permiso para realizar la operación.",
    404: "El registro o el archivo solicitado no existe o no está disponible.",
    409: "Conflicto con el estado actual, versión obsoleta o dato duplicado.",
    413: "La carga supera el tamaño permitido.",
    422: "La solicitud no cumple el formato o las reglas de la operación.",
    503: "Un servicio requerido no está disponible.",
}

AUTH_ERRORS = (401, 403)
GATEWAY_ERRORS = (*AUTH_ERRORS, 503)


def errors(*codes: int) -> dict:
    return {
        code: {"description": ERRORS[code], "model": ValidationFailure if code == 422 else ApiError}
        for code in codes
    }


def result(model, *codes: int, status: int = 200, description: str = "Operación exitosa.") -> dict:
    return {status: {"model": model, "description": description}, **errors(*codes)}


def image_result(*codes: int) -> dict:
    return {
        200: {
            "description": "Archivo de imagen.",
            "content": {
                mime: {"schema": {"type": "string", "format": "binary"}}
                for mime in ("image/jpeg", "image/png", "image/webp")
            },
        },
        **errors(*codes),
    }


def json_body(model: type[BaseModel], example: dict | None = None) -> dict:
    schema = model.model_json_schema()
    definitions = schema.pop("$defs", {})

    def inline(value):
        if isinstance(value, list):
            return [inline(item) for item in value]
        if isinstance(value, dict):
            if "$ref" in value:
                definition = definitions[value["$ref"].removeprefix("#/$defs/")]
                return inline({**definition, **{key: item for key, item in value.items() if key != "$ref"}})
            return {key: inline(item) for key, item in value.items()}
        return value

    media = {"schema": inline(schema)}
    if example is not None:
        media["example"] = example
    return {"requestBody": {"required": True, "content": {"application/json": media}}}


class Message(BaseModel):
    message: str


class StatusMessage(Message):
    bin_status: int


class CatalogStatus(BaseModel):
    id: int
    value: str
    description: str


class RoleDetails(BaseModel):
    id: int
    code: str
    name: str
    description: str
    bin_status: int
    status: str
    version: int


class StaffDetails(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    role_id: int
    role_name: str
    status: str


class PostalSettlementDetails(BaseModel):
    id: int
    postal_code: str
    state: str
    municipality: str
    neighborhood: str


class WorkshopDetails(PostalSettlementDetails):
    name: str
    rfc: str
    email: str
    street: str
    number: str
    bin_status: int
    status: str
    version: int
    has_image: bool


class Address(BaseModel):
    street: str
    number: str
    neighborhood: str
    municipality: str
    state: str


class Contacts(BaseModel):
    email: str | None = None
    mobile: str | None = None
    alternative: str | None = None


class CustomerDraft(BaseModel):
    fullName: str
    address: Address
    contacts: Contacts = Field(description="Indica al menos un medio de contacto.")
    workshopId: int = Field(ge=1, description="ID de un taller activo.")


CUSTOMER_EXAMPLE = {
    "fullName": "Cliente de ejemplo",
    "address": {"street": "Av. Central", "number": "10", "neighborhood": "Centro",
                "municipality": "Cuauhtémoc", "state": "Ciudad de México"},
    "contacts": {"email": "cliente@example.com"},
    "workshopId": 1,
}


class ConfirmCustomer(BaseModel):
    customer: CustomerDraft
    previewToken: str
    confirmed: Literal[True]


class CustomerUpdateDraft(BaseModel):
    customer: CustomerDraft
    version: int = Field(ge=1)


class ConfirmCustomerUpdate(ConfirmCustomer):
    version: int = Field(ge=1)


class DeactivateCustomer(BaseModel):
    version: int = Field(ge=1)
    confirmed: Literal[True]


class CustomerDetails(CustomerDraft):
    id: int
    workshopId: int | None
    workshopName: str | None
    status: str
    fingerprint: str
    version: int


class Page(BaseModel):
    total: int
    page: int
    pageSize: int


class CustomerPage(Page):
    items: list[CustomerDetails]


class CustomerPreview(BaseModel):
    customer: CustomerDetails
    matches: list[CustomerDetails]
    previewToken: str | None = Field(description="Se devuelve null si hay coincidencias.")


class CustomerAudit(BaseModel):
    id: int
    actorId: int
    actorUsername: str
    customerId: int
    occurredAt: datetime
    action: str


class SavedCustomer(BaseModel):
    customer: CustomerDetails
    auditEntry: CustomerAudit


class VehicleDraft(BaseModel):
    vin: str = Field(description="VIN de 17 caracteres para el alta.")
    plate: str = Field(description="Placa mexicana según los formatos admitidos.")
    make: str
    model: str
    year: int = Field(ge=1900)
    version: str
    color: str
    mileage: int | None = Field(default=None, ge=0, le=10_000_000)


VEHICLE_EXAMPLE = {
    "vin": "1HGCM82633A004352", "plate": "ABC-123-D", "make": "Honda", "model": "Accord",
    "year": 2003, "version": "EX", "color": "Gris", "mileage": 0,
}


class ConfirmVehicle(BaseModel):
    vehicle: VehicleDraft
    confirmed: Literal[True]


class VehicleRevision(BaseModel):
    recordVersion: int = Field(ge=1)
    confirmed: Literal[True]


class ChangeVehicleOwner(VehicleRevision):
    customerId: int = Field(ge=1)


class VehicleRecord(VehicleDraft):
    id: int
    customerId: int
    status: str
    recordVersion: int


class VehicleAudit(CustomerAudit):
    vehicleId: int
    previousCustomerId: int | None


class SavedVehicle(BaseModel):
    vehicle: VehicleRecord
    auditEntry: VehicleAudit


class VehicleListItem(BaseModel):
    vehicle: VehicleRecord
    customerName: str
    workshopName: str | None
    photoCount: int


class VehiclePage(Page):
    items: list[VehicleListItem]


class VehiclePhoto(BaseModel):
    id: int
    contentType: str
    sizeBytes: int


class VehicleDetails(BaseModel):
    vehicle: VehicleRecord
    customerName: str
    workshopName: str | None
    photos: list[VehiclePhoto]
    auditEntries: list[VehicleAudit]
