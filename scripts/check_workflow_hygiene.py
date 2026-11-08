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

* **Blocking** - every workflow that is not a pinned generated lock file. A
  ``(workflow, job)`` pair with no ``timeout-minutes`` that is not in the
  baseline fails (a new job, or a new workflow). The baseline is the open set at
  the time it was cut and may only shrink:
  - an entry whose job now has a timeout (or no longer exists) is *stale* and
    fails, so a repaired job leaves the baseline (``--prune-baseline``);
  - an entry (or pinned lock file) that is not justified by the base ref is
    *growth* and fails. When the base ref has a baseline, growth is anything not
    in it. When it has none (the PR that introduces the gate), growth is any
    entry that is not a sensor finding at the base commit, and any pinned lock
    file that was not already a generated lock with its gh-aw source at the base.
* **Excluded, reported** - gh-aw generated lock files, but only the ones pinned
  by name in the baseline (``excluded.generated-lock-files.files``), and only
  while the sensor still classifies them as generated (``_is_generated_lock``),
  they carry the gh-aw banner, and their gh-aw source ``<name>.md`` sits beside them. A gh-aw banner or a
  ``.lock.yml`` suffix alone never excludes anything: an unpinned file is
  blocking until it is pinned deliberately, and pinning is growth-checked.
  gh-aw v0.92.6 refuses per-job ``timeout-minutes`` on its compiled jobs, so
  their findings are printed on every run and stay open in the Steward census;
  they are not suppressed, only not blocking.

Exit codes: 0 pass, 1 gate failure, 2 cannot evaluate (fail closed).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gaia_cli.steward.sensors_ci import (  # noqa: E402  (path set above)
    _GH_AW_MARKER,
    _is_generated_lock,
    _workflow_findings,
)

WORKFLOWS_DIR = ".github/workflows"
BASELINE_RELATIVE = "scripts/lint/workflow-timeout-baseline.json"
DEFAULT_BASELINE_PATH = REPO_ROOT / BASELINE_RELATIVE
RULE = "missing-timeout"
LOCK_SUFFIX = ".lock.yml"
EXCLUSION_REASON = (
    "gh-aw generated lock file: gh-aw v0.92.6 refuses per-job timeout-minutes on compiled "
    "jobs and a hand edit is overwritten by the next compile; the repair is in the .md "
    "source plus a founder-gated recompile. Reported, never blocking; the Steward finding stays open. "
    "Only the files listed here are excluded, and only while each is still a gh-aw lock with its .md source beside it."
)
_DETAIL = re.compile(r"^job (?P<job>.+) has no timeout-minutes$")

Pair = tuple[str, str]


@dataclass
class Baseline:
    entries: set[Pair] = field(default_factory=set)
    pinned: set[str] = field(default_factory=set)


@dataclass
class Scan:
    """Missing-timeout findings of one tree, split by the sensor's generated-lock verdict."""

    findings: dict[str, set[Pair]] = field(default_factory=dict)  # workflow -> pairs
    generated: set[str] = field(default_factory=set)  # sensor says gh-aw generated
    sources: set[str] = field(default_factory=set)  # lock files whose <name>.md exists
    bannered: set[str] = field(default_factory=set)  # files carrying the gh-aw banner in their head
    errors: list[str] = field(default_factory=list)


def _is_workflow_name(name: str) -> bool:
    return name.endswith((".yml", ".yaml"))


def workflow_files(repo_root: Path) -> list[str]:
    """Direct-child workflow files on disk, repo-relative POSIX paths, sorted."""

    folder = repo_root / WORKFLOWS_DIR
    if not folder.is_dir():
        return []
    return sorted(f"{WORKFLOWS_DIR}/{p.name}" for p in folder.iterdir() if p.is_file() and _is_workflow_name(p.name))


def source_of(lock: str) -> str:
    return lock[: -len(LOCK_SUFFIX)] + ".md"


def scan_files(root: Path, files: Iterable[str], has_file: Callable[[str], bool]) -> Scan:
    scan = Scan()
    for relative in files:
        path = root / relative
        findings = _workflow_findings(path)
        if _is_generated_lock(path, relative):
            scan.generated.add(relative)
        if relative.endswith(LOCK_SUFFIX) and has_file(source_of(relative)):
            scan.sources.add(relative)
        try:
            if _GH_AW_MARKER in path.read_bytes()[:4096].decode("utf-8", "replace"):
                scan.bannered.add(relative)
        except OSError:
            pass  # unreadable: _workflow_findings above already reports it
        for item in findings:
            if item["rule"] == "unparseable-workflow":
                scan.errors.append(f"{relative}: {item['detail']}")
                continue
            if item["rule"] != RULE:
                continue
            match = _DETAIL.match(item["detail"])
            if not match:
                scan.errors.append(f"{relative}: unrecognised {RULE} detail {item['detail']!r}")
                continue
            scan.findings.setdefault(relative, set()).add((relative, match.group("job")))
    return scan


def scan_worktree(repo_root: Path) -> Scan:
    return scan_files(repo_root, workflow_files(repo_root), lambda rel: (repo_root / rel).is_file())


def excludable(scan: Scan, workflow: str) -> bool:
    """A pinned lock is excluded only while it is a ``*.lock.yml`` that the sensor calls generated,
    carries the gh-aw banner, and has its gh-aw ``.md`` source beside it."""

    return (
        workflow.endswith(LOCK_SUFFIX)
        and workflow in scan.generated
        and workflow in scan.bannered
        and workflow in scan.sources
    )


def classify(scan: Scan, pinned: set[str]) -> tuple[set[Pair], set[Pair], list[str]]:
    """``(blocking-tier findings, excluded findings, pin problems)``."""

    hand: set[Pair] = set()
    excluded: set[Pair] = set()
    for workflow, pairs in scan.findings.items():
        if workflow in pinned and excludable(scan, workflow):
            excluded |= pairs
        else:
            hand |= pairs
    problems = [
        f"{workflow} is pinned as a generated lock file but is not one now "
        "(missing, no gh-aw banner, or no .md source beside it); remove the pin"
        for workflow in sorted(pinned)
        if not excludable(scan, workflow)
    ]
    return hand, excluded, problems


def parse_baseline(text: str, where: str) -> Baseline:
    """Parse and validate baseline JSON; raise ValueError on any malformed input."""

    data = json.loads(text)
    if not isinstance(data, dict) or data.get("version") != 1 or data.get("rule") != RULE:
        raise ValueError(f"{where}: unsupported baseline format")
    entries = data.get("entries")
    if not isinstance(entries, list):
        raise ValueError(f"{where}: entries must be a list")
    baseline = Baseline()
    for entry in entries:
        if (
            not isinstance(entry, dict)
            or set(entry) != {"workflow", "job"}
            or not all(isinstance(entry[k], str) and entry[k] for k in ("workflow", "job"))
        ):
            raise ValueError(f"{where}: invalid entry {entry!r}")
        workflow = entry["workflow"]
        _check_workflow_path(workflow, where)
        if workflow.endswith(LOCK_SUFFIX):
            raise ValueError(f"{where}: {workflow!r} is a generated lock file; pin it under excluded, do not baseline it")
        pair = (workflow, entry["job"])
        if pair in baseline.entries:
            raise ValueError(f"{where}: duplicate entry {pair!r}")
        baseline.entries.add(pair)
    excluded = data.get("excluded")
    locks = excluded.get("generated-lock-files") if isinstance(excluded, dict) else None
    files = locks.get("files") if isinstance(locks, dict) else None
    if not isinstance(files, list):
        raise ValueError(f"{where}: excluded.generated-lock-files.files must be a list")
    for workflow in files:
        if not isinstance(workflow, str):
            raise ValueError(f"{where}: invalid pinned lock file {workflow!r}")
        _check_workflow_path(workflow, where)
        if not workflow.endswith(LOCK_SUFFIX):
            raise ValueError(f"{where}: pinned file {workflow!r} is not a *{LOCK_SUFFIX} file")
        if workflow in baseline.pinned:
            raise ValueError(f"{where}: duplicate pinned file {workflow!r}")
        baseline.pinned.add(workflow)
    return baseline


def _check_workflow_path(workflow: str, where: str) -> None:
    if workflow.count("/") != 2 or not workflow.startswith(f"{WORKFLOWS_DIR}/") or not _is_workflow_name(workflow):
        raise ValueError(f"{where}: {workflow!r} is not a direct-child workflow path")


def load_baseline(path: Path) -> Baseline:
    return parse_baseline(path.read_text(encoding="utf-8"), str(path))


def render_baseline(pairs: Iterable[Pair], pinned: Iterable[str] = ()) -> str:
    data: dict[str, Any] = {
        "version": 1,
        "rule": RULE,
        "source": "gaia_cli.steward.sensors_ci._workflow_findings (Steward ci-workflow sensor rule)",
        "policy": "shrink-only: stale entries fail; entries or pins not justified by the base ref fail",
        "excluded": {"generated-lock-files": {"reason": EXCLUSION_REASON, "files": sorted(set(pinned))}},
        "entries": [{"workflow": w, "job": j} for w, j in sorted(set(pairs))],
    }
    return json.dumps(data, indent=2) + "\n"


def evaluate(
    hand: set[Pair],
    baseline: Baseline,
    allowed_entries: set[Pair] | None = None,
    allowed_pins: set[str] | None = None,
) -> dict[str, list[Any]]:
    """Compare findings with the baseline.

    ``new``: findings not in the baseline (blocking).
    ``stale``: baseline entries no longer observed (repaired or removed).
    ``grown`` / ``grown_pins``: entries or pins the base ref does not justify.
    """

    return {
        "new": sorted(hand - baseline.entries),
        "stale": sorted(baseline.entries - hand),
        "grown": sorted(baseline.entries - allowed_entries) if allowed_entries is not None else [],
        "grown_pins": sorted(baseline.pinned - allowed_pins) if allowed_pins is not None else [],
    }


def _git(repo_root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=repo_root, capture_output=True, check=False)


def base_allowance(repo_root: Path, ref: str) -> tuple[set[Pair], set[str], str]:
    """What the base ref justifies: ``(allowed entries, allowed pins, how)``.

    With a baseline at ``ref``: exactly its entries and pins. Without one: the
    sensor's missing-timeout findings at the base commit (non-lock files) and the
    lock files that were already gh-aw generated with their source beside them.
    Raises ValueError when ``ref`` cannot be resolved or read (fail closed).
    """

    resolved = _git(repo_root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    if resolved.returncode != 0:
        raise ValueError(f"cannot resolve base ref {ref!r}")
    commit = resolved.stdout.decode().strip()
    shown = _git(repo_root, "show", f"{commit}:{BASELINE_RELATIVE}")
    if shown.returncode == 0:
        base = parse_baseline(shown.stdout.decode("utf-8"), f"{ref}:{BASELINE_RELATIVE}")
        return base.entries, base.pinned, f"the baseline at {ref}"
    listed = _git(repo_root, "ls-tree", "--name-only", "-z", commit, f"{WORKFLOWS_DIR}/")
    if listed.returncode != 0:
        raise ValueError(f"cannot list {WORKFLOWS_DIR} at {ref!r}")
    names = {n.decode() for n in listed.stdout.split(b"\0") if n}
    files = sorted(n for n in names if n.count("/") == 2 and _is_workflow_name(n))
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        for relative in files:
            blob = _git(repo_root, "show", f"{commit}:{relative}")
            if blob.returncode != 0:
                raise ValueError(f"cannot read {relative} at {ref!r}")
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(blob.stdout)
        scan = scan_files(root, files, lambda rel: rel in names)
    if scan.errors:
        raise ValueError(f"base {ref!r} has unreadable workflow(s): {'; '.join(scan.errors)}")
    allowed_entries = {pair for wf, pairs in scan.findings.items() if not wf.endswith(LOCK_SUFFIX) for pair in pairs}
    allowed_pins = {wf for wf in files if excludable(scan, wf)}
    return allowed_entries, allowed_pins, f"sensor findings at {ref} (it has no baseline yet)"


def main(argv: Sequence[str] | None = None, repo_root: Path = REPO_ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--baseline", type=Path, default=None, help="Baseline JSON path.")
    parser.add_argument(
        "--base-ref",
        default=None,
        help="Git ref the baseline may only shrink from (CI passes the PR base or push 'before').",
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
        help="Remove stale entries and dead pins from the baseline and exit. Never adds anything.",
    )
    parser.add_argument(
        "--init-baseline",
        action="store_true",
        help="Write a NEW baseline: the current open set, pinning the current gh-aw locks. Refuses if one exists.",
    )
    args = parser.parse_args(argv)
    baseline_path = (args.baseline or repo_root / BASELINE_RELATIVE).resolve()

    scan = scan_worktree(repo_root)
    if scan.errors:
        for line in scan.errors:
            print(f"[ERROR] {line}", file=sys.stderr)
        print("Cannot evaluate: unreadable workflow(s).", file=sys.stderr)
        return 2

    if args.init_baseline:
        if baseline_path.exists():
            print(f"Refusing: {baseline_path} exists; the baseline only shrinks (use --prune-baseline).", file=sys.stderr)
            return 2
        pinned = {wf for wf in workflow_files(repo_root) if excludable(scan, wf)}
        hand, _, _ = classify(scan, pinned)
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(render_baseline(hand, pinned), encoding="utf-8")
        print(f"Baseline written: {len(hand)} hand-written jobs, {len(pinned)} pinned generated lock files.")
        return 0

    try:
        baseline = load_baseline(baseline_path)
    except (OSError, ValueError) as exc:
        print(f"Error loading baseline: {exc}", file=sys.stderr)
        return 2

    hand, excluded, pin_problems = classify(scan, baseline.pinned)

    if args.prune_baseline:
        kept = baseline.entries & hand
        pins = {wf for wf in baseline.pinned if excludable(scan, wf)}
        baseline_path.write_text(render_baseline(kept, pins), encoding="utf-8")
        print(
            f"Pruned {len(baseline.entries) - len(kept)} stale entr(y/ies) and "
            f"{len(baseline.pinned) - len(pins)} dead pin(s); {len(kept)} entries, {len(pins)} pins remain."
        )
        return 0

    allowed_entries: set[Pair] | None = None
    allowed_pins: set[str] | None = None
    if args.base_ref:
        try:
            allowed_entries, allowed_pins, how = base_allowance(repo_root, args.base_ref)
        except (ValueError, UnicodeDecodeError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2
        print(f"[INFO] growth is judged against {how}.")

    result = evaluate(hand, baseline, allowed_entries, allowed_pins)

    for workflow, job in sorted(excluded):
        print(f"[EXCLUDED] {workflow}: job {job} has no timeout-minutes (pinned generated gh-aw lock file)")
    unpinned = sorted({wf for wf, _ in hand if wf in scan.generated or wf.endswith(LOCK_SUFFIX)})
    for workflow in unpinned:
        print(
            f"[UNPINNED] {workflow} looks generated but is not a pinned gh-aw lock file; its jobs are blocking. "
            "Add timeouts, or pin it in excluded.generated-lock-files (growth-checked) if it is real gh-aw output.",
            file=sys.stderr,
        )
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
    for problem in pin_problems:
        print(f"[{stale_tag}] {problem}", file=sys.stderr if args.stale == "fail" else sys.stdout)
    for workflow, job in result["grown"]:
        print(
            f"[GROWN] {workflow}: job {job} is in the baseline but not justified by the base ref; "
            "the baseline may only shrink. Add a timeout instead.",
            file=sys.stderr,
        )
    for workflow in result["grown_pins"]:
        print(
            f"[GROWN] {workflow} is pinned as a generated lock file but the base ref does not justify it.",
            file=sys.stderr,
        )

    print("\n============ Workflow Hygiene Gate (missing-timeout) ============")
    print(f"Blocking-tier open jobs:   {len(hand)} ({len(hand & baseline.entries)} baselined)")
    print(f"New (blocking):            {len(result['new'])}")
    print(f"Stale entries / dead pins: {len(result['stale'])} / {len(pin_problems)} ({args.stale})")
    print(f"Baseline growth:           {len(result['grown'])} entries, {len(result['grown_pins'])} pins")
    print(f"Generated lock (excluded): {len(excluded)} jobs in {len({w for w, _ in excluded})} pinned files")
    print("==================================================================")

    stale = bool(result["stale"] or pin_problems)
    failed = bool(result["new"] or result["grown"] or result["grown_pins"] or (stale and args.stale == "fail"))
    if failed:
        print("FAILED: workflow hygiene gate.", file=sys.stderr)
        return 1
    print("PASSED: workflow hygiene gate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
