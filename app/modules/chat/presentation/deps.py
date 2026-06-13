# app/modules/chat/presentation/deps.py
from fastapi import Depends

from app.modules.chat.data.repo import ChatSessionDataRepository
from app.modules.chat.domain.repo import ChatSessionRepo
from app.modules.chat.domain.usecases.create_session import CreateSessionUseCase
from app.modules.chat.domain.usecases.list_sessions import ListSessionsUseCase
from app.modules.chat.domain.usecases.get_session import GetSessionUseCase
from app.modules.chat.domain.usecases.delete_session import DeleteSessionUseCase
from app.modules.chat.domain.usecases.clear_messages import ClearMessagesUseCase
from app.modules.chat.domain.usecases.list_messages import ListMessagesUseCase
from app.modules.chat.domain.usecases.append_messages import AppendMessagesUseCase


def get_chat_repo() -> ChatSessionRepo:
    return ChatSessionDataRepository()


def get_uc_create_session(repo: ChatSessionRepo = Depends(get_chat_repo)) -> CreateSessionUseCase:
    return CreateSessionUseCase(repo=repo)


def get_uc_list_sessions(repo: ChatSessionRepo = Depends(get_chat_repo)) -> ListSessionsUseCase:
    return ListSessionsUseCase(repo=repo)


def get_uc_get_session(repo: ChatSessionRepo = Depends(get_chat_repo)) -> GetSessionUseCase:
    return GetSessionUseCase(repo=repo)


def get_uc_delete_session(repo: ChatSessionRepo = Depends(get_chat_repo)) -> DeleteSessionUseCase:
    return DeleteSessionUseCase(repo=repo)


def get_uc_clear_messages(repo: ChatSessionRepo = Depends(get_chat_repo)) -> ClearMessagesUseCase:
    return ClearMessagesUseCase(repo=repo)


def get_uc_list_messages(repo: ChatSessionRepo = Depends(get_chat_repo)) -> ListMessagesUseCase:
    return ListMessagesUseCase(repo=repo)


def get_uc_append_messages(repo: ChatSessionRepo = Depends(get_chat_repo)) -> AppendMessagesUseCase:
    return AppendMessagesUseCase(repo=repo)
