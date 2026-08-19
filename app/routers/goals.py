from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.deps import require_admin
from app.db.models import Goal, GoalItem, GoalLog, User
from app.db.session import get_db
from app.schemas import (
    ChecklistItemCreate,
    ChecklistItemOut,
    ChecklistItemUpdate,
    GoalCreate,
    GoalLogCreate,
    GoalLogOut,
    GoalOut,
    GoalReorderIn,
    GoalUpdate,
    UserOut,
)
from app.services.ist import now_ist

router = APIRouter(prefix="/goals", tags=["goals"])


def _priority_from_rank(index: int) -> str:
    if index < 5:
        return "urgent"
    if index < 10:
        return "high"
    if index < 20:
        return "normal"
    return "low"


def _apply_ranks(db: Session, ids: List[int]) -> None:
    for index, goal_id in enumerate(ids):
        goal = db.query(Goal).filter(Goal.id == goal_id).first()
        if not goal:
            continue
        goal.sort_order = index
        goal.priority = _priority_from_rank(index)


def _query(db: Session):
    return db.query(Goal).options(
        joinedload(Goal.creator),
        selectinload(Goal.items),
        selectinload(Goal.logs).joinedload(GoalLog.creator),
    )


def _item_out(item: GoalItem, children: List[ChecklistItemOut]) -> ChecklistItemOut:
    return ChecklistItemOut(
        id=item.id,
        title=item.title,
        is_done=item.is_done,
        sort_order=item.sort_order,
        parent_id=item.parent_id,
        children=children,
    )


def _nest_items(items: List[GoalItem]) -> List[ChecklistItemOut]:
    by_parent: Dict[Optional[int], List[GoalItem]] = {}
    for item in items or []:
        by_parent.setdefault(item.parent_id, []).append(item)

    def build(parent_id: Optional[int]) -> List[ChecklistItemOut]:
        rows = sorted(by_parent.get(parent_id, []), key=lambda row: (row.sort_order, row.id))
        return [_item_out(row, build(row.id)) for row in rows]

    return build(None)


def _out(goal: Goal) -> GoalOut:
    logs = sorted(goal.logs or [], key=lambda log: (log.happened_on, log.id), reverse=True)
    return GoalOut(
        id=goal.id,
        title=goal.title,
        notes=goal.notes or "",
        due_date=goal.due_date,
        created_by=goal.created_by,
        status=goal.status,
        priority=goal.priority or "normal",
        sort_order=goal.sort_order or 0,
        creator=UserOut.model_validate(goal.creator) if goal.creator else None,
        items=_nest_items(goal.items or []),
        logs=[
            GoalLogOut(
                id=log.id,
                body=log.body,
                happened_on=log.happened_on,
                created_at=log.created_at,
                created_by=log.created_by,
                creator=UserOut.model_validate(log.creator) if log.creator else None,
            )
            for log in logs
        ],
    )


@router.get("", response_model=list)
def list_goals(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return [_out(goal) for goal in _query(db).order_by(Goal.sort_order, Goal.id).all()]


@router.post("", response_model=GoalOut, status_code=201)
def create_goal(
    payload: GoalCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin),
):
    max_sort = db.query(func.max(Goal.sort_order)).scalar()
    sort_order = (max_sort + 1) if max_sort is not None else 0
    goal = Goal(
        title=payload.title,
        notes=payload.notes,
        due_date=payload.due_date,
        created_by=current.id,
        status="open",
        sort_order=sort_order,
        priority=_priority_from_rank(sort_order),
    )
    db.add(goal)
    db.commit()
    for index, title in enumerate(payload.items or []):
        text = str(title).strip()
        if not text:
            continue
        db.add(GoalItem(goal_id=goal.id, title=text[:300], sort_order=index, is_done=False, parent_id=None))
    db.commit()
    return _out(_query(db).filter(Goal.id == goal.id).first())


@router.post("/reorder", response_model=list)
def reorder_goals(
    payload: GoalReorderIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    ids = [int(goal_id) for goal_id in payload.ids]
    current_ids = [row.id for row in db.query(Goal.id).order_by(Goal.sort_order, Goal.id).all()]
    seen = set()
    ordered: List[int] = []
    for goal_id in ids:
        if goal_id in current_ids and goal_id not in seen:
            ordered.append(goal_id)
            seen.add(goal_id)
    for goal_id in current_ids:
        if goal_id not in seen:
            ordered.append(goal_id)
    _apply_ranks(db, ordered)
    db.commit()
    return [_out(goal) for goal in _query(db).order_by(Goal.sort_order, Goal.id).all()]


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
    parent_id = payload.parent_id
    if parent_id is not None:
        parent = db.query(GoalItem).filter(GoalItem.id == parent_id, GoalItem.goal_id == goal.id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent task not found")
        if parent.parent_id is not None:
            raise HTTPException(status_code=400, detail="Subtasks can only be added under a main task")
    siblings = [item for item in (goal.items or []) if item.parent_id == parent_id]
    db.add(
        GoalItem(
            goal_id=goal.id,
            title=payload.title.strip()[:300],
            sort_order=len(siblings),
            is_done=False,
            parent_id=parent_id,
        )
    )
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


@router.post("/{goal_id}/logs", response_model=GoalOut)
def add_log(
    goal_id: int,
    payload: GoalLogCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin),
):
    goal = _query(db).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    body = payload.body.strip()
    if not body:
        raise HTTPException(status_code=400, detail="Write what happened today")
    db.add(
        GoalLog(
            goal_id=goal.id,
            body=body[:2000],
            happened_on=now_ist().date(),
            created_by=current.id,
        )
    )
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
    remaining = [row.id for row in db.query(Goal.id).filter(Goal.id != goal_id).order_by(Goal.sort_order, Goal.id).all()]
    db.delete(goal)
    db.commit()
    _apply_ranks(db, remaining)
    db.commit()
