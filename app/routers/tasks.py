from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.deps import get_current_user, require_admin
from app.core.security import is_admin
from app.db.models import Task, TaskFile, TaskItem, User
from app.db.session import get_db
from app.schemas import (
    PRIORITIES,
    ChecklistItemCreate,
    ChecklistItemOut,
    ChecklistItemUpdate,
    TaskArchiveIn,
    TaskCreate,
    TaskFileOut,
    TaskOut,
    TaskPublicOut,
    UserOut,
)
from app.services.notify import send_task_assigned
from app.services.timefmt import format_duration
from app.services.uploads import file_path, save_upload

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _query(db: Session):
    return db.query(Task).options(
        joinedload(Task.assignee),
        joinedload(Task.creator),
        joinedload(Task.archiver),
        selectinload(Task.items),
        selectinload(Task.files),
    )


def _is_archived(task: Task) -> bool:
    return bool(getattr(task, "is_archived", False))


def _out(task: Task) -> TaskOut:
    duration = None
    if task.closed_at:
        duration = format_duration(task.created_at, task.closed_at)
    items = sorted(task.items or [], key=lambda item: (item.sort_order, item.id))
    files = sorted(task.files or [], key=lambda item: item.id, reverse=True)
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
        priority=task.priority or "normal",
        is_archived=_is_archived(task),
        archive_reason=getattr(task, "archive_reason", "") or "",
        archived_at=getattr(task, "archived_at", None),
        archived_by=getattr(task, "archived_by", None),
        duration=duration,
        assignee=UserOut.model_validate(task.assignee) if task.assignee else None,
        creator=UserOut.model_validate(task.creator) if task.creator else None,
        archiver=UserOut.model_validate(task.archiver) if getattr(task, "archiver", None) else None,
        items=[ChecklistItemOut.model_validate(item) for item in items],
        files=[TaskFileOut.model_validate(item) for item in files],
    )


def _can_access(task: Task, current: User) -> bool:
    return is_admin(current) or task.assigned_to == current.id


def _load_or_404(db: Session, task_id: int, current: User) -> Task:
    task = _query(db).filter(Task.id == task_id).first()
    if not task or not _can_access(task, current):
        raise HTTPException(status_code=404, detail="Task not found")
    return task


def _add_items(db: Session, task_id: int, titles) -> None:
    for index, title in enumerate(titles or []):
        text = str(title).strip()
        if not text:
            continue
        db.add(TaskItem(task_id=task_id, title=text[:300], sort_order=index, is_done=False))


def _guard_active(task: Task) -> None:
    if _is_archived(task):
        raise HTTPException(status_code=400, detail="This task is archived")


@router.get("", response_model=list)
def list_tasks(
    archived: bool = Query(False),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    q = _query(db).order_by(Task.id.desc())
    if archived:
        q = q.filter(Task.is_archived.is_(True))
    else:
        q = q.filter((Task.is_archived.is_(False)) | (Task.is_archived.is_(None)))
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
    priority = (payload.priority or "normal").lower()
    if priority not in PRIORITIES:
        raise HTTPException(status_code=400, detail="Priority must be urgent, high, normal, or low")
    task = Task(
        title=payload.title,
        description=payload.description,
        assigned_to=assignee.id,
        deadline=payload.deadline,
        created_by=current.id,
        is_done=False,
        priority=priority,
    )
    db.add(task)
    db.commit()
    _add_items(db, task.id, payload.items)
    db.commit()
    loaded = _query(db).filter(Task.id == task.id).first()
    send_task_assigned(loaded)
    return _out(loaded)


@router.get("/public/{public_id}", response_model=TaskPublicOut)
def public_task(public_id: str, db: Session = Depends(get_db)):
    task = _query(db).filter(Task.public_id == public_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    items = sorted(task.items or [], key=lambda item: (item.sort_order, item.id))
    files = sorted(task.files or [], key=lambda item: item.id, reverse=True)
    return TaskPublicOut(
        public_id=task.public_id,
        title=task.title,
        description=task.description,
        deadline=task.deadline,
        is_done=task.is_done,
        is_archived=_is_archived(task),
        archive_reason=getattr(task, "archive_reason", "") or "",
        priority=task.priority or "normal",
        assignee_name=task.assignee.name if task.assignee else "",
        assignee_email=task.assignee.email if task.assignee else "",
        items=[ChecklistItemOut.model_validate(item) for item in items],
        files=[TaskFileOut.model_validate(item) for item in files],
    )


@router.get("/by-public/{public_id}", response_model=TaskOut)
def get_by_public(public_id: str, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    task = _query(db).filter(Task.public_id == public_id).first()
    if not task or not _can_access(task, current):
        raise HTTPException(status_code=404, detail="Task not found")
    return _out(task)


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return _out(_load_or_404(db, task_id, current))


@router.post("/{task_id}/close", response_model=TaskOut)
def close_task(task_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    from app.core.config import settings
    from app.services import interakt

    task = _load_or_404(db, task_id, current)
    _guard_active(task)
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


@router.post("/{task_id}/items", response_model=TaskOut)
def add_item(
    task_id: int,
    payload: ChecklistItemCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    task = _load_or_404(db, task_id, current)
    _guard_active(task)
    sort_order = len(task.items or [])
    db.add(TaskItem(task_id=task.id, title=payload.title.strip()[:300], sort_order=sort_order, is_done=False))
    db.commit()
    return _out(_query(db).filter(Task.id == task_id).first())


@router.patch("/{task_id}/items/{item_id}", response_model=TaskOut)
def update_item(
    task_id: int,
    item_id: int,
    payload: ChecklistItemUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    task = _load_or_404(db, task_id, current)
    _guard_active(task)
    item = db.query(TaskItem).filter(TaskItem.id == item_id, TaskItem.task_id == task.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Checklist item not found")
    item.is_done = payload.is_done
    db.commit()
    return _out(_query(db).filter(Task.id == task_id).first())


@router.post("/{task_id}/files", response_model=TaskFileOut, status_code=201)
def upload_task_file(
    task_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    task = _load_or_404(db, task_id, current)
    _guard_active(task)
    original, stored, size, content_type = save_upload(task.id, file)
    row = TaskFile(
        task_id=task.id,
        original_name=original,
        stored_name=stored,
        content_type=content_type,
        size_bytes=size,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return TaskFileOut.model_validate(row)


@router.get("/{task_id}/files/{file_id}")
def download_task_file(
    task_id: int,
    file_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    task = _load_or_404(db, task_id, current)
    row = db.query(TaskFile).filter(TaskFile.id == file_id, TaskFile.task_id == task.id).first()
    if not row:
        raise HTTPException(status_code=404, detail="File not found")
    path = file_path(task.id, row.stored_name)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk")
    return FileResponse(path, filename=row.original_name, media_type=row.content_type)


@router.post("/{task_id}/archive", response_model=TaskOut)
def archive_task(
    task_id: int,
    payload: TaskArchiveIn,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin),
):
    task = _load_or_404(db, task_id, current)
    if _is_archived(task):
        return _out(task)
    reason = payload.reason.strip()
    if len(reason) < 3:
        raise HTTPException(status_code=400, detail="Please enter a reason")
    task.is_archived = True
    task.archive_reason = reason
    task.archived_at = datetime.now(timezone.utc)
    task.archived_by = current.id
    db.commit()
    return _out(_query(db).filter(Task.id == task_id).first())
