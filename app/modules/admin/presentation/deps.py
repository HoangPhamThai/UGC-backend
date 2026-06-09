from fastapi import Depends

from app.modules.admin.domain.usecases.create_managed_user import (
    CreateManagedUserUseCase,
)
from app.modules.admin.domain.usecases.get_managed_user import GetManagedUserUseCase
from app.modules.admin.domain.usecases.list_users_by_role import (
    ListUsersByRoleUseCase,
)
from app.modules.admin.domain.usecases.update_managed_user import (
    UpdateManagedUserUseCase,
)
from app.modules.users.data.repo import UserDataRepository
from app.modules.users.domain.repo import UserRepo
from app.modules.users.domain.usecases.create_user import CreateUserUseCase


def get_user_repo() -> UserRepo:
    return UserDataRepository()


def get_uc_create_user(
    user_repo: UserRepo = Depends(get_user_repo),
) -> CreateUserUseCase:
    return CreateUserUseCase(user_repo=user_repo)


def get_uc_create_managed_user(
    uc_create_user: CreateUserUseCase = Depends(get_uc_create_user),
) -> CreateManagedUserUseCase:
    return CreateManagedUserUseCase(uc_create_user=uc_create_user)


def get_uc_list_users_by_role(
    user_repo: UserRepo = Depends(get_user_repo),
) -> ListUsersByRoleUseCase:
    return ListUsersByRoleUseCase(user_repo=user_repo)


def get_uc_get_managed_user(
    user_repo: UserRepo = Depends(get_user_repo),
) -> GetManagedUserUseCase:
    return GetManagedUserUseCase(user_repo=user_repo)


def get_uc_update_managed_user(
    user_repo: UserRepo = Depends(get_user_repo),
) -> UpdateManagedUserUseCase:
    return UpdateManagedUserUseCase(user_repo=user_repo)
