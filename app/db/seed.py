from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.models import User


def seed_defaults(db: Session) -> None:
    owner = db.query(User).filter(User.email == settings.seed_admin_email).first()
    if not owner:
        db.add(
            User(
                kind="owner",
                email=settings.seed_admin_email,
                password_hash=hash_password(settings.seed_admin_password),
                name=settings.seed_admin_name,
                designation="Owner",
                is_active=True,
            )
        )

    manager = db.query(User).filter(User.email == settings.seed_manager_email).first()
    if not manager:
        db.add(
            User(
                kind="manager",
                email=settings.seed_manager_email,
                password_hash=hash_password(settings.seed_manager_password),
                name=settings.seed_manager_name,
                designation="Manager",
                is_active=True,
            )
        )

    db.commit()
