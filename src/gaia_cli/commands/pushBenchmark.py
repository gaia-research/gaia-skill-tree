"""Benchmark-flow subhandler for ``gaia push --benchmark``.

Diverts from the standard skill-proposal push flow into a benchmark-evidence
append flow: the USER verb writes a ``provenance: pending`` benchmark-result
row, which a CI workflow (or a 4★+ Verifier co-sign) later promotes to
``ci-reproduced`` or ``verifier-attested``.

Design rules (root CLAUDE.md, EPIC W2b, Sprint D handover):

* This module DOES NOT reimplement any of `_preflight_benchmark_row`. It
  builds an argparse.Namespace matching what `meta_evidence_command` expects
  and calls that function directly — the SSOT preflight fires exactly once
  from there.
* `gaia push --benchmark …` ALWAYS writes ``provenance: pending``. Promotion
  is the CI / Verifier layer's job.
* ``--from-result-file`` reads the harness output JSON and populates every
  required field automatically, so the happy path is a single flag.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path


# Frozen short-name → versioned benchmarkId map. Extending this is a
# coordinated schema change (a new benchmarkId lands in registry/schema/,
# a new harness lands in scripts/benchmarks/<name>/, then a row lands here).
BENCHMARK_ID_ALIASES: dict[str, str] = {
    "humaneval": "humaneval@v1.0",
}


def _fail(msg: str, fix: str | None = None) -> None:
    """Emit a structured error and exit non-zero. Shape matches the dev preflight."""
    print(f"error: {msg}", file=sys.stderr)
    if fix:
        print(f"  fix: {fix}", file=sys.stderr)
    sys.exit(2)


def _resolveBenchmarkId(shortName: str, fromFileId: str | None = None) -> str:
    """Turn a --benchmark short-name into a canonical versioned id.

    If the result file already carries a `benchmarkId`, that value wins —
    but we assert its short-name prefix matches so callers cannot silently
    push a swe-bench result under a --benchmark humaneval flag.
    """
    canonical = BENCHMARK_ID_ALIASES.get(shortName)
    if canonical is None:
        _fail(
            f"unknown --benchmark {shortName!r}",
            fix=f"Supported: {', '.join(sorted(BENCHMARK_ID_ALIASES))}. "
                "Add a new alias in src/gaia_cli/commands/pushBenchmark.py alongside a "
                "harness in scripts/benchmarks/<name>/.",
        )
    if fromFileId is None:
        return canonical
    fileShort = fromFileId.split("@", 1)[0]
    if fileShort != shortName:
        _fail(
            f"--benchmark {shortName!r} disagrees with result file benchmarkId {fromFileId!r}",
            fix="The short-name flag must match the benchmarkId embedded in the "
                "result file, or omit --benchmark and let the file speak.",
        )
    return fromFileId


def _loadResultFile(path: Path) -> dict:
    """Load and structurally validate a harness result JSON."""
    if not path.exists():
        _fail(
            f"--from-result-file {path} not found",
            fix="Run scripts/benchmarks/<name>/run.py first to produce the result file.",
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        _fail(
            f"--from-result-file {path} is not valid JSON: {exc}",
            fix="Regenerate the file with the harness — do not hand-edit it.",
        )
    required = ("benchmarkId", "score", "unit", "datasetHash", "benchmarkInputHash", "runAt")
    missing = [k for k in required if k not in payload]
    if missing:
        _fail(
            f"--from-result-file {path} is missing fields: {missing}",
            fix="Older harness output? Re-run the harness at HEAD to regenerate "
                "with the current fingerprint schema.",
        )
    return payload


def _resolveAttestor(explicit: str | None) -> str:
    """Pick the attestor handle for a pending row.

    Preference order: explicit --attestor flag → gaiaUser from config →
    'unknown' (which _preflight_benchmark_row rejects with a clean error,
    so we never silently ship an empty attestor).
    """
    if explicit and explicit.strip():
        return explicit.strip()
    # Reuse the same contributor helper the rest of `gaia dev` uses so the
    # attestor handle matches every other timeline event on the skill.
    from gaia_cli.commands.dev.helpers import _get_contributor
    handle = _get_contributor()
    if handle and handle != "unknown":
        return handle
    _fail(
        "cannot determine --attestor for pending benchmark row",
        fix="Set it explicitly with --attestor <github-handle>, or run "
            "`gaia init` to record your GitHub username.",
    )
    return "unknown"  # unreachable — _fail sys.exits


def _resolveSourceUrl(harnessUrl: str | None, benchmarkId: str, inputHash: str) -> str:
    """Return the evidence-row source URL.

    Prefer an explicit --harness-url (pinned-commit permalink into
    scripts/benchmarks/<name>/run.py). Fall back to the canonical benchmark
    spec page with the input fingerprint as a fragment — that keeps the URL
    absolute http(s) (which _preflight_evidence_static requires) while still
    being unique per (benchmark, input fingerprint) so the duplicate-source
    preflight catches repeated pushes of the exact same run.
    """
    if harnessUrl and harnessUrl.strip():
        return harnessUrl.strip()
    shortName = benchmarkId.split("@", 1)[0]
    return f"https://gaiaskilltree.com/benchmarks/{shortName}-v1.md#{inputHash}"


def _buildEvidenceNamespace(args: argparse.Namespace, resolved: dict) -> argparse.Namespace:
    """Assemble the argparse.Namespace `meta_evidence_command` consumes.

    We stamp exactly the fields the evidence writer reads via getattr,
    matching the argparse contract in commands/dev/__init__.py.
    """
    return argparse.Namespace(
        registry=getattr(args, "registry", "."),
        skill_id=resolved["skillId"],
        source=resolved["source"],
        evidence_type="benchmark-result",
        trust=None,
        evaluator=None,
        date=None,
        notes=resolved.get("notes"),
        index=None,
        # numeric magnitude drivers
        stars=None,
        views=None,
        citations=None,
        reviewers=None,
        commits=None,
        contributors=None,
        skill_count_in_repo=None,
        percentile=resolved.get("percentile"),
        source_started_at=None,
        # benchmark-result fingerprint (SSOT preflight validates these)
        benchmark_id=resolved["benchmarkId"],
        score=resolved["score"],
        unit=resolved["unit"],
        run_at=resolved["runAt"],
        provenance="pending",
        attestor=resolved["attestor"],
        dataset_hash=resolved["datasetHash"],
        benchmark_input_hash=resolved["benchmarkInputHash"],
        harness_url=resolved.get("harnessUrl"),
        no_build=getattr(args, "no_build", True),
    )


def push_benchmark_command(args: argparse.Namespace) -> int:
    """Divert flow for `gaia push --benchmark`.

    Consolidates flag values (with optional --from-result-file shortcut),
    infers the attestor and source URL, then delegates to the standard
    dev-evidence writer so the SSOT preflight fires exactly once.
    """
    shortName: str | None = getattr(args, "benchmark", None)
    if not shortName:
        _fail("internal: push_benchmark_command called without --benchmark")

    resultFile: str | None = getattr(args, "fromResultFile", None)
    resolved: dict = {}
    fromFileBenchmarkId: str | None = None

    if resultFile:
        payload = _loadResultFile(Path(resultFile))
        fromFileBenchmarkId = payload["benchmarkId"]
        resolved.update(
            {
                "skillId": payload.get("skillId"),
                "score": payload["score"],
                "unit": payload["unit"],
                "datasetHash": payload["datasetHash"],
                "benchmarkInputHash": payload["benchmarkInputHash"],
                "runAt": payload["runAt"],
            }
        )

    # Explicit flags override the result file (except for hashes — those are
    # the fingerprint and cannot be argued with; a mismatch would be a bug).
    for flag, key in (
        ("skillId", "skillId"),
        ("score", "score"),
        ("unit", "unit"),
        ("datasetHash", "datasetHash"),
        ("benchmarkInputHash", "benchmarkInputHash"),
        ("runAt", "runAt"),
        ("percentile", "percentile"),
        ("harnessUrl", "harnessUrl"),
    ):
        explicit = getattr(args, flag, None)
        if explicit is not None:
            resolved[key] = explicit

    # Defaults
    resolved.setdefault("unit", "pct")
    resolved.setdefault("runAt", _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"))

    # Hard-required. --skill-id, --score, --dataset-hash, --benchmark-input-hash
    # are individually reported so the CLI error is actionable in isolation.
    if not resolved.get("skillId"):
        _fail(
            "--skill-id required (or provide --from-result-file with a skillId field)",
            fix="Example: --skill-id addy-osmani/code-simplification",
        )
    if resolved.get("score") is None:
        _fail(
            "--score required (or provide --from-result-file with a score field)",
            fix="Example: --score 0.83",
        )
    if not resolved.get("datasetHash"):
        _fail(
            "--dataset-hash required (or provide --from-result-file)",
            fix="Compute with: python -c \"import hashlib; print(hashlib.sha256(open('HumanEval.jsonl','rb').read()).hexdigest())\"",
        )
    if not resolved.get("benchmarkInputHash"):
        _fail(
            "--benchmark-input-hash required (or provide --from-result-file)",
            fix="Emitted by the harness alongside datasetHash — see scripts/benchmarks/README.md.",
        )

    resolved["benchmarkId"] = _resolveBenchmarkId(shortName, fromFileBenchmarkId)
    resolved["attestor"] = _resolveAttestor(getattr(args, "attestor", None))
    resolved["source"] = _resolveSourceUrl(
        resolved.get("harnessUrl"),
        resolved["benchmarkId"],
        resolved["benchmarkInputHash"],
    )

    if getattr(args, "dry_run", False):
        preview = {
            "skillId": resolved["skillId"],
            "benchmarkId": resolved["benchmarkId"],
            "score": resolved["score"],
            "unit": resolved["unit"],
            "provenance": "pending",
            "attestor": resolved["attestor"],
            "source": resolved["source"],
            "datasetHash": resolved["datasetHash"],
            "benchmarkInputHash": resolved["benchmarkInputHash"],
            "runAt": resolved["runAt"],
        }
        print("Would append benchmark-result row (dry-run — nothing written):")
        print(json.dumps(preview, indent=2, sort_keys=True))
        return 0

    from gaia_cli.commands.dev.evidence import meta_evidence_command

    evArgs = _buildEvidenceNamespace(args, resolved)
    # meta_evidence_command uses sys.exit on preflight failure — that's the
    # SSOT contract. If it returns, the row landed successfully.
    meta_evidence_command(evArgs)
    print(
        f"Filed pending benchmark row for {resolved['skillId']}: "
        f"{resolved['benchmarkId']} score={resolved['score']} "
        f"attestor={resolved['attestor']}"
    )
    print(
        "Next: a CI workflow (or a 4★+ Verifier co-sign) will promote this "
        "row from provenance:pending to ci-reproduced/verifier-attested. "
        "It stays pending — and blocks merges to main — until then."
    )
    return 0
