import os
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv


load_dotenv()


def send_otp_email(email: str, otp: str, purpose: str = "verification") -> None:
    """Send a one-time verification code using SMTP settings from .env."""

    host = os.getenv("SMTP_HOST")
    port_value = os.getenv("SMTP_PORT", "587")
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SMTP_FROM_EMAIL") or username

    if not all([host, username, password, sender]):
        raise RuntimeError(
            "Email settings missing. Check SMTP_HOST, SMTP_USERNAME, "
            "SMTP_PASSWORD, and SMTP_FROM_EMAIL in your .env file."
        )

    try:
        port = int(port_value)
    except ValueError as exc:
        raise RuntimeError("SMTP_PORT must be a number, for example 587.") from exc

    message = EmailMessage()
    message["Subject"] = "Your Spam Detector verification code"
    message["From"] = sender
    message["To"] = email
    message.set_content(
        f"""Your verification code is: {otp}

This code was requested for {purpose}.
Do not share this code with anyone.

If you did not request it, you can ignore this email.
"""
    )

    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=20) as server:
                server.login(username, password)
                server.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=20) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(username, password)
                server.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise RuntimeError(
            "OTP email send nahi hua. SMTP settings aur provider configuration check karein."
        ) from exc