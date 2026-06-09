from fastapi import APIRouter, Body, Depends, HTTPException, Query, status

from app.core.auth import get_current_user
from app.core.model import StandardResponse, create_success_response
from app.core.permissions import (
    has_permission,
    permission_to_create,
    permission_to_read,
    permission_to_update,
)
from app.modules.admin.domain.usecases.create_managed_user import (
    CreateManagedUserUseCase,
)
from app.modules.admin.domain.usecases.get_managed_user import GetManagedUserUseCase
from app.modules.admin.domain.usecases.list_users_by_role import (
    ListUsersByRoleUseCase,
)
from app.modules.admin.domain.usecases.update_managed_user import (
    UpdateManagedUserUseCase,
)
from app.modules.admin.presentation.deps import (
    get_uc_create_managed_user,
    get_uc_get_managed_user,
    get_uc_list_users_by_role,
    get_uc_update_managed_user,
)
from app.modules.admin.presentation.schema import (
    CreateManagedUserRequest,
    ManagedUserListResponse,
    ManagedUserResponse,
    UpdateManagedUserRequest,
)
from app.modules.users.data.model import User, UserRole

router = APIRouter(prefix="/admin", tags=["admin"])


def _to_response(user: User) -> ManagedUserResponse:
    return ManagedUserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        qc_product=user.qc_product,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.post(
    "/users",
    response_model=StandardResponse[ManagedUserResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_managed_user(
    body: CreateManagedUserRequest = Body(...),
    current_user: User = Depends(get_current_user),
    uc: CreateManagedUserUseCase = Depends(get_uc_create_managed_user),
):
    perm = permission_to_create(body.role)
    if perm is None or not has_permission(current_user, perm):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    try:
        user = await uc.execute(
            email=body.email,
            password=body.password,
            role=body.role,
            qc_product=body.qc_product,
        )
        return create_success_response(_to_response(user), "User created")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get(
    "/users",
    response_model=StandardResponse[ManagedUserListResponse],
)
async def list_users(
    role: UserRole = Query(..., description="Role to filter by"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    uc: ListUsersByRoleUseCase = Depends(get_uc_list_users_by_role),
):
    perm = permission_to_read(role)
    if perm is None or not has_permission(current_user, perm):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    try:
        result = await uc.execute(role=role, page=page, page_size=page_size)
        data = ManagedUserListResponse(
            items=[_to_response(u) for u in result.items],
            total=result.total,
            page=page,
            page_size=page_size,
        )
        return create_success_response(data, f"Found {result.total} user(s)")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get(
    "/users/{user_id}",
    response_model=StandardResponse[ManagedUserResponse],
)
async def get_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    uc: GetManagedUserUseCase = Depends(get_uc_get_managed_user),
):
    try:
        user = await uc.execute(user_id=user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        perm = permission_to_read(user.role)
        if perm is None or not has_permission(current_user, perm):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return create_success_response(_to_response(user), "User retrieved")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.patch(
    "/users/{user_id}",
    response_model=StandardResponse[ManagedUserResponse],
)
async def update_user(
    user_id: str,
    body: UpdateManagedUserRequest = Body(...),
    current_user: User = Depends(get_current_user),
    uc_get: GetManagedUserUseCase = Depends(get_uc_get_managed_user),
    uc_update: UpdateManagedUserUseCase = Depends(get_uc_update_managed_user),
):
    try:
        target = await uc_get.execute(user_id=user_id)
        if target is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        perm = permission_to_update(target.role)
        if perm is None or not has_permission(current_user, perm):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        # Detect whether qc_product was explicitly present in the request body
        # (`exclude_unset=True` returns the dict keys the client actually sent).
        qc_provided = "qc_product" in body.model_dump(exclude_unset=True)
        try:
            updated = await uc_update.execute(
                user_id=user_id,
                is_active=body.is_active,
                password=body.password,
                qc_product=body.qc_product,
                qc_product_provided=qc_provided,
            )
        except ValueError as ve:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve)
            )
        if updated is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        return create_success_response(_to_response(updated), "User updated")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
