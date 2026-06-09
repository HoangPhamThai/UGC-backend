from datetime import datetime
import traceback
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.core.security import generate_api_key, hash_api_key
from app.modules.api_keys.data.model import ApiKey
from app.modules.api_keys.domain.repo import ApiKeyRepo


@dataclass
class CreateApiKeyResult:
    id: str
    name: str
    api_key: str
    key_prefix: str
    created_at: datetime


@dataclass(frozen=True)
class CreateApiKeyUseCase(LoggerMixin):
    api_key_repo: ApiKeyRepo

    async def execute(self, *, user_id: str, name: str) -> CreateApiKeyResult:
        try:
            raw_key = generate_api_key()
            key_hash = hash_api_key(raw_key)
            key_prefix = raw_key[:8]

            api_key = ApiKey(
                user_id=user_id,
                name=name,
                key_hash=key_hash,
                key_prefix=key_prefix,
            )
            created = await self.api_key_repo.create(api_key)
            self.log_info(f"API key created: id={created.id} for user={user_id}")

            return CreateApiKeyResult(
                id=created.id,
                name=created.name,
                api_key=raw_key,
                key_prefix=key_prefix,
                created_at=created.created_at,
            )
        except Exception as e:
            self.log_exception(f"CreateApiKeyUseCase error: {str(e)}")
            self.log_exception(traceback.format_exc())
            raise Exception(f"Failed to create API key: {str(e)}") from e
