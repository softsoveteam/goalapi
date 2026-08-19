from datetime import date, datetime, timezone
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_public_id() -> str:
    return uuid4().hex


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(32), default="")
    designation: Mapped[str] = mapped_column(String(80), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    assigned_tasks: Mapped[List["Task"]] = relationship(
        back_populates="assignee",
        foreign_keys="Task.assigned_to",
    )


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    notes: Mapped[str] = mapped_column(Text, default="")
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(32), default="open")
    priority: Mapped[str] = mapped_column(String(20), default="normal")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    creator: Mapped["User"] = relationship(foreign_keys=[created_by])
    items: Mapped[List["GoalItem"]] = relationship(
        back_populates="goal",
        cascade="all, delete-orphan",
        order_by="GoalItem.sort_order",
    )
    logs: Mapped[List["GoalLog"]] = relationship(
        back_populates="goal",
        cascade="all, delete-orphan",
    )


class GoalItem(Base):
    __tablename__ = "goal_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    goal_id: Mapped[int] = mapped_column(ForeignKey("goals.id", ondelete="CASCADE"), index=True)
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("goal_items.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(300))
    is_done: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    goal: Mapped["Goal"] = relationship(back_populates="items")


class GoalLog(Base):
    __tablename__ = "goal_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    goal_id: Mapped[int] = mapped_column(ForeignKey("goals.id", ondelete="CASCADE"), index=True)
    body: Mapped[str] = mapped_column(Text)
    happened_on: Mapped[date] = mapped_column(Date, index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    goal: Mapped["Goal"] = relationship(back_populates="logs")
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, default=new_public_id)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    assigned_to: Mapped[int] = mapped_column(ForeignKey("users.id"))
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_done: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="normal")
    reminded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    warned_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    recurring_rule_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("recurring_rules.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    archive_reason: Mapped[str] = mapped_column(Text, default="")
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    archived_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)

    assignee: Mapped["User"] = relationship(foreign_keys=[assigned_to], back_populates="assigned_tasks")
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])
    archiver: Mapped[Optional["User"]] = relationship(foreign_keys=[archived_by])
    items: Mapped[List["TaskItem"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskItem.sort_order",
    )
    files: Mapped[List["TaskFile"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )


class TaskItem(Base):
    __tablename__ = "task_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    is_done: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    task: Mapped["Task"] = relationship(back_populates="items")


class TaskFile(Base):
    __tablename__ = "task_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    original_name: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str] = mapped_column(String(80), unique=True)
    content_type: Mapped[str] = mapped_column(String(120), default="application/octet-stream")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    task: Mapped["Task"] = relationship(back_populates="files")


class RecurringRule(Base):
    __tablename__ = "recurring_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    assigned_to: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    priority: Mapped[str] = mapped_column(String(20), default="normal")
    interval: Mapped[str] = mapped_column(String(20), default="daily")
    send_time: Mapped[str] = mapped_column(String(5), default="09:00")
    weekday: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    day_of_month: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    next_run_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    checklist_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    assignee: Mapped["User"] = relationship(foreign_keys=[assigned_to])
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])


class JobRun(Base):
    __tablename__ = "job_runs"
    __table_args__ = (UniqueConstraint("job_name", "run_date", name="uq_job_runs_name_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_name: Mapped[str] = mapped_column(String(40))
    run_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class OtpCode(Base):
    __tablename__ = "otp_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    purpose: Mapped[str] = mapped_column(String(32), default="login")
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class CarePerson(Base):
    __tablename__ = "care_people"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(32))
    relation: Mapped[str] = mapped_column(String(40), default="custom")
    notes: Mapped[str] = mapped_column(Text, default="")
    last_period_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    cycle_days: Mapped[int] = mapped_column(Integer, default=28)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    creator: Mapped["User"] = relationship(foreign_keys=[created_by])
    reminders: Mapped[List["CareReminder"]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
    )


class CareReminder(Base):
    __tablename__ = "care_reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("care_people.id", ondelete="CASCADE"), index=True)
    niche: Mapped[str] = mapped_column(String(40), default="take_care")
    interval: Mapped[str] = mapped_column(String(20), default="daily")
    send_time: Mapped[str] = mapped_column(String(5), default="20:00")
    weekday: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    day_of_month: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    custom_text: Mapped[str] = mapped_column(Text, default="")
    next_run_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    last_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    person: Mapped["CarePerson"] = relationship(back_populates="reminders")
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])
