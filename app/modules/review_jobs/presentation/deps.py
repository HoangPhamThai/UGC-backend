# app/modules/review_jobs/presentation/deps.py
from fastapi import Depends

from app.modules.review_jobs.data.repo import ReviewJobDataRepository
from app.modules.review_jobs.domain.repo import ReviewJobRepo
from app.modules.review_jobs.domain.usecases.create_job import CreateReviewJobUseCase
from app.modules.review_jobs.domain.usecases.get_job import GetReviewJobUseCase
from app.modules.review_jobs.domain.usecases.update_job import (
    AppendResultUseCase,
    FinalizeJobUseCase,
    SetTotalUseCase,
)


def get_review_job_repo() -> ReviewJobRepo:
    return ReviewJobDataRepository()


def get_uc_create_job(repo: ReviewJobRepo = Depends(get_review_job_repo)) -> CreateReviewJobUseCase:
    return CreateReviewJobUseCase(repo=repo)


def get_uc_get_job(repo: ReviewJobRepo = Depends(get_review_job_repo)) -> GetReviewJobUseCase:
    return GetReviewJobUseCase(repo=repo)


def get_uc_set_total(repo: ReviewJobRepo = Depends(get_review_job_repo)) -> SetTotalUseCase:
    return SetTotalUseCase(repo=repo)


def get_uc_append_result(repo: ReviewJobRepo = Depends(get_review_job_repo)) -> AppendResultUseCase:
    return AppendResultUseCase(repo=repo)


def get_uc_finalize_job(repo: ReviewJobRepo = Depends(get_review_job_repo)) -> FinalizeJobUseCase:
    return FinalizeJobUseCase(repo=repo)
