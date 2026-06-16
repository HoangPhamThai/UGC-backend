import asyncio
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Callable, Optional, Protocol, Sequence

import smtplib

from app.core.logging_mixin import LoggerMixin
from app.modules.email.messages import build_email_content
from app.modules.email.templates import build_article_link, render_html_email
from app.modules.users.domain.repo import UserRepo
from app.modules.workspaces.data.model import Article, ArticleEventType

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
DEFAULT_RETRY_DELAYS: tuple[float, ...] = (2.0, 4.0, 8.0)


class SmtpSender(Protocol):
    def __call__(
        self,
        *,
        from_addr: str,
        password: str,
        to_addr: str,
        subject: str,
        html_body: str,
    ) -> None: ...


def _default_smtp_sender(
    *,
    from_addr: str,
    password: str,
    to_addr: str,
    subject: str,
    html_body: str,
) -> None:
    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content("Vui lòng xem email bằng trình duyệt hỗ trợ HTML.")
    msg.add_alternative(html_body, subtype="html")
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(from_addr, password)
        smtp.send_message(msg)


@dataclass
class EmailService(LoggerMixin):
    from_email: Optional[str]
    email_app_password: Optional[str]
    frontend_base_url: Optional[str]
    user_repo: UserRepo
    smtp_sender: SmtpSender = field(default=_default_smtp_sender)
    retry_delays: Sequence[float] = DEFAULT_RETRY_DELAYS

    @property
    def enabled(self) -> bool:
        return bool(
            self.from_email
            and self.email_app_password
            and self.frontend_base_url
        )

    def schedule(
        self,
        *,
        event_type: ArticleEventType,
        article: Article,
        creator_user_id: str,
    ) -> None:
        if not self.enabled:
            self.log_info("Email notifications disabled; skipping schedule")
            return
        asyncio.create_task(
            self.send_article_event(
                event_type=event_type,
                article=article,
                creator_user_id=creator_user_id,
            )
        )

    async def send_article_event(
        self,
        *,
        event_type: ArticleEventType,
        article: Article,
        creator_user_id: str,
    ) -> None:
        if not self.enabled:
            return
        try:
            user = await self.user_repo.get_by_id(creator_user_id)
            to_addr = (user.email if user else "") or ""
            if not to_addr.strip():
                self.log_warning(
                    f"No creator email for user {creator_user_id}; skipping email"
                )
                return
            content = build_email_content(
                event_type,
                article_name=article.name,
                reject_reason=article.reject_reason,
            )
            article_url = build_article_link(
                self.frontend_base_url or "",
                article.workspace_id,
                article.id,
            )
            html_body = render_html_email(
                subject=content.subject,
                body_text=content.body_text,
                article_url=article_url,
            )
            await self._send_with_retry(
                to_addr=to_addr.strip(),
                subject=content.subject,
                html_body=html_body,
                event_type=event_type,
                article_id=article.id,
            )
        except Exception as exc:  # noqa: BLE001 - best-effort background task
            self.log_warning(
                f"Email task failed for article {article.id} ({event_type.value}): {exc}"
            )

    async def _send_with_retry(
        self,
        *,
        to_addr: str,
        subject: str,
        html_body: str,
        event_type: ArticleEventType,
        article_id: str,
    ) -> None:
        attempts = len(self.retry_delays) + 1
        for attempt in range(1, attempts + 1):
            try:
                await asyncio.to_thread(
                    self._send_sync,
                    to_addr=to_addr,
                    subject=subject,
                    html_body=html_body,
                )
                return
            except Exception as exc:  # noqa: BLE001
                if attempt >= attempts:
                    self.log_warning(
                        f"Email send failed after {attempts} attempts "
                        f"(article={article_id}, event={event_type.value}, to={to_addr}): {exc}"
                    )
                    return
                delay = self.retry_delays[attempt - 1]
                self.log_warning(
                    f"Email send attempt {attempt}/{attempts} failed; retrying in {delay}s: {exc}"
                )
                await asyncio.sleep(delay)

    def _send_sync(self, *, to_addr: str, subject: str, html_body: str) -> None:
        self.smtp_sender(
            from_addr=self.from_email or "",
            password=self.email_app_password or "",
            to_addr=to_addr,
            subject=subject,
            html_body=html_body,
        )
