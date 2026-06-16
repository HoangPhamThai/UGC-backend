from fastapi import Depends

from app.modules.report_rule_jobs.data.repo import RuleJobDataRepository
from app.modules.report_rule_jobs.domain.repo import RuleJobRepo
from app.modules.report_rule_jobs.domain.usecases.create_job import CreateRuleJobUseCase
from app.modules.report_rule_jobs.domain.usecases.get_job import GetRuleJobUseCase
from app.modules.report_rule_jobs.domain.usecases.update_job import (
    FinalizeRuleJobUseCase, SetResultUseCase,
)


def get_rule_job_repo() -> RuleJobRepo:
    return RuleJobDataRepository()


def get_uc_create_rule_job(repo: RuleJobRepo = Depends(get_rule_job_repo)) -> CreateRuleJobUseCase:
    return CreateRuleJobUseCase(repo=repo)


def get_uc_get_rule_job(repo: RuleJobRepo = Depends(get_rule_job_repo)) -> GetRuleJobUseCase:
    return GetRuleJobUseCase(repo=repo)


def get_uc_set_rule_result(repo: RuleJobRepo = Depends(get_rule_job_repo)) -> SetResultUseCase:
    return SetResultUseCase(repo=repo)


def get_uc_finalize_rule_job(repo: RuleJobRepo = Depends(get_rule_job_repo)) -> FinalizeRuleJobUseCase:
    return FinalizeRuleJobUseCase(repo=repo)
