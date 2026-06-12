# app/modules/notifications/presentation/routes.py
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.core.auth import get_current_user
from app.core.model import StandardResponse, create_success_response
from app.modules.notifications.presentation.deps import (
    get_uc_list_notifications,
    get_uc_mark_all_notifications_read,
    get_uc_mark_notification_read,
)
from app.modules.notifications.presentation.schema import (
    NotificationListResponse,
    NotificationResponse,
)
from app.modules.users.data.model import User

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=StandardResponse[NotificationListResponse])
async def list_notifications(
    unread_only: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    uc=Depends(get_uc_list_notifications),
):
    result = await uc.execute(
        recipient_id=current_user.id, unread_only=unread_only, page=page, limit=limit
    )
    data = NotificationListResponse(
        items=[NotificationResponse.from_model(n) for n in result.items],
        total=result.total,
        unread_count=result.unread_count,
    )
    return create_success_response(data)


@router.post("/read-all", response_model=StandardResponse)
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    uc=Depends(get_uc_mark_all_notifications_read),
):
    count = await uc.execute(recipient_id=current_user.id)
    return create_success_response(None, f"Marked {count} notifications read")


@router.post("/{notification_id}/read", response_model=StandardResponse[NotificationResponse])
async def mark_read(
    notification_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    uc=Depends(get_uc_mark_notification_read),
):
    n = await uc.execute(notification_id=notification_id, recipient_id=current_user.id)
    if n is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return create_success_response(NotificationResponse.from_model(n))
