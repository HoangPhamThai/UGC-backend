# app/modules/workspaces/presentation/deps.py
from functools import lru_cache

from app.modules.workspaces.data.repo import (
    ArticleDataRepository,
    WorkspaceDataRepository,
)
from app.modules.workspaces.domain.repo import ArticleRepo, WorkspaceRepo
from app.modules.workspaces.domain.usecases.approve_article import ApproveArticleUseCase
from app.modules.workspaces.domain.usecases.create_article import CreateArticleUseCase
from app.modules.workspaces.domain.usecases.create_workspace import (
    CreateWorkspaceUseCase,
)
from app.modules.workspaces.domain.usecases.delete_article import DeleteArticleUseCase
from app.modules.workspaces.domain.usecases.delete_workspace import (
    DeleteWorkspaceUseCase,
)
from app.modules.workspaces.domain.usecases.get_workspace import GetWorkspaceUseCase
from app.modules.workspaces.domain.usecases.list_workspaces import (
    ListWorkspacesUseCase,
)
from app.modules.workspaces.domain.usecases.reject_article import RejectArticleUseCase
from app.modules.workspaces.domain.usecases.start_review_article import (
    StartReviewArticleUseCase,
)
from app.modules.workspaces.domain.usecases.submit_article import SubmitArticleUseCase
from app.modules.workspaces.domain.usecases.update_article_content import (
    UpdateArticleContentUseCase,
)


@lru_cache(maxsize=1)
def get_workspace_repo() -> WorkspaceRepo:
    return WorkspaceDataRepository()


@lru_cache(maxsize=1)
def get_article_repo() -> ArticleRepo:
    return ArticleDataRepository()


def get_uc_create_workspace() -> CreateWorkspaceUseCase:
    return CreateWorkspaceUseCase(workspace_repo=get_workspace_repo())


def get_uc_list_workspaces() -> ListWorkspacesUseCase:
    return ListWorkspacesUseCase(workspace_repo=get_workspace_repo())


def get_uc_get_workspace() -> GetWorkspaceUseCase:
    return GetWorkspaceUseCase(
        workspace_repo=get_workspace_repo(),
        article_repo=get_article_repo(),
    )


def get_uc_delete_workspace() -> DeleteWorkspaceUseCase:
    return DeleteWorkspaceUseCase(
        workspace_repo=get_workspace_repo(),
        article_repo=get_article_repo(),
    )


def get_uc_create_article() -> CreateArticleUseCase:
    return CreateArticleUseCase(
        workspace_repo=get_workspace_repo(),
        article_repo=get_article_repo(),
    )


def get_uc_delete_article() -> DeleteArticleUseCase:
    return DeleteArticleUseCase(
        workspace_repo=get_workspace_repo(),
        article_repo=get_article_repo(),
    )


def get_uc_update_article_content() -> UpdateArticleContentUseCase:
    return UpdateArticleContentUseCase(
        workspace_repo=get_workspace_repo(),
        article_repo=get_article_repo(),
    )


def get_uc_submit_article() -> SubmitArticleUseCase:
    return SubmitArticleUseCase(
        workspace_repo=get_workspace_repo(),
        article_repo=get_article_repo(),
    )


def get_uc_start_review_article() -> StartReviewArticleUseCase:
    return StartReviewArticleUseCase(article_repo=get_article_repo())


def get_uc_approve_article() -> ApproveArticleUseCase:
    return ApproveArticleUseCase(article_repo=get_article_repo())


def get_uc_reject_article() -> RejectArticleUseCase:
    return RejectArticleUseCase(article_repo=get_article_repo())
