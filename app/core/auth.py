from fastapi import HTTPException, Request, status
from jwt import PyJWTError

from app.core.security import decode_token, hash_api_key
from app.modules.users.data.model import User
from app.modules.users.data.repo import UserDataRepository
from app.modules.api_keys.data.repo import ApiKeyDataRepository


async def get_current_user(request: Request) -> User:
    """Resolve the current user from either Bearer token or X-API-Key.

    Rejects requests that send both headers.
    """
    auth_header = request.headers.get("Authorization")
    api_key_header = request.headers.get("X-API-Key")

    if auth_header and api_key_header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot use both Authorization and X-API-Key headers",
        )

    if auth_header:
        return await _resolve_from_bearer(auth_header)

    if api_key_header:
        return await _resolve_from_api_key(api_key_header)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing authentication",
    )


async def _resolve_from_bearer(auth_header: str) -> User:
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format",
        )
    token = auth_header[7:]
    try:
        payload = decode_token(token)
    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user_repo = UserDataRepository()
    user = await user_repo.get_by_id(user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user


async def _resolve_from_api_key(raw_key: str) -> User:
    key_hash = hash_api_key(raw_key)
    api_key_repo = ApiKeyDataRepository()
    api_key = await api_key_repo.get_by_key_hash(key_hash)
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    user_repo = UserDataRepository()
    user = await user_repo.get_by_id(api_key.user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user
