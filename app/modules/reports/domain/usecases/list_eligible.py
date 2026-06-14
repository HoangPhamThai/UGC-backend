# app/modules/reports/domain/usecases/list_eligible.py
from dataclasses import dataclass, field

from app.core.logging_mixin import LoggerMixin
from app.modules.profiles.data.model import REQUIRED_PROFILE_FIELDS
from app.modules.profiles.domain.repo import CreatorProfileRepo
from app.modules.reports.domain.repo import EligibleArticle, ReportSourceRepo
from app.modules.reports.helpers import period_bounds


@dataclass
class EligibleCreatorGroup:
    creator_user_id: str
    email: str
    profile_complete: bool
    article_count: int
    articles: list[EligibleArticle] = field(default_factory=list)


@dataclass(frozen=True)
class ListEligibleUseCase(LoggerMixin):
    source_repo: ReportSourceRepo
    profile_repo: CreatorProfileRepo

    async def execute(self, *, period: str) -> list[EligibleCreatorGroup]:
        start, end = period_bounds(period)
        eligible = await self.source_repo.list_eligible(start=start, end=end)

        by_creator: dict[str, list[EligibleArticle]] = {}
        for a in eligible:
            by_creator.setdefault(a.owner_user_id, []).append(a)

        emails = await self.source_repo.creator_emails(set(by_creator.keys()))

        groups: list[EligibleCreatorGroup] = []
        for creator_id, arts in by_creator.items():
            profile = await self.profile_repo.get_by_user_id(creator_id)
            complete = bool(profile) and all(
                str(getattr(profile, f)).strip() for f in REQUIRED_PROFILE_FIELDS
            )
            groups.append(
                EligibleCreatorGroup(
                    creator_user_id=creator_id,
                    email=emails.get(creator_id, ""),
                    profile_complete=complete,
                    article_count=len(arts),
                    articles=sorted(arts, key=lambda x: (x.on_air_date, x.article_id)),
                )
            )
        groups.sort(key=lambda g: g.email or g.creator_user_id)
        return groups
