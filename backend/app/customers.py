"""Pasarela autenticada para registrar, consultar, actualizar y dar de baja clientes."""
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from .dependencies import CurrentUser
from .models import UserRole
from typing import Annotated
from fastapi import Header

router = APIRouter(prefix="/api/customers", tags=["Gestión de clientes"])


def forward(path: str, data: dict | None, user, authorization: str, method: str = "POST") -> Response:
    if user.role not in (UserRole.ADMINISTRADOR, UserRole.RECEPCIONISTA):
        raise HTTPException(403, "Solo administradores y recepcionistas pueden gestionar clientes.")
    request = Request("http://127.0.0.1:8003" + path, data=json.dumps(data).encode() if data is not None else None,
                      headers={"Content-Type": "application/json", "Authorization": authorization}, method=method)
    try:
        with urlopen(request, timeout=15) as result:
            return Response(result.read(), status_code=result.status, media_type="application/json")
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
def list_customers(user: CurrentUser, authorization: Annotated[str, Header()],
                   page: int = Query(1, ge=1, le=100_000), page_size: int = Query(10, ge=1, le=100),
                   search: str = Query("", max_length=120)) -> Response:
    query = urlencode({"page": page, "pageSize": page_size, "search": search})
    return forward("/customers?" + query, None, user, authorization, "GET")


@router.get("/{customer_id}")
def get_customer(customer_id: int, user: CurrentUser, authorization: Annotated[str, Header()]) -> Response:
    return forward(f"/customers/{customer_id}", None, user, authorization, "GET")


@router.post("/{customer_id}/preview")
def preview_update(customer_id: int, data: dict, user: CurrentUser, authorization: Annotated[str, Header()]) -> Response:
    return forward(f"/customers/{customer_id}/preview", data, user, authorization)


@router.put("/{customer_id}")
def update_customer(customer_id: int, data: dict, user: CurrentUser, authorization: Annotated[str, Header()]) -> Response:
    return forward(f"/customers/{customer_id}", data, user, authorization, "PUT")


@router.delete("/{customer_id}")
def delete_customer(customer_id: int, data: dict, user: CurrentUser, authorization: Annotated[str, Header()]) -> Response:
    return forward(f"/customers/{customer_id}", data, user, authorization, "DELETE")
