# app/modules/interim_keys/presentation/deps.py
from fastapi import Depends

from app.modules.interim_keys.data.repo import InterimKeyDataRepository
from app.modules.interim_keys.domain.repo import InterimKeyRepo
from app.modules.interim_keys.domain.usecases.issue_interim_key import (
    IssueInterimKeyUseCase,
)
from app.modules.interim_keys.domain.usecases.revoke_interim_key import (
    RevokeInterimKeyUseCase,
)


def get_interim_key_repo() -> InterimKeyRepo:
    return InterimKeyDataRepository()


def get_uc_issue_interim_key(
    repo: InterimKeyRepo = Depends(get_interim_key_repo),
) -> IssueInterimKeyUseCase:
    return IssueInterimKeyUseCase(repo=repo)


def get_uc_revoke_interim_key(
    repo: InterimKeyRepo = Depends(get_interim_key_repo),
) -> RevokeInterimKeyUseCase:
    return RevokeInterimKeyUseCase(repo=repo)
