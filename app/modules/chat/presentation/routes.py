# app/modules/chat/presentation/routes.py
from typing import Optional

from fastapi import APIRouter, Body, Depends, Query

from app.core.auth import get_current_principal, get_current_user
from app.core.model import StandardResponse, create_success_response
from app.modules.chat.data.model import ChatMessage
from app.modules.chat.presentation.deps import (
    get_uc_append_messages,
    get_uc_clear_messages,
    get_uc_create_session,
    get_uc_delete_session,
    get_uc_get_session,
    get_uc_list_messages,
    get_uc_list_sessions,
)
from app.modules.chat.presentation.schema import (
    AppendMessagesRequest,
    ChatMessageResponse,
    ChatSessionListResponse,
    ChatSessionResponse,
    ChatSessionSummaryResponse,
    CreateSessionRequest,
    MessagesResponse,
)
from app.modules.users.data.model import User

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/sessions", response_model=StandardResponse[ChatSessionResponse], status_code=201)
async def create_session(
    body: CreateSessionRequest = Body(default=CreateSessionRequest()),
    current_user: User = Depends(get_current_user),
    uc=Depends(get_uc_create_session),
):
    session = await uc.execute(user_id=current_user.id, title=body.title or "")
    return create_success_response(ChatSessionResponse.from_session(session))


@router.get("/sessions", response_model=StandardResponse[ChatSessionListResponse])
async def list_sessions(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    uc=Depends(get_uc_list_sessions),
):
    items, total = await uc.execute(user_id=current_user.id, page=page, limit=limit)
    data = ChatSessionListResponse(
        items=[ChatSessionSummaryResponse.from_summary(s) for s in items], total=total
    )
    return create_success_response(data)


@router.get("/sessions/{session_id}", response_model=StandardResponse[ChatSessionResponse])
async def get_session(
    session_id: str,
    principal: User = Depends(get_current_principal),
    uc=Depends(get_uc_get_session),
):
    session = await uc.execute(session_id=session_id, caller_id=principal.id)
    return create_success_response(ChatSessionResponse.from_session(session))


@router.delete("/sessions/{session_id}", response_model=StandardResponse)
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    uc=Depends(get_uc_delete_session),
):
    await uc.execute(session_id=session_id, caller_id=current_user.id)
    return create_success_response(None, "Session deleted")


@router.delete("/sessions/{session_id}/messages", response_model=StandardResponse[ChatSessionResponse])
async def clear_messages(
    session_id: str,
    current_user: User = Depends(get_current_user),
    uc=Depends(get_uc_clear_messages),
):
    session = await uc.execute(session_id=session_id, caller_id=current_user.id)
    return create_success_response(ChatSessionResponse.from_session(session))


@router.get("/sessions/{session_id}/messages", response_model=StandardResponse[MessagesResponse])
async def list_messages(
    session_id: str,
    limit: Optional[int] = Query(default=None, ge=1),
    principal: User = Depends(get_current_principal),
    uc=Depends(get_uc_list_messages),
):
    messages = await uc.execute(session_id=session_id, caller_id=principal.id, limit=limit)
    data = MessagesResponse(messages=[ChatMessageResponse.from_message(m) for m in messages])
    return create_success_response(data)


@router.post("/sessions/{session_id}/messages", response_model=StandardResponse[ChatSessionResponse])
async def append_messages(
    session_id: str,
    body: AppendMessagesRequest = Body(...),
    principal: User = Depends(get_current_principal),
    uc=Depends(get_uc_append_messages),
):
    msgs = [ChatMessage(role=m.role, content=m.content) for m in body.messages]
    session = await uc.execute(session_id=session_id, caller_id=principal.id, messages=msgs)
    return create_success_response(ChatSessionResponse.from_session(session))
