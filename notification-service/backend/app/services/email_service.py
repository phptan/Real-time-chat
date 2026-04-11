from __future__ import annotations

from email.message import EmailMessage

import aiosmtplib

from app.core.config import settings


class EmailService:
    async def send_email(self, *, to_email: str, subject: str, content: str) -> None:
        if not settings.smtp_host:
            raise RuntimeError("SMTP host is not configured")

        message = EmailMessage()
        message["From"] = settings.smtp_from_email
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(content)

        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username or None,
            password=settings.smtp_password or None,
            start_tls=settings.smtp_use_tls,
        )
