#!/usr/bin/env python3
"""Check verifier sign-offs on a GitHub PR.

A "verifier sign-off" is an approved review from a GitHub account that holds a
4★+ named skill in registry/named-skills.json.

Sprint D W2b (#905) extension: also validates benchmark-attestation files
under ``docs/verifier-signoffs/YYYY-MM/``. Each attestation file carries a
YAML frontmatter block linking a 4★+ verifier to a specific benchmark run
(skill, benchmarkId, score, datasetHash). Any file whose ``verifier`` is not
in the 4★+ set — or whose ``skill`` cannot be matched — fails the check.

Usage:
  python scripts/check_verifier_signoffs.py --pr <PR_NUMBER> [--min-signoffs N]
  python scripts/check_verifier_signoffs.py --check-attestations   # scan the signoff tree only

Environment:
  GITHUB_TOKEN  — personal access token or Actions token with pull-requests read scope.
  GITHUB_REPOSITORY — owner/repo (e.g. "gaia-research/gaia-skill-tree").
                      Falls back to reading from git remote.

Exit code:
  0 — enough verifier sign-offs AND every attestation file is well-formed & authorized
  1 — insufficient sign-offs or a malformed / unauthorized attestation was found
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path
from urllib.parse import urlparse

def is_github_remote(url: str) -> bool:
    if url.startswith("git@"):
        host = url.split("@", 1)[1].split(":", 1)[0]
    else:
        host = urlparse(url).hostname or ""
    return host == "github.com" or host.endswith(".github.com")

_REPO_ROOT = Path(__file__).resolve().parent.parent
_NAMED_SKILLS_INDEX = _REPO_ROOT / "registry" / "named-skills.json"
_SIGNOFFS_DIR = _REPO_ROOT / "docs" / "verifier-signoffs"


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


def loadKnownSkills() -> set[str]:
    """Return the set of `contributor/slug` ids known to the registry."""
    knownSkills: set[str] = set()
    if not _NAMED_SKILLS_INDEX.exists():
        return knownSkills
    try:
        idx = json.loads(_NAMED_SKILLS_INDEX.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return knownSkills
    for entries in idx.get("buckets", {}).values():
        for entry in entries:
            slug = entry.get("slug") or entry.get("id") or entry.get("skillId")
            if slug:
                knownSkills.add(slug)
    return knownSkills


_FRONTMATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\s*\r?\n", re.DOTALL)
_YAML_LINE_RE = re.compile(r"^([A-Za-z][\w-]*)\s*:\s*(.*?)\s*$")
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+\-]\d{2}:\d{2})$")


def _parseFrontmatter(text: str) -> dict[str, str] | None:
    """Return the leading YAML frontmatter as a flat dict, or None if missing.

    Deliberately hand-rolled: we do NOT want to add PyYAML as a dep for CI
    just to validate 6 flat fields. Numeric-looking values are left as
    strings; the caller parses further if needed.
    """
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return None
    block = m.group(1)
    out: dict[str, str] = {}
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lm = _YAML_LINE_RE.match(line)
        if not lm:
            continue
        key, value = lm.group(1), lm.group(2)
        # Strip surrounding quotes (either kind); we do not support nested / list values.
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        out[key] = value
    return out


def _iterAttestationFiles(root: Path) -> list[Path]:
    """Walk docs/verifier-signoffs/YYYY-MM/*.md — skip README-style files."""
    if not root.exists():
        return []
    files: list[Path] = []
    for monthDir in sorted(root.iterdir()):
        if not monthDir.is_dir():
            continue
        if not re.match(r"^\d{4}-\d{2}$", monthDir.name):
            continue
        for path in sorted(monthDir.glob("*.md")):
            if path.name.lower() in {"readme.md", "index.md"}:
                continue
            files.append(path)
    return files


def checkBenchmarkAttestations(
    signoffsDir: Path,
    verifiers: set[str],
    knownSkills: set[str],
) -> list[str]:
    """Validate every attestation file. Return a list of error strings (empty = pass).

    Each file must carry a YAML frontmatter block with:

      verifier:    4★+ GitHub handle
      skill:       contributor/slug in the registry
      benchmark:   semver-ish benchmarkId (e.g. humaneval@v1.0)
      score:       numeric
      datasetHash: 64-char lowercase hex sha256
      attestedAt:  ISO 8601 with timezone

    Only the first three carry authorization risk (unknown verifier /
    unknown skill / malformed benchmark id). The last three are format
    invariants — they must be present and well-formed but do not otherwise
    gate authorization.
    """
    errors: list[str] = []
    for path in _iterAttestationFiles(signoffsDir):
        rel = path.relative_to(_REPO_ROOT).as_posix() if _REPO_ROOT in path.parents else str(path)
        text = path.read_text(encoding="utf-8")
        fm = _parseFrontmatter(text)
        if fm is None:
            errors.append(f"{rel}: missing YAML frontmatter block (`--- ... ---`).")
            continue

        required = ("verifier", "skill", "benchmark", "score", "datasetHash", "attestedAt")
        missing = [k for k in required if not fm.get(k)]
        if missing:
            errors.append(f"{rel}: frontmatter missing fields: {missing}.")
            continue

        verifier = fm["verifier"]
        if verifier not in verifiers:
            errors.append(
                f"{rel}: verifier {verifier!r} is not in the 4★+ set "
                f"({sorted(verifiers) or '[]'} — see registry/named-skills.json)."
            )

        skill = fm["skill"]
        if knownSkills and skill not in knownSkills:
            # If we could not load the index at all (empty set), skip this
            # check — bootstrap mode. Only fire when we know something.
            errors.append(
                f"{rel}: skill {skill!r} is not present in registry/named-skills.json."
            )

        benchmark = fm["benchmark"]
        if "@" not in benchmark:
            errors.append(
                f"{rel}: benchmark {benchmark!r} must be versioned as '<name>@<version>'."
            )

        dsHash = fm["datasetHash"]
        if not _HASH_RE.match(dsHash):
            errors.append(
                f"{rel}: datasetHash {dsHash!r} must be 64-char lowercase hex sha256."
            )

        attestedAt = fm["attestedAt"]
        if not _ISO_RE.match(attestedAt):
            errors.append(
                f"{rel}: attestedAt {attestedAt!r} must be ISO 8601 with timezone "
                "(YYYY-MM-DDTHH:MM:SS[Z|+HH:MM])."
            )

        try:
            float(fm["score"])
        except (TypeError, ValueError):
            errors.append(f"{rel}: score {fm['score']!r} must be numeric.")

    return errors


def _runAttestationCheck() -> int:
    verifiers = loadVerifiers()
    knownSkills = loadKnownSkills()
    errors = checkBenchmarkAttestations(_SIGNOFFS_DIR, verifiers, knownSkills)
    if not _SIGNOFFS_DIR.exists() or not _iterAttestationFiles(_SIGNOFFS_DIR):
        print(f"No attestation files found under {_SIGNOFFS_DIR.relative_to(_REPO_ROOT) if _SIGNOFFS_DIR.exists() else 'docs/verifier-signoffs/'} — nothing to check.")
        return 0
    if errors:
        print("ERROR: benchmark attestation check failed:", file=sys.stderr)
        for err in errors:
            print(f"  • {err}", file=sys.stderr)
        return 1
    checked = len(_iterAttestationFiles(_SIGNOFFS_DIR))
    print(f"OK: {checked} attestation file(s) valid; verifier count = {len(verifiers)}.")
    return 0


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
        if is_github_remote(url):
            if url.startswith("git@"):
                path = url.split(":", 1)[-1]
            else:
                path = url.split("github.com/", 1)[-1]
            path = path.removesuffix(".git")
            return path
    except Exception:
        pass
    return "gaia-research/gaia-skill-tree"


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
    parser.add_argument("--pr", type=int, metavar="PR_NUMBER",
                        help="Check reviewer sign-offs on the given PR.")
    parser.add_argument("--min-signoffs", type=int, default=2, metavar="N",
                        help="Minimum number of verifier approvals required (default: 2).")
    parser.add_argument("--check-attestations", action="store_true",
                        help="Also (or only) validate docs/verifier-signoffs/**/*.md attestation files.")
    args = parser.parse_args()

    if args.check_attestations and args.pr is None:
        return _runAttestationCheck()

    if args.pr is None:
        parser.error("either --pr <N> or --check-attestations is required")

    # Always run the attestation check alongside the PR check — a malformed
    # attestation file must fail CI even if the PR has enough sign-offs.
    attestationRc = _runAttestationCheck()

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("WARNING: GITHUB_TOKEN not set — skipping verifier sign-off check.", file=sys.stderr)
        print("  In production CI, this step is required.", file=sys.stderr)
        # Allow in environments without a token (e.g. local testing without auth)
        return attestationRc

    repo = detectRepository()
    verifiers = loadVerifiers()

    if not verifiers:
        # Bootstrap: no 4★+ verifiers exist yet; skip the gate.
        print(f"INFO: No verifiers found in registry — bootstrap state, skipping sign-off gate.")
        return attestationRc

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
        return attestationRc

    print(
        f"ERROR: Only {count} verifier approval(s) found; need {args.min_signoffs}.",
        file=sys.stderr,
    )
    print("  Add approvals from accounts with 4★+ named skills in registry/named-skills.json.",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
