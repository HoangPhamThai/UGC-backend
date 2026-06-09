from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.core.model import StandardResponse, create_success_response
from app.modules.users.data.model import User
from app.modules.users.presentation.schema import UserMeResponse

router = APIRouter(prefix="/users", tags=["users"])


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
        created_at=current_user.created_at,
    )
    return create_success_response(data, "User retrieved")
