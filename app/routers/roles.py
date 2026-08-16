from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user, has_permission, require_permission
from app.core.security import ALL_PERMISSIONS
from app.db.models import Role, User
from app.db.session import get_db
from app.schemas import PermissionCatalogOut, RoleCreate, RoleOut, RoleUpdate

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("/permissions", response_model=PermissionCatalogOut)
def list_permissions(_: User = Depends(require_permission("roles.manage"))):
    return PermissionCatalogOut(permissions=ALL_PERMISSIONS)


@router.get("", response_model=list[RoleOut])
def list_roles(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    if not (has_permission(current, "roles.manage") or has_permission(current, "users.manage")):
        raise HTTPException(status_code=403, detail="Permission denied")
    return db.query(Role).order_by(Role.id.asc()).all()


@router.post("", response_model=RoleOut, status_code=201)
def create_role(
    payload: RoleCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("roles.manage")),
):
    if db.query(Role).filter(Role.name == payload.name).first():
        raise HTTPException(status_code=400, detail="Role name already exists")
    permissions = [p for p in payload.permissions if p in ALL_PERMISSIONS]
    role = Role(name=payload.name, permissions=permissions, is_system=False)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@router.patch("/{role_id}", response_model=RoleOut)
def update_role(
    role_id: int,
    payload: RoleUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("roles.manage")),
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    if payload.name and payload.name != role.name:
        if role.is_system:
            raise HTTPException(status_code=400, detail="System roles cannot be renamed")
        if db.query(Role).filter(Role.name == payload.name, Role.id != role_id).first():
            raise HTTPException(status_code=400, detail="Role name already exists")
        role.name = payload.name
    if payload.permissions is not None:
        if role.name == "Owner" and role.is_system:
            role.permissions = list(ALL_PERMISSIONS)
        else:
            role.permissions = [p for p in payload.permissions if p in ALL_PERMISSIONS]
    db.commit()
    db.refresh(role)
    return role


@router.delete("/{role_id}", status_code=204)
def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("roles.manage")),
):
    role = db.query(Role).options(joinedload(Role.users)).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    if role.is_system:
        raise HTTPException(status_code=400, detail="System roles cannot be deleted")
    if role.users:
        raise HTTPException(status_code=400, detail="Reassign users before deleting this role")
    db.delete(role)
    db.commit()
