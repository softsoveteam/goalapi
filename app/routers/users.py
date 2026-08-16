from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user, has_permission, require_permission
from app.core.security import hash_password
from app.db.models import Role, User
from app.db.session import get_db
from app.schemas import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


def _user_query(db: Session):
    return db.query(User).options(joinedload(User.role))


@router.get("", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    if not (has_permission(current, "users.manage") or has_permission(current, "teams.manage") or has_permission(current, "tasks.assign")):
        raise HTTPException(status_code=403, detail="Permission denied")
    return _user_query(db).order_by(User.id.asc()).all()


@router.post("", response_model=UserOut, status_code=201)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("users.manage")),
):
    if db.query(User).filter(User.email == payload.email.lower()).first():
        raise HTTPException(status_code=400, detail="Email already exists")
    role = db.query(Role).filter(Role.id == payload.role_id).first()
    if not role:
        raise HTTPException(status_code=400, detail="Role not found")
    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        name=payload.name,
        role_id=payload.role_id,
        is_active=payload.is_active,
    )
    db.add(user)
    db.commit()
    return _user_query(db).filter(User.id == user.id).first()


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("users.manage")),
):
    user = _user_query(db).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.email and payload.email.lower() != user.email:
        if db.query(User).filter(User.email == payload.email.lower()).first():
            raise HTTPException(status_code=400, detail="Email already exists")
        user.email = payload.email.lower()
    if payload.name is not None:
        user.name = payload.name
    if payload.password:
        user.password_hash = hash_password(payload.password)
    if payload.role_id is not None:
        role = db.query(Role).filter(Role.id == payload.role_id).first()
        if not role:
            raise HTTPException(status_code=400, detail="Role not found")
        user.role_id = payload.role_id
    if payload.is_active is not None:
        if user.id == current.id and not payload.is_active:
            raise HTTPException(status_code=400, detail="You cannot disable your own account")
        user.is_active = payload.is_active
    db.commit()
    return _user_query(db).filter(User.id == user_id).first()


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("users.manage")),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")
    db.delete(user)
    db.commit()
