from app.db.models import User
from app.schemas import UserOut


def serialize_user(user: User) -> UserOut:
    return UserOut.model_validate(user)
