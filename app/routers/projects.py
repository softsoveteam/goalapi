from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.access import can_see_project, can_view_all_projects, project_query, serialize_project, serialize_task, team_ids_for
from app.core.deps import get_current_user, has_permission, require_permission
from app.db.models import Project, Task, Team, User
from app.db.session import get_db
from app.schemas import ProjectCreate, ProjectDetailOut, ProjectOut, ProjectUpdate, TaskCreate, TaskOut

router = APIRouter(prefix="/projects", tags=["projects"])


def _get_visible_or_404(db: Session, user: User, project_id: int) -> Project:
    project = project_query(db).filter(Project.id == project_id).first()
    if not project or not can_see_project(user, project, db):
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    projects = project_query(db).order_by(Project.id.desc()).all()
    if can_view_all_projects(current):
        visible = projects
    else:
        visible = [p for p in projects if can_see_project(current, p, db)]
    return [serialize_project(p) for p in visible]


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("projects.create")),
):
    team = db.query(Team).filter(Team.id == payload.team_id).first()
    if not team:
        raise HTTPException(status_code=400, detail="Team not found")
    project = Project(
        name=payload.name,
        description=payload.description,
        team_id=payload.team_id,
        created_by=current.id,
        deadline=payload.deadline,
        status="active",
    )
    db.add(project)
    db.commit()
    loaded = project_query(db).filter(Project.id == project.id).first()
    return serialize_project(loaded)


@router.get("/{project_id}", response_model=ProjectDetailOut)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    project = _get_visible_or_404(db, current, project_id)
    base = serialize_project(project)
    tasks = project.tasks
    if not can_view_all_projects(current) and not has_permission(current, "tasks.assign"):
        if project.team_id not in team_ids_for(current) and project.created_by != current.id:
            tasks = [t for t in tasks if t.assigned_to == current.id]
    return ProjectDetailOut(**base.model_dump(), tasks=[serialize_task(t) for t in tasks])


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    if not has_permission(current, "projects.create") and not can_view_all_projects(current):
        raise HTTPException(status_code=403, detail="Permission denied")
    project = _get_visible_or_404(db, current, project_id)
    if payload.name is not None:
        project.name = payload.name
    if payload.description is not None:
        project.description = payload.description
    if payload.team_id is not None:
        team = db.query(Team).filter(Team.id == payload.team_id).first()
        if not team:
            raise HTTPException(status_code=400, detail="Team not found")
        project.team_id = payload.team_id
    if payload.deadline is not None:
        project.deadline = payload.deadline
    if payload.status is not None:
        project.status = payload.status
    db.commit()
    return serialize_project(project_query(db).filter(Project.id == project_id).first())


@router.delete("/{project_id}", status_code=204)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    if not has_permission(current, "projects.create") and not can_view_all_projects(current):
        raise HTTPException(status_code=403, detail="Permission denied")
    project = _get_visible_or_404(db, current, project_id)
    db.delete(project)
    db.commit()


@router.post("/{project_id}/tasks", response_model=TaskOut, status_code=201)
def create_task(
    project_id: int,
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    project = _get_visible_or_404(db, current, project_id)
    can_create = (
        has_permission(current, "projects.create")
        or has_permission(current, "tasks.assign")
        or project.created_by == current.id
        or project.team_id in team_ids_for(current)
    )
    if not can_create:
        raise HTTPException(status_code=403, detail="Permission denied")
    assigned_to = payload.assigned_to
    if assigned_to is not None and not has_permission(current, "tasks.assign"):
        if assigned_to != current.id:
            raise HTTPException(status_code=403, detail="You cannot assign tasks to others")
    task = Task(
        project_id=project.id,
        title=payload.title,
        assigned_to=assigned_to,
        deadline=payload.deadline,
        created_by=current.id,
        is_done=False,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    loaded = project_query(db).filter(Project.id == project_id).first()
    created = next(t for t in loaded.tasks if t.id == task.id)
    return serialize_task(created)
