import asyncio
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import pytest

from app.modules.users.data.model import User, UserRole
from app.modules.users.domain.repo import UserRepo
from app.modules.workspaces.data.model import Article, ArticleEventType, ArticleStatus, Product

from app.modules.email.service import EmailService


class FakeUserRepo(UserRepo):
    def __init__(self, users: dict[str, User]) -> None:
        self._users = users

    async def create(self, user: User) -> User:
        self._users[user.id] = user
        return user

    async def get_by_id(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)

    async def get_by_email(self, email: str) -> Optional[User]:
        return next((u for u in self._users.values() if u.email == email), None)

    async def update(self, user: User) -> User:
        self._users[user.id] = user
        return user

    async def exists_with_role(self, role: UserRole) -> bool:
        return any(u.role == role for u in self._users.values())

    async def list_by_role(self, role, *, skip=0, limit=50):
        return [u for u in self._users.values() if u.role == role][skip : skip + limit]

    async def count_by_role(self, role) -> int:
        return sum(1 for u in self._users.values() if u.role == role)


@dataclass
class RecordingSmtpSender:
    calls: list[tuple[str, str, str, str, str]] = field(default_factory=list)
    fail_times: int = 0
    fail_count: int = 0

    def __call__(
        self,
        *,
        from_addr: str,
        password: str,
        to_addr: str,
        subject: str,
        html_body: str,
    ) -> None:
        self.calls.append((from_addr, password, to_addr, subject, html_body))
        if self.fail_count < self.fail_times:
            self.fail_count += 1
            raise RuntimeError("smtp down")


def _article(**kwargs) -> Article:
    defaults = dict(
        _id="art_1",
        workspace_id="ws_1",
        name="Bài test",
        product=Product.CL,
        on_air_date=date(2026, 6, 16),
        status=ArticleStatus.APPROVED,
    )
    defaults.update(kwargs)
    return Article(**defaults)


@pytest.mark.asyncio
async def test_send_article_event_success():
    sender = RecordingSmtpSender()
    svc = EmailService(
        from_email="sender@gmail.com",
        email_app_password="secret",
        frontend_base_url="https://ugc.example.com",
        user_repo=FakeUserRepo({"u_creator": User(_id="u_creator", email="c@x.com", password_hashed="x", role=UserRole.CREATOR)}),
        smtp_sender=sender,
    )
    await svc.send_article_event(
        event_type=ArticleEventType.APPROVED,
        article=_article(),
        creator_user_id="u_creator",
    )
    assert len(sender.calls) == 1
    _, password, to_addr, subject, html = sender.calls[0]
    assert password == "secret"
    assert to_addr == "c@x.com"
    assert "Bài test" in subject
    assert "Xem bài viết" in html


@pytest.mark.asyncio
async def test_send_skips_when_credentials_missing():
    sender = RecordingSmtpSender()
    svc = EmailService(
        from_email=None,
        email_app_password=None,
        frontend_base_url="https://ugc.example.com",
        user_repo=FakeUserRepo({}),
        smtp_sender=sender,
    )
    await svc.send_article_event(
        event_type=ArticleEventType.APPROVED,
        article=_article(),
        creator_user_id="u_creator",
    )
    assert sender.calls == []


@pytest.mark.asyncio
async def test_send_skips_when_creator_has_no_email():
    sender = RecordingSmtpSender()
    svc = EmailService(
        from_email="sender@gmail.com",
        email_app_password="secret",
        frontend_base_url="https://ugc.example.com",
        user_repo=FakeUserRepo({}),
        smtp_sender=sender,
    )
    await svc.send_article_event(
        event_type=ArticleEventType.APPROVED,
        article=_article(),
        creator_user_id="missing",
    )
    assert sender.calls == []


@pytest.mark.asyncio
async def test_send_retries_on_smtp_failure():
    sender = RecordingSmtpSender(fail_times=2)
    svc = EmailService(
        from_email="sender@gmail.com",
        email_app_password="secret",
        frontend_base_url="https://ugc.example.com",
        user_repo=FakeUserRepo({"u_creator": User(_id="u_creator", email="c@x.com", password_hashed="x", role=UserRole.CREATOR)}),
        smtp_sender=sender,
        retry_delays=(0.0, 0.0),
    )
    await svc.send_article_event(
        event_type=ArticleEventType.REVIEW_PUBLISHED,
        article=_article(name="Bài A"),
        creator_user_id="u_creator",
    )
    assert len(sender.calls) == 3


def test_schedule_does_not_raise_when_disabled(monkeypatch):
    monkeypatch.setattr(asyncio, "create_task", lambda coro: coro.close() or None)
    svc = EmailService(
        from_email=None,
        email_app_password=None,
        frontend_base_url=None,
        user_repo=FakeUserRepo({}),
    )
    svc.schedule(
        event_type=ArticleEventType.APPROVED,
        article=_article(),
        creator_user_id="u_creator",
    )


from app.modules.email.messages import ReportEmailEvent


@pytest.mark.asyncio
async def test_send_report_event_success():
    sender = RecordingSmtpSender()
    svc = EmailService(
        from_email="sender@gmail.com",
        email_app_password="secret",
        frontend_base_url="https://ugc.example.com",
        user_repo=FakeUserRepo({"u_creator": User(_id="u_creator", email="c@x.com", password_hashed="x", role=UserRole.CREATOR)}),
        smtp_sender=sender,
    )
    await svc.send_report_event(
        event=ReportEmailEvent.CREATED,
        period="2026-06",
        creator_user_id="u_creator",
    )
    assert len(sender.calls) == 1
    _, password, to_addr, subject, html = sender.calls[0]
    assert to_addr == "c@x.com"
    assert "2026-06" in subject
    assert "đã được tạo" in subject
    assert "https://ugc.example.com/me/reports" in html
    assert "Mở biên bản nghiệm thu" in html


@pytest.mark.asyncio
async def test_send_report_event_skips_when_disabled():
    sender = RecordingSmtpSender()
    svc = EmailService(
        from_email=None,
        email_app_password=None,
        frontend_base_url="https://ugc.example.com",
        user_repo=FakeUserRepo({}),
        smtp_sender=sender,
    )
    await svc.send_report_event(
        event=ReportEmailEvent.APPROVED, period="2026-06", creator_user_id="u_creator"
    )
    assert sender.calls == []


@pytest.mark.asyncio
async def test_send_report_event_skips_when_creator_has_no_email():
    sender = RecordingSmtpSender()
    svc = EmailService(
        from_email="sender@gmail.com",
        email_app_password="secret",
        frontend_base_url="https://ugc.example.com",
        user_repo=FakeUserRepo({}),
        smtp_sender=sender,
    )
    await svc.send_report_event(
        event=ReportEmailEvent.APPROVED, period="2026-06", creator_user_id="missing"
    )
    assert sender.calls == []


def test_schedule_report_event_does_not_raise_when_disabled(monkeypatch):
    monkeypatch.setattr(asyncio, "create_task", lambda coro: coro.close() or None)
    svc = EmailService(
        from_email=None,
        email_app_password=None,
        frontend_base_url=None,
        user_repo=FakeUserRepo({}),
    )
    svc.schedule_report_event(
        event=ReportEmailEvent.CREATED, period="2026-06", creator_user_id="u_creator"
    )
