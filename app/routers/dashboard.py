from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user
from app.core.security import is_admin
from app.db.models import Goal, Task, User
from app.db.session import get_db
from app.schemas import DashboardOut, DashboardTaskOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    q = db.query(Task).options(joinedload(Task.assignee)).order_by(Task.id.desc())
    if not is_admin(current):
        q = q.filter(Task.assigned_to == current.id)
    tasks = q.all()
    open_tasks = [t for t in tasks if not t.is_done]
    done_tasks = [t for t in tasks if t.is_done]
    upcoming = sorted([t for t in open_tasks if t.deadline], key=lambda t: t.deadline)[:8]
    my_open = [t for t in open_tasks if t.assigned_to == current.id][:8]

    def to_out(task):
        return DashboardTaskOut(
            id=task.id,
            public_id=task.public_id,
            title=task.title,
            deadline=task.deadline,
            is_done=task.is_done,
            assignee_name=task.assignee.name if task.assignee else "",
        )

    employee_count = 0
    open_goals = 0
    if is_admin(current):
        employee_count = db.query(User).filter(User.kind == "employee").count()
        open_goals = db.query(Goal).filter(Goal.status == "open").count()

    return DashboardOut(
        employee_count=employee_count,
        open_task_count=len(open_tasks),
        done_task_count=len(done_tasks),
        open_goal_count=open_goals,
        upcoming_deadlines=[to_out(t) for t in upcoming],
        my_open_tasks=[to_out(t) for t in my_open],
    )
