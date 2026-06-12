# app/modules/workspaces/domain/usecases/add_reply.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.users.data.model import User, UserRole
from app.modules.workspaces.data.model import (
    ArticleEvent,
    ArticleEventType,
    Feedback,
    FeedbackReply,
)
from app.modules.workspaces.domain.errors import (
    ArticleNotFoundError,
    ClaimConflictError,
    FeedbackNotFoundError,
)
from app.modules.workspaces.domain.repo import (
    ArticleEventRepo,
    ArticleRepo,
    FeedbackRepo,
    WorkspaceRepo,
)
from app.modules.workspaces.domain.usecases._review_guard import ensure_qc_scope


@dataclass(frozen=True)
class AddReplyUseCase(LoggerMixin):
    workspace_repo: WorkspaceRepo
    article_repo: ArticleRepo
    feedback_repo: FeedbackRepo
    event_repo: ArticleEventRepo

    async def execute(
        self, *, workspace_id: str, article_id: str, feedback_id: str,
        body: str, caller: User,
    ) -> Feedback:
        article = await self.article_repo.get_by_id(article_id)
        if article is None or article.workspace_id != workspace_id:
            raise ArticleNotFoundError()

        # Authorize: the claiming QC (or superuser), or the workspace-owning creator.
        if caller.role in (UserRole.QC, UserRole.SUPERUSER):
            ensure_qc_scope(article, caller)
            if caller.role == UserRole.QC and article.claimed_by != caller.id:
                raise ClaimConflictError("You must claim this article before replying")
        else:
            ws = await self.workspace_repo.get_by_id(workspace_id)
            if ws is None or ws.owner_user_id != caller.id:
                raise ArticleNotFoundError()

        feedback = await self.feedback_repo.get_by_id(feedback_id)
        if feedback is None or feedback.article_id != article_id:
            raise FeedbackNotFoundError()

        reply = FeedbackReply(author_id=caller.id, body=body)
        updated = await self.feedback_repo.add_reply(feedback_id, reply)
        if updated is None:
            raise FeedbackNotFoundError()

        await self.article_repo.touch_activity(article_id, actor_id=caller.id)
        await self.event_repo.create(
            ArticleEvent(
                article_id=article_id, actor_id=caller.id, type=ArticleEventType.REPLY_ADDED,
                payload={"feedback_id": feedback_id},
            )
        )
        self.log_info(f"Reply added: feedback={feedback_id} by={caller.id}")
        return updated
