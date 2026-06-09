import traceback
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.api_keys.data.model import ApiKey
from app.modules.api_keys.domain.repo import ApiKeyRepo


@dataclass(frozen=True)
class ListApiKeysUseCase(LoggerMixin):
    api_key_repo: ApiKeyRepo

    async def execute(self, *, user_id: str) -> list[ApiKey]:
        try:
            return await self.api_key_repo.list_by_user_id(user_id)
        except Exception as e:
            self.log_exception(f"ListApiKeysUseCase error: {str(e)}")
            self.log_exception(traceback.format_exc())
            raise Exception(f"Failed to list API keys: {str(e)}") from e
