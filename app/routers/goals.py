from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.core.deps import require_admin
from app.db.models import Goal, User
from app.db.session import get_db
from app.schemas import GoalCreate, GoalOut, GoalUpdate, UserOut

router = APIRouter(prefix="/goals", tags=["goals"])


def _query(db: Session):
    return db.query(Goal).options(joinedload(Goal.creator))


def _out(goal: Goal) -> GoalOut:
    return GoalOut(
        id=goal.id,
        title=goal.title,
        notes=goal.notes,
        due_date=goal.due_date,
        created_by=goal.created_by,
        status=goal.status,
        creator=UserOut.model_validate(goal.creator) if goal.creator else None,
    )


@router.get("", response_model=list)
def list_goals(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return [_out(goal) for goal in _query(db).order_by(Goal.id.desc()).all()]


@router.post("", response_model=GoalOut, status_code=201)
def create_goal(
    payload: GoalCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin),
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
    return _out(_query(db).filter(Goal.id == goal.id).first())


@router.patch("/{goal_id}", response_model=GoalOut)
def update_goal(
    goal_id: int,
    payload: GoalUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    goal = _query(db).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    if payload.title is not None:
        goal.title = payload.title
    if payload.notes is not None:
        goal.notes = payload.notes
    if payload.due_date is not None:
        goal.due_date = payload.due_date
    if payload.status is not None:
        goal.status = payload.status
    db.commit()
    return _out(_query(db).filter(Goal.id == goal_id).first())


@router.delete("/{goal_id}", status_code=204)
def delete_goal(
    goal_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    db.delete(goal)
    db.commit()
