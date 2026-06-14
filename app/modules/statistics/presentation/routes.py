# app/modules/statistics/presentation/routes.py
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.model import StandardResponse, create_success_response
from app.core.permissions import Permission, require_permissions
from app.core.time import business_day_end_utc, business_day_start_utc
from app.modules.users.data.model import User
from app.modules.workspaces.data.model import Product
from app.modules.statistics.presentation.deps import (
    get_uc_get_qc_breakdown,
    get_uc_get_summary,
    get_uc_list_all_articles,
    get_uc_list_creator_articles,
    get_uc_list_creators,
)
from app.modules.statistics.presentation.schema import (
    ArticleListResponse,
    ArticleRowResponse,
    CreatorArticleItemResponse,
    CreatorArticlesResponse,
    CreatorListItemResponse,
    CreatorListResponse,
    QcBreakdownResponse,
    QcBreakdownRowResponse,
    SummaryResponse,
)

router = APIRouter(prefix="/statistics", tags=["statistics"])


def _window(from_: Optional[date], to: Optional[date]):
    """Validate and convert the optional [from, to] calendar window to inclusive
    UTC datetime bounds. Raises 422 if from > to."""
    if from_ and to and from_ > to:
        raise HTTPException(status_code=422, detail="from: must be on or before 'to'")
    from_dt = business_day_start_utc(from_) if from_ else None
    to_dt = business_day_end_utc(to) if to else None
    return from_dt, to_dt


@router.get("/summary", response_model=StandardResponse[SummaryResponse])
async def get_summary(
    from_: Optional[date] = Query(default=None, alias="from"),
    to: Optional[date] = Query(default=None),
    product: Optional[Product] = Query(default=None),
    current_user: User = Depends(require_permissions(Permission.STATS_READ)),
    uc=Depends(get_uc_get_summary),
):
    from_dt, to_dt = _window(from_, to)
    counts = await uc.execute(from_dt=from_dt, to_dt=to_dt, product=product)
    return create_success_response(SummaryResponse.from_counts(counts))


@router.get("/qc-breakdown", response_model=StandardResponse[QcBreakdownResponse])
async def get_qc_breakdown(
    from_: Optional[date] = Query(default=None, alias="from"),
    to: Optional[date] = Query(default=None),
    product: Optional[Product] = Query(default=None),
    current_user: User = Depends(require_permissions(Permission.STATS_READ)),
    uc=Depends(get_uc_get_qc_breakdown),
):
    from_dt, to_dt = _window(from_, to)
    result = await uc.execute(from_dt=from_dt, to_dt=to_dt, product=product)
    data = QcBreakdownResponse(
        items=[QcBreakdownRowResponse.from_row(r) for r in result.items]
    )
    return create_success_response(data)


@router.get("/articles", response_model=StandardResponse[ArticleListResponse])
async def list_articles(
    from_: Optional[date] = Query(default=None, alias="from"),
    to: Optional[date] = Query(default=None),
    product: Optional[Product] = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_permissions(Permission.STATS_READ)),
    uc=Depends(get_uc_list_all_articles),
):
    from_dt, to_dt = _window(from_, to)
    result = await uc.execute(
        from_dt=from_dt, to_dt=to_dt, product=product, page=page, limit=limit
    )
    data = ArticleListResponse(
        items=[ArticleRowResponse.from_entry(e) for e in result.items],
        total=result.total,
    )
    return create_success_response(data)


@router.get("/creators", response_model=StandardResponse[CreatorListResponse])
async def list_creators(
    q: Optional[str] = Query(default=None),
    from_: Optional[date] = Query(default=None, alias="from"),
    to: Optional[date] = Query(default=None),
    product: Optional[Product] = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_permissions(Permission.STATS_READ)),
    uc=Depends(get_uc_list_creators),
):
    from_dt, to_dt = _window(from_, to)
    result = await uc.execute(
        q=q, from_dt=from_dt, to_dt=to_dt, product=product, page=page, limit=limit
    )
    data = CreatorListResponse(
        items=[CreatorListItemResponse.from_entry(e) for e in result.items],
        total=result.total,
    )
    return create_success_response(data)


@router.get(
    "/creators/{creator_id}/articles",
    response_model=StandardResponse[CreatorArticlesResponse],
)
async def list_creator_articles(
    creator_id: str,
    from_: Optional[date] = Query(default=None, alias="from"),
    to: Optional[date] = Query(default=None),
    product: Optional[Product] = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_permissions(Permission.STATS_READ)),
    uc=Depends(get_uc_list_creator_articles),
):
    from_dt, to_dt = _window(from_, to)
    result = await uc.execute(
        creator_id=creator_id,
        from_dt=from_dt,
        to_dt=to_dt,
        product=product,
        page=page,
        limit=limit,
    )
    data = CreatorArticlesResponse(
        items=[CreatorArticleItemResponse.from_entry(e) for e in result.items],
        total=result.total,
    )
    return create_success_response(data)
