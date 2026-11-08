"""
gaia dev relink <skill-id> --new-url <url>

Mutates links.github in frontmatter and appends a timeline event:
action: "relinked", details: f"Relinked from {old_url} to {new_url}".

CLI Pre-Flight checks (per docs/agents/upstream-watcher.md:549):
  1. Skill must exist in registry/named/**/*.md.
  2. --new-url must be a non-empty valid GitHub blob URL.
"""

from __future__ import annotations

import datetime
import sys
from pathlib import Path
from typing import Any

from gaia_cli.commands.dev.helpers import (
    _fail_dev_preflight,
    _find_named_file,
    _get_contributor,
    _run_dev_preflights,
    preflightGithubLink,
)
from gaia_cli.frontmatter import (
    append_timeline_event,
    load_yaml_simple,
    split_frontmatter,
)
from gaia_cli.registry import named_skills_dir


def _utc_now_iso() -> str:
    return (
        datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _set_links_github_in_frontmatter(text: str, new_url: str) -> str:
    """Set (or update) links.github in frontmatter."""
    import re
    import yaml

    _FM_RE = re.compile(r"^---\r?\n(.*?)\r?\n---(?:\r?\n|$)", re.DOTALL)
    m = _FM_RE.match(text)
    if not m:
        return text

    fm_text = m.group(1)
    body_text = text[m.end():]

    fm_dict: dict = yaml.safe_load(fm_text) or {}
    if "links" not in fm_dict or not isinstance(fm_dict["links"], dict):
        fm_dict["links"] = {}
    fm_dict["links"]["github"] = new_url

    new_fm_text = yaml.dump(fm_dict, sort_keys=False, allow_unicode=True).rstrip("\n")
    return f"---\n{new_fm_text}\n---\n{body_text}"


def relink_command(args) -> int | None:
    registry_path = getattr(args, "registry", None)
    named_dir = Path(named_skills_dir(registry_path))
    skill_id = args.skill_id.lstrip("/")
    new_url = getattr(args, "new_url", None)
    dry_run = getattr(args, "dry_run", False)
    user = getattr(args, "user", None)

    named_file = _find_named_file(named_dir, skill_id)

    # --- Pre-flight validation ---
    def _pf_skill_exists() -> None:
        if not named_file or not named_file.exists():
            _fail_dev_preflight(
                f"Named skill '{skill_id}' not found in {named_dir}.",
                fix="Check the skill ID (e.g. 'mattpocock/old-skill'). Run `gaia dev list --named` to see valid IDs.",
            )

    def _pf_new_url() -> None:
        if not new_url or not isinstance(new_url, str) or not new_url.strip():
            _fail_dev_preflight(
                "--new-url must be non-empty.",
                fix="Provide a valid GitHub blob URL, e.g. https://github.com/owner/repo/blob/main/path/to/SKILL.md",
            )
        preflightGithubLink(new_url)

    _run_dev_preflights([
        _pf_skill_exists,
        _pf_new_url,
    ])

    raw_text = named_file.read_text(encoding="utf-8")
    _fence, fm_text, _body = split_frontmatter(raw_text)
    meta: dict = load_yaml_simple(fm_text) or {}

    old_url = (meta.get("links") or {}).get("github", "")

    contributor = user or _get_contributor()
    ts = _utc_now_iso()
    timeline_event: dict[str, Any] = {
        "timestamp": ts,
        "action": "relinked",
        "contributor": contributor,
        "previousValue": old_url or None,
        "newValue": new_url,
        "details": f"Relinked from {old_url} to {new_url}",
    }

    if dry_run:
        import yaml
        print("=== DRY RUN — no files written ===")
        print(f"\nWould update links.github on {named_file} to {new_url}")
        print("timeline event that would be appended:")
        print(yaml.dump(timeline_event, sort_keys=False, allow_unicode=True))
        return None

    # Atomic in-memory compose
    new_text = _set_links_github_in_frontmatter(raw_text, new_url)
    new_text = append_timeline_event(new_text, timeline_event)

    named_file.write_text(new_text, encoding="utf-8")

    print(f"Relinked {skill_id}: {old_url or '(none)'} → {new_url}")
    return 0
