from app.modules.chat.data.model import ChatMessage, ChatRole
from tests.conftest import FakeChatSessionRepo, make_chat_session


async def test_fake_append_and_clear():
    repo = FakeChatSessionRepo([make_chat_session(sid="cs_1", user_id="u1")])
    msg = ChatMessage(role=ChatRole.USER, content="hi")
    s = await repo.append_messages("cs_1", [msg], title="hi")
    assert [m.content for m in s.messages] == ["hi"] and s.title == "hi"
    s = await repo.clear_messages("cs_1")
    assert s.messages == []
    assert await repo.append_messages("missing", [msg], title=None) is None
