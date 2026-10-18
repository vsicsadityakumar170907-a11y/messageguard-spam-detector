import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SECRET_FILE = PROJECT_ROOT / ".secret_key"

SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    if SECRET_FILE.exists():
        SECRET_KEY = SECRET_FILE.read_text(encoding="utf-8").strip()
    else:
        SECRET_KEY = secrets.token_urlsafe(48)
        SECRET_FILE.write_text(SECRET_KEY, encoding="utf-8")

ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 60

password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return password_hasher.verify(password, hashed_password)
    except Exception:
        return False


def create_access_token(email: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": email,
        "exp": expires_at,
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_email_from_token(token: str) -> str | None:
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )
        email = payload.get("sub")
        return email if isinstance(email, str) else None
    except InvalidTokenError:
        return None