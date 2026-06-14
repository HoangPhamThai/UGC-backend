# app/modules/reports/domain/usecases/generate_reports.py
from dataclasses import dataclass
from typing import Callable, Optional

from app.core.logging_mixin import LoggerMixin
from app.modules.profiles.domain.repo import CreatorProfileRepo
from app.modules.reports.data.model import AcceptanceReport, LineItem
from app.modules.reports.domain.errors import ReportValidationError
from app.modules.reports.domain.repo import AcceptanceReportRepo, ReportSourceRepo
from app.modules.reports.helpers import DOCX_MIME, period_bounds, report_to_render_inputs
from app.modules.reports.numbers import number_to_vietnamese
from app.modules.reports.storage import ObjectStorage
from app.modules.workspaces.domain.repo import ArticleRepo

_PROFILE_KEYS = (
    "full_name", "date_of_birth", "social_id", "social_id_date_of_issue",
    "social_id_place_of_issue", "primary_address", "current_address",
    "tax_number", "bank_account_number", "bank_name", "bank_branch",
)


@dataclass(frozen=True)
class GenerateReportsUseCase(LoggerMixin):
    report_repo: AcceptanceReportRepo
    source_repo: ReportSourceRepo
    profile_repo: CreatorProfileRepo
    article_repo: ArticleRepo
    storage: ObjectStorage
    render: Callable[..., bytes]  # render_acceptance_report(*, scalars, line_items)

    async def execute(
        self,
        *,
        period: str,
        article_award_price: int,
        tax_amount: int,
        created_by: str,
        creator_user_id: Optional[str] = None,
    ) -> list[AcceptanceReport]:
        if article_award_price < 0 or tax_amount < 0:
            raise ReportValidationError("price and tax must be non-negative")

        start, end = period_bounds(period)
        eligible = await self.source_repo.list_eligible(start=start, end=end)

        by_creator: dict[str, list] = {}
        for a in eligible:
            if creator_user_id is not None and a.owner_user_id != creator_user_id:
                continue
            by_creator.setdefault(a.owner_user_id, []).append(a)

        created: list[AcceptanceReport] = []
        for owner_id, arts in by_creator.items():
            if await self.report_repo.get_by_creator_period(owner_id, period):
                continue

            profile = await self.profile_repo.get_by_user_id(owner_id)
            snapshot = (
                {k: getattr(profile, k) for k in _PROFILE_KEYS} if profile else {}
            )
            ordered = sorted(arts, key=lambda x: (x.on_air_date, x.article_id))
            line_items = [
                LineItem(
                    article_id=a.article_id, seq=i + 1, platform=a.platform,
                    on_air_date=a.on_air_date.isoformat(), link=a.link, views=a.views,
                )
                for i, a in enumerate(ordered)
            ]
            count = len(line_items)
            total_award = article_award_price * count
            final_award = total_award - tax_amount

            report = AcceptanceReport(
                period=period,
                creator_user_id=owner_id,
                created_by=created_by,
                creator_snapshot=snapshot,
                line_items=line_items,
                article_award_price=article_award_price,
                total_approved_articles=count,
                total_award=total_award,
                tax=tax_amount,
                final_award=final_award,
                final_award_verbal=number_to_vietnamese(max(final_award, 0)),
                object_key="placeholder",
            )
            report.object_key = f"reports/{period}/{report.id}.docx"

            scalars, items = report_to_render_inputs(report)
            docx_bytes = self.render(scalars=scalars, line_items=items)
            await self.storage.put(report.object_key, docx_bytes, content_type=DOCX_MIME)
            await self.report_repo.create(report)
            for a in ordered:
                await self.article_repo.set_report_id(a.article_id, report.id)

            created.append(report)
            self.log_info(f"Report drafted: id={report.id} creator={owner_id} n={count}")
        return created
