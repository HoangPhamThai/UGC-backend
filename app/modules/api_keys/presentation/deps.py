from fastapi import Depends

from app.modules.api_keys.data.repo import ApiKeyDataRepository
from app.modules.api_keys.domain.repo import ApiKeyRepo
from app.modules.api_keys.domain.usecases.create_api_key import CreateApiKeyUseCase
from app.modules.api_keys.domain.usecases.list_api_keys import ListApiKeysUseCase
from app.modules.api_keys.domain.usecases.delete_api_key import DeleteApiKeyUseCase


def get_api_key_repo() -> ApiKeyRepo:
    return ApiKeyDataRepository()


def get_uc_create_api_key(
    api_key_repo: ApiKeyRepo = Depends(get_api_key_repo),
) -> CreateApiKeyUseCase:
    return CreateApiKeyUseCase(api_key_repo=api_key_repo)


def get_uc_list_api_keys(
    api_key_repo: ApiKeyRepo = Depends(get_api_key_repo),
) -> ListApiKeysUseCase:
    return ListApiKeysUseCase(api_key_repo=api_key_repo)


def get_uc_delete_api_key(
    api_key_repo: ApiKeyRepo = Depends(get_api_key_repo),
) -> DeleteApiKeyUseCase:
    return DeleteApiKeyUseCase(api_key_repo=api_key_repo)
