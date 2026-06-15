# app/modules/review_jobs/presentation/routes.py
from fastapi import APIRouter, Body, Depends

from app.core.auth import get_current_principal
from app.core.model import StandardResponse, create_success_response
from app.core.permissions import Permission, require_permissions
from app.modules.review_jobs.data.model import ReviewJobStatus
from app.modules.review_jobs.presentation.deps import (
    get_uc_append_result,
    get_uc_create_job,
    get_uc_finalize_job,
    get_uc_get_job,
    get_uc_set_total,
)
from app.modules.review_jobs.presentation.schema import (
    CreateReviewJobRequest,
    CreateReviewJobResponse,
    ReviewJobResponse,
    UpdateReviewJobRequest,
)
from app.modules.users.data.model import User

router = APIRouter(prefix="/review-jobs", tags=["review-jobs"])


@router.post("", response_model=StandardResponse[CreateReviewJobResponse], status_code=201)
async def create_review_job(
    body: CreateReviewJobRequest = Body(...),
    principal: User = Depends(require_permissions(Permission.REVIEW_JOBS_WRITE)),
    uc=Depends(get_uc_create_job),
):
    job = await uc.execute(
        owner_user_id=principal.id,
        article_id=body.article_id,
        workspace_id=body.workspace_id,
    )
    return create_success_response(CreateReviewJobResponse(job_id=job.id))


@router.patch("/{job_id}", response_model=StandardResponse[ReviewJobResponse])
async def update_review_job(
    job_id: str,
    body: UpdateReviewJobRequest = Body(...),
    principal: User = Depends(require_permissions(Permission.REVIEW_JOBS_WRITE)),
    set_total=Depends(get_uc_set_total),
    append_result=Depends(get_uc_append_result),
    finalize=Depends(get_uc_finalize_job),
):
    if body.total is not None:
        job = await set_total.execute(job_id=job_id, total=body.total)
    elif body.result is not None:
        job = await append_result.execute(job_id=job_id, card=body.result)
    else:
        status = ReviewJobStatus(body.status or ReviewJobStatus.DONE.value)
        job = await finalize.execute(job_id=job_id, status=status, error=body.error)
    return create_success_response(ReviewJobResponse.from_job(job))


@router.get("/{job_id}", response_model=StandardResponse[ReviewJobResponse])
async def get_review_job(
    job_id: str,
    principal: User = Depends(require_permissions(Permission.ARTICLES_REVIEW)),
    uc=Depends(get_uc_get_job),
):
    job = await uc.execute(job_id=job_id, caller_id=principal.id)
    return create_success_response(ReviewJobResponse.from_job(job))
