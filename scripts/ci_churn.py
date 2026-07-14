#!/usr/bin/env python3
"""
ci_churn.py — CI churn cost calculator for a pull request.

Measures how many commits and how many CI-compute seconds were spent on
avoidable "fix the CI" push rounds — pushes that only existed because a
problem wasn't caught before the first push.

Usage
─────
  python3 scripts/ci_churn.py <pr>
  python3 scripts/ci_churn.py <pr> --json
  python3 scripts/ci_churn.py <pr> --owner myorg --repo myrepo
  python3 scripts/ci_churn.py <pr> --session-log ~/.pi/sessions/latest.jsonl

Flags
  --json            Emit machine-readable JSON instead of prose
  --owner / --repo  Override repo detection (defaults to git remote origin)
  --session-log     Path to a pi or claude-code JSONL session log.
                    When provided, agent turn durations are parsed and
                    correlated with churn commits to produce an
                    "agent time burned" estimate alongside CI compute.

Exit codes
  0  Report printed successfully
  1  gh CLI not found or not authenticated
  2  PR not found or API error

Requires
  gh CLI (authenticated), Python 3.8+, no third-party packages.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from typing import Optional

# ---------------------------------------------------------------------------
# Commit classification
# ---------------------------------------------------------------------------

# Ordered — first match wins.  Patterns are matched case-insensitively against
# the full commit message (subject + body if available).
_CI_FIX_PATTERNS = [
    r"\bci[\s_-]fix\b",
    r"\bfix[\s(]ci\b",
    r"fix.*\bimport\b",
    r"fix.*\bsmoke.?test\b",
    r"\blazy.?import\b",
    r"\brestore.*export\b",
    r"\bopen_pr\b.*\bexport\b",
    r"\bcodeql\b",
    r"\burlparse\b",
    r"\bsubstring.*sanitiz",
    r"\bImportError\b",
    r"\bwheel.*smoke\b",
    r"\bpackaging.*crash\b",
    r"fix.*\bwheel\b",
    r"\bpyaml\b",
    r"fix.*\bcrash\b.*\bimport\b",
    r"\brebase\b.*\bconflict\b",
    r"\bconflict\b.*\brebase\b",
]

_REVIEW_FIX_PATTERNS = [
    r"\bper\s+review\b",
    r"\baddress\s+review\b",
    r"\bfrom\s+review\b",
    r"\breview\s+findings\b",
    r"\breview\s+items\b",
    r"\breview\s+feedback\b",
    r"\bper\s+code\s+review\b",
]


def classify_commit(message: str, replaced: bool = False) -> str:
    """Return 'replaced', 'ci-fix', 'review-fix', or 'feature'.

    'replaced' is returned for commits that were force-pushed away — they are
    churn by definition regardless of their message content, since the entire
    push round was discarded.
    """
    if replaced:
        return "replaced"
    msg = message.lower()
    for pat in _CI_FIX_PATTERNS:
        if re.search(pat, msg):
            return "ci-fix"
    for pat in _REVIEW_FIX_PATTERNS:
        if re.search(pat, msg):
            return "review-fix"
    return "feature"


# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------

def _gh(*args: str) -> dict | list:
    """Run `gh api <args>` and return parsed JSON, or raise on error.

    Note: on Windows with Git bash, leading slashes in API paths are rewritten
    as filesystem paths.  All callers must use paths WITHOUT a leading slash
    (e.g. 'repos/owner/repo/...' not '/repos/owner/repo/...').
    gh api accepts both forms; omitting the slash avoids the rewrite.
    """
    cmd = ["gh", "api", "--paginate"] + list(args)
    result = subprocess.run(
        cmd, capture_output=True, text=True, check=False,
        encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"gh api failed ({result.returncode}): {result.stderr.strip()}"
        )
    # gh --paginate may concatenate multiple JSON arrays; handle both forms.
    raw = result.stdout.strip()
    if raw.startswith("[") and raw.endswith("]["):
        # Multiple pages of arrays: join them
        import re as _re
        items = _re.findall(r'\[.*?\]', raw, _re.DOTALL)
        merged: list = []
        for chunk in items:
            try:
                merged.extend(json.loads(chunk))
            except json.JSONDecodeError:
                pass
        return merged
    return json.loads(raw)


def detect_repo(owner: Optional[str], repo: Optional[str]) -> tuple[str, str]:
    """Return (owner, repo) from args or git remote origin."""
    if owner and repo:
        return owner, repo
    try:
        remote = subprocess.check_output(
            ["git", "config", "--get", "remote.origin.url"],
            text=True, stderr=subprocess.DEVNULL
        ).strip()
    except subprocess.CalledProcessError:
        sys.exit("Could not detect repo from git remote. Pass --owner and --repo.")
    # git@github.com:owner/repo.git  or  https://github.com/owner/repo
    m = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$", remote)
    if not m:
        sys.exit(f"Could not parse GitHub owner/repo from remote: {remote}")
    return m.group(1), m.group(2)


def get_pr_commits(pr: int, owner: str, repo: str) -> list[dict]:
    """Return list of {sha, message} for all commits currently on the PR branch."""
    data = _gh(f"repos/{owner}/{repo}/pulls/{pr}/commits")
    return [
        {
            "sha": c["sha"],
            "short": c["sha"][:9],
            "message": c["commit"]["message"].split("\n")[0],  # subject line only
            "replaced": False,
        }
        for c in (data if isinstance(data, list) else [])
    ]


def get_force_pushed_shas(
    pr: int,
    owner: str,
    repo: str,
    current_shas: set[str],
) -> list[dict]:
    """Return commits whose CI runs are invisible because they were force-pushed away.

    Strategy — fork push-event ``before`` SHAs:

    1. Fetch the PR's ``head.ref`` (branch name) and ``head.repo.full_name``
       (the fork that owns the branch).
    2. Query push events on the fork repo:
       ``GET /repos/{fork_owner}/{fork_repo}/events?per_page=100``
    3. For each ``PushEvent`` whose ``payload.ref`` matches the PR branch,
       collect ``payload.before`` — the SHA that was on the branch *before*
       the push.  This is the replaced commit.
    4. Fetch CI runs for each replaced SHA from the *base* repo (where CI runs).
    5. Fetch commit messages for display; fall back gracefully if unavailable.

    Why not the timeline API?
    The PR timeline's ``committed`` events only record the current branch tip
    for fork PRs — replaced commits were never observed on the upstream side.
    ``head_ref_force_pushed`` carries only the *new* SHA, not the old one.

    Why not ``actions/runs?head_branch=...``?
    GitHub's API does not reliably filter by branch names containing slashes;
    the query returns thousands of unrelated runs.

    GitHub Events retention: ~90 days.  Adequate for measuring recent PR churn.

    Returns a list of {sha, short, message, replaced=True} dicts.
    """
    try:
        pr_info = _gh(f"repos/{owner}/{repo}/pulls/{pr}")
        if not isinstance(pr_info, dict):
            return []

        branch = pr_info.get("head", {}).get("ref", "")
        head_repo = (pr_info.get("head", {}).get("repo") or {}).get("full_name", "")
        if not branch or not head_repo:
            return []

        ref_full = f"refs/heads/{branch}"

        # Query push events on the fork.  Each PushEvent carries:
        #   payload.before = SHA that was on the branch before the push
        #   payload.after  = SHA on the branch after the push
        #   payload.ref    = full ref name (refs/heads/...)
        try:
            events = _gh(f"repos/{head_repo}/events?per_page=100")
        except RuntimeError:
            return []  # fork inaccessible (private, deleted, etc.)

        if not isinstance(events, list):
            return []

        _ZERO = "0000000000000000000000000000000000000000"
        replaced: dict[str, str] = {}  # sha -> message

        for evt in events:
            if evt.get("type") != "PushEvent":
                continue
            payload = evt.get("payload", {})
            if payload.get("ref") != ref_full:
                continue
            before = payload.get("before", "")
            if not before or before == _ZERO or before in current_shas:
                continue
            if before in replaced:
                continue

            # `before` is exactly the branch HEAD that had CI run on it before
            # being replaced.  We only need this SHA — no parent walk needed.
            # (CI only runs on the branch tip; parent commits in the chain don't
            # get their own CI runs, so walking back into history just collects
            # unrelated main-branch commits.)
            try:
                commit = _gh(f"repos/{owner}/{repo}/git/commits/{before}")
                msg = (
                    commit.get("message", "").split("\n")[0]
                    if isinstance(commit, dict) else ""
                )
            except Exception:
                msg = "(commit on fork — message unavailable)"
            replaced[before] = msg

        return [
            {"sha": sha, "short": sha[:9], "message": msg, "replaced": True}
            for sha, msg in replaced.items()
        ]

    except Exception:
        # Never crash the caller — force-push history is best-effort
        return []


def get_runs_for_sha(sha: str, owner: str, repo: str) -> list[dict]:
    """Return all workflow runs triggered by this commit SHA."""
    # Use URL query string instead of --field to avoid Git-bash path rewriting
    # on Windows which mangles /repos/... leading slashes.
    data = _gh(
        f"repos/{owner}/{repo}/actions/runs?head_sha={sha}&per_page=50"
    )
    runs = data.get("workflow_runs", []) if isinstance(data, dict) else []
    result = []
    for r in runs:
        try:
            started = datetime.fromisoformat(
                r["run_started_at"].replace("Z", "+00:00")
            )
            ended = datetime.fromisoformat(
                r["updated_at"].replace("Z", "+00:00")
            )
            duration_s = max(0, int((ended - started).total_seconds()))
        except Exception:
            duration_s = 0
        result.append({
            "name": r.get("name", "unknown"),
            "conclusion": r.get("conclusion") or r.get("status", "unknown"),
            "duration_s": duration_s,
            "run_id": r.get("id"),
            "html_url": r.get("html_url", ""),
        })
    return result


# ---------------------------------------------------------------------------
# Optional: parse pi / claude-code session log for agent turn durations
# ---------------------------------------------------------------------------

def parse_session_log(path: str) -> list[dict]:
    """Parse a pi or claude-code JSONL session log.

    Returns a list of {type, duration_ms} entries for turns that contain
    timing information.  Both formats supported:
      - pi:         {"type":"assistant","durationMs":12345,...}
      - claude-code: {"type":"assistant","usage":{"..."},"duration_ms":12345}
    Returns [] silently if the file is missing or unparsable.
    """
    turns = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ms = obj.get("durationMs") or obj.get("duration_ms")
                if ms and obj.get("type") in ("assistant", "tool_result"):
                    turns.append({"type": obj["type"], "duration_ms": int(ms)})
    except (OSError, IOError):
        pass
    return turns


# ---------------------------------------------------------------------------
# Core calculation
# ---------------------------------------------------------------------------

def _fmt_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    m, s = divmod(seconds, 60)
    if m < 60:
        return f"{m}m {s:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h {m:02d}m {s:02d}s"


def calculate_churn(
    commits: list[dict],
    runs_by_sha: dict[str, list[dict]],
    session_turns: list[dict],
) -> dict:
    """Compute churn metrics from commits + CI runs + optional session data.

    ``commits`` must include both the current-branch commits AND any
    force-pushed (replaced) commits returned by ``get_force_pushed_shas``.
    Each entry must have a ``replaced`` boolean field.
    """

    classified = []
    for c in commits:
        label = classify_commit(c["message"], replaced=c.get("replaced", False))
        runs = runs_by_sha.get(c["sha"], [])
        # Total CI compute this commit consumed (all workflows, pass or fail)
        total_s = sum(r["duration_s"] for r in runs)
        # Count how many workflows failed for this commit
        failures = [r for r in runs if r["conclusion"] in ("failure", "timed_out", "error")]
        classified.append({
            **c,
            "label": label,
            "runs": runs,
            "total_ci_s": total_s,
            "failure_count": len(failures),
            "failure_s": sum(r["duration_s"] for r in failures),
        })

    total_commits = len(classified)
    feature_commits = [c for c in classified if c["label"] == "feature"]
    review_fix_commits = [c for c in classified if c["label"] == "review-fix"]
    ci_fix_commits = [c for c in classified if c["label"] == "ci-fix"]
    # Replaced commits: entire push rounds discarded by force-push — 100% waste
    replaced_commits = [c for c in classified if c["label"] == "replaced"]

    avoidable_commits = review_fix_commits + ci_fix_commits + replaced_commits

    # CI compute burned on avoidable commits
    avoidable_ci_s = sum(c["total_ci_s"] for c in avoidable_commits)
    # CI compute that failed (the "we had to wait for this to fail" cost)
    failed_ci_s = sum(c["failure_s"] for c in classified)
    # Churn ratio — uses ALL commits (current + replaced) as denominator
    churn_ratio = len(avoidable_commits) / total_commits if total_commits else 0

    # Agent time estimate: each avoidable commit required at least one
    # wait-for-CI-to-fail cycle before the fix was written.
    # Minimum estimate = sum of all *failed* run durations (blocked wait time).
    # Full estimate = avoidable CI compute (because the fix run also consumed agent wait time).
    agent_wait_min_s = failed_ci_s
    agent_wait_full_s = avoidable_ci_s

    # Session log: total agent milliseconds in the session
    session_total_ms = sum(t["duration_ms"] for t in session_turns)

    # Root cause hints
    hints = _root_cause_hints(ci_fix_commits, replaced_commits)

    return {
        "total_commits": total_commits,
        "feature_count": len(feature_commits),
        "review_fix_count": len(review_fix_commits),
        "ci_fix_count": len(ci_fix_commits),
        "replaced_count": len(replaced_commits),
        "avoidable_count": len(avoidable_commits),
        "churn_ratio": round(churn_ratio, 3),
        "churn_pct": round(churn_ratio * 100, 1),
        "avoidable_ci_s": avoidable_ci_s,
        "failed_ci_s": failed_ci_s,
        "agent_wait_min_s": agent_wait_min_s,
        "agent_wait_full_s": agent_wait_full_s,
        "session_total_ms": session_total_ms,
        "commits": classified,
        "hints": hints,
    }


def _root_cause_hints(
    ci_fix_commits: list[dict],
    replaced_commits: list[dict] | None = None,
) -> list[str]:
    """Infer preventable local checks from ci-fix and replaced commit messages."""
    hints = []
    seen: set[str] = set()

    def add(hint: str) -> None:
        if hint not in seen:
            seen.add(hint)
            hints.append(hint)

    for c in ci_fix_commits:
        msg = c["message"].lower()
        if any(k in msg for k in ["import", "open_pr", "restore"]):
            add('python3 -c "from gaia_cli.main import main"  # import chain smoke test')
        if any(k in msg for k in ["test", "pytest", "smoke", "wheel", "packaging"]):
            add("python3 -m pytest tests/ -x -q --timeout=30          # fast local test gate")
        if any(k in msg for k in ["codeql", "urlparse", "sanitiz", "security"]):
            add("bandit -r src/ -ll                                    # security lint (catches CodeQL class)")
        if any(k in msg for k in ["yaml", "pyyaml", "lazy"]):
            add("pip show pyyaml >/dev/null 2>&1 || echo 'MISSING: pyyaml'  # dep presence check")
        if any(k in msg for k in ["rebase", "conflict", "merge"]):
            add("git fetch origin main && git rebase origin/main --dry-run   # rebase sanity")

    # When force-push rounds are present, surface the identity check hint.
    # The most common cause is author email not linked to a GitHub account.
    if replaced_commits:
        add(
            "git config user.email  # verify this matches a verified email at "
            "github.com/settings/emails"
        )

    if not hints:
        hints.append("python3 -m pytest tests/ -x -q  # general regression gate")

    return hints


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def format_text(pr: int, owner: str, repo: str, metrics: dict) -> str:
    c = metrics
    replaced_count = c.get("replaced_count", 0)

    commit_breakdown = (
        f"({c['feature_count']} feature · "
        f"{c['review_fix_count']} review-fix · "
        f"{c['ci_fix_count']} ci-fix"
        + (f" · {replaced_count} force-push-round" if replaced_count else "")
        + ")"
    )

    lines = [
        f"CI Churn Report — PR #{pr}  ({owner}/{repo})",
        "═" * 56,
        "",
        f"Commits: {c['total_commits']} total  {commit_breakdown}",
        f"Churn ratio: {c['churn_pct']}%  "
        f"({c['avoidable_count']} of {c['total_commits']} commits were avoidable)",
        "",
    ]

    if replaced_count:
        lines += [
            f"  ⚠  {replaced_count} force-push round(s) detected — CI runs on replaced",
            f"     commits are included in churn totals below.",
            "",
        ]

    if c["avoidable_count"] == 0:
        lines += [
            "✅ No churn detected — all commits were feature work.",
            "",
        ]
    else:
        lines += [
            f"CI compute burned on avoidable commits : {_fmt_duration(c['avoidable_ci_s'])}",
            f"CI compute on failed runs (all commits): {_fmt_duration(c['failed_ci_s'])}",
            f"Agent blocked-wait estimate (min / max): "
            f"{_fmt_duration(c['agent_wait_min_s'])} / {_fmt_duration(c['agent_wait_full_s'])}",
        ]
        if c["session_total_ms"]:
            session_s = c["session_total_ms"] // 1000
            pct = round(c["avoidable_ci_s"] / session_s * 100) if session_s else 0
            lines.append(
                f"Session agent time (from log)        : {_fmt_duration(session_s)}  "
                f"(churn ≈ {pct}% of session)"
            )
        lines.append("")

    # Commit breakdown table
    lines += [
        "Commit breakdown",
        "─" * 56,
        f"{'SHA':>9}  {'Label':14}  {'CI (s)':>8}  {'Fails':>5}  Message",
        f"{'─'*9}  {'─'*14}  {'─'*8}  {'─'*5}  {'─'*30}",
    ]
    for commit in c["commits"]:
        label_badge = {
            "feature":    "feature       ",
            "ci-fix":     "⚠ ci-fix      ",
            "review-fix": "△ review-fix  ",
            "replaced":   "✕ replaced    ",
        }.get(commit["label"], commit["label"].ljust(14))
        msg = commit["message"][:46]
        lines.append(
            f"{commit['short']:>9}  {label_badge}  "
            f"{commit['total_ci_s']:>8}  {commit['failure_count']:>5}  {msg}"
        )

    if c["avoidable_count"] > 0:
        lines += [
            "",
            "Suggested local pre-push checks",
            "─" * 56,
        ]
        for hint in c["hints"]:
            lines.append(f"  • {hint}")

    lines += ["", "─" * 56]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="CI churn cost calculator for a GitHub pull request."
    )
    parser.add_argument("pr", type=int, help="Pull request number")
    parser.add_argument("--owner", default=None, help="GitHub org/user (auto-detected from git remote)")
    parser.add_argument("--repo", default=None, help="GitHub repo name (auto-detected from git remote)")
    parser.add_argument("--json", dest="as_json", action="store_true", help="Emit JSON instead of prose")
    parser.add_argument(
        "--session-log",
        dest="session_log",
        default=None,
        metavar="PATH",
        help=(
            "Path to a pi or claude-code JSONL session log. "
            "Parses durationMs/duration_ms fields to estimate agent time burned on churn. "
            "Optional — omit to use CI API data only."
        ),
    )
    args = parser.parse_args()

    # Dependency check
    if subprocess.run(["gh", "auth", "status"], capture_output=True).returncode != 0:
        print("ERROR: gh CLI is not installed or not authenticated.", file=sys.stderr)
        sys.exit(1)

    owner, repo = detect_repo(args.owner, args.repo)

    print(f"Fetching commits for PR #{args.pr} ({owner}/{repo})…", file=sys.stderr)
    try:
        commits = get_pr_commits(args.pr, owner, repo)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)

    # Recover force-pushed commits invisible to /pulls/{pr}/commits
    current_shas = {c["sha"] for c in commits}
    print("Checking force-push history…", file=sys.stderr)
    replaced = get_force_pushed_shas(args.pr, owner, repo, current_shas)
    if replaced:
        print(
            f"  Found {len(replaced)} replaced commit(s) from "
            f"{sum(1 for c in replaced if c['replaced'])} force-push round(s).",
            file=sys.stderr,
        )

    all_commits = commits + replaced

    runs_by_sha: dict[str, list[dict]] = {}
    for i, c in enumerate(all_commits, 1):
        label = "(replaced)" if c.get("replaced") else ""
        print(f"  [{i}/{len(all_commits)}] runs for {c['short']} {label}…", file=sys.stderr)
        try:
            runs_by_sha[c["sha"]] = get_runs_for_sha(c["sha"], owner, repo)
        except RuntimeError:
            runs_by_sha[c["sha"]] = []

    session_turns = parse_session_log(args.session_log) if args.session_log else []

    metrics = calculate_churn(all_commits, runs_by_sha, session_turns)

    if args.as_json:
        print(json.dumps(metrics, indent=2, ensure_ascii=False))
    else:
        # Write with UTF-8 explicitly so em-dashes and box-drawing chars
        # render correctly on Windows terminals that default to cp1252.
        out = format_text(args.pr, owner, repo, metrics)
        sys.stdout.buffer.write(out.encode("utf-8", errors="replace") + b"\n")


if __name__ == "__main__":
    main()
