import pytest

from app.modules.workspaces.data.model import ArticleEventType
from app.modules.email.messages import build_email_content, EmailContent


def test_review_published_message():
    c = build_email_content(
        ArticleEventType.REVIEW_PUBLISHED, article_name="Bài A", reject_reason=None
    )
    assert c == EmailContent(
        subject="Bài viết Bài A đã được nhận xét",
        body_text="Bài viết Bài A đã được nhận xét. Nhấn để xem.",
    )


def test_approved_message():
    c = build_email_content(
        ArticleEventType.APPROVED, article_name="Bài B", reject_reason=None
    )
    assert c == EmailContent(
        subject="Bài viết Bài B đã được xét duyệt",
        body_text=(
            "Bài viết Bài B đã được xét duyệt. "
            "Vui lòng upload lên nền tảng và gửi link public."
        ),
    )


def test_rejected_message_includes_reason():
    c = build_email_content(
        ArticleEventType.REJECTED,
        article_name="Bài C",
        reject_reason="Nội dung không phù hợp",
    )
    assert c == EmailContent(
        subject="Bài viết Bài C đã bị huỷ",
        body_text=(
            "Bài viết Bài C đã được huỷ với nội dung Nội dung không phù hợp."
        ),
    )


def test_unsupported_event_raises():
    with pytest.raises(ValueError, match="Unsupported"):
        build_email_content(ArticleEventType.REPLY_ADDED, article_name="X", reject_reason=None)
