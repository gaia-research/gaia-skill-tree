"""Unit tests for gaia_registry_client — sync and async clients."""

from __future__ import annotations

import pytest
import respx

from gaia_registry_client import AsyncGaiaClient, GaiaClient
from gaia_registry_client.client import GaiaApiError
from gaia_registry_client.models import (
    ContributorDetail,
    ContributorList,
    EvidenceTypeCatalogue,
    Health,
    Heroes,
    Leaderboard,
    SearchIndexEntry,
    SkillDetail,
    SkillListPage,
    Trending,
)

# ─── Fixtures (matching real API shapes) ──────────────────────────────────────

BASE = "https://gaia.tiongson.co"

HEALTH_JSON = {
    "ok": True,
    "version": "5.6.0",
    "registryGeneratedAt": "2026-06-26",
    "namedSkillsCount": 139,
}

SKILLS_PAGE_JSON = {
    "skills": [
        {
            "id": "garrytan/gstack",
            "name": "Gstack",
            "level": "5\u2605",
            "trustMagnitude": 589.32,
            "overallTrustGrade": "S",
            "contributor": "garrytan",
            "type": "ultimate",
            "_links": {"self": "/api/v1/skills/garrytan/gstack.json"},
        }
    ],
    "page": 1,
    "totalPages": 3,
    "totalSkills": 139,
    "_links": {
        "self": "/api/v1/skills/index.json",
        "next": "/api/v1/skills/page-2.json",
    },
}

SKILL_DETAIL_JSON = {
    "id": "garrytan/gstack",
    "name": "Gstack",
    "level": "5\u2605",
    "trustMagnitude": 589.32,
    "overallTrustGrade": "S",
    "contributor": "garrytan",
    "type": "ultimate",
    "status": "named",
    "title": "Gstack \u2014 Garry Tan's Full-Stack Agent Suite",
    "description": "Agent orchestration framework.",
    "tags": ["agent", "orchestration"],
    "evidence": [
        {
            "type": "repo",
            "class": "A",
            "source": "https://github.com/garrytan/gstack",
            "grade": "B",
            "trustNumber": 70.0,
        }
    ],
    "_links": {
        "self": "/api/v1/skills/garrytan/gstack.json",
        "contributor": "/api/v1/contributors/garrytan.json",
        "list": "/api/v1/skills/index.json",
    },
}

CONTRIBUTORS_JSON = {
    "contributors": [
        {
            "handle": "garrytan",
            "namedSkills": 47,
            "topSkill": {"id": "garrytan/gstack", "level": "5\u2605", "trustMagnitude": 589.32},
            "prestigeScore": 2996.5,
            "_links": {"self": "/api/v1/contributors/garrytan.json"},
        }
    ]
}

CONTRIBUTOR_DETAIL_JSON = {
    "handle": "garrytan",
    "namedSkills": [
        {
            "id": "garrytan/gstack",
            "name": "Gstack",
            "level": "5\u2605",
            "trustMagnitude": 589.32,
            "overallTrustGrade": "S",
            "contributor": "garrytan",
            "type": "ultimate",
            "_links": {"self": "/api/v1/skills/garrytan/gstack.json"},
        }
    ],
}

LEADERBOARD_JSON = {
    "distribution": {"total": 249, "S": 4, "A": 42, "B": 56, "C": 77, "ungraded": 70},
    "rows": [
        {"id": "garrytan/gstack", "trustMagnitude": 589.32, "grade": "S", "level": "5\u2605"}
    ],
}

EVIDENCE_TYPES_JSON = {
    "types": [
        {
            "id": "github-stars-own",
            "description": "Stars on the contributor's own repo",
            "weight": 1.0,
            "gradeCeiling": "S",
            "selfProducible": True,
        }
    ]
}

SEARCH_INDEX_JSON = [
    {
        "id": "garrytan/gstack",
        "name": "Gstack",
        "contributor": "garrytan",
        "level": "5\u2605",
        "grade": "S",
        "trustMagnitude": 589.32,
        "tokens": ["gstack", "garry", "tan", "agent"],
    }
]

TRENDING_JSON = {
    "window": "7d",
    "entries": [
        {
            "id": "garrytan/gstack",
            "name": "Gstack",
            "contributor": "garrytan",
            "delta": 12.5,
            "trustMagnitude": 589.32,
            "grade": "S",
        }
    ],
}

HEROES_JSON = {
    "heroes": [
        {"handle": "garrytan", "skills": 47, "prestigeScore": 2996.5},
    ]
}


# ─── Sync Client Tests ────────────────────────────────────────────────────────


class TestGaiaClientSync:
    """Test the synchronous GaiaClient."""

    @respx.mock
    def test_get_health(self):
        respx.get(f"{BASE}/api/v1/health.json").respond(json=HEALTH_JSON)
        client = GaiaClient(base_url=BASE)
        health = client.get_health()

        assert isinstance(health, Health)
        assert health.ok is True
        assert health.version == "5.6.0"
        assert health.registry_generated_at == "2026-06-26"
        assert health.named_skills_count == 139

    @respx.mock
    def test_list_skills_page1(self):
        respx.get(f"{BASE}/api/v1/skills/index.json").respond(json=SKILLS_PAGE_JSON)
        client = GaiaClient(base_url=BASE)
        result = client.list_skills()

        assert isinstance(result, SkillListPage)
        assert result.page == 1
        assert result.total_pages == 3
        assert result.total_skills == 139
        assert len(result.skills) == 1
        assert result.skills[0].id == "garrytan/gstack"
        assert result.links.next_url == "/api/v1/skills/page-2.json"

    @respx.mock
    def test_list_skills_page2(self):
        respx.get(f"{BASE}/api/v1/skills/page-2.json").respond(
            json={**SKILLS_PAGE_JSON, "page": 2}
        )
        client = GaiaClient(base_url=BASE)
        result = client.list_skills(page=2)
        assert result.page == 2

    @respx.mock
    def test_get_skill(self):
        respx.get(f"{BASE}/api/v1/skills/garrytan/gstack.json").respond(json=SKILL_DETAIL_JSON)
        client = GaiaClient(base_url=BASE)
        skill = client.get_skill("garrytan", "gstack")

        assert isinstance(skill, SkillDetail)
        assert skill.id == "garrytan/gstack"
        assert skill.status == "named"
        assert skill.overall_trust_grade == "S"
        assert len(skill.evidence) == 1
        assert skill.evidence[0].evidence_class == "A"
        assert skill.evidence[0].trust_number == 70.0

    @respx.mock
    def test_list_contributors(self):
        respx.get(f"{BASE}/api/v1/contributors/index.json").respond(json=CONTRIBUTORS_JSON)
        client = GaiaClient(base_url=BASE)
        result = client.list_contributors()

        assert isinstance(result, ContributorList)
        assert len(result.contributors) == 1
        assert result.contributors[0].handle == "garrytan"
        assert result.contributors[0].prestige_score == 2996.5
        assert result.contributors[0].top_skill is not None
        assert result.contributors[0].top_skill.trust_magnitude == 589.32

    @respx.mock
    def test_get_contributor(self):
        respx.get(f"{BASE}/api/v1/contributors/garrytan.json").respond(
            json=CONTRIBUTOR_DETAIL_JSON
        )
        client = GaiaClient(base_url=BASE)
        detail = client.get_contributor("garrytan")

        assert isinstance(detail, ContributorDetail)
        assert detail.handle == "garrytan"
        assert len(detail.named_skills) == 1

    @respx.mock
    def test_get_leaderboard(self):
        respx.get(f"{BASE}/api/v1/leaderboard.json").respond(json=LEADERBOARD_JSON)
        client = GaiaClient(base_url=BASE)
        lb = client.get_leaderboard()

        assert isinstance(lb, Leaderboard)
        assert lb.distribution.total == 249
        assert lb.distribution.s == 4
        assert len(lb.rows) == 1
        assert lb.rows[0].grade == "S"

    @respx.mock
    def test_get_evidence_types(self):
        respx.get(f"{BASE}/api/v1/evidence-types.json").respond(json=EVIDENCE_TYPES_JSON)
        client = GaiaClient(base_url=BASE)
        cat = client.get_evidence_types()

        assert isinstance(cat, EvidenceTypeCatalogue)
        assert len(cat.types) == 1
        assert cat.types[0].id == "github-stars-own"
        assert cat.types[0].weight == 1.0

    @respx.mock
    def test_get_search_index(self):
        respx.get(f"{BASE}/api/v1/search-index.json").respond(json=SEARCH_INDEX_JSON)
        client = GaiaClient(base_url=BASE)
        index = client.get_search_index()

        assert len(index) == 1
        assert isinstance(index[0], SearchIndexEntry)
        assert "agent" in index[0].tokens

    @respx.mock
    def test_get_trending(self):
        respx.get(f"{BASE}/api/v1/trending/7d.json").respond(json=TRENDING_JSON)
        client = GaiaClient(base_url=BASE)
        result = client.get_trending("7d")

        assert isinstance(result, Trending)
        assert result.window == "7d"
        assert len(result.entries) == 1
        assert result.entries[0].delta == 12.5

    @respx.mock
    def test_get_heroes(self):
        respx.get(f"{BASE}/api/v1/heroes.json").respond(json=HEROES_JSON)
        client = GaiaClient(base_url=BASE)
        result = client.get_heroes()

        assert isinstance(result, Heroes)
        assert len(result.heroes) == 1
        assert result.heroes[0].handle == "garrytan"

    @respx.mock
    def test_error_404(self):
        respx.get(f"{BASE}/api/v1/skills/nobody/nothing.json").respond(status_code=404)
        client = GaiaClient(base_url=BASE)

        with pytest.raises(GaiaApiError) as exc_info:
            client.get_skill("nobody", "nothing")

        assert exc_info.value.status_code == 404
        assert "nobody" in exc_info.value.url

    @respx.mock
    def test_context_manager(self):
        respx.get(f"{BASE}/api/v1/health.json").respond(json=HEALTH_JSON)
        with GaiaClient(base_url=BASE) as client:
            health = client.get_health()
            assert health.ok is True

    @respx.mock
    def test_trailing_slash_stripped(self):
        respx.get(f"{BASE}/api/v1/health.json").respond(json=HEALTH_JSON)
        client = GaiaClient(base_url=f"{BASE}///")
        health = client.get_health()
        assert health.ok is True


# ─── Async Client Tests ───────────────────────────────────────────────────────


class TestAsyncGaiaClient:
    """Test the asynchronous AsyncGaiaClient."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_health(self):
        respx.get(f"{BASE}/api/v1/health.json").respond(json=HEALTH_JSON)
        async with AsyncGaiaClient(base_url=BASE) as client:
            health = await client.get_health()

        assert isinstance(health, Health)
        assert health.ok is True
        assert health.named_skills_count == 139

    @respx.mock
    @pytest.mark.asyncio
    async def test_list_skills(self):
        respx.get(f"{BASE}/api/v1/skills/index.json").respond(json=SKILLS_PAGE_JSON)
        async with AsyncGaiaClient(base_url=BASE) as client:
            result = await client.list_skills()

        assert result.page == 1
        assert len(result.skills) == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_skill(self):
        respx.get(f"{BASE}/api/v1/skills/garrytan/gstack.json").respond(json=SKILL_DETAIL_JSON)
        async with AsyncGaiaClient(base_url=BASE) as client:
            skill = await client.get_skill("garrytan", "gstack")

        assert skill.id == "garrytan/gstack"
        assert skill.status == "named"

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_leaderboard(self):
        respx.get(f"{BASE}/api/v1/leaderboard.json").respond(json=LEADERBOARD_JSON)
        async with AsyncGaiaClient(base_url=BASE) as client:
            lb = await client.get_leaderboard()

        assert lb.distribution.total == 249

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_trending(self):
        respx.get(f"{BASE}/api/v1/trending/30d.json").respond(
            json={**TRENDING_JSON, "window": "30d"}
        )
        async with AsyncGaiaClient(base_url=BASE) as client:
            result = await client.get_trending("30d")

        assert result.window == "30d"

    @respx.mock
    @pytest.mark.asyncio
    async def test_error_raises(self):
        respx.get(f"{BASE}/api/v1/health.json").respond(status_code=500)
        async with AsyncGaiaClient(base_url=BASE) as client:
            with pytest.raises(GaiaApiError) as exc_info:
                await client.get_health()
            assert exc_info.value.status_code == 500
