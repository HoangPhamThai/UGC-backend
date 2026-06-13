import pytest

from app.modules.chat.domain.errors import ChatSessionNotFoundError
from app.modules.chat.domain.usecases.create_session import CreateSessionUseCase
from app.modules.chat.domain.usecases.list_sessions import ListSessionsUseCase
from app.modules.chat.domain.usecases.get_session import GetSessionUseCase
from app.modules.chat.domain.usecases.delete_session import DeleteSessionUseCase
from tests.conftest import FakeChatSessionRepo, make_chat_session


async def test_create_session_for_owner():
    repo = FakeChatSessionRepo()
    uc = CreateSessionUseCase(repo=repo)
    s = await uc.execute(user_id="u_admin", title="My chat")
    assert s.user_id == "u_admin" and s.title == "My chat" and s.messages == []
    assert repo.items[s.id] is s


async def test_list_sessions_returns_summaries_and_total():
    repo = FakeChatSessionRepo([
        make_chat_session(sid="cs_1", user_id="u_admin", title="a", messages=[]),
        make_chat_session(sid="cs_2", user_id="u_other", title="b"),
    ])
    uc = ListSessionsUseCase(repo=repo)
    items, total = await uc.execute(user_id="u_admin", page=1, limit=10)
    assert [i.id for i in items] == ["cs_1"]
    assert items[0].message_count == 0
    assert total == 1


async def test_get_session_owner_ok_and_nonowner_404():
    repo = FakeChatSessionRepo([make_chat_session(sid="cs_1", user_id="u_admin")])
    uc = GetSessionUseCase(repo=repo)
    assert (await uc.execute(session_id="cs_1", caller_id="u_admin")).id == "cs_1"
    with pytest.raises(ChatSessionNotFoundError):
        await uc.execute(session_id="cs_1", caller_id="u_intruder")
    with pytest.raises(ChatSessionNotFoundError):
        await uc.execute(session_id="missing", caller_id="u_admin")


async def test_delete_session_owner_only():
    repo = FakeChatSessionRepo([make_chat_session(sid="cs_1", user_id="u_admin")])
    uc = DeleteSessionUseCase(repo=repo)
    with pytest.raises(ChatSessionNotFoundError):
        await uc.execute(session_id="cs_1", caller_id="u_intruder")
    await uc.execute(session_id="cs_1", caller_id="u_admin")
    assert "cs_1" not in repo.items
