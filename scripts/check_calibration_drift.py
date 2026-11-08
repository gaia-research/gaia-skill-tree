#!/usr/bin/env python3
"""PR-time prevention gate for trust calibration drift (refs #2283).

A named skill's stored ``level`` is a separate field from the level its computed
Trust Magnitude grade publishes. Whenever evidence, a cap or the engine moves the
grade and nobody recalibrates in the same change, the two disagree: that is a
``trust_calibration_drift`` finding of the Steward sensor. This gate keeps a PR
from introducing NEW drift relative to its base:

* the drift set is computed at the base and at the head by the Steward sensor
  itself (``TrustCalibrationDriftSensor``), imported, never re-implemented; the
  base is checked out in a temporary detached worktree and scanned by the head's
  code, so both sides are judged by the same rules;
* a drift at the head that the base does not have (same skill, stored level and
  target level) fails, and is printed with the exact ``gaia dev calibrate`` command
  to run in the same PR. Both directions count: a below-ceiling promotion
  candidate (founder ruling F1) and a stored level above the ceiling;
* drift already present at the base is tolerated, so the set can only shrink;
* frozen skills (``gaia_cli.frozen``, as the sensor marks them) are skipped;
* it fails closed (exit 2) when the base cannot be resolved to exactly one
  commit, when either scan is unavailable, or when the head leaves a named
  record unevaluated that the base could evaluate.

It only reports; it never calibrates or writes to the repository.

Base resolution, the same one-exact-base rule as the ruff gate: ``--base``, else
``origin/$GITHUB_BASE_REF`` in a pull request, else the push's ``before`` commit
(its parent for a new branch). Nothing else is tried.

Exit codes: 0 no new drift, 1 new drift, 2 cannot judge (fail closed).
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

DRIFT_KIND = "trust_calibration_drift"


class GateError(RuntimeError):
    """The gate cannot judge this change (exit 2)."""


def resolve_base_ref(repo_root: Path, base_arg: str | None = None) -> tuple[str, str]:
    """The one exact base commit: (sha, label). Raises GateError otherwise."""

    if base_arg:
        candidate, label = base_arg, f"--base {base_arg}"
    elif os.environ.get("GITHUB_BASE_REF"):
        candidate = f"origin/{os.environ['GITHUB_BASE_REF']}"
        label = f"GITHUB_BASE_REF ({candidate})"
    elif os.environ.get("GITHUB_EVENT_NAME") == "push":
        event_path = os.environ.get("GITHUB_EVENT_PATH")
        if not event_path:
            raise GateError("push event payload is unavailable; cannot determine the base ref")
        try:
            with open(event_path, encoding="utf-8") as handle:
                before = json.load(handle).get("before")
        except (OSError, json.JSONDecodeError) as exc:
            raise GateError(f"cannot read the push event payload: {exc}") from exc
        if not isinstance(before, str) or not before:
            raise GateError("push event has no valid before SHA")
        candidate = before if before.strip("0") else "HEAD~1"
        label = f"push before {candidate}"
    else:
        raise GateError(
            "cannot determine the base ref; pass --base <ref> (the branch this change targets)"
        )
    done = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{candidate}^{{commit}}"],
        cwd=repo_root, capture_output=True, text=True, check=False,
    )
    if done.returncode != 0 or not done.stdout.strip():
        raise GateError(f"base ref {candidate} ({label}) does not resolve to a commit")
    return done.stdout.strip(), label


@contextlib.contextmanager
def fast_yaml(enabled: bool) -> Iterator[None]:
    """Parse with libyaml's CSafeLoader while scanning, when available.

    The sensor parses every named record more than once with ``yaml.safe_load``,
    which is pure Python; on the live registry that is ~20 s per scan against
    ~3 s with the C loader, with an identical drift set. Both sides of the
    comparison use the same loader. ``--pure-yaml`` turns this off.
    """

    import yaml

    loader = getattr(yaml, "CSafeLoader", None)
    if not enabled or loader is None:
        yield
        return
    original = yaml.safe_load
    yaml.safe_load = lambda stream: yaml.load(stream, Loader=loader)  # CSafeLoader is a safe loader
    try:
        yield
    finally:
        yaml.safe_load = original


@contextlib.contextmanager
def base_checkout(repo_root: Path, ref: str) -> Iterator[Path]:
    """A detached, temporary worktree of ``ref``, removed afterwards.

    The sensor inventories named records through git, so the base must be a real
    checkout. Nothing in the head checkout's working tree is touched.
    """

    scratch = Path(tempfile.mkdtemp(prefix="gaia-calibration-gate-"))
    tree = scratch / "base"
    try:
        done = subprocess.run(
            ["git", "worktree", "add", "--quiet", "--detach", str(tree), ref],
            cwd=repo_root, capture_output=True, text=True, check=False,
        )
        if done.returncode != 0:
            raise GateError(f"cannot check out base {ref}: {done.stderr.strip()[:200]}")
        yield tree
    finally:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(tree)],
            cwd=repo_root, capture_output=True, check=False,
        )
        subprocess.run(["git", "worktree", "prune"], cwd=repo_root, capture_output=True, check=False)
        shutil.rmtree(scratch, ignore_errors=True)


def scan_drift(root: Path) -> tuple[dict[tuple[str, str, str], dict[str, Any]], set[str]]:
    """``({(skill id, stored level, target level): observed state}, skipped subject ids)``."""

    from gaia_cli.steward.primitives.files import SensorUnavailable
    from gaia_cli.steward.sensors import TrustCalibrationDriftSensor

    # The sensor intentionally emits no observation or skip for an unsupported
    # level. Audit the input inventory independently so that silence is never
    # mistaken for an aligned, evaluated record.
    import yaml

    named_root = root / "registry/named"
    if not named_root.is_dir():
        raise GateError(f"named registry is unavailable at {root}")
    invalid = []
    for path in sorted(named_root.rglob("*.md")):
        relative = str(path.relative_to(root))
        parts = path.read_text(encoding="utf-8").split("---", 2)
        if len(parts) < 3:
            continue  # the sensor explicitly skips this record
        skill = yaml.safe_load(parts[1]) or {}
        if not isinstance(skill, dict) or not skill.get("id"):
            continue  # the sensor reports these as unavailable or skipped
        timeline = skill.get("timeline", [])
        frozen = isinstance(timeline, list) and any(
            isinstance(event, dict) and event.get("action") == "upstream_deprecated"
            for event in timeline
        )
        if not frozen and skill.get("level") not in TrustCalibrationDriftSensor._TARGET_LEVEL.values():
            invalid.append(str(skill["id"]))
    if invalid:
        raise GateError(f"unevaluated named records at {root}: {', '.join(invalid)}")

    try:
        # An absent catalog cannot distinguish an older checkout from deletion;
        # fail closed rather than substitute head data or assume an empty catalog.
        scan = TrustCalibrationDriftSensor().scan_detailed(
            root, "1970-01-01T00:00:00Z", requireSourceCatalog=True
        )
    except SensorUnavailable as exc:
        raise GateError(f"the trust calibration sensor is unavailable at {root}: {exc}") from exc
    drift: dict[tuple[str, str, str], dict[str, Any]] = {}
    for observation in scan.observations:
        if observation.kind != DRIFT_KIND:
            continue
        state = dict(observation.observed_state)
        key = (observation.subject.id, str(observation.current_state.get("level")), str(state["targetLevel"]))
        drift[key] = state
    skipped = {str(item.get("subjectId")) for item in scan.skipped}
    return drift, skipped


def evaluate(
    base: dict[tuple[str, str, str], dict[str, Any]],
    head: dict[tuple[str, str, str], dict[str, Any]],
) -> tuple[list[tuple[tuple[str, str, str], dict[str, Any]]], int, int, int]:
    """``(new drift, tolerated, resolved, frozen skipped)``. Pure; no I/O."""

    new: list[tuple[tuple[str, str, str], dict[str, Any]]] = []
    tolerated = frozen = 0
    for key in sorted(head):
        state = head[key]
        if state.get("frozen"):
            frozen += 1
            continue
        if key in base:
            tolerated += 1
        else:
            new.append((key, state))
    resolved = sum(1 for key in base if key not in head)
    return new, tolerated, resolved, frozen


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Block new trust calibration drift against the base ref.")
    parser.add_argument("--base", default=None, help="The branch or commit this change targets.")
    parser.add_argument("--pure-yaml", action="store_true", help="Parse with pure-Python YAML (slower).")
    args = parser.parse_args(argv)
    repo_root = REPO_ROOT
    started = time.monotonic()
    try:
        base_sha, label = resolve_base_ref(repo_root, args.base)
        with base_checkout(repo_root, base_sha) as base_tree, fast_yaml(not args.pure_yaml):
            base_drift, base_skipped = scan_drift(base_tree)
            head_drift, head_skipped = scan_drift(repo_root)
    except GateError as exc:
        print(f"cannot judge calibration drift: {exc}; fail closed", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - any unexpected failure must not read as a verdict
        print(f"cannot judge calibration drift: {type(exc).__name__}: {exc}; fail closed", file=sys.stderr)
        return 2

    blind = sorted(head_skipped - base_skipped)
    new, tolerated, resolved, frozen = evaluate(base_drift, head_drift)
    for (skill_id, level, target), state in new:
        print(
            f"[NEW DRIFT] {skill_id}: stored {level}, computed grade {state.get('trustGrade')} "
            f"(TM {state.get('trustMagnitude')}) publishes {target} ({state.get('direction')}). "
            f"Run in this PR: gaia dev calibrate {skill_id} {target}",
            file=sys.stderr,
        )
    for subject in blind:
        print(f"[UNEVALUATED] {subject}: the head leaves this named record unscored", file=sys.stderr)

    print("\n============ Trust Calibration Drift Gate ============")
    print(f"Base:                 {label} @ {base_sha[:12]}")
    print(f"New drift:            {len(new)} (fails if > 0)")
    print(f"Tolerated (at base):  {tolerated}")
    print(f"Resolved since base:  {resolved}")
    print(f"Frozen (skipped):     {frozen}")
    print(f"Unevaluated at head:  {len(blind)} (fails closed if > 0)")
    print(f"Runtime:              {time.monotonic() - started:.1f}s")
    print("======================================================")
    if blind:
        print("FAILED: the head has named records the sensor could not evaluate.", file=sys.stderr)
        return 2
    if new:
        print(
            "FAILED: this change introduces calibration drift. Recalibrate in the same PR with the "
            "commands above (the gate never calibrates).",
            file=sys.stderr,
        )
        return 1
    print("PASSED: no new calibration drift.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
