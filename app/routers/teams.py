from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user, has_permission, require_permission
from app.db.models import Team, TeamMember, User
from app.db.session import get_db
from app.schemas import TeamCreate, TeamMemberIn, TeamOut, TeamUpdate

router = APIRouter(prefix="/teams", tags=["teams"])


def _team_query(db: Session):
    return db.query(Team).options(joinedload(Team.members).joinedload(TeamMember.user).joinedload(User.role))


def _visible_teams(db: Session, user: User) -> list[Team]:
    teams = _team_query(db).order_by(Team.id.asc()).all()
    if has_permission(user, "teams.manage") or has_permission(user, "projects.view_all") or has_permission(user, "projects.create"):
        return teams
    member_team_ids = {m.team_id for m in user.team_memberships}
    return [t for t in teams if t.id in member_team_ids]


@router.get("", response_model=list[TeamOut])
def list_teams(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return _visible_teams(db, current)


@router.post("", response_model=TeamOut, status_code=201)
def create_team(
    payload: TeamCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("teams.manage")),
):
    if db.query(Team).filter(Team.name == payload.name).first():
        raise HTTPException(status_code=400, detail="Team name already exists")
    team = Team(name=payload.name, description=payload.description)
    db.add(team)
    db.commit()
    return _team_query(db).filter(Team.id == team.id).first()


@router.patch("/{team_id}", response_model=TeamOut)
def update_team(
    team_id: int,
    payload: TeamUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("teams.manage")),
):
    team = _team_query(db).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    if payload.name and payload.name != team.name:
        if db.query(Team).filter(Team.name == payload.name, Team.id != team_id).first():
            raise HTTPException(status_code=400, detail="Team name already exists")
        team.name = payload.name
    if payload.description is not None:
        team.description = payload.description
    db.commit()
    return _team_query(db).filter(Team.id == team_id).first()


@router.delete("/{team_id}", status_code=204)
def delete_team(
    team_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("teams.manage")),
):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    db.delete(team)
    db.commit()


@router.post("/{team_id}/members", response_model=TeamOut)
def add_member(
    team_id: int,
    payload: TeamMemberIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("teams.manage")),
):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")
    existing = db.query(TeamMember).filter(TeamMember.team_id == team_id, TeamMember.user_id == payload.user_id).first()
    if existing:
        existing.designation = payload.designation
    else:
        db.add(TeamMember(team_id=team_id, user_id=payload.user_id, designation=payload.designation))
    db.commit()
    return _team_query(db).filter(Team.id == team_id).first()


@router.delete("/{team_id}/members/{user_id}", response_model=TeamOut)
def remove_member(
    team_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("teams.manage")),
):
    member = db.query(TeamMember).filter(TeamMember.team_id == team_id, TeamMember.user_id == user_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    db.delete(member)
    db.commit()
    team = _team_query(db).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team
