#!/usr/bin/env python3
"""Workflow-hygiene ratchet: no new GitHub Actions job without ``timeout-minutes``.

Detection is not new. Every finding comes from the Steward ``ci-workflow``
sensor's own rule (``gaia_cli.steward.sensors_ci._workflow_findings``,
``rule == "missing-timeout"``), so this gate and the Steward census can never
disagree about what a missing timeout is. The gate adds only a committed
baseline and a comparison.

Scope: direct children of ``.github/workflows/`` ending in ``.yml``/``.yaml``,
the same inventory the sensor scans (``shared/`` and ``_disabled/`` are nested
and never run as workflows).

Tiers:

* **Blocking** - hand-written workflows. A ``(workflow, job)`` pair with no
  ``timeout-minutes`` that is not in the baseline fails (a new job, or a new
  workflow). The baseline is the open set at the time it was cut and may only
  shrink:
  - an entry whose job now has a timeout (or no longer exists) is *stale* and
    fails, so a repaired job leaves the baseline (``--prune-baseline``);
  - an entry added relative to the base ref's baseline fails.
* **Excluded, reported** - gh-aw generated lock files (``*.lock.yml`` or the
  gh-aw banner, decided by the sensor's ``_is_generated_lock``). gh-aw v0.92.6
  refuses per-job ``timeout-minutes`` on its compiled ``activation``,
  ``conclusion`` and custom jobs, and a hand edit is overwritten by the next
  compile. Their findings are printed on every run and stay open in the Steward
  census; they are not suppressed, only not blocking.

Exit codes: 0 pass, 1 gate failure, 2 cannot evaluate (fail closed).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gaia_cli.steward.sensors_ci import (  # noqa: E402  (path set above)
    _is_generated_lock,
    _workflow_findings,
)

WORKFLOWS_DIR = ".github/workflows"
BASELINE_RELATIVE = "scripts/lint/workflow-timeout-baseline.json"
DEFAULT_BASELINE_PATH = REPO_ROOT / BASELINE_RELATIVE
RULE = "missing-timeout"
EXCLUSION_REASON = (
    "gh-aw generated lock file: gh-aw v0.92.6 refuses per-job timeout-minutes on compiled "
    "jobs and a hand edit is overwritten by the next compile; the repair is in the .md "
    "source plus a founder-gated recompile. Reported, never blocking; the Steward finding stays open."
)
_DETAIL = re.compile(r"^job (?P<job>.+) has no timeout-minutes$")

Pair = tuple[str, str]


def workflow_files(repo_root: Path) -> list[str]:
    """Direct-child workflow files, repo-relative POSIX paths, sorted."""

    folder = repo_root / WORKFLOWS_DIR
    if not folder.is_dir():
        return []
    return sorted(
        f"{WORKFLOWS_DIR}/{path.name}"
        for path in folder.iterdir()
        if path.is_file() and path.suffix in (".yml", ".yaml")
    )


def collect(repo_root: Path) -> tuple[set[Pair], set[Pair], list[str]]:
    """Return (hand-written findings, generated-excluded findings, errors).

    ``errors`` names workflows the sensor rule could not parse; a workflow the
    gate cannot read is not a pass.
    """

    hand: set[Pair] = set()
    generated: set[Pair] = set()
    errors: list[str] = []
    for relative in workflow_files(repo_root):
        path = repo_root / relative
        findings = _workflow_findings(path)
        bucket = generated if _is_generated_lock(path, relative) else hand
        for item in findings:
            if item["rule"] == "unparseable-workflow":
                errors.append(f"{relative}: {item['detail']}")
                continue
            if item["rule"] != RULE:
                continue
            match = _DETAIL.match(item["detail"])
            if not match:
                errors.append(f"{relative}: unrecognised {RULE} detail {item['detail']!r}")
                continue
            bucket.add((relative, match.group("job")))
    return hand, generated, errors


def load_baseline_text(text: str, where: str) -> set[Pair]:
    """Parse and validate baseline JSON; raise ValueError on any malformed input."""

    data = json.loads(text)
    if not isinstance(data, dict) or data.get("version") != 1 or data.get("rule") != RULE:
        raise ValueError(f"{where}: unsupported baseline format")
    entries = data.get("entries")
    if not isinstance(entries, list):
        raise ValueError(f"{where}: entries must be a list")
    pairs: set[Pair] = set()
    for entry in entries:
        if (
            not isinstance(entry, dict)
            or set(entry) != {"workflow", "job"}
            or not all(isinstance(entry[k], str) and entry[k] for k in ("workflow", "job"))
        ):
            raise ValueError(f"{where}: invalid entry {entry!r}")
        workflow = entry["workflow"]
        if workflow.count("/") != 2 or not workflow.startswith(f"{WORKFLOWS_DIR}/"):
            raise ValueError(f"{where}: {workflow!r} is not a direct-child workflow path")
        if workflow.endswith(".lock.yml"):
            raise ValueError(f"{where}: {workflow!r} is a generated lock file; lock files are excluded, not baselined")
        pair = (workflow, entry["job"])
        if pair in pairs:
            raise ValueError(f"{where}: duplicate entry {pair!r}")
        pairs.add(pair)
    return pairs


def load_baseline(path: Path) -> set[Pair]:
    return load_baseline_text(path.read_text(encoding="utf-8"), str(path))


def render_baseline(pairs: Iterable[Pair]) -> str:
    data: dict[str, Any] = {
        "version": 1,
        "rule": RULE,
        "source": "gaia_cli.steward.sensors_ci._workflow_findings (Steward ci-workflow sensor rule)",
        "policy": "shrink-only: stale entries fail; entries added relative to the base ref fail",
        "excluded": {"generated-lock-files": EXCLUSION_REASON},
        "entries": [{"workflow": w, "job": j} for w, j in sorted(set(pairs))],
    }
    return json.dumps(data, indent=2) + "\n"


def evaluate(
    hand: set[Pair],
    baseline: set[Pair],
    base_baseline: set[Pair] | None = None,
) -> dict[str, list[Pair]]:
    """Compare findings with the baseline.

    ``new``: findings not in the baseline (blocking).
    ``stale``: baseline entries no longer observed (repaired or removed).
    ``grown``: baseline entries absent from the base ref's baseline.
    """

    return {
        "new": sorted(hand - baseline),
        "stale": sorted(baseline - hand),
        "grown": sorted(baseline - base_baseline) if base_baseline is not None else [],
    }


def base_baseline_at(repo_root: Path, ref: str) -> set[Pair] | None:
    """The baseline at ``ref``; None when that ref has no baseline yet.

    Raises ValueError when ``ref`` itself cannot be resolved (fail closed).
    """

    resolved = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if resolved.returncode != 0:
        raise ValueError(f"cannot resolve base ref {ref!r}")
    shown = subprocess.run(
        ["git", "show", f"{resolved.stdout.strip()}:{BASELINE_RELATIVE}"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if shown.returncode != 0:
        return None
    return load_baseline_text(shown.stdout, f"{ref}:{BASELINE_RELATIVE}")


def main(argv: Sequence[str] | None = None, repo_root: Path = REPO_ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--baseline", type=Path, default=None, help="Baseline JSON path.")
    parser.add_argument(
        "--base-ref",
        default=None,
        help="Git ref whose committed baseline this one may only shrink from (CI passes the PR base or push 'before').",
    )
    parser.add_argument(
        "--stale",
        choices=("fail", "warn"),
        default="fail",
        help="How to treat baseline entries whose job now has a timeout (default: fail).",
    )
    parser.add_argument(
        "--prune-baseline",
        action="store_true",
        help="Remove stale entries from the baseline and exit. Never adds entries.",
    )
    parser.add_argument(
        "--init-baseline",
        action="store_true",
        help="Write the current hand-written open set as a NEW baseline. Refuses if one exists.",
    )
    args = parser.parse_args(argv)
    baseline_path = (args.baseline or repo_root / BASELINE_RELATIVE).resolve()

    hand, generated, errors = collect(repo_root)
    if errors:
        for line in errors:
            print(f"[ERROR] {line}", file=sys.stderr)
        print("Cannot evaluate: unreadable workflow(s).", file=sys.stderr)
        return 2

    if args.init_baseline:
        if baseline_path.exists():
            print(f"Refusing: {baseline_path} exists; the baseline only shrinks (use --prune-baseline).", file=sys.stderr)
            return 2
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(render_baseline(hand), encoding="utf-8")
        print(f"Baseline written: {len(hand)} hand-written jobs.")
        return 0

    try:
        baseline = load_baseline(baseline_path)
    except (OSError, ValueError) as exc:
        print(f"Error loading baseline: {exc}", file=sys.stderr)
        return 2

    if args.prune_baseline:
        kept = baseline & hand
        baseline_path.write_text(render_baseline(kept), encoding="utf-8")
        print(f"Pruned {len(baseline) - len(kept)} stale entr(y/ies); {len(kept)} remain.")
        return 0

    base_baseline: set[Pair] | None = None
    if args.base_ref:
        try:
            base_baseline = base_baseline_at(repo_root, args.base_ref)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2
        if base_baseline is None:
            print(f"[INFO] {args.base_ref} has no baseline yet; growth check skipped (baseline introduced here).")

    result = evaluate(hand, baseline, base_baseline)

    for workflow, job in sorted(generated):
        print(f"[EXCLUDED] {workflow}: job {job} has no timeout-minutes (generated gh-aw lock file)")
    for workflow, job in result["new"]:
        print(
            f"[BLOCKING] {workflow}: job {job} has no timeout-minutes. "
            "Add `timeout-minutes:` sized to the job's real waits.",
            file=sys.stderr,
        )
    stale_tag = "STALE" if args.stale == "fail" else "STALE-WARN"
    for workflow, job in result["stale"]:
        print(
            f"[{stale_tag}] {workflow}: job {job} is baselined but now has a timeout or no longer exists. "
            f"Run: python3 scripts/check_workflow_hygiene.py --prune-baseline",
            file=sys.stderr if args.stale == "fail" else sys.stdout,
        )
    for workflow, job in result["grown"]:
        print(
            f"[GROWN] {workflow}: job {job} was added to the baseline; it may only shrink. "
            "Add a timeout instead.",
            file=sys.stderr,
        )

    print("\n============ Workflow Hygiene Gate (missing-timeout) ============")
    print(f"Hand-written open jobs:    {len(hand)} ({len(hand & baseline)} baselined)")
    print(f"New (blocking):            {len(result['new'])}")
    print(f"Stale baseline entries:    {len(result['stale'])} ({args.stale})")
    print(f"Baseline growth:           {len(result['grown'])}")
    print(f"Generated lock (excluded): {len(generated)} jobs in {len({w for w, _ in generated})} files")
    print("==================================================================")

    failed = bool(result["new"] or result["grown"] or (result["stale"] and args.stale == "fail"))
    if failed:
        print("FAILED: workflow hygiene gate.", file=sys.stderr)
        return 1
    print("PASSED: workflow hygiene gate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
