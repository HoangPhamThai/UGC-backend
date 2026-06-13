import pytest

from app.modules.chat.data.model import ChatMessage, ChatRole
from app.modules.chat.domain.errors import ChatSessionNotFoundError
from app.modules.chat.domain.usecases.clear_messages import ClearMessagesUseCase
from app.modules.chat.domain.usecases.list_messages import ListMessagesUseCase
from app.modules.chat.domain.usecases.append_messages import AppendMessagesUseCase
from tests.conftest import FakeChatSessionRepo, make_chat_session


def _um(text):
    return ChatMessage(role=ChatRole.USER, content=text)


def _am(text):
    return ChatMessage(role=ChatRole.ASSISTANT, content=text)


async def test_append_sets_title_from_first_user_message_when_empty():
    repo = FakeChatSessionRepo([make_chat_session(sid="cs_1", user_id="u_admin", title="")])
    uc = AppendMessagesUseCase(repo=repo)
    s = await uc.execute(
        session_id="cs_1", caller_id="u_admin",
        messages=[_um("How many articles this month?"), _am("42 articles.")],
    )
    assert [m.content for m in s.messages] == ["How many articles this month?", "42 articles."]
    assert s.title == "How many articles this month?"


async def test_append_does_not_overwrite_existing_title():
    repo = FakeChatSessionRepo([make_chat_session(sid="cs_1", user_id="u_admin", title="Kept")])
    uc = AppendMessagesUseCase(repo=repo)
    s = await uc.execute(session_id="cs_1", caller_id="u_admin", messages=[_um("hi")])
    assert s.title == "Kept"


async def test_append_nonowner_404():
    repo = FakeChatSessionRepo([make_chat_session(sid="cs_1", user_id="u_admin")])
    uc = AppendMessagesUseCase(repo=repo)
    with pytest.raises(ChatSessionNotFoundError):
        await uc.execute(session_id="cs_1", caller_id="u_intruder", messages=[_um("x")])


async def test_list_messages_tail_limit():
    msgs = [_um("m1"), _am("m2"), _um("m3"), _am("m4")]
    repo = FakeChatSessionRepo([make_chat_session(sid="cs_1", user_id="u_admin", messages=msgs)])
    uc = ListMessagesUseCase(repo=repo)
    all_msgs = await uc.execute(session_id="cs_1", caller_id="u_admin", limit=None)
    assert [m.content for m in all_msgs] == ["m1", "m2", "m3", "m4"]
    last2 = await uc.execute(session_id="cs_1", caller_id="u_admin", limit=2)
    assert [m.content for m in last2] == ["m3", "m4"]


async def test_list_messages_nonowner_404():
    repo = FakeChatSessionRepo([make_chat_session(sid="cs_1", user_id="u_admin")])
    uc = ListMessagesUseCase(repo=repo)
    with pytest.raises(ChatSessionNotFoundError):
        await uc.execute(session_id="cs_1", caller_id="u_intruder", limit=None)


async def test_clear_messages_keeps_session():
    repo = FakeChatSessionRepo([make_chat_session(sid="cs_1", user_id="u_admin", messages=[_um("x")])])
    uc = ClearMessagesUseCase(repo=repo)
    s = await uc.execute(session_id="cs_1", caller_id="u_admin")
    assert s.id == "cs_1" and s.messages == []
    with pytest.raises(ChatSessionNotFoundError):
        await uc.execute(session_id="cs_1", caller_id="u_intruder")
