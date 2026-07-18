"""Contract completeness oracle for the Yggdrasil II taxonomy authority (PR1).

For every named-skill variant in docs/graph/named/index.json (~228 under
`.buckets`) AND every generic node in docs/graph/gaia.json (243 under
`.skills`), assert the canonical authority against a direct ground-truth
computation of the SYNTHESIS rule, and track parity with the two legacy
resolvers:

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

DELETE-GATE DISCIPLINE (§2.5): legacy resolvers #1 and #3 are known to diverge
from the membership authority on ~9 nodes (JS #1, type-gated fusion guard) and
~12 nodes (Py #3, rank-gated suite check). This drift is NOT blessed or
ratified — it is RED-by-design. test_four_way_parity_pending_deletion is a
strict-xfail that must stay xfail until Phase 3 DELETES the legacy resolvers and
parity actually holds. The moment it flips to XPASS, CI hard-fails, forcing
removal of the marker. That handshake IS the delete-gate.
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


@pytest.mark.xfail(strict=True, reason=(
    "known Ygg-I-vs-membership drift in legacy resolvers #1 (JS computeBranch, "
    "type-gated) and #3 (trustMagnitude.computeBranch); resolved by DELETION in "
    "Phase 3. Strict-xfail is the delete-gate handshake: the day Phase 3 deletes "
    "the legacy resolvers and parity holds, this flips XPASS -> hard failure, "
    "forcing the marker's removal."
))
def test_four_way_parity_pending_deletion():
    """RED-by-design: authority == legacy #1 == legacy #3 on every node.
    Fails until Phase 3 deletes the drifted legacy resolvers (delete-gate)."""
    jsBranches = runJsHarness(ENTRIES)  # {id: branch} or None-per-node if harness unavailable
    mismatches = []
    for sid, node, effRank in ENTRIES:
        c = canonicalBranch(node, effRank)
        p = pythonBranch(node, effRank)
        j = jsBranches.get(sid) if jsBranches else None
        if c != p or (j is not None and c != j):
            mismatches.append((sid, c, p, j))
    assert not mismatches, f"drift (canonical, py#3, js#1): {mismatches}"


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


def test_no_banned_words_emitted_across_corpus():
    """Every entry's resolved rankLabel across the corpus is free of banned
    vocabulary ('Transcendent', 'Hardened')."""
    banned = ("Transcendent", "Hardened")
    for sid, node, effRank in ENTRIES:
        branch = canonicalBranch(node, effRank)
        label = taxonomy.rankLabel(effRank, branch)
        for bad in banned:
            assert bad not in label, (sid, label)
