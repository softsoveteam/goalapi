import hashlib
from datetime import datetime, timedelta, timezone
from secrets import randbelow

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.security import create_access_token, is_admin, verify_password
from app.db.models import OtpCode, Task, User
from app.db.session import get_db
from app.schemas import LoginIn, MeOut, OtpRequestIn, OtpVerifyIn, TokenOut, UserOut
from app.services.mailer import send_otp_email

router = APIRouter(prefix="/auth", tags=["auth"])


def _hash_code(code: str) -> str:
    return hashlib.sha256("{0}:{1}".format(settings.secret_key, code).encode("utf-8")).hexdigest()


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.email == payload.email.lower()).first()
    except (ProgrammingError, OperationalError) as exc:
        db.rollback()
        print("[auth] login db error: {0}".format(exc))
        raise HTTPException(
            status_code=503,
            detail="Database schema is out of date. On the server run: python -m app.migrate",
        )
    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Use the email code sent with your task link")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")
    return TokenOut(access_token=create_access_token(str(user.id)))


@router.post("/otp/request")
def request_otp(payload: OtpRequestIn, db: Session = Depends(get_db)):
    email = payload.email.lower()
    user = db.query(User).filter(User.email == email, User.kind == "employee", User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Employee not found")
    if payload.public_id:
        task = db.query(Task).filter(Task.public_id == payload.public_id).first()
        if not task or task.assigned_to != user.id:
            raise HTTPException(status_code=403, detail="This task is not assigned to you")
    code = "{0:06d}".format(randbelow(1000000))
    expires = datetime.now(timezone.utc) + timedelta(minutes=10)
    db.query(OtpCode).filter(OtpCode.email == email).delete()
    db.add(OtpCode(email=email, code_hash=_hash_code(code), purpose="login", expires_at=expires))
    db.commit()
    send_otp_email(email, code)
    return {"ok": True}


@router.post("/otp/verify", response_model=TokenOut)
def verify_otp(payload: OtpVerifyIn, db: Session = Depends(get_db)):
    email = payload.email.lower()
    row = (
        db.query(OtpCode)
        .filter(OtpCode.email == email, OtpCode.purpose == "login")
        .order_by(OtpCode.id.desc())
        .first()
    )
    if not row:
        raise HTTPException(status_code=400, detail="No code requested")
    expires = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Code expired")
    if row.code_hash != _hash_code(payload.code.strip()):
        raise HTTPException(status_code=400, detail="Invalid code")
    user = db.query(User).filter(User.email == email, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Employee not found")
    db.delete(row)
    db.commit()
    return TokenOut(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(get_current_user)):
    data = UserOut.model_validate(user)
    return MeOut(**data.model_dump(), is_admin=is_admin(user))
