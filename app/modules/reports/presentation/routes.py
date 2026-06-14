# app/modules/reports/presentation/routes.py
from typing import Optional

from fastapi import APIRouter, Body, Depends, Path, Query, Response, status

from app.core.auth import get_current_user
from app.core.model import StandardResponse, create_success_response
from app.core.permissions import Permission, require_permissions
from app.modules.reports.data.model import ReportStatus
from app.modules.reports.helpers import DOCX_MIME
from app.modules.reports.presentation.deps import (
    get_uc_delete_report,
    get_uc_download_report,
    get_uc_finalize_report,
    get_uc_generate_reports,
    get_uc_get_report,
    get_uc_list_eligible,
    get_uc_list_my_reports,
    get_uc_list_reports,
    get_uc_recheck_link_metrics,
    get_uc_report_statistics,
)
from app.modules.reports.presentation.schema import (
    EligibleGroupResponse,
    GenerateReportsRequest,
    RecheckResponse,
    ReportResponse,
    ReportStatisticsResponse,
)
from app.modules.users.data.model import User

router = APIRouter(tags=["reports"])


def _docx_response(filename: str, data: bytes) -> Response:
    return Response(
        content=data,
        media_type=DOCX_MIME,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/reports/eligible", response_model=StandardResponse[list[EligibleGroupResponse]])
async def list_eligible(
    period: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    current_user: User = Depends(require_permissions(Permission.REPORTS_MANAGE)),
    uc=Depends(get_uc_list_eligible),
):
    groups = await uc.execute(period=period)
    return create_success_response([EligibleGroupResponse.from_group(g) for g in groups])


@router.post(
    "/reports/generate",
    response_model=StandardResponse[list[ReportResponse]],
    status_code=status.HTTP_201_CREATED,
)
async def generate_reports(
    body: GenerateReportsRequest = Body(...),
    current_user: User = Depends(require_permissions(Permission.REPORTS_MANAGE)),
    uc=Depends(get_uc_generate_reports),
):
    created = await uc.execute(
        period=body.period,
        article_award_price=body.article_award_price,
        tax_rate=body.tax_rate,
        creator_user_id=body.creator_user_id,
        created_by=current_user.id,
    )
    return create_success_response(
        [ReportResponse.from_model(r) for r in created],
        f"Generated {len(created)} report(s)",
    )


@router.get("/reports", response_model=StandardResponse[list[ReportResponse]])
async def list_reports(
    period: Optional[str] = Query(default=None),
    status_: Optional[ReportStatus] = Query(default=None, alias="status"),
    creator_user_id: Optional[str] = Query(default=None),
    current_user: User = Depends(require_permissions(Permission.REPORTS_READ)),
    uc=Depends(get_uc_list_reports),
):
    reports = await uc.execute(
        period=period, status=status_, creator_user_id=creator_user_id
    )
    return create_success_response([ReportResponse.from_model(r) for r in reports])


@router.get(
    "/reports/statistics",
    response_model=StandardResponse[ReportStatisticsResponse],
)
async def report_statistics(
    period: Optional[str] = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    current_user: User = Depends(require_permissions(Permission.REPORTS_READ)),
    uc=Depends(get_uc_report_statistics),
):
    stats = await uc.execute(period=period)
    return create_success_response(ReportStatisticsResponse.from_stats(stats))


@router.get("/reports/{report_id}", response_model=StandardResponse[ReportResponse])
async def get_report(
    report_id: str = Path(...),
    current_user: User = Depends(require_permissions(Permission.REPORTS_READ)),
    uc=Depends(get_uc_get_report),
):
    report = await uc.execute(report_id=report_id)
    return create_success_response(ReportResponse.from_model(report))


@router.post("/reports/{report_id}/finalize", response_model=StandardResponse[ReportResponse])
async def finalize_report(
    report_id: str = Path(...),
    current_user: User = Depends(require_permissions(Permission.REPORTS_MANAGE)),
    uc=Depends(get_uc_finalize_report),
):
    report = await uc.execute(report_id=report_id, finalized_by=current_user.id)
    return create_success_response(ReportResponse.from_model(report), "Report finalized")


@router.delete("/reports/{report_id}", response_model=StandardResponse)
async def delete_report(
    report_id: str = Path(...),
    current_user: User = Depends(require_permissions(Permission.REPORTS_MANAGE)),
    uc=Depends(get_uc_delete_report),
):
    await uc.execute(report_id=report_id)
    return create_success_response(None, "Report deleted")


@router.get("/reports/{report_id}/download")
async def download_report(
    report_id: str = Path(...),
    current_user: User = Depends(require_permissions(Permission.REPORTS_MANAGE)),
    uc=Depends(get_uc_download_report),
):
    filename, data = await uc.execute(report_id=report_id, require_creator_id=None)
    return _docx_response(filename, data)


@router.get("/me/reports", response_model=StandardResponse[list[ReportResponse]])
async def list_my_reports(
    current_user: User = Depends(get_current_user),
    uc=Depends(get_uc_list_my_reports),
):
    reports = await uc.execute(creator_user_id=current_user.id)
    return create_success_response([ReportResponse.from_model(r) for r in reports])


@router.get("/me/reports/{report_id}/download")
async def download_my_report(
    report_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    uc=Depends(get_uc_download_report),
):
    filename, data = await uc.execute(
        report_id=report_id, require_creator_id=current_user.id
    )
    return _docx_response(filename, data)


@router.post(
    "/reports/articles/{article_id}/recheck",
    response_model=StandardResponse[RecheckResponse],
)
async def recheck_article_metrics(
    article_id: str = Path(...),
    current_user: User = Depends(require_permissions(Permission.REPORTS_READ)),
    uc=Depends(get_uc_recheck_link_metrics),
):
    result = await uc.execute(article_id=article_id)
    return create_success_response(RecheckResponse.from_result(result))
