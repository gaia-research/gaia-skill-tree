"""
gaia_registry_lib.frontmatter — regex-based YAML frontmatter parse and rewrite.

Shared implementation used by the Gaia CLI and registry scripts.

Public API
----------
split_frontmatter(text)
    Split raw file text into (fence, fm_content, body).

load_yaml_simple(text)
    Parse a YAML string into a dict (thin pyyaml wrapper).

update_list_item_in_frontmatter(text, list_key, row_index, field_updates)
    Update specific fields on the Nth item of a list block in the frontmatter.

upsert_top_level_block(text, block_key, block_value)
    Write or merge an entire top-level frontmatter mapping block.

append_timeline_event(text, event)
    Append a timeline event dict to the ``timeline:`` list in frontmatter.
"""

from __future__ import annotations

import re
from typing import Any

_FM_RE = re.compile(r"^---\r?\n(.*?)\r?\n---(?:\r?\n|$)", re.DOTALL)


def split_frontmatter(text: str) -> tuple[str, str, str]:
    """Split *text* into ``(pre_fence, fm_content, body)``.

    ``pre_fence`` is always ``'---\n'`` when frontmatter is present.
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
    import yaml

    return yaml.safe_load(text) or {}


def update_list_item_in_frontmatter(
    text: str,
    list_key: str,
    row_index: int,
    field_updates: dict[str, Any],
) -> str:
    """Update fields on the *row_index*-th item of the *list_key* block.

    Existing non-updated fields are preserved verbatim. New fields are inserted
    after the first line of the item block (the ``- …`` line). Returns *text*
    unchanged if the frontmatter or requested item cannot be located.
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
        return text

    if item_end_line is None:
        item_end_line = len(lines)

    block_lines = lines[item_start_line:item_end_line]
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

    insert_pos = 1
    for field, value in field_updates.items():
        if field not in handled:
            formatted = _format_field_value(value)
            new_block.insert(insert_pos, f"  {field}: {formatted}")
            insert_pos += 1

    new_lines = lines[:item_start_line] + new_block + lines[item_end_line:]
    new_fm = "\n".join(new_lines)
    return f"---\n{new_fm}\n---\n{body_text}"


def upsert_top_level_block(
    text: str,
    block_key: str,
    block_value: dict[str, Any],
) -> str:
    """Write or merge a top-level frontmatter mapping block."""
    m = _FM_RE.match(text)
    if not m:
        return text

    fm_text = m.group(1)
    body_text = text[m.end():]

    import yaml

    existing_fm: dict = yaml.safe_load(fm_text) or {}
    existing_block: dict = existing_fm.get(block_key) or {}
    merged_block = {**existing_block, **block_value}

    new_fm_text = _replace_block_in_fm_text(fm_text, block_key, merged_block)
    return f"---\n{new_fm_text}\n---\n{body_text}"


def append_timeline_event(text: str, event: dict[str, Any]) -> str:
    """Append *event* to the ``timeline:`` list in the frontmatter.

    Uses pyyaml round-trip: parse the full frontmatter, append the event,
    re-serialise. Returns the updated full file text. If the file has no
    frontmatter, returns *text* unchanged.
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
    """Replace or append the *block_key* section in raw frontmatter text."""
    lines = fm_text.split("\n")
    key_pattern = re.compile(rf"^{re.escape(block_key)}\s*:")

    block_start: int | None = None
    block_end: int | None = None

    for i, line in enumerate(lines):
        if key_pattern.match(line):
            block_start = i
            continue
        if block_start is not None and block_end is None:
            if line and not line[0].isspace() and not line.startswith("-"):
                block_end = i
                break

    if block_start is not None and block_end is None:
        block_end = len(lines)

    new_block_lines = [f"{block_key}:"]
    for k in sorted(block_value.keys()):
        v = block_value[k]
        formatted = _format_field_value(v) if v is not None else "null"
        new_block_lines.append(f"  {k}: {formatted}")

    if block_start is not None:
        new_lines = lines[:block_start] + new_block_lines + lines[block_end:]
    else:
        new_lines = lines + [""] + new_block_lines

    return "\n".join(new_lines)
