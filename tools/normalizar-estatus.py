"""Respaldo dirigido y eliminación verificable del texto redundante de estatus.

Ejecutar con los servicios detenidos. No contiene ni exporta credenciales.
Sin --apply únicamente inspecciona, sin modificar la base de datos.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

from sqlalchemy import inspect, text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.database import engine
from app.migrations import normalize_status_storage

TABLES = ('users', 'customers', 'status', 'roles', 'user_sessions',
          'password_reset_tokens', 'customer_contact_keys', 'audit_entries',
          'administration_audit', 'workshops')


def digest(value):
    def serialize(item):
        return item.hex() if isinstance(item, bytes) else str(item)
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=serialize,
                                    ensure_ascii=False).encode('utf-8')).hexdigest()


def snapshot(column_sets=None):
    result = {}
    with engine.connect() as connection:
        schema = inspect(connection)
        for table in TABLES:
            if not schema.has_table(table):
                continue
            columns = (column_sets[table] if column_sets else
                       [c['name'] for c in schema.get_columns(table)
                        if not (table in ('users', 'customers') and c['name'] == 'status')])
            projection = ','.join(f'`{name}`' for name in columns)
            hashes = sorted(digest(dict(row)) for row in connection.execute(
                text(f'SELECT {projection} FROM `{table}`')).mappings())
            result[table] = dict(columns=columns, records=len(hashes), sha256=digest(hashes))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    before = snapshot()
    legacy = {}
    with engine.connect() as connection:
        schema = inspect(connection)
        for table in ('users', 'customers'):
            columns = {c['name']: c for c in schema.get_columns(table)}
            if 'status' in columns:
                metadata = columns['status']
                projection = 'id,status' + (',bin_status' if 'bin_status' in columns else '')
                legacy[table] = dict(type=str(metadata['type']), nullable=metadata['nullable'],
                                     default=metadata['default'], rows=[dict(row) for row in
                                     connection.execute(text(f'SELECT {projection} FROM {table} ORDER BY id')).mappings()])
    if not args.apply:
        print(json.dumps(dict(legacy_columns=list(legacy), records={t: v['records'] for t, v in before.items()})))
        return
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder = ROOT / 'database' / 'backups'
    folder.mkdir(parents=True, exist_ok=True)
    backup = folder / f'status-legacy-{stamp}.json'
    # Exclusivo: no sobrescribir un respaldo anterior. Solo ID/estatus y huellas.
    with backup.open('x', encoding='utf-8') as stream:
        json.dump(dict(created_at=stamp, legacy=legacy, snapshot=before), stream,
                  ensure_ascii=False, indent=2)
    columns = {table: value['columns'] for table, value in before.items()}
    normalize_status_storage()
    after = snapshot(columns)
    if before != after:
        raise RuntimeError(f'La comparación de datos no coincide; revisar el respaldo {backup}')
    normalize_status_storage()
    repeated = snapshot(columns)
    if after != repeated:
        raise RuntimeError('La segunda ejecución no fue idempotente')
    with engine.connect() as connection:
        schema = inspect(connection)
        for table in ('users', 'customers'):
            if 'status' in {c['name'] for c in schema.get_columns(table)}:
                raise RuntimeError(f'La columna redundante sigue presente en {table}')
    report = dict(created_at=stamp, removed_columns=[f'{t}.status' for t in legacy],
                  backup=str(backup), records_and_states_preserved=True,
                  idempotent=True, verified_tables={t: v['records'] for t, v in after.items()})
    report_path = ROOT / 'analisis' / 'verificacion-estatus-normalizados.json'
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
