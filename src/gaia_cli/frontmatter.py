"""
gaia_cli.frontmatter — regex-based YAML frontmatter parse and rewrite helpers.

# Duplicated from scripts/lib/frontmatter.py — see docs/agents/upstream-watcher.md §9.
# Keep in sync manually until a shared package extraction lands.
# Follow-up: https://github.com/gaia-research/gaia-skill-tree/issues/1028
#   "Extract scripts/lib into a shared installable package (upstream-watcher PR 5 follow-up)"

Public API
----------
split_frontmatter(text)
    Split raw file text into (fence, fm_content, body).

load_yaml_simple(text)
    Parse a YAML string into a dict (thin pyyaml wrapper).

upsert_top_level_block(text, block_key, block_value)
    Write or merge an entire top-level frontmatter mapping block.
    Used by sync-upstream to write/update the ``upstream:`` block atomically.

append_timeline_event(text, event)
    Append a timeline event dict to the ``timeline:`` list in frontmatter.
    Returns the updated full file text.
"""

from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# Frontmatter fence regex
# ---------------------------------------------------------------------------

_FM_RE = re.compile(r"^---\r?\n(.*?)\r?\n---(?:\r?\n|$)", re.DOTALL)


# ---------------------------------------------------------------------------
# Core parse helpers
# ---------------------------------------------------------------------------


def split_frontmatter(text: str) -> tuple[str, str, str]:
    """Split *text* into ``(pre_fence, fm_content, body)``.

    Returns ``('', '', text)`` when the file has no frontmatter fence.
    """
    m = _FM_RE.match(text)
    if not m:
        return ("", "", text)
    fm_raw = m.group(1)
    body = text[m.end():]
    return ("---\n", fm_raw, body)


def load_yaml_simple(text: str) -> dict:
    """Parse *text* as YAML and return a dict (empty dict on blank/None input)."""
    import yaml  # pyyaml — always available in this project

    return yaml.safe_load(text) or {}


# ---------------------------------------------------------------------------
# Top-level block upsert
# ---------------------------------------------------------------------------


def upsert_top_level_block(
    text: str,
    block_key: str,
    block_value: dict[str, Any],
) -> str:
    """Write or merge a top-level frontmatter mapping block.

    If *block_key* already exists in the frontmatter, its sub-keys are updated
    with the values from *block_value* (unrelated sub-keys are preserved).  If
    *block_key* is absent, the entire block is appended before the closing
    fence.

    Parameters
    ----------
    text:
        Full raw file text including frontmatter fences.
    block_key:
        Top-level YAML key to create or update (e.g. ``'upstream'``).
    block_value:
        Dict of sub-key/value pairs to write under *block_key*.

    Returns
    -------
    str
        Updated full file text.  Returns *text* unchanged if it has no
        frontmatter.
    """
    m = _FM_RE.match(text)
    if not m:
        return text

    fm_text = m.group(1)
    body_text = text[m.end():]

    import yaml  # pyyaml

    existing_fm: dict = yaml.safe_load(fm_text) or {}

    # Merge: preserve existing block, overlay with new values
    existing_block: dict = existing_fm.get(block_key) or {}
    merged_block = {**existing_block, **block_value}

    new_fm_text = _replace_block_in_fm_text(fm_text, block_key, merged_block)
    return f"---\n{new_fm_text}\n---\n{body_text}"


# ---------------------------------------------------------------------------
# Timeline event appender
# ---------------------------------------------------------------------------


def append_timeline_event(text: str, event: dict[str, Any]) -> str:
    """Append *event* to the ``timeline:`` list in the frontmatter.

    Uses pyyaml round-trip: parse the full frontmatter, append the event,
    re-serialise.  Returns the updated full file text.

    If the file has no frontmatter, returns *text* unchanged.
    """
    import yaml

    m = _FM_RE.match(text)
    if not m:
        return text

    fm_text = m.group(1)
    body_text = text[m.end():]

    fm_dict: dict = yaml.safe_load(fm_text) or {}
    if "timeline" not in fm_dict or fm_dict["timeline"] is None:
        fm_dict["timeline"] = []
    fm_dict["timeline"].append(event)

    new_fm_text = yaml.dump(fm_dict, sort_keys=False, allow_unicode=True).rstrip("\n")
    return f"---\n{new_fm_text}\n---\n{body_text}"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _format_field_value(value: Any) -> str:
    """Render a scalar value for inline YAML emission."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(value)
    if value is None:
        return "null"
    s = str(value)
    if re.match(r"^\d{4}-\d{2}-\d{2}", s) or ":" in s or not re.match(r"^[A-Za-z0-9_\-./]+$", s):
        return f"'{s}'"
    return s


def _replace_block_in_fm_text(
    fm_text: str,
    block_key: str,
    block_value: dict[str, Any],
) -> str:
    """Replace or append the *block_key* section in raw frontmatter text.

    Preserves all other lines verbatim.  Deterministic key ordering for the
    replaced block.
    """
    lines = fm_text.split("\n")
    key_pattern = re.compile(rf"^{re.escape(block_key)}\s*:")

    # Find the range occupied by an existing block (if any)
    block_start: int | None = None
    block_end: int | None = None

    for i, line in enumerate(lines):
        if key_pattern.match(line):
            block_start = i
            continue
        if block_start is not None and block_end is None:
            # Block ends when we hit a non-empty, non-indented, non-list line
            if line and not line[0].isspace() and not line.startswith("-"):
                block_end = i
                break

    if block_start is not None and block_end is None:
        block_end = len(lines)

    # Build the replacement block lines
    new_block_lines = [f"{block_key}:"]
    for k in sorted(block_value.keys()):
        v = block_value[k]
        formatted = _format_field_value(v)
        new_block_lines.append(f"  {k}: {formatted}")

    if block_start is not None:
        # Replace existing block
        new_lines = lines[:block_start] + new_block_lines + lines[block_end:]
    else:
        # Append as new block (with blank separator)
        new_lines = lines + [""] + new_block_lines

    return "\n".join(new_lines)
