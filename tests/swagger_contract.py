"""Comprueba el OpenAPI y el acceso a Swagger sin escribir en MySQL."""
from collections import Counter
from datetime import datetime, timedelta, timezone
import io
import json
import os
from secrets import token_urlsafe
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI, Response
from fastapi.testclient import TestClient
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
os.environ.update(
    APP_ENV="development",
    DATABASE_URL="sqlite://",
    SECRET_KEY=token_urlsafe(32),
    SWAGGER_USERNAME="",
    SWAGGER_PASSWORD="",
)
os.environ.pop("RAILWAY_ENVIRONMENT_ID", None)

from app.api_docs import install_api_docs
from app.config import Settings
from app.database import get_db
from app.main import app
from app.models import User
from app.security import create_access_token


local = TestClient(app, client=("127.0.0.1", 50000))
docs = local.get("/docs")
assert docs.status_code == 200 and "SwaggerUIBundle" in docs.text
schema = local.get("/openapi.json").json()
operations = {(path, method.upper()): op for path, methods in schema["paths"].items()
              for method, op in methods.items()}
assert Counter(path.split("/")[2] for path, _ in operations) == {
    "health": 1, "auth": 7, "admin": 8, "postal": 3, "customers": 9, "vehicles": 7, "workshops": 5,
}
assert all(op["summary"] and op.get("description") and op["responses"] for op in operations.values())
assert schema["components"]["securitySchemes"]["SessionBearer"]["scheme"] == "bearer"
assert "security" not in operations["/api/auth/login", "POST"]
assert operations["/api/vehicles", "GET"]["security"] == [{"SessionBearer": []}]
assert all(param["name"].lower() != "authorization" for op in operations.values()
           for param in op.get("parameters", []))
assert local.get("/redoc").status_code == 200
other_host = TestClient(app, client=("192.0.2.10", 50000))
assert all(other_host.get(path).status_code == 404 for path in ("/docs", "/openapi.json", "/redoc"))

sample_password = token_urlsafe(32)


def deployed_client(**options):
    target = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    install_api_docs(target, Settings(_env_file=None, **options))
    return TestClient(target, base_url="https://taller.example.com")


closed = deployed_client(app_env="production")
assert all(closed.get(path).status_code == 404 for path in ("/docs", "/openapi.json", "/redoc"))
short = deployed_client(app_env="production", swagger_username="docs", swagger_password="corta")
assert short.get("/docs").status_code == 404
with patch.dict(os.environ, {"RAILWAY_ENVIRONMENT_ID": "railway-test"}):
    railway = deployed_client(app_env="development", swagger_username="docs", swagger_password=sample_password)
for path in ("/docs", "/openapi.json"):
    assert railway.get(path).status_code == 401
    assert railway.get(path).headers["WWW-Authenticate"].startswith("Basic")
    assert railway.get(path, auth=("docs", "incorrecta")).status_code == 401
    authorized = railway.get(path, auth=("docs", sample_password))
    assert authorized.status_code == 200
    assert "no-store" in authorized.headers["Cache-Control"]
assert railway.get("/redoc", auth=("docs", sample_password)).status_code == 404

# El JWT y el análisis multipart son reales. Se sustituyen la consulta de sesión
# y el envío al servicio .NET para evitar guardar un vehículo de prueba.
assert local.get("/api/auth/me").status_code == 401
session_id = "sesion-prueba-swagger"
user = SimpleNamespace(id=1, username="prueba", full_name="Cuenta de prueba", email=None, role="ADMINISTRADOR",
                       bin_status=1, active_session_id=session_id, state=SimpleNamespace(value="activo"),
                       assigned_role=SimpleNamespace(name="Administrador", bin_status=1))
active_session = SimpleNamespace(ended_at=None)
app.dependency_overrides[get_db] = lambda: SimpleNamespace(get=lambda model, _: user if model is User else active_session)
try:
    token = create_access_token(user_id=1, session_id=session_id,
                                expires_at=datetime.now(timezone.utc) + timedelta(minutes=10))
    headers = {"Authorization": f"Bearer {token}"}
    assert local.get("/api/auth/me", headers=headers).json()["username"] == "prueba"
    upload = operations["/api/vehicles/customer/{customer_id}", "POST"]["requestBody"]["content"]["multipart/form-data"]
    assert upload["schema"]["properties"]["photos"]["items"]["format"] == "binary"
    payload = json.loads(upload["schema"]["properties"]["payload"]["example"])
    photo = io.BytesIO()
    Image.new("RGB", (1, 1)).save(photo, format="PNG")
    with patch("app.vehicles.forward", return_value=Response(status_code=201)) as forward:
        uploaded = local.post("/api/vehicles/customer/1", headers=headers,
                              data={"payload": json.dumps(payload)},
                              files={"photos": ("test.png", photo.getvalue(), "image/png")})
        assert uploaded.status_code == 201, uploaded.text
        assert forward.call_args.args[1]["photos"][0]["contentType"] == "image/png"
finally:
    app.dependency_overrides.clear()

print(f"Swagger verificado: {len(operations)} operaciones, acceso por ambiente, JWT y multipart.")
