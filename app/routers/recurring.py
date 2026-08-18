import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.core.deps import require_admin
from app.db.models import RecurringRule, Task, User
from app.db.session import get_db
from app.schemas import (
    PRIORITIES,
    RECURRENCE_INTERVALS,
    RecurringRuleCreate,
    RecurringRuleOut,
    RecurringRuleUpdate,
    UserOut,
)
from app.services.ist import as_utc_naive, compute_next_run

router = APIRouter(prefix="/recurring", tags=["recurring"])


def _items(rule: RecurringRule):
    try:
        raw = json.loads(rule.checklist_json or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item).strip()]


def _out(rule: RecurringRule) -> RecurringRuleOut:
    return RecurringRuleOut(
        id=rule.id,
        title=rule.title,
        description=rule.description,
        assigned_to=rule.assigned_to,
        created_by=rule.created_by,
        priority=rule.priority or "normal",
        interval=rule.interval,
        send_time=rule.send_time,
        weekday=rule.weekday,
        day_of_month=rule.day_of_month,
        next_run_at=rule.next_run_at,
        is_active=rule.is_active,
        items=_items(rule),
        assignee=UserOut.model_validate(rule.assignee) if rule.assignee else None,
    )


def _query(db: Session):
    return db.query(RecurringRule).options(joinedload(RecurringRule.assignee))


@router.get("", response_model=list)
def list_rules(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return [_out(rule) for rule in _query(db).order_by(RecurringRule.id.desc()).all()]


@router.post("", response_model=RecurringRuleOut, status_code=201)
def create_rule(
    payload: RecurringRuleCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin),
):
    assignee = db.query(User).filter(User.id == payload.assigned_to, User.kind == "employee", User.is_active.is_(True)).first()
    if not assignee:
        raise HTTPException(status_code=400, detail="Select an active employee")
    interval = (payload.interval or "daily").lower()
    if interval not in RECURRENCE_INTERVALS:
        raise HTTPException(status_code=400, detail="Interval must be daily, weekly, or monthly")
    priority = (payload.priority or "normal").lower()
    if priority not in PRIORITIES:
        raise HTTPException(status_code=400, detail="Priority must be urgent, high, normal, or low")
    if interval == "weekly" and payload.weekday is None:
        raise HTTPException(status_code=400, detail="Pick a weekday for weekly tasks")
    send_time = payload.send_time or "09:00"
    if len(send_time) < 4 or ":" not in send_time:
        raise HTTPException(status_code=400, detail="Send time must be HH:MM")
    next_run = as_utc_naive(
        compute_next_run(interval, send_time, payload.weekday, payload.day_of_month)
    )
    titles = [item.strip() for item in payload.items if item and item.strip()]
    rule = RecurringRule(
        title=payload.title,
        description=payload.description,
        assigned_to=assignee.id,
        created_by=current.id,
        priority=priority,
        interval=interval,
        send_time=send_time,
        weekday=payload.weekday,
        day_of_month=payload.day_of_month,
        next_run_at=next_run,
        is_active=True,
        checklist_json=json.dumps(titles),
    )
    db.add(rule)
    db.commit()
    return _out(_query(db).filter(RecurringRule.id == rule.id).first())


@router.patch("/{rule_id}", response_model=RecurringRuleOut)
def update_rule(
    rule_id: int,
    payload: RecurringRuleUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    rule = _query(db).filter(RecurringRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Recurring task not found")
    if payload.is_active is not None:
        rule.is_active = payload.is_active
        if payload.is_active:
            rule.next_run_at = as_utc_naive(
                compute_next_run(rule.interval, payload.send_time or rule.send_time, rule.weekday, rule.day_of_month)
            )
    if payload.send_time is not None:
        rule.send_time = payload.send_time
        rule.next_run_at = as_utc_naive(
            compute_next_run(rule.interval, rule.send_time, rule.weekday, rule.day_of_month)
        )
    db.commit()
    return _out(_query(db).filter(RecurringRule.id == rule_id).first())


@router.delete("/{rule_id}", status_code=204)
def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    rule = db.query(RecurringRule).filter(RecurringRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Recurring task not found")
    db.query(Task).filter(Task.recurring_rule_id == rule_id).update({Task.recurring_rule_id: None})
    db.delete(rule)
    db.commit()
