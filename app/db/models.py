from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    permissions: Mapped[List] = mapped_column(JSON, default=list)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    users: Mapped[List["User"]] = relationship(back_populates="role")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(120))
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    role: Mapped["Role"] = relationship(back_populates="users")
    team_memberships: Mapped[List["TeamMember"]] = relationship(back_populates="user")


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    members: Mapped[List["TeamMember"]] = relationship(back_populates="team", cascade="all, delete-orphan")
    projects: Mapped[List["Project"]] = relationship(back_populates="team")


class TeamMember(Base):
    __tablename__ = "team_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    designation: Mapped[str] = mapped_column(String(80), default="Member")

    user: Mapped["User"] = relationship(back_populates="team_memberships")
    team: Mapped["Team"] = relationship(back_populates="members")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    team: Mapped["Team"] = relationship(back_populates="projects")
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])
    tasks: Mapped[List["Task"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    title: Mapped[str] = mapped_column(String(200))
    assigned_to: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_done: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    project: Mapped["Project"] = relationship(back_populates="tasks")
    assignee: Mapped[Optional["User"]] = relationship(foreign_keys=[assigned_to])
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    notes: Mapped[str] = mapped_column(Text, default="")
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(32), default="open")
    converted_project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    creator: Mapped["User"] = relationship(foreign_keys=[created_by])
    converted_project: Mapped[Optional["Project"]] = relationship(foreign_keys=[converted_project_id])
