"""Python mirrors of docs/js/atlas-helpers.js.

Shared helpers used by registry generators (generateProfilePages.py,
generateProjections.py, generateOgCards.py) to keep slash-name and
contributor-handle conventions identical between the browser JS and the
build-time HTML/markdown output.
"""

from __future__ import annotations

import html


def named_slug(entry: dict) -> str:
    """Return '/{second_segment}' from entry["id"].

    For ``{"id": "karpathy/autoresearch"}`` → ``"/autoresearch"``.
    Falls back to ``"/{entry['genericSkillRef'] or entry['id']}"`` if the
    id has no slash.
    """
    if not isinstance(entry, dict):
        return ""
    raw_id = entry.get("id", "") or ""
    if "/" in raw_id:
        return "/" + raw_id.split("/", 1)[1]
    fallback = entry.get("genericSkillRef") or raw_id
    return "/" + (fallback or "")


def profile_href(handle: str, rel: str = "./u/") -> str:
    """Return ``f"{rel}{handle}/"`` preserving handle casing."""
    return f"{rel}{handle or ''}/"


def handle_link(handle: str, rel: str = "./u/", extra_class: str = "") -> str:
    """Return an HTML anchor ``<a class="atlas-handle …">@handle</a>``.

    Empty handle → returns empty string. ``html.escape`` is applied to the
    handle and the href so callers can pass raw data safely.
    """
    if not handle:
        return ""
    cls = "atlas-handle" + (f" {extra_class}" if extra_class else "")
    href = profile_href(handle, rel)
    return (
        f'<a class="{html.escape(cls)}" href="{html.escape(href)}">'
        f"@{html.escape(handle)}</a>"
    )


def markdown_handle_link(handle: str, rel: str = "u/", with_at: bool = True) -> str:
    """Return a markdown link of the form ``[@handle](rel{handle}/)``.

    Used by registry/markdown projections (``docs/tree.md``,
    ``registry/skills/**/*.md``, ``registry/registry.md``,
    ``registry/combinations.md``) so contributor mentions render as
    hover-underlined links when the file is rendered by GitHub or the
    docs server. The default ``rel`` is ``u/`` because ``docs/tree.md``
    is served from ``/tree.md`` and resolves ``u/<handle>/`` against
    the docs root.

    Set ``with_at=False`` to omit the leading ``@`` — useful inside a
    composite identifier like ``[karpathy](u/karpathy/)/autoresearch``.
    """
    if not handle:
        return ""
    label = f"@{handle}" if with_at else handle
    return f"[{label}]({rel}{handle}/)"
