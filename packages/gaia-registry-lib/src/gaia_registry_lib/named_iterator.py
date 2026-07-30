"""
gaia_registry_lib.named_iterator — walk registry/named/**/*.md.

Provides a single iterator that yields (path, parsed_frontmatter_dict) for
every named skill markdown file in the registry.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from gaia_registry_lib.frontmatter import load_yaml_simple, split_frontmatter


def _find_repo_named_dir() -> Path:
    """Return the nearest checkout's ``registry/named`` directory if present."""
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "registry" / "named"
        if candidate.exists():
            return candidate
    # Source checkout layout: packages/gaia-registry-lib/src/gaia_registry_lib/*.py
    return Path(__file__).resolve().parents[4] / "registry" / "named"


_DEFAULT_NAMED_DIR = _find_repo_named_dir()


def iter_named_skills(
    root: Path | None = None,
) -> Iterator[tuple[Path, dict]]:
    """Yield ``(path, frontmatter_dict)`` for every ``registry/named/**/*.md``.

    ``root`` overrides the default ``registry/named/`` directory. Files whose
    frontmatter fence is absent or malformed are skipped.
    """
    named_dir = root if root is not None else _DEFAULT_NAMED_DIR

    for md_path in sorted(named_dir.rglob("*.md")):
        text = md_path.read_text(encoding="utf-8")
        _, fm_raw, _ = split_frontmatter(text)
        if not fm_raw:
            continue
        fm = load_yaml_simple(fm_raw)
        yield (md_path, fm)
