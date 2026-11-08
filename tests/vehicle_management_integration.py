"""UC-CV-06..16 con fixtures UUID; nunca modifica cuentas o sesiones existentes."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import secrets
import sys
import uuid

import httpx
from PIL import Image
from sqlalchemy import bindparam, select, text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.database import SessionLocal, engine
from app.models import Role, User, UserRole, UserSession, Workshop
from app.security import create_access_token, hash_password


def run():
    marker = uuid.uuid4().hex
    user_ids, customer_ids, tokens, role_states = [], [], {}, {}
    checks = 0
    client = httpx.Client(base_url='http://127.0.0.1:8002', timeout=120)

    def check(condition, label):
        nonlocal checks
        assert condition, label
        checks += 1
        print('OK:', label, flush=True)

    def call(method, path, data=None, role='ADMINISTRADOR', photos=None, direct=False):
        headers = {'Authorization': 'Bearer ' + tokens[role]} if role else {}
        path = 'http://127.0.0.1:8003' + path if direct else path
        if photos is not None:
            # Campo dummy para conservar multipart aun cuando no hay fotografías.
            fields = [('payload', (None, json.dumps(data)))] + [('photos', (name, content, mime)) for name, content, mime in photos]
            return client.request(method, path, files=fields, headers=headers)
        return client.request(method, path, json=data, headers=headers)

    def photo(format='PNG'):
        output = io.BytesIO()
        Image.new('RGB', (5, 5), '#2F4F4F').save(output, format)
        return output.getvalue()

    try:
        with SessionLocal.begin() as db:
            workshop = db.scalar(select(Workshop).where(Workshop.bin_status == 1).limit(1))
            assert workshop is not None, 'Se requiere un taller activo para los fixtures.'
            workshop_id = workshop.id
            for role in [item.value for item in UserRole] + ['SECRETARIA']:
                if db.scalar(select(Role.id).where(Role.code == role)) is None:
                    continue
                user = User(username='vid_' + role[:3] + marker[:10], full_name='Prueba video ' + marker[:6],
                            role=role, bin_status=1, password_hash=hash_password(secrets.token_urlsafe(24)))
                db.add(user); db.flush(); user_ids.append(user.id)
                role_states[role] = user.assigned_role.bin_status
                expires = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=20)
                session = UserSession(user_id=user.id, expires_at=expires)
                db.add(session); db.flush(); user.active_session_id = session.id
                tokens[role] = create_access_token(user_id=user.id, session_id=session.id, expires_at=expires)
        for index in range(2):
            customer = {'workshopId': workshop_id, 'fullName': 'Cliente Video Prueba ' + ('Uno' if index == 0 else 'Dos'),
                        'address': dict(street='Prueba ' + marker, number=str(index + 1), neighborhood='Centro', municipality='Puebla', state='Puebla'),
                        'contacts': dict(email=f'{marker}{index}@example.com', mobile=None, alternative=None)}
            preview = call('POST', '/api/customers/preview', customer)
            assert preview.status_code == 200, preview.text
            saved = call('POST', '/api/customers', dict(customer=customer, previewToken=preview.json()['previewToken'], confirmed=True))
            assert saved.status_code == 201, saved.text
            customer_ids.append(saved.json()['customer']['id'])
        seed = int(marker[:8], 16)
        serial, number = seed % 999980 + 1, seed % 9980 + 1
        alphabet = 'ABCDEFGHJKLMNPRSTUVWXYZ'
        prefix = ''.join(alphabet[int(char, 16)] for char in marker[:3])

        def vehicle(index=0):
            return dict(vin=f'WVWZZZ1JZXW{serial + index:06d}', plate=f'{prefix}-{number + index:04d}',
                        make='Video ' + marker, model='Golf', year=1999, version='Base', color='Gris', mileage=None)

        payload = dict(vehicle=vehicle(), confirmed=True)
        registration = f'/api/vehicles/customer/{customer_ids[0]}'
        png = photo()
        check(call('GET', '/api/vehicles', role=None).status_code == 401, 'Consulta requiere sesión')
        for role in ('MECANICO', 'INVITADO', 'SECRETARIA'):
            if role not in role_states:
                continue
            expected = 403 if role_states[role] == 1 else 401
            check(call('POST', registration, payload, role=role, photos=[]).status_code == expected, role + ' no registra vehículos')
        check(call('POST', registration, {**payload, 'confirmed': False}, photos=[]).status_code == 422, 'Alta exige confirmación')
        check(call('POST', registration, payload, photos=[('falsa.png', b'no es una imagen', 'image/png')]).status_code == 422, 'Foto falsa rechazada')
        check(call('POST', registration, payload, photos=[('falsa.jpg', png, 'image/jpeg')]).status_code == 422, 'MIME falso rechazado')
        check(call('POST', registration, payload, photos=[('grande.png', bytes(15000001), 'image/png')]).status_code == 413, 'Foto de más de 15 MB rechazada')
        with engine.connect() as connection:
            check(connection.execute(text('SELECT COUNT(*) FROM vehicles WHERE customer_id=:id'), {'id': customer_ids[0]}).scalar_one() == 0,
                  'Validaciones fallidas no crean vehículo ni asociación')
        operator = 'RECEPCIONISTA' if role_states['RECEPCIONISTA'] == 1 else 'ADMINISTRADOR'
        result = call('POST', registration, payload, role=operator, photos=[('uno.png', png, 'image/png'), ('dos.jpg', photo('JPEG'), 'image/jpeg')])
        check(result.status_code == 201, 'Registro con varias fotos: ' + str(result.status_code))
        saved = result.json()['vehicle']; vehicle_id = saved['id']; path = f'/api/vehicles/{vehicle_id}'
        check(saved['status'] == 'ACTIVO' and saved['customerId'] == customer_ids[0], 'Vehículo activo asociado al cliente')
        details = call('GET', path).json()
        check(len(details['photos']) == 2 and details['customerName'] and details['workshopName'], 'Expediente incluye cliente, taller y dos fotos')
        image_path = path + '/photos/' + str(details['photos'][0]['id'])
        check(call('GET', image_path, role=None).status_code == 401, 'Foto privada requiere sesión')
        image = call('GET', image_path)
        check(image.status_code == 200 and image.content == png and image.headers['content-type'] == 'image/png', 'Foto recuperada íntegra con tipo real')
        check(image.headers['cache-control'] == 'private, no-store' and image.headers['x-content-type-options'] == 'nosniff', 'Fotos sin publicación estática ni caché compartida')
        check(call('GET', path + '/photos/9223372036854775807').status_code == 404, 'Foto ajena o inexistente no se obtiene')
        listing = call('GET', '/api/vehicles?search=' + marker).json()
        check(listing['total'] == 1 and listing['items'][0]['photoCount'] == 2, 'Búsqueda paginada por marca incluye fotos')
        for query in ('page=0', 'page_size=101', 'status=otro'):
            check(call('GET', '/api/vehicles?' + query).status_code == 422, 'Filtro/página inválido bloqueado: ' + query)
        check(call('POST', registration, payload, photos=[]).status_code == 409, 'VIN/placa duplicados no crean otro registro')
        check(call('POST', registration, {'vehicle': {**vehicle(1), 'plate': vehicle()['plate']}, 'confirmed': True}, photos=[]).status_code == 409, 'Placa repetida con otro VIN bloqueada')
        update = dict(vehicle={**vehicle(), 'plate': vehicle(3)['plate'], 'make': 'Video Editado ' + marker,
                               'model': 'Jetta', 'year': 2000, 'version': 'Comfort', 'color': 'Negro', 'mileage': 100},
                      recordVersion=1, confirmed=True)
        for field in update['vehicle']:
            for invalid in ('', '   ', None):
                incomplete = {**update, 'vehicle': {**update['vehicle'], field: invalid}}
                check(call('PUT', path, incomplete, photos=[]).status_code == 422, f'Edición: {field} vacío/nulo bloqueado')
            incomplete_vehicle = {key: value for key, value in update['vehicle'].items() if key != field}
            check(call('PUT', path, {**update, 'vehicle': incomplete_vehicle}, photos=[]).status_code == 422,
                  f'Edición: omitir {field} bloqueado')
        for field in update['vehicle']:
            incomplete = {**update, 'vehicle': {**update['vehicle'], field: None}}
            check(call('PUT', f'/vehicles/{vehicle_id}', incomplete, direct=True).status_code in (400, 422),
                  f'C# directo: {field} nulo bloqueado')
        unchanged_invalid = call('GET', path).json()
        check(unchanged_invalid['vehicle']['recordVersion'] == 1 and unchanged_invalid['vehicle']['color'] == 'Gris'
              and unchanged_invalid['vehicle']['mileage'] is None and len(unchanged_invalid['photos']) == 2
              and len(unchanged_invalid['auditEntries']) == 1,
              'Datos incompletos no alteran vehículo, fotos, revisión ni auditoría')
        for role in ('SECRETARIA', 'MECANICO', 'INVITADO'):
            if role not in role_states:
                continue
            expected = 403 if role_states[role] == 1 else 401
            check(call('PUT', path, update, role=role, photos=[]).status_code == expected, role + ' no actualiza vehículos')
        check(call('PUT', path, {**update, 'vehicle': {**update['vehicle'], 'vin': 'INVALIDO'}}, photos=[]).status_code == 422,
              'Edición rechaza una referencia que no coincide con el VIN guardado')
        changed_vin = {**update, 'vehicle': {**update['vehicle'], 'vin': vehicle(3)['vin']}}
        check(call('PUT', path, changed_vin, photos=[('rechazada.png', png, 'image/png')]).status_code == 422,
              'Edición rechaza un VIN distinto aunque sea válido')
        check(call('PUT', f'/vehicles/{vehicle_id}', changed_vin, direct=True).status_code == 422,
              'C# directo también rechaza cambiar el VIN')
        check(call('GET', path).json() == unchanged_invalid,
              'Cambiar el VIN no altera los datos, las fotos, la revisión ni la auditoría')
        changed = call('PUT', path, update, role=operator, photos=[('tres.webp', photo('WEBP'), 'image/webp')])
        check(changed.status_code == 200 and changed.json()['vehicle']['recordVersion'] == 2, 'Operador actualiza con control de concurrencia')
        details = call('GET', path).json()
        check(details['vehicle']['vin'] == vehicle()['vin'] and all(
            details['vehicle'][key] == (value.replace('-', '') if key == 'plate' else value)
            for key, value in update['vehicle'].items()
        ), 'Se guardan los siete campos editables y se conserva el VIN original')
        check(len(details['photos']) == 3 and details['vehicle']['color'] == 'Negro', 'Edición agrega fotos sin borrar anteriores')
        check(details['auditEntries'][0]['action'] == 'UC-CV-08 ActualizarVehiculo', 'Edición auditada con actor y hora')
        failed_photos = call('PUT', path, {**update, 'recordVersion': 2, 'vehicle': {**update['vehicle'], 'color': 'Rojo'}},
                            photos=[(f'extra-{index}.png', png, 'image/png') for index in range(8)])
        check(failed_photos.status_code == 422, 'No se supera el máximo de 10 fotos acumuladas')
        unchanged = call('GET', path).json()
        check(unchanged['vehicle']['color'] == 'Negro' and unchanged['vehicle']['recordVersion'] == 2
              and len(unchanged['photos']) == 3 and len(unchanged['auditEntries']) == 2,
              'Fallo al agregar fotos revierte datos, revisión, fotos y auditoría')
        check(call('PUT', path, update, photos=[]).status_code == 409, 'Revisión antigua no sobrescribe cambios')
        second = call('POST', registration, dict(vehicle=vehicle(1), confirmed=True), photos=[])
        check(second.status_code == 201, 'Segundo vehículo sin foto conserva compatibilidad')
        second_id = second.json()['vehicle']['id']
        no_photo_update = dict(vehicle={**vehicle(1), 'mileage': 0}, recordVersion=1, confirmed=True)
        check(call('PUT', f'/api/vehicles/{second_id}', no_photo_update, photos=[]).status_code == 422,
              'Edición: vehículo sin fotografías debe adjuntar al menos una')
        check(call('PUT', f'/vehicles/{second_id}', no_photo_update, direct=True).status_code == 422,
              'C# directo: fotografía obligatoria también se comprueba en servidor')
        no_photo_details = call('GET', f'/api/vehicles/{second_id}').json()
        check(no_photo_details['vehicle']['recordVersion'] == 1 and len(no_photo_details['photos']) == 0
              and len(no_photo_details['auditEntries']) == 1, 'Falta de fotografía no modifica el registro')
        collision = dict(vehicle={**update['vehicle'], 'plate': vehicle(1)['plate']}, recordVersion=2, confirmed=True)
        check(call('PUT', path, collision, photos=[]).status_code == 409, 'Edición no permite placa de otro vehículo')
        check(call('PUT', path + '/owner', dict(customerId=customer_ids[1], recordVersion=2, confirmed=False)).status_code == 422, 'Cambiar cliente exige confirmación')
        transfer = call('PUT', path + '/owner', dict(customerId=customer_ids[1], recordVersion=2, confirmed=True), role=operator)
        check(transfer.status_code == 200 and transfer.json()['vehicle']['customerId'] == customer_ids[1], 'Vehículo asociado al nuevo cliente activo')
        check(transfer.json()['auditEntry']['previousCustomerId'] == customer_ids[0], 'Se conserva cliente anterior en auditoría')
        check(call('GET', f'/api/customers/{customer_ids[0]}/vehicles').json()[0]['id'] == second_id, 'Cliente anterior conserva solo sus vehículos actuales')
        check(call('GET', f'/api/customers/{customer_ids[1]}/vehicles').json()[0]['id'] == vehicle_id, 'Nuevo cliente consulta su vehículo')
        check(len(call('GET', path).json()['photos']) == 3, 'Cambio de propietario conserva fotos')
        if role_states['RECEPCIONISTA'] == 1:
            check(call('DELETE', path, dict(recordVersion=3, confirmed=True), role='RECEPCIONISTA').status_code == 403, 'Recepcionista no desactiva vehículos')
        check(call('DELETE', path, dict(recordVersion=3, confirmed=False)).status_code == 422, 'Baja exige confirmación')
        check(call('DELETE', path, dict(recordVersion=2, confirmed=True)).status_code == 409, 'Baja rechaza revisión antigua')
        disabled = call('DELETE', path, dict(recordVersion=3, confirmed=True))
        check(disabled.status_code == 200 and disabled.json()['vehicle']['status'] == 'INACTIVO', 'Solo administrador aplica baja lógica')
        details = call('GET', path).json()
        check(len(details['photos']) == 3 and len(details['auditEntries']) == 4, 'Baja conserva expediente, galería y auditoría completa')
        check(call('GET', image_path).content == png, 'Foto se conserva después de la baja')
        check(call('GET', '/api/vehicles?status=inactive&search=' + marker).json()['total'] == 1, 'Filtro consulta vehículo inactivo')
        check(call('GET', '/api/vehicles?status=active&search=' + marker).json()['total'] == 1, 'Filtro activo excluye vehículo dado de baja')
        check(call('DELETE', path, dict(recordVersion=4, confirmed=True)).status_code == 409, 'Baja repetida no genera otra auditoría')
        check(call('PUT', path, {**update, 'recordVersion': 4}, photos=[]).status_code == 409, 'Vehículo inactivo no se edita')
        check(call('POST', registration, payload, photos=[]).status_code == 409, 'Baja lógica no libera VIN ni placa para duplicarlos')
        with engine.connect() as connection:
            row = connection.execute(text('SELECT v.bin_status,s.valor,v.deleted_at,v.record_version FROM vehicles v INNER JOIN status s ON s.id=v.bin_status WHERE v.id=:id'), {'id': vehicle_id}).one()
            check(row.bin_status == 2 and row.valor == 'suspendido' and row.deleted_at and row.record_version == 4,
                  'MySQL: estado por INNER JOIN, fecha de baja y revisión sin texto redundante')
        # Verifica el límite exacto con una imagen real y bytes de relleno posteriores al PNG.
        boundary = png + bytes(15000000 - len(png))
        limit_result = call('POST', registration, dict(vehicle=vehicle(2), confirmed=True), photos=[('limite.png', boundary, 'image/png')])
        check(limit_result.status_code == 201, 'Carga real de exactamente 15 MB admitida')
        limit_id = limit_result.json()['vehicle']['id']
        limit_detail = call('GET', f'/api/vehicles/{limit_id}').json()
        check(limit_detail['photos'][0]['sizeBytes'] == 15000000, 'MySQL conserva íntegra la imagen de 15 MB')
        full_gallery = call('PUT', f'/api/vehicles/{limit_id}', dict(vehicle={**vehicle(2), 'mileage': 0}, recordVersion=1, confirmed=True),
                            photos=[(f'foto-{index}.png', png, 'image/png') for index in range(9)])
        check(full_gallery.status_code == 200 and len(call('GET', f'/api/vehicles/{limit_id}').json()['photos']) == 10,
              'Se permiten exactamente 10 fotos acumuladas por vehículo')
        check(call('POST', registration, dict(vehicle=vehicle(3), confirmed=True),
                   photos=[(f'foto-{index}.png', png, 'image/png') for index in range(11)]).status_code == 422,
              'El parser limita la cantidad de archivos antes de persistir')
        # Peticiones simultáneas: la revisión permite una sola edición.
        def concurrent_edit(color):
            return call('PUT', f'/api/vehicles/{second_id}', dict(vehicle={**vehicle(1), 'color': color, 'mileage': 0}, recordVersion=1, confirmed=True),
                        photos=[('obligatoria.png', png, 'image/png')]).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            codes = list(pool.map(concurrent_edit, ['Blanco', 'Azul']))
        check(sorted(codes) == [200, 409], 'Ediciones simultáneas: una gana y otra recibe conflicto')
        with_existing_photo = call('PUT', f'/api/vehicles/{second_id}',
                                   dict(vehicle={**vehicle(1), 'mileage': 0}, recordVersion=2, confirmed=True), photos=[])
        check(with_existing_photo.status_code == 200 and with_existing_photo.json()['vehicle']['mileage'] == 0,
              'Edición completa acepta cero km y conserva la foto anterior sin volver a subirla')
        complete_details = call('GET', f'/api/vehicles/{second_id}').json()
        check(len(complete_details['photos']) == 1 and complete_details['vehicle']['recordVersion'] == 3,
              'Fotografía previa conservada sin duplicarse tras la actualización')
        # Simular un VIN guardado antes del formato actual, solo sobre este vehículo de prueba.
        legacy_vin = 'Q-' + marker[:10]
        with engine.begin() as connection:
            updated = connection.execute(text('UPDATE vehicles SET vin=:vin WHERE id=:id AND customer_id=:customer'),
                                         {'vin': legacy_vin, 'id': second_id, 'customer': customer_ids[0]})
            assert updated.rowcount == 1, 'No se pudo preparar el vehículo anterior.'
        legacy_data = {**vehicle(1), 'vin': legacy_vin, 'color': 'Verde', 'mileage': 0}
        legacy_edit = call('PUT', f'/api/vehicles/{second_id}', dict(vehicle=legacy_data, recordVersion=3, confirmed=True), photos=[])
        check(legacy_edit.status_code == 200, 'Edición permite conservar un VIN anterior')
        legacy_vehicle = call('GET', f'/api/vehicles/{second_id}').json()['vehicle']
        check(legacy_vehicle['vin'] == legacy_vin and legacy_vehicle['color'] == 'Verde' and legacy_vehicle['recordVersion'] == 4,
              'Se guarda el color nuevo y el VIN anterior se conserva exactamente')
        check(call('POST', registration, dict(vehicle={**legacy_data, 'plate': vehicle(4)['plate']}, confirmed=True), photos=[]).status_code == 422,
              'El alta conserva la validación de VIN nuevo')
        # Darse de baja un cliente no elimina físicamente el historial del vehículo.
        check(call('DELETE', f'/api/customers/{customer_ids[1]}', dict(version=1, confirmed=True)).status_code == 200, 'Fixture de cliente dado de baja')
        check(call('PUT', f'/api/vehicles/{second_id}/owner', dict(customerId=customer_ids[1], recordVersion=4, confirmed=True)).status_code == 409, 'No se asocia a cliente inactivo')
        print(f'RESULTADO: {checks} comprobaciones HTTP/MySQL del video aprobadas.', flush=True)
    finally:
        client.close()
        if customer_ids:
            with engine.begin() as connection:
                for sql in (
                    'DELETE p FROM vehicle_photos p JOIN vehicles v ON v.id=p.vehicle_id WHERE v.customer_id IN :ids',
                    'DELETE a FROM vehicle_audit_entries a JOIN vehicles v ON v.id=a.vehicle_id WHERE v.customer_id IN :ids',
                    'DELETE FROM vehicles WHERE customer_id IN :ids',
                    'DELETE FROM audit_entries WHERE customer_id IN :ids',
                    'DELETE FROM customers WHERE id IN :ids',
                ):
                    connection.execute(text(sql).bindparams(bindparam('ids', expanding=True)), {'ids': customer_ids})
        if user_ids:
            with SessionLocal.begin() as db:
                for user in db.scalars(select(User).where(User.id.in_(user_ids))):
                    user.active_session_id = None
                    db.delete(user)


if __name__ == '__main__':
    run()
