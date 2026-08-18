import hashlib
import hmac
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.deps import require_admin, require_care
from app.core.security import create_care_token
from app.db.models import CarePerson, CareReminder, User
from app.db.session import get_db
from app.schemas import (
    CareNicheOut,
    CarePersonCreate,
    CarePersonOut,
    CarePersonUpdate,
    CareReminderCreate,
    CareReminderOut,
    CareReminderUpdate,
    CareUnlockIn,
    CareUnlockOut,
)
from app.services.care_messages import NICHE_LABELS, NICHES, pick_message, preview_message
from app.services.ist import as_utc_naive, compute_next_run, compute_period_next_run, now_ist, period_window

router = APIRouter(prefix="/care", tags=["care"])
RELATIONS = ("mum", "wife", "dad", "sister", "custom")


def _as_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    return value


def _next_period_dt(person: CarePerson):
    start = _as_date(person.last_period_start)
    if not start:
        return None
    _wstart, _wend, expected = period_window(start, person.cycle_days or 28, now_ist().date())
    return datetime(expected.year, expected.month, expected.day)


def _person_out(person: CarePerson) -> CarePersonOut:
    return CarePersonOut(
        id=person.id,
        name=person.name,
        phone=person.phone,
        relation=person.relation,
        notes=person.notes or "",
        last_period_start=datetime.combine(_as_date(person.last_period_start), datetime.min.time()) if person.last_period_start else None,
        cycle_days=person.cycle_days or 28,
        is_active=person.is_active,
        next_period_start=_next_period_dt(person),
    )


def _next_run(person: CarePerson, payload) -> datetime:
    interval = payload.interval
    if payload.niche == "periods":
        interval = "period_window"
    if interval == "period_window":
        start = _as_date(person.last_period_start)
        if not start:
            raise HTTPException(status_code=400, detail="Set last period date for this person first")
        return as_utc_naive(compute_period_next_run(start, person.cycle_days or 28, payload.send_time))
    return as_utc_naive(
        compute_next_run(interval, payload.send_time, payload.weekday, payload.day_of_month)
    )


def _reminder_out(row: CareReminder) -> CareReminderOut:
    person = row.person
    preview = pick_message(row.niche, row.person_id, now_ist().date(), row.custom_text)
    return CareReminderOut(
        id=row.id,
        person_id=row.person_id,
        niche=row.niche,
        interval=row.interval,
        send_time=row.send_time,
        weekday=row.weekday,
        day_of_month=row.day_of_month,
        custom_text=row.custom_text or "",
        next_run_at=row.next_run_at,
        last_sent_at=row.last_sent_at,
        is_active=row.is_active,
        preview=preview,
        person=_person_out(person) if person else None,
    )


@router.post("/unlock", response_model=CareUnlockOut)
def unlock_care(payload: CareUnlockIn, current: User = Depends(require_admin)):
    expected = hashlib.sha256((settings.care_tab_password or "").encode("utf-8")).digest()
    given = hashlib.sha256((payload.password or "").encode("utf-8")).digest()
    if not hmac.compare_digest(given, expected):
        raise HTTPException(status_code=403, detail="Wrong password")
    return CareUnlockOut(access_token=create_care_token(str(current.id)))


@router.get("/niches", response_model=list)
def list_niches(_: User = Depends(require_care)):
    return [
        CareNicheOut(key=key, label=NICHE_LABELS[key], preview=preview_message(key if key != "custom" else "take_care"))
        for key in NICHES
    ]


@router.get("/people", response_model=list)
def list_people(db: Session = Depends(get_db), _: User = Depends(require_care)):
    rows = db.query(CarePerson).order_by(CarePerson.id.desc()).all()
    return [_person_out(row) for row in rows]


@router.post("/people", response_model=CarePersonOut, status_code=201)
def create_person(payload: CarePersonCreate, db: Session = Depends(get_db), current: User = Depends(require_care)):
    relation = (payload.relation or "custom").lower()
    if relation not in RELATIONS:
        relation = "custom"
    person = CarePerson(
        name=payload.name.strip(),
        phone="".join(ch for ch in payload.phone if ch.isdigit() or ch == "+"),
        relation=relation,
        notes=payload.notes or "",
        last_period_start=_as_date(payload.last_period_start),
        cycle_days=payload.cycle_days or 28,
        is_active=True,
        created_by=current.id,
    )
    db.add(person)
    db.commit()
    db.refresh(person)
    return _person_out(person)


@router.patch("/people/{person_id}", response_model=CarePersonOut)
def update_person(
    person_id: int,
    payload: CarePersonUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_care),
):
    person = db.query(CarePerson).filter(CarePerson.id == person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    if payload.name is not None:
        person.name = payload.name.strip()
    if payload.phone is not None:
        person.phone = "".join(ch for ch in payload.phone if ch.isdigit() or ch == "+")
    if payload.relation is not None:
        person.relation = payload.relation.lower() if payload.relation.lower() in RELATIONS else "custom"
    if payload.notes is not None:
        person.notes = payload.notes
    if payload.cycle_days is not None:
        person.cycle_days = payload.cycle_days
    if payload.last_period_start is not None:
        person.last_period_start = _as_date(payload.last_period_start)
    if payload.period_started_today:
        person.last_period_start = now_ist().date()
    db.commit()
    db.refresh(person)
    return _person_out(person)


@router.delete("/people/{person_id}", status_code=204)
def delete_person(person_id: int, db: Session = Depends(get_db), _: User = Depends(require_care)):
    person = db.query(CarePerson).filter(CarePerson.id == person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    db.delete(person)
    db.commit()


@router.get("/reminders", response_model=list)
def list_reminders(db: Session = Depends(get_db), _: User = Depends(require_care)):
    rows = (
        db.query(CareReminder)
        .options(joinedload(CareReminder.person))
        .order_by(CareReminder.id.desc())
        .all()
    )
    return [_reminder_out(row) for row in rows]


@router.post("/reminders", response_model=CareReminderOut, status_code=201)
def create_reminder(
    payload: CareReminderCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_care),
):
    person = db.query(CarePerson).filter(CarePerson.id == payload.person_id, CarePerson.is_active.is_(True)).first()
    if not person:
        raise HTTPException(status_code=400, detail="Select a person")
    niche = payload.niche if payload.niche in NICHES else "take_care"
    interval = payload.interval if payload.interval in ("daily", "weekly", "monthly", "period_window") else "daily"
    if niche == "periods":
        interval = "period_window"
    if niche == "custom" and not (payload.custom_text or "").strip():
        raise HTTPException(status_code=400, detail="Write a custom message")
    if interval == "weekly" and payload.weekday is None:
        raise HTTPException(status_code=400, detail="Pick a weekday")
    fake = type("P", (), {})()
    fake.interval = interval
    fake.niche = niche
    fake.send_time = payload.send_time
    fake.weekday = payload.weekday
    fake.day_of_month = payload.day_of_month
    next_run = _next_run(person, fake)
    row = CareReminder(
        person_id=person.id,
        niche=niche,
        interval=interval,
        send_time=payload.send_time or "20:00",
        weekday=payload.weekday,
        day_of_month=payload.day_of_month,
        custom_text=(payload.custom_text or "").strip(),
        next_run_at=next_run,
        is_active=True,
        created_by=current.id,
    )
    db.add(row)
    db.commit()
    loaded = db.query(CareReminder).options(joinedload(CareReminder.person)).filter(CareReminder.id == row.id).first()
    return _reminder_out(loaded)


@router.patch("/reminders/{reminder_id}", response_model=CareReminderOut)
def update_reminder(
    reminder_id: int,
    payload: CareReminderUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_care),
):
    row = db.query(CareReminder).options(joinedload(CareReminder.person)).filter(CareReminder.id == reminder_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Reminder not found")
    if payload.is_active is not None:
        row.is_active = payload.is_active
        if payload.is_active:
            fake = type("P", (), {})()
            fake.interval = row.interval
            fake.niche = row.niche
            fake.send_time = payload.send_time or row.send_time
            fake.weekday = row.weekday
            fake.day_of_month = row.day_of_month
            row.next_run_at = _next_run(row.person, fake)
    if payload.send_time is not None:
        row.send_time = payload.send_time
        fake = type("P", (), {})()
        fake.interval = row.interval
        fake.niche = row.niche
        fake.send_time = row.send_time
        fake.weekday = row.weekday
        fake.day_of_month = row.day_of_month
        row.next_run_at = _next_run(row.person, fake)
    if payload.custom_text is not None:
        row.custom_text = payload.custom_text.strip()
    db.commit()
    loaded = db.query(CareReminder).options(joinedload(CareReminder.person)).filter(CareReminder.id == reminder_id).first()
    return _reminder_out(loaded)


@router.delete("/reminders/{reminder_id}", status_code=204)
def delete_reminder(reminder_id: int, db: Session = Depends(get_db), _: User = Depends(require_care)):
    row = db.query(CareReminder).filter(CareReminder.id == reminder_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Reminder not found")
    db.delete(row)
    db.commit()
