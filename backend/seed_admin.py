"""Crea el primer administrador sin guardar su contraseña en texto plano."""
import getpass
import re

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import User, UserRole
from app.security import hash_password
from app.migrations import initialize_database


def main() -> None:
    initialize_database()
    username = input("Usuario administrador: ").strip()
    full_name = input("Nombre completo: ").strip()
    email = input("Correo electrónico de recuperación: ").strip().lower()
    password = getpass.getpass("Contraseña (mínimo 8 caracteres): ")
    if len(username) < 3 or len(password) < 8 or not full_name or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise SystemExit("Datos no válidos. Usuario mínimo 3, contraseña mínimo 8, nombre y correo válidos obligatorios.")
    with SessionLocal.begin() as db:
        if db.execute(select(User).where(User.username == username)).scalar_one_or_none():
            raise SystemExit("Ese usuario ya existe.")
        db.add(User(username=username, full_name=full_name, email=email, password_hash=hash_password(password), role=UserRole.ADMINISTRADOR, bin_status=1))
    print("Administrador creado correctamente.")


if __name__ == "__main__":
    main()
