"""
gaia dev sync-upstream <skill-id> --version <tag> --source-url <url>

Writes (or updates) the ``upstream:`` frontmatter block on a named skill
AND appends a ``timeline.action: upstream_synced`` event.  Both writes are
atomic (built in memory, flushed in one write call) — either both land or
neither does.

CLI Pre-Flight checks (per CLAUDE.md CLI Pre-Flight Rule):
  1. Skill must exist in registry/named/**/*.md.
  2. --version must match ``^v?\\d+\\.\\d+\\.\\d+.*$``.
  3. --source-url must be a github.com/{owner}/{repo}/releases/tag/{tag} URL
     whose owner/repo matches the skill's existing upstream.repo OR the repo
     derived from links.github.
  4. Refuses if upstream.version already equals the target (already synced).
  5. Skill must be 2★+.
  6. --bootstrap refuses if the skill already has an upstream: block.
"""

from __future__ import annotations

import re
import sys
import datetime
from pathlib import Path
from typing import Any

from gaia_cli.commands.dev.helpers import (
    _find_named_file,
    _get_contributor,
    _run_dev_preflights,
    _fail_dev_preflight,
)
from gaia_cli.registry import named_skills_dir
from gaia_cli.frontmatter import (
    load_yaml_simple,
    split_frontmatter,
    upsert_top_level_block,
    append_timeline_event,
)

# ---------------------------------------------------------------------------
# Regex constants
# ---------------------------------------------------------------------------

_VERSION_RE = re.compile(r"^v?\d+\.\d+\.\d+.*$")
_RELEASE_URL_RE = re.compile(
    r"^https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/releases/tag/.+$"
)
_GITHUB_REPO_RE = re.compile(
    r"^https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)(?:/|$)"
)

# Ordered list of star levels so we can compare numerically.
_STAR_LEVELS = ["1★", "2★", "3★", "4★", "5★", "6★"]


def _parse_owner_repo_from_url(url: str) -> str | None:
    """Return 'owner/repo' extracted from a github.com URL, or None."""
    m = _GITHUB_REPO_RE.match(url or "")
    if m:
        return f"{m.group('owner')}/{m.group('repo')}"
    return None


def _utc_now_iso() -> str:
    return (
        datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


# ---------------------------------------------------------------------------
# Pre-flight helpers
# ---------------------------------------------------------------------------


def _pf_version_format(version: str) -> None:
    if not _VERSION_RE.match(version):
        _fail_dev_preflight(
            f"Invalid version tag: {version!r}. Must match ^v?\\d+\\.\\d+\\.\\d+.*$",
            fix="Use a semver-style tag such as v1.2.3 or 1.2.3-beta.",
        )


def _pf_source_url_format(source_url: str) -> None:
    if not _RELEASE_URL_RE.match(source_url):
        _fail_dev_preflight(
            f"Invalid --source-url: {source_url!r}. "
            "Must be https://github.com/<owner>/<repo>/releases/tag/<tag>.",
            fix="Copy the URL directly from the GitHub Releases page.",
        )


def _pf_source_url_matches_skill(source_url: str, meta: dict, skill_id: str) -> None:
    """Ensure source-url owner/repo matches upstream.repo or links.github."""
    url_repo = _parse_owner_repo_from_url(source_url)
    if not url_repo:
        return  # already rejected by format check above

    # Acceptable: existing upstream.repo block
    existing_upstream_repo = (meta.get("upstream") or {}).get("repo")
    if existing_upstream_repo and existing_upstream_repo == url_repo:
        return

    # Acceptable: derived from links.github
    links_github = (meta.get("links") or {}).get("github", "")
    derived_repo = _parse_owner_repo_from_url(links_github)
    if derived_repo and derived_repo == url_repo:
        return

    _fail_dev_preflight(
        f"Source URL owner/repo {url_repo!r} does not match skill's upstream.repo "
        f"({existing_upstream_repo!r}) or links.github-derived repo ({derived_repo!r}). "
        f"Nothing was written.",
        fix=(
            "Ensure --source-url points to the same GitHub repo as the skill's "
            "links.github field or existing upstream.repo."
        ),
    )


def _pf_not_already_synced(version: str, meta: dict) -> None:
    existing = (meta.get("upstream") or {}).get("version")
    if existing and existing == version:
        _fail_dev_preflight(
            f"Skill already synced at version {existing!r}. "
            "Use --force to re-record (not implemented in V1).",
            fix="Nothing was written. Bump the --tag value or omit --tag to check current state.",
        )


def _pf_min_two_stars(skill_id: str, meta: dict) -> None:
    level = meta.get("level", "1★")
    if level not in _STAR_LEVELS:
        _fail_dev_preflight(
            f"Skill {skill_id!r} has unrecognised level {level!r}; "
            "upstream tracking requires 2★+.",
            fix="Calibrate the skill to at least 2★ before enabling upstream tracking.",
        )
        return
    idx = _STAR_LEVELS.index(level)
    if idx < 1:  # < index of "2★"
        _fail_dev_preflight(
            f"Skill is at level {level}; upstream tracking requires 2★+.",
            fix=(
                "Run `gaia dev calibrate <skill-id> 2★` to promote before syncing upstream."
            ),
        )


def _pf_bootstrap_no_existing_block(skill_id: str, meta: dict, is_bootstrap: bool) -> None:
    if not is_bootstrap:
        return
    if meta.get("upstream"):
        _fail_dev_preflight(
            f"--bootstrap was specified but skill {skill_id!r} already has an "
            "`upstream:` block. Nothing was written.",
            fix=(
                "Omit --bootstrap to update an existing upstream block. "
                "(--force is not implemented in V1.)"
            ),
        )


# ---------------------------------------------------------------------------
# Core command
# ---------------------------------------------------------------------------


def sync_upstream_command(args) -> None:
    """Implement ``gaia dev sync-upstream``."""
    registry_path = args.registry
    skill_id = args.skill_id.lstrip("/")
    version: str = args.tag
    source_url: str = args.source_url
    is_bootstrap: bool = getattr(args, "bootstrap", False)
    released_at: str | None = getattr(args, "released_at", None)
    mode: str = getattr(args, "mode", "components") or "components"
    dry_run: bool = getattr(args, "dry_run", False)
    user: str | None = getattr(args, "user", None)

    if released_at is None:
        print(
            "Warning: --released-at was not supplied; defaulting to current UTC timestamp. "
            "In production runs the watcher always passes the release's published_at.",
            file=sys.stderr,
        )
        released_at = _utc_now_iso()

    # --- Locate the named skill file ---
    named_dir = Path(named_skills_dir(registry_path))
    named_file = _find_named_file(named_dir, skill_id)
    if not named_file:
        print(
            f"Named skill '{skill_id}' not found in registry/named/. Nothing was written.",
            file=sys.stderr,
        )
        sys.exit(1)

    raw_text = named_file.read_text(encoding="utf-8")
    _fence, fm_text, _body = split_frontmatter(raw_text)
    meta: dict = load_yaml_simple(fm_text)

    # --- Pre-flight validation ---
    _run_dev_preflights([
        lambda: _pf_version_format(version),
        lambda: _pf_source_url_format(source_url),
        lambda: _pf_source_url_matches_skill(source_url, meta, skill_id),
        lambda: _pf_not_already_synced(version, meta),
        lambda: _pf_min_two_stars(skill_id, meta),
        lambda: _pf_bootstrap_no_existing_block(skill_id, meta, is_bootstrap),
    ])

    # --- Compute new upstream block ---
    url_repo = _parse_owner_repo_from_url(source_url)
    existing_repo = (meta.get("upstream") or {}).get("repo")
    repo = existing_repo or url_repo or ""

    old_version: str | None = (meta.get("upstream") or {}).get("version")
    synced_at = _utc_now_iso()

    new_upstream: dict[str, Any] = {
        "repo": repo,
        "version": version,
        "releasedAt": released_at,
        "syncedAt": synced_at,
        "sourceUrl": source_url,
        "mode": mode,
    }

    # --- Build timeline event ---
    contributor = user or _get_contributor()
    details = (
        "first-run baseline"
        if is_bootstrap
        else f"synced from {source_url}"
    )
    timeline_event: dict[str, Any] = {
        "timestamp": synced_at,
        "action": "upstream_synced",
        "contributor": contributor,
        "previousValue": old_version,
        "newValue": version,
        "details": details,
    }

    # --- Dry-run: print intended diff, no write ---
    if dry_run:
        import yaml  # pyyaml
        print("=== DRY RUN — no files written ===")
        print(f"\nupstream block would be written to {named_file}:")
        print(yaml.dump({"upstream": new_upstream}, sort_keys=False, allow_unicode=True))
        print("timeline event that would be appended:")
        print(yaml.dump(timeline_event, sort_keys=False, allow_unicode=True))
        return

    # --- Atomic write: compose full content in memory first ---
    new_text = upsert_top_level_block(raw_text, "upstream", new_upstream)
    new_text = append_timeline_event(new_text, timeline_event)

    # Single filesystem write — atomic from caller's perspective.
    named_file.write_text(new_text, encoding="utf-8")

    # --- Success message ---
    old_str = old_version or "(none)"
    suffix = " (bootstrap)" if is_bootstrap else ""
    print(f"Synced {skill_id}: {old_str} → {version}{suffix}")
