"""Pasarela autenticada para registrar, consultar, actualizar y dar de baja clientes."""
import json
import os
from typing import Annotated
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import Response

from .dependencies import CurrentUser
from .openapi_contracts import (
    CUSTOMER_EXAMPLE, GATEWAY_ERRORS, VEHICLE_EXAMPLE, ConfirmCustomer, ConfirmCustomerUpdate,
    ConfirmVehicle, CustomerDetails, CustomerDraft, CustomerPage, CustomerPreview, CustomerUpdateDraft,
    DeactivateCustomer, SavedCustomer, SavedVehicle, VehicleRecord, json_body, result,
)

router = APIRouter(prefix="/api/customers", tags=["Gestión de clientes"])
# El JWT se documenta mediante el esquema de seguridad de CurrentUser.
AuthorizationHeader = Annotated[str, Header(include_in_schema=False)]
CUSTOMER_READ = "Administrador, recepción o secretaría."
CUSTOMER_WRITE = "Administrador o recepción."
CUSTOMER_UPDATE = "Administrador o secretaría."
ADMIN_ONLY = "Solo administrador."


def forward(
    path: str,
    data: dict | None,
    user,
    authorization: str,
    method: str = "POST",
    operation: str = "register",
) -> Response:
    permissions = {
        "read": {"ADMINISTRADOR", "RECEPCIONISTA", "SECRETARIA"},
        "register": {"ADMINISTRADOR", "RECEPCIONISTA"},
        "update": {"ADMINISTRADOR", "SECRETARIA"},
        "deactivate": {"ADMINISTRADOR"},
        "vehicle": {"ADMINISTRADOR", "RECEPCIONISTA"},
    }
    if user.role not in permissions[operation]:
        raise HTTPException(403, "Tu rol no tiene permiso para realizar esta operación.")

    base_url = os.getenv("CUSTOMER_SERVICE_URL", "http://127.0.0.1:8003")
    request = Request(
        base_url.rstrip("/") + path,
        data=json.dumps(data).encode() if data is not None else None,
        headers={"Content-Type": "application/json", "Authorization": authorization},
        method=method,
    )
    try:
        with urlopen(request, timeout=15) as result:
            content_type = result.headers.get("Content-Type", "application/json")
            return Response(
                result.read(),
                status_code=result.status,
                media_type=content_type,
                headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
            )
    except HTTPError as error:
        return Response(error.read(), status_code=error.code, media_type="application/json")
    except (URLError, TimeoutError, OSError):
        raise HTTPException(503, "El módulo de clientes no está disponible. Inicia CustomerService e intenta nuevamente.")


@router.post("/preview", summary="Revisar un cliente antes de registrarlo",
             description=f"{CUSTOMER_WRITE} Devuelve coincidencias y un token temporal para confirmar el alta.",
             responses=result(CustomerPreview, *GATEWAY_ERRORS, 422), openapi_extra=json_body(CustomerDraft, CUSTOMER_EXAMPLE))
def preview(data: dict, user: CurrentUser, authorization: AuthorizationHeader) -> Response:
    return forward("/customers/preview", data, user, authorization)


@router.post("", status_code=201, summary="Registrar cliente",
             description=f"{CUSTOMER_WRITE} Envía los mismos datos de la revisión con su previewToken y confirmed=true.",
             responses=result(SavedCustomer, *GATEWAY_ERRORS, 409, 422, status=201),
             openapi_extra=json_body(ConfirmCustomer, {"customer": CUSTOMER_EXAMPLE, "previewToken": "<token de revisión>", "confirmed": True}))
def register(data: dict, user: CurrentUser, authorization: AuthorizationHeader) -> Response:
    return forward("/customers", data, user, authorization)


@router.get("", summary="Buscar y paginar clientes", description=CUSTOMER_READ,
            responses=result(CustomerPage, *GATEWAY_ERRORS, 422))
def list_customers(user: CurrentUser, authorization: AuthorizationHeader,
                   page: int = Query(1, ge=1, le=100_000), page_size: int = Query(10, ge=1, le=100),
                   search: str = Query("", max_length=120)) -> Response:
    query = urlencode({"page": page, "pageSize": page_size, "search": search})
    return forward("/customers?" + query, None, user, authorization, "GET", "read")


@router.get("/{customer_id}", summary="Consultar un cliente", description=CUSTOMER_READ,
            responses=result(CustomerDetails, *GATEWAY_ERRORS, 404, 422))
def get_customer(customer_id: int, user: CurrentUser, authorization: AuthorizationHeader) -> Response:
    return forward(f"/customers/{customer_id}", None, user, authorization, "GET", "read")


@router.post("/{customer_id}/preview", summary="Revisar una actualización de cliente",
             description=f"{CUSTOMER_UPDATE} Incluye la versión vigente y conserva el taller asociado.",
             responses=result(CustomerPreview, *GATEWAY_ERRORS, 404, 409, 422),
             openapi_extra=json_body(CustomerUpdateDraft, {"customer": CUSTOMER_EXAMPLE, "version": 1}))
def preview_update(customer_id: int, data: dict, user: CurrentUser, authorization: AuthorizationHeader) -> Response:
    return forward(f"/customers/{customer_id}/preview", data, user, authorization, operation="update")


@router.put("/{customer_id}", summary="Actualizar un cliente",
            description=f"{CUSTOMER_UPDATE} Confirma los datos con la misma versión y el token de la revisión.",
            responses=result(SavedCustomer, *GATEWAY_ERRORS, 404, 409, 422),
            openapi_extra=json_body(ConfirmCustomerUpdate, {"customer": CUSTOMER_EXAMPLE, "previewToken": "<token de revisión>",
                                                           "confirmed": True, "version": 1}))
def update_customer(customer_id: int, data: dict, user: CurrentUser, authorization: AuthorizationHeader) -> Response:
    return forward(f"/customers/{customer_id}", data, user, authorization, "PUT", "update")


@router.delete("/{customer_id}", summary="Dar de baja un cliente",
               description=f"{ADMIN_ONLY} Aplica baja lógica con confirmación y versión vigente.",
               responses=result(SavedCustomer, *GATEWAY_ERRORS, 404, 409, 422),
               openapi_extra=json_body(DeactivateCustomer, {"version": 1, "confirmed": True}))
def delete_customer(customer_id: int, data: dict, user: CurrentUser, authorization: AuthorizationHeader) -> Response:
    return forward(f"/customers/{customer_id}", data, user, authorization, "DELETE", "deactivate")


@router.get("/{customer_id}/vehicles", summary="Listar los vehículos de un cliente", description=CUSTOMER_READ,
            responses=result(list[VehicleRecord], *GATEWAY_ERRORS, 404, 422))
def list_vehicles(customer_id: int, user: CurrentUser, authorization: AuthorizationHeader) -> Response:
    return forward(f"/customers/{customer_id}/vehicles", None, user, authorization, "GET", "read")


@router.post("/{customer_id}/vehicles", status_code=201, summary="Registrar vehículo con JSON",
             description=f"{CUSTOMER_WRITE} Para adjuntar fotos usa POST /api/vehicles/customer/{{customer_id}}.",
             responses=result(SavedVehicle, *GATEWAY_ERRORS, 404, 409, 422, status=201),
             openapi_extra=json_body(ConfirmVehicle, {"vehicle": VEHICLE_EXAMPLE, "confirmed": True}))
def register_vehicle(customer_id: int, data: dict, user: CurrentUser, authorization: AuthorizationHeader) -> Response:
    if 'photos' in data:
        raise HTTPException(422, 'Adjunta fotografías mediante el formulario de vehículos, no como JSON.')
    return forward(f"/customers/{customer_id}/vehicles", data, user, authorization, operation="vehicle")
