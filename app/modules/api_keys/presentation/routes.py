from fastapi import APIRouter, Body, Depends, HTTPException, status

from app.core.auth import get_current_user
from app.core.model import StandardResponse, create_success_response
from app.modules.api_keys.domain.usecases.create_api_key import CreateApiKeyUseCase
from app.modules.api_keys.domain.usecases.list_api_keys import ListApiKeysUseCase
from app.modules.api_keys.domain.usecases.delete_api_key import DeleteApiKeyUseCase
from app.modules.api_keys.presentation.deps import (
    get_uc_create_api_key,
    get_uc_list_api_keys,
    get_uc_delete_api_key,
)
from app.modules.api_keys.presentation.schema import (
    CreateApiKeyRequest,
    CreateApiKeyResponse,
    ApiKeyInfo,
)
from app.modules.users.data.model import User

router = APIRouter(prefix="/api-keys", tags=["api_keys"])


@router.post(
    "",
    response_model=StandardResponse[CreateApiKeyResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_api_key(
    request: CreateApiKeyRequest = Body(...),
    current_user: User = Depends(get_current_user),
    uc: CreateApiKeyUseCase = Depends(get_uc_create_api_key),
):
    try:
        result = await uc.execute(user_id=current_user.id, name=request.name)
        data = CreateApiKeyResponse(
            id=result.id,
            name=result.name,
            api_key=result.api_key,
            key_prefix=result.key_prefix,
            created_at=result.created_at,
        )
        return create_success_response(data, "API key created")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get(
    "",
    response_model=StandardResponse,
)
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    uc: ListApiKeysUseCase = Depends(get_uc_list_api_keys),
):
    try:
        keys = await uc.execute(user_id=current_user.id)
        items = [
            ApiKeyInfo(
                id=k.id,
                name=k.name,
                key_prefix=k.key_prefix,
                created_at=k.created_at,
            )
            for k in keys
        ]
        return create_success_response(
            {"items": items}, f"Found {len(items)} API key(s)"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.delete(
    "/{key_id}",
    response_model=StandardResponse,
)
async def delete_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    uc: DeleteApiKeyUseCase = Depends(get_uc_delete_api_key),
):
    try:
        await uc.execute(key_id=key_id, user_id=current_user.id)
        return create_success_response(None, "API key deleted")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
