from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import ALL_PERMISSIONS, hash_password
from app.db.models import Role, User


def seed_defaults(db: Session) -> None:
    owner = db.query(Role).filter(Role.name == "Owner").first()
    if not owner:
        owner = Role(name="Owner", permissions=list(ALL_PERMISSIONS), is_system=True)
        db.add(owner)
        db.flush()

    member = db.query(Role).filter(Role.name == "Member").first()
    if not member:
        db.add(Role(name="Member", permissions=[], is_system=True))

    admin = db.query(User).filter(User.email == settings.seed_admin_email).first()
    if not admin:
        db.add(
            User(
                email=settings.seed_admin_email,
                password_hash=hash_password(settings.seed_admin_password),
                name=settings.seed_admin_name,
                role_id=owner.id,
                is_active=True,
            )
        )

    db.commit()
