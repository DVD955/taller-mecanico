"""Publicación de la documentación, separada de las sesiones del taller."""
from hashlib import sha256
import os
from secrets import compare_digest
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.openapi.docs import get_redoc_html
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from .config import Settings

SWAGGER_ASSETS = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.36.0"
SWAGGER_JS_HASH = "sha384-fUpRgC19yPykTqzdrUbdAg8NTiu16NEKf9U12J+IJWCg8/1mEI8f2+PEIz60Wyd+"
SWAGGER_CSS_HASH = "sha384-z/AtSaOHGn5MJ5auAHXUypohywlIWLBZo1jeGmhdpVIbCnFhxAH92cwdV41oyINc"
PRIVATE_HEADERS = {"Cache-Control": "private, no-store", "Vary": "Authorization", "X-Robots-Tag": "noindex"}


def install_api_docs(app: FastAPI, settings: Settings) -> None:
    local = settings.app_env == "development" and not os.getenv("RAILWAY_ENVIRONMENT_ID")
    username = settings.swagger_username
    password = settings.swagger_password.get_secret_value()
    if not local and not (username and username.isascii() and ":" not in username
                          and password.isascii() and len(password) >= 32):
        # La API sigue funcionando si la documentación no está configurada.
        return

    basic = HTTPBasic(realm="Taller Mecanico API", auto_error=False)
    username_digest = sha256(username.encode()).digest()
    password_digest = sha256(password.encode()).digest()

    def require_docs_access(request: Request) -> None:
        if local and request.client and request.client.host in {"127.0.0.1", "::1"}:
            return
        raise HTTPException(404, "Not Found", headers=PRIVATE_HEADERS)

    def require_docs_credentials(
        credentials: Annotated[HTTPBasicCredentials | None, Depends(basic)],
    ) -> None:
        if credentials is not None:
            valid_user = compare_digest(sha256(credentials.username.encode()).digest(), username_digest)
            valid_password = compare_digest(sha256(credentials.password.encode()).digest(), password_digest)
            if valid_user and valid_password:
                return
        raise HTTPException(401, "Credenciales de documentación requeridas.", headers={
            **PRIVATE_HEADERS,
            "WWW-Authenticate": 'Basic realm="Taller Mecanico API"',
        })

    access = [Depends(require_docs_access if local else require_docs_credentials)]

    @app.get("/openapi.json", include_in_schema=False, dependencies=access)
    def openapi_schema() -> JSONResponse:
        return JSONResponse(app.openapi(), headers=PRIVATE_HEADERS)

    @app.get("/docs", include_in_schema=False, dependencies=access)
    def swagger_ui() -> HTMLResponse:
        return HTMLResponse(f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Taller Mecánico API | Swagger UI</title>
  <link rel="stylesheet" href="{SWAGGER_ASSETS}/swagger-ui.css"
        integrity="{SWAGGER_CSS_HASH}" crossorigin="anonymous">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="{SWAGGER_ASSETS}/swagger-ui-bundle.js"
          integrity="{SWAGGER_JS_HASH}" crossorigin="anonymous"></script>
  <script>
    SwaggerUIBundle({{
      url: './openapi.json',
      dom_id: '#swagger-ui',
      presets: [SwaggerUIBundle.presets.apis],
      deepLinking: true,
      filter: true,
      docExpansion: 'list',
      persistAuthorization: false,
      validatorUrl: null
    }});
  </script>
</body>
</html>""", headers=PRIVATE_HEADERS)

    if local:
        @app.get("/redoc", include_in_schema=False, dependencies=access)
        def redoc() -> HTMLResponse:
            response = get_redoc_html(openapi_url="./openapi.json", title="Taller Mecánico API | ReDoc")
            response.headers.update(PRIVATE_HEADERS)
            return response
