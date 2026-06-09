from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.core.model import StandardResponse, create_success_response
from app.core.permissions import ROLE_PERMISSIONS, Permission
from app.modules.users.data.model import User
from app.modules.users.presentation.schema import UserMeResponse

router = APIRouter(prefix="/users", tags=["users"])


def _permissions_for(user: User) -> list[Permission]:
    """Return the caller's permissions in a stable order (enum declaration)."""
    granted = ROLE_PERMISSIONS[user.role]
    return [p for p in Permission if p in granted]


@router.get(
    "/me",
    response_model=StandardResponse[UserMeResponse],
)
async def get_user_me(
    current_user: User = Depends(get_current_user),
):
    data = UserMeResponse(
        id=current_user.id,
        email=current_user.email,
        is_active=current_user.is_active,
        role=current_user.role,
        qc_product=current_user.qc_product,
        permissions=_permissions_for(current_user),
        created_at=current_user.created_at,
    )
    return create_success_response(data, "User retrieved")
