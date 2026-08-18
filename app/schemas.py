from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


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


class GoalOut(ORMModel):
    id: int
    title: str
    notes: str
    due_date: Optional[datetime]
    created_by: int
    status: str
    creator: Optional[UserOut] = None


class GoalCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    notes: str = ""
    due_date: Optional[datetime] = None


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
    duration: Optional[str] = None
    assignee: Optional[UserOut] = None
    creator: Optional[UserOut] = None


class TaskPublicOut(BaseModel):
    public_id: str
    title: str
    description: str
    deadline: Optional[datetime]
    is_done: bool
    assignee_name: str
    assignee_email: EmailStr


class TaskCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = ""
    assigned_to: int
    deadline: Optional[datetime] = None


class DashboardTaskOut(BaseModel):
    id: int
    public_id: str
    title: str
    deadline: Optional[datetime]
    is_done: bool
    assignee_name: str


class DashboardOut(BaseModel):
    employee_count: int
    open_task_count: int
    done_task_count: int
    open_goal_count: int
    upcoming_deadlines: List[DashboardTaskOut]
    my_open_tasks: List[DashboardTaskOut]
