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
import tarfile
import tempfile
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASELINE_PATH = REPO_ROOT / "scripts" / "lint" / "ruff-baseline.json"

BLOCKING_EXACT = {"F821", "F811"}
BLOCKING_PREFIXES = ("F63", "F7")
RATCHET_CODES = {"F401", "S110", "S112", "E722"}
ADVISORY_CODES = {"BLE001"}


def normalize_message(msg: str | None) -> str:
    """Normalize a violation message by collapsing whitespace."""
    if not msg:
        return ""
    return " ".join(str(msg).strip().split())


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
    except OSError as exc:  # interpreter not launchable: fall through to plain `ruff`
        print(f"Note: cannot probe '{sys.executable} -m ruff': {exc}", file=sys.stderr)
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
        except OSError as exc:
            print(f"Error: cannot run git merge-base: {exc}", file=sys.stderr)
            return None
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
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
    filename = v.get("filename") or v.get("file", "")
    if not filename:
        rel_path = ""
    else:
        try:
            p = Path(filename)
            if not p.is_absolute():
                p = (repo_root / p).resolve()
            else:
                p = p.resolve()
            rel_path = p.relative_to(repo_root.resolve()).as_posix()
        except Exception:
            rel_path = str(filename).replace("\\", "/")

    loc = v.get("location")
    if isinstance(loc, dict):
        row = loc.get("row", v.get("line", 0))
        col = loc.get("column", v.get("column", 0))
    else:
        row = v.get("line", 0)
        col = v.get("column", 0)
    code = v.get("code", "")
    msg = normalize_message(v.get("message", ""))
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

    # Build baseline tracker (multiset of (file, code, normalized_message))
    baseline_pool: dict[tuple[str, str, str], int] = {}
    if baseline_data and "violations" in baseline_data:
        for b in baseline_data["violations"]:
            nb = normalize_violation(b, repo_root)
            key_exact = (nb["file"], nb["code"], normalize_message(nb.get("message", "")))
            baseline_pool[key_exact] = baseline_pool.get(key_exact, 0) + 1

    ratchet_failures: list[dict[str, Any]] = []
    pre_existing_count = 0

    for v in ratchet_candidates:
        if changed_files is not None and v["file"] not in changed_files:
            pre_existing_count += 1
            continue
        exact = (v["file"], v["code"], normalize_message(v.get("message", "")))
        if baseline_pool.get(exact, 0) > 0:
            baseline_pool[exact] -= 1
            pre_existing_count += 1
        else:
            ratchet_failures.append(v)

    return blocking_failures, ratchet_failures, advisory_warnings, pre_existing_count


def find_stale_entries(
    violations: list[dict[str, Any]],
    baseline_data: dict[str, Any] | None,
    changed_files: set[str] | None = None,
    repo_root: Path | None = None,
    checked_paths: Sequence[str | Path] | None = None,
) -> list[dict[str, Any]]:
    """Identify baseline entries that are no longer present.

    If changed_files is provided, only inspects baseline entries belonging
    to those changed files. If checked_paths is provided, only inspects entries
    belonging to files that were actually checked.
    """
    if not baseline_data or "violations" not in baseline_data:
        return []
    if repo_root is None:
        repo_root = REPO_ROOT

    resolved_checked = [
        (Path(p) if Path(p).is_absolute() else (repo_root / p)).resolve()
        for p in checked_paths
    ] if checked_paths else None

    # Index current ratchet violations by fingerprint
    current_pool: dict[tuple[str, str, str], int] = {}
    for v in violations:
        if classify_code(v.get("code", "")) == "ratchet":
            nv = normalize_violation(v, repo_root)
            fp = (nv["file"], nv["code"], normalize_message(nv["message"]))
            current_pool[fp] = current_pool.get(fp, 0) + 1

    stale: list[dict[str, Any]] = []
    for b in baseline_data["violations"]:
        nb = normalize_violation(b, repo_root)
        if changed_files is not None and nb["file"] not in changed_files:
            continue
        if resolved_checked is not None:
            b_path = (repo_root / nb["file"]).resolve()
            if not any(b_path == cp or cp in b_path.parents for cp in resolved_checked):
                continue
        fp = (nb["file"], nb["code"], normalize_message(nb["message"]))
        if current_pool.get(fp, 0) > 0:
            current_pool[fp] -= 1
        else:
            stale.append(nb)

    return stale


def load_baseline_from_git(
    repo_root: Path,
    base_ref: str,
    baseline_path: Path,
) -> tuple[dict[str, Any] | None, str | None]:
    """Load baseline JSON from a git ref; return (data, error_message)."""
    try:
        rel_path = baseline_path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return None, f"Baseline path {baseline_path} is outside repository root {repo_root}"

    res = subprocess.run(
        ["git", "show", f"{base_ref}:{rel_path}"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if res.returncode != 0:
        return None, f"Baseline file '{rel_path}' not found at git ref '{base_ref}'"

    try:
        data = json.loads(res.stdout)
        if not isinstance(data, dict) or "violations" not in data:
            return None, f"Invalid baseline format at git ref '{base_ref}'"
        return data, None
    except json.JSONDecodeError as exc:
        return None, f"Failed to parse baseline JSON at git ref '{base_ref}': {exc}"


def resolve_base_ref(repo_root: Path, base_arg: str | None = None) -> tuple[str | None, str]:
    """The one exact base commit to judge the baseline against: (commit, label) or (None, error).

    No search across other refs: an explicit ``--base``; else, in a pull request,
    ``origin/$GITHUB_BASE_REF``; else, on a push, the event's ``before`` commit (its
    parent for a new branch). Anything else, or a ref that does not resolve, is an
    error, and the gate fails closed rather than skip the monotonicity check.
    """
    if base_arg:
        candidate, source = base_arg, f"--base {base_arg}"
    elif os.environ.get("GITHUB_BASE_REF"):
        candidate = f"origin/{os.environ['GITHUB_BASE_REF']}"
        source = f"GITHUB_BASE_REF ({candidate})"
    elif os.environ.get("GITHUB_EVENT_NAME") == "push":
        event_path = os.environ.get("GITHUB_EVENT_PATH")
        if not event_path:
            return None, "push event payload is unavailable; cannot determine the base ref"
        try:
            with open(event_path, encoding="utf-8") as f:
                before = json.load(f).get("before")
        except (OSError, json.JSONDecodeError) as exc:
            return None, f"cannot read the push event payload: {exc}"
        if not isinstance(before, str) or not before:
            return None, "push event has no valid before SHA"
        candidate = before if before.strip("0") else "HEAD~1"
        source = f"push before {candidate}"
    else:
        return None, (
            "cannot determine the base ref; pass --base <ref> (the branch this change targets) "
            "or --base-baseline <ref_or_file>"
        )
    res = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{candidate}^{{commit}}"],
        cwd=repo_root, capture_output=True, text=True, check=False,
    )
    if res.returncode != 0 or not res.stdout.strip():
        return None, f"base ref {candidate} ({source}) does not resolve to a commit"
    return res.stdout.strip(), source


def scan_ref_findings(
    repo_root: Path, ref: str, ruff_bin: str | None = None
) -> list[dict[str, Any]]:
    """Ratchet-tier findings of ref's own sources, under this checkout's lint config.

    The base tree is exported from git (no worktree, nothing written in the
    checkout) and scanned with the head's ``pyproject.toml``, so a ref that predates
    the ruff config is judged by the same rules the baseline records.
    """
    scratch = Path(tempfile.mkdtemp(prefix="gaia-ruff-base-"))
    try:
        archive = scratch / "base.tar"
        with archive.open("wb") as out:
            done = subprocess.run(
                ["git", "archive", "--format=tar", ref], cwd=repo_root, stdout=out,
                stderr=subprocess.PIPE, check=False,
            )
        if done.returncode != 0:
            raise RuntimeError(f"git archive {ref} failed: {done.stderr.decode(errors='replace')[:200]}")
        tree = scratch / "tree"
        tree.mkdir()
        with tarfile.open(archive) as bundle:
            if hasattr(tarfile, "data_filter"):
                bundle.extractall(tree, filter="data")
            else:  # pragma: no cover - Python < 3.10.12
                bundle.extractall(tree)
        shutil.copyfile(repo_root / "pyproject.toml", tree / "pyproject.toml")
        findings = run_ruff(paths=None, repo_root=tree, ruff_bin=ruff_bin)
        return [
            normalize_violation(item, tree)
            for item in findings
            if classify_code(item.get("code", "")) == "ratchet"
        ]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def resolve_base_baseline(
    repo_root: Path,
    baseline_path: Path,
    base_baseline_arg: str | None = None,
    base_arg: str | None = None,
    ruff_bin: str | None = None,
) -> tuple[dict[str, Any] | None, str | None, str | None]:
    """Resolve the trusted base baseline for the shrink-only check, failing closed.

    Returns (base_baseline_data, base_ref_label, error_message). With an explicit
    ``--base-baseline`` that file or ref is used. Otherwise the single base ref from
    resolve_base_ref() is used: its committed baseline when it has one; when it has
    none (first adoption), a baseline made of the ratchet findings ruff reports at
    that ref, so an entry is allowed only if the base itself already had that
    finding. Any error returns no data, and the caller fails closed.
    """
    if base_baseline_arg:
        p = Path(base_baseline_arg)
        if not p.is_absolute():
            p = (repo_root / p).resolve()
        if p.is_file():
            data = load_baseline(p)
            if data is None:
                return None, str(p), f"Failed to load base baseline from file: {p}"
            return data, str(p), None
        data, err = load_baseline_from_git(repo_root, base_baseline_arg, baseline_path)
        if data is not None:
            return data, base_baseline_arg, None
        return None, base_baseline_arg, err

    ref, source = resolve_base_ref(repo_root, base_arg)
    if ref is None:
        return None, None, source
    try:
        rel_path = baseline_path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return None, ref, f"Baseline path {baseline_path} is outside repository root {repo_root}"
    present = subprocess.run(
        ["git", "cat-file", "-e", f"{ref}:{rel_path}"], cwd=repo_root, capture_output=True, check=False
    ).returncode == 0
    if present:
        data, err = load_baseline_from_git(repo_root, ref, baseline_path)
        return (data, f"{source} @ {ref[:12]}", None) if data is not None else (None, ref, err)
    try:
        findings = scan_ref_findings(repo_root, ref, ruff_bin)
    except (OSError, RuntimeError, tarfile.TarError) as exc:
        return None, ref, f"cannot scan base ref {ref} for first adoption: {exc}"
    label = f"{source} @ {ref[:12]} (no baseline there; first adoption judged against ruff findings at that ref)"
    return {"version": 1, "violations": findings}, label, None


def find_added_baseline_entries(
    current_baseline: dict[str, Any],
    base_baseline: dict[str, Any],
    repo_root: Path,
) -> list[dict[str, Any]]:
    """Identify entries in current_baseline that are not in base_baseline (shrink-only)."""
    base_pool: dict[tuple[str, str, str], int] = {}
    for item in base_baseline.get("violations", []):
        norm = normalize_violation(item, repo_root)
        fp = (norm["file"], norm["code"], normalize_message(norm["message"]))
        base_pool[fp] = base_pool.get(fp, 0) + 1

    added: list[dict[str, Any]] = []
    for item in current_baseline.get("violations", []):
        norm = normalize_violation(item, repo_root)
        fp = (norm["file"], norm["code"], normalize_message(norm["message"]))
        if base_pool.get(fp, 0) > 0:
            base_pool[fp] -= 1
        else:
            added.append(norm)

    return added


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
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as exc:
        print(f"Error: failed to execute '{cmd[0]}': {exc}", file=sys.stderr)
        sys.exit(2)

    # Ruff exits 1 when violations are found; that is normal
    if res.returncode not in (0, 1):
        print(f"Error executing ruff (exit code {res.returncode}):\n{res.stderr}", file=sys.stderr)
        exit_code = res.returncode if 1 <= res.returncode <= 255 else 2
        sys.exit(exit_code)

    stdout = res.stdout.strip()
    if not stdout:
        print(
            f"Error: ruff exited {res.returncode} with empty output. "
            f"Expected JSON report of violations (e.g. '[]' for clean scan).",
            file=sys.stderr,
        )
        sys.exit(2)

    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError as exc:
        print(f"Failed to parse ruff JSON output: {exc}\nRaw: {stdout[:500]}", file=sys.stderr)
        sys.exit(2)

    if not isinstance(parsed, list):
        print(
            f"Error: ruff JSON output must be a list, got {type(parsed).__name__}",
            file=sys.stderr,
        )
        sys.exit(2)

    if res.returncode == 1 and not parsed:
        print(
            "Error: ruff exited 1 with empty JSON list ([]). Expected violations.",
            file=sys.stderr,
        )
        sys.exit(2)

    for item in parsed:
        if not isinstance(item, dict):
            print(
                f"Error: ruff JSON output record must be a dict, got {type(item).__name__}: {item}",
                file=sys.stderr,
            )
            sys.exit(2)
        code = item.get("code")
        fn = item.get("filename") or item.get("file")
        msg = item.get("message")
        if not isinstance(code, str) or not code.strip():
            print(
                f"Error: ruff record missing valid string 'code': {item}",
                file=sys.stderr,
            )
            sys.exit(2)
        if not isinstance(fn, str) or not fn.strip():
            print(
                f"Error: ruff record missing valid string filename/file: {item}",
                file=sys.stderr,
            )
            sys.exit(2)
        if not isinstance(msg, str) or not msg.strip():
            print(
                f"Error: ruff record missing valid string 'message': {item}",
                file=sys.stderr,
            )
            sys.exit(2)
        loc = item.get("location")
        if loc is not None:
            if not isinstance(loc, dict):
                print(
                    f"Error: ruff record 'location' must be a dict: {item}",
                    file=sys.stderr,
                )
                sys.exit(2)
            if "row" in loc and not isinstance(loc["row"], int):
                print(
                    f"Error: ruff record location 'row' must be an int: {item}",
                    file=sys.stderr,
                )
                sys.exit(2)
            if "column" in loc and not isinstance(loc["column"], int):
                print(
                    f"Error: ruff record location 'column' must be an int: {item}",
                    file=sys.stderr,
                )
                sys.exit(2)

    return parsed


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Multi-tier Ruff lint gate for Gaia.")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--update-baseline",
        action="store_true",
        help="Record current ratchet violations into baseline JSON and exit.",
    )
    mode_group.add_argument(
        "--prune-baseline",
        action="store_true",
        help="Prune stale entries from baseline JSON and exit.",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=DEFAULT_BASELINE_PATH,
        help="Path to ruff baseline JSON.",
    )
    parser.add_argument(
        "--base-baseline",
        type=str,
        default=None,
        help="Path or git ref for the trusted base baseline to verify monotonicity (shrink-only).",
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
        "--stale",
        choices=["warn", "fail", "ignore"],
        default="warn",
        help="Action on stale baseline entries in changed files (warn, fail, ignore).",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Specific files or directories to check (default: whole repo config).",
    )

    args = parser.parse_args(argv)
    repo_root = REPO_ROOT
    baseline_path = (
        Path(args.baseline) if Path(args.baseline).is_absolute() else (repo_root / args.baseline)
    ).resolve()

    violations = run_ruff(paths=args.paths, repo_root=repo_root, ruff_bin=args.ruff_bin)

    if args.update_baseline:
        if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
            print(
                "Error: --update-baseline cannot be run in CI. "
                "CI enforces that the baseline only shrinks against the base branch.",
                file=sys.stderr,
            )
            return 2

        ratchet_only = [v for v in violations if classify_code(v.get("code", "")) == "ratchet"]
        target_paths = [
            (Path(p) if Path(p).is_absolute() else (repo_root / p)).resolve()
            for p in args.paths
        ] if args.paths else None

        if target_paths is not None and baseline_path.is_file():
            existing = load_baseline(baseline_path)
            if existing is None:
                return 2
            if "violations" in existing:
                kept_outside = []
                for b in existing["violations"]:
                    nb = normalize_violation(b, repo_root)
                    b_path = (repo_root / nb["file"]).resolve()
                    if not any(b_path == tp or tp in b_path.parents for tp in target_paths):
                        kept_outside.append(nb)
                ratchet_only.extend(kept_outside)

        saved = save_baseline(ratchet_only, baseline_path, repo_root)
        print(
            f"Baseline written to {baseline_path} "
            f"({saved['total_ratchet_violations']} ratchet violations recorded)."
        )
        base_baseline, base_ref_label, _ = resolve_base_baseline(
            repo_root=repo_root,
            baseline_path=baseline_path,
            base_baseline_arg=args.base_baseline,
            base_arg=args.base,
            ruff_bin=args.ruff_bin,
        )
        if base_baseline is not None:
            added = find_added_baseline_entries(saved, base_baseline, repo_root)
            if added:
                print(
                    f"Warning: --update-baseline added {len(added)} violation(s) "
                    f"not in base ref '{base_ref_label}'. The gate will reject this baseline "
                    f"unless resolved or pruned.",
                    file=sys.stderr,
                )
        return 0

    if args.prune_baseline:
        baseline_data = load_baseline(baseline_path)
        if baseline_data is None:
            return 2

        current_ratchet = [
            v for v in violations if classify_code(v.get("code", "")) == "ratchet"
        ]
        current_pool: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
        for v in current_ratchet:
            nv = normalize_violation(v, repo_root)
            fp = (nv["file"], nv["code"], normalize_message(nv["message"]))
            current_pool.setdefault(fp, []).append(nv)

        target_paths = [
            (Path(p) if Path(p).is_absolute() else (repo_root / p)).resolve()
            for p in args.paths
        ] if args.paths else None

        kept_entries: list[dict[str, Any]] = []
        pruned_count = 0
        for b in baseline_data.get("violations", []):
            nb = normalize_violation(b, repo_root)
            b_path = (repo_root / nb["file"]).resolve()
            if target_paths is not None:
                is_targeted = any(
                    b_path == tp or tp in b_path.parents
                    for tp in target_paths
                )
                if not is_targeted:
                    kept_entries.append(nb)
                    continue

            fp = (nb["file"], nb["code"], normalize_message(nb["message"]))
            if current_pool.get(fp):
                matched = current_pool[fp].pop(0)
                kept_entries.append(matched)
            else:
                pruned_count += 1

        saved = save_baseline(kept_entries, baseline_path, repo_root)
        remaining = saved["total_ratchet_violations"]
        entry_str = "entry" if pruned_count == 1 else "entries"
        print(f"Pruned {pruned_count} stale {entry_str}; {remaining} entries remain.")
        return 0

    baseline_data = load_baseline(baseline_path)
    if baseline_data is None:
        return 2

    base_baseline, base_ref_label, base_err = resolve_base_baseline(
        repo_root=repo_root,
        baseline_path=baseline_path,
        base_baseline_arg=args.base_baseline,
        base_arg=args.base,
        ruff_bin=args.ruff_bin,
    )
    if base_baseline is None:
        # Never skip the shrink-only check: an unresolvable base is a failure, not a pass.
        print(f"Error: could not resolve the base baseline: {base_err}", file=sys.stderr)
        return 2
    if base_ref_label and "first adoption" in base_ref_label:
        print(f"[INFO] baseline growth is judged against {base_ref_label}.")

    added_baseline_entries = find_added_baseline_entries(
        current_baseline=baseline_data,
        base_baseline=base_baseline,
        repo_root=repo_root,
    )

    changed_files = get_changed_files(repo_root, base_ref=args.base)
    if changed_files is None:
        return 2

    effective_baseline = baseline_data
    if added_baseline_entries:
        effective_baseline = base_baseline

    blocking, ratchet, advisory, pre_existing_count = evaluate_violations(
        violations=violations,
        baseline_data=effective_baseline,
        changed_files=changed_files,
        repo_root=repo_root,
    )

    stale_entries: list[dict[str, Any]] = []
    if args.stale != "ignore":
        stale_entries = find_stale_entries(
            violations=violations,
            baseline_data=baseline_data,
            changed_files=changed_files,
            repo_root=repo_root,
            checked_paths=args.paths,
        )

    # Print baseline additions
    for b in added_baseline_entries:
        print(
            f"[BASELINE] {b['file']}:{b['line']}:{b['column']}: "
            f"{b['code']} {b['message']} (added to baseline; baseline is shrink-only)",
            file=sys.stderr,
        )

    # Print advisory warnings
    for a in advisory:
        print(f"[ADVISORY] {a['file']}:{a['line']}:{a['column']}: {a['code']} {a['message']}")

    # Print stale warnings
    for s in stale_entries:
        stream = sys.stderr if args.stale == "fail" else sys.stdout
        print(
            f"[STALE] {s['file']}:{s['line']}:{s['column']}: {s['code']} {s['message']}",
            file=stream,
        )

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
    print(f"Baseline additions:   {len(added_baseline_entries)} (fails if > 0; shrink-only vs {base_ref_label})")
    if args.stale != "ignore":
        print(f"Stale baseline entries: {len(stale_entries)}")
    print("=============================================================")

    has_error = False
    if blocking or ratchet or added_baseline_entries:
        has_error = True

    if added_baseline_entries:
        print(
            f"FAILED: Found {len(added_baseline_entries)} added baseline entries. "
            f"Baseline is not monotonic against base ref '{base_ref_label}' (shrink only).",
            file=sys.stderr,
        )

    if args.stale == "fail" and stale_entries:
        print(
            f"FAILED: Found {len(stale_entries)} stale baseline entries in changed files with --stale fail.",
            file=sys.stderr,
        )
        has_error = True

    if has_error:
        print("FAILED: Ruff multi-tier gate failed.", file=sys.stderr)
        return 1

    print("PASSED: Ruff multi-tier gate passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
