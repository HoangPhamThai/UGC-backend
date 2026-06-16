import pytest

from app.modules.reports.domain.errors import ReportValidationError
from app.modules.reports.domain.usecases.rules import GetRulesUseCase, SaveRulesUseCase


class FakeRulesRepo:
    def __init__(self, doc=None):
        self.doc = doc

    async def get_active(self):
        return self.doc

    async def save_active(self, *, source_markdown, ir, warnings, status, updated_by):
        self.doc = {"source_markdown": source_markdown, "ir": ir, "warnings": warnings,
                    "status": status, "updated_by": updated_by}
        return self.doc


async def test_get_returns_empty_when_no_doc():
    out = await GetRulesUseCase(rules_repo=FakeRulesRepo()).execute()
    assert out["status"] == "empty" and out["ir"] == {"version": 1, "rules": []}


async def test_save_valid_ir():
    repo = FakeRulesRepo()
    ir = {"version": 1, "rules": []}
    out = await SaveRulesUseCase(rules_repo=repo).execute(
        source_markdown="x", ir=ir, updated_by="u1")
    assert out["status"] == "ok"


async def test_save_invalid_ir_raises():
    repo = FakeRulesRepo()
    bad_ir = {"version": 1, "rules": [{"id": "a", "target": "nope", "scope": "scalar",
              "type": "conditional_formula", "inputs": [], "cases": [], "default": "keep"}]}
    with pytest.raises(ReportValidationError):
        await SaveRulesUseCase(rules_repo=repo).execute(source_markdown="x", ir=bad_ir, updated_by="u1")
