from app.modules.users.data.repo import UserDataRepository
from app.modules.users.domain.repo import UserRepo


def get_user_repo() -> UserRepo:
    return UserDataRepository()
