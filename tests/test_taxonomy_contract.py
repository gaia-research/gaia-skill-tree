"""Contract completeness oracle for the Yggdrasil II taxonomy authority.

For every named-skill variant in docs/graph/named/index.json (~228 under
`.buckets`) AND every generic node in docs/graph/gaia.json (243 under
`.skills`), assert the canonical authority against a direct ground-truth
computation of the SYNTHESIS rule:

    taxonomy.resolveDisplayBranch(...)      # the new authority (Python)
    synthesisBranch(...)                    # ground truth (this test, inline)

BRANCH STATE (dev/ygg2-consume-frontend):
  - PRIMARY membership check with §7 stamp-honor: 79 generic nodes in
    docs/graph/gaia.json carry an origin-surfaced `branch` stamp; synthesisBranch
    honors the stamp directly (see §7 comment inline) — recomputing would wrongly
    classify them since bare generics carry no suiteComponents.
  - Python delete-gate SATISFIED: trustMagnitude.computeBranch has been DELETED
    on this branch. test_legacy_python_parity_delete_gate SKIPS — the §3
    handshake is done, the resolver is gone.
  - JS delete-gate OPEN (strict-xfail): docs/js/skill-semantics.js::computeBranch
    is still alive (7 refs). test_legacy_js_parity_delete_gate is strict-xfail;
    if the harness file is present + node is available it XFAILS (RED-by-design);
    if the harness is missing or node unavailable it SKIPS.

--------------------------------------------------------------------------------
SYNTHESIS RULE (founder ruling v2). Suite-presence decides branch FIRST (no rank
gate); rank only splits the no-suite case:

    suiteComponents present        -> 'suite'    (ANY rank 1..6)
    no suiteComponents, rank 1..3  -> 'standard'
    no suiteComponents, rank 4..6  -> 'unique'

§7 ORIGIN MECHANIC: a stamped `branch` field on a generic gaia.json node
supersedes recomputation. The stamp is authoritative for starless generics that
carry no suiteComponents of their own (those live on the named origin entry).
Honoring the stamp avoids false standard/unique classifications on 79 nodes.

Canonical == synthesis on ALL entries (test_synthesis_ground_truth) — that is
the primary, resolver-independent correctness check.

The two handover-pinned Class-A nodes (fusion rank>=4, no suiteComponents ->
'unique') are kept as an explicit anchor in test_pinned_divergence_is_unique_canonically.
--------------------------------------------------------------------------------

Run: PYTHONIOENCODING=utf-8 PYTHONPATH=./src python -m pytest tests/test_taxonomy_contract.py -q
"""

import json
import os
import shutil
import subprocess

import pytest

from gaia_cli import taxonomy

# ---------------------------------------------------------------------------
# Defensive import: Python resolver #3 (trustMagnitude.computeBranch) is
# DELETED on this branch. Attempt import so the module-level flag reflects
# reality without killing collection with ImportError.
# ---------------------------------------------------------------------------
try:
    from gaia_cli import trustMagnitude as _trustMagnitude
    PYTHON_RESOLVER_PRESENT = hasattr(_trustMagnitude, "computeBranch")
except (ImportError, AttributeError):
    _trustMagnitude = None
    PYTHON_RESOLVER_PRESENT = False


REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
GAIA_JSON = os.path.join(REPO_ROOT, "docs", "graph", "gaia.json")
NAMED_INDEX = os.path.join(REPO_ROOT, "docs", "graph", "named", "index.json")
HARNESS = os.path.join(os.path.dirname(__file__), "harness", "js_branch_dump.js")

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
    ground truth the authority must match on every entry.

    Per authority doc §7 origin mechanic: a generic node in docs/graph/gaia.json
    may carry a STAMPED branch field surfaced from its bucket's origin. Honor the
    stamp directly — do not recompute — because bare generics carry no
    suiteComponents (those live on the named origin entry) and recomputing would
    wrongly yield 'standard'/'unique' where the stamp says 'suite'. This mirrors
    what taxonomy.normalize()/resolveDisplayBranch already does (pre-resolved
    branch passthrough). On this branch 79 nodes are stamped, making this
    load-bearing (without it test_synthesis_ground_truth fails on all 79).
    """
    # §7: honor a stamped branch field if present and valid — return it directly.
    stamped = node.get("branch") if isinstance(node, dict) else None
    if stamped in {"standard", "suite", "unique"}:
        return stamped

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
# JS leg — batch-shell the harness once
# ---------------------------------------------------------------------------

def runJsHarness(entries):
    """Return {id: branch} from the JS computeBranch resolver, or None if node
    is unavailable / harness file missing / harness fails.

    Returns None when:
      - node binary is not on PATH
      - HARNESS file does not exist (tests/harness/js_branch_dump.js missing)
      - harness exits non-zero
      - harness stdout is not valid JSON
    The JS delete-gate test skips when this returns None.
    """
    if shutil.which("node") is None:
        return None
    if not os.path.exists(HARNESS):
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
    independent). A mismatch means the authority drifted from founder ruling v2.

    §7 stamp-honor in synthesisBranch is load-bearing here: 79 generic nodes in
    docs/graph/gaia.json carry stamped branch values that would mismatch without
    it (bare generics have no suiteComponents so recomputing yields standard/unique
    rather than the stamped value)."""
    mismatches = []
    for sid, node, effRank in ENTRIES:
        c = canonicalBranch(node, effRank)
        s = synthesisBranch(node, effRank)
        if c != s:
            mismatches.append((sid, c, s))
    assert not mismatches, f"canonical vs synthesis mismatches: {mismatches}"


@pytest.mark.skipif(
    not PYTHON_RESOLVER_PRESENT,
    reason="Python resolver #3 (trustMagnitude.computeBranch) deleted — delete-gate satisfied on this branch",
)
def test_legacy_python_parity_delete_gate():
    """Canonical (membership) == legacy Python #3 on EVERY entry.

    DELETE-GATE SATISFIED (authority doc §3): trustMagnitude.computeBranch has
    been DELETED on this branch (dev/ygg2-consume-frontend). This test SKIPS
    because PYTHON_RESOLVER_PRESENT is False — the resolver is gone, which IS
    the terminal state of the §3 handshake. The skip here is correct and
    intentional; do NOT hand-edit to force-pass or add an xfail.

    If somehow the resolver is present (e.g. the branch is rebased onto a
    version that restored it), the test body runs and asserts real parity.
    """
    mismatches = []
    for sid, node, effRank in ENTRIES:
        c = canonicalBranch(node, effRank)
        p = _trustMagnitude.computeBranch({**node, "level": effRank})
        if c != p:
            mismatches.append((sid, c, p))
    assert not mismatches, f"legacy Python #3 parity broke: {mismatches}"


@pytest.mark.skipif(
    JS_BRANCHES is None,
    reason="node/harness unavailable — JS delete-gate cannot execute; JS resolver still alive",
)
@pytest.mark.xfail(
    strict=True,
    reason=(
        "DELETE-GATE §3: JS computeBranch (docs/js/skill-semantics.js) is still alive "
        "and divergent from the canonical membership authority on Class-A nodes. "
        "RED-by-design; this gate flips to hard failure forcing marker removal "
        "once the JS resolver is deleted/collapsed in the frontend consume phase."
    ),
)
def test_legacy_js_parity_delete_gate():
    """Canonical (membership) == legacy JS #1 on EVERY entry. XFAILS now (by
    design); passes only after the JS computeBranch resolver is deleted.

    When the harness file (tests/harness/js_branch_dump.js) is absent or node
    is unavailable, this test SKIPS — the JS delete-gate is open but cannot
    execute. The skip is correct while the harness is missing."""
    mismatches = []
    for sid, node, effRank in ENTRIES:
        c = canonicalBranch(node, effRank)
        j = JS_BRANCHES.get(sid)
        if j is not None and c != j:
            mismatches.append((sid, c, j))
    assert not mismatches, f"legacy JS #1 parity not yet real: {mismatches}"


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
