# app/modules/workspaces/presentation/routes.py
from fastapi import APIRouter, Body, Depends, Path, Query, status

from app.core.auth import get_current_user
from app.core.model import StandardResponse, create_success_response
from app.core.permissions import Permission, require_permissions
from app.modules.users.data.model import User
from app.modules.workspaces.presentation.deps import (
    get_uc_approve_article,
    get_uc_create_article,
    get_uc_create_workspace,
    get_uc_delete_article,
    get_uc_delete_workspace,
    get_uc_get_workspace,
    get_uc_list_workspaces,
    get_uc_reject_article,
    get_uc_start_review_article,
    get_uc_submit_article,
    get_uc_update_article_content,
)
from app.modules.workspaces.presentation.schema import (
    ArticleResponse,
    CreateArticleRequest,
    CreateWorkspaceRequest,
    UpdateArticleContentRequest,
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


@router.delete(
    "/{workspace_id}",
    response_model=StandardResponse,
)
async def delete_workspace(
    workspace_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    uc=Depends(get_uc_delete_workspace),
):
    await uc.execute(workspace_id=workspace_id, caller=current_user)
    return create_success_response(None, "Workspace deleted")


# --- Articles ---


@router.post(
    "/{workspace_id}/articles",
    response_model=StandardResponse[ArticleResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_article(
    workspace_id: str = Path(...),
    body: CreateArticleRequest = Body(...),
    current_user: User = Depends(get_current_user),
    uc=Depends(get_uc_create_article),
):
    article = await uc.execute(
        workspace_id=workspace_id,
        name=body.name,
        product=body.product,
        caller=current_user,
    )
    return create_success_response(
        ArticleResponse.from_model(article), "Article created"
    )


@router.delete(
    "/{workspace_id}/articles/{article_id}",
    response_model=StandardResponse,
)
async def delete_article(
    workspace_id: str = Path(...),
    article_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    uc=Depends(get_uc_delete_article),
):
    await uc.execute(
        workspace_id=workspace_id, article_id=article_id, caller=current_user
    )
    return create_success_response(None, "Article deleted")


@router.patch(
    "/{workspace_id}/articles/{article_id}",
    response_model=StandardResponse[ArticleResponse],
)
async def update_article_content(
    workspace_id: str = Path(...),
    article_id: str = Path(...),
    body: UpdateArticleContentRequest = Body(...),
    current_user: User = Depends(get_current_user),
    uc=Depends(get_uc_update_article_content),
):
    article = await uc.execute(
        workspace_id=workspace_id,
        article_id=article_id,
        content=body.content,
        caller=current_user,
    )
    return create_success_response(ArticleResponse.from_model(article))


@router.post(
    "/{workspace_id}/articles/{article_id}/submit",
    response_model=StandardResponse[ArticleResponse],
)
async def submit_article(
    workspace_id: str = Path(...),
    article_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    uc=Depends(get_uc_submit_article),
):
    article = await uc.execute(
        workspace_id=workspace_id, article_id=article_id, caller=current_user
    )
    return create_success_response(ArticleResponse.from_model(article))


@router.post(
    "/{workspace_id}/articles/{article_id}/start-review",
    response_model=StandardResponse[ArticleResponse],
)
async def start_review_article(
    workspace_id: str = Path(...),
    article_id: str = Path(...),
    current_user: User = Depends(require_permissions(Permission.WORKSPACES_REVIEW)),
    uc=Depends(get_uc_start_review_article),
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
    current_user: User = Depends(require_permissions(Permission.WORKSPACES_REVIEW)),
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
    current_user: User = Depends(require_permissions(Permission.WORKSPACES_REVIEW)),
    uc=Depends(get_uc_reject_article),
):
    article = await uc.execute(
        workspace_id=workspace_id, article_id=article_id, caller=current_user
    )
    return create_success_response(ArticleResponse.from_model(article))
