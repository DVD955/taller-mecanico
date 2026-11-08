"""Prueba integrada HTTP del registro, consulta, edición y baja de clientes.

Solo crea usuarios, sesiones y clientes marcados con un UUID de prueba; los limpia
en finally. No cierra ni modifica las sesiones de los usuarios existentes.
"""
import json
import secrets
import uuid
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from sqlalchemy import select, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.database import SessionLocal, engine
from app.models import User, UserRole, UserSession, Workshop
from app.security import create_access_token, hash_password


def call(path, payload=None, token=None, method="POST", port=8002):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    request = Request(f"http://127.0.0.1:{port}" + path, data=json.dumps(payload).encode() if payload is not None else None, headers=headers, method=method)
    try:
        with urlopen(request, timeout=20) as result:
            return result.status, json.loads(result.read())
    except HTTPError as error:
        return error.code, json.loads(error.read())


def run():
    marker = uuid.uuid4().hex
    user_ids = []
    users = {}
    role_states = {}
    count = 0

    def check(condition, message):
        nonlocal count
        assert condition, message
        count += 1
        print("OK:", message)

    customer = {
        "workshopId": None,
        "fullName": "  Cliente   Integracion  ",
        "address": {"street": "Test " + marker, "number": "1", "neighborhood": "Centro", "municipality": "Puebla", "state": "Puebla"},
        "contacts": {"email": marker + "@example.com", "mobile": None, "alternative": None},
    }
    try:
        with SessionLocal() as db:
            workshop = db.scalar(select(Workshop).where(Workshop.bin_status == 1).limit(1))
            assert workshop is not None, 'Se requiere un taller activo.'
            customer['workshopId'] = workshop.id
            for role in UserRole:
                user = User(username="uc_test_" + role.value[:3] + marker[:8], full_name="Prueba UC", role=role,
                            bin_status=1, password_hash=hash_password(secrets.token_urlsafe(32)))
                db.add(user)
                db.flush()
                user_ids.append(user.id)
                role_states[role.value] = user.assigned_role.bin_status
                expires = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=10)
                session = UserSession(user_id=user.id, expires_at=expires)
                db.add(session)
                db.flush()
                user.active_session_id = session.id
                users[role.value] = (user.id, create_access_token(user_id=user.id, session_id=session.id, expires_at=expires))
            db.commit()
        admin_id, admin_token = users["ADMINISTRADOR"]
        receptionist_id, receptionist_token = users["RECEPCIONISTA"]
        if role_states["RECEPCIONISTA"] != 1:
            check(call("/api/customers/preview", customer, receptionist_token)[0] == 401,
                  "HTTP: recepcionista suspendido no accede; se conserva su estado real")
            receptionist_id, receptionist_token = admin_id, admin_token
        operator_name = "recepcionista" if role_states["RECEPCIONISTA"] == 1 else "administrador temporal"
        check(call("/api/customers/preview", customer)[0] == 401, "HTTP: sin sesión recibe 401")
        check(call("/api/customers/preview", customer, users["MECANICO"][1])[0] == 403, "HTTP: mecánico recibe 403")
        invalid = {**customer, "contacts": {"email": "no-valido", "mobile": None, "alternative": None}}
        check(call("/api/customers/preview", invalid, admin_token)[0] == 422, "HTTP: formato inválido recibe 422")
        missing = {**customer, "contacts": {"email": None, "mobile": None, "alternative": None}}
        check(call("/api/customers/preview", missing, admin_token)[0] == 422, "HTTP: sin contactos recibe 422")
        status, preview_admin = call("/api/customers/preview", customer, admin_token)
        check(status == 200 and preview_admin["previewToken"] is not None, "HTTP: administrador puede revisar")
        status, preview = call("/api/customers/preview", customer, receptionist_token)
        check(status == 200 and preview["customer"]["fullName"] == "Cliente Integracion", f"HTTP: {operator_name} y normalización integrados")
        confirmation = {"customer": customer, "previewToken": preview["previewToken"], "confirmed": False}
        check(call("/api/customers", confirmation, receptionist_token)[0] == 422, "HTTP: confirmación obligatoria")
        changed = {**customer, "fullName": "Nombre Modificado"}
        check(call("/api/customers", {**confirmation, "customer": changed, "confirmed": True}, receptionist_token)[0] == 422,
              "HTTP: revisión no permite datos alterados")
        status, saved = call("/api/customers", {**confirmation, "confirmed": True}, receptionist_token)
        check(status == 201 and saved["customer"]["status"] == "ACTIVO", "HTTP: cliente persistido activo")
        check(saved["auditEntry"]["actorId"] == receptionist_id and saved["auditEntry"]["customerId"] == saved["customer"]["id"],
              "HTTP: auditoría identifica al operador y al cliente")
        check(call("/api/customers", {"customer": customer, "previewToken": preview_admin["previewToken"], "confirmed": True}, admin_token)[0] == 409,
              "HTTP: coincidencia posterior a revisión devuelve 409")
        status, duplicate = call("/api/customers/preview", {**customer, "fullName": "Otro Nombre"}, admin_token)
        check(status == 200 and len(duplicate["matches"]) == 1 and duplicate["previewToken"] is None,
              "HTTP: contacto duplicado alerta y bloquea confirmación")
        with engine.connect() as connection:
            total = connection.execute(text("SELECT COUNT(*) FROM customers WHERE email=:email"), {"email": customer["contacts"]["email"]}).scalar_one()
            check(total == 1, "MySQL: solo hay un registro tras reintentar")
        customer_id = saved["customer"]["id"]
        with engine.connect() as connection:
            normalized = connection.execute(text("SELECT c.bin_status,s.valor FROM customers c INNER JOIN status s ON s.id=c.bin_status WHERE c.id=:id"), {"id": customer_id}).one()
            check(normalized.bin_status == 1 and normalized.valor == "activo",
                  "MySQL: cliente guarda solo bin_status y obtiene su estatus del catálogo con INNER JOIN")
        path = f"/api/customers/{customer_id}"
        check(saved['customer']['workshopId'] == customer['workshopId'] and saved['customer']['workshopName'],
              "HTTP: alta asociada a taller y nombre obtenido por JOIN")
        check(call('/api/customers/preview', {**customer, 'workshopId': None}, admin_token)[0] == 422,
              "HTTP: taller obligatorio")
        check(call('/api/customers/preview', {**customer, 'workshopId': 2147483647}, admin_token)[0] == 422,
              "HTTP: taller inexistente bloqueado")
        check(call(path + '/preview', {'customer': {**customer, 'workshopId': 2147483647}, 'version': 1}, admin_token)[0] == 422,
              "HTTP: no se puede cambiar taller al actualizar")
        if role_states['RECEPCIONISTA'] == 1:
            check(call(path + '/preview', {'customer': customer, 'version': 1}, receptionist_token)[0] == 403,
                  "HTTP: recepcionista no edita clientes")
            check(call(path, {'confirmed': True, 'version': 1}, receptionist_token, 'DELETE')[0] == 403,
                  "HTTP: recepcionista no desactiva clientes")
        mechanic_token = users["MECANICO"][1]
        check(call("/api/customers", token=mechanic_token, method="GET")[0] == 403, "HTTP: mecánico no consulta el directorio")
        check(call(path, {}, mechanic_token, "PUT")[0] == 403, "HTTP: mecánico no actualiza clientes")
        check(call(path, {"version": 1, "confirmed": True}, mechanic_token, "DELETE")[0] == 403,
              "HTTP: mecánico no elimina clientes")
        check(call(f"/customers/{customer_id}", token=mechanic_token, method="GET", port=8003)[0] == 403,
              "C#: acceso directo tampoco permite un rol no autorizado")
        status, listing = call("/api/customers?search=" + marker, token=receptionist_token, method="GET")
        check(status == 200 and listing["total"] == 1 and listing["items"][0]["id"] == customer_id,
              f"HTTP: {operator_name} consulta y busca clientes")
        check(call(path, token=admin_token, method="GET")[0] == 200, "HTTP: administrador consulta el detalle")
        check(call(path + "/preview", {"customer": customer, "version": 1}, admin_token)[1]["matches"] == [],
              "HTTP: editar no considera al mismo cliente como duplicado")
        edited = {**customer, "fullName": "Cliente Actualizado"}
        status, edit_preview = call(path + "/preview", {"customer": edited, "version": 1}, admin_token)
        check(status == 200 and edit_preview["previewToken"] is not None, "HTTP: administrador revisa una edición")
        edit_request = {"customer": edited, "version": 1, "previewToken": edit_preview["previewToken"], "confirmed": False}
        check(call(path, edit_request, admin_token, "PUT")[0] == 422, "HTTP: edición exige confirmación")
        check(call(path, {**edit_request, "confirmed": True, "customer": customer}, admin_token, "PUT")[0] == 422,
              "HTTP: edición rechaza datos distintos a la revisión")
        status, updated = call(path, {**edit_request, "confirmed": True}, admin_token, "PUT")
        check(status == 200 and updated["customer"]["version"] == 2 and updated["customer"]["fullName"] == "Cliente Actualizado"
              and updated["auditEntry"]["actorId"] == admin_id, "HTTP: administrador actualiza y queda auditado")
        check(call(path, {**edit_request, "confirmed": True}, admin_token, "PUT")[0] == 409,
              "HTTP: edición con versión antigua no sobrescribe cambios")
        second = {**customer, "fullName": "Segundo Cliente", "address": {**customer["address"], "number": "2"},
                  "contacts": {"email": marker + "second@example.com", "mobile": None, "alternative": None}}
        _, second_preview = call("/api/customers/preview", second, admin_token)
        status, second_saved = call("/api/customers", {"customer": second, "previewToken": second_preview["previewToken"], "confirmed": True}, admin_token)
        check(status == 201, "HTTP: administrador también registra clientes")
        status, collision = call(path + "/preview", {"customer": {**edited, "contacts": second["contacts"]}, "version": 2}, admin_token)
        check(status == 200 and len(collision["matches"]) == 1 and collision["previewToken"] is None,
              "HTTP: edición alerta duplicados de otro cliente")
        admin_edit = {**edited, "address": {**edited["address"], "number": "3"}}
        _, admin_review = call(path + "/preview", {"customer": admin_edit, "version": 2}, admin_token)
        status, admin_updated = call(path, {"customer": admin_edit, "version": 2, "previewToken": admin_review["previewToken"], "confirmed": True}, admin_token, "PUT")
        check(status == 200 and admin_updated["auditEntry"]["actorId"] == admin_id and admin_updated["customer"]["version"] == 3,
              "HTTP: administrador actualiza y queda auditado")
        seed = int(marker[:8], 16)
        serial = seed % 999997 + 1
        plate_number = seed % 9997 + 1
        plate_alphabet = 'ABCDEFGHJKLMNPRSTUVWXYZ'
        plate_prefix = ''.join(plate_alphabet[int(character, 16)] for character in marker[:3])
        vehicle = {'vin': f'WVWZZZ1JZXW{serial:06d}', 'plate': f'{plate_prefix}-{plate_number:04d}',
                   'make': 'Volkswagen', 'model': 'Golf', 'year': 1999, 'version': 'Base', 'color': 'Gris', 'mileage': None}
        vehicle_path = path + '/vehicles'
        check(call(vehicle_path, {'vehicle': vehicle, 'confirmed': True}, mechanic_token)[0] == 403,
              'HTTP: mecánico no registra vehículos')
        check(call(vehicle_path, {'vehicle': {**vehicle, 'vin': 'VININVALIDO'}, 'confirmed': True}, admin_token)[0] == 422,
              'HTTP: VIN inválido bloqueado')
        check(call(vehicle_path, {'vehicle': {**vehicle, 'plate': '??'}, 'confirmed': True}, admin_token)[0] == 422,
              'HTTP: placa inválida bloqueada')
        for bad_vin in ('1HGCM82643A004352', 'WVWZZZ1JZXW00000A', '11111111111111111', '1HGCM82633A00435I'):
            check(call(vehicle_path, {'vehicle': {**vehicle, 'vin': bad_vin}, 'confirmed': True}, admin_token)[0] == 422,
                  'HTTP: VIN con verificador, serie o caracteres incorrectos bloqueado')
        for bad_plate in ('ABCDEFG', '1234567', 'AB12CDE', 'AB-123-CD', 'ABC--123-D', 'ABC-000-D', 'IAB-123-C', 'AB-1234-C'):
            check(call(vehicle_path, {'vehicle': {**vehicle, 'plate': bad_plate}, 'confirmed': True}, admin_token)[0] == 422,
                  'HTTP: placa fuera de los formatos mexicanos de automóvil bloqueada')
        check(call(vehicle_path, {'vehicle': {**vehicle, 'mileage': -1}, 'confirmed': True}, admin_token)[0] == 422,
              'HTTP: kilometraje negativo bloqueado')
        check(call(vehicle_path, {'vehicle': vehicle, 'confirmed': False}, admin_token)[0] == 422,
              'HTTP: confirmar vehículo es obligatorio')
        status, vehicle_saved = call(vehicle_path, {'vehicle': vehicle, 'confirmed': True}, receptionist_token)
        check(status == 201 and vehicle_saved['vehicle']['customerId'] == customer_id
              and vehicle_saved['vehicle']['status'] == 'ACTIVO' and '-' not in vehicle_saved['vehicle']['plate'],
              'HTTP: vehículo activo asociado al cliente; placa normalizada')
        check(call(vehicle_path, {'vehicle': vehicle, 'confirmed': True}, admin_token)[0] == 409,
              'HTTP: no se duplica vehículo por VIN')
        check(call(vehicle_path, {'vehicle': {**vehicle, 'vin': f'WVWZZZ1JZXW{serial + 1:06d}'}, 'confirmed': True}, admin_token)[0] == 409,
              'HTTP: no se duplica vehículo por placa')
        status, registered_vehicles = call(vehicle_path, token=admin_token, method='GET')
        check(status == 200 and len(registered_vehicles) == 1, 'HTTP: detalle consulta vehículos del cliente')
        check(call(path, {"version": 3, "confirmed": False}, admin_token, "DELETE")[0] == 422,
              "HTTP: eliminación exige confirmación")
        check(call(path, {"version": 2, "confirmed": True}, admin_token, "DELETE")[0] == 409,
              "HTTP: eliminación rechaza versión desactualizada")
        status, deleted = call(path, {"version": 3, "confirmed": True}, admin_token, "DELETE")
        check(status == 200 and deleted["customer"]["status"] == "INACTIVO" and deleted["auditEntry"]["actorId"] == admin_id,
              "HTTP: administrador desactiva y queda auditado")
        check(call(vehicle_path, {'vehicle': {**vehicle, 'vin': f'WVWZZZ1JZXW{serial + 2:06d}', 'plate': f'{plate_prefix}{plate_number + 1:04d}'}, 'confirmed': True}, admin_token)[0] == 404,
              'HTTP: cliente dado de baja no recibe vehículos nuevos')
        check(call(path, token=admin_token, method="GET")[0] == 404, "HTTP: cliente eliminado no se abre en el directorio")
        check(call(path, {"version": 4, "confirmed": True}, admin_token, "DELETE")[0] == 404,
              "HTTP: eliminar dos veces no crea otra auditoría")
        second_id = second_saved["customer"]["id"]
        check(call(f"/api/customers/{second_id}", {"version": 1, "confirmed": True}, admin_token, "DELETE")[0] == 200,
              "HTTP: administrador también elimina clientes")
        status, empty_listing = call("/api/customers?search=" + marker, token=admin_token, method="GET")
        check(status == 200 and empty_listing["total"] == 0, "HTTP: los clientes eliminados no aparecen en búsquedas")
        with engine.connect() as connection:
            row = connection.execute(text("SELECT c.bin_status,s.valor,c.deleted_at,c.version FROM customers c INNER JOIN status s ON s.id=c.bin_status WHERE c.id=:id"), {"id": customer_id}).one()
            audits = connection.execute(text("SELECT action,actor_id FROM audit_entries WHERE customer_id=:id ORDER BY id"), {"id": customer_id}).all()
            check(row.bin_status == 2 and row.valor == "suspendido" and row.deleted_at is not None and row.version == 4 and len(audits) == 4
                  and audits[-1].action == "UC-CV-04 DesactivarCliente", "MySQL: baja lógica conserva datos e historial completo")
            vehicle_count = connection.execute(text('SELECT count(*) FROM vehicles WHERE customer_id=:id'), {'id': customer_id}).scalar_one()
            audit_count = connection.execute(text('SELECT count(*) FROM vehicle_audit_entries WHERE customer_id=:id'), {'id': customer_id}).scalar_one()
            check(vehicle_count == audit_count == 1, 'MySQL: baja conserva vehículo y auditoría')
        status, archived_duplicate = call("/api/customers/preview", customer, admin_token)
        check(status == 200 and archived_duplicate["previewToken"] is None,
              "HTTP: clientes dados de baja siguen protegidos contra duplicados")
        with SessionLocal() as db:
            user = db.get(User, admin_id)
            session = db.get(UserSession, user.active_session_id)
            session.ended_at = datetime.now(timezone.utc).replace(tzinfo=None)
            user.active_session_id = None
            db.commit()
        check(call("/api/customers/preview", customer, admin_token)[0] == 401, "HTTP: sesión cerrada pierde acceso")
        print(f"RESULTADO: {count} comprobaciones HTTP/MySQL aprobadas.")
    finally:
        with engine.begin() as connection:
            test_emails = {"email": customer["contacts"]["email"], "second": marker + "second@example.com"}
            connection.execute(text("DELETE a FROM vehicle_audit_entries a JOIN customers c ON c.id=a.customer_id WHERE c.email IN (:email,:second)"), test_emails)
            connection.execute(text("DELETE v FROM vehicles v JOIN customers c ON c.id=v.customer_id WHERE c.email IN (:email,:second)"), test_emails)
            connection.execute(text("DELETE a FROM audit_entries a JOIN customers c ON c.id=a.customer_id WHERE c.email IN (:email,:second)"), test_emails)
            connection.execute(text("DELETE FROM customers WHERE email IN (:email,:second)"), test_emails)
        with SessionLocal() as db:
            for user in db.scalars(select(User).where(User.id.in_(user_ids))):
                user.active_session_id = None
                db.delete(user)
            db.commit()


if __name__ == "__main__":
    run()
