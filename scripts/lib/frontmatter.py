"""
scripts.lib.frontmatter — regex-based YAML frontmatter parse and rewrite.

Ported and generalised from ``scripts/stargazerHeartbeat.py`` so that both
the heartbeat and the upcoming upstream-watcher share identical parsing logic
(upstream-watcher design §9, PR 2 of 7).

Public API
----------
split_frontmatter(text)
    Split raw file text into (fence, fm_content, body).

load_yaml_simple(text)
    Parse a YAML string into a dict (thin pyyaml wrapper).

update_list_item_in_frontmatter(text, list_key, row_index, field_updates)
    Update specific fields on the Nth item of a list block in the frontmatter.
    Generalised form of the heartbeat's ``_update_evidence_row_in_text``.

upsert_top_level_block(text, block_key, block_value)
    Write or merge an entire top-level frontmatter mapping block.
    Used by the watcher to write/update ``upstream:`` in one shot.
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

    ``pre_fence`` is always ``'---\\n'`` when frontmatter is present.
    Returns ``('', '', text)`` when the file has no frontmatter fence.

    Ported verbatim from ``stargazerHeartbeat._split_frontmatter``, renamed
    to a public API (no leading underscore).
    """
    m = _FM_RE.match(text)
    if not m:
        return ("", "", text)
    fm_raw = m.group(1)
    body = text[m.end():]
    return ("---\n", fm_raw, body)


def load_yaml_simple(text: str) -> dict:
    """Parse *text* as YAML and return a dict (empty dict on blank/None input).

    Thin wrapper around ``yaml.safe_load`` — pyyaml is always available in
    this project (listed in ``pyproject.toml`` dependencies).

    Ported from ``stargazerHeartbeat._load_yaml_simple``.
    """
    import yaml  # pyyaml — always available in this project

    return yaml.safe_load(text) or {}


# ---------------------------------------------------------------------------
# List-item rewriter
# ---------------------------------------------------------------------------


def update_list_item_in_frontmatter(
    text: str,
    list_key: str,
    row_index: int,
    field_updates: dict[str, Any],
) -> str:
    """Update fields on the *row_index*-th item of the *list_key* block.

    Generalised form of ``stargazerHeartbeat._update_evidence_row_in_text``.
    The heartbeat use-case (``list_key='evidence'``,
    ``field_updates={'stars': N, 'updatedAt': 'YYYY-MM-DD'}``) still works
    unchanged through this API.

    Parameters
    ----------
    text:
        Full raw file text including frontmatter fences.
    list_key:
        Name of the top-level list key (e.g. ``'evidence'``, ``'timeline'``).
    row_index:
        Zero-based index of the list item to update.
    field_updates:
        Mapping of ``{field_name: new_value}`` to apply/insert on the item.
        Existing non-updated fields are preserved verbatim.  New fields are
        inserted after the first line of the item block (the ``- …`` line).

    Returns
    -------
    str
        The full file text with the targeted item rewritten.  Returns *text*
        unchanged if the frontmatter or the requested item cannot be located.
    """
    m = _FM_RE.match(text)
    if not m:
        return text

    fm_text = m.group(1)
    body_text = text[m.end():]

    lines = fm_text.split("\n")
    in_block = False
    item_idx = -1
    item_start_line: int | None = None
    item_end_line: int | None = None

    for i, line in enumerate(lines):
        if re.match(rf"^{re.escape(list_key)}\s*:", line):
            in_block = True
            continue
        if in_block:
            # A top-level key (non-indented, non-list-item) ends the block
            if line and not line[0].isspace() and not line.startswith("-"):
                in_block = False
                if item_start_line is not None and item_end_line is None:
                    item_end_line = i
                break
            if re.match(r"^- ", line):
                item_idx += 1
                if item_idx == row_index:
                    item_start_line = i
                elif item_idx == row_index + 1:
                    item_end_line = i
                    break

    if item_start_line is None:
        return text  # Could not locate the requested item

    if item_end_line is None:
        item_end_line = len(lines)

    block_lines = lines[item_start_line:item_end_line]

    # Track which fields we've handled (to know which need inserting)
    handled: set[str] = set()
    new_block: list[str] = []

    for bl in block_lines:
        replaced = False
        for field, value in field_updates.items():
            if re.match(rf"\s+{re.escape(field)}\s*:", bl):
                indent_m = re.match(r"(\s+)", bl)
                prefix = indent_m.group(1) if indent_m else "  "
                formatted = _format_field_value(value)
                new_block.append(f"{prefix}{field}: {formatted}")
                handled.add(field)
                replaced = True
                break
        if not replaced:
            new_block.append(bl)

    # Insert any fields not found in the existing block (after the '- …' line)
    insert_pos = 1
    for field, value in field_updates.items():
        if field not in handled:
            formatted = _format_field_value(value)
            new_block.insert(insert_pos, f"  {field}: {formatted}")
            insert_pos += 1

    new_lines = lines[:item_start_line] + new_block + lines[item_end_line:]
    new_fm = "\n".join(new_lines)
    return f"---\n{new_fm}\n---\n{body_text}"


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

    Key ordering within the merged/inserted block is deterministic (sorted).

    Intended use: the upstream-watcher writing/updating ``upstream:`` in one
    shot.

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

    # Rebuild the top-level frontmatter with the block updated
    # Strategy: parse all keys, replace or append the target block.
    new_fm_dict = dict(existing_fm)
    new_fm_dict[block_key] = {k: merged_block[k] for k in sorted(merged_block)}

    # Serialise back.  We want to preserve the *rest* of the frontmatter
    # exactly as-is.  Safe strategy: locate (or append) the block via
    # line-level surgery so unrelated keys retain their formatting.
    new_fm_text = _replace_block_in_fm_text(fm_text, block_key, merged_block)
    return f"---\n{new_fm_text}\n---\n{body_text}"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _format_field_value(value: Any) -> str:
    """Render a scalar value for inline YAML emission.

    Strings are single-quoted if they look like dates or ISO timestamps;
    integers/booleans are unquoted; other strings are single-quoted.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(value)
    # Strings: single-quote if they contain a colon, look like a date/datetime,
    # or are not simple alphanumeric tokens.
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
        formatted = _format_field_value(v) if v is not None else "null"
        new_block_lines.append(f"  {k}: {formatted}")

    if block_start is not None:
        # Replace existing block
        new_lines = lines[:block_start] + new_block_lines + lines[block_end:]
    else:
        # Append as new block (with blank separator)
        new_lines = lines + [""] + new_block_lines

    return "\n".join(new_lines)
