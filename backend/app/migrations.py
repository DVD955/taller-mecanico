"""Migración repetible. El catálogo de estatus es la referencia de bin_status."""
from sqlalchemy import inspect, text

from .database import Base, engine
# Registra las tablas también al ejecutar esta migración desde una herramienta.
from . import models  # noqa: F401


def _normalize_status_table(connection, table_name: str) -> None:
    """Un único estatus persistido; conserva bin_status si ya existe."""
    if table_name not in {'users', 'customers'}:
        raise ValueError('Tabla fuera del alcance de la normalización de estatus')
    inspector = inspect(connection)
    if not inspector.has_table(table_name):
        return
    columns = {column['name'] for column in inspector.get_columns(table_name)}
    if 'bin_status' not in columns:
        connection.execute(text(f'ALTER TABLE {table_name} ADD COLUMN bin_status INT NOT NULL DEFAULT 1'))
        # Solo bases antiguas sin FK: recuperar el estado antes de quitar texto.
        if table_name == 'customers':
            deleted = 'WHEN deleted_at IS NOT NULL THEN 3 ' if 'deleted_at' in columns else ''
            suspended = "WHEN status='INACTIVO' THEN 2 " if 'status' in columns else ''
            if deleted or suspended:
                connection.execute(text(f'UPDATE customers SET bin_status=CASE {deleted}{suspended}ELSE 1 END'))
        elif 'status' in columns:
            connection.execute(text("UPDATE users SET bin_status=IF(status='ACTIVO',1,2)"))
    invalid = connection.execute(text(f'''
        SELECT COUNT(*) FROM {table_name} t LEFT JOIN status s ON s.id=t.bin_status
        WHERE s.id IS NULL
    ''')).scalar_one()
    if invalid:
        raise ValueError(f'{table_name}: hay estatus sin referencia al catálogo; no se elimina la columna anterior')
    keys = inspect(connection).get_foreign_keys(table_name)
    has_reference = any(key['constrained_columns'] == ['bin_status']
                        and key['referred_table'] == 'status'
                        and key['referred_columns'] == ['id'] for key in keys)
    if not has_reference:
        connection.execute(text(f'ALTER TABLE {table_name} ADD CONSTRAINT fk_{table_name}_bin_status '
                                'FOREIGN KEY (bin_status) REFERENCES status(id)'))
    if 'status' in columns:
        connection.execute(text(f'ALTER TABLE {table_name} DROP COLUMN status'))


def normalize_status_storage() -> None:
    """Migración dirigida y repetible, sin tocar roles, sesiones ni otros datos."""
    with engine.begin() as connection:
        for table_name in ('users', 'customers'):
            _normalize_status_table(connection, table_name)


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(text("""
            INSERT IGNORE INTO status (id, valor, descripcion) VALUES
            (1, 'activo', 'Usuario o registro activo'),
            (2, 'suspendido', 'Usuario o registro suspendido; se conserva'),
            (3, 'eliminado', 'Registro dado de baja lógica; se conserva')
        """))
        # Corrección del catálogo previo, sin recrear tablas ni perder registros.
        connection.execute(text("UPDATE status SET valor='suspendido', descripcion='Usuario o registro suspendido; se conserva' WHERE id=2 AND valor='inactivo'"))
        # En roles, SoftDeleted es Activo(1) -> Suspendido(2). El estatus 3
        # se conserva para las bajas históricas de otros módulos.
        connection.execute(text('UPDATE roles SET bin_status=2, version=version+1, updated_at=UTC_TIMESTAMP() WHERE bin_status=3'))
        connection.execute(text("""
            INSERT IGNORE INTO roles (code, name, description, bin_status, version, created_at, updated_at) VALUES
            ('ADMINISTRADOR', 'Administrador', 'Administra roles, cuentas, clientes y talleres', 1, 1, UTC_TIMESTAMP(), UTC_TIMESTAMP()),
            ('RECEPCIONISTA', 'Recepcionista', 'Registra y administra clientes y talleres', 1, 1, UTC_TIMESTAMP(), UTC_TIMESTAMP()),
            ('MECANICO', 'Mecánico', 'Cuenta de personal sin administración de clientes o talleres', 1, 1, UTC_TIMESTAMP(), UTC_TIMESTAMP()),
            ('INVITADO', 'Invitado', 'Cuenta creada mediante registro público', 1, 1, UTC_TIMESTAMP(), UTC_TIMESTAMP())
        """))
        columns = {column['name']: column for column in inspect(connection).get_columns('users')}
        additions = {
            'email': 'VARCHAR(255) NULL UNIQUE',
            'recovery_code_hash': 'VARCHAR(255) NULL',
            'recovery_expires_at': 'DATETIME NULL',
        }
        for name, definition in additions.items():
            if name not in columns:
                connection.execute(text(f'ALTER TABLE users ADD COLUMN {name} {definition}'))
        if str(columns['role']['type']).startswith('ENUM'):
            connection.execute(text('ALTER TABLE users MODIFY COLUMN role VARCHAR(50) NOT NULL'))
        foreign_keys = {key['name'] for key in inspect(connection).get_foreign_keys('users')}
        if 'fk_users_role_catalog' not in foreign_keys:
            connection.execute(text('ALTER TABLE users ADD CONSTRAINT fk_users_role_catalog FOREIGN KEY (role) REFERENCES roles(code)'))
        # Comparte el catálogo con C# y conserva el mismo contrato HTTP.
        for table_name in ('users', 'customers'):
            _normalize_status_table(connection, table_name)
        workshop_columns = {column['name'] for column in inspect(connection).get_columns('workshops')}
        if 'email' not in workshop_columns:
            connection.execute(text('ALTER TABLE workshops ADD COLUMN email VARCHAR(254) NULL'))
    normalize_postal_catalog()


def normalize_postal_catalog() -> None:
    """Dimensiones relacionadas; conserva las columnas de la importación original."""
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        columns = {column['name'] for column in inspect(connection).get_columns('postal_settlements')}
        if 'municipality_id' not in columns:
            connection.execute(text('ALTER TABLE postal_settlements ADD COLUMN municipality_id INT NULL, ADD INDEX idx_postal_municipality (municipality_id), ADD CONSTRAINT fk_postal_municipality FOREIGN KEY (municipality_id) REFERENCES postal_municipalities(id)'))
        # La conversión nacional solo se repite cuando hay asentamientos nuevos.
        if connection.execute(text('SELECT 1 FROM postal_settlements WHERE municipality_id IS NULL LIMIT 1')).first() is None:
            return
        connection.execute(text('INSERT IGNORE INTO postal_states (name) SELECT DISTINCT state FROM postal_settlements'))
        connection.execute(text('''
            INSERT IGNORE INTO postal_municipalities (state_id, name)
            SELECT DISTINCT s.id, p.municipality FROM postal_settlements p JOIN postal_states s ON s.name=p.state
        '''))
        connection.execute(text('''
            UPDATE postal_settlements p JOIN postal_states s ON s.name=p.state
            JOIN postal_municipalities m ON m.state_id=s.id AND m.name=p.municipality
            SET p.municipality_id=m.id WHERE p.municipality_id IS NULL
        '''))
