# app/modules/workspaces/domain/usecases/create_workspace.py
import traceback
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.workspaces.data.model import Workspace
from app.modules.workspaces.domain.repo import WorkspaceRepo


@dataclass(frozen=True)
class CreateWorkspaceUseCase(LoggerMixin):
    workspace_repo: WorkspaceRepo

    async def execute(self, *, name: str, owner_user_id: str) -> Workspace:
        try:
            trimmed = name.strip()
            if not trimmed:
                raise ValueError("name must not be empty")
            workspace = Workspace(
                name=trimmed,
                name_lower=trimmed.casefold(),
                owner_user_id=owner_user_id,
            )
            created = await self.workspace_repo.create(workspace)
            self.log_info(f"Workspace created: id={created.id} owner={owner_user_id}")
            return created
        except Exception as e:
            # Let WorkspaceNameTakenError, ValueError, etc. bubble unchanged.
            if isinstance(e, (ValueError,)):
                raise
            from app.modules.workspaces.domain.errors import WorkspaceError
            if isinstance(e, WorkspaceError):
                raise
            self.log_exception(f"CreateWorkspaceUseCase error: {str(e)}")
            self.log_exception(traceback.format_exc())
            raise
