from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session, joinedload

from app.core.security import decode_access_token
from app.db.models import User
from app.db.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    user_id = decode_access_token(token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user = (
        db.query(User)
        .options(joinedload(User.role), joinedload(User.team_memberships))
        .filter(User.id == int(user_id))
        .first()
    )
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is inactive or missing")
    return user


def has_permission(user: User, permission: str) -> bool:
    perms = user.role.permissions or []
    return permission in perms


def require_permission(permission: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if not has_permission(user, permission):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
        return user

    return checker
