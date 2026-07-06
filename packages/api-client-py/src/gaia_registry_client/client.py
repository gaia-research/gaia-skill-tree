"""Gaia Registry API Client — sync and async HTTP clients.

Both clients provide typed access to all Gaia Registry API endpoints.
The API is static JSON served via CDN — no authentication required.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

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
    Hero,
    Heroes,
    Leaderboard,
    LeaderboardRow,
    PaginationLinks,
    SearchIndex,
    SearchIndexEntry,
    SkillDetail,
    SkillListPage,
    SkillSummary,
    TopSkill,
    Trending,
    TrendingEntry,
)

DEFAULT_BASE_URL = "https://gaiaskilltree.com"
DEFAULT_TIMEOUT = 30.0


# ─── Deserialization helpers ───────────────────────────────────────────────────


def _parse_health(data: dict[str, Any]) -> Health:
    return Health(
        ok=data["ok"],
        version=data["version"],
        registry_generated_at=data["registryGeneratedAt"],
        named_skills_count=data["namedSkillsCount"],
    )


def _parse_skill_summary(data: dict[str, Any]) -> SkillSummary:
    return SkillSummary(
        id=data["id"],
        name=data["name"],
        level=data["level"],
        trust_magnitude=data["trustMagnitude"],
        overall_trust_grade=data["overallTrustGrade"],
        contributor=data["contributor"],
        type=data["type"],
        links_self=data.get("_links", {}).get("self", ""),
    )


def _parse_pagination_links(data: dict[str, Any]) -> PaginationLinks:
    links = data.get("_links", {})
    return PaginationLinks(
        self_url=links.get("self", ""),
        next_url=links.get("next"),
        prev_url=links.get("prev"),
    )


def _parse_skill_list_page(data: dict[str, Any]) -> SkillListPage:
    return SkillListPage(
        skills=[_parse_skill_summary(s) for s in data.get("skills", [])],
        page=data.get("page", 1),
        total_pages=data.get("totalPages", 1),
        total_skills=data.get("totalSkills", 0),
        links=_parse_pagination_links(data),
    )


def _parse_evidence_entry(data: dict[str, Any]) -> EvidenceEntry:
    return EvidenceEntry(
        type=data["type"],
        evidence_class=data["class"],
        source=data["source"],
        grade=data["grade"],
        evaluator=data.get("evaluator"),
        date=data.get("date"),
        notes=data.get("notes"),
        trust_number=data.get("trustNumber"),
    )


def _parse_apex_gate_status(data: dict[str, Any] | None) -> ApexGateStatus | None:
    if data is None:
        return None
    return ApexGateStatus(
        a_graded_origins_gte5=data.get("aGradedOriginsGte5"),
        source_tenure_days_gte180_a_or_s=data.get("sourceTenureDaysGte180AorS"),
        direct_nested_suite_gte1=data.get("directNestedSuiteGte1"),
        depth2_only_reachable_gte1=data.get("depth2OnlyReachableGte1"),
        overall_grade_s=data.get("overallGradeS"),
        apex_promotion_pr_signed=data.get("apexPromotionPrSigned"),
        cross_org_verifier=data.get("crossOrgVerifier"),
        system_wide_cap=data.get("systemWideCap"),
    )


def _parse_skill_detail(data: dict[str, Any]) -> SkillDetail:
    links = data.get("_links", {})
    return SkillDetail(
        id=data["id"],
        name=data["name"],
        level=data["level"],
        trust_magnitude=data["trustMagnitude"],
        overall_trust_grade=data["overallTrustGrade"],
        contributor=data["contributor"],
        type=data["type"],
        status=data.get("status"),
        title=data.get("title"),
        generic_skill_ref=data.get("genericSkillRef"),
        description=data.get("description"),
        tags=data.get("tags", []),
        origin=data.get("origin"),
        evidence=[_parse_evidence_entry(e) for e in data.get("evidence", [])],
        apex_gate_status=_parse_apex_gate_status(data.get("apexGateStatus")),
        links_self=links.get("self", ""),
        links_contributor=links.get("contributor", ""),
        links_list=links.get("list", ""),
    )


def _parse_top_skill(data: dict[str, Any] | None) -> TopSkill | None:
    if data is None:
        return None
    return TopSkill(
        id=data["id"],
        level=data["level"],
        trust_magnitude=data["trustMagnitude"],
    )


def _parse_contributor_summary(data: dict[str, Any]) -> ContributorSummary:
    return ContributorSummary(
        handle=data["handle"],
        named_skills=data["namedSkills"],
        prestige_score=data["prestigeScore"],
        top_skill=_parse_top_skill(data.get("topSkill")),
        links_self=data.get("_links", {}).get("self", ""),
    )


def _parse_contributor_list(data: dict[str, Any]) -> ContributorList:
    return ContributorList(
        contributors=[_parse_contributor_summary(c) for c in data.get("contributors", [])],
    )


def _parse_contributor_detail(data: dict[str, Any]) -> ContributorDetail:
    return ContributorDetail(
        handle=data["handle"],
        named_skills=[_parse_skill_summary(s) for s in data.get("namedSkills", [])],
    )


def _parse_grade_distribution(data: dict[str, Any]) -> GradeDistribution:
    return GradeDistribution(
        total=data.get("total", 0),
        s=data.get("S", 0),
        a=data.get("A", 0),
        b=data.get("B", 0),
        c=data.get("C", 0),
        ungraded=data.get("ungraded", 0),
        floor=data.get("floor", 0),
        up=data.get("up", 0),
    )


def _parse_leaderboard_row(data: dict[str, Any]) -> LeaderboardRow:
    return LeaderboardRow(
        id=data["id"],
        trust_magnitude=data["trustMagnitude"],
        grade=data["grade"],
        level=data["level"],
    )


def _parse_leaderboard(data: dict[str, Any]) -> Leaderboard:
    return Leaderboard(
        distribution=_parse_grade_distribution(data.get("distribution", {})),
        rows=[_parse_leaderboard_row(r) for r in data.get("rows", [])],
    )


def _parse_evidence_type(data: dict[str, Any]) -> EvidenceType:
    return EvidenceType(
        id=data["id"],
        description=data["description"],
        weight=data["weight"],
        magnitude=data.get("magnitude"),
        cap=data.get("cap"),
        grade_ceiling=data.get("gradeCeiling"),
        freshness=data.get("freshness"),
        self_producible=data.get("selfProducible"),
        allowed_layers=data.get("allowedLayers", []),
        notes=data.get("notes"),
    )


def _parse_evidence_type_catalogue(data: dict[str, Any]) -> EvidenceTypeCatalogue:
    return EvidenceTypeCatalogue(
        types=[_parse_evidence_type(t) for t in data.get("types", [])],
    )


def _parse_search_index_entry(data: dict[str, Any]) -> SearchIndexEntry:
    return SearchIndexEntry(
        id=data["id"],
        name=data["name"],
        contributor=data["contributor"],
        tokens=data.get("tokens", []),
        level=data.get("level"),
        grade=data.get("grade"),
        trust_magnitude=data.get("trustMagnitude"),
    )


def _parse_search_index(data: list[dict[str, Any]]) -> SearchIndex:
    return [_parse_search_index_entry(e) for e in data]


def _parse_trending_entry(data: dict[str, Any]) -> TrendingEntry:
    return TrendingEntry(
        id=data["id"],
        name=data["name"],
        contributor=data["contributor"],
        delta=data["delta"],
        trust_magnitude=data["trustMagnitude"],
        grade=data.get("grade"),
    )


def _parse_trending(data: dict[str, Any]) -> Trending:
    return Trending(
        window=data["window"],
        entries=[_parse_trending_entry(e) for e in data.get("entries", [])],
    )


def _parse_hero(data: dict[str, Any]) -> Hero:
    return Hero(
        handle=data["handle"],
        skills=data["skills"],
        prestige_score=data["prestigeScore"],
        title=data.get("title"),
    )


def _parse_heroes(data: dict[str, Any]) -> Heroes:
    return Heroes(heroes=[_parse_hero(h) for h in data.get("heroes", [])])


# ─── GaiaApiError ──────────────────────────────────────────────────────────────


class GaiaApiError(Exception):
    """Raised when the Gaia API returns a non-2xx response."""

    def __init__(self, message: str, status_code: int, url: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.url = url


# ─── Sync Client ───────────────────────────────────────────────────────────────


class GaiaClient:
    """Synchronous client for the Gaia Registry API.

    Example:
        >>> from gaia_registry_client import GaiaClient
        >>> client = GaiaClient()
        >>> health = client.get_health()
        >>> print(health.named_skills_count)
        139
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        client: httpx.Client | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=timeout)
        self._owns_client = client is None

    def close(self) -> None:
        """Close the underlying HTTP client (only if we created it)."""
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> GaiaClient:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def _get(self, path: str) -> Any:
        url = f"{self._base_url}{path}"
        response = self._client.get(url)
        if response.status_code >= 400:
            raise GaiaApiError(
                f"HTTP {response.status_code}: {response.reason_phrase}",
                response.status_code,
                url,
            )
        return response.json()

    def get_health(self) -> Health:
        """Health check — API liveness, registry version, generation date."""
        return _parse_health(self._get("/api/v1/health.json"))

    def list_skills(self, page: int = 1) -> SkillListPage:
        """List named skills (paginated). Page 1 is the default."""
        path = (
            "/api/v1/skills/index.json"
            if page <= 1
            else f"/api/v1/skills/page-{page}.json"
        )
        return _parse_skill_list_page(self._get(path))

    def get_skill(self, contributor: str, skill: str) -> SkillDetail:
        """Get full detail for a single named skill."""
        contributor_slug = quote(contributor, safe="")
        skill_slug = quote(skill, safe="")
        return _parse_skill_detail(
            self._get(f"/api/v1/skills/{contributor_slug}/{skill_slug}.json")
        )

    def list_contributors(self) -> ContributorList:
        """List all contributors sorted by prestige score."""
        return _parse_contributor_list(self._get("/api/v1/contributors/index.json"))

    def get_contributor(self, handle: str) -> ContributorDetail:
        """Get a contributor's full profile with all their named skills."""
        handle_slug = quote(handle, safe="")
        return _parse_contributor_detail(
            self._get(f"/api/v1/contributors/{handle_slug}.json")
        )

    def get_leaderboard(self) -> Leaderboard:
        """Trust leaderboard — grade distribution and ranked skills."""
        return _parse_leaderboard(self._get("/api/v1/leaderboard.json"))

    def get_evidence_types(self) -> EvidenceTypeCatalogue:
        """Evidence type catalogue — all recognised types with formulas."""
        return _parse_evidence_type_catalogue(self._get("/api/v1/evidence-types.json"))

    def get_search_index(self) -> SearchIndex:
        """Search index — flat array for client-side full-text search."""
        return _parse_search_index(self._get("/api/v1/search-index.json"))

    def get_trending(self, window: str = "7d") -> Trending:
        """Trending skills over a time window ('7d' or '30d')."""
        return _parse_trending(self._get(f"/api/v1/trending/{window}.json"))

    def get_heroes(self) -> Heroes:
        """Heroes — top contributors by prestige."""
        return _parse_heroes(self._get("/api/v1/heroes.json"))


# ─── Async Client ──────────────────────────────────────────────────────────────


class AsyncGaiaClient:
    """Asynchronous client for the Gaia Registry API.

    Example:
        >>> import asyncio
        >>> from gaia_registry_client import AsyncGaiaClient
        >>> async def main():
        ...     async with AsyncGaiaClient() as client:
        ...         health = await client.get_health()
        ...         print(health.named_skills_count)
        >>> asyncio.run(main())
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.AsyncClient(timeout=timeout)
        self._owns_client = client is None

    async def close(self) -> None:
        """Close the underlying HTTP client (only if we created it)."""
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> AsyncGaiaClient:
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    async def _get(self, path: str) -> Any:
        url = f"{self._base_url}{path}"
        response = await self._client.get(url)
        if response.status_code >= 400:
            raise GaiaApiError(
                f"HTTP {response.status_code}: {response.reason_phrase}",
                response.status_code,
                url,
            )
        return response.json()

    async def get_health(self) -> Health:
        """Health check — API liveness, registry version, generation date."""
        return _parse_health(await self._get("/api/v1/health.json"))

    async def list_skills(self, page: int = 1) -> SkillListPage:
        """List named skills (paginated). Page 1 is the default."""
        path = (
            "/api/v1/skills/index.json"
            if page <= 1
            else f"/api/v1/skills/page-{page}.json"
        )
        return _parse_skill_list_page(await self._get(path))

    async def get_skill(self, contributor: str, skill: str) -> SkillDetail:
        """Get full detail for a single named skill."""
        contributor_slug = quote(contributor, safe="")
        skill_slug = quote(skill, safe="")
        return _parse_skill_detail(
            await self._get(f"/api/v1/skills/{contributor_slug}/{skill_slug}.json")
        )

    async def list_contributors(self) -> ContributorList:
        """List all contributors sorted by prestige score."""
        return _parse_contributor_list(await self._get("/api/v1/contributors/index.json"))

    async def get_contributor(self, handle: str) -> ContributorDetail:
        """Get a contributor's full profile with all their named skills."""
        handle_slug = quote(handle, safe="")
        return _parse_contributor_detail(
            await self._get(f"/api/v1/contributors/{handle_slug}.json")
        )

    async def get_leaderboard(self) -> Leaderboard:
        """Trust leaderboard — grade distribution and ranked skills."""
        return _parse_leaderboard(await self._get("/api/v1/leaderboard.json"))

    async def get_evidence_types(self) -> EvidenceTypeCatalogue:
        """Evidence type catalogue — all recognised types with formulas."""
        return _parse_evidence_type_catalogue(await self._get("/api/v1/evidence-types.json"))

    async def get_search_index(self) -> SearchIndex:
        """Search index — flat array for client-side full-text search."""
        return _parse_search_index(await self._get("/api/v1/search-index.json"))

    async def get_trending(self, window: str = "7d") -> Trending:
        """Trending skills over a time window ('7d' or '30d')."""
        return _parse_trending(await self._get(f"/api/v1/trending/{window}.json"))

    async def get_heroes(self) -> Heroes:
        """Heroes — top contributors by prestige."""
        return _parse_heroes(await self._get("/api/v1/heroes.json"))
