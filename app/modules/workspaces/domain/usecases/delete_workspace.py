# app/modules/workspaces/domain/usecases/delete_workspace.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.users.data.model import User
from app.modules.workspaces.domain.errors import WorkspaceNotFoundError
from app.modules.workspaces.domain.repo import ArticleRepo, WorkspaceRepo


@dataclass(frozen=True)
class DeleteWorkspaceUseCase(LoggerMixin):
    workspace_repo: WorkspaceRepo
    article_repo: ArticleRepo

    async def execute(self, *, workspace_id: str, caller: User) -> None:
        ws = await self.workspace_repo.get_by_id(workspace_id)
        if ws is None or ws.owner_user_id != caller.id:
            # Hide existence for non-owners (404, not 403).
            raise WorkspaceNotFoundError()

        await self.workspace_repo.delete(workspace_id)
        deleted = await self.article_repo.delete_by_workspace(workspace_id)
        self.log_info(
            f"Workspace deleted: id={workspace_id} cascade_articles={deleted}"
        )
