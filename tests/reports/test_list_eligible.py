import pytest

from app.modules.profiles.data.model import CreatorProfile, REQUIRED_PROFILE_FIELDS
from app.modules.reports.domain.usecases.list_eligible import ListEligibleUseCase
from tests.profiles.test_usecases import FakeProfileRepo
from tests.reports.fakes import FakeReportSourceRepo, make_eligible

ALL_REQUIRED = {f: "x" for f in REQUIRED_PROFILE_FIELDS}


@pytest.mark.asyncio
async def test_groups_eligible_by_creator_with_profile_flag():
    source = FakeReportSourceRepo(
        eligible=[
            make_eligible("art_1", "u_a"),
            make_eligible("art_2", "u_a"),
            make_eligible("art_3", "u_b"),
        ],
        emails={"u_a": "a@x.com", "u_b": "b@x.com"},
    )
    profiles = FakeProfileRepo([CreatorProfile(user_id="u_a", **ALL_REQUIRED)])
    uc = ListEligibleUseCase(source_repo=source, profile_repo=profiles)
    groups = await uc.execute(period="2026-06")

    by_id = {g.creator_user_id: g for g in groups}
    assert by_id["u_a"].article_count == 2
    assert by_id["u_a"].profile_complete is True
    assert by_id["u_a"].email == "a@x.com"
    assert by_id["u_b"].article_count == 1
    assert by_id["u_b"].profile_complete is False
