# app/modules/workspaces/domain/usecases/_review_guard.py
from app.modules.users.data.model import User, UserRole
from app.modules.workspaces.data.model import Article
from app.modules.workspaces.domain.errors import (
    ArticleNotFoundError,
    ClaimConflictError,
    QcMisconfiguredError,
)


def ensure_qc_scope(article: Article, caller: User) -> None:
    """Caller may see/act on this article's product. Superuser bypasses.
    Hides existence (404) when out of scope — same as the existing use-cases."""
    if caller.role == UserRole.SUPERUSER:
        return
    if not caller.qc_products:
        raise QcMisconfiguredError()
    if article.product not in caller.qc_products:
        raise ArticleNotFoundError()


def ensure_claimed_by_caller(article: Article, caller: User) -> None:
    """Caller must hold the claim to perform review actions. Superuser bypasses."""
    if caller.role == UserRole.SUPERUSER:
        return
    if article.claimed_by != caller.id:
        raise ClaimConflictError("You must claim this article before acting on it")
