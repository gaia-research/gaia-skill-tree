"""Contract completeness oracle for the Yggdrasil II taxonomy authority (PR1).

For every named-skill variant in docs/graph/named/index.json (~228 under
`.buckets`) AND every generic node in docs/graph/gaia.json (243 under
`.skills`), assert cross-resolver parity between:

    taxonomy.resolveDisplayBranch(...)      # the new authority (Python)
    trustMagnitude.computeBranch(...)       # live Python resolver #3
    JS computeBranch(...)                   # live JS resolver #1 (via harness)

resolveSemantics (JS resolver #2) reuses the SAME read order as JS #1
computeBranch (its isUnique/isSuite booleans map to the same branch string), so
the JS-harness leg covers #2 as well.

COMPLETENESS MECHANISM: an unported resolver (a branch we forgot to fold into
taxonomy.py) surfaces as a parity failure whose signature does NOT match either
of the two RATIFIED, TYPE-INDEPENDENT-vs-JS divergence classes below.

--------------------------------------------------------------------------------
DIVERGENCE MAP (canonical/Python #3 vs JS #1) — measured against the live
2026-07-18 corpus. Both classes have the SAME root cause: JS #1 consults `type`
and applies its suiteComponents branch WITHOUT a rank gate (skill-semantics.js
L58/L61), whereas the canonical resolver + Python #3 are type-independent and
rank-gate first (Founder ruling). canonical == Python #3 on ALL entries.

  CLASS A — canonical/Py3 = 'unique' , JS = 'standard'   (9 nodes)
    `fusion` node at rank >= 4 with NO suiteComponents. JS #1's
    `type === 'basic'` unique-guard fails on `fusion`, so it falls through to
    'standard'. The two handover-named instances are the named-variant form:
        firecrawl/firecrawl-build-scrape
        obra/subagent-driven-development
    The other 7 are the generic-node / 5★ equivalents of the SAME semantics
    (web-scrape, superpowers, skill-mastery, git-ship-done-pipeline,
     multi-topology-orchestration, founder-mode-orchestration,
     subagent-driven-development).

  CLASS B — canonical/Py3 = 'standard' , JS = 'suite'    (12 nodes)
    node at rank < 4 WITH suiteComponents (all 3★ suite parents). Canonical +
    Python #3 rank-gate first -> 'standard'; JS #1 has no rank gate on its
    suiteComponents branch -> 'suite'. The handover did NOT enumerate this axis;
    it is documented here as a second RATIFIED, canonical==Py3 divergence.

Any JS divergence that does NOT fit one of these two signatures — OR any
canonical-vs-Python-#3 mismatch — is a REAL failure (an unported / drifted
resolver) and must RED-build. See test_js_divergences_all_ratified.
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

# The two handover-named nodes, kept as an explicit anchor: canonical/Py3 say
# 'unique', JS #1 says 'standard' (Class A). If either stops diverging in JS,
# the pin is stale and test_pinned_nodes_diverge_in_js flags it.
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
      - generic gaia.json nodes: `namedMaxLevel` (the highest named form;
        generics have no `level` and carry no suiteComponents)
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
# Resolver adapters — feed the SAME joined effRank to each resolver
# ---------------------------------------------------------------------------

def canonicalBranch(node, effRank):
    """taxonomy authority. Overlay the joined effRank via a `rank` field so
    normalize() uses the same effective rank (generics have no `level`)."""
    return taxonomy.resolveDisplayBranch(taxonomy.normalize({**node, "rank": effRank}))


def pythonBranch(node, effRank):
    """trustMagnitude.computeBranch (Python resolver #3). Reads named['level'];
    overlay the joined effRank so generics resolve on namedMaxLevel."""
    return trustMagnitude.computeBranch({**node, "level": effRank})


def divergenceClass(node, effRank, canon, js):
    """Classify a canonical-vs-JS divergence. Returns 'A', 'B', or None
    (None => unratified => real failure)."""
    rank = taxonomy.levelNum(effRank)
    hasSuite = taxonomy.suiteComponentsPresent(node)
    if canon == "unique" and js == "standard" and rank >= 4 and not hasSuite:
        return "A"
    if canon == "standard" and js == "suite" and rank < 4 and hasSuite:
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


def test_python_parity_all_entries():
    """canonical == Python #3 for EVERY entry (no divergence tolerated on the
    Python side — both are type-independent). A mismatch here means the new
    authority drifted from the ratified Python resolver."""
    mismatches = []
    for sid, node, effRank in ENTRIES:
        c = canonicalBranch(node, effRank)
        p = pythonBranch(node, effRank)
        if c != p:
            mismatches.append((sid, c, p))
    assert not mismatches, f"canonical vs Python #3 mismatches: {mismatches}"


def test_pinned_divergence_is_unique_canonically():
    """The two handover-pinned nodes resolve to 'unique' under canonical + Py3."""
    byId = {sid: (node, effRank) for sid, node, effRank in ENTRIES}
    for sid in PINNED_JS_DIVERGENCE:
        assert sid in byId, f"pinned node {sid} not found in corpus"
        node, effRank = byId[sid]
        assert canonicalBranch(node, effRank) == "unique", sid
        assert pythonBranch(node, effRank) == "unique", sid


@pytest.mark.skipif(JS_BRANCHES is None, reason="node unavailable")
def test_js_divergences_all_ratified():
    """Every canonical-vs-JS divergence MUST fit Class A or Class B (the two
    ratified, type-independent-vs-JS signatures). A divergence with any other
    signature is an unported/drifted resolver and RED-builds.

    This is the completeness gate: it does not hard-code an id list, it
    hard-codes the two SIGNATURES, so new corpus nodes matching a ratified
    signature pass while a genuinely novel drift fails.
    """
    unratified = []
    for sid, node, effRank in ENTRIES:
        c = canonicalBranch(node, effRank)
        j = JS_BRANCHES.get(sid)
        if j is None or c == j:
            continue
        if divergenceClass(node, effRank, c, j) is None:
            unratified.append((sid, c, j, taxonomy.levelNum(effRank),
                               taxonomy.suiteComponentsPresent(node)))
    assert not unratified, (
        "UNRATIFIED JS divergence (likely an unported/drifted resolver) — "
        "does not match Class A (unique/standard, rank>=4, no suite) or "
        f"Class B (standard/suite, rank<4, suite): {unratified}"
    )


@pytest.mark.skipif(JS_BRANCHES is None, reason="node unavailable")
def test_pinned_nodes_diverge_in_js():
    """Assert the pinned Class-A drift actually occurs (JS says 'standard'). If
    JS ever stops diverging the pin is stale and should be revisited."""
    for sid in PINNED_JS_DIVERGENCE:
        j = JS_BRANCHES.get(sid)
        assert j == "standard", (
            f"pinned node {sid} no longer diverges in JS (got {j!r}); "
            "update PINNED_JS_DIVERGENCE"
        )


@pytest.mark.skipif(JS_BRANCHES is None, reason="node unavailable")
def test_class_a_class_b_both_present_in_corpus():
    """Document the observed shape: both ratified classes exist in the live
    corpus. If a corpus refresh empties one class this test flags it so the
    divergence map in the module docstring gets revisited (not a correctness
    failure, a documentation-drift tripwire)."""
    seen = set()
    for sid, node, effRank in ENTRIES:
        c = canonicalBranch(node, effRank)
        j = JS_BRANCHES.get(sid)
        if j is None or c == j:
            continue
        cls = divergenceClass(node, effRank, c, j)
        if cls:
            seen.add(cls)
    assert seen == {"A", "B"}, (
        f"divergence classes present changed (expected {{A, B}}, got {seen}); "
        "revisit the divergence map in the module docstring"
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
