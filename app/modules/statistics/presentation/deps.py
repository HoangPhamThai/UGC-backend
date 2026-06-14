# app/modules/statistics/presentation/deps.py
from fastapi import Depends

from app.modules.statistics.data.repo import StatisticsDataRepository
from app.modules.statistics.domain.repo import StatisticsRepo
from app.modules.statistics.domain.usecases.get_summary import GetSummaryUseCase
from app.modules.statistics.domain.usecases.get_qc_breakdown import (
    GetQcBreakdownUseCase,
)
from app.modules.statistics.domain.usecases.list_creators import ListCreatorsUseCase
from app.modules.statistics.domain.usecases.list_creator_articles import (
    ListCreatorArticlesUseCase,
)
from app.modules.statistics.domain.usecases.list_all_articles import (
    ListAllArticlesUseCase,
)
from app.modules.statistics.domain.usecases.list_qc_articles import (
    ListQcArticlesUseCase,
)
from app.modules.statistics.domain.usecases.get_article_detail import (
    GetArticleDetailUseCase,
)


def get_statistics_repo() -> StatisticsRepo:
    return StatisticsDataRepository()


def get_uc_get_summary(
    repo: StatisticsRepo = Depends(get_statistics_repo),
) -> GetSummaryUseCase:
    return GetSummaryUseCase(repo=repo)


def get_uc_get_qc_breakdown(
    repo: StatisticsRepo = Depends(get_statistics_repo),
) -> GetQcBreakdownUseCase:
    return GetQcBreakdownUseCase(repo=repo)


def get_uc_list_creators(
    repo: StatisticsRepo = Depends(get_statistics_repo),
) -> ListCreatorsUseCase:
    return ListCreatorsUseCase(repo=repo)


def get_uc_list_creator_articles(
    repo: StatisticsRepo = Depends(get_statistics_repo),
) -> ListCreatorArticlesUseCase:
    return ListCreatorArticlesUseCase(repo=repo)


def get_uc_list_all_articles(
    repo: StatisticsRepo = Depends(get_statistics_repo),
) -> ListAllArticlesUseCase:
    return ListAllArticlesUseCase(repo=repo)


def get_uc_list_qc_articles(
    repo: StatisticsRepo = Depends(get_statistics_repo),
) -> ListQcArticlesUseCase:
    return ListQcArticlesUseCase(repo=repo)


def get_uc_get_article_detail(
    repo: StatisticsRepo = Depends(get_statistics_repo),
) -> GetArticleDetailUseCase:
    return GetArticleDetailUseCase(repo=repo)
