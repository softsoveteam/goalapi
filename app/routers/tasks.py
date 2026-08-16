from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.access import can_see_project, can_view_all_projects, project_query, serialize_task, team_ids_for
from app.core.deps import get_current_user, has_permission
from app.db.models import Task, User
from app.db.session import get_db
from app.schemas import TaskOut, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _load_task(db: Session, task_id: int) -> Optional[Task]:
    return (
        db.query(Task)
        .options(joinedload(Task.assignee).joinedload(User.role), joinedload(Task.project))
        .filter(Task.id == task_id)
        .first()
    )


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    task = _load_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    project = project_query(db).filter_by(id=task.project_id).first()
    if not project or not can_see_project(current, project, db):
        raise HTTPException(status_code=404, detail="Task not found")

    assigning = payload.assigned_to is not None and payload.assigned_to != task.assigned_to
    if assigning and not has_permission(current, "tasks.assign"):
        raise HTTPException(status_code=403, detail="You cannot assign tasks")

    if payload.title is not None:
        can_edit = (
            has_permission(current, "tasks.assign")
            or has_permission(current, "projects.create")
            or task.created_by == current.id
        )
        if not can_edit:
            raise HTTPException(status_code=403, detail="Permission denied")
        task.title = payload.title

    if payload.deadline is not None:
        if not (has_permission(current, "tasks.assign") or has_permission(current, "projects.create")):
            raise HTTPException(status_code=403, detail="Permission denied")
        task.deadline = payload.deadline

    if assigning:
        task.assigned_to = payload.assigned_to

    if payload.is_done is not None:
        can_toggle = (
            task.assigned_to == current.id
            or task.created_by == current.id
            or has_permission(current, "tasks.assign")
            or can_view_all_projects(current)
            or project.team_id in team_ids_for(current)
        )
        if not can_toggle:
            raise HTTPException(status_code=403, detail="Permission denied")
        task.is_done = payload.is_done

    db.commit()
    refreshed = _load_task(db, task_id)
    return serialize_task(refreshed)


@router.delete("/{task_id}", status_code=204)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    task = _load_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    project = project_query(db).filter_by(id=task.project_id).first()
    if not project or not can_see_project(current, project, db):
        raise HTTPException(status_code=404, detail="Task not found")
    can_delete = (
        has_permission(current, "tasks.assign")
        or has_permission(current, "projects.create")
        or task.created_by == current.id
    )
    if not can_delete:
        raise HTTPException(status_code=403, detail="Permission denied")
    db.delete(task)
    db.commit()
