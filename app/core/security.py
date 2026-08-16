from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

ALL_PERMISSIONS = [
    "roles.manage",
    "users.manage",
    "teams.manage",
    "projects.create",
    "projects.view_all",
    "tasks.assign",
    "goals.view",
    "goals.manage",
]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        subject = payload.get("sub")
        return str(subject) if subject else None
    except JWTError:
        return None
