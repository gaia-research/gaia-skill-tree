"""Contract completeness oracle for the Yggdrasil II taxonomy authority.

For every named-skill variant in docs/graph/named/index.json (~228 under
`.buckets`) AND every generic node in docs/graph/gaia.json (243 under
`.skills`), assert the canonical authority against a direct ground-truth
computation of the SYNTHESIS rule:

    taxonomy.resolveDisplayBranch(...)      # the new authority (Python)
    synthesisBranch(...)                    # ground truth (this test, inline)

PR3b DELETED the two legacy resolvers this oracle used to cross-check against
(trustMagnitude.computeBranch and the docs/js/skill-semantics.js harness). The
divergence-classification legs are gone with them; taxonomy.py is now the sole
authority and the resolver-independent synthesis check below is the primary
correctness oracle.

--------------------------------------------------------------------------------
SYNTHESIS RULE (founder ruling v2). Suite-presence decides branch FIRST (no rank
gate); rank only splits the no-suite case:

    suiteComponents present        -> 'suite'    (ANY rank 1..6)
    no suiteComponents, rank 1..3  -> 'standard'
    no suiteComponents, rank 4..6  -> 'unique'

Canonical == synthesis on ALL entries (test_synthesis_ground_truth) — that is
the primary, resolver-independent correctness check.

The two handover-pinned Class-A nodes (fusion rank>=4, no suiteComponents ->
'unique') are kept as an explicit anchor in test_pinned_divergence_is_unique.
--------------------------------------------------------------------------------

Run: PYTHONIOENCODING=utf-8 PYTHONPATH=./src python -m pytest tests/test_taxonomy_contract.py -q
"""

import json
import os

import pytest

from gaia_cli import taxonomy


REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
GAIA_JSON = os.path.join(REPO_ROOT, "docs", "graph", "gaia.json")
NAMED_INDEX = os.path.join(REPO_ROOT, "docs", "graph", "named", "index.json")

# The two handover-named Class-A nodes, kept as an explicit anchor. Under the
# synthesis rule these are 'unique' (fusion rank>=4, no suiteComponents).
PINNED_UNIQUE_NODES = {
    "firecrawl/firecrawl-build-scrape",
    "obra/subagent-driven-development",
}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def loadJson(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def collectEntries():
    """Yield (id, node, effRankStr) for every oracle subject.

    effRankStr is the effective star level fed to EVERY resolver so the
    comparison is apples-to-apples:
      - named variants: their own `level`
      - generic gaia.json nodes: `namedMaxLevel` (highest named form; generics
        have no `level` and carry no suiteComponents)
    """
    entries = []

    named = loadJson(NAMED_INDEX)
    for genericSlug, variants in named.get("buckets", {}).items():
        for v in variants:
            entries.append((v.get("id"), v, v.get("level")))

    gaia = loadJson(GAIA_JSON)
    for node in gaia.get("skills", []):
        entries.append((node.get("id"), node, node.get("namedMaxLevel")))

    return entries


ENTRIES = collectEntries()


# ---------------------------------------------------------------------------
# Ground-truth synthesis rule (inline — independent of the module under test)
# ---------------------------------------------------------------------------

def synthesisBranch(node, effRank):
    """Direct implementation of the SYNTHESIS rule — the resolver-independent
    ground truth the authority must match on every entry."""
    rank = taxonomy.levelNum(effRank)
    hasSuite = taxonomy.suiteComponentsPresent(node)
    if hasSuite:
        return "suite"
    if rank >= 4:
        return "unique"
    return "standard"


# ---------------------------------------------------------------------------
# Resolver adapters — feed the SAME joined effRank to each resolver
# ---------------------------------------------------------------------------

def canonicalBranch(node, effRank):
    """taxonomy authority. Overlay the joined effRank via a `rank` field so
    normalize() uses the same effective rank (generics have no `level`)."""
    return taxonomy.resolveDisplayBranch(taxonomy.normalize({**node, "rank": effRank}))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_oracle_has_subjects():
    # Sanity: the corpus is non-trivial (handover: ~228 variants + 243 nodes).
    assert len(ENTRIES) >= 400, len(ENTRIES)


def test_synthesis_ground_truth():
    """PRIMARY CHECK: canonical == synthesis rule on EVERY entry (resolver-
    independent). A mismatch means the authority drifted from founder ruling v2."""
    mismatches = []
    for sid, node, effRank in ENTRIES:
        c = canonicalBranch(node, effRank)
        s = synthesisBranch(node, effRank)
        if c != s:
            mismatches.append((sid, c, s))
    assert not mismatches, f"canonical vs synthesis mismatches: {mismatches}"


def test_pinned_divergence_is_unique_canonically():
    """The two handover-pinned Class-A nodes resolve to 'unique' under canonical
    + synthesis (fusion rank>=4, no suiteComponents)."""
    byId = {sid: (node, effRank) for sid, node, effRank in ENTRIES}
    for sid in PINNED_UNIQUE_NODES:
        assert sid in byId, f"pinned node {sid} not found in corpus"
        node, effRank = byId[sid]
        assert canonicalBranch(node, effRank) == "unique", sid
        assert synthesisBranch(node, effRank) == "unique", sid


def test_no_banned_words_emitted_across_corpus():
    """Every entry's resolved rankLabel across the corpus is free of banned
    vocabulary ('Transcendent', 'Hardened')."""
    banned = ("Transcendent", "Hardened")
    for sid, node, effRank in ENTRIES:
        branch = canonicalBranch(node, effRank)
        label = taxonomy.rankLabel(effRank, branch)
        for bad in banned:
            assert bad not in label, (sid, label)


# ---------------------------------------------------------------------------
# PR2: named-index emitted shape assertions
# ---------------------------------------------------------------------------

NAMED_SKILLS_JSON = os.path.join(REPO_ROOT, "registry", "named-skills.json")

VALID_BRANCHES = {"suite", "standard", "unique"}
VALID_MEDALLIONS = {taxonomy.MEDALLION_SUITE, taxonomy.MEDALLION_STANDARD, taxonomy.MEDALLION_UNIQUE}


def test_named_index_emitted_taxonomy_shape():
    """Every entry in registry/named-skills.json carries the five emitted
    taxonomy fields with correct types and values (PR2 contract).

    Skipped when the file is absent (Class P — gitignored, not present in CI).
    """
    if not os.path.exists(NAMED_SKILLS_JSON):
        pytest.skip("registry/named-skills.json absent (Class P — run generateNamedIndex.py first)")

    with open(NAMED_SKILLS_JSON, encoding="utf-8") as f:
        index = json.load(f)

    entries = []
    for variants in index.get("buckets", {}).values():
        entries.extend(variants)

    assert entries, "named-skills.json has no entries in .buckets"

    for entry in entries:
        sid = entry.get("id", "<unknown>")
        assert "branch" in entry, f"{sid}: missing 'branch'"
        assert entry["branch"] in VALID_BRANCHES, (
            f"{sid}: branch {entry['branch']!r} not in {VALID_BRANCHES}"
        )
        assert "rank" in entry, f"{sid}: missing 'rank'"
        assert isinstance(entry["rank"], int), (
            f"{sid}: rank must be int, got {type(entry['rank']).__name__}"
        )
        assert 0 <= entry["rank"] <= 6, (
            f"{sid}: rank {entry['rank']} out of range 0–6"
        )
        assert "rankWord" in entry, f"{sid}: missing 'rankWord'"
        assert isinstance(entry["rankWord"], str) and entry["rankWord"], (
            f"{sid}: rankWord must be a non-empty string"
        )
        assert "medallion" in entry, f"{sid}: missing 'medallion'"
        assert entry["medallion"] in VALID_MEDALLIONS, (
            f"{sid}: medallion {entry['medallion']!r} not in {VALID_MEDALLIONS}"
        )
        assert "contractVersion" in entry, f"{sid}: missing 'contractVersion'"
        assert entry["contractVersion"] == "gaia-public-v1", (
            f"{sid}: contractVersion {entry['contractVersion']!r} != 'gaia-public-v1'"
        )


def test_named_index_has_suite_and_standard_entries():
    """At least one suite branch entry and one standard branch entry must exist
    (structural completeness check — the registry always has both)."""
    if not os.path.exists(NAMED_SKILLS_JSON):
        pytest.skip("registry/named-skills.json absent (Class P — run generateNamedIndex.py first)")

    with open(NAMED_SKILLS_JSON, encoding="utf-8") as f:
        index = json.load(f)

    branches_seen = set()
    for variants in index.get("buckets", {}).values():
        for entry in variants:
            if "branch" in entry:
                branches_seen.add(entry["branch"])

    assert "suite" in branches_seen, (
        "No 'suite' branch entry found — registry must contain at least one suite skill"
    )
    assert "standard" in branches_seen, (
        "No 'standard' branch entry found — registry must contain at least one standard skill"
    )
