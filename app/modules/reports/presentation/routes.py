# app/modules/reports/presentation/routes.py
from typing import Optional

from fastapi import APIRouter, Body, Depends, File, HTTPException, Path, Query, Response, UploadFile, status

from app.core.auth import get_current_user
from app.core.model import StandardResponse, create_success_response
from app.core.permissions import Permission, require_permissions
from app.modules.reports.data.model import ReportStatus
from app.modules.reports.helpers import DOCX_MIME
from app.modules.reports.presentation.deps import (
    get_uc_approve_report,
    get_uc_cancel_report,
    get_uc_delete_report,
    get_uc_download_report,
    get_uc_preview_report,
    get_uc_download_template,
    get_uc_finalize_report,
    get_uc_generate_reports,
    get_uc_get_my_report,
    get_uc_get_report,
    get_uc_get_rules,
    get_uc_get_template,
    get_uc_list_eligible,
    get_uc_list_my_reports,
    get_uc_list_reports,
    get_uc_recheck_link_metrics,
    get_uc_regenerate_report,
    get_uc_report_statistics,
    get_uc_save_rules,
    get_uc_submit_report,
    get_uc_upload_article_image,
    get_uc_upload_template,
    get_storage,
)
from app.modules.reports.presentation.schema import (
    EligibleGroupResponse,
    FieldRegistryEntry,
    GenerateReportsRequest,
    LineItemResponse,
    RecheckResponse,
    ReportDetailResponse,
    ReportResponse,
    ReportStatisticsResponse,
    RulesResponse,
    SaveRulesRequest,
    TemplateMetaResponse,
    _content_type_from_key,
)
from app.modules.reports.rules.registry import FIELD_REGISTRY
from app.modules.users.data.model import User

router = APIRouter(tags=["reports"])


def _docx_response(filename: str, data: bytes) -> Response:
    return Response(
        content=data,
        media_type=DOCX_MIME,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _docx_inline_response(filename: str, data: bytes) -> Response:
    return Response(
        content=data,
        media_type=DOCX_MIME,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
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
    rows = await uc.execute(
        period=period, status=status_, creator_user_id=creator_user_id
    )
    return create_success_response(
        [ReportResponse.from_model(rw.report, rw.email) for rw in rows]
    )


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


@router.get("/reports/template", response_model=StandardResponse[TemplateMetaResponse])
async def get_template(
    current_user: User = Depends(require_permissions(Permission.REPORTS_READ)),
    uc=Depends(get_uc_get_template),
):
    view = await uc.execute()
    return create_success_response(TemplateMetaResponse.from_view(view))


@router.get("/reports/template/download")
async def download_template(
    current_user: User = Depends(require_permissions(Permission.REPORTS_READ)),
    uc=Depends(get_uc_download_template),
):
    filename, data = await uc.execute()
    return _docx_response(filename, data)


@router.post("/reports/template", response_model=StandardResponse[TemplateMetaResponse])
async def upload_template(
    file: UploadFile = File(...),
    current_user: User = Depends(require_permissions(Permission.REPORTS_MANAGE)),
    uc=Depends(get_uc_upload_template),
):
    data = await file.read()
    view = await uc.execute(
        data=data,
        filename=file.filename or "template.docx",
        uploaded_by=getattr(current_user, "id", "unknown"),
    )
    return create_success_response(TemplateMetaResponse.from_view(view), "Template updated")


@router.post("/reports/{report_id}/approve", response_model=StandardResponse[ReportResponse])
async def approve_report_route(
    report_id: str = Path(...),
    current_user: User = Depends(require_permissions(Permission.REPORTS_MANAGE)),
    uc=Depends(get_uc_approve_report),
):
    report = await uc.execute(report_id=report_id, approved_by=current_user.id)
    return create_success_response(ReportResponse.from_model(report), "Report approved")


@router.get("/reports/{report_id}/images/{article_id}")
async def get_report_image(
    report_id: str = Path(...),
    article_id: str = Path(...),
    current_user: User = Depends(require_permissions(Permission.REPORTS_READ)),
    uc=Depends(get_uc_get_report),
    storage=Depends(get_storage),
):
    report = await uc.execute(report_id=report_id)
    item = next((li for li in report.line_items if li.article_id == article_id), None)
    if item is None or not item.article_image:
        raise HTTPException(status_code=404, detail="Image not found")
    data = await storage.get(item.article_image)
    return Response(content=data, media_type=_content_type_from_key(item.article_image))


@router.get("/report-rules", response_model=StandardResponse[RulesResponse])
async def get_report_rules(
    current_user: User = Depends(require_permissions(Permission.REPORTS_MANAGE)),
    uc=Depends(get_uc_get_rules),
):
    data = await uc.execute()
    return create_success_response(RulesResponse(**data))


@router.post("/report-rules", response_model=StandardResponse[RulesResponse])
async def save_report_rules(
    body: SaveRulesRequest = Body(...),
    current_user: User = Depends(require_permissions(Permission.REPORTS_MANAGE)),
    uc=Depends(get_uc_save_rules),
):
    doc = await uc.execute(source_markdown=body.source_markdown, ir=body.ir, updated_by=current_user.id)
    return create_success_response(RulesResponse(
        source_markdown=doc["source_markdown"], ir=doc["ir"],
        warnings=doc.get("warnings", []), status=doc["status"]))


@router.get("/report-rules/registry", response_model=StandardResponse[list[FieldRegistryEntry]])
async def get_report_rules_registry(
    current_user: User = Depends(require_permissions(Permission.REPORTS_READ)),
):
    entries = [FieldRegistryEntry(
        key=f.key, scope=f.scope, type=f.type, writable=f.writable,
        description=f.description, enum_values=list(f.enum_values) if f.enum_values else None,
    ) for f in FIELD_REGISTRY.values()]
    return create_success_response(entries)


@router.get("/reports/{report_id}", response_model=StandardResponse[ReportDetailResponse])
async def get_report(
    report_id: str = Path(...),
    current_user: User = Depends(require_permissions(Permission.REPORTS_READ)),
    uc=Depends(get_uc_get_report),
):
    # Returns the detail shape (incl. line_items) so admins can view article
    # images / approve without hitting the creator-scoped /me/reports/{id}.
    report = await uc.execute(report_id=report_id)
    return create_success_response(ReportDetailResponse.from_detail_model(report))


@router.post("/reports/{report_id}/finalize", response_model=StandardResponse[ReportResponse])
async def finalize_report(
    report_id: str = Path(...),
    current_user: User = Depends(require_permissions(Permission.REPORTS_MANAGE)),
    uc=Depends(get_uc_finalize_report),
):
    report = await uc.execute(report_id=report_id, finalized_by=current_user.id)
    return create_success_response(ReportResponse.from_model(report), "Report finalized")


@router.post("/reports/{report_id}/regenerate", response_model=StandardResponse[ReportResponse])
async def regenerate_report(
    report_id: str = Path(...),
    current_user: User = Depends(require_permissions(Permission.REPORTS_MANAGE)),
    uc=Depends(get_uc_regenerate_report),
):
    report = await uc.execute(report_id=report_id, regenerated_by=current_user.id)
    return create_success_response(ReportResponse.from_model(report), "Report regenerated")


@router.post("/reports/{report_id}/cancel", response_model=StandardResponse[ReportResponse])
async def cancel_report(
    report_id: str = Path(...),
    current_user: User = Depends(require_permissions(Permission.REPORTS_MANAGE)),
    uc=Depends(get_uc_cancel_report),
):
    report = await uc.execute(report_id=report_id, cancelled_by=current_user.id)
    return create_success_response(ReportResponse.from_model(report), "Report cancelled")


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


@router.get("/reports/{report_id}/preview")
async def preview_report(
    report_id: str = Path(...),
    current_user: User = Depends(require_permissions(Permission.REPORTS_MANAGE)),
    uc=Depends(get_uc_preview_report),
):
    filename, data = await uc.execute(report_id=report_id, require_creator_id=None)
    return _docx_inline_response(filename, data)


@router.get("/me/reports", response_model=StandardResponse[list[ReportResponse]])
async def list_my_reports(
    current_user: User = Depends(get_current_user),
    uc=Depends(get_uc_list_my_reports),
):
    reports = await uc.execute(creator_user_id=current_user.id)
    return create_success_response([ReportResponse.from_model(r) for r in reports])


@router.get("/me/reports/{report_id}", response_model=StandardResponse[ReportDetailResponse])
async def get_my_report(
    report_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    uc=Depends(get_uc_get_my_report),
):
    report = await uc.execute(report_id=report_id, creator_user_id=current_user.id)
    return create_success_response(ReportDetailResponse.from_detail_model(report))


@router.post(
    "/me/reports/{report_id}/images/{article_id}",
    response_model=StandardResponse[ReportDetailResponse],
)
async def upload_my_report_image(
    report_id: str = Path(...),
    article_id: str = Path(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    uc=Depends(get_uc_upload_article_image),
):
    data = await file.read()
    report = await uc.execute(
        report_id=report_id, article_id=article_id,
        image_bytes=data, content_type=file.content_type or "image/jpeg",
        uploader_user_id=current_user.id,
    )
    return create_success_response(ReportDetailResponse.from_detail_model(report))


@router.post("/me/reports/{report_id}/submit", response_model=StandardResponse[ReportResponse])
async def submit_my_report(
    report_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    uc=Depends(get_uc_submit_report),
):
    report = await uc.execute(report_id=report_id, submitter_user_id=current_user.id)
    return create_success_response(ReportResponse.from_model(report))


@router.get("/me/reports/{report_id}/images/{article_id}")
async def get_my_report_image(
    report_id: str = Path(...),
    article_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    uc=Depends(get_uc_get_my_report),
    storage=Depends(get_storage),
):
    report = await uc.execute(report_id=report_id, creator_user_id=current_user.id)
    item = next((li for li in report.line_items if li.article_id == article_id), None)
    if item is None or not item.article_image:
        raise HTTPException(status_code=404, detail="Image not found")
    data = await storage.get(item.article_image)
    return Response(content=data, media_type=_content_type_from_key(item.article_image))


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


@router.get("/me/reports/{report_id}/preview")
async def preview_my_report(
    report_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    uc=Depends(get_uc_preview_report),
):
    filename, data = await uc.execute(
        report_id=report_id, require_creator_id=current_user.id
    )
    return _docx_inline_response(filename, data)


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
