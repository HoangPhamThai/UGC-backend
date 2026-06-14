# app/modules/workspaces/presentation/routes.py
from fastapi import APIRouter, BackgroundTasks, Body, Depends, Path, Query, status

from app.core.auth import get_current_user
from app.core.model import StandardResponse, create_success_response
from app.core.permissions import Permission, require_permissions
from app.modules.profiles.presentation.gate import require_profile_complete
from app.modules.users.data.model import User
from app.modules.workspaces.data.model import ExtractionStatus, FeedbackAnchor
from app.modules.workspaces.extraction.deps import run_extraction_task
from app.modules.workspaces.presentation.deps import (
    get_uc_add_reply,
    get_uc_approve_article,
    get_uc_claim_article,
    get_uc_create_article,
    get_uc_create_feedback,
    get_uc_create_workspace,
    get_uc_delete_article,
    get_uc_delete_feedback,
    get_uc_delete_workspace,
    get_uc_get_article,
    get_uc_get_workspace,
    get_uc_list_feedbacks,
    get_uc_list_workspaces,
    get_uc_publish_review,
    get_uc_reject_article,
    get_uc_retry_extraction,
    get_uc_set_feedback_status,
    get_uc_submit_article,
    get_uc_submit_article_link,
    get_uc_update_article,
    get_uc_update_feedback,
    get_uc_withdraw_article,
)
from app.modules.workspaces.presentation.schema import (
    AddReplyRequest,
    ArticleResponse,
    CreateArticleRequest,
    CreateFeedbackRequest,
    CreateWorkspaceRequest,
    FeedbackResponse,
    RejectArticleRequest,
    SetFeedbackStatusRequest,
    SubmitArticleLinkRequest,
    UpdateArticleRequest,
    UpdateFeedbackBodyRequest,
    WorkspaceListResponse,
    WorkspaceResponse,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


# --- Workspaces ---


@router.get(
    "",
    response_model=StandardResponse[WorkspaceListResponse],
    response_model_exclude_none=True,
)
async def list_workspaces(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=12, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    uc=Depends(get_uc_list_workspaces),
):
    result = await uc.execute(caller=current_user, page=page, limit=limit)
    items = [
        WorkspaceResponse.from_model(
            ws,
            article_count=result.article_counts.get(ws.id, 0),
            products=result.products_by_ws.get(ws.id, []),
        )
        for ws in result.items
    ]
    data = WorkspaceListResponse(items=items, total=result.total)
    return create_success_response(data)


@router.post(
    "",
    response_model=StandardResponse[WorkspaceResponse],
    status_code=status.HTTP_201_CREATED,
    response_model_exclude_none=True,
    dependencies=[Depends(require_profile_complete)],
)
async def create_workspace(
    body: CreateWorkspaceRequest = Body(...),
    current_user: User = Depends(require_permissions(Permission.WORKSPACES_CREATE)),
    uc=Depends(get_uc_create_workspace),
):
    ws = await uc.execute(name=body.name, owner_user_id=current_user.id)
    return create_success_response(
        WorkspaceResponse.from_model(ws), "Workspace created"
    )


@router.get(
    "/{workspace_id}",
    response_model=StandardResponse[WorkspaceResponse],
    response_model_exclude_none=True,
)
async def get_workspace(
    workspace_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    uc=Depends(get_uc_get_workspace),
):
    result = await uc.execute(workspace_id=workspace_id, caller=current_user)
    return create_success_response(
        WorkspaceResponse.from_model(
            result.workspace,
            articles=result.articles,
            products=result.products,
        )
    )


@router.get(
    "/{workspace_id}/articles/{article_id}",
    response_model=StandardResponse[ArticleResponse],
)
async def get_article(
    workspace_id: str = Path(...),
    article_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    uc=Depends(get_uc_get_article),
):
    article = await uc.execute(
        workspace_id=workspace_id, article_id=article_id, caller=current_user
    )
    return create_success_response(ArticleResponse.from_model(article))


@router.delete(
    "/{workspace_id}",
    response_model=StandardResponse,
    dependencies=[Depends(require_profile_complete)],
)
async def delete_workspace(
    workspace_id: str = Path(...),
    current_user: User = Depends(require_permissions(Permission.WORKSPACES_DELETE)),
    uc=Depends(get_uc_delete_workspace),
):
    await uc.execute(workspace_id=workspace_id, caller=current_user)
    return create_success_response(None, "Workspace deleted")


# --- Articles ---


@router.post(
    "/{workspace_id}/articles",
    response_model=StandardResponse[ArticleResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_profile_complete)],
)
async def create_article(
    workspace_id: str = Path(...),
    body: CreateArticleRequest = Body(...),
    current_user: User = Depends(require_permissions(Permission.ARTICLES_CREATE)),
    uc=Depends(get_uc_create_article),
):
    article = await uc.execute(
        workspace_id=workspace_id,
        name=body.name,
        product=body.product,
        on_air_date=body.on_air_date,
        caller=current_user,
    )
    return create_success_response(
        ArticleResponse.from_model(article), "Article created"
    )


@router.delete(
    "/{workspace_id}/articles/{article_id}",
    response_model=StandardResponse,
    dependencies=[Depends(require_profile_complete)],
)
async def delete_article(
    workspace_id: str = Path(...),
    article_id: str = Path(...),
    current_user: User = Depends(require_permissions(Permission.ARTICLES_DELETE)),
    uc=Depends(get_uc_delete_article),
):
    await uc.execute(
        workspace_id=workspace_id, article_id=article_id, caller=current_user
    )
    return create_success_response(None, "Article deleted")


@router.patch(
    "/{workspace_id}/articles/{article_id}",
    response_model=StandardResponse[ArticleResponse],
    dependencies=[Depends(require_profile_complete)],
)
async def update_article(
    workspace_id: str = Path(...),
    article_id: str = Path(...),
    body: UpdateArticleRequest = Body(...),
    current_user: User = Depends(require_permissions(Permission.ARTICLES_UPDATE)),
    uc=Depends(get_uc_update_article),
):
    article = await uc.execute(
        workspace_id=workspace_id,
        article_id=article_id,
        caller=current_user,
        name=body.name,
        product=body.product,
        on_air_date=body.on_air_date,
        content=body.content,
    )
    return create_success_response(ArticleResponse.from_model(article))


@router.post(
    "/{workspace_id}/articles/{article_id}/link",
    response_model=StandardResponse[ArticleResponse],
    dependencies=[Depends(require_profile_complete)],
)
async def submit_article_link(
    background_tasks: BackgroundTasks,
    workspace_id: str = Path(...),
    article_id: str = Path(...),
    body: SubmitArticleLinkRequest = Body(...),
    current_user: User = Depends(require_permissions(Permission.ARTICLES_UPDATE)),
    uc=Depends(get_uc_submit_article_link),
):
    article = await uc.execute(
        workspace_id=workspace_id,
        article_id=article_id,
        caller=current_user,
        link=body.link,
    )
    if article.extraction_status == ExtractionStatus.PENDING and article.link:
        background_tasks.add_task(run_extraction_task, article.id, article.link)
    return create_success_response(ArticleResponse.from_model(article), "Link saved")


@router.post(
    "/{workspace_id}/articles/{article_id}/link/extract",
    response_model=StandardResponse[ArticleResponse],
    dependencies=[Depends(require_profile_complete)],
)
async def retry_article_extraction(
    background_tasks: BackgroundTasks,
    workspace_id: str = Path(...),
    article_id: str = Path(...),
    current_user: User = Depends(require_permissions(Permission.ARTICLES_UPDATE)),
    uc=Depends(get_uc_retry_extraction),
):
    article = await uc.execute(
        workspace_id=workspace_id, article_id=article_id, caller=current_user
    )
    if article.link:
        background_tasks.add_task(run_extraction_task, article.id, article.link)
    return create_success_response(
        ArticleResponse.from_model(article), "Re-extracting metrics"
    )


@router.post(
    "/{workspace_id}/articles/{article_id}/submit",
    response_model=StandardResponse[ArticleResponse],
    dependencies=[Depends(require_profile_complete)],
)
async def submit_article(
    workspace_id: str = Path(...),
    article_id: str = Path(...),
    current_user: User = Depends(require_permissions(Permission.ARTICLES_SUBMIT)),
    uc=Depends(get_uc_submit_article),
):
    article = await uc.execute(
        workspace_id=workspace_id, article_id=article_id, caller=current_user
    )
    return create_success_response(ArticleResponse.from_model(article))


@router.post(
    "/{workspace_id}/articles/{article_id}/approve",
    response_model=StandardResponse[ArticleResponse],
)
async def approve_article(
    workspace_id: str = Path(...),
    article_id: str = Path(...),
    current_user: User = Depends(require_permissions(Permission.ARTICLES_REVIEW)),
    uc=Depends(get_uc_approve_article),
):
    article = await uc.execute(
        workspace_id=workspace_id, article_id=article_id, caller=current_user
    )
    return create_success_response(ArticleResponse.from_model(article))


@router.post(
    "/{workspace_id}/articles/{article_id}/reject",
    response_model=StandardResponse[ArticleResponse],
)
async def reject_article(
    workspace_id: str = Path(...),
    article_id: str = Path(...),
    body: RejectArticleRequest = Body(...),
    current_user: User = Depends(require_permissions(Permission.ARTICLES_REVIEW)),
    uc=Depends(get_uc_reject_article),
):
    article = await uc.execute(
        workspace_id=workspace_id,
        article_id=article_id,
        caller=current_user,
        reason=body.reason,
    )
    return create_success_response(ArticleResponse.from_model(article))


@router.post(
    "/{workspace_id}/articles/{article_id}/claim",
    response_model=StandardResponse[ArticleResponse],
)
async def claim_article(
    workspace_id: str = Path(...),
    article_id: str = Path(...),
    current_user: User = Depends(require_permissions(Permission.ARTICLES_REVIEW)),
    uc=Depends(get_uc_claim_article),
):
    article = await uc.execute(
        workspace_id=workspace_id, article_id=article_id, caller=current_user
    )
    return create_success_response(ArticleResponse.from_model(article))


@router.post(
    "/{workspace_id}/articles/{article_id}/withdraw",
    response_model=StandardResponse[ArticleResponse],
    dependencies=[Depends(require_profile_complete)],
)
async def withdraw_article(
    workspace_id: str = Path(...),
    article_id: str = Path(...),
    current_user: User = Depends(require_permissions(Permission.ARTICLES_SUBMIT)),
    uc=Depends(get_uc_withdraw_article),
):
    article = await uc.execute(
        workspace_id=workspace_id, article_id=article_id, caller=current_user
    )
    return create_success_response(ArticleResponse.from_model(article))


@router.get(
    "/{workspace_id}/articles/{article_id}/feedbacks",
    response_model=StandardResponse[list[FeedbackResponse]],
)
async def list_feedbacks(
    workspace_id: str = Path(...),
    article_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    uc=Depends(get_uc_list_feedbacks),
):
    feedbacks = await uc.execute(
        workspace_id=workspace_id, article_id=article_id, caller=current_user
    )
    return create_success_response([FeedbackResponse.from_model(f) for f in feedbacks])


@router.post(
    "/{workspace_id}/articles/{article_id}/feedbacks",
    response_model=StandardResponse[FeedbackResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_feedback(
    workspace_id: str = Path(...),
    article_id: str = Path(...),
    body: CreateFeedbackRequest = Body(...),
    current_user: User = Depends(require_permissions(Permission.ARTICLES_REVIEW)),
    uc=Depends(get_uc_create_feedback),
):
    anchor = FeedbackAnchor(**body.anchor.model_dump())
    fb = await uc.execute(
        workspace_id=workspace_id,
        article_id=article_id,
        caller=current_user,
        body=body.body,
        anchor=anchor,
    )
    return create_success_response(FeedbackResponse.from_model(fb), "Feedback created")


@router.patch(
    "/{workspace_id}/articles/{article_id}/feedbacks/{feedback_id}",
    response_model=StandardResponse[FeedbackResponse],
)
async def set_feedback_status(
    workspace_id: str = Path(...),
    article_id: str = Path(...),
    feedback_id: str = Path(...),
    body: SetFeedbackStatusRequest = Body(...),
    current_user: User = Depends(require_permissions(Permission.ARTICLES_REVIEW)),
    uc=Depends(get_uc_set_feedback_status),
):
    fb = await uc.execute(
        workspace_id=workspace_id,
        article_id=article_id,
        feedback_id=feedback_id,
        target=body.status,
        caller=current_user,
    )
    return create_success_response(FeedbackResponse.from_model(fb))


@router.patch(
    "/{workspace_id}/articles/{article_id}/feedbacks/{feedback_id}/body",
    response_model=StandardResponse[FeedbackResponse],
)
async def update_feedback_body(
    workspace_id: str = Path(...),
    article_id: str = Path(...),
    feedback_id: str = Path(...),
    body: UpdateFeedbackBodyRequest = Body(...),
    current_user: User = Depends(require_permissions(Permission.ARTICLES_REVIEW)),
    uc=Depends(get_uc_update_feedback),
):
    fb = await uc.execute(
        workspace_id=workspace_id,
        article_id=article_id,
        feedback_id=feedback_id,
        body=body.body,
        caller=current_user,
    )
    return create_success_response(FeedbackResponse.from_model(fb))


@router.delete(
    "/{workspace_id}/articles/{article_id}/feedbacks/{feedback_id}",
    response_model=StandardResponse[None],
)
async def delete_feedback(
    workspace_id: str = Path(...),
    article_id: str = Path(...),
    feedback_id: str = Path(...),
    current_user: User = Depends(require_permissions(Permission.ARTICLES_REVIEW)),
    uc=Depends(get_uc_delete_feedback),
):
    await uc.execute(
        workspace_id=workspace_id,
        article_id=article_id,
        feedback_id=feedback_id,
        caller=current_user,
    )
    return create_success_response(None, "Feedback deleted")


@router.post(
    "/{workspace_id}/articles/{article_id}/feedbacks/{feedback_id}/replies",
    response_model=StandardResponse[FeedbackResponse],
    status_code=status.HTTP_201_CREATED,
)
async def add_reply(
    workspace_id: str = Path(...),
    article_id: str = Path(...),
    feedback_id: str = Path(...),
    body: AddReplyRequest = Body(...),
    current_user: User = Depends(get_current_user),
    uc=Depends(get_uc_add_reply),
):
    fb = await uc.execute(
        workspace_id=workspace_id,
        article_id=article_id,
        feedback_id=feedback_id,
        body=body.body,
        caller=current_user,
    )
    return create_success_response(FeedbackResponse.from_model(fb), "Reply added")


@router.post(
    "/{workspace_id}/articles/{article_id}/publish-review",
    response_model=StandardResponse[ArticleResponse],
)
async def publish_review(
    workspace_id: str = Path(...),
    article_id: str = Path(...),
    current_user: User = Depends(require_permissions(Permission.ARTICLES_REVIEW)),
    uc=Depends(get_uc_publish_review),
):
    article = await uc.execute(
        workspace_id=workspace_id, article_id=article_id, caller=current_user
    )
    return create_success_response(ArticleResponse.from_model(article))
