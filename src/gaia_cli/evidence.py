"""Evidence inheritance for the rank-less generic / named skill model.

Generic skill refs are pure taxonomy and hold capability-level (Class A /
academic) evidence. Every named skill that points at a generic via
``genericSkillRef`` *inherits* that evidence, and may add its own
implementation-specific evidence (e.g. its GitHub repo).

This module is the single place that computes a named skill's effective
evidence pool, used by rendering, the CLI, and validation.
"""

from __future__ import annotations


# Legacy evidence type aliases, normalized before keying (``repo`` is the
# historical spelling of ``repo-own``). ``trustMagnitude.TYPE_ALIASES`` is this
# same mapping so the merge here and the scoring-time dedup there cannot drift.
EVIDENCE_TYPE_ALIASES: dict = {"repo": "repo-own"}


def canonicalSourceUrl(url) -> str | None:
    """Normalize a source URL for same-source dedup (RFC section 5.2).

    Strips fragments and trailing slashes, normalizes ``tree/`` to ``blob/``,
    lower-cases. Returns None for an empty or missing URL.
    """
    if not url:
        return None
    text = str(url).strip()
    if not text:
        return None
    if "#" in text:
        text = text.split("#", 1)[0]
    text = text.replace("/tree/", "/blob/")
    while text.endswith("/"):
        text = text[:-1]
    return text.lower()


def evidenceTypeOf(entry: dict) -> str | None:
    """Resolve an evidence row's type, normalizing legacy aliases."""
    rowType = entry.get("type")
    if not rowType:
        return None
    return EVIDENCE_TYPE_ALIASES.get(rowType, rowType)


def evidenceDedupKey(entry: dict) -> tuple:
    """Same-source dedup key: ``(evidence type, canonical source URL)``.

    Dedup is *within type* (META.md / curation authority map): a
    ``github-stars-own`` row and a ``repo-own`` row at one URL are different
    keys and both count toward Trust Magnitude. Mirrors ``_dedupeSameSource``
    in ``trustMagnitude.py``.
    """
    url = (
        canonicalSourceUrl(entry.get("source"))
        or canonicalSourceUrl(entry.get("url"))
        or canonicalSourceUrl(entry.get("sourceUrl"))
    )
    return (evidenceTypeOf(entry) or "", url)


def merge_evidence(*groups) -> list:
    """Concatenate evidence lists, de-duplicating by ``(type, source)`` (first wins).

    Rows of *different* types at the same URL are distinct evidence and are
    all kept; only a same-type, same-canonical-source repeat is dropped.
    """
    seen = set()
    merged = []
    for group in groups:
        for entry in group or []:
            key = evidenceDedupKey(entry)
            if key in seen:
                continue
            seen.add(key)
            merged.append(entry)
    return merged


def inherited_evidence(named_skill: dict, generic_node: dict | None) -> list:
    """Return a named skill's effective evidence pool.

    Own evidence first (most specific), then the generic ref's inherited
    capability evidence. De-duplicated by ``(type, source)``.
    """
    generic = (generic_node or {}).get("evidence") if generic_node else []
    return merge_evidence(named_skill.get("evidence"), generic)


def build_generic_evidence_map(skills) -> dict:
    """Map generic skill id -> its evidence list, for inheritance lookups."""
    return {s["id"]: (s.get("evidence") or []) for s in skills if "id" in s}
