"""Envío SMTP de enlaces temporales de recuperación."""
import smtplib
from email.message import EmailMessage
from urllib.parse import quote

from .config import get_settings


def send_recovery_email(recipient: str, token: str) -> None:
    settings = get_settings()
    if not settings.smtp_host or not settings.smtp_from or not settings.smtp_password:
        raise RuntimeError("El correo saliente no está configurado.")
    url = f"{settings.frontend_url.rstrip('/')}?reset_token={quote(token)}"
    message = EmailMessage()
    message["Subject"] = "Recuperación de cuenta - Taller Mecánico"
    message["From"] = settings.smtp_from
    message["To"] = recipient
    message.set_content(
        "Recibimos una solicitud para restablecer tu contraseña.\n\n"
        f"Abre este enlace durante los próximos 15 minutos:\n{url}\n\n"
        "Si no solicitaste el cambio, ignora este mensaje."
    )
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
        if settings.smtp_starttls:
            server.starttls()
        if settings.smtp_user:
            server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(message)
