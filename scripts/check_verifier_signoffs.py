#!/usr/bin/env python3
"""Check verifier sign-offs on a GitHub PR.

A "verifier sign-off" is an approved review from a GitHub account that holds a
4★+ named skill in registry/named-skills.json.

Usage:
  python scripts/check_verifier_signoffs.py --pr <PR_NUMBER> [--min-signoffs N]

Environment:
  GITHUB_TOKEN  — personal access token or Actions token with pull-requests read scope.
  GITHUB_REPOSITORY — owner/repo (e.g. "mbtiongson1/gaia-skill-tree").
                      Falls back to reading from git remote.

Exit code:
  0 — enough verifier sign-offs (>= --min-signoffs, default 2)
  1 — insufficient sign-offs
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_NAMED_SKILLS_INDEX = _REPO_ROOT / "registry" / "named-skills.json"


def loadVerifiers() -> set[str]:
    """Return the set of GitHub usernames that hold a 4★+ named skill."""
    verifiers: set[str] = set()
    if not _NAMED_SKILLS_INDEX.exists():
        return verifiers
    try:
        idx = json.loads(_NAMED_SKILLS_INDEX.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return verifiers

    for entries in idx.get("buckets", {}).values():
        for entry in entries:
            lvl = entry.get("level", "")
            if lvl and lvl[0].isdigit() and int(lvl[0]) >= 4:
                contributor = entry.get("contributor")
                if contributor:
                    verifiers.add(contributor)
    return verifiers


def detectRepository() -> str:
    """Return 'owner/repo' from GITHUB_REPOSITORY env var or git remote."""
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if repo:
        return repo
    # Fall back to parsing origin remote
    import subprocess
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, cwd=str(_REPO_ROOT),
        )
        url = result.stdout.strip()
        # https://github.com/owner/repo.git  or  git@github.com:owner/repo.git
        if "github.com" in url:
            if url.startswith("git@"):
                path = url.split(":", 1)[-1]
            else:
                path = url.split("github.com/", 1)[-1]
            path = path.removesuffix(".git")
            return path
    except Exception:
        pass
    return "mbtiongson1/gaia-skill-tree"


def fetchPRReviews(prNumber: int, repo: str, token: str) -> list[dict]:
    """Fetch reviews for the given PR from the GitHub REST API."""
    url = f"https://api.github.com/repos/{repo}/pulls/{prNumber}/reviews"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        print(f"ERROR: GitHub API returned HTTP {exc.code} for PR #{prNumber}.", file=sys.stderr)
        print(f"  URL: {url}", file=sys.stderr)
        return []
    except Exception as exc:
        print(f"ERROR: Could not reach GitHub API: {exc}", file=sys.stderr)
        return []


def countVerifierApprovals(reviews: list[dict], verifiers: set[str]) -> list[str]:
    """Return the list of verifier logins who approved (latest state per reviewer)."""
    latestState: dict[str, str] = {}
    for review in reviews:
        reviewer = (review.get("user") or {}).get("login", "")
        state = review.get("state", "")
        if reviewer:
            latestState[reviewer] = state
    return [
        login for login, state in latestState.items()
        if state == "APPROVED" and login in verifiers
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check that a PR has enough verifier sign-off approvals."
    )
    parser.add_argument("--pr", type=int, required=True, metavar="PR_NUMBER")
    parser.add_argument("--min-signoffs", type=int, default=2, metavar="N",
                        help="Minimum number of verifier approvals required (default: 2).")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("WARNING: GITHUB_TOKEN not set — skipping verifier sign-off check.", file=sys.stderr)
        print("  In production CI, this step is required.", file=sys.stderr)
        # Allow in environments without a token (e.g. local testing without auth)
        return 0

    repo = detectRepository()
    verifiers = loadVerifiers()

    if not verifiers:
        # Bootstrap: no 4★+ verifiers exist yet; skip the gate.
        print(f"INFO: No verifiers found in registry — bootstrap state, skipping sign-off gate.")
        return 0

    print(f"Verifier sign-off check: PR #{args.pr} in {repo}")
    print(f"  Known verifiers (4★+): {sorted(verifiers)}")

    reviews = fetchPRReviews(args.pr, repo, token)
    if not reviews:
        # If we got no reviews (API issue or no reviews yet), treat as insufficient
        print(f"  No reviews found (0/{args.min_signoffs} verifier approvals).", file=sys.stderr)
        print(f"ERROR: Insufficient verifier sign-offs (0 < {args.min_signoffs}).", file=sys.stderr)
        return 1

    approvers = countVerifierApprovals(reviews, verifiers)
    count = len(approvers)
    print(f"  Verifier approvals: {count} — {sorted(approvers)}")

    if count >= args.min_signoffs:
        print(f"  PASS: {count}/{args.min_signoffs} verifier approvals met.")
        return 0

    print(
        f"ERROR: Only {count} verifier approval(s) found; need {args.min_signoffs}.",
        file=sys.stderr,
    )
    print("  Add approvals from accounts with 4★+ named skills in registry/named-skills.json.",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
