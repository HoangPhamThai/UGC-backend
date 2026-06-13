# app/modules/interim_keys/presentation/routes.py
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.auth import get_current_user
from app.core.model import StandardResponse, create_success_response, to_epoch_ms
from app.modules.interim_keys.presentation.deps import (
    get_uc_issue_interim_key,
    get_uc_revoke_interim_key,
)
from app.modules.interim_keys.presentation.schema import InterimKeyResponse
from app.modules.users.data.model import User, UserRole

router = APIRouter(tags=["interim-keys"])

_ISSUER_ROLES = {UserRole.ADMIN, UserRole.SUPERUSER}


@router.post("/interim-key", response_model=StandardResponse[InterimKeyResponse])
async def issue_interim_key(
    current_user: User = Depends(get_current_user),
    uc=Depends(get_uc_issue_interim_key),
):
    if current_user.role not in _ISSUER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )
    issued = await uc.execute(user_id=current_user.id, now=datetime.now(timezone.utc))
    return create_success_response(
        InterimKeyResponse(
            interim_key=issued.raw_key, expires_at=to_epoch_ms(issued.expires_at)
        )
    )


@router.delete("/interim-key", response_model=StandardResponse)
async def revoke_interim_key(
    request: Request,
    uc=Depends(get_uc_revoke_interim_key),
):
    raw = request.headers.get("X-Interim-Key")
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing interim key"
        )
    deleted = await uc.execute(raw_key=raw)
    return create_success_response({"deleted": deleted})
