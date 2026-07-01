import sys
import os
import json
import datetime
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from gaia_cli.registry import (
    registry_graph_path,
    named_skills_index_path,
    registry_nodes_dir,
    named_skills_dir,
)
from gaia_cli.scanner import load_config


_GENERATED_PREFIXES = (
    "docs/",
    "skill-trees/",
    "registry/gaia.gexf",
    "registry/gaia.svg",
    "registry/named-skills.json",
    "registry/combinations.md",
    "registry/registry.md",
    "registry/skill-sources.md",
)
_GENERATED_SUFFIXES = (
    ".gexf",
    ".svg",
    ".html",
)
_GENERATED_EXACT = {
    "uv.lock",
    "docs/css/tokens.css",
    "docs/tree.md",
}
_VERSION_FILES = {
    "pyproject.toml",
    "packages/cli-npm/package.json",
    "packages/mcp/package.json",
    "registry/gaia.json",
    "docs/graph/gaia.json",
}


@dataclass(frozen=True)
class DevPreflightError(Exception):
    """A mutating `gaia dev` command would violate an invariant before writing."""

    message: str
    fix: str | None = None


def _format_dev_preflight_error(error: DevPreflightError) -> str:
    lines = [f"Error: {error.message}"]
    if error.fix:
        lines.append(f"Fix: {error.fix}")
    return "\n".join(lines)


def _fail_dev_preflight(message: str, *, fix: str | None = None) -> None:
    raise DevPreflightError(message=message, fix=fix)


def _run_dev_preflights(checks: Iterable[Callable[[], None]]) -> None:
    """Run invariant checks and abort before any write if one fails."""
    try:
        for check in checks:
            check()
    except DevPreflightError as error:
        print(_format_dev_preflight_error(error), file=sys.stderr)
        sys.exit(1)


def _preflight_named_status_identity(skill_id: str, meta: dict, args) -> None:
    new_status = getattr(args, "status", None)
    if new_status != "named":
        return
    if (
        meta.get("title")
        or meta.get("catalogRef")
        or getattr(args, "title", None)
        or getattr(args, "catalog_ref", None)
    ):
        return
    _fail_dev_preflight(
        f"status='named' requires 'title' or 'catalogRef' on {skill_id}.",
        fix=(
            f"Re-run `gaia dev update-named {skill_id} --status named "
            f"--title \"<lore title>\"` (or `--catalog-ref <slug>`) to satisfy "
            f"the schema constraint."
        ),
    )


def _preflight_starbar_blob_link(skill_id: str, skill_data: dict, level: str) -> None:
    three_star_plus = {"3★", "4★", "5★", "6★"}
    if level not in three_star_plus:
        return
    github_url = (skill_data.get("links") or {}).get("github", "")
    if github_url and "/blob/" in github_url:
        return
    _fail_dev_preflight(
        f"Cannot calibrate {skill_id} to {level}: `links.github` is missing or not a `blob/` URL.",
        fix=(
            "The Star Bar (META.md §2.4) requires a verified GitHub blob URL for 3★+ skills. "
            f"Current value: {github_url!r}. Re-run `gaia dev update-named {skill_id} "
            "--github-link https://github.com/<owner>/<repo>/blob/<branch>/<path-to-skill>`."
        ),
    )


def _preflight_evidence_static(args, valid_types: set[str] | list[str] | tuple[str, ...]) -> None:
    evidence_type = getattr(args, "evidence_type", None)
    if evidence_type is not None and evidence_type not in valid_types:
        valid_list = ", ".join(valid_types)
        _fail_dev_preflight(
            f"unknown evidence type '{evidence_type}'.",
            fix=f"Use one of: {valid_list}",
        )

    percentile = getattr(args, "percentile", None)
    if evidence_type == "benchmark-result":
        if percentile is None:
            _fail_dev_preflight(
                "`--type benchmark-result` requires `--percentile <0-100>`.",
                fix=(
                    "Pass `--percentile <int>` (0-100 inclusive). If the percentile is unknown, "
                    "use `--type peer-review` with `--reviewers` instead for a gradeable entry."
                ),
            )
        if not (0 <= int(percentile) <= 100):
            _fail_dev_preflight(f"`--percentile` must be in range 0-100; got {percentile!r}.")

    for attr, flag in (("date", "--date"), ("source_started_at", "--source-started-at")):
        value = getattr(args, attr, None)
        if value is None:
            continue
        try:
            datetime.date.fromisoformat(value)
        except ValueError:
            _fail_dev_preflight(f"{flag} must be ISO YYYY-MM-DD; got '{value}'.")

    index = getattr(args, "index", None)
    patch_fields = (
        "trust",
        "evidence_type",
        "notes",
        "evaluator",
        "date",
        "stars",
        "views",
        "citations",
        "reviewers",
        "commits",
        "contributors",
        "skill_count_in_repo",
        "percentile",
        "source_started_at",
    )
    if index is not None and not any(getattr(args, field, None) is not None for field in patch_fields):
        _fail_dev_preflight(
            "--index requires at least one update field.",
            fix="Pass one of --trust, --type, --notes, --date, --source-started-at, or a numeric payload flag.",
        )


def _preflight_evidence_index_bounds(skill_id: str, ev_list: list, index: int | None) -> None:
    if index is None:
        return
    if index < 0 or index >= len(ev_list):
        _fail_dev_preflight(
            f"Evidence index {index} out of range for skill '{skill_id}' ({len(ev_list)} entries).",
            fix="Use a valid zero-based --index value or omit --index to append new evidence.",
        )


def _run_docs_build(registry_path) -> None:
    import gaia_cli.commands.dev as dev
    patched = getattr(dev, "_run_docs_build", None)
    if patched and patched is not _run_docs_build:
        patched(registry_path)
        return

    cmd = [sys.executable, "-m", "gaia_cli"]
    if registry_path:
        cmd += ["--registry", str(registry_path)]
    cmd += ["docs", "build"]
    subprocess.run(cmd, check=True)



def _get_contributor():
    config = load_config() or {}
    return config.get("gaiaUser") or config.get("username") or "unknown"


def _is_verifier(username, registry_path=".") -> bool:
    """Check if the user holds at least one 4★ skill implementation."""
    index_path = named_skills_index_path(registry_path)
    if not os.path.exists(index_path):
        return False
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            index = json.load(f)
        for entries in index.get("buckets", {}).values():
            for e in entries:
                if e.get("contributor") == username:
                    level = e.get("level", "2★")
                    if level and level[0].isdigit() and int(level[0]) >= 4:
                        return True
    except Exception:
        pass
    return False


def _confirm_destructive(message: str, args) -> None:
    """Prompt for confirmation before a destructive operation.

    Skipped when ``args.yes`` is True.  In non-interactive contexts (CI, piped
    stdin) ``confirm()`` returns the default value (False), so automation MUST
    pass ``--yes`` explicitly to avoid an implicit abort.
    """
    if getattr(args, "yes", False):
        return
    from gaia_cli.interactive import confirm
    if not confirm(message, default=False):
        print("Aborted.")
        sys.exit(0)


def _parse_md(path):
    import yaml
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return {}, content
    _, frontmatter, body = content.split("---", 2)
    return (yaml.safe_load(frontmatter) or {}), body


def _write_md(path, meta, body) -> None:
    import yaml
    path.write_text(
        "---\n" + yaml.dump(meta, sort_keys=False, allow_unicode=True) + "---" + body,
        encoding="utf-8",
    )


def _find_named_file(named_dir, skill_id):
    for p in named_dir.glob("**/*.md"):
        meta, _ = _parse_md(p)
        if meta.get("id") == skill_id:
            return p
    return None


def _replace_section(body: str, section_heading: str, new_content: str) -> str:
    """Replace (or append) a top-level markdown section in the body text.

    Matches ``## {section_heading}`` through the next ``##``-level heading
    or end-of-string, then substitutes new_content.  If the section is not
    found it is appended.
    """
    import re

    pattern = rf"(##\s+{re.escape(section_heading)}\s*\n)(.*?)(?=\n##\s|\Z)"
    replacement = rf"\g<1>{new_content}\n"
    result, n = re.subn(pattern, replacement, body, flags=re.DOTALL)
    if n == 0:
        result = body.rstrip("\n") + f"\n\n## {section_heading}\n\n{new_content}\n"
    return result


def _update_named_skill_ref(md_path: Path, old_ref: str, new_ref: str):
    """Update genericSkillRef in a named skill markdown file."""
    meta, body = _parse_md(md_path)
    if meta.get("genericSkillRef") == old_ref:
        meta["genericSkillRef"] = new_ref
        _write_md(md_path, meta, body)
        return True
    return False


def _is_generated(path):
    if path in _GENERATED_EXACT:
        return True
    for prefix in _GENERATED_PREFIXES:
        if path.startswith(prefix):
            return True
    for suffix in _GENERATED_SUFFIXES:
        if path.endswith(suffix):
            return True
    return False


def _parse_named_frontmatter(content):
    """Extract key/value pairs from YAML frontmatter in a named skill file."""
    if not content.startswith("---"):
        return {}
    lines = content.split("\n")
    end = None
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end = i
            break
    if end is None:
        return {}
    meta = {}
    for line in lines[1:end]:
        if ":" in line:
            key, _, val = line.partition(":")
            meta[key.strip()] = val.strip().strip("'\"")
    return meta
