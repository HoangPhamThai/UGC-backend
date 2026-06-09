from fastapi import APIRouter, Body, Depends, HTTPException, Request, status

from app.core.auth import get_current_user
from app.core.model import StandardResponse, create_success_response
from app.core.rate_limit import limiter
from app.core.settings import settings
from app.modules.auth.domain.usecases.register import RegisterUseCase
from app.modules.auth.domain.usecases.login import LoginUseCase
from app.modules.auth.domain.usecases.refresh import RefreshTokenUseCase
from app.modules.auth.domain.usecases.logout import LogoutUseCase
from app.modules.auth.presentation.deps import (
    get_uc_register,
    get_uc_login,
    get_uc_refresh,
    get_uc_logout,
)
from app.modules.auth.presentation.schema import (
    RegisterRequest,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    AccessTokenResponse,
)
from app.modules.users.data.model import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(settings.register_rate_limit)
async def register(
    request: Request,
    body: RegisterRequest = Body(...),
    uc: RegisterUseCase = Depends(get_uc_register),
):
    try:
        await uc.execute(email=body.email, password=body.password)
        return create_success_response(None, "User registered")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post(
    "/login",
    response_model=StandardResponse[LoginResponse],
)
async def login(
    request: LoginRequest = Body(...),
    uc: LoginUseCase = Depends(get_uc_login),
):
    try:
        result = await uc.execute(email=request.email, password=request.password)
        data = LoginResponse(
            access_token=result.access_token,
            refresh_token=result.refresh_token,
        )
        return create_success_response(data, "Login successful")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post(
    "/refresh",
    response_model=StandardResponse[AccessTokenResponse],
)
async def refresh_token(
    request: RefreshRequest = Body(...),
    uc: RefreshTokenUseCase = Depends(get_uc_refresh),
):
    try:
        access_token = await uc.execute(refresh_token=request.refresh_token)
        data = AccessTokenResponse(access_token=access_token)
        return create_success_response(data, "Token refreshed")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post(
    "/logout",
    response_model=StandardResponse,
)
async def logout(
    current_user: User = Depends(get_current_user),
    uc: LogoutUseCase = Depends(get_uc_logout),
):
    try:
        await uc.execute(user_id=current_user.id)
        return create_success_response(None, "Logged out")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
