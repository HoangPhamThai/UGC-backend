# app/modules/reports/presentation/deps.py
from functools import lru_cache

from app.modules.profiles.presentation.deps import get_profile_repo
from app.modules.reports.data.repo import (
    AcceptanceReportDataRepository,
    ReportSourceDataRepository,
)
from app.modules.reports.domain.repo import AcceptanceReportRepo, ReportSourceRepo
from app.modules.reports.domain.usecases.delete_report import DeleteReportUseCase
from app.modules.reports.domain.usecases.download_report import DownloadReportUseCase
from app.modules.reports.domain.usecases.finalize_report import FinalizeReportUseCase
from app.modules.reports.domain.usecases.generate_reports import GenerateReportsUseCase
from app.modules.reports.domain.usecases.list_eligible import ListEligibleUseCase
from app.modules.reports.domain.usecases.query_reports import (
    GetReportUseCase,
    ListMyReportsUseCase,
    ListReportsUseCase,
)
from app.modules.reports.domain.usecases.report_statistics import ReportStatisticsUseCase
from app.modules.reports.rendering import render_acceptance_report
from app.modules.reports.storage import ObjectStorage, get_object_storage
from app.modules.workspaces.presentation.deps import get_article_repo


@lru_cache(maxsize=1)
def get_report_repo() -> AcceptanceReportRepo:
    return AcceptanceReportDataRepository()


@lru_cache(maxsize=1)
def get_report_source_repo() -> ReportSourceRepo:
    return ReportSourceDataRepository()


def _storage() -> ObjectStorage:
    return get_object_storage()


def get_uc_list_eligible() -> ListEligibleUseCase:
    return ListEligibleUseCase(
        source_repo=get_report_source_repo(), profile_repo=get_profile_repo()
    )


def get_uc_generate_reports() -> GenerateReportsUseCase:
    return GenerateReportsUseCase(
        report_repo=get_report_repo(),
        source_repo=get_report_source_repo(),
        profile_repo=get_profile_repo(),
        article_repo=get_article_repo(),
        storage=_storage(),
        render=render_acceptance_report,
    )


def get_uc_list_reports() -> ListReportsUseCase:
    return ListReportsUseCase(report_repo=get_report_repo())


def get_uc_list_my_reports() -> ListMyReportsUseCase:
    return ListMyReportsUseCase(report_repo=get_report_repo())


def get_uc_get_report() -> GetReportUseCase:
    return GetReportUseCase(report_repo=get_report_repo())


def get_uc_finalize_report() -> FinalizeReportUseCase:
    return FinalizeReportUseCase(report_repo=get_report_repo())


def get_uc_delete_report() -> DeleteReportUseCase:
    return DeleteReportUseCase(
        report_repo=get_report_repo(), article_repo=get_article_repo(), storage=_storage()
    )


def get_uc_download_report() -> DownloadReportUseCase:
    return DownloadReportUseCase(report_repo=get_report_repo(), storage=_storage())


def get_uc_report_statistics() -> ReportStatisticsUseCase:
    return ReportStatisticsUseCase(report_repo=get_report_repo())
