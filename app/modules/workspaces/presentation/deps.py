# app/modules/workspaces/presentation/deps.py
from functools import lru_cache

from app.modules.notifications.data.repo import NotificationDataRepository
from app.modules.notifications.domain.repo import NotificationRepo
from app.modules.workspaces.data.notifying_event_repo import NotifyingEventRepo
from app.modules.workspaces.data.repo import (
    ArticleDataRepository,
    ArticleEventDataRepository,
    FeedbackDataRepository,
    WorkspaceDataRepository,
)
from app.modules.workspaces.domain.repo import (
    ArticleEventRepo,
    ArticleRepo,
    FeedbackRepo,
    WorkspaceRepo,
)
from app.modules.workspaces.domain.usecases.add_reply import AddReplyUseCase
from app.modules.workspaces.domain.usecases.list_review_queue import ListReviewQueueUseCase
from app.modules.workspaces.domain.usecases.approve_article import ApproveArticleUseCase
from app.modules.workspaces.domain.usecases.claim_article import ClaimArticleUseCase
from app.modules.workspaces.domain.usecases.create_article import CreateArticleUseCase
from app.modules.workspaces.domain.usecases.create_feedback import CreateFeedbackUseCase
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
from app.modules.workspaces.domain.usecases.publish_review import PublishReviewUseCase
from app.modules.workspaces.domain.usecases.reject_article import RejectArticleUseCase
from app.modules.workspaces.domain.usecases.set_feedback_status import SetFeedbackStatusUseCase
from app.modules.workspaces.domain.usecases.submit_article import SubmitArticleUseCase
from app.modules.workspaces.domain.usecases.update_article import UpdateArticleUseCase
from app.modules.workspaces.domain.usecases.withdraw_article import WithdrawArticleUseCase


@lru_cache(maxsize=1)
def get_workspace_repo() -> WorkspaceRepo:
    return WorkspaceDataRepository()


@lru_cache(maxsize=1)
def get_article_repo() -> ArticleRepo:
    return ArticleDataRepository()


@lru_cache(maxsize=1)
def get_feedback_repo() -> FeedbackRepo:
    return FeedbackDataRepository()


@lru_cache(maxsize=1)
def get_notification_repo() -> NotificationRepo:
    return NotificationDataRepository()


@lru_cache(maxsize=1)
def _get_raw_event_repo() -> ArticleEventRepo:
    return ArticleEventDataRepository()


@lru_cache(maxsize=1)
def get_event_repo() -> ArticleEventRepo:
    # Decorate the raw event repo so every persisted event also fans out notifications.
    return NotifyingEventRepo(
        inner=_get_raw_event_repo(),
        notification_repo=get_notification_repo(),
        article_repo=get_article_repo(),
        workspace_repo=get_workspace_repo(),
    )


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


def get_uc_update_article() -> UpdateArticleUseCase:
    return UpdateArticleUseCase(
        workspace_repo=get_workspace_repo(),
        article_repo=get_article_repo(),
    )


def get_uc_submit_article() -> SubmitArticleUseCase:
    return SubmitArticleUseCase(
        workspace_repo=get_workspace_repo(),
        article_repo=get_article_repo(),
        event_repo=get_event_repo(),
    )


def get_uc_approve_article() -> ApproveArticleUseCase:
    return ApproveArticleUseCase(
        article_repo=get_article_repo(),
        feedback_repo=get_feedback_repo(),
        event_repo=get_event_repo(),
    )


def get_uc_reject_article() -> RejectArticleUseCase:
    return RejectArticleUseCase(
        article_repo=get_article_repo(), event_repo=get_event_repo()
    )


def get_uc_claim_article() -> ClaimArticleUseCase:
    return ClaimArticleUseCase(article_repo=get_article_repo(), event_repo=get_event_repo())


def get_uc_withdraw_article() -> WithdrawArticleUseCase:
    return WithdrawArticleUseCase(
        workspace_repo=get_workspace_repo(),
        article_repo=get_article_repo(),
        event_repo=get_event_repo(),
    )


def get_uc_create_feedback() -> CreateFeedbackUseCase:
    return CreateFeedbackUseCase(
        article_repo=get_article_repo(), feedback_repo=get_feedback_repo()
    )


def get_uc_set_feedback_status() -> SetFeedbackStatusUseCase:
    return SetFeedbackStatusUseCase(
        article_repo=get_article_repo(),
        feedback_repo=get_feedback_repo(),
        event_repo=get_event_repo(),
    )


def get_uc_add_reply() -> AddReplyUseCase:
    return AddReplyUseCase(
        workspace_repo=get_workspace_repo(),
        article_repo=get_article_repo(),
        feedback_repo=get_feedback_repo(),
        event_repo=get_event_repo(),
    )


def get_uc_publish_review() -> PublishReviewUseCase:
    return PublishReviewUseCase(
        article_repo=get_article_repo(),
        feedback_repo=get_feedback_repo(),
        event_repo=get_event_repo(),
    )


def get_uc_list_review_queue() -> ListReviewQueueUseCase:
    return ListReviewQueueUseCase(article_repo=get_article_repo())
