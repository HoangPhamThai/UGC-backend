from fastapi import Depends

from app.modules.users.data.repo import UserDataRepository
from app.modules.users.domain.repo import UserRepo
from app.modules.users.domain.usecases.create_user import CreateUserUseCase
from app.modules.refresh_tokens.data.repo import RefreshTokenDataRepository
from app.modules.refresh_tokens.domain.repo import RefreshTokenRepo
from app.modules.auth.domain.usecases.register import RegisterUseCase
from app.modules.auth.domain.usecases.login import LoginUseCase
from app.modules.auth.domain.usecases.refresh import RefreshTokenUseCase
from app.modules.auth.domain.usecases.logout import LogoutUseCase


def get_user_repo() -> UserRepo:
    return UserDataRepository()


def get_refresh_token_repo() -> RefreshTokenRepo:
    return RefreshTokenDataRepository()


def get_uc_create_user(
    user_repo: UserRepo = Depends(get_user_repo),
) -> CreateUserUseCase:
    return CreateUserUseCase(user_repo=user_repo)


def get_uc_register(
    uc_create_user: CreateUserUseCase = Depends(get_uc_create_user),
) -> RegisterUseCase:
    return RegisterUseCase(uc_create_user=uc_create_user)


def get_uc_login(
    user_repo: UserRepo = Depends(get_user_repo),
    refresh_token_repo: RefreshTokenRepo = Depends(get_refresh_token_repo),
) -> LoginUseCase:
    return LoginUseCase(user_repo=user_repo, refresh_token_repo=refresh_token_repo)


def get_uc_refresh(
    refresh_token_repo: RefreshTokenRepo = Depends(get_refresh_token_repo),
) -> RefreshTokenUseCase:
    return RefreshTokenUseCase(refresh_token_repo=refresh_token_repo)


def get_uc_logout(
    refresh_token_repo: RefreshTokenRepo = Depends(get_refresh_token_repo),
) -> LogoutUseCase:
    return LogoutUseCase(refresh_token_repo=refresh_token_repo)
