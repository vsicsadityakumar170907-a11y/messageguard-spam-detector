import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv


load_dotenv()

OTP_LENGTH = 6
OTP_VALID_MINUTES = 10


def generate_otp() -> str:
    """Return a cryptographically random six-digit code."""
    return f"{secrets.randbelow(10**OTP_LENGTH):0{OTP_LENGTH}d}"


def otp_expiry_time() -> datetime:
    """Return the UTC time when a newly generated code expires."""
    return datetime.now(timezone.utc) + timedelta(minutes=OTP_VALID_MINUTES)


def hash_otp(email: str, purpose: str, otp: str) -> str:
    """Hash an OTP with a secret key, so the plain code needn't be stored."""
    secret = os.getenv("OTP_SECRET")
    if not secret:
        raise RuntimeError("OTP_SECRET .env file mein set nahi hai.")

    value = f"{email.strip().lower()}:{purpose}:{otp}"
    return hmac.new(
        secret.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_otp_hash(email: str, purpose: str, otp: str, saved_hash: str) -> bool:
    """Compare an entered code to its saved hash safely."""
    try:
        entered_hash = hash_otp(email, purpose, otp)
    except RuntimeError:
        return False

    return hmac.compare_digest(entered_hash, saved_hash)