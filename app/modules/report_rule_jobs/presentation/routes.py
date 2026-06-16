from fastapi import APIRouter, Body, Depends

from app.core.model import StandardResponse, create_success_response
from app.core.permissions import Permission, require_permissions
from app.modules.report_rule_jobs.data.model import RuleJobStatus
from app.modules.report_rule_jobs.presentation.deps import (
    get_uc_create_rule_job, get_uc_finalize_rule_job, get_uc_get_rule_job, get_uc_set_rule_result,
)
from app.modules.report_rule_jobs.presentation.schema import (
    CreateRuleJobRequest, CreateRuleJobResponse, RuleJobResponse, UpdateRuleJobRequest,
)
from app.modules.reports.rules.validator import validate_ir
from app.modules.users.data.model import User

router = APIRouter(prefix="/report-rule-jobs", tags=["report-rule-jobs"])


@router.post("", response_model=StandardResponse[CreateRuleJobResponse], status_code=201)
async def create_rule_job(
    body: CreateRuleJobRequest = Body(...),
    principal: User = Depends(require_permissions(Permission.REPORT_RULE_JOBS_WRITE)),
    uc=Depends(get_uc_create_rule_job),
):
    job = await uc.execute(owner_user_id=principal.id, source_markdown=body.source_markdown)
    return create_success_response(CreateRuleJobResponse(job_id=job.id))


@router.patch("/{job_id}", response_model=StandardResponse[RuleJobResponse])
async def update_rule_job(
    job_id: str,
    body: UpdateRuleJobRequest = Body(...),
    principal: User = Depends(require_permissions(Permission.REPORT_RULE_JOBS_WRITE)),
    set_result=Depends(get_uc_set_rule_result),
    finalize=Depends(get_uc_finalize_rule_job),
):
    if body.ir is not None:
        warnings = list(body.warnings or [])
        warnings += [{"rule_hint": "validation", "message": m} for m in validate_ir(body.ir)]
        job = await set_result.execute(job_id=job_id, ir=body.ir, warnings=warnings)
    else:
        status = RuleJobStatus(body.status or RuleJobStatus.DONE.value)
        job = await finalize.execute(job_id=job_id, status=status, error=body.error)
    return create_success_response(RuleJobResponse.from_job(job))


@router.get("/{job_id}", response_model=StandardResponse[RuleJobResponse])
async def get_rule_job(
    job_id: str,
    principal: User = Depends(require_permissions(Permission.REPORTS_MANAGE)),
    uc=Depends(get_uc_get_rule_job),
):
    job = await uc.execute(job_id=job_id, caller_id=principal.id)
    return create_success_response(RuleJobResponse.from_job(job))
