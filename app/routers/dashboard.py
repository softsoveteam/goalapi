from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.access import can_see_project, can_view_all_projects
from app.core.deps import get_current_user, has_permission
from app.db.models import Goal, Project, Task, Team, User
from app.db.session import get_db
from app.schemas import DashboardOut, DashboardTaskOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    projects = db.query(Project).options(joinedload(Project.tasks)).all()
    visible_projects = [p for p in projects if can_see_project(current, p, db)]
    visible_ids = {p.id for p in visible_projects}

    if visible_ids:
        tasks = db.query(Task).options(joinedload(Task.project)).filter(Task.project_id.in_(visible_ids)).all()
    else:
        tasks = []
    if not can_view_all_projects(current) and not has_permission(current, "tasks.assign"):
        scoped = []
        for task in tasks:
            if task.assigned_to == current.id or task.project.created_by == current.id:
                scoped.append(task)
            elif task.project.team_id in {m.team_id for m in current.team_memberships}:
                scoped.append(task)
        tasks = scoped

    open_tasks = [t for t in tasks if not t.is_done]
    done_tasks = [t for t in tasks if t.is_done]
    my_open = [t for t in open_tasks if t.assigned_to == current.id]

    upcoming = sorted(
        [t for t in open_tasks if t.deadline],
        key=lambda t: t.deadline,
    )[:8]

    teams_count = db.query(Team).count() if can_view_all_projects(current) or has_permission(current, "teams.manage") else len({m.team_id for m in current.team_memberships})
    open_goals = 0
    if has_permission(current, "goals.view"):
        open_goals = db.query(Goal).filter(Goal.status == "open").count()

    def to_out(task: Task) -> DashboardTaskOut:
        return DashboardTaskOut(
            id=task.id,
            title=task.title,
            deadline=task.deadline,
            is_done=task.is_done,
            project_id=task.project_id,
            project_name=task.project.name if task.project else "",
        )

    return DashboardOut(
        project_count=len(visible_projects),
        open_task_count=len(open_tasks),
        done_task_count=len(done_tasks),
        team_count=teams_count,
        open_goal_count=open_goals,
        upcoming_deadlines=[to_out(t) for t in upcoming],
        my_open_tasks=[to_out(t) for t in my_open[:8]],
    )
