from fastapi import Depends, HTTPException, status

from app.core.auth import get_current_principal
from app.modules.profiles.domain.repo import CreatorProfileRepo
from app.modules.profiles.presentation.deps import get_profile_repo
from app.modules.users.data.model import User, UserRole


async def require_profile_complete(
    user: User = Depends(get_current_principal),
    profile_repo: CreatorProfileRepo = Depends(get_profile_repo),
) -> User:
    """Block creators whose profile is incomplete. Non-creators bypass."""
    if user.role != UserRole.CREATOR:
        return user
    profile = await profile_repo.get_by_user_id(user.id)
    if profile is None or not profile.is_complete:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Complete your profile before continuing",
        )
    return user
