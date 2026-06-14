from fastapi import APIRouter, Body, Depends, HTTPException, Path, status

from app.core.auth import get_current_user
from app.core.model import StandardResponse, create_success_response
from app.core.permissions import Permission, require_permissions
from app.modules.profiles.domain.usecases.get_creator_profile import (
    GetCreatorProfileUseCase,
)
from app.modules.profiles.domain.usecases.get_my_profile import GetMyProfileUseCase
from app.modules.profiles.domain.usecases.upsert_my_profile import UpsertMyProfileUseCase
from app.modules.profiles.presentation.deps import (
    get_uc_get_creator_profile,
    get_uc_get_my_profile,
    get_uc_upsert_my_profile,
)
from app.modules.profiles.presentation.schema import ProfileResponse, UpdateProfileRequest
from app.modules.users.data.model import User

router = APIRouter(tags=["profiles"])


@router.get("/me/profile", response_model=StandardResponse[ProfileResponse])
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    uc: GetMyProfileUseCase = Depends(get_uc_get_my_profile),
):
    profile = await uc.execute(user_id=current_user.id)
    return create_success_response(ProfileResponse.from_model(profile))


@router.put("/me/profile", response_model=StandardResponse[ProfileResponse])
async def put_my_profile(
    body: UpdateProfileRequest = Body(...),
    current_user: User = Depends(get_current_user),
    uc: UpsertMyProfileUseCase = Depends(get_uc_upsert_my_profile),
):
    profile = await uc.execute(user_id=current_user.id, fields=body.model_dump())
    return create_success_response(ProfileResponse.from_model(profile), "Profile saved")


@router.get(
    "/admin/creators/{user_id}/profile",
    response_model=StandardResponse[ProfileResponse],
)
async def get_creator_profile(
    user_id: str = Path(...),
    current_user: User = Depends(require_permissions(Permission.USERS_READ_CREATOR)),
    uc: GetCreatorProfileUseCase = Depends(get_uc_get_creator_profile),
):
    profile = await uc.execute(user_id=user_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )
    return create_success_response(ProfileResponse.from_model(profile))
