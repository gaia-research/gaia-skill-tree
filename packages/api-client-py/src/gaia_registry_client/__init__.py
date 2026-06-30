"""Gaia Registry API Client — Python SDK.

Provides sync and async typed HTTP clients for the Gaia skill registry.

Usage:
    from gaia_registry_client import GaiaClient, AsyncGaiaClient

    client = GaiaClient()
    health = client.get_health()
    print(health.named_skills_count)
"""

from gaia_registry_client.client import AsyncGaiaClient, GaiaApiError, GaiaClient
from gaia_registry_client.models import (
    ApexGateStatus,
    ContributorDetail,
    ContributorList,
    ContributorSummary,
    EvidenceEntry,
    EvidenceType,
    EvidenceTypeCatalogue,
    GradeDistribution,
    Health,
    Heroes,
    Hero,
    Leaderboard,
    LeaderboardRow,
    PaginationLinks,
    SearchIndex,
    SearchIndexEntry,
    SkillDetail,
    SkillListPage,
    SkillSummary,
    Trending,
    TrendingEntry,
)

__version__ = "0.1.0"

__all__ = [
    # Clients
    "GaiaClient",
    "AsyncGaiaClient",
    "GaiaApiError",
    # Models
    "ApexGateStatus",
    "ContributorDetail",
    "ContributorList",
    "ContributorSummary",
    "EvidenceEntry",
    "EvidenceType",
    "EvidenceTypeCatalogue",
    "GradeDistribution",
    "Health",
    "Hero",
    "Heroes",
    "Leaderboard",
    "LeaderboardRow",
    "PaginationLinks",
    "SearchIndex",
    "SearchIndexEntry",
    "SkillDetail",
    "SkillListPage",
    "SkillSummary",
    "Trending",
    "TrendingEntry",
]
