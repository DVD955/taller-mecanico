"""Verifica permisos, duplicados, imágenes y baja lógica con datos aislados."""
from datetime import datetime, timedelta
import asyncio
import io
import json
from pathlib import Path
import secrets
import sys
import uuid

import httpx
from fastapi import UploadFile
from PIL import Image
from sqlalchemy import delete, select, func
from starlette.datastructures import Headers

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.database import SessionLocal
from app.models import AdministrationAudit, PostalMunicipality, PostalSettlement, PostalState, Role, Status, User, UserSession, Workshop
from app.security import create_access_token, hash_password
from app.workshops import validate_image


def run():
    marker = uuid.uuid4().hex[:12]
    users, roles, workshops, results = [], [], [], []
    client = httpx.Client(base_url='http://127.0.0.1:8002', timeout=45)

    def check(condition, label):
        if not condition:
            raise AssertionError(label)
        results.append(label)
        print('OK:', label, flush=True)

    def call(method, path, data=None, token=None, files=None):
        headers = {'Authorization': f'Bearer {token}'} if token else {}
        if files is not None:
            return client.request(method, path, data={'payload': json.dumps(data)}, files=files, headers=headers)
        return client.request(method, path, json=data, headers=headers)

    tokens = {}
    role_states = {}
    try:
        with SessionLocal.begin() as db:
            for code in ('ADMINISTRADOR', 'RECEPCIONISTA'):
                user = User(username='test_' + code[:3] + marker, full_name='Prueba aislada',
                            password_hash=hash_password(secrets.token_urlsafe(20)), role=code,
                            bin_status=1)
                db.add(user); db.flush(); users.append(user.id)
                role_states[code] = user.assigned_role.bin_status
                expiry = datetime.utcnow() + timedelta(minutes=20)
                session = UserSession(user_id=user.id, expires_at=expiry)
                db.add(session); db.flush(); user.active_session_id = session.id
                tokens[code] = create_access_token(user_id=user.id, session_id=session.id, expires_at=expiry)
        admin, reception = tokens['ADMINISTRADOR'], tokens['RECEPCIONISTA']
        reception_active = role_states['RECEPCIONISTA'] == 1
        operator = reception if reception_active else admin
        operator_name = 'Recepcionista' if reception_active else 'Administrador temporal'
        if not reception_active:
            check(call('GET', '/api/auth/me', token=reception).status_code == 401,
                  'Recepcionista suspendido pierde acceso sin modificar su estado real')
        payload = dict(username='guest_' + marker, full_name='Invitado de prueba',
                       email=marker + '@example.com', password=secrets.token_urlsafe(16))
        response = call('POST', '/api/auth/register', payload)
        check(response.status_code == 201 and response.json()['role'] == 'INVITADO', 'Registro público crea únicamente Invitado')
        guest_id = response.json()['id']; users.append(guest_id)
        with SessionLocal() as db:
            check(db.get(User, guest_id).password_hash.startswith('$argon2'), 'La contraseña se almacena con Argon2')
            normalized = db.execute(select(User.id, User.bin_status, Status.value).join(User.state).where(User.id == guest_id)).one()
            check(normalized.id == guest_id and normalized.bin_status == 1 and normalized.value == 'activo',
                  'Usuario guarda solo bin_status y obtiene su estatus del catálogo mediante INNER JOIN')
        check(call('POST', '/api/auth/register', payload).status_code == 409, 'Cuenta duplicada rechazada')
        check(call('POST', '/api/auth/register', {**payload, 'role': 'ADMINISTRADOR'}).status_code == 422, 'No se puede inyectar un rol en el registro público')
        login = call('POST', '/api/auth/login', dict(username=payload['username'], password=payload['password']))
        check(login.status_code == 200, 'Invitado puede iniciar sesión')
        guest = login.json()['access_token']
        check(call('POST', '/api/auth/login', dict(username=payload['username'], password=payload['password'])).status_code == 409, 'Se conserva el control de sesión única')
        check(call('GET', '/api/admin/roles').status_code == 401, 'Administración requiere sesión')
        check(call('GET', '/api/admin/roles', token=guest).status_code == 403, 'Invitado no administra roles')
        check(call('POST', '/api/admin/roles', {'name': 'Prueba ' + marker, 'description': 'Descripción de prueba'}, reception).status_code == (403 if reception_active else 401),
              'Recepcionista no crea roles' if reception_active else 'Recepcionista suspendido tampoco accede a crear roles')
        created = call('POST', '/api/admin/roles', {'name': 'Prueba ' + marker}, admin)
        check(created.status_code == 201, 'Administrador crea roles')
        role = created.json(); roles.append(role['id'])
        check(role['description'] == '', 'Descripción del rol es opcional')
        check(call('POST', '/api/admin/roles', {'name': role['name'].upper(), 'description': 'Duplicado'}, admin).status_code == 409, 'Rol duplicado normalizado rechazado')
        changed = call('PUT', f'/api/admin/roles/{role["id"]}', dict(name='Renombrado ' + marker, description='Nueva descripción', bin_status=1, version=role['version']), admin)
        check(changed.status_code == 200 and changed.json()['version'] == 2, 'Actualizar rol incrementa versión')
        check(changed.json()['name'] == 'Renombrado ' + marker and changed.json()['code'] == role['code'], 'Cambiar nombre del rol conserva su código interno y sus permisos')
        role = changed.json()
        check(call('PUT', f'/api/admin/roles/{role["id"]}', dict(name='Administrador', description=role['description'], bin_status=1, version=role['version']), admin).status_code == 409, 'Cambiar nombre no permite duplicar otro rol')
        check(call('PUT', f'/api/admin/roles/{role["id"]}', dict(name=role['name'], description='Anterior', bin_status=1, version=1), admin).status_code == 409, 'Versión anterior no sobrescribe un rol')
        check(call('PUT', f'/api/admin/users/{guest_id}/role', {'role_id': role['id']}, reception).status_code == (403 if reception_active else 401),
              'Solo administrador asigna roles' if reception_active else 'Recepcionista suspendido no puede asignar roles')
        check(call('PUT', f'/api/admin/users/{guest_id}/role', {'role_id': role['id']}, admin).status_code == 200, 'Administrador asigna rol')
        suspended = call('PUT', f'/api/admin/roles/{role["id"]}', dict(name=role['name'], description=role['description'], bin_status=2, version=role['version']), admin)
        check(suspended.status_code == 200 and suspended.json()['bin_status'] == 2 and suspended.json()['status'] == 'suspendido', 'Administrador suspende un rol sin borrar sus cuentas asociadas')
        role = suspended.json()
        check(call('GET', '/api/auth/me', token=guest).status_code == 401, 'Una sesión abierta pierde acceso mientras su rol está suspendido')
        check(call('POST', '/api/auth/login', dict(username=payload['username'], password=payload['password'])).status_code == 403, 'Un rol suspendido impide nuevos inicios de sesión')
        check(call('PUT', f'/api/admin/users/{guest_id}/role', {'role_id': role['id']}, admin).status_code == 409, 'No se pueden asignar roles suspendidos')
        reactivated = call('PUT', f'/api/admin/roles/{role["id"]}', dict(name=role['name'], description=role['description'], bin_status=1, version=role['version']), admin)
        check(reactivated.status_code == 200 and reactivated.json()['bin_status'] == 1, 'Administrador puede reactivar el mismo rol conservado')
        role = reactivated.json()
        catalog = call('GET', '/api/admin/roles', token=admin).json()
        guest_role = next(item for item in catalog if item['code'] == 'INVITADO')
        check(call('PUT', f'/api/admin/users/{guest_id}/role', {'role_id': guest_role['id']}, admin).status_code == 200, 'Reasignación de cuenta a Invitado')
        removed = call('DELETE', f'/api/admin/roles/{role["id"]}', {'version': role['version']}, admin)
        check(removed.status_code == 200 and removed.json()['bin_status'] == 2, 'Eliminar rol aplica SoftDeleted: Activo 1 a Suspendido 2')
        with SessionLocal() as db:
            check(db.get(Role, role['id']).bin_status == 2, 'El rol eliminado se conserva con referencia a status 2')
            check(len(db.scalars(select(AdministrationAudit).where(AdministrationAudit.entity == 'roles', AdministrationAudit.entity_id == role['id'], AdministrationAudit.action == 'BAJA_LOGICA_ROL')).all()) == 1, 'SoftDeleted del rol deja una auditoría sin borrar el registro')
        listed = next(item for item in call('GET', '/api/admin/roles', token=admin).json() if item['id'] == role['id'])
        check(listed['status'] == 'suspendido', 'INNER JOIN del catálogo permite consultar el rol suspendido con su estatus')
        check(call('DELETE', f'/api/admin/roles/{role["id"]}', {'version': listed['version']}, admin).status_code == 409, 'Repetir eliminación de rol no genera otra suspensión')
        check(call('POST', '/api/admin/roles', {'name': role['name'], 'description': 'Duplicado después de baja'}, admin).status_code == 409, 'La baja no permite recrear un rol duplicado')
        status = call('GET', '/api/admin/status', token=admin).json()
        check(any(item['id'] == 1 and item['value'] == 'activo' and item['description'] for item in status)
              and any(item['id'] == 2 and item['value'] == 'suspendido' and item['description'] for item in status), 'Tabla de estatus contiene ID 1 activo e ID 2 suspendido, ambos con descripción')
        admin_role = next(item for item in catalog if item['code'] == 'ADMINISTRADOR')
        check(call('DELETE', f'/api/admin/roles/{admin_role["id"]}', {'version': admin_role['version']}, admin).status_code == 409, 'Administrador protegido para no bloquear el acceso a la configuración')
        staff_payload = dict(username='staff_' + marker, full_name='Personal prueba', email='staff' + marker + '@example.com', password=secrets.token_urlsafe(16), role_id=guest_role['id'])
        check(call('POST', '/api/admin/users', staff_payload, guest).status_code == 403, 'Invitado no crea cuentas de personal')
        staff = call('POST', '/api/admin/users', staff_payload, admin)
        check(staff.status_code == 201, 'Administrador puede crear cuenta de personal')
        users.append(staff.json()['id'])
        check(call('POST', '/api/admin/users', staff_payload, admin).status_code == 409, 'No se duplica cuenta de personal')
        check(call('GET', '/api/workshops', token=guest).status_code == 403, 'Invitado no accede a talleres')
        check(call('GET', '/api/customers', token=guest).status_code == 403, 'Invitado no administra clientes')
        states = call('GET', '/api/postal/states', token=operator)
        check(states.status_code == 200 and len(states.json()) == 32, 'Catálogo postal cubre las 32 entidades')
        with SessionLocal() as db:
            check(db.scalar(select(func.count()).select_from(PostalMunicipality).join(PostalMunicipality.state_record)) > 2400
                  and db.scalar(select(func.count()).select_from(PostalSettlement).where(PostalSettlement.municipality_id.is_(None))) == 0,
                  'Catálogo nacional relacionado: estados, municipios y asentamientos sin referencias pendientes')
        settlements = call('GET', '/api/postal/settlements?postal_code=06600', token=admin)
        check(settlements.status_code == 200 and bool(settlements.json()), 'Buscar CP devuelve colonia, municipio y estado')
        multiple = call('GET', '/api/postal/settlements?postal_code=97130', token=admin)
        check(multiple.status_code == 200 and len(multiple.json()) > 1
              and all(item['state'] == 'Yucatán' and item['municipality'] == 'Mérida' and item['postal_code'] == '97130' for item in multiple.json()),
              'CP con varias colonias devuelve todas las alternativas y su dirección coherente')
        check(call('GET', '/api/postal/settlements?postal_code=99999', token=admin).status_code == 404,
              'CP inexistente devuelve 404, sin inventar una dirección')
        address = settlements.json()[0]
        municipalities = client.get('/api/postal/municipalities', params={'state': address['state']}, headers={'Authorization': f'Bearer {operator}'})
        check(municipalities.status_code == 200 and address['municipality'] in municipalities.json(), 'Estado devuelve su catálogo de municipios relacionados')
        manual = client.get('/api/postal/settlements', params={'state': address['state'], 'municipality': address['municipality']}, headers={'Authorization': f'Bearer {operator}'})
        check(manual.status_code == 200 and any(item['postal_code'] == address['postal_code'] and item['neighborhood'] == address['neighborhood'] for item in manual.json()), 'Búsqueda inversa devuelve el CP de la colonia')
        workshop_data = {key: address[key] for key in ('postal_code', 'state', 'municipality', 'neighborhood')}
        workshop_data.update(name='Taller prueba ' + marker, rfc='ABC001231' + marker[:3].upper(), email='taller' + marker + '@example.com', street='Calle prueba ' + marker, number='1')
        check(call('POST', '/api/workshops', workshop_data, guest, files={'image': ('x.png', b'x', 'image/png')}).status_code == 403, 'Invitado no registra talleres')
        check(call('POST', '/api/workshops', {**workshop_data, 'rfc': 'ABC001332ABC'}, admin, files={'image': ('x.png', b'x', 'image/png')}).status_code == 422, 'RFC inválido rechazado')
        check(call('POST', '/api/workshops', {**workshop_data, 'rfc': 'ABC000231ABC'}, admin, files={'image': ('x.png', b'x', 'image/png')}).status_code == 422, 'RFC con formato correcto pero fecha inexistente es rechazado')
        check(call('POST', '/api/workshops', {**workshop_data, 'postal_code': '99999'}, admin, files={'image': ('x.png', b'x', 'image/png')}).status_code == 422, 'Dirección incoherente rechazada')
        check(call('POST', '/api/workshops', workshop_data, admin, files={'image': ('x.png', b'<svg/>', 'image/png')}).status_code == 422, 'Archivo disfrazado de imagen rechazado')
        check(call('POST', '/api/workshops', workshop_data, admin, files={'image': ('x.png', b'x' * 10_000_001, 'image/png')}).status_code == 413, 'Imagen de 10 MB más un byte rechazada en backend')
        output = io.BytesIO(); Image.new('RGB', (8, 8), '#2F4F4F').save(output, format='PNG')
        picture = output.getvalue()
        # Comprueba el límite inclusive con una imagen PNG válida y relleno final.
        boundary = picture + b'\0' * (10_000_000 - len(picture))
        upload = UploadFile(io.BytesIO(boundary), filename='limite.png', headers=Headers({'content-type': 'image/png'}))
        check(len(asyncio.run(validate_image(upload))[0]) == 10_000_000, 'Imagen real de exactamente 10 MB es admitida')
        check(call('POST', '/api/workshops', workshop_data, admin, files={}).status_code == 422, 'Fotografía obligatoria para registrar taller')
        check(call('POST', '/api/workshops', {**workshop_data, 'email': 'correo-invalido'}, admin, files={'image': ('taller.png', picture, 'image/png')}).status_code == 422, 'Correo de contacto inválido rechazado')
        created = call('POST', '/api/workshops', workshop_data, operator, files={'image': ('taller.png', picture, 'image/png')})
        check(created.status_code == 201 and created.json()['has_image'], f'{operator_name} registra taller con imagen real')
        workshop = created.json(); workshops.append(workshop['id'])
        check(workshop['email'] == workshop_data['email'], 'Correo de contacto del taller persistido')
        check(call('POST', '/api/workshops', workshop_data, admin, files={'image': ('taller.png', picture, 'image/png')}).status_code == 409, 'Taller duplicado rechazado')
        check(call('POST', '/api/workshops', {**workshop_data, 'name': 'Otro taller ' + marker, 'number': '2'}, admin, files={'image': ('taller.png', picture, 'image/png')}).status_code == 409, 'Un RFC repetido se rechaza aunque cambien nombre y domicilio')
        different_rfc = 'XYZ001231' + marker[:3].upper()
        check(call('POST', '/api/workshops', {**workshop_data, 'rfc': different_rfc}, admin, files={'image': ('taller.png', picture, 'image/png')}).status_code == 409, 'La misma identidad de taller se rechaza aunque cambie el RFC')
        image = call('GET', f'/api/workshops/{workshop["id"]}/image', token=admin)
        check(image.status_code == 200 and image.content == picture, 'Imagen almacenada en MySQL y consultable con permiso')
        changed = call('PUT', f'/api/workshops/{workshop["id"]}', {**workshop_data, 'name': workshop_data['name'] + ' actualizado', 'version': 1}, admin, files={})
        check(changed.status_code == 200 and changed.json()['version'] == 2 and changed.json()['has_image'], 'Actualizar taller conserva imagen e incrementa versión')
        check(call('DELETE', f'/api/workshops/{workshop["id"]}', {'version': 1}, operator).status_code == 409, 'Baja con versión anterior rechazada')
        check(call('DELETE', f'/api/workshops/{workshop["id"]}', {'version': 2}, operator).status_code == 200, f'{operator_name} da de baja taller')
        with SessionLocal() as db:
            stored = db.get(Workshop, workshop['id'])
            check(stored.bin_status == 3 and stored.image == picture, 'Baja conserva el taller, su imagen y estatus 3')
            check(len(db.scalars(select(AdministrationAudit).where(AdministrationAudit.entity == 'workshops', AdministrationAudit.entity_id == workshop['id'])).all()) == 3, 'Alta, actualización y baja tienen auditoría')
        check(call('POST', '/api/workshops', workshop_data, admin, files={'image': ('taller.png', picture, 'image/png')}).status_code == 409, 'Taller dado de baja no se recrea como duplicado')
        check(call('POST', '/api/auth/logout', token=guest).status_code == 204, 'Invitado puede cerrar sesión')
        (ROOT / 'analisis' / 'verificacion-integracion.json').write_text(json.dumps({'passed': len(results), 'checks': results}, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'Pruebas completadas: {len(results)}.', flush=True)
    finally:
        client.close()
        # Elimina exclusivamente los recursos UUID creados por esta prueba.
        with SessionLocal.begin() as db:
            db.execute(delete(AdministrationAudit).where(AdministrationAudit.actor_id.in_(users)))
            db.execute(delete(Workshop).where(Workshop.id.in_(workshops)))
            db.execute(delete(UserSession).where(UserSession.user_id.in_(users)))
            db.execute(delete(User).where(User.id.in_(users)))
            db.execute(delete(Role).where(Role.id.in_(roles)))


if __name__ == '__main__':
    run()
