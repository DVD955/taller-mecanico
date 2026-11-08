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

router = APIRouter(prefix="/api/customers", tags=["Gestión de clientes"])


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


@router.post("/preview")
def preview(data: dict, user: CurrentUser, authorization: Annotated[str, Header()]) -> Response:
    return forward("/customers/preview", data, user, authorization)


@router.post("", status_code=201)
def register(data: dict, user: CurrentUser, authorization: Annotated[str, Header()]) -> Response:
    return forward("/customers", data, user, authorization)


@router.get("")
def list_customers(
    user: CurrentUser,
    authorization: Annotated[str, Header()],
    page: int = Query(1, ge=1, le=100_000),
    page_size: int = Query(10, ge=1, le=100),
    search: str = Query("", max_length=120),
) -> Response:
    query = urlencode({"page": page, "pageSize": page_size, "search": search})
    return forward("/customers?" + query, None, user, authorization, "GET", "read")


@router.get("/{customer_id}")
def get_customer(customer_id: int, user: CurrentUser, authorization: Annotated[str, Header()]) -> Response:
    return forward(f"/customers/{customer_id}", None, user, authorization, "GET", "read")


@router.post("/{customer_id}/preview")
def preview_update(customer_id: int, data: dict, user: CurrentUser, authorization: Annotated[str, Header()]) -> Response:
    return forward(f"/customers/{customer_id}/preview", data, user, authorization, operation="update")


@router.put("/{customer_id}")
def update_customer(customer_id: int, data: dict, user: CurrentUser, authorization: Annotated[str, Header()]) -> Response:
    return forward(f"/customers/{customer_id}", data, user, authorization, "PUT", "update")


@router.delete("/{customer_id}")
def delete_customer(customer_id: int, data: dict, user: CurrentUser, authorization: Annotated[str, Header()]) -> Response:
    return forward(f"/customers/{customer_id}", data, user, authorization, "DELETE", "deactivate")


@router.get("/{customer_id}/vehicles")
def list_vehicles(customer_id: int, user: CurrentUser, authorization: Annotated[str, Header()]) -> Response:
    return forward(f"/customers/{customer_id}/vehicles", None, user, authorization, "GET", "read")


@router.post("/{customer_id}/vehicles", status_code=201)
def register_vehicle(customer_id: int, data: dict, user: CurrentUser, authorization: Annotated[str, Header()]) -> Response:
    if "photos" in data:
        raise HTTPException(422, "Adjunta fotografías mediante el formulario de vehículos, no como JSON.")
    return forward(f"/customers/{customer_id}/vehicles", data, user, authorization, operation="vehicle")
