import sys
import os
import json
import datetime
import subprocess
from pathlib import Path

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
