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

import datetime
import json
import re
import stat
import sys
import urllib.parse
from pathlib import Path
from typing import Any

from gaia_cli.canonicalTransaction import _atomic as _atomic_write_bytes
from gaia_cli.commands.dev.helpers import (
    _find_named_file,
    _get_contributor,
    _run_dev_preflights,
    _fail_dev_preflight,
    preflightNamedSkillMutable,
)
from gaia_cli.registry import named_skills_dir
from gaia_cli.frontmatter import (
    load_yaml_simple,
    split_frontmatter,
    upsert_top_level_block,
    append_timeline_event,
)

# ---------------------------------------------------------------------------
# Regex & validation constants
# ---------------------------------------------------------------------------

_VERSION_RE = re.compile(r"^v?\d+\.\d+\.\d+.*$")
_CANONICAL_REPO_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9-]*/[a-zA-Z0-9._-]+$")
_DATE_TIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)

# Ordered list of star levels so we can compare numerically.
_STAR_LEVELS = ["1★", "2★", "3★", "4★", "5★", "6★"]


def _is_valid_owner_repo(owner: str, repo: str) -> bool:
    """Return True if owner and repo are valid non-dot GitHub identifiers."""
    if not isinstance(owner, str) or not isinstance(repo, str):
        return False
    if not owner or not repo:
        return False
    if any(c.isspace() for c in owner) or any(c.isspace() for c in repo):
        return False
    if owner in {".", ".."} or repo in {".", ".."}:
        return False
    return bool(_CANONICAL_REPO_RE.fullmatch(f"{owner}/{repo}"))


def _parse_release_source_url(source_url: str) -> tuple[str, str, str] | None:
    """Parse a GitHub release tag URL into ``(owner, repo, decoded_tag)``.

    Rejects whitespace, non-https schemes, non-github.com hosts, userinfo,
    ports, literal queries (``?``), literal fragments (``#``), dot/dotdot
    owner/repo segments, and empty tags.
    """
    if not isinstance(source_url, str) or not source_url:
        return None
    if any(c.isspace() for c in source_url):
        return None
    if "?" in source_url or "#" in source_url:
        return None
    parsed = urllib.parse.urlsplit(source_url)
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != "github.com"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
        or parsed.query != ""
        or parsed.fragment != ""
    ):
        return None

    parts = parsed.path.lstrip("/").split("/", 4)
    if len(parts) != 5 or parts[2] != "releases" or parts[3] != "tag":
        return None
    owner, repo, raw_tag = parts[0], parts[1], parts[4]
    if not _is_valid_owner_repo(owner, repo):
        return None
    raw_tag = raw_tag.rstrip("/")
    if not raw_tag:
        return None
    decoded_tag = urllib.parse.unquote(raw_tag)
    if not decoded_tag or "\x00" in decoded_tag:
        return None
    return (owner, repo, decoded_tag)


def _parse_owner_repo_from_url(url: str) -> str | None:
    """Return 'owner/repo' extracted from a parsed github.com URL, or None."""
    if not isinstance(url, str) or not url or any(c.isspace() for c in url):
        return None
    parsed = urllib.parse.urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != "github.com"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
    ):
        return None
    segments = [s for s in parsed.path.split("/") if s]
    if len(segments) < 2:
        return None
    owner, repo = segments[0], segments[1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    if not _is_valid_owner_repo(owner, repo):
        return None
    return f"{owner}/{repo}"


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


def _pf_source_url_format(source_url: str, version: str | None = None) -> None:
    parsed = _parse_release_source_url(source_url)
    if not parsed:
        _fail_dev_preflight(
            f"Invalid --source-url: {source_url!r}. "
            "Must be https://github.com/<owner>/<repo>/releases/tag/<tag> "
            "with no query, fragment, userinfo, or whitespace.",
            fix="Copy the URL directly from the GitHub Releases page.",
        )
        return
    _, _, url_tag = parsed
    if version is not None and url_tag != version:
        _fail_dev_preflight(
            f"--source-url tag {url_tag!r} does not match --tag {version!r}. "
            "Nothing was written.",
            fix="Ensure --source-url points to the release tag matching --tag.",
        )


def _pf_repo_format(target_repo: str | None) -> None:
    if target_repo is None:
        return
    parts = target_repo.split("/") if isinstance(target_repo, str) else []
    if len(parts) != 2 or not _is_valid_owner_repo(parts[0], parts[1]):
        _fail_dev_preflight(
            f"Invalid --repo: {target_repo!r}. "
            "Must be <owner>/<repo> with valid identifiers and no whitespace.",
            fix="Provide a valid GitHub owner/repo such as ruvnet/agentdb.",
        )


def _normalize_repo_for_comparison(repo: Any) -> str | None:
    """Normalize owner/repo for case-insensitive comparison.

    Rejects non-strings, whitespace, dot/dotdot segments, and malformed
    owner/repo specifications.
    """
    if not isinstance(repo, str):
        return None
    parts = repo.split("/")
    if len(parts) != 2 or not _is_valid_owner_repo(parts[0], parts[1]):
        return None
    return repo.lower()


def _pf_source_url_matches_skill(
    source_url: str,
    meta: dict,
    skill_id: str,
    target_repo: str | None = None,
) -> None:
    """Ensure source-url owner/repo matches explicit --repo, upstream.repo, or links.github."""
    url_repo = _parse_owner_repo_from_url(source_url)
    if not url_repo:
        return  # already rejected by format check above

    norm_url_repo = _normalize_repo_for_comparison(url_repo)

    if target_repo is not None:
        norm_target = _normalize_repo_for_comparison(target_repo)
        if norm_url_repo and norm_target and norm_url_repo == norm_target:
            return
        _fail_dev_preflight(
            f"Source URL owner/repo {url_repo!r} does not match explicit --repo "
            f"{target_repo!r}. Nothing was written.",
            fix="Ensure --source-url points to the same GitHub repo as --repo.",
        )
        return

    # Acceptable when no --repo given: existing upstream.repo block (if present)
    existing_upstream_repo = (meta.get("upstream") or {}).get("repo")
    if existing_upstream_repo is not None:
        norm_existing = _normalize_repo_for_comparison(existing_upstream_repo)
        if norm_url_repo and norm_existing and norm_existing == norm_url_repo:
            return
        _fail_dev_preflight(
            f"Source URL owner/repo {url_repo!r} does not match skill's upstream.repo "
            f"({existing_upstream_repo!r}). Pass --repo to repoint explicitly. "
            f"Nothing was written.",
            fix=(
                "Ensure --source-url points to the skill's existing upstream.repo, "
                "or pass --repo <owner>/<repo> to repoint."
            ),
        )
        return

    # Acceptable when no upstream.repo exists: derived from links.github
    links_github = (meta.get("links") or {}).get("github", "")
    derived_repo = _parse_owner_repo_from_url(links_github)
    norm_derived = _normalize_repo_for_comparison(derived_repo)
    if norm_url_repo and norm_derived and norm_derived == norm_url_repo:
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


def _pf_not_already_synced(
    version: str,
    meta: dict,
    target_repo: str | None = None,
) -> None:
    existing_version = (meta.get("upstream") or {}).get("version")
    existing_repo = (meta.get("upstream") or {}).get("repo")
    is_repo_change = (
        target_repo is not None
        and _normalize_repo_for_comparison(target_repo)
        != _normalize_repo_for_comparison(existing_repo)
    )
    if existing_version and existing_version == version and not is_repo_change:
        _fail_dev_preflight(
            f"Skill already synced at version {existing_version!r}. "
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
# Canonical named-skill schema validation
# ---------------------------------------------------------------------------


def _resolve_named_skill_schema(registry_path: str) -> dict[str, Any]:
    """Load namedSkill.schema.json from registry_path or bundled data."""
    candidates = [
        Path(registry_path) / "registry" / "schema" / "namedSkill.schema.json",
        Path(__file__).resolve().parents[2]
        / "data"
        / "registry"
        / "schema"
        / "namedSkill.schema.json",
    ]
    for candidate in candidates:
        if candidate.is_file():
            try:
                data = json.loads(candidate.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                _fail_dev_preflight(
                    f"Cannot read namedSkill.schema.json at {candidate}: {exc}. "
                    "Nothing was written.",
                    fix="Ensure registry/schema/namedSkill.schema.json is valid JSON.",
                )
            if isinstance(data, dict) and isinstance(data.get("properties"), dict):
                return data
    _fail_dev_preflight(
        "Cannot locate valid namedSkill.schema.json in registry or bundled data. "
        "Nothing was written.",
        fix="Ensure registry/schema/namedSkill.schema.json is present.",
    )
    raise AssertionError("unreachable")


def _schema_format_checker():
    import jsonschema

    checker = jsonschema.FormatChecker()
    if "date-time" not in checker.checkers:
        @checker.checks("date-time", raises=(TypeError, ValueError))
        def _check_date_time(value: object) -> bool:
            if not isinstance(value, str):
                return True
            if not _DATE_TIME_RE.fullmatch(value):
                return False
            parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.tzinfo is not None

    if "uri" not in checker.checkers:
        @checker.checks("uri", raises=(TypeError, ValueError))
        def _check_uri(value: object) -> bool:
            if not isinstance(value, str):
                return True
            if not value or any(c.isspace() for c in value):
                return False
            parsed = urllib.parse.urlsplit(value)
            return bool(parsed.scheme and parsed.netloc)

    return checker


def _validate_proposed_named_record(registry_path: str, proposed_text: str) -> None:
    """Validate proposed frontmatter, upstream block, and appended timeline event."""
    try:
        import jsonschema
    except ImportError as exc:
        _fail_dev_preflight(
            f"jsonschema is required to validate proposed named skill record: {exc}. "
            "Nothing was written.",
            fix="Install jsonschema in the Python environment.",
        )

    schema = _resolve_named_skill_schema(registry_path)
    _fence, new_fm_text, _body = split_frontmatter(proposed_text)
    new_meta = load_yaml_simple(new_fm_text)
    if not isinstance(new_meta, dict):
        _fail_dev_preflight(
            "Proposed frontmatter is not a YAML mapping. Nothing was written.",
            fix="Check the named skill frontmatter syntax.",
        )

    missing = [req for req in schema.get("required", []) if req not in new_meta]
    if missing:
        _fail_dev_preflight(
            f"Proposed named skill record is missing required schema field(s): "
            f"{', '.join(missing)}. Nothing was written.",
            fix="Ensure the named skill record satisfies namedSkill.schema.json required fields.",
        )

    checker = _schema_format_checker()
    schema_meta = schema.get("$schema", "http://json-schema.org/draft-07/schema#")
    defs = schema.get("definitions", {})
    props = schema.get("properties", {})

    def _validate_subschema(label: str, instance: Any, subschema: dict[str, Any]) -> None:
        wrapped = {"$schema": schema_meta, "definitions": defs, **subschema}
        validator = jsonschema.Draft7Validator(wrapped, format_checker=checker)
        errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
        if errors:
            err = errors[0]
            loc = ".".join(str(p) for p in err.path)
            loc_str = f" at {loc}" if loc else ""
            _fail_dev_preflight(
                f"Proposed {label}{loc_str} violates namedSkill.schema.json: "
                f"{err.message}. Nothing was written.",
                fix="Provide schema-valid upstream metadata and contributor username.",
            )

    if "upstream" in props:
        _validate_subschema("upstream", new_meta.get("upstream"), props["upstream"])

    if "contributor" in props and "contributor" in new_meta:
        _validate_subschema("contributor", new_meta.get("contributor"), props["contributor"])

    timeline = new_meta.get("timeline")
    if not isinstance(timeline, list) or not timeline:
        _fail_dev_preflight(
            "Proposed timeline must be a non-empty list. Nothing was written.",
            fix="Check timeline serialization in the named skill file.",
        )
    timeline_event_schema = defs.get("timelineEvent")
    if isinstance(timeline_event_schema, dict):
        _validate_subschema("timeline[-1]", timeline[-1], timeline_event_schema)


# ---------------------------------------------------------------------------
# Core command
# ---------------------------------------------------------------------------


def sync_upstream_command(args) -> None:
    """Implement ``gaia dev sync-upstream``."""
    registry_path = args.registry
    skill_id = args.skill_id.lstrip("/")
    version: str = args.tag
    source_url: str = args.source_url
    target_repo: str | None = getattr(args, "repo", None)
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
        lambda: preflightNamedSkillMutable(registry_path, skill_id),
        lambda: _pf_repo_format(target_repo),
        lambda: _pf_version_format(version),
        lambda: _pf_source_url_format(source_url, version),
        lambda: _pf_source_url_matches_skill(source_url, meta, skill_id, target_repo),
        lambda: _pf_not_already_synced(version, meta, target_repo),
        lambda: _pf_min_two_stars(skill_id, meta),
        lambda: _pf_bootstrap_no_existing_block(skill_id, meta, is_bootstrap),
    ])

    # --- Compute new upstream block ---
    url_repo = _parse_owner_repo_from_url(source_url)
    existing_upstream = meta.get("upstream") or {}
    existing_repo = existing_upstream.get("repo")
    old_version: str | None = existing_upstream.get("version")
    old_source_url: str | None = existing_upstream.get("sourceUrl")
    repo = target_repo if target_repo is not None else (existing_repo or url_repo or "")
    is_repoint = (
        target_repo is not None
        and _normalize_repo_for_comparison(target_repo)
        != _normalize_repo_for_comparison(existing_repo)
    )

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
    if is_repoint:
        prev_val: str | None = (
            f"{existing_repo}@{old_version}"
            if (existing_repo and old_version)
            else (existing_repo or old_version)
        )
        new_val = f"{repo}@{version}"
        details = (
            f"repointed from {existing_repo or '(none)'}@{old_version or '(none)'} "
            f"({old_source_url or 'no sourceUrl'}) to {repo}@{version}; "
            f"synced from {source_url}"
        )
    else:
        prev_val = old_version
        new_val = version
        details = (
            "first-run baseline"
            if is_bootstrap
            else f"synced from {source_url}"
        )
    timeline_event: dict[str, Any] = {
        "timestamp": synced_at,
        "action": "upstream_synced",
        "contributor": contributor,
        "previousValue": prev_val,
        "newValue": new_val,
        "details": details,
    }

    # --- Compose and schema-validate complete replacement BEFORE any write ---
    new_text = upsert_top_level_block(raw_text, "upstream", new_upstream)
    new_text = append_timeline_event(new_text, timeline_event)
    _run_dev_preflights([
        lambda: _validate_proposed_named_record(registry_path, new_text),
    ])

    # --- Dry-run: print intended diff, no write ---
    if dry_run:
        import yaml  # pyyaml
        print("=== DRY RUN — no files written ===")
        print(f"\nupstream block would be written to {named_file}:")
        print(yaml.dump({"upstream": new_upstream}, sort_keys=False, allow_unicode=True))
        print("timeline event that would be appended:")
        print(yaml.dump(timeline_event, sort_keys=False, allow_unicode=True))
        return

    # --- Atomic same-directory temp + fsync + os.replace preserving mode ---
    mode_bits = stat.S_IMODE(named_file.stat().st_mode)
    _atomic_write_bytes(named_file, new_text.encode("utf-8"), mode_bits)

    # --- Success message ---
    old_str = old_version or "(none)"
    suffix = " (bootstrap)" if is_bootstrap else ""
    print(f"Synced {skill_id}: {old_str} → {version}{suffix}")
