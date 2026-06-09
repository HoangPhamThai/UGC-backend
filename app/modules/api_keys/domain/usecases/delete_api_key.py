import traceback
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.api_keys.domain.repo import ApiKeyRepo


@dataclass(frozen=True)
class DeleteApiKeyUseCase(LoggerMixin):
    api_key_repo: ApiKeyRepo

    async def execute(self, *, key_id: str, user_id: str) -> bool:
        """Delete an API key, verifying it belongs to the user."""
        try:
            keys = await self.api_key_repo.list_by_user_id(user_id)
            if not any(k.id == key_id for k in keys):
                raise ValueError(f"API key not found: {key_id}")

            deleted = await self.api_key_repo.delete(key_id)
            self.log_info(f"API key deleted: id={key_id}")
            return deleted
        except ValueError:
            raise
        except Exception as e:
            self.log_exception(f"DeleteApiKeyUseCase error: {str(e)}")
            self.log_exception(traceback.format_exc())
            raise Exception(f"Failed to delete API key: {str(e)}") from e
