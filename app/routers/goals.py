from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.deps import require_admin
from app.db.models import Goal, GoalItem, User
from app.db.session import get_db
from app.schemas import ChecklistItemCreate, ChecklistItemOut, ChecklistItemUpdate, GoalCreate, GoalOut, GoalUpdate, UserOut

router = APIRouter(prefix="/goals", tags=["goals"])


def _query(db: Session):
    return db.query(Goal).options(joinedload(Goal.creator), selectinload(Goal.items))


def _out(goal: Goal) -> GoalOut:
    items = sorted(goal.items or [], key=lambda item: (item.sort_order, item.id))
    return GoalOut(
        id=goal.id,
        title=goal.title,
        notes=goal.notes,
        due_date=goal.due_date,
        created_by=goal.created_by,
        status=goal.status,
        creator=UserOut.model_validate(goal.creator) if goal.creator else None,
        items=[ChecklistItemOut.model_validate(item) for item in items],
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
    for index, title in enumerate(payload.items or []):
        text = str(title).strip()
        if not text:
            continue
        db.add(GoalItem(goal_id=goal.id, title=text[:300], sort_order=index, is_done=False))
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


@router.post("/{goal_id}/items", response_model=GoalOut)
def add_item(
    goal_id: int,
    payload: ChecklistItemCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    goal = _query(db).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    db.add(GoalItem(goal_id=goal.id, title=payload.title.strip()[:300], sort_order=len(goal.items or []), is_done=False))
    db.commit()
    return _out(_query(db).filter(Goal.id == goal_id).first())


@router.patch("/{goal_id}/items/{item_id}", response_model=GoalOut)
def update_item(
    goal_id: int,
    item_id: int,
    payload: ChecklistItemUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    goal = _query(db).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    item = db.query(GoalItem).filter(GoalItem.id == item_id, GoalItem.goal_id == goal.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Checklist item not found")
    item.is_done = payload.is_done
    db.commit()
    return _out(_query(db).filter(Goal.id == goal_id).first())


@router.delete("/{goal_id}", status_code=204)
def delete_goal(
    goal_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    goal = _query(db).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    db.delete(goal)
    db.commit()
