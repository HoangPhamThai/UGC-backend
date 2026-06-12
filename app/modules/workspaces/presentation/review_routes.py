# app/modules/workspaces/presentation/review_routes.py
from fastapi import APIRouter, Depends, Query

from app.core.model import StandardResponse, create_success_response
from app.core.permissions import Permission, require_permissions
from app.modules.users.data.model import User
from app.modules.workspaces.domain.usecases.list_review_queue import ReviewQueueGroup
from app.modules.workspaces.presentation.deps import get_uc_list_review_queue
from app.modules.workspaces.presentation.schema import ArticleResponse, ReviewQueueResponse

router = APIRouter(prefix="/review", tags=["review"])


@router.get("/queue", response_model=StandardResponse[ReviewQueueResponse])
async def review_queue(
    group: ReviewQueueGroup = Query(default=ReviewQueueGroup.NEEDS_REVIEW),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_permissions(Permission.ARTICLES_REVIEW)),
    uc=Depends(get_uc_list_review_queue),
):
    result = await uc.execute(caller=current_user, group=group, page=page, limit=limit)
    data = ReviewQueueResponse(
        items=[ArticleResponse.from_model(a) for a in result.items],
        total=result.total,
    )
    return create_success_response(data)
