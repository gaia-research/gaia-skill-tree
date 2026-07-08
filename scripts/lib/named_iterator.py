"""
scripts.lib.named_iterator — walk registry/named/**/*.md.

Provides a single iterator that yields (path, parsed_frontmatter_dict) for
every named skill markdown file in the registry.

Public API
----------
iter_named_skills(root=None)
    Walk ``registry/named/**/*.md``, yield ``(Path, dict)`` pairs.
    Skips files with no frontmatter.  Defaults *root* to the repo's
    ``registry/named/`` directory, resolved from ``__file__``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from scripts.lib.frontmatter import load_yaml_simple, split_frontmatter

# ---------------------------------------------------------------------------
# Repo-root resolution (same pattern as heartbeat's REPO_ROOT)
# ---------------------------------------------------------------------------

_THIS_FILE = Path(__file__).resolve()
# scripts/lib/named_iterator.py → up two dirs → repo root
_REPO_ROOT = _THIS_FILE.parent.parent.parent
_DEFAULT_NAMED_DIR = _REPO_ROOT / "registry" / "named"


# ---------------------------------------------------------------------------
# Iterator
# ---------------------------------------------------------------------------


def iter_named_skills(
    root: Path | None = None,
) -> Iterator[tuple[Path, dict]]:
    """Yield ``(path, frontmatter_dict)`` for every ``registry/named/**/*.md``.

    Parameters
    ----------
    root:
        Override the ``registry/named/`` directory.  Defaults to the
        canonical location resolved from this file's position in the repo.

    Yields
    ------
    tuple[Path, dict]
        *path* is the absolute ``Path`` to the ``.md`` file.
        *dict* is the parsed YAML frontmatter (empty dict if no frontmatter).

    Skips files whose frontmatter fence is absent or malformed.
    """
    named_dir = root if root is not None else _DEFAULT_NAMED_DIR

    for md_path in sorted(named_dir.rglob("*.md")):
        text = md_path.read_text(encoding="utf-8")
        _, fm_raw, _ = split_frontmatter(text)
        if not fm_raw:
            continue
        fm = load_yaml_simple(fm_raw)
        yield (md_path, fm)
