from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.deps import get_current_user, require_admin
from app.core.security import is_admin
from app.db.models import Task, User
from app.db.session import get_db
from app.schemas import TaskCreate, TaskOut, TaskPublicOut, UserOut
from app.services import interakt
from app.services.timefmt import format_deadline, format_duration, format_remaining

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _query(db: Session):
    return db.query(Task).options(joinedload(Task.assignee), joinedload(Task.creator))


def _out(task: Task) -> TaskOut:
    duration = None
    if task.closed_at:
        duration = format_duration(task.created_at, task.closed_at)
    return TaskOut(
        id=task.id,
        public_id=task.public_id,
        title=task.title,
        description=task.description,
        assigned_to=task.assigned_to,
        deadline=task.deadline,
        is_done=task.is_done,
        created_by=task.created_by,
        created_at=task.created_at,
        closed_at=task.closed_at,
        duration=duration,
        assignee=UserOut.model_validate(task.assignee) if task.assignee else None,
        creator=UserOut.model_validate(task.creator) if task.creator else None,
    )


@router.get("", response_model=list)
def list_tasks(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    q = _query(db).order_by(Task.id.desc())
    if not is_admin(current):
        q = q.filter(Task.assigned_to == current.id)
    return [_out(task) for task in q.all()]


@router.post("", response_model=TaskOut, status_code=201)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin),
):
    assignee = db.query(User).filter(User.id == payload.assigned_to, User.kind == "employee", User.is_active.is_(True)).first()
    if not assignee:
        raise HTTPException(status_code=400, detail="Select an active employee")
    task = Task(
        title=payload.title,
        description=payload.description,
        assigned_to=assignee.id,
        deadline=payload.deadline,
        created_by=current.id,
        is_done=False,
    )
    db.add(task)
    db.commit()
    loaded = _query(db).filter(Task.id == task.id).first()
    remaining = format_remaining(loaded.deadline)
    deadline_text = format_deadline(loaded.deadline)
    link_suffix = loaded.public_id
    interakt.send_template(
        assignee.phone,
        settings.interakt_template_task,
        [assignee.name, loaded.title, deadline_text, remaining],
        button_suffix=link_suffix,
    )
    return _out(loaded)


@router.get("/public/{public_id}", response_model=TaskPublicOut)
def public_task(public_id: str, db: Session = Depends(get_db)):
    task = _query(db).filter(Task.public_id == public_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskPublicOut(
        public_id=task.public_id,
        title=task.title,
        description=task.description,
        deadline=task.deadline,
        is_done=task.is_done,
        assignee_name=task.assignee.name if task.assignee else "",
        assignee_email=task.assignee.email if task.assignee else "",
    )


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    task = _query(db).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not is_admin(current) and task.assigned_to != current.id:
        raise HTTPException(status_code=404, detail="Task not found")
    return _out(task)


@router.get("/by-public/{public_id}", response_model=TaskOut)
def get_by_public(public_id: str, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    task = _query(db).filter(Task.public_id == public_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not is_admin(current) and task.assigned_to != current.id:
        raise HTTPException(status_code=404, detail="Task not found")
    return _out(task)


@router.post("/{task_id}/close", response_model=TaskOut)
def close_task(task_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    task = _query(db).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not is_admin(current) and task.assigned_to != current.id:
        raise HTTPException(status_code=403, detail="Permission denied")
    if task.is_done:
        return _out(task)
    now = datetime.now(timezone.utc)
    task.is_done = True
    task.closed_at = now
    db.commit()
    loaded = _query(db).filter(Task.id == task_id).first()
    duration = format_duration(loaded.created_at, loaded.closed_at)
    member_name = loaded.assignee.name if loaded.assignee else "Team member"
    if settings.admin_whatsapp:
        interakt.send_template(
            settings.admin_whatsapp,
            settings.interakt_template_done,
            [loaded.title, member_name, duration],
        )
    return _out(loaded)
