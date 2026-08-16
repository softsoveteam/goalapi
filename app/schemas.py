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


class RoleOut(ORMModel):
    id: int
    name: str
    permissions: List[str]
    is_system: bool


class RoleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    permissions: List[str] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=80)
    permissions: Optional[List[str]] = None


class UserOut(ORMModel):
    id: int
    email: EmailStr
    name: str
    role_id: int
    is_active: bool
    role: Optional[RoleOut] = None


class MeOut(UserOut):
    permissions: List[str] = Field(default_factory=list)
    team_ids: List[int] = Field(default_factory=list)


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = Field(min_length=2, max_length=120)
    role_id: int
    is_active: bool = True


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=6)
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    role_id: Optional[int] = None
    is_active: Optional[bool] = None


class TeamMemberOut(ORMModel):
    id: int
    user_id: int
    team_id: int
    designation: str
    user: Optional[UserOut] = None


class TeamMemberIn(BaseModel):
    user_id: int
    designation: str = "Member"


class TeamOut(ORMModel):
    id: int
    name: str
    description: str
    members: List[TeamMemberOut] = Field(default_factory=list)


class TeamCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = ""


class TeamUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    description: Optional[str] = None


class TaskOut(ORMModel):
    id: int
    project_id: int
    title: str
    assigned_to: Optional[int]
    deadline: Optional[datetime]
    is_done: bool
    created_by: int
    assignee: Optional[UserOut] = None


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    assigned_to: Optional[int] = None
    deadline: Optional[datetime] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    assigned_to: Optional[int] = None
    deadline: Optional[datetime] = None
    is_done: Optional[bool] = None


class ProjectOut(ORMModel):
    id: int
    name: str
    description: str
    team_id: int
    created_by: int
    deadline: Optional[datetime]
    status: str
    team: Optional[TeamOut] = None
    task_total: int = 0
    task_done: int = 0
    designations: List[str] = Field(default_factory=list)


class ProjectDetailOut(ProjectOut):
    tasks: List[TaskOut] = Field(default_factory=list)


class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str = ""
    team_id: int
    deadline: Optional[datetime] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=160)
    description: Optional[str] = None
    team_id: Optional[int] = None
    deadline: Optional[datetime] = None
    status: Optional[str] = None


class GoalOut(ORMModel):
    id: int
    title: str
    notes: str
    due_date: Optional[datetime]
    created_by: int
    status: str
    converted_project_id: Optional[int]
    creator: Optional[UserOut] = None


class GoalCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    notes: str = ""
    due_date: Optional[datetime] = None


class GoalUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=200)
    notes: Optional[str] = None
    due_date: Optional[datetime] = None


class GoalConvertIn(BaseModel):
    team_id: int
    first_task_title: Optional[str] = None


class DashboardTaskOut(ORMModel):
    id: int
    title: str
    deadline: Optional[datetime]
    is_done: bool
    project_id: int
    project_name: str


class DashboardOut(BaseModel):
    project_count: int
    open_task_count: int
    done_task_count: int
    team_count: int
    open_goal_count: int
    upcoming_deadlines: List[DashboardTaskOut]
    my_open_tasks: List[DashboardTaskOut]


class PermissionCatalogOut(BaseModel):
    permissions: List[str]
