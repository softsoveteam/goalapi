from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user
from app.core.security import create_access_token, verify_password
from app.db.models import User
from app.db.session import get_db
from app.schemas import LoginIn, MeOut, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).options(joinedload(User.role)).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")
    return TokenOut(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(get_current_user)):
    base = UserOut.model_validate(user)
    return MeOut(
        **base.model_dump(),
        permissions=user.role.permissions or [],
        team_ids=[m.team_id for m in user.team_memberships],
    )
