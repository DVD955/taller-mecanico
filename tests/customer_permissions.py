"""Matriz del gateway, sin modificar cuentas ni el catálogo de roles."""
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from fastapi import HTTPException
from app.customers import forward

allowed = {
    'read': {'ADMINISTRADOR', 'RECEPCIONISTA', 'SECRETARIA'},
    'register': {'ADMINISTRADOR', 'RECEPCIONISTA'},
    'update': {'ADMINISTRADOR', 'SECRETARIA'},
    'deactivate': {'ADMINISTRADOR'},
    'vehicle': {'ADMINISTRADOR', 'RECEPCIONISTA'},
}
response = MagicMock()
response.status = 200
response.headers = {'Content-Type': 'application/json'}
response.read.return_value = b'{}'
count = 0
for role in ('ADMINISTRADOR', 'RECEPCIONISTA', 'SECRETARIA', 'MECANICO', 'INVITADO'):
    for operation, roles in allowed.items():
        with patch('app.customers.urlopen') as opener:
            opener.return_value.__enter__.return_value = response
            try:
                forward('/customers', {}, SimpleNamespace(role=role), 'Bearer test', operation=operation)
                assert role in roles, (role, operation)
                assert opener.call_count == 1
            except HTTPException as error:
                assert role not in roles and error.status_code == 403, (role, operation)
                assert opener.call_count == 0
            count += 1
print(f'RESULTADO: {count} combinaciones de rol/operación aprobadas.')
