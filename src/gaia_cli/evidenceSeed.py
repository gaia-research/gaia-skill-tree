"""Evidence-seed emitter (RFC2 Gap C, §3.4 / #1148 §2 "Intake handoff").

Materializes an L4-approved intake's raw source rows into the evidence-seed —
the seam the #1148 evidence bridge consumes. Emission is a DUAL WRITE:

(a) A standalone seed artifact **partitioned by evidence type** under
    ``evidence/seeds/<skill-id>/<claimedEvidenceType>.jsonl``. Each line is one
    JSON row ``{skillId, sourceUrl, claimedEvidenceType, attributionScope}`` —
    the exact #1148 §2 shape for §1's future reader. This is the canonical seed.

(b) The same sources appended into the existing
    ``evidence/collectors/{technical,social}/<file>.md`` channel files in the
    block format ``evidence/scripts/compile_data_lake.py`` reads, so today's
    compiler (ev-collection Phase 1) picks them up without waiting on the #1148
    §1/§3/§4 lake-script rewrite (out of scope, per RFC2 §6).

Invariants (RFC2 locked decisions):

- **Raw sources only.** No authoritative star / tier / grade / class is carried;
  Trust Magnitude and rank are derived canonically at appraisal time.
- **A suite-wide source is NOT copied as full-strength proof for every
  component.** It is emitted ONCE at ``suite-wide`` scope; components reference
  it (a lightweight ``suite-wide`` reference row) rather than duplicating the
  full-strength source. (Firecrawl learning: suite-wide repo adoption != per-
  endpoint proof.)
"""

from __future__ import annotations

import json
import os


# The evidence-seed claimedEvidenceType vocabulary == meta.json evidence.types
# ids. (Distinct from the intake YAML evidence 'type' enum, which is bridged in
# intakeAdapter.py.)
SEED_EVIDENCE_TYPES = (
    "repo-own",
    "github-stars-own",
    "social-signal",
    "benchmark-result",
    "arxiv",
    "peer-review",
    "proxy-containment",
    "verifier-attestation",
    "fusion-recipe",
    "self-attestation",
)

VALID_ATTRIBUTION_SCOPES = ("standalone", "suite-component", "suite-wide")

# Keys that would smuggle an authoritative strength claim into the seed. The
# seed is raw sources only; these are rejected at build time.
FORBIDDEN_STRENGTH_KEYS = ("star", "stars", "tier", "grade", "class", "trustnumber")

# Map each claimedEvidenceType to the collector channel file the compiler reads
# (evidence/scripts/compile_data_lake.py::parseCollectorFiles). Value is
# (relativePath, headerMarker) where headerMarker is the split token the
# compiler uses for that file's blocks.
COLLECTOR_CHANNELS = {
    "benchmark-result": ("technical/benchmark_results.md", "### "),
    "arxiv": ("technical/academic_papers.md", "### "),
    "peer-review": ("technical/peer_reviews_audits.md", "## "),
    "social-signal": ("social/blogs_newsletters.md", "### "),
    # Repo / verification / composition types have no dedicated compiler reader
    # beyond the tier files; route them into the technical channel so ev-
    # collection's manual scan (ev-collection SKILL Step 1) still surfaces them.
    "repo-own": ("technical/benchmark_results.md", "### "),
    "github-stars-own": ("technical/benchmark_results.md", "### "),
    "proxy-containment": ("technical/benchmark_results.md", "### "),
    "verifier-attestation": ("technical/peer_reviews_audits.md", "## "),
    "fusion-recipe": ("technical/benchmark_results.md", "### "),
    "self-attestation": ("social/blogs_newsletters.md", "### "),
}


def _assertNoStrengthKeys(source):
    """Reject any raw source dict carrying an authoritative strength claim."""
    for key in source:
        if key.lower() in FORBIDDEN_STRENGTH_KEYS:
            raise ValueError(
                f"evidence-seed source carries forbidden strength key {key!r} — "
                "the seed is raw sources only; TM/rank are derived at appraisal"
            )


def buildSeedRow(skillId, sourceUrl, claimedEvidenceType, attributionScope):
    """Build a single evidence-seed row (the #1148 §2 shape).

    Validates the type/scope vocabularies and returns the row dict. Raises
    ValueError on an unknown evidence type or attribution scope.
    """
    if claimedEvidenceType not in SEED_EVIDENCE_TYPES:
        raise ValueError(
            f"unknown claimedEvidenceType {claimedEvidenceType!r} "
            f"(valid: {sorted(SEED_EVIDENCE_TYPES)})"
        )
    if attributionScope not in VALID_ATTRIBUTION_SCOPES:
        raise ValueError(
            f"unknown attributionScope {attributionScope!r} "
            f"(valid: {list(VALID_ATTRIBUTION_SCOPES)})"
        )
    return {
        "skillId": skillId,
        "sourceUrl": sourceUrl,
        "claimedEvidenceType": claimedEvidenceType,
        "attributionScope": attributionScope,
    }


def partitionByType(rows):
    """Group seed rows by ``claimedEvidenceType``.

    Returns an ordered dict-like plain dict ``{evidenceType: [row, ...]}``,
    preserving first-seen order within each type. This is the partitioning the
    standalone artifact and the #1148 §1 reader key on.
    """
    partitions = {}
    for row in rows:
        partitions.setdefault(row["claimedEvidenceType"], []).append(row)
    return partitions


def _dedupeSuiteWide(rows):
    """Enforce: a suite-wide source is NOT copied full-strength per component.

    A ``suite-wide`` source (same sourceUrl + type) is emitted ONCE. Any
    additional row for the SAME (sourceUrl, claimedEvidenceType) that is scoped
    ``suite-component`` is collapsed to a single lightweight reference — the
    component points at the suite-wide source rather than duplicating it as
    full-strength proof. Returns the filtered row list.
    """
    suiteWideKeys = {
        (r["sourceUrl"], r["claimedEvidenceType"])
        for r in rows
        if r["attributionScope"] == "suite-wide"
    }
    out = []
    seenComponentRefs = set()
    for row in rows:
        key = (row["sourceUrl"], row["claimedEvidenceType"])
        if (
            row["attributionScope"] == "suite-component"
            and key in suiteWideKeys
        ):
            # This component is trying to claim a suite-wide source. Do not copy
            # it as full-strength proof; emit at most one reference row.
            if key in seenComponentRefs:
                continue
            seenComponentRefs.add(key)
            refRow = dict(row)
            refRow["attributionScope"] = "suite-wide"
            refRow["reference"] = True  # a pointer, not full-strength proof
            out.append(refRow)
        else:
            out.append(row)
    return out


def buildSeedRows(skillId, sources, attributionScope="standalone"):
    """Build seed rows for one skill from its raw ``sources``.

    ``sources`` is an iterable of dicts, each ``{url, type}`` (optionally
    ``scope`` to override the per-skill ``attributionScope``). No authoritative
    strength keys are permitted on a source (raw sources only).

    Returns the list of seed rows (suite-wide dedup applied).
    """
    rows = []
    for source in sources:
        _assertNoStrengthKeys(source)
        scope = source.get("scope", attributionScope)
        rows.append(
            buildSeedRow(
                skillId,
                source["url"],
                source["type"],
                scope,
            )
        )
    return _dedupeSuiteWide(rows)


def seedsDir(evidenceRoot="evidence"):
    """Return the evidence-seed output dir (``evidence/seeds/``)."""
    return os.path.join(evidenceRoot, "seeds")


def writeSeedArtifact(skillId, rows, evidenceRoot="evidence"):
    """Write the standalone seed artifact partitioned by type.

    Layout: ``evidence/seeds/<skill-id>/<claimedEvidenceType>.jsonl`` — one JSON
    row per line. Returns the list of file paths written.
    """
    outDir = os.path.join(seedsDir(evidenceRoot), skillId)
    os.makedirs(outDir, exist_ok=True)
    written = []
    for evType, typeRows in partitionByType(rows).items():
        outPath = os.path.join(outDir, f"{evType}.jsonl")
        with open(outPath, "w", encoding="utf-8") as f:
            for row in typeRows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        written.append(outPath)
    return written


def _collectorBlock(row, marker):
    """Render one seed row as a compiler-readable collector block.

    Uses the header ``marker`` the compiler splits on for that channel file, and
    embeds the skill id in the title so ``parseCollectorFiles`` associates the
    block with the skill. NOT pre-marked ``<!-- injected -->`` — the compiler
    adds that once it imports the row.
    """
    scopeNote = row["attributionScope"]
    if row.get("reference"):
        scopeNote += " (reference — not full-strength proof)"
    return (
        f"{marker}`{row['skillId']}` — {row['claimedEvidenceType']}\n"
        f"* **Skill:** `{row['skillId']}`\n"
        f"* **Source:** {row['sourceUrl']}\n"
        f"* **Claimed evidence type:** {row['claimedEvidenceType']}\n"
        f"* **Attribution scope:** {scopeNote}\n"
    )


def appendToCollectors(rows, evidenceRoot="evidence"):
    """Append seed rows into the existing collector channel files.

    Dual-write leg (b): materializes each row as a compiler-readable block in
    ``evidence/collectors/{technical,social}/<file>.md`` so ev-collection Phase 1
    picks them up today. Returns the set of collector paths touched.
    """
    collectorsDir = os.path.join(evidenceRoot, "collectors")
    touched = {}
    for row in rows:
        channel = COLLECTOR_CHANNELS.get(row["claimedEvidenceType"])
        if channel is None:
            continue
        relPath, marker = channel
        touched.setdefault((relPath, marker), []).append(row)

    written = set()
    for (relPath, marker), channelRows in touched.items():
        fullPath = os.path.normpath(os.path.join(collectorsDir, relPath))
        os.makedirs(os.path.dirname(fullPath), exist_ok=True)
        block = "\n".join(_collectorBlock(r, marker) for r in channelRows)
        # Append (never truncate — the loop is additive per RFC2 §3.5).
        with open(fullPath, "a", encoding="utf-8") as f:
            f.write("\n" + block + "\n")
        written.add(fullPath)
    return written


def emitEvidenceSeed(skillId, sources, attributionScope="standalone",
                     evidenceRoot="evidence", appendCollectors=True):
    """Emit the evidence-seed for one L4-approved skill (dual write).

    Builds the rows, writes the standalone partitioned artifact, and (unless
    ``appendCollectors`` is False) appends them into the collector channel files.

    Returns ``{rows, artifactPaths, collectorPaths}``.
    """
    rows = buildSeedRows(skillId, sources, attributionScope=attributionScope)
    artifactPaths = writeSeedArtifact(skillId, rows, evidenceRoot=evidenceRoot)
    collectorPaths = set()
    if appendCollectors:
        collectorPaths = appendToCollectors(rows, evidenceRoot=evidenceRoot)
    return {
        "rows": rows,
        "artifactPaths": artifactPaths,
        "collectorPaths": collectorPaths,
    }
