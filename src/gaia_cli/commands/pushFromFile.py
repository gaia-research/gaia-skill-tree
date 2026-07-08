"""
gaia push --from-file <path>

Loads a multi-skill YAML file (the intake schema defined in
.github/ISSUE_TEMPLATE/new_skill_intake.yml) and submits it as a single
skill-batch intake issue — no repo scan required.

Schema summary (top-level):

    skills:
      - id: <kebab-case>
        name: <display name>
        type: basic | fusion         # Yggdrasil II axis only
        prerequisites: []            # required for fusion; empty list for basic
        description: >-
          <agent-agnostic definition>
        attribution:
          upstream_author: <github-handle>   # optional
          skill_file_url: <blob-url>          # optional
          type: self-made | aggregator | attributed | abstract
        evidence:
          - grade: A | B | C
            type: repo | arxiv | github-stars-own | ...
            url: https://...
            notes: "..."              # optional
        named:                        # optional block
          contributor: <github-handle>
          level: "2★"
          links_github: https://...

All fields not recognised by the schema are silently passed through into the
batch JSON as extra metadata so reviewers can see them.
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Dependency: PyYAML is a gaia_cli install-time dependency. If it is somehow
# missing, give an explicit error rather than an ImportError traceback.
# ---------------------------------------------------------------------------
try:
    import yaml as _yaml
except ImportError:  # pragma: no cover
    print(
        "ERROR: PyYAML is required for `gaia push --from-file` but is not installed.\n"
        "Fix: pip install pyyaml",
        file=sys.stderr,
    )
    sys.exit(1)

from gaia_cli.push import (
    SKILL_ID_RE,
    build_similarity,
    load_canonical_skill_map,
    skill_name_from_id,
)
from gaia_cli.registry import registry_graph_path, skill_batches_dir

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

_VALID_TYPES = {"basic", "fusion"}
_VALID_ATTR_TYPES = {"self-made", "aggregator", "attributed", "abstract"}
_VALID_EVIDENCE_GRADES = {"A", "B", "C"}
_VALID_EVIDENCE_TYPES = {
    "repo",
    "arxiv",
    "github-stars-own",
    "social-signal",
    "peer-review",
    "benchmark-result",
    "course-certification",
    "enterprise-adoption",
    "ecosystem-integration",
    "registry-curation",
}
_STAR_RE = re.compile(r"^[2-6][★\*]$")


def _validate_skill(entry, index, canonical_ids):
    """Return a list of validation error strings for a single skill entry.
    An empty list means the entry is valid.
    """
    errors = []
    prefix = f"skills[{index}]"

    skill_id = entry.get("id", "")
    if not skill_id:
        errors.append(f"{prefix}: 'id' is required")
    elif not SKILL_ID_RE.match(skill_id):
        errors.append(
            f"{prefix}.id '{skill_id}': must match ^[a-z][a-z0-9]*(-[a-z0-9]+)*$"
        )

    if not entry.get("name", "").strip():
        errors.append(f"{prefix}: 'name' is required")

    sk_type = entry.get("type", "")
    if sk_type not in _VALID_TYPES:
        errors.append(
            f"{prefix}.type '{sk_type}': must be 'basic' or 'fusion' (Yggdrasil II)"
        )

    description = entry.get("description", "")
    if not isinstance(description, str) or len(description.strip()) < 10:
        errors.append(f"{prefix}.description: must be a string of at least 10 characters")

    prereqs = entry.get("prerequisites", [])
    if sk_type == "fusion" and not prereqs:
        errors.append(f"{prefix}: type=fusion requires at least one prerequisite")
    if sk_type == "basic" and prereqs:
        errors.append(f"{prefix}: type=basic must have an empty prerequisites list")
    for prereq in prereqs or []:
        if prereq not in canonical_ids:
            errors.append(
                f"{prefix}.prerequisites: '{prereq}' does not exist in registry/gaia.json"
            )

    attribution = entry.get("attribution") or {}
    if attribution:
        attr_type = attribution.get("type", "")
        if attr_type and attr_type not in _VALID_ATTR_TYPES:
            errors.append(
                f"{prefix}.attribution.type '{attr_type}': must be one of "
                f"{sorted(_VALID_ATTR_TYPES)}"
            )

    evidence = entry.get("evidence") or []
    if not evidence:
        errors.append(
            f"{prefix}: at least one evidence entry is required (Grade B or above preferred)"
        )
    for ei, ev in enumerate(evidence):
        ev_prefix = f"{prefix}.evidence[{ei}]"
        grade = str(ev.get("grade", "")).upper()
        if grade not in _VALID_EVIDENCE_GRADES:
            errors.append(f"{ev_prefix}.grade '{grade}': must be A, B, or C")
        ev_type = ev.get("type", "")
        if ev_type and ev_type not in _VALID_EVIDENCE_TYPES:
            errors.append(
                f"{ev_prefix}.type '{ev_type}': unrecognised evidence type "
                f"(valid: {sorted(_VALID_EVIDENCE_TYPES)})"
            )
        url = ev.get("url", "")
        if not url:
            errors.append(f"{ev_prefix}: 'url' is required")
        elif url.startswith("https://github.com") and "/tree/" in url:
            errors.append(
                f"{ev_prefix}.url: use blob/ URLs, not tree/ (got: {url})"
            )

    named = entry.get("named") or {}
    if named:
        if not named.get("contributor", "").strip():
            errors.append(f"{prefix}.named.contributor: required when named block present")
        level = named.get("level", "")
        if level and not _STAR_RE.match(str(level).strip()):
            errors.append(
                f"{prefix}.named.level '{level}': must be a star rating like '2★' (2–6)"
            )
        links_github = named.get("links_github", "")
        if links_github and "/tree/" in links_github:
            errors.append(
                f"{prefix}.named.links_github: use blob/ URLs, not tree/ (got: {links_github})"
            )

    return errors


# ---------------------------------------------------------------------------
# Batch builder
# ---------------------------------------------------------------------------

def _skill_entry_to_proposed(entry, source_repo):
    """Convert a validated YAML skill entry to the proposedSkills batch format."""
    # Preserve all fields; add sourceRepo and lifecycle.
    proposed = dict(entry)
    proposed.setdefault("sourceRepo", source_repo)
    proposed.setdefault("lifecycle", "pending")
    # Normalise: ensure name is set
    if not proposed.get("name"):
        proposed["name"] = skill_name_from_id(entry.get("id", ""))
    return proposed


def build_from_file_batch(skills_yaml, config, registry_root, source_repo, now=None):
    """Build a skill batch dict from a parsed YAML 'skills:' list."""
    graph_path = registry_graph_path(registry_root)
    canonical_map = load_canonical_skill_map(graph_path)
    canonical_ids = set(canonical_map.keys())

    timestamp = now or datetime.now(timezone.utc)
    generated_at = timestamp.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    batch_id = (
        f"{timestamp.strftime('%Y%m%d%H%M%S')}-"
        f"{config.get('gaiaUser', 'unknown')}-from-file"
    )

    # ── validate all entries up front ──────────────────────────────────────
    all_errors = []
    for i, entry in enumerate(skills_yaml):
        all_errors.extend(_validate_skill(entry, i, canonical_ids))

    if all_errors:
        print("Validation errors in --from-file YAML:", file=sys.stderr)
        for err in all_errors:
            print(f"  • {err}", file=sys.stderr)
        return None, all_errors

    proposed_skills = [
        _skill_entry_to_proposed(entry, source_repo) for entry in skills_yaml
    ]
    proposed_ids = [s["id"] for s in proposed_skills]

    return {
        "batchId": batch_id,
        "userId": config.get("gaiaUser", "unknown"),
        "sourceRepo": source_repo,
        "generatedAt": generated_at,
        "fromFile": True,  # signals prWriter to use rich rendering
        "knownSkills": [],
        "proposedSkills": proposed_skills,
        "similarity": build_similarity(proposed_ids, canonical_map),
    }, []


# ---------------------------------------------------------------------------
# Load helpers
# ---------------------------------------------------------------------------

def _load_yaml_file(path):
    """Load and parse a YAML file; return (data, error_message)."""
    try:
        with open(path, encoding="utf-8") as f:
            raw = f.read()
    except OSError as exc:
        return None, f"Cannot read file '{path}': {exc}"
    try:
        data = _yaml.safe_load(raw)
    except _yaml.YAMLError as exc:
        return None, f"YAML parse error in '{path}':\n  {exc}"
    if not isinstance(data, dict):
        return None, f"'{path}' must be a YAML mapping with a top-level 'skills:' key"
    if "skills" not in data:
        return None, f"'{path}' is missing the required top-level 'skills:' list"
    if not isinstance(data["skills"], list) or len(data["skills"]) == 0:
        return None, f"'{path}': 'skills:' must be a non-empty list"
    return data, None


# ---------------------------------------------------------------------------
# Command entry point
# ---------------------------------------------------------------------------

def push_from_file_command(args):
    """Entry point called by PushCommand.execute() when --from-file is set."""
    from gaia_cli.config import load_config
    from gaia_cli.push import detect_source_repo, NonPublicRepoError, write_skill_batch
    from gaia_cli.prWriter import build_intake_issue_body, open_intake_issue

    registry_root = "."
    config = load_config(registry_root)

    # ── load and parse YAML ────────────────────────────────────────────────
    file_path = args.fromFile
    yaml_data, load_err = _load_yaml_file(file_path)
    if load_err:
        print(f"ERROR: {load_err}", file=sys.stderr)
        return 1

    skills_yaml = yaml_data["skills"]
    print(f"Loaded {len(skills_yaml)} skill(s) from '{file_path}'.")

    # ── resolve source repo ───────────────────────────────────────────────
    try:
        source_repo = detect_source_repo(config)
    except NonPublicRepoError:
        source_repo = f"manual/{config.get('gaiaUser', 'unknown')}"

    # ── build batch ───────────────────────────────────────────────────────
    batch, errors = build_from_file_batch(
        skills_yaml, config, registry_root, source_repo
    )
    if errors:
        # errors already printed inside build_from_file_batch
        return 1

    n = len(batch["proposedSkills"])
    print(f"Batch: {n} skill(s) proposed, {len(batch['similarity'])} similarity links computed.")

    # ── dry run ───────────────────────────────────────────────────────────
    if getattr(args, "dry_run", False):
        print("\n── Dry run — batch JSON ──────────────────────────────────────")
        print(json.dumps(batch, indent=2, ensure_ascii=False))
        print("\n── Dry run — issue body ─────────────────────────────────────")
        print(build_intake_issue_body(batch))
        return 0

    # ── confirmation prompt ───────────────────────────────────────────────
    if not getattr(args, "yes", False):
        ids = ", ".join(s["id"] for s in batch["proposedSkills"])
        print(f"\nAbout to write batch and open an intake issue for:\n  {ids}")
        answer = input("Proceed? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            print("Aborted.")
            return 0

    # ── write batch file ──────────────────────────────────────────────────
    batch_path = write_skill_batch(batch, registry_root)
    print(f"Batch written → {batch_path}")

    # ── open issue (unless --no-issue) ────────────────────────────────────
    if getattr(args, "no_issue", False):
        print("Issue creation skipped (--no-issue).")
        print(f"To open manually:  gh issue create --title '[intake] batch' --body-file <(cat {batch_path})")
        return 0

    issue_url = open_intake_issue(
        config.get("gaiaUser", "unknown"),
        batch,
        batch_path=batch_path,
        repo_root=registry_root,
    )
    if issue_url:
        print(f"Intake issue: {issue_url}")
    return 0
