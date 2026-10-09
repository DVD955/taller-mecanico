"""Comprueba de forma exclusivamente lectora el catálogo único de estatus.

No migra ni crea, actualiza o elimina registros; se ejecuta después de la
migración coordinada. Los estados de negocio y la respuesta API se verifican
además en los tests integrados de cuentas y clientes.
"""
from pathlib import Path
import sys

from sqlalchemy import inspect, text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.database import engine
from app.models import User


def run():
    count = 0

    def check(condition, message):
        nonlocal count
        assert condition, message
        count += 1
        print("OK:", message)

    with engine.connect() as connection:
        schema = inspect(connection)
        for table in ("users", "customers"):
            columns = {column["name"] for column in schema.get_columns(table)}
            check("status" not in columns and "bin_status" in columns,
                  f"MySQL: {table} conserva bin_status y no repite el estatus en texto")
        check("status" not in User.__table__.columns and "bin_status" in User.__table__.columns,
              "Modelo Python de usuario utiliza únicamente el ID del catálogo")
        for table in ("users", "customers", "roles", "workshops"):
            foreign_keys = schema.get_foreign_keys(table)
            check(any(key["constrained_columns"] == ["bin_status"]
                      and key["referred_table"] == "status"
                      and key["referred_columns"] == ["id"] for key in foreign_keys),
                  f"MySQL: {table}.bin_status está relacionado con status.id por llave foránea")
            # Nombres de tablas constantes, no provenientes de entradas del usuario.
            records = connection.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
            joined = connection.execute(text(f"SELECT COUNT(*) FROM {table} r INNER JOIN status s ON s.id=r.bin_status")).scalar_one()
            check(joined == records,
                  f"MySQL: INNER JOIN de {table} recupera todos los registros sin estatus huérfanos")
        values = dict(connection.execute(text("SELECT id,valor FROM status WHERE id IN (1,2,3)")).all())
        check(values == {1: "activo", 2: "suspendido", 3: "eliminado"},
              "Catálogo conserva Activo 1, Suspendido 2 y Eliminado 3 sin alterar bajas existentes")
    print(f"RESULTADO: {count} comprobaciones de normalización aprobadas (solo lectura).")


if __name__ == "__main__":
    run()
