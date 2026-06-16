import pytest

from app.modules.workspaces.data.model import ArticleEventType
from app.modules.email.messages import (
    EmailContent,
    ReportEmailEvent,
    build_email_content,
    build_report_email_content,
)


def test_review_published_message():
    c = build_email_content(
        ArticleEventType.REVIEW_PUBLISHED, article_name="Bài A", reject_reason=None
    )
    assert c == EmailContent(
        subject="[UGC] Bài viết Bài A đã được nhận xét",
        body_text="Bạn thân mến,\n\nBài viết Bài A đã được nhận xét. Nhấn để xem.",
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


def test_report_created_message():
    c = build_report_email_content(ReportEmailEvent.CREATED, period="2026-06")
    assert c == EmailContent(
        subject="[UGC] Biên bản nghiệm thu kỳ 2026-06 đã được tạo",
        body_text=(
            "Biên bản nghiệm thu của bạn đã được tạo. "
            "Vui lòng truy cập link bên dưới để upload hình."
        ),
    )


def test_report_approved_message():
    c = build_report_email_content(ReportEmailEvent.APPROVED, period="2026-06")
    assert c == EmailContent(
        subject="[UGC] Biên bản nghiệm thu kỳ 2026-06 đã được duyệt",
        body_text=(
            "Biên bản nghiệm thu của bạn đã được duyệt. "
            "Bạn có thể truy cập link bên dưới để xem chi tiết."
        ),
    )


def test_report_unsupported_event_raises():
    with pytest.raises(ValueError, match="Unsupported report email event"):
        build_report_email_content("unknown_event", period="2026-06")  # type: ignore[arg-type]
