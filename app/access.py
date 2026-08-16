from sqlalchemy.orm import Session, joinedload

from app.core.deps import has_permission
from app.db.models import Project, Task, Team, TeamMember, User
from app.schemas import ProjectOut, TaskOut, TeamOut, UserOut


def team_ids_for(user: User) -> set[int]:
    return {m.team_id for m in user.team_memberships}


def can_view_all_projects(user: User) -> bool:
    return has_permission(user, "projects.view_all")


def can_see_project(user: User, project: Project, db: Session) -> bool:
    if can_view_all_projects(user):
        return True
    if project.created_by == user.id:
        return True
    if project.team_id in team_ids_for(user):
        return True
    assigned = (
        db.query(Task.id)
        .filter(Task.project_id == project.id, Task.assigned_to == user.id)
        .first()
    )
    return assigned is not None


def project_query(db: Session):
    return db.query(Project).options(
        joinedload(Project.team).joinedload(Team.members).joinedload(TeamMember.user).joinedload(User.role),
        joinedload(Project.tasks).joinedload(Task.assignee).joinedload(User.role),
    )


def serialize_project(project: Project) -> ProjectOut:
    tasks = project.tasks or []
    designations = sorted({m.designation for m in (project.team.members if project.team else []) if m.designation})
    return ProjectOut(
        id=project.id,
        name=project.name,
        description=project.description,
        team_id=project.team_id,
        created_by=project.created_by,
        deadline=project.deadline,
        status=project.status,
        team=TeamOut.model_validate(project.team) if project.team else None,
        task_total=len(tasks),
        task_done=sum(1 for t in tasks if t.is_done),
        designations=designations,
    )


def serialize_task(task: Task) -> TaskOut:
    return TaskOut(
        id=task.id,
        project_id=task.project_id,
        title=task.title,
        assigned_to=task.assigned_to,
        deadline=task.deadline,
        is_done=task.is_done,
        created_by=task.created_by,
        assignee=UserOut.model_validate(task.assignee) if task.assignee else None,
    )
