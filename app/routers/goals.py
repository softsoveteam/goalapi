from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.access import project_query, serialize_project
from app.core.deps import require_permission
from app.db.models import Goal, Project, Task, Team, User
from app.db.session import get_db
from app.schemas import GoalConvertIn, GoalCreate, GoalOut, GoalUpdate, ProjectOut

router = APIRouter(prefix="/goals", tags=["goals"])


def _goal_query(db: Session):
    return db.query(Goal).options(joinedload(Goal.creator).joinedload(User.role))


@router.get("", response_model=list[GoalOut])
def list_goals(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("goals.view")),
):
    return _goal_query(db).order_by(Goal.id.desc()).all()


@router.post("", response_model=GoalOut, status_code=201)
def create_goal(
    payload: GoalCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("goals.manage")),
):
    goal = Goal(
        title=payload.title,
        notes=payload.notes,
        due_date=payload.due_date,
        created_by=current.id,
        status="open",
    )
    db.add(goal)
    db.commit()
    return _goal_query(db).filter(Goal.id == goal.id).first()


@router.patch("/{goal_id}", response_model=GoalOut)
def update_goal(
    goal_id: int,
    payload: GoalUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("goals.manage")),
):
    goal = _goal_query(db).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    if goal.status == "converted":
        raise HTTPException(status_code=400, detail="Converted goals cannot be edited")
    if payload.title is not None:
        goal.title = payload.title
    if payload.notes is not None:
        goal.notes = payload.notes
    if payload.due_date is not None:
        goal.due_date = payload.due_date
    db.commit()
    return _goal_query(db).filter(Goal.id == goal_id).first()


@router.delete("/{goal_id}", status_code=204)
def delete_goal(
    goal_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("goals.manage")),
):
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    db.delete(goal)
    db.commit()


@router.post("/{goal_id}/convert", response_model=ProjectOut)
def convert_goal(
    goal_id: int,
    payload: GoalConvertIn,
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("goals.manage")),
):
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    if goal.status == "converted":
        raise HTTPException(status_code=400, detail="Goal already converted")
    team = db.query(Team).filter(Team.id == payload.team_id).first()
    if not team:
        raise HTTPException(status_code=400, detail="Team not found")
    project = Project(
        name=goal.title,
        description=goal.notes,
        team_id=payload.team_id,
        created_by=current.id,
        deadline=goal.due_date,
        status="active",
    )
    db.add(project)
    db.flush()
    if payload.first_task_title:
        db.add(
            Task(
                project_id=project.id,
                title=payload.first_task_title,
                deadline=goal.due_date,
                created_by=current.id,
                is_done=False,
            )
        )
    goal.status = "converted"
    goal.converted_project_id = project.id
    db.commit()
    loaded = project_query(db).filter(Project.id == project.id).first()
    return serialize_project(loaded)
