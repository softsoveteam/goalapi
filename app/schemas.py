from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


PRIORITIES = ("urgent", "high", "normal", "low")
RECURRENCE_INTERVALS = ("daily", "weekly", "monthly")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class OtpRequestIn(BaseModel):
    email: EmailStr
    public_id: Optional[str] = None


class OtpVerifyIn(BaseModel):
    email: EmailStr
    code: str = Field(min_length=4, max_length=8)


class UserOut(ORMModel):
    id: int
    kind: str
    email: EmailStr
    name: str
    phone: str
    designation: str
    is_active: bool


class MeOut(UserOut):
    is_admin: bool = False


class EmployeeCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str = Field(min_length=10, max_length=20)
    designation: str = Field(min_length=1, max_length=80)


class EmployeeUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, min_length=10, max_length=20)
    designation: Optional[str] = Field(default=None, min_length=1, max_length=80)
    is_active: Optional[bool] = None


class ChecklistItemOut(ORMModel):
    id: int
    title: str
    is_done: bool
    sort_order: int


class ChecklistItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)


class ChecklistItemUpdate(BaseModel):
    is_done: bool


class TaskFileOut(ORMModel):
    id: int
    original_name: str
    content_type: str
    size_bytes: int
    created_at: datetime


class GoalOut(ORMModel):
    id: int
    title: str
    notes: str
    due_date: Optional[datetime]
    created_by: int
    status: str
    creator: Optional[UserOut] = None
    items: List[ChecklistItemOut] = []


class GoalCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    notes: str = ""
    due_date: Optional[datetime] = None
    items: List[str] = []


class GoalUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=200)
    notes: Optional[str] = None
    due_date: Optional[datetime] = None
    status: Optional[str] = None


class TaskOut(ORMModel):
    id: int
    public_id: str
    title: str
    description: str
    assigned_to: int
    deadline: Optional[datetime]
    is_done: bool
    created_by: int
    created_at: datetime
    closed_at: Optional[datetime]
    priority: str = "normal"
    is_archived: bool = False
    archive_reason: str = ""
    archived_at: Optional[datetime] = None
    archived_by: Optional[int] = None
    duration: Optional[str] = None
    assignee: Optional[UserOut] = None
    creator: Optional[UserOut] = None
    archiver: Optional[UserOut] = None
    items: List[ChecklistItemOut] = []
    files: List[TaskFileOut] = []


class TaskPublicOut(BaseModel):
    public_id: str
    title: str
    description: str
    deadline: Optional[datetime]
    is_done: bool
    is_archived: bool = False
    archive_reason: str = ""
    priority: str = "normal"
    assignee_name: str
    assignee_email: EmailStr
    items: List[ChecklistItemOut] = []
    files: List[TaskFileOut] = []


class TaskCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = ""
    assigned_to: int
    deadline: Optional[datetime] = None
    priority: str = "normal"
    items: List[str] = []


class TaskArchiveIn(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class RecurringRuleOut(ORMModel):
    id: int
    title: str
    description: str
    assigned_to: int
    created_by: int
    priority: str
    interval: str
    send_time: str
    weekday: Optional[int] = None
    day_of_month: Optional[int] = None
    next_run_at: datetime
    is_active: bool
    items: List[str] = []
    assignee: Optional[UserOut] = None


class RecurringRuleCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = ""
    assigned_to: int
    priority: str = "normal"
    interval: str = "daily"
    send_time: str = "09:00"
    weekday: Optional[int] = Field(default=None, ge=0, le=6)
    day_of_month: Optional[int] = Field(default=None, ge=1, le=31)
    items: List[str] = []


class RecurringRuleUpdate(BaseModel):
    is_active: Optional[bool] = None
    send_time: Optional[str] = None


class DashboardTaskOut(BaseModel):
    id: int
    public_id: str
    title: str
    deadline: Optional[datetime]
    is_done: bool
    assignee_name: str
    priority: str = "normal"


class DashboardOut(BaseModel):
    employee_count: int
    open_task_count: int
    done_task_count: int
    open_goal_count: int
    upcoming_deadlines: List[DashboardTaskOut]
    my_open_tasks: List[DashboardTaskOut]
