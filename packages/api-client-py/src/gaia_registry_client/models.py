"""Data models for the Gaia Registry API.

Uses dataclasses for zero extra dependencies beyond the standard library.
All field names use snake_case; JSON deserialization handles camelCase conversion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


# ─── Health ────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Health:
    ok: bool
    version: str
    registry_generated_at: str
    named_skills_count: int


# ─── Skills ────────────────────────────────────────────────────────────────────

TrustGrade = Literal["S", "A", "B", "C", "D", "F"]
EvidenceClass = Literal["A", "B", "C"]
SkillType = Literal["basic", "extra", "unique", "ultimate"]
SkillStatus = Literal["named", "generic", "pending"]


@dataclass(frozen=True, slots=True)
class SkillSummary:
    id: str
    name: str
    level: str
    trust_magnitude: float
    overall_trust_grade: str
    contributor: str
    type: str
    links_self: str = ""


@dataclass(frozen=True, slots=True)
class PaginationLinks:
    self_url: str = ""
    next_url: str | None = None
    prev_url: str | None = None


@dataclass(frozen=True, slots=True)
class SkillListPage:
    skills: list[SkillSummary] = field(default_factory=list)
    page: int = 1
    total_pages: int = 1
    total_skills: int = 0
    links: PaginationLinks = field(default_factory=PaginationLinks)


@dataclass(frozen=True, slots=True)
class EvidenceEntry:
    type: str
    evidence_class: str
    source: str
    grade: str
    evaluator: str | None = None
    date: str | None = None
    notes: str | None = None
    trust_number: float | None = None


@dataclass(frozen=True, slots=True)
class ApexGateStatus:
    a_graded_origins_gte5: bool | None = None
    source_tenure_days_gte180_a_or_s: bool | None = None
    direct_nested_suite_gte1: bool | None = None
    depth2_only_reachable_gte1: bool | None = None
    overall_grade_s: bool | None = None
    apex_promotion_pr_signed: bool | None = None
    cross_org_verifier: bool | None = None
    system_wide_cap: bool | None = None


@dataclass(frozen=True, slots=True)
class SkillDetail:
    id: str
    name: str
    level: str
    trust_magnitude: float
    overall_trust_grade: str
    contributor: str
    type: str
    status: str | None = None
    title: str | None = None
    generic_skill_ref: str | None = None
    description: str | None = None
    tags: list[str] = field(default_factory=list)
    origin: bool | None = None
    evidence: list[EvidenceEntry] = field(default_factory=list)
    apex_gate_status: ApexGateStatus | None = None
    links_self: str = ""
    links_contributor: str = ""
    links_list: str = ""


# ─── Contributors ──────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class TopSkill:
    id: str
    level: str
    trust_magnitude: float


@dataclass(frozen=True, slots=True)
class ContributorSummary:
    handle: str
    named_skills: int
    prestige_score: float
    top_skill: TopSkill | None = None
    links_self: str = ""


@dataclass(frozen=True, slots=True)
class ContributorList:
    contributors: list[ContributorSummary] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ContributorDetail:
    handle: str
    named_skills: list[SkillSummary] = field(default_factory=list)


# ─── Leaderboard ───────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class GradeDistribution:
    total: int = 0
    s: int = 0
    a: int = 0
    b: int = 0
    c: int = 0
    ungraded: int = 0
    floor: int = 0
    up: int = 0


@dataclass(frozen=True, slots=True)
class LeaderboardRow:
    id: str
    trust_magnitude: float
    grade: str
    level: str


@dataclass(frozen=True, slots=True)
class Leaderboard:
    distribution: GradeDistribution = field(default_factory=GradeDistribution)
    rows: list[LeaderboardRow] = field(default_factory=list)


# ─── Evidence Types ────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class EvidenceType:
    id: str
    description: str
    weight: float
    magnitude: str | None = None
    cap: float | str | None = None
    grade_ceiling: str | None = None
    freshness: str | None = None
    self_producible: bool | None = None
    allowed_layers: list[str] = field(default_factory=list)
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class EvidenceTypeCatalogue:
    types: list[EvidenceType] = field(default_factory=list)


# ─── Search Index ──────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class SearchIndexEntry:
    id: str
    name: str
    contributor: str
    tokens: list[str] = field(default_factory=list)
    level: str | None = None
    grade: str | None = None
    trust_magnitude: float | None = None


SearchIndex = list[SearchIndexEntry]


# ─── Trending ──────────────────────────────────────────────────────────────────

TrendingWindow = Literal["7d", "30d"]


@dataclass(frozen=True, slots=True)
class TrendingEntry:
    id: str
    name: str
    contributor: str
    delta: float
    trust_magnitude: float
    grade: str | None = None


@dataclass(frozen=True, slots=True)
class Trending:
    window: str
    entries: list[TrendingEntry] = field(default_factory=list)


# ─── Heroes ────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Hero:
    handle: str
    skills: int
    prestige_score: float
    title: str | None = None


@dataclass(frozen=True, slots=True)
class Heroes:
    heroes: list[Hero] = field(default_factory=list)
