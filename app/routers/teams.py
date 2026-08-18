from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.db.models import Task, User
from app.db.session import get_db
from app.schemas import EmployeeCreate, EmployeeUpdate, UserOut

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("", response_model=list)
def list_employees(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    rows = db.query(User).filter(User.kind == "employee").order_by(User.id.desc()).all()
    return [UserOut.model_validate(row) for row in rows]


@router.post("", response_model=UserOut, status_code=201)
def create_employee(
    payload: EmployeeCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    email = payload.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already exists")
    user = User(
        kind="employee",
        email=email,
        password_hash=None,
        name=payload.name,
        phone=payload.phone.strip(),
        designation=payload.designation,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.patch("/{employee_id}", response_model=UserOut)
def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == employee_id, User.kind == "employee").first()
    if not user:
        raise HTTPException(status_code=404, detail="Employee not found")
    if payload.email and payload.email.lower() != user.email:
        if db.query(User).filter(User.email == payload.email.lower()).first():
            raise HTTPException(status_code=400, detail="Email already exists")
        user.email = payload.email.lower()
    if payload.name is not None:
        user.name = payload.name
    if payload.phone is not None:
        user.phone = payload.phone.strip()
    if payload.designation is not None:
        user.designation = payload.designation
    if payload.is_active is not None:
        user.is_active = payload.is_active
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.delete("/{employee_id}", status_code=204)
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == employee_id, User.kind == "employee").first()
    if not user:
        raise HTTPException(status_code=404, detail="Employee not found")
    if db.query(Task).filter(Task.assigned_to == user.id).first():
        raise HTTPException(status_code=400, detail="Employee has tasks. Disable them instead.")
    db.delete(user)
    db.commit()
