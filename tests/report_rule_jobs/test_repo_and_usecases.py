import pytest

from app.modules.report_rule_jobs.data.model import RuleJobStatus
from app.modules.report_rule_jobs.domain.errors import RuleJobNotFoundError
from app.modules.report_rule_jobs.domain.usecases.create_job import CreateRuleJobUseCase
from app.modules.report_rule_jobs.domain.usecases.get_job import GetRuleJobUseCase
from app.modules.report_rule_jobs.domain.usecases.update_job import SetResultUseCase, FinalizeRuleJobUseCase


class FakeRepo:
    def __init__(self):
        self.jobs = {}

    async def create(self, job):
        self.jobs[job.id] = job
        return job

    async def get_by_id(self, job_id):
        return self.jobs.get(job_id)

    async def set_result(self, job_id, *, ir, warnings):
        j = self.jobs[job_id]; j.ir = ir; j.warnings = warnings; j.status = RuleJobStatus.RUNNING
        return j

    async def finalize(self, job_id, status, *, error=None):
        j = self.jobs[job_id]; j.status = status; j.error = error
        return j


async def test_create_and_get():
    repo = FakeRepo()
    job = await CreateRuleJobUseCase(repo=repo).execute(owner_user_id="u1", source_markdown="r")
    got = await GetRuleJobUseCase(repo=repo).execute(job_id=job.id, caller_id="u1")
    assert got.id == job.id


async def test_get_wrong_owner_raises():
    repo = FakeRepo()
    job = await CreateRuleJobUseCase(repo=repo).execute(owner_user_id="u1", source_markdown="r")
    with pytest.raises(RuleJobNotFoundError):
        await GetRuleJobUseCase(repo=repo).execute(job_id=job.id, caller_id="other")


async def test_set_result_then_finalize():
    repo = FakeRepo()
    job = await CreateRuleJobUseCase(repo=repo).execute(owner_user_id="u1", source_markdown="r")
    await SetResultUseCase(repo=repo).execute(job_id=job.id, ir={"version": 1, "rules": []}, warnings=[])
    done = await FinalizeRuleJobUseCase(repo=repo).execute(job_id=job.id, status=RuleJobStatus.DONE)
    assert done.status == RuleJobStatus.DONE and done.ir == {"version": 1, "rules": []}
