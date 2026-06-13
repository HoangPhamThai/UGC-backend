from datetime import datetime, timezone

import pytest

from app.modules.workspaces.data.model import ArticleStatus
from app.modules.statistics.domain.repo import CreatorRef
from app.modules.statistics.domain.errors import CreatorNotFoundError
from app.modules.statistics.domain.usecases.list_creator_articles import (
    ListCreatorArticlesUseCase,
)
from tests.conftest import FakeStatisticsRepo, make_article_stat


def _dt(day):
    return datetime(2026, 6, day, 12, 0, 0, tzinfo=timezone.utc)


def _repo():
    creators = [CreatorRef(id="c_a", email="ann@x.com")]
    stats = [
        make_article_stat(aid="old", owner_user_id="c_a", created_at=_dt(1), status=ArticleStatus.NOT_SUBMITTED),
        make_article_stat(aid="mid", owner_user_id="c_a", created_at=_dt(2), status=ArticleStatus.SUBMITTED, claimed_by="qc1"),
        make_article_stat(aid="new", owner_user_id="c_a", created_at=_dt(3), status=ArticleStatus.APPROVED, reviewer_user_id="qc1"),
        # another creator's article — must never appear
        make_article_stat(aid="other", owner_user_id="c_b", created_at=_dt(3)),
    ]
    return FakeStatisticsRepo(stats=stats, creators=creators)


async def test_lists_creator_articles_newest_first_including_drafts():
    uc = ListCreatorArticlesUseCase(repo=_repo())
    res = await uc.execute(
        creator_id="c_a", from_dt=None, to_dt=None, product=None, page=1, limit=10
    )
    assert [a.id for a in res.items] == ["new", "mid", "old"]  # desc by created_at
    assert res.total == 3
    # field mapping carries through
    new = res.items[0]
    assert new.status == ArticleStatus.APPROVED
    assert new.reviewer_user_id == "qc1"


async def test_pagination():
    uc = ListCreatorArticlesUseCase(repo=_repo())
    page2 = await uc.execute(
        creator_id="c_a", from_dt=None, to_dt=None, product=None, page=2, limit=2
    )
    assert [a.id for a in page2.items] == ["old"]
    assert page2.total == 3


async def test_unknown_creator_raises():
    uc = ListCreatorArticlesUseCase(repo=_repo())
    with pytest.raises(CreatorNotFoundError):
        await uc.execute(
            creator_id="nope", from_dt=None, to_dt=None, product=None, page=1, limit=10
        )
