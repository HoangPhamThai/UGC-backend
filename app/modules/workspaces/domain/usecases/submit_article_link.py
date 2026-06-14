# app/modules/workspaces/domain/usecases/submit_article_link.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.users.data.model import User
from app.modules.workspaces.data.model import Article, ArticleStatus, MAX_LINK_EDITS
from app.modules.workspaces.domain.errors import (
    ArticleNotFoundError,
    ArticleStateConflictError,
    InvalidInputError,
    WorkspaceNotFoundError,
)
from app.modules.workspaces.domain.link_platform import detect_platform
from app.modules.workspaces.domain.repo import ArticleRepo, WorkspaceRepo


@dataclass(frozen=True)
class SubmitArticleLinkUseCase(LoggerMixin):
    """Attach or re-edit the public link of an approved article (spec §5.1).

    Guards: the article must be approved, not locked by a report, and within the
    link-edit cap; the URL must be a supported (TikTok/Threads) link. The first
    submit does not consume an edit; re-submitting the identical URL is a no-op.
    """

    workspace_repo: WorkspaceRepo
    article_repo: ArticleRepo

    async def execute(
        self, *, workspace_id: str, article_id: str, caller: User, link: str
    ) -> Article:
        trimmed = (link or "").strip()
        if not trimmed:
            raise InvalidInputError("link must not be empty")
        if detect_platform(trimmed) is None:
            raise InvalidInputError("link must be a TikTok or Threads URL")

        ws = await self.workspace_repo.get_by_id(workspace_id)
        if ws is None or ws.owner_user_id != caller.id:
            raise WorkspaceNotFoundError()

        article = await self.article_repo.get_by_id(article_id)
        if article is None or article.workspace_id != workspace_id:
            raise ArticleNotFoundError()

        if article.report_id is not None:
            raise ArticleStateConflictError(
                "Article is locked by an acceptance report"
            )
        if article.status != ArticleStatus.APPROVED:
            raise ArticleStateConflictError(
                "Link can only be attached to an approved article"
            )

        if article.link is None:
            new_count = article.link_edit_count  # first submit — no edit consumed
        elif trimmed == article.link:
            return article  # idempotent — same URL, nothing to change
        elif article.link_edit_count >= MAX_LINK_EDITS:
            raise ArticleStateConflictError("Link edit limit reached")
        else:
            new_count = article.link_edit_count + 1

        updated = await self.article_repo.set_link(
            article_id, link=trimmed, link_edit_count=new_count
        )
        if updated is None:
            raise ArticleNotFoundError()
        self.log_info(
            f"Article link set: id={article_id} edits={updated.link_edit_count}"
        )
        return updated
