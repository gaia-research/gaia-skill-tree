#!/usr/bin/env python3
"""Multi-tier Ruff lint gate for Gaia.

Tiers:
1. Blocking (F821, F811, F63, F7):
   Zero tolerance. Fails if > 0 violations exist in any file.
2. Ratchet (F401, S110, S112, E722):
   Blocks only new violations in changed files vs git merge-base (or vs baseline).
   Untouched pre-existing violations pass safely.
3. Advisory (BLE001):
   Prints warning/advisory, never fails (exit code 0).
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASELINE_PATH = REPO_ROOT / "scripts" / "lint" / "ruff-baseline.json"

BLOCKING_EXACT = {"F821", "F811"}
BLOCKING_PREFIXES = ("F63", "F7")
RATCHET_CODES = {"F401", "S110", "S112", "E722"}
ADVISORY_CODES = {"BLE001"}


def classify_code(code: str) -> str:
    """Classify a ruff rule code into tier: 'blocking', 'ratchet', 'advisory', or 'other'."""
    if code in BLOCKING_EXACT or any(code.startswith(prefix) for prefix in BLOCKING_PREFIXES):
        return "blocking"
    if code in RATCHET_CODES:
        return "ratchet"
    if code in ADVISORY_CODES:
        return "advisory"
    return "other"


def find_ruff_cmd(ruff_bin: str | None = None) -> list[str]:
    """Locate the ruff executable."""
    if ruff_bin:
        return [ruff_bin]
    which_ruff = shutil.which("ruff")
    if which_ruff:
        return [which_ruff]
    venv_ruff = REPO_ROOT / ".venv" / "bin" / "ruff"
    if venv_ruff.is_file() and os.access(venv_ruff, os.X_OK):
        return [str(venv_ruff)]
    try:
        res = subprocess.run(
            [sys.executable, "-m", "ruff", "--version"],
            capture_output=True,
            check=False,
        )
        if res.returncode == 0:
            return [sys.executable, "-m", "ruff"]
    except Exception:
        pass
    return ["ruff"]


def get_merge_base(repo_root: Path, base_target: str | None = None) -> str | None:
    """Find git merge-base against base_target or standard remotes/branches."""
    candidates: list[str] = []
    if base_target:
        candidates.append(base_target)
    env_base = os.environ.get("GITHUB_BASE_REF")
    if env_base:
        candidates.append(f"origin/{env_base}")
        candidates.append(env_base)
    candidates.extend(["origin/main", "main", "HEAD~1"])

    for cand in candidates:
        if not cand:
            continue
        try:
            res = subprocess.run(
                ["git", "merge-base", "HEAD", cand],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception:
            continue
    return None


def get_changed_files(repo_root: Path, base_ref: str | None = None) -> set[str] | None:
    """Identify committed, working-tree, and individual untracked changes; fail closed."""
    try:
        target = base_ref
        new_branch = False
        if target is None and os.environ.get("GITHUB_EVENT_NAME") == "push":
            event_path = os.environ.get("GITHUB_EVENT_PATH")
            if not event_path:
                raise ValueError("push event payload is unavailable")
            with open(event_path, encoding="utf-8") as f:
                before = json.load(f).get("before")
            if before and before.strip("0"):
                target = before
            elif isinstance(before, str) and before and not before.strip("0"):
                # A new branch has no prior ref; HEAD~1 alone can miss earlier
                # pushed commits, so also conservatively check all tracked files.
                new_branch = True
                parent = subprocess.run(
                    ["git", "rev-parse", "--verify", "HEAD~1"],
                    cwd=repo_root, capture_output=True, check=False,
                )
                target = "HEAD~1" if parent.returncode == 0 else "HEAD"
            else:
                raise ValueError("push event has no valid before SHA")
        if target is None:
            target = get_merge_base(repo_root)
        if target is None:
            raise ValueError("cannot determine git base")

        def paths(*args: str) -> set[str]:
            result = subprocess.run(
                ["git", *args], cwd=repo_root, capture_output=True, check=True
            )
            return {os.fsdecode(p).replace("\\", "/") for p in result.stdout.split(b"\0") if p}

        # A range describes committed changes; a single ref includes working-tree changes.
        changed = paths("diff", "--name-only", "-z", target)
        changed |= paths("diff", "--name-only", "-z", "HEAD")
        changed |= paths("ls-files", "--others", "--exclude-standard", "-z")
        if new_branch:
            changed |= paths("ls-files", "-z")
        return changed
    except (OSError, subprocess.CalledProcessError, ValueError, json.JSONDecodeError) as exc:
        print(f"Error determining changed files: {exc}", file=sys.stderr)
        return None


def normalize_violation(v: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    """Normalize a ruff violation record with repo-relative posix path."""
    filename = v.get("filename", "")
    try:
        rel_path = Path(filename).resolve().relative_to(repo_root.resolve()).as_posix()
    except Exception:
        rel_path = filename.replace("\\", "/")

    loc = v.get("location") or {}
    row = loc.get("row", v.get("line", 0))
    col = loc.get("column", v.get("column", 0))
    code = v.get("code", "")
    msg = v.get("message", "")
    return {
        "file": rel_path,
        "line": row,
        "column": col,
        "code": code,
        "message": msg,
    }


def save_baseline(
    ratchet_violations: list[dict[str, Any]],
    baseline_path: Path,
    repo_root: Path,
) -> dict[str, Any]:
    """Serialize current ratchet violations to baseline JSON."""
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    entries = [normalize_violation(v, repo_root) for v in ratchet_violations]
    entries.sort(key=lambda e: (e["file"], e["line"], e["code"], e["message"]))

    counts_by_code: dict[str, int] = {}
    file_counts: dict[str, dict[str, int]] = {}
    for e in entries:
        code = e["code"]
        file_path = e["file"]
        counts_by_code[code] = counts_by_code.get(code, 0) + 1
        file_counts.setdefault(file_path, {})
        file_counts[file_path][code] = file_counts[file_path].get(code, 0) + 1

    data = {
        "version": 1,
        "total_ratchet_violations": len(entries),
        "counts_by_code": counts_by_code,
        "file_counts": file_counts,
        "violations": entries,
    }

    with open(baseline_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")

    return data


def load_baseline(baseline_path: Path) -> dict[str, Any] | None:
    """Load and validate the committed baseline, refusing malformed input."""
    try:
        with open(baseline_path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or data.get("version") != 1:
            raise ValueError("unsupported baseline format")
        entries = data.get("violations")
        if not isinstance(entries, list):
            raise ValueError("violations must be a list")
        for entry in entries:
            if (not isinstance(entry, dict) or
                any(not isinstance(entry.get(k), str) or not entry[k] for k in ("file", "code", "message")) or
                entry["code"] not in RATCHET_CODES):
                raise ValueError("invalid baseline violation")
        return data
    except (OSError, ValueError, TypeError) as exc:
        print(f"Error loading baseline {baseline_path}: {exc}", file=sys.stderr)
        return None


def evaluate_violations(
    violations: list[dict[str, Any]],
    baseline_data: dict[str, Any] | None,
    changed_files: set[str] | None = None,
    repo_root: Path | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], int]:
    """Evaluate violations against multi-tier rules and baseline.

    Returns:
        (blocking_failures, ratchet_failures, advisory_warnings, pre_existing_ratchet_count)
    """
    if repo_root is None:
        repo_root = REPO_ROOT

    normalized = [normalize_violation(v, repo_root) for v in violations]

    blocking_failures: list[dict[str, Any]] = []
    advisory_warnings: list[dict[str, Any]] = []
    ratchet_candidates: list[dict[str, Any]] = []

    for v in normalized:
        tier = classify_code(v["code"])
        if tier == "blocking":
            blocking_failures.append(v)
        elif tier == "advisory":
            advisory_warnings.append(v)
        elif tier == "ratchet":
            ratchet_candidates.append(v)

    # Build baseline tracker (multiset of (file, code, message) and fallback (file, code))
    baseline_pool: dict[tuple[str, str, str], int] = {}
    baseline_file_code_pool: dict[tuple[str, str], int] = {}
    if baseline_data and "violations" in baseline_data:
        for b in baseline_data["violations"]:
            key_exact = (b["file"], b["code"], b.get("message", ""))
            baseline_pool[key_exact] = baseline_pool.get(key_exact, 0) + 1
            key_fc = (b["file"], b["code"])
            baseline_file_code_pool[key_fc] = baseline_file_code_pool.get(key_fc, 0) + 1

    ratchet_failures: list[dict[str, Any]] = []
    pre_existing_count = 0

    unmatched = []
    # Reserve exact matches first so an earlier new finding cannot steal them.
    for v in ratchet_candidates:
        if changed_files is not None and v["file"] not in changed_files:
            pre_existing_count += 1
            continue
        exact = (v["file"], v["code"], v["message"])
        fc = (v["file"], v["code"])
        if baseline_pool.get(exact, 0):
            baseline_pool[exact] -= 1
            baseline_file_code_pool[fc] -= 1
            pre_existing_count += 1
        else:
            unmatched.append(v)

    for v in unmatched:
        fc = (v["file"], v["code"])
        if baseline_file_code_pool.get(fc, 0):
            baseline_file_code_pool[fc] -= 1
            pre_existing_count += 1
        else:
            ratchet_failures.append(v)

    return blocking_failures, ratchet_failures, advisory_warnings, pre_existing_count


def run_ruff(
    paths: Sequence[str] | None = None,
    repo_root: Path | None = None,
    ruff_bin: str | None = None,
) -> list[dict[str, Any]]:
    """Execute ruff check with JSON output format."""
    if repo_root is None:
        repo_root = REPO_ROOT

    cmd = find_ruff_cmd(ruff_bin) + ["check", "--output-format", "json"]
    if paths:
        cmd.extend(paths)

    try:
        res = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        print("Error: 'ruff' command not found. Please install ruff>=0.5.0.", file=sys.stderr)
        sys.exit(2)

    # Ruff exits 1 when violations are found; that is normal
    if res.returncode not in (0, 1):
        print(f"Error executing ruff (exit code {res.returncode}):\n{res.stderr}", file=sys.stderr)
        sys.exit(res.returncode)

    stdout = res.stdout.strip()
    if not stdout:
        return []

    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        print(f"Failed to parse ruff JSON output: {exc}\nRaw: {stdout[:500]}", file=sys.stderr)
        sys.exit(2)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Multi-tier Ruff lint gate for Gaia.")
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Record current ratchet violations into baseline JSON and exit.",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=DEFAULT_BASELINE_PATH,
        help="Path to ruff baseline JSON.",
    )
    parser.add_argument(
        "--base",
        type=str,
        default=None,
        help="Git merge-base target or commit ref.",
    )
    parser.add_argument(
        "--ruff-bin",
        type=str,
        default=None,
        help="Custom path to ruff executable.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Specific files or directories to check (default: whole repo config).",
    )

    args = parser.parse_args(argv)
    repo_root = REPO_ROOT
    baseline_path = args.baseline.resolve()

    violations = run_ruff(paths=args.paths, repo_root=repo_root, ruff_bin=args.ruff_bin)

    if args.update_baseline:
        ratchet_only = [v for v in violations if classify_code(v.get("code", "")) == "ratchet"]
        saved = save_baseline(ratchet_only, baseline_path, repo_root)
        print(
            f"Baseline written to {baseline_path} "
            f"({saved['total_ratchet_violations']} ratchet violations recorded)."
        )
        if args.update_baseline:
            return 0

    baseline_data = load_baseline(baseline_path)
    if baseline_data is None:
        return 2
    changed_files = get_changed_files(repo_root, base_ref=args.base)
    if changed_files is None:
        return 2

    blocking, ratchet, advisory, pre_existing_count = evaluate_violations(
        violations=violations,
        baseline_data=baseline_data,
        changed_files=changed_files,
        repo_root=repo_root,
    )

    # Print advisory warnings
    for a in advisory:
        print(f"[ADVISORY] {a['file']}:{a['line']}:{a['column']}: {a['code']} {a['message']}")

    # Print ratchet failures
    for r in ratchet:
        print(
            f"[RATCHET] {r['file']}:{r['line']}:{r['column']}: "
            f"{r['code']} {r['message']} (new violation in changed file)",
            file=sys.stderr,
        )

    # Print blocking failures
    for b in blocking:
        print(
            f"[BLOCKING] {b['file']}:{b['line']}:{b['column']}: {b['code']} {b['message']}",
            file=sys.stderr,
        )

    print("\n================ Ruff Multi-Tier Gate Report ================")
    print(f"Blocking violations:  {len(blocking)} (fails if > 0)")
    print(f"Ratchet violations:   {len(ratchet)} new ({pre_existing_count} pre-existing allowed)")
    print(f"Advisory warnings:    {len(advisory)} (BLE001 - non-blocking)")
    print("=============================================================")

    if blocking or ratchet:
        print("FAILED: Ruff multi-tier gate failed.", file=sys.stderr)
        return 1

    print("PASSED: Ruff multi-tier gate passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
