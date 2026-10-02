"""Crea el primer administrador sin guardar su contraseña en texto plano."""
import getpass

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import User, UserRole, UserStatus
from app.security import hash_password


def main() -> None:
    Base.metadata.create_all(bind=engine)
    username = input("Usuario administrador: ").strip()
    full_name = input("Nombre completo: ").strip()
    password = getpass.getpass("Contraseña (mínimo 8 caracteres): ")
    if len(username) < 3 or len(password) < 8 or not full_name:
        raise SystemExit("Datos no válidos. Usuario mínimo 3, contraseña mínimo 8 y nombre obligatorio.")
    with SessionLocal.begin() as db:
        if db.execute(select(User).where(User.username == username)).scalar_one_or_none():
            raise SystemExit("Ese usuario ya existe.")
        db.add(User(username=username, full_name=full_name, password_hash=hash_password(password), role=UserRole.ADMINISTRADOR, status=UserStatus.ACTIVO))
    print("Administrador creado correctamente.")


if __name__ == "__main__":
    main()
