import pytest

from app.modules.workspaces.data.model import ArticleEventType, ArticleStatus
from app.modules.workspaces.domain.errors import (
    ArticleNotFoundError,
    ClaimConflictError,
)
from app.modules.workspaces.domain.usecases.claim_article import ClaimArticleUseCase
from tests.conftest import (
    FakeArticleEventRepo,
    FakeArticleRepo,
    make_article,
)
from app.modules.users.data.model import Product


async def test_claim_sets_owner_and_logs_event(qc):
    art = make_article(status=ArticleStatus.SUBMITTED, claimed_by=None)
    repo = FakeArticleRepo([art])
    events = FakeArticleEventRepo()
    uc = ClaimArticleUseCase(article_repo=repo, event_repo=events)

    result = await uc.execute(workspace_id="ws_1", article_id="art_1", caller=qc)

    assert result.claimed_by == qc.id
    assert result.claimed_at is not None
    assert events.events[-1].type == ArticleEventType.CLAIMED


async def test_claim_already_claimed_raises(qc):
    art = make_article(claimed_by="u_other")
    uc = ClaimArticleUseCase(
        article_repo=FakeArticleRepo([art]), event_repo=FakeArticleEventRepo()
    )
    with pytest.raises(ClaimConflictError):
        await uc.execute(workspace_id="ws_1", article_id="art_1", caller=qc)


async def test_claim_out_of_product_scope_is_404(qc):
    art = make_article(product=Product.MMF, claimed_by=None)  # qc only has CL
    uc = ClaimArticleUseCase(
        article_repo=FakeArticleRepo([art]), event_repo=FakeArticleEventRepo()
    )
    with pytest.raises(ArticleNotFoundError):
        await uc.execute(workspace_id="ws_1", article_id="art_1", caller=qc)


async def test_claim_non_awaiting_article_raises_state_conflict(qc):
    from app.modules.workspaces.data.model import ArticleStatus
    from app.modules.workspaces.domain.errors import ArticleStateConflictError
    art = make_article(status=ArticleStatus.APPROVED, claimed_by=None)
    uc = ClaimArticleUseCase(
        article_repo=FakeArticleRepo([art]), event_repo=FakeArticleEventRepo()
    )
    with pytest.raises(ArticleStateConflictError):
        await uc.execute(workspace_id="ws_1", article_id="art_1", caller=qc)
