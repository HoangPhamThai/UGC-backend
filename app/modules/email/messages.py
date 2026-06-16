from dataclasses import dataclass
from enum import Enum

from app.modules.workspaces.data.model import ArticleEventType


@dataclass(frozen=True)
class EmailContent:
    subject: str
    body_text: str


def build_email_content(
    event_type: ArticleEventType,
    *,
    article_name: str,
    reject_reason: str | None,
) -> EmailContent:
    if event_type == ArticleEventType.REVIEW_PUBLISHED:
        return EmailContent(
            subject=f"[UGC] Bài viết {article_name} đã được nhận xét",
            body_text=f"Bạn thân mến,\n\nBài viết {article_name} đã được nhận xét. Nhấn để xem.",
        )
    if event_type == ArticleEventType.APPROVED:
        return EmailContent(
            subject=f"Bài viết {article_name} đã được xét duyệt",
            body_text=(
                f"Bài viết {article_name} đã được xét duyệt. "
                "Vui lòng upload lên nền tảng và gửi link public."
            ),
        )
    if event_type == ArticleEventType.REJECTED:
        reason = reject_reason or ""
        return EmailContent(
            subject=f"Bài viết {article_name} đã bị huỷ",
            body_text=f"Bài viết {article_name} đã được huỷ với nội dung {reason}.",
        )
    raise ValueError(f"Unsupported email event type: {event_type.value}")


class ReportEmailEvent(str, Enum):
    CREATED = "report_created"
    APPROVED = "report_approved"


def build_report_email_content(
    event: ReportEmailEvent, *, period: str
) -> EmailContent:
    if event == ReportEmailEvent.CREATED:
        return EmailContent(
            subject=f"[UGC] Biên bản nghiệm thu kỳ {period} đã được tạo",
            body_text=(
                "Biên bản nghiệm thu của bạn đã được tạo. "
                "Vui lòng truy cập link bên dưới để upload hình."
            ),
        )
    if event == ReportEmailEvent.APPROVED:
        return EmailContent(
            subject=f"[UGC] Biên bản nghiệm thu kỳ {period} đã được duyệt",
            body_text=(
                "Biên bản nghiệm thu của bạn đã được duyệt. "
                "Bạn có thể truy cập link bên dưới để xem chi tiết."
            ),
        )
    raise ValueError(f"Unsupported report email event: {event}")
