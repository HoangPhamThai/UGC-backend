from dataclasses import dataclass

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
            subject=f"Bài viết {article_name} đã được nhận xét",
            body_text=f"Bài viết {article_name} đã được nhận xét. Nhấn để xem.",
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
