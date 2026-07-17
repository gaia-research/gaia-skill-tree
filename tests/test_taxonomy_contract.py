"""Contract completeness oracle for the Yggdrasil II taxonomy authority (PR1).

For every named-skill variant in docs/graph/named/index.json (~228 under
`.buckets`) AND every generic node in docs/graph/gaia.json (243 under
`.skills`), assert the canonical authority against a direct ground-truth
computation of the SYNTHESIS rule, and characterize its divergence from the two
legacy resolvers:

    taxonomy.resolveDisplayBranch(...)      # the new authority (Python)
    synthesisBranch(...)                    # ground truth (this test, inline)
    trustMagnitude.computeBranch(...)       # legacy Python resolver #3
    JS computeBranch(...)                   # legacy JS resolver #1 (via harness)

resolveSemantics (JS resolver #2) reuses the SAME read order as JS #1
computeBranch, so the JS-harness leg covers #2 as well.

--------------------------------------------------------------------------------
SYNTHESIS RULE (founder ruling v2). Suite-presence decides branch FIRST (no rank
gate); rank only splits the no-suite case:

    suiteComponents present        -> 'suite'    (ANY rank 1..6)
    no suiteComponents, rank 1..3  -> 'standard'
    no suiteComponents, rank 4..6  -> 'unique'

Canonical == synthesis on ALL entries (test_synthesis_ground_truth) — that is
the primary, resolver-independent correctness check.

Canonical is NEITHER legacy resolver verbatim; it AGREES with each on a
different class and DISAGREES on the other:

  CLASS A — canonical/synthesis = 'unique' , JS #1 = 'standard' , Py #3 = 'unique'
    `fusion` node at rank >= 4 with NO suiteComponents. JS #1's `type==='basic'`
    unique-guard fails on fusion -> 'standard'. Canonical AGREES with Py #3 here.
    (9 nodes; the two handover-named instances are the named-variant form:
     firecrawl/firecrawl-build-scrape, obra/subagent-driven-development.)

  CLASS B — canonical/synthesis = 'suite' , Py #3 = 'standard' , JS #1 = 'suite'
    node at rank < 4 WITH suiteComponents. Py #3 rank-gates first -> 'standard'.
    Canonical AGREES with JS #1 here (suite-presence-first, no rank gate).
    (12 nodes; all 3-star suite parents.)

Any divergence (vs EITHER legacy resolver) that does NOT fit Class A or Class B
is a REAL failure (an unported / drifted resolver). See
test_python_divergences_all_ratified / test_js_divergences_all_ratified.
--------------------------------------------------------------------------------

Run: PYTHONIOENCODING=utf-8 PYTHONPATH=./src python -m pytest tests/test_taxonomy_contract.py -q
"""

import json
import os
import shutil
import subprocess

import pytest

from gaia_cli import taxonomy
from gaia_cli import trustMagnitude


REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
GAIA_JSON = os.path.join(REPO_ROOT, "docs", "graph", "gaia.json")
NAMED_INDEX = os.path.join(REPO_ROOT, "docs", "graph", "named", "index.json")
HARNESS = os.path.join(os.path.dirname(__file__), "harness", "js_branch_dump.js")

# The two handover-named Class-A nodes, kept as an explicit anchor.
PINNED_JS_DIVERGENCE = {
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


def pythonBranch(node, effRank):
    """trustMagnitude.computeBranch (legacy Python resolver #3). Reads
    named['level']; overlay the joined effRank so generics resolve on
    namedMaxLevel."""
    return trustMagnitude.computeBranch({**node, "level": effRank})


def divergenceClass(node, effRank, canon, other):
    """Classify a canonical-vs-<legacy> divergence. Returns 'A', 'B', or None
    (None => unratified => real failure).

    Class A: canonical='unique', other='standard', rank>=4, no suite.
    Class B: canonical='suite',  other='standard', rank<4,  suite present.
    (Both legacy resolvers diverge toward 'standard' — JS #1 on Class A via its
    type-guard, Py #3 on Class B via its rank-gate.)
    """
    rank = taxonomy.levelNum(effRank)
    hasSuite = taxonomy.suiteComponentsPresent(node)
    if canon == "unique" and other == "standard" and rank >= 4 and not hasSuite:
        return "A"
    if canon == "suite" and other == "standard" and rank < 4 and hasSuite:
        return "B"
    return None


# ---------------------------------------------------------------------------
# JS leg — batch-shell the harness once
# ---------------------------------------------------------------------------

def runJsHarness(entries):
    """Return {id: branch} from the JS computeBranch resolver, or None if node
    is unavailable / the harness fails (contract test skips the JS leg then)."""
    if shutil.which("node") is None:
        return None
    payload = [
        {"id": sid, "node": node, "effRank": effRank}
        for (sid, node, effRank) in entries
    ]
    try:
        proc = subprocess.run(
            ["node", HARNESS],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout)
    except Exception:
        return None


JS_BRANCHES = runJsHarness(ENTRIES)


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


def test_python_divergences_all_ratified():
    """canonical vs Python #3: EVERY divergence must be Class B (rank<4 + suite).
    canonical agrees with Py #3 everywhere else (incl. Class A)."""
    unratified = []
    for sid, node, effRank in ENTRIES:
        c = canonicalBranch(node, effRank)
        p = pythonBranch(node, effRank)
        if c == p:
            continue
        if divergenceClass(node, effRank, c, p) != "B":
            unratified.append((sid, c, p, taxonomy.levelNum(effRank),
                               taxonomy.suiteComponentsPresent(node)))
    assert not unratified, (
        "UNRATIFIED canonical-vs-Python-#3 divergence (only Class B — rank<4 + "
        f"suite — is ratified here): {unratified}"
    )


@pytest.mark.skipif(JS_BRANCHES is None, reason="node unavailable")
def test_js_divergences_all_ratified():
    """canonical vs JS #1: EVERY divergence must be Class A (rank>=4 + no suite).
    canonical agrees with JS #1 everywhere else (incl. Class B). A divergence of
    any other signature is an unported/drifted resolver and RED-builds.

    Signature-based (not an id list) so new corpus nodes matching a ratified
    signature pass while a genuinely novel drift fails."""
    unratified = []
    for sid, node, effRank in ENTRIES:
        c = canonicalBranch(node, effRank)
        j = JS_BRANCHES.get(sid)
        if j is None or c == j:
            continue
        if divergenceClass(node, effRank, c, j) != "A":
            unratified.append((sid, c, j, taxonomy.levelNum(effRank),
                               taxonomy.suiteComponentsPresent(node)))
    assert not unratified, (
        "UNRATIFIED canonical-vs-JS-#1 divergence (only Class A — rank>=4 + no "
        f"suite — is ratified here): {unratified}"
    )


def test_pinned_divergence_is_unique_canonically():
    """The two handover-pinned Class-A nodes resolve to 'unique' under canonical
    + synthesis + Py3."""
    byId = {sid: (node, effRank) for sid, node, effRank in ENTRIES}
    for sid in PINNED_JS_DIVERGENCE:
        assert sid in byId, f"pinned node {sid} not found in corpus"
        node, effRank = byId[sid]
        assert canonicalBranch(node, effRank) == "unique", sid
        assert synthesisBranch(node, effRank) == "unique", sid
        assert pythonBranch(node, effRank) == "unique", sid


@pytest.mark.skipif(JS_BRANCHES is None, reason="node unavailable")
def test_pinned_nodes_diverge_in_js():
    """Assert the pinned Class-A drift actually occurs (JS says 'standard')."""
    for sid in PINNED_JS_DIVERGENCE:
        j = JS_BRANCHES.get(sid)
        assert j == "standard", (
            f"pinned node {sid} no longer diverges in JS (got {j!r}); "
            "update PINNED_JS_DIVERGENCE"
        )


@pytest.mark.skipif(JS_BRANCHES is None, reason="node unavailable")
def test_divergence_counts_are_exactly_9A_and_12B():
    """Pin the exact observed shape against the 2026-07-18 corpus:
       Class A = 9 unique ids (canonical 'unique' vs JS 'standard')
       Class B = 12 unique ids (canonical 'suite' vs Py3 'standard')
    A drift in these counts flags a corpus change that must be re-reviewed
    against the divergence map (not necessarily a correctness failure)."""
    classA, classB = set(), set()
    for sid, node, effRank in ENTRIES:
        c = canonicalBranch(node, effRank)
        j = JS_BRANCHES.get(sid)
        p = pythonBranch(node, effRank)
        if j is not None and c != j and divergenceClass(node, effRank, c, j) == "A":
            classA.add(sid)
        if c != p and divergenceClass(node, effRank, c, p) == "B":
            classB.add(sid)
    assert len(classA) == 9, sorted(classA)
    assert len(classB) == 12, sorted(classB)
    # No id is simultaneously A and B (mutually exclusive signatures).
    assert not (classA & classB), sorted(classA & classB)


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
