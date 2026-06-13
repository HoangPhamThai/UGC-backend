from datetime import datetime, timezone

from fastapi import HTTPException, Request, status
from jwt import PyJWTError

from app.core.security import decode_token, hash_interim_key
from app.modules.interim_keys.data.repo import InterimKeyDataRepository
from app.modules.users.data.model import User
from app.modules.users.data.repo import UserDataRepository


async def get_current_user(request: Request) -> User:
    """Resolve the current user from a Bearer JWT in the Authorization header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication",
        )

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


async def _resolve_interim_principal(raw_key: str) -> User:
    key_hash = hash_interim_key(raw_key)
    rec = await InterimKeyDataRepository().get_active_by_hash(
        key_hash, datetime.now(timezone.utc)
    )
    if rec is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired interim key",
        )
    user = await UserDataRepository().get_by_id(rec.user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user


async def get_current_principal(request: Request) -> User:
    """Resolve the caller from either a Bearer JWT (full user) or an
    X-Interim-Key header (agent acting for a user). A valid Bearer takes
    precedence. Sets request.state.is_interim for downstream permission checks."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        request.state.is_interim = False
        return await get_current_user(request)

    interim = request.headers.get("X-Interim-Key")
    if interim:
        user = await _resolve_interim_principal(interim)
        request.state.is_interim = True
        return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing authentication",
    )
