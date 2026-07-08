"""
gaia dev freeze <skill-id> --reason <text>

Sets ``installable: false`` in a named skill's frontmatter AND appends a
``timeline.action: upstream_deprecated`` event.  Atomic — both writes land
together or neither does.

CLI Pre-Flight checks (per CLAUDE.md CLI Pre-Flight Rule):
  1. Skill must exist in registry/named/**/*.md.
  2. --reason must be non-empty and ≤500 chars.
  3. Refuses if installable: false is already set (no-op guard).
  4. Warns (does not refuse) if the skill is 3★+:
     META.md §2.4 Star Bar may fail for frozen 3★+ skills.
"""

from __future__ import annotations

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
    append_timeline_event,
)

# ---------------------------------------------------------------------------
# Star level helpers (mirrors sync_upstream.py — keep in sync)
# ---------------------------------------------------------------------------

_STAR_LEVELS = ["1★", "2★", "3★", "4★", "5★", "6★"]
_THREE_STAR_PLUS = {"3★", "4★", "5★", "6★"}


def _utc_now_iso() -> str:
    return (
        datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


# ---------------------------------------------------------------------------
# Frontmatter helper: set a scalar top-level key
# ---------------------------------------------------------------------------


def _set_scalar_in_frontmatter(text: str, key: str, value: Any) -> str:
    """Set (or replace) a scalar *key* at the top level of the frontmatter.

    Uses pyyaml round-trip.  Returns updated full file text.
    """
    import yaml
    import re

    _FM_RE = re.compile(r"^---\r?\n(.*?)\r?\n---(?:\r?\n|$)", re.DOTALL)
    m = _FM_RE.match(text)
    if not m:
        return text

    fm_text = m.group(1)
    body_text = text[m.end():]

    fm_dict: dict = yaml.safe_load(fm_text) or {}
    fm_dict[key] = value

    new_fm_text = yaml.dump(fm_dict, sort_keys=False, allow_unicode=True).rstrip("\n")
    return f"---\n{new_fm_text}\n---\n{body_text}"


# ---------------------------------------------------------------------------
# Pre-flight helpers
# ---------------------------------------------------------------------------


def _pf_reason_non_empty(reason: str) -> None:
    if not reason or not reason.strip():
        _fail_dev_preflight(
            "--reason must be non-empty.",
            fix="Provide a human-readable explanation, e.g. 'removed from mattpocock/skills@v1.2.0'.",
        )
    if len(reason) > 500:
        _fail_dev_preflight(
            f"--reason is {len(reason)} characters; maximum is 500.",
            fix="Shorten the reason text.",
        )


def _pf_not_already_frozen(skill_id: str, meta: dict) -> None:
    if meta.get("installable") is False:
        _fail_dev_preflight(
            f"Skill '{skill_id}' is already frozen (installable: false). No change.",
            fix="Nothing was written. The skill is already frozen.",
        )


# ---------------------------------------------------------------------------
# Core command
# ---------------------------------------------------------------------------


def freeze_command(args) -> None:
    """Implement ``gaia dev freeze``."""
    registry_path = args.registry
    skill_id = args.skill_id.lstrip("/")
    reason: str = args.reason
    dry_run: bool = getattr(args, "dry_run", False)
    user: str | None = getattr(args, "user", None)

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
        lambda: _pf_reason_non_empty(reason),
        lambda: _pf_not_already_frozen(skill_id, meta),
    ])

    # --- Warn if 3★+ (not a refusal) ---
    level = meta.get("level", "")
    if level in _THREE_STAR_PLUS:
        print(
            f"Warning: freezing a {level} skill may fail Star Bar (META.md §2.4). "
            "Proceeding — flag this case in the tracking issue.",
            file=sys.stderr,
        )

    # --- Build timeline event ---
    contributor = user or _get_contributor()
    ts = _utc_now_iso()
    timeline_event: dict[str, Any] = {
        "timestamp": ts,
        "action": "upstream_deprecated",
        "contributor": contributor,
        "previousValue": None,
        "newValue": None,
        "details": reason,
    }

    # --- Dry-run: print intended changes, no write ---
    if dry_run:
        import yaml  # pyyaml
        print("=== DRY RUN — no files written ===")
        print(f"\nWould set installable: false on {named_file}")
        print("timeline event that would be appended:")
        print(yaml.dump(timeline_event, sort_keys=False, allow_unicode=True))
        return

    # --- Atomic write: compose full content in memory first ---
    new_text = _set_scalar_in_frontmatter(raw_text, "installable", False)
    new_text = append_timeline_event(new_text, timeline_event)

    # Single filesystem write.
    named_file.write_text(new_text, encoding="utf-8")

    print(f"Frozen {skill_id}: {reason}")
