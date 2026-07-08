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

from urllib.parse import urlparse

from gaia_cli.push import (
    SKILL_ID_RE,
    build_similarity,
    load_canonical_skill_map,
    skill_name_from_id,
)
from gaia_cli.registry import registry_graph_path, skill_batches_dir


def _is_github_tree_url(url):
    """Return True when *url* is a GitHub tree/ directory URL.

    Uses urlparse so the netloc is checked exactly rather than via substring
    matching, which CodeQL flags as incomplete URL sanitization (CWE-625).
    A blob/ URL or a non-GitHub URL both return False.
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    netloc = parsed.netloc.lower()
    # Accept github.com and the github.com. prefix-spoof guard:
    # require the netloc to be exactly 'github.com' (with optional www.).
    if netloc not in ("github.com", "www.github.com"):
        return False
    return "/tree/" in parsed.path

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


def _validate_skill(entry, index, canonicalIds):
    """Return a list of validation error strings for a single skill entry.
    An empty list means the entry is valid.
    """
    errors = []
    prefix = f"skills[{index}]"

    skillId = entry.get("id", "")
    if not skillId:
        errors.append(f"{prefix}: 'id' is required")
    elif not SKILL_ID_RE.match(skillId):
        errors.append(
            f"{prefix}.id '{skillId}': must match ^[a-z][a-z0-9]*(-[a-z0-9]+)*$"
        )

    if not entry.get("name", "").strip():
        errors.append(f"{prefix}: 'name' is required")

    skType = entry.get("type", "")
    if skType not in _VALID_TYPES:
        errors.append(
            f"{prefix}.type '{skType}': must be 'basic' or 'fusion' (Yggdrasil II)"
        )

    description = entry.get("description", "")
    if not isinstance(description, str) or len(description.strip()) < 10:
        errors.append(f"{prefix}.description: must be a string of at least 10 characters")

    # prereqs: must be a list (not a string scalar, not null) when present
    prereqsRaw = entry.get("prerequisites")
    if prereqsRaw is None:
        prereqs = []
    elif not isinstance(prereqsRaw, list):
        errors.append(
            f"{prefix}.prerequisites: must be a list, got {type(prereqsRaw).__name__} "
            f"— use [skill-a, skill-b] not a bare string"
        )
        prereqs = []  # skip further checks on malformed value
    else:
        prereqs = prereqsRaw

    if skType == "fusion" and not prereqs:
        errors.append(f"{prefix}: type=fusion requires at least one prerequisite")
    if skType == "basic" and prereqs:
        errors.append(f"{prefix}: type=basic must have an empty prerequisites list")
    for prereq in prereqs:
        if prereq not in canonicalIds:
            errors.append(
                f"{prefix}.prerequisites: '{prereq}' does not exist in registry/gaia.json"
            )

    attribution = entry.get("attribution") or {}
    if attribution:
        attrType = attribution.get("type", "")
        if attrType and attrType not in _VALID_ATTR_TYPES:
            errors.append(
                f"{prefix}.attribution.type '{attrType}': must be one of "
                f"{sorted(_VALID_ATTR_TYPES)}"
            )

    evidence = entry.get("evidence") or []
    if not evidence:
        errors.append(
            f"{prefix}: at least one evidence entry is required (Grade B or above preferred)"
        )
    for ei, ev in enumerate(evidence):
        evPrefix = f"{prefix}.evidence[{ei}]"
        grade = str(ev.get("grade", "")).upper()
        if grade not in _VALID_EVIDENCE_GRADES:
            errors.append(f"{evPrefix}.grade '{grade}': must be A, B, or C")
        evType = ev.get("type", "")
        if evType and evType not in _VALID_EVIDENCE_TYPES:
            errors.append(
                f"{evPrefix}.type '{evType}': unrecognised evidence type "
                f"(valid: {sorted(_VALID_EVIDENCE_TYPES)})"
            )
        url = ev.get("url", "")
        if not url:
            errors.append(f"{evPrefix}: 'url' is required")
        elif _is_github_tree_url(url):
            errors.append(
                f"{evPrefix}.url: use blob/ URLs, not tree/ (got: {url})"
            )

    named = entry.get("named") or {}
    if named:
        if not named.get("contributor", "").strip():
            errors.append(f"{prefix}.named.contributor: required when named block present")
        # level is required when the named block is present
        level = named.get("level", "")
        if not level:
            errors.append(f"{prefix}.named.level: required when named block present (e.g. '2★')")
        elif not _STAR_RE.match(str(level).strip()):
            errors.append(
                f"{prefix}.named.level '{level}': must be a star rating like '2★' (2–6)"
            )
        # links_github is required when the named block is present
        linksGithub = named.get("links_github", "")
        if not linksGithub:
            errors.append(
                f"{prefix}.named.links_github: required when named block present "
                f"(blob/ URL to SKILL.md or repo root)"
            )
        elif _is_github_tree_url(linksGithub):
            errors.append(
                f"{prefix}.named.links_github: use blob/ URLs, not tree/ (got: {linksGithub})"
            )

    return errors


# ---------------------------------------------------------------------------
# Batch builder
# ---------------------------------------------------------------------------

def _skillEntryToProposed(entry, sourceRepo):
    """Convert a validated YAML skill entry to the proposedSkills batch format."""
    proposed = dict(entry)
    proposed.setdefault("sourceRepo", sourceRepo)
    proposed.setdefault("lifecycle", "pending")
    if not proposed.get("name"):
        proposed["name"] = skill_name_from_id(entry.get("id", ""))
    return proposed


def build_from_file_batch(skillsYaml, config, registryRoot, sourceRepo, now=None):
    """Build a skill batch dict from a parsed YAML 'skills:' list.

    Returns (batch_dict, errors).  When errors is non-empty, batch_dict is None
    and nothing has been written to disk.
    """
    graphPath = registry_graph_path(registryRoot)
    canonicalMap = load_canonical_skill_map(graphPath)
    if not canonicalMap:
        print(
            "Warning: registry/gaia.json not found or empty — "
            "prerequisite validation will be skipped.",
            file=sys.stderr,
        )
    canonicalIds = set(canonicalMap.keys())

    timestamp = now or datetime.now(timezone.utc)
    generatedAt = timestamp.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    batchId = (
        f"{timestamp.strftime('%Y%m%d%H%M%S')}-"
        f"{config.get('gaiaUser', 'unknown')}-from-file"
    )

    # ── validate all entries up front — nothing is written until this passes ──
    allErrors = []
    for i, entry in enumerate(skillsYaml):
        allErrors.extend(_validate_skill(entry, i, canonicalIds))

    if allErrors:
        print("Validation errors in --from-file YAML:", file=sys.stderr)
        for err in allErrors:
            print(f"  • {err}", file=sys.stderr)
        return None, allErrors

    proposedSkills = [
        _skillEntryToProposed(entry, sourceRepo) for entry in skillsYaml
    ]
    proposedIds = [s["id"] for s in proposedSkills]

    return {
        "batchId": batchId,
        "userId": config.get("gaiaUser", "unknown"),
        "sourceRepo": sourceRepo,
        "generatedAt": generatedAt,
        "fromFile": True,  # signals prWriter to use rich rendering
        "knownSkills": [],
        "proposedSkills": proposedSkills,
        "similarity": build_similarity(proposedIds, canonicalMap),
    }, []


# ---------------------------------------------------------------------------
# Load helpers
# ---------------------------------------------------------------------------

def _load_yaml_file(path):
    """Load and parse a YAML file; return (data, error_message)."""
    # Import yaml lazily so the module can be imported without PyYAML installed.
    # The ImportError only surfaces when --from-file is actually used.
    try:
        import yaml as _yaml
    except ImportError:  # pragma: no cover
        return None, (
            "PyYAML is required for `gaia push --from-file` but is not installed.\n"
            "Fix: pip install pyyaml"
        )
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

    registryRoot = "."
    config = load_config(registryRoot)

    # ── load and parse YAML ────────────────────────────────────────────────
    filePath = args.fromFile
    yamlData, loadErr = _load_yaml_file(filePath)
    if loadErr:
        print(f"ERROR: {loadErr}", file=sys.stderr)
        return 1

    skillsYaml = yamlData["skills"]
    print(f"Loaded {len(skillsYaml)} skill(s) from '{filePath}'.")

    # ── resolve source repo ───────────────────────────────────────────────
    try:
        sourceRepo = detect_source_repo(config)
    except NonPublicRepoError:
        sourceRepo = f"manual/{config.get('gaiaUser', 'unknown')}"

    # ── build batch (validates first — nothing written on error) ─────────
    batch, errors = build_from_file_batch(
        skillsYaml, config, registryRoot, sourceRepo
    )
    if errors:
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
    batchPath = write_skill_batch(batch, registryRoot)
    print(f"Batch written → {batchPath}")

    # ── open issue (unless --no-issue) ────────────────────────────────────
    if getattr(args, "no_issue", False):
        print("Issue creation skipped (--no-issue).")
        print(f"To open manually:  gh issue create --title '[intake] batch' --body-file <(cat {batchPath})")
        return 0

    issueUrl = open_intake_issue(
        config.get("gaiaUser", "unknown"),
        batch,
        batch_path=batchPath,
        repo_root=registryRoot,
    )
    if issueUrl:
        print(f"Intake issue: {issueUrl}")
    return 0
