# app/modules/reports/domain/usecases/generate_reports.py
from dataclasses import dataclass
from typing import Callable, Optional

from app.core.logging_mixin import LoggerMixin
from app.modules.profiles.domain.repo import CreatorProfileRepo
from app.modules.reports.data.model import AcceptanceReport, LineItem
from app.modules.reports.domain.errors import ReportValidationError
from app.modules.email.messages import ReportEmailEvent
from app.modules.email.service import EmailService
from app.modules.reports.domain.repo import AcceptanceReportRepo, ReportRulesRepo, ReportSourceRepo, TemplateRepo
from app.modules.reports.helpers import DOCX_MIME, _vnd, period_bounds, report_to_render_inputs
from app.modules.reports.numbers import number_to_vietnamese
from app.modules.reports.rules.engine import apply_rules
from app.modules.reports.rules.ir import RuleIR
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
    render: Callable[..., bytes]  # render_acceptance_report(*, scalars, line_items, template_bytes)
    template_repo: TemplateRepo
    rules_repo: Optional[ReportRulesRepo] = None
    email_service: Optional[EmailService] = None

    async def execute(
        self,
        *,
        period: str,
        article_award_price: int,
        tax_rate: float,
        created_by: str,
        creator_user_id: Optional[str] = None,
    ) -> list[AcceptanceReport]:
        if article_award_price < 0:
            raise ReportValidationError("price must be non-negative")
        if not 0.0 <= tax_rate <= 1.0:
            raise ReportValidationError("tax_rate must be between 0 and 1")

        start, end = period_bounds(period)
        eligible = await self.source_repo.list_eligible(start=start, end=end)
        template_bytes = await self.template_repo.get_active_bytes()

        active_ir = None
        if self.rules_repo is not None:
            doc = await self.rules_repo.get_active()
            if doc and (doc.get("ir", {}) or {}).get("rules"):
                try:
                    active_ir = RuleIR.model_validate(doc["ir"])
                except Exception as exc:  # noqa: BLE001 — invalid active IR: skip rules defensively
                    self.log_warning(f"active rules IR invalid ({exc}); skipping rule application")

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
            count = len(ordered)
            total_award = article_award_price * count
            tax = round(total_award * tax_rate)  # scales with count; never exceeds total
            final_award = total_award - tax
            report_award_price = article_award_price

            bonus_by_article: dict[str, int] = {}
            if active_ir is not None:
                base_scalars = {
                    "tax": tax, "total_award": total_award, "final_award": final_award,
                    "article_award_price": article_award_price,
                    "total_approved_articles": count, "total_articles": count,
                }
                base_items = [
                    {"article_id": a.article_id,
                     "article_platform": a.platform or "",
                     "article_view": 0 if a.views is None else a.views,
                     "article_bonus_money": 0}
                    for a in ordered
                ]
                out_s, out_i = apply_rules(active_ir, base_scalars, base_items)
                tax = int(out_s["tax"])
                total_award = int(out_s["total_award"])
                final_award = int(out_s["final_award"])
                report_award_price = int(out_s["article_award_price"])
                bonus_by_article = {it["article_id"]: int(it["article_bonus_money"])
                                    for it in out_i if int(it["article_bonus_money"]) != 0}

            line_items = [
                LineItem(
                    article_id=a.article_id, seq=i + 1, platform=a.platform,
                    on_air_date=a.on_air_date.isoformat(), link=a.link, views=a.views,
                    article_bonus_money=(_vnd(bonus_by_article[a.article_id])
                                         if a.article_id in bonus_by_article else "  "),
                )
                for i, a in enumerate(ordered)
            ]

            report = AcceptanceReport(
                period=period,
                creator_user_id=owner_id,
                created_by=created_by,
                creator_snapshot=snapshot,
                line_items=line_items,
                article_award_price=report_award_price,
                total_approved_articles=count,
                total_award=total_award,
                tax=tax,
                final_award=final_award,
                final_award_verbal=number_to_vietnamese(max(final_award, 0)),
                object_key="placeholder",
            )
            report.object_key = f"reports/{period}/{report.id}.docx"

            scalars, items = report_to_render_inputs(report)
            docx_bytes = self.render(scalars=scalars, line_items=items, template_bytes=template_bytes)
            await self.storage.put(report.object_key, docx_bytes, content_type=DOCX_MIME)
            await self.report_repo.create(report)
            for a in ordered:
                await self.article_repo.set_report_id(a.article_id, report.id)

            created.append(report)
            if self.email_service is not None:
                try:
                    self.email_service.schedule_report_event(
                        event=ReportEmailEvent.CREATED,
                        period=period,
                        creator_user_id=owner_id,
                    )
                except Exception as exc:  # noqa: BLE001 - email is best-effort
                    self.log_warning(
                        f"Failed to schedule created email for report {report.id}: {exc}"
                    )
            self.log_info(f"Report drafted: id={report.id} creator={owner_id} n={count}")
        return created
