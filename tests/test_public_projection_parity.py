"""Parity checks across the committed public projections.

Every public surface (trust ledger, leaderboard API, skills API, named index,
contributor API, health endpoint, HTML asset stamps) is generated from the same
registry, so the committed bytes must agree with each other. These tests read
only the committed Class S / API artifacts and derive every expectation from
source data; nothing here hard-codes a count.

Known genuine data defects are encoded as strict xfails with a reason so the
suite stays green while the defect is open, and goes red (xpass) the moment it
is fixed so the marker gets removed.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from collections import defaultdict
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
API = DOCS / "api" / "v1"

# Ceiling on stars imposed by the overall Trust grade (META 1.1 / 4.2): the one
# shared definition used by the named index, ledger and leaderboard.
import sys  # noqa: E402

sys.path.insert(0, str(ROOT / "src"))
from gaia_cli.trustMagnitude import GRADE_MAX_STARS, clampLevelToGrade  # noqa: E402

# HTML pages allowed to carry a stale asset/version stamp, path -> reason.
STALE_STAMP_ALLOWLIST: dict[str, str] = {}


def stars(level: str | None) -> int:
    match = re.match(r"(\d+)", level or "")
    return int(match.group(1)) if match else 0


def grade(value: str | None) -> str:
    """The ledger spells a missing grade `ungraded`; the named index uses null."""
    return value or "ungraded"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def pyprojectVersion() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert match, "pyproject.toml has no version"
    return match.group(1)


@pytest.fixture(scope="module")
def ledger() -> dict:
    return load(DOCS / "graph" / "ledger" / "data.json")


@pytest.fixture(scope="module")
def ledgerRows(ledger) -> dict[str, dict]:
    return {row["skillId"]: row for row in ledger["rows"]}


@pytest.fixture(scope="module")
def leaderboard() -> dict:
    return load(API / "leaderboard.json")


@pytest.fixture(scope="module")
def namedIndex() -> dict:
    return load(DOCS / "graph" / "named" / "index.json")


@pytest.fixture(scope="module")
def namedEntries(namedIndex) -> dict[str, dict]:
    """Every named entry (bucketed or awaiting classification) keyed by id."""
    entries = {
        entry["id"]: entry
        for bucket in namedIndex["buckets"].values()
        for entry in bucket
    }
    for entry in namedIndex["awaitingClassification"]:
        entries.setdefault(entry["id"], entry)
    return entries


@pytest.fixture(scope="module")
def bucketedEntries(namedIndex) -> dict[str, dict]:
    return {
        entry["id"]: entry
        for bucket in namedIndex["buckets"].values()
        for entry in bucket
    }


@pytest.fixture(scope="module")
def apiSkillPages() -> list[dict]:
    index = load(API / "skills" / "index.json")
    pages = [index]
    for number in range(2, index["totalPages"] + 1):
        pages.append(load(API / "skills" / f"page-{number}.json"))
    return pages


@pytest.fixture(scope="module")
def apiSkills(apiSkillPages) -> dict[str, dict]:
    return {skill["id"]: skill for page in apiSkillPages for skill in page["skills"]}


@pytest.fixture(scope="module")
def apiDetails(apiSkills) -> dict[str, dict]:
    details = {}
    for skillId in apiSkills:
        details[skillId] = load(API / "skills" / f"{skillId}.json")
    return details


# --- (a) leaderboard vs ledger ----------------------------------------------


def test_leaderboard_matches_ledger_rows(leaderboard, ledger, ledgerRows):
    boardRows = {row["id"]: row for row in leaderboard["rows"]}
    assert len(boardRows) == len(leaderboard["rows"]), "duplicate ids in leaderboard"
    assert set(boardRows) == set(ledgerRows)
    for skillId, row in boardRows.items():
        source = ledgerRows[skillId]
        assert row["trustMagnitude"] == source["tm"], skillId
        assert row["grade"] == source["grade"], skillId
        assert row["level"] == source["currentStars"], skillId
        assert row["origin"] == source["origin"], skillId


def test_leaderboard_distribution_equals_ledger_summary(leaderboard, ledger):
    assert leaderboard["distribution"] == ledger["summary"]


def test_ledger_summary_matches_its_rows(ledger):
    rows = ledger["rows"]
    summary = ledger["summary"]
    assert summary["total"] == len(rows)
    for letter in ("S", "A", "B", "C", "ungraded"):
        assert summary[letter] == sum(1 for row in rows if row["grade"] == letter), letter
    assert sum(summary[letter] for letter in ("S", "A", "B", "C", "ungraded")) == summary["total"]
    assert summary["floor"] == sum(1 for row in rows if row["flag"] == "[floor]")
    assert summary["up"] == sum(1 for row in rows if row["flag"] == "[up]")


def test_leaderboard_sorted_by_tm_desc_with_stable_tiebreak(leaderboard):
    rows = leaderboard["rows"]
    keys = [(-row["trustMagnitude"], row["id"]) for row in rows]
    assert keys == sorted(keys)


def test_leaderboard_carries_generated_at_the_page_reads(leaderboard, ledger):
    # docs/trust/leaderboard/leaderboard.js stamps its "Updated" tag from this.
    # Every `gaia dev docs` bumps the ledger's generatedAt while the drift check
    # masks it, so leaderboard.json may legitimately lag the ledger: require a
    # valid ISO-8601 stamp that is not newer than the ledger's.
    stamp = leaderboard.get("generatedAt")
    assert stamp, "leaderboard.json lost generatedAt"
    parse = lambda value: datetime.fromisoformat(value.replace("Z", "+00:00"))  # noqa: E731
    assert parse(stamp) <= parse(ledger["generatedAt"])


# --- (b) skills API vs ledger (1-star redaction) ----------------------------


def test_skills_api_pages_are_consistent(apiSkillPages, apiSkills):
    declared = apiSkillPages[0]["totalSkills"]
    listed = [skill["id"] for page in apiSkillPages for skill in page["skills"]]
    assert len(listed) == len(set(listed)), "a skill appears on two pages"
    assert declared == len(listed) == len(apiSkills)
    assert all(page["totalSkills"] == declared for page in apiSkillPages)
    assert all(page["totalPages"] == len(apiSkillPages) for page in apiSkillPages)
    keys = [(-skill["trustMagnitude"], skill["id"]) for skill in listedSkills(apiSkillPages)]
    assert keys == sorted(keys), "skills pages are not TM-desc with id tiebreak"


def listedSkills(pages):
    return [skill for page in pages for skill in page["skills"]]


def test_skills_api_is_ledger_minus_one_star_redaction(
    apiSkills, ledgerRows, namedEntries, apiSkillPages
):
    """totalSkills == ledger rows whose published level is not 1-star.

    Redaction is decided on the displayed (grade-clamped) named index level.
    """
    redacted = {
        skillId for skillId in ledgerRows if stars(namedEntries[skillId]["level"]) <= 1
    }
    assert set(apiSkills) == set(ledgerRows) - redacted
    assert apiSkillPages[0]["totalSkills"] == len(ledgerRows) - len(redacted)
    assert all(stars(skill["level"]) >= 2 for skill in apiSkills.values())


# --- (c) named index vs API detail vs ledger --------------------------------


def test_named_index_matches_api_detail(apiDetails, bucketedEntries):
    for skillId, detail in apiDetails.items():
        entry = bucketedEntries[skillId]
        assert detail["trustMagnitude"] == entry["trustMagnitude"], skillId
        assert detail["level"] == entry["level"], skillId
        assert detail["overallTrustGrade"] == entry["overallTrustGrade"], skillId
        assert detail["origin"] == entry["origin"], skillId


def test_api_list_rows_match_api_detail(apiSkills, apiDetails):
    for skillId, row in apiSkills.items():
        detail = apiDetails[skillId]
        for key in ("trustMagnitude", "level", "overallTrustGrade", "branch", "type"):
            assert row[key] == detail[key], (skillId, key)


def test_ledger_matches_named_index_on_tm_grade_origin(ledgerRows, namedEntries):
    for skillId, row in ledgerRows.items():
        entry = namedEntries[skillId]
        assert row["tm"] == entry["trustMagnitude"], skillId
        assert row["grade"] == grade(entry.get("overallTrustGrade")), skillId
        assert row["origin"] == entry["origin"], skillId


def test_ledger_level_equals_named_index_level(ledgerRows, namedEntries):
    """FD-7: the ledger publishes the grade-clamped level, like the named index."""
    drift = {
        skillId: (row["currentStars"], namedEntries[skillId]["level"])
        for skillId, row in ledgerRows.items()
        if row["currentStars"] != namedEntries[skillId]["level"]
    }
    assert not drift, f"{len(drift)} ledger rows disagree on level: {sorted(drift)[:5]}"


def test_ledger_stored_stars_is_clamped_to_displayed_level(ledgerRows):
    """storedStars keeps the frontmatter level; currentStars is its grade clamp."""
    for skillId, row in ledgerRows.items():
        assert "storedStars" in row, skillId
        assert row["currentStars"] == clampLevelToGrade(row["storedStars"], row["grade"]), skillId
        assert stars(row["currentStars"]) <= GRADE_MAX_STARS[row["grade"]], skillId


def test_all_surfaces_agree_on_displayed_level(
    ledgerRows, leaderboard, apiSkills, apiDetails, namedEntries
):
    """Named index, ledger, leaderboard and skills API show one level per skill."""
    board = {row["id"]: row for row in leaderboard["rows"]}
    for skillId, row in ledgerRows.items():
        shown = namedEntries[skillId]["level"]
        assert row["currentStars"] == shown, (skillId, "ledger")
        assert board[skillId]["level"] == shown, (skillId, "leaderboard")
        assert board[skillId]["storedStars"] == row["storedStars"], (skillId, "leaderboard stored")
        if skillId in apiSkills:
            assert apiSkills[skillId]["level"] == shown, (skillId, "skills api list")
            assert apiDetails[skillId]["level"] == shown, (skillId, "skills api detail")


def test_leaderboard_order_is_tm_sorted_independent_of_level(leaderboard):
    keys = [(-row["trustMagnitude"], row["id"]) for row in leaderboard["rows"]]
    assert keys == sorted(keys)


# --- (d) contributor prestige -----------------------------------------------


def test_contributor_prestige_is_sum_of_visible_tm(apiSkills):
    # Definition: scripts/buildApiProjection.py::build_contributors sums the
    # trustMagnitude of the contributor's non-redacted skills, rounded to 2dp.
    byHandle: dict[str, list[dict]] = defaultdict(list)
    for skill in apiSkills.values():
        byHandle[skill["contributor"]].append(skill)
    index = load(API / "contributors" / "index.json")
    indexed = {entry["handle"]: entry for entry in index["contributors"]}
    assert set(indexed) == set(byHandle)
    for handle, skills in byHandle.items():
        expected = round(sum(skill["trustMagnitude"] for skill in skills), 2)
        detail = load(API / "contributors" / f"{handle}.json")
        assert detail["prestigeScore"] == pytest.approx(expected, abs=0.011), handle
        assert indexed[handle]["prestigeScore"] == pytest.approx(expected, abs=0.011), handle
        assert detail["namedSkillsCount"] == len(skills), handle
        top = max(skills, key=lambda skill: skill["trustMagnitude"])
        assert detail["topSkill"]["trustMagnitude"] == top["trustMagnitude"], handle


# --- (e) API detail evidence vs named index evidence ------------------------


def test_api_detail_evidence_equals_named_index_evidence(apiDetails, bucketedEntries):
    for skillId, detail in apiDetails.items():
        assert detail.get("evidence", []) == bucketedEntries[skillId].get("evidence", []), skillId


# --- (f) Origin uniqueness ---------------------------------------------------


def test_each_claimed_bucket_has_exactly_one_origin(namedIndex):
    # GOVERNANCE: exactly one current Origin per claimed generic node.
    for generic, entries in namedIndex["buckets"].items():
        origins = [entry["id"] for entry in entries if entry.get("origin") is True]
        assert len(origins) <= 1, (generic, origins)
        assert all(entry["genericSkillRef"] == generic for entry in entries), generic


def test_origin_is_unique_across_all_named_entries(namedIndex):
    claims: dict[str, list[str]] = defaultdict(list)
    for entries in list(namedIndex["buckets"].values()) + [namedIndex["awaitingClassification"]]:
        for entry in entries:
            if entry.get("origin") is True:
                claims[entry["genericSkillRef"]].append(entry["id"])
    assert all(len(ids) == 1 for ids in claims.values()), {
        generic: ids for generic, ids in claims.items() if len(ids) != 1
    }


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "Finding: a named skill at 2-star or above sits in awaitingClassification "
        "(status awakened) so it is absent from the ledger, leaderboard, skills "
        "API and every bucket, yet carries origin true. At the time of writing: "
        "google-deepmind/workflow-skill-creator (4-star, TM 100.82, grade A). "
        "Registry data must not be edited here."
    ),
)
def test_no_public_level_entry_is_hidden_in_awaiting_classification(namedIndex):
    hidden = [
        entry["id"]
        for entry in namedIndex["awaitingClassification"]
        if stars(entry["level"]) >= 2
    ]
    assert not hidden, hidden


def test_origin_flags_in_ledger_belong_to_bucketed_entries(ledgerRows, bucketedEntries):
    for skillId, row in ledgerRows.items():
        assert skillId in bucketedEntries, skillId
        assert row["origin"] == bucketedEntries[skillId]["origin"], skillId


# --- (g) version stamps ------------------------------------------------------


def test_health_version_matches_pyproject():
    assert load(API / "health.json")["version"] == pyprojectVersion()


def test_health_named_count_matches_skills_api(apiSkills):
    assert load(API / "health.json")["namedSkillsCount"] == len(apiSkills)


ASSET_STAMP = re.compile(r"""\.(?:css|js)\?v=(\d+\.\d+\.\d+)""")
GLOBAL_STAMP = re.compile(r"""window\.GAIA_VERSION\s*=\s*"(\d+\.\d+\.\d+)\"""")


def test_every_html_version_stamp_matches_pyproject():
    expected = pyprojectVersion()
    stale: dict[str, set[str]] = {}
    for page in sorted(DOCS.rglob("*.html")):
        rel = page.relative_to(DOCS).as_posix()
        text = page.read_text(encoding="utf-8", errors="replace")
        found = set(ASSET_STAMP.findall(text)) | set(GLOBAL_STAMP.findall(text))
        found.discard(expected)
        if found and rel not in STALE_STAMP_ALLOWLIST:
            stale[rel] = found
    assert not stale, (
        f"{len(stale)} pages carry a version stamp other than {expected}: "
        f"{dict(list(stale.items())[:5])}. Run `gaia dev docs` and commit the result."
    )


def test_stale_stamp_allowlist_entries_have_reasons():
    assert all(reason.strip() for reason in STALE_STAMP_ALLOWLIST.values())
