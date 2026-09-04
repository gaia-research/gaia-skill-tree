"""Portable share bundles — `gaia share` producer and `gaia install <bundle>` consumer.

A *share bundle* is a single, self-contained JSON artifact that travels anywhere
(Issue #128). It carries three things:

1. A snapshot of the sharer's local skill tree (`unlockedSkills` + levels), so a
   bundle from *any* repo's state shares 100% — even if those skills are not yet
   canonical.
2. A flat **install manifest** that points each installable skill at its *source*
   repository via the existing `links.github` `blob/branch/subpath` path, so
   `gaia install` consumes it through the same resolution code that
   `gaia skills install` already uses (no rebuild — see install.py).
3. Pre-resolved **skill metadata** (name / level / type / owned-prereq edges) so
   the consumer can re-render the sharer's tree preview with zero dependency on
   their own registry. A bundle can span multiple repos and still present as one
   tree at the user level (the "mattpocock's collection" case).

The producer does the heavy lifting (canonical→named prereq translation, source
resolution) at `gaia share` time; the consumer renderer is intentionally dumb so
the preview is always faithful to the sharer regardless of the consumer's setup.
"""

import json
import os
import re
from datetime import datetime, timezone

from gaia_cli.registry import (
    generated_output_dir,
    named_skills_index_path,
    registry_graph_path,
)
from gaia_cli.treeManager import load_tree

BUNDLE_KIND = "gaia-share-bundle"
BUNDLE_VERSION = "1"

_TYPE_SYMBOL = {"basic": "○", "extra": "◇", "ultimate": "◆", "unique": "◉"}


# ─── github url normalization ──────────────────────────────────────────────────


def _normalize_github_url(url):
    """Convert a GitHub directory-view URL (``tree/``) to the installer's ``blob/``.

    ``install.py::_parse_github_url`` only recognises ``blob/branch/subpath``. A
    ``tree/`` URL (what GitHub's directory view produces) would otherwise install
    to the repo root and make the skill undiscoverable. See CLAUDE.md §1.
    """
    if not url or not isinstance(url, str):
        return None
    return url.replace("/tree/", "/blob/", 1)


# ─── registry data loaders ─────────────────────────────────────────────────────


def _load_canonical_skill_map(registry_path):
    """{canonical_id -> skill dict} from gaia.json, or {} if unavailable."""
    path = registry_graph_path(registry_path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    return {s["id"]: s for s in data.get("skills", []) if s.get("id")}


def _load_named_by_id(registry_path):
    """{named_id -> index entry} from named-skills.json, or {} if unavailable."""
    path = named_skills_index_path(registry_path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    result = {}
    for bucket in data.get("buckets", {}).values():
        for entry in bucket:
            if entry.get("id"):
                result[entry["id"]] = entry
    for entry in data.get("awaitingClassification", []):
        if entry.get("id"):
            result[entry["id"]] = entry
    return result


# ─── producer ──────────────────────────────────────────────────────────────────


def build_share_bundle(username, registry_path, source_repo=None, now=None):
    """Assemble a self-contained share bundle for ``username``.

    Returns the bundle dict. Raises ValueError if the user has no skill tree.
    """
    tree = load_tree(username, registry_path=registry_path)
    if not tree:
        raise ValueError(f"No skill tree found for user '{username}'.")

    canon = _load_canonical_skill_map(registry_path)
    named_by_id = _load_named_by_id(registry_path)

    unlocked = tree.get("unlockedSkills", [])
    owned_ids = {u.get("skillId") for u in unlocked if u.get("skillId")}

    # First pass: resolve per-skill metadata + generic ref.
    skill_meta = {}
    generic_to_owned = {}  # canonical genericSkillRef -> owned named id
    for u in unlocked:
        sid = u.get("skillId")
        if not sid:
            continue
        named_entry = named_by_id.get(sid)
        canon_entry = canon.get(sid, {})

        generic_ref = None
        if named_entry:
            name = named_entry.get("name") or sid
            stype = named_entry.get("type") or canon_entry.get("type", "basic")
            generic_ref = named_entry.get("genericSkillRef")
            is_named = True
        else:
            name = canon_entry.get("name") or sid
            stype = canon_entry.get("type", "basic")
            # A bare canonical id is its own generic ref.
            generic_ref = sid if "/" not in sid else None
            is_named = "/" in sid

        level = u.get("level") or (named_entry or {}).get("level") or canon_entry.get("level", "?")

        skill_meta[sid] = {
            "name": name,
            "level": level,
            "type": stype,
            "named": is_named,
            "genericRef": generic_ref,
            "prereqs": [],
        }
        if generic_ref and generic_ref not in generic_to_owned:
            generic_to_owned[generic_ref] = sid

    # Second pass: translate canonical prerequisites into owned-skill edges so the
    # preview shows the structure among the sharer's own skills.
    for sid, meta in skill_meta.items():
        generic_ref = meta.get("genericRef")
        if not generic_ref:
            continue
        canon_prereqs = canon.get(generic_ref, {}).get("prerequisites", [])
        edges = set()
        for p in canon_prereqs:
            if p in owned_ids:  # canonical prereq owned directly
                edges.add(p)
            owned = generic_to_owned.get(p)  # prereq owned under a named id
            if owned:
                edges.add(owned)
        edges.discard(sid)
        meta["prereqs"] = sorted(edges)

    # Build the flat install manifest (only skills with a resolvable source).
    install_manifest = []
    for u in unlocked:
        sid = u.get("skillId")
        if not sid:
            continue
        named_entry = named_by_id.get(sid)
        if not named_entry:
            continue  # no named implementation → not installable, preview-only
        github = _normalize_github_url((named_entry.get("links") or {}).get("github"))
        suite_components = named_entry.get("suiteComponents") or []
        if not github and not suite_components:
            continue  # neither a source nor a suite → can't install
        entry = {
            "id": sid,
            "name": named_entry.get("name") or sid,
            "level": skill_meta[sid]["level"],
            "type": named_entry.get("type", "basic"),
        }
        if github:
            entry["github"] = github
        if suite_components:
            entry["suiteComponents"] = suite_components
        if named_entry.get("genericSkillRef"):
            entry["genericSkillRef"] = named_entry["genericSkillRef"]
        install_manifest.append(entry)

    timestamp = now or datetime.now(timezone.utc)
    generated_at = timestamp.replace(microsecond=0).isoformat().replace("+00:00", "Z")

    return {
        "kind": BUNDLE_KIND,
        "bundleVersion": BUNDLE_VERSION,
        "generatedAt": generated_at,
        "sharer": username,
        "sourceRepo": source_repo or tree.get("sourceRepo"),
        "tree": {
            "userId": tree.get("userId", username),
            "updatedAt": tree.get("updatedAt"),
            "unlockedSkills": unlocked,
            "stats": tree.get("stats", {}),
        },
        "skillMeta": skill_meta,
        "install": install_manifest,
    }


def default_bundle_path(username, registry_path):
    return os.path.join(
        generated_output_dir(registry_path), "share", f"{username}-share-bundle.json"
    )


def write_bundle(bundle, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(bundle, f, indent=2)
        f.write("\n")
    return path


# ─── consumer: bundle loading + validation ─────────────────────────────────────


def _looks_like_bundle_ref(ref):
    """True if ``ref`` should be treated as a share bundle rather than a skill id.

    Skill ids are bare slugs or ``contributor/slug`` — never URLs and never
    ``.json`` paths, so those two shapes unambiguously signal a bundle.
    """
    if not ref:
        return False
    return ref.startswith(("http://", "https://")) or ref.endswith(".json")


def load_bundle(ref):
    """Load a bundle dict from a local file path or an http(s) URL.

    Raises ValueError if it does not parse or is not a share bundle.
    """
    if ref.startswith(("http://", "https://")):
        import urllib.request

        try:
            with urllib.request.urlopen(ref, timeout=30) as resp:  # noqa: S310 (user-provided URL)
                raw = resp.read().decode("utf-8")
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"Could not fetch bundle from {ref}: {exc}") from exc
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Bundle at {ref} is not valid JSON: {exc}") from exc
    else:
        try:
            with open(ref, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError as exc:
            raise ValueError(f"Bundle file not found: {ref}") from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"Bundle file {ref} is not valid JSON: {exc}") from exc

    if not isinstance(data, dict) or data.get("kind") != BUNDLE_KIND:
        raise ValueError(
            f"{ref} is not a Gaia share bundle (missing kind == '{BUNDLE_KIND}')."
        )
    return data


# ─── consumer: tree preview renderer ───────────────────────────────────────────


def render_bundle_tree_lines(bundle, color=False):
    """Render the sharer's tree as a list of lines, self-contained from skillMeta."""
    meta = bundle.get("skillMeta", {})
    sharer = bundle.get("sharer", bundle.get("tree", {}).get("userId", "unknown"))

    # Roots: owned skills that are not a prereq of any other owned skill.
    prereq_targets = set()
    for m in meta.values():
        prereq_targets.update(m.get("prereqs", []))
    roots = sorted(sid for sid in meta if sid not in prereq_targets)
    # Fallback: if every node is someone's prereq (a cycle), show them all flat.
    if not roots and meta:
        roots = sorted(meta)

    lines = [_color_sharer(sharer) if color else sharer]
    seen = set()

    def render(sid, prefix, is_last):
        m = meta.get(sid, {})
        stype = m.get("type", "basic")
        symbol = _TYPE_SYMBOL.get(stype, "○")
        level = m.get("level", "?")
        star = f" {level}" if level and level not in ("0★", "?") else ""
        label = f"{symbol} {sid}{star}"
        connector = "└── " if is_last else "├── "
        if sid in seen:
            lines.append(prefix + connector + label + " (see above)")
            return
        seen.add(sid)
        if color:
            lines.append(_dim(prefix + connector) + _color_label(label, level, m.get("named")))
        else:
            lines.append(prefix + connector + label)
        children = sorted(c for c in m.get("prereqs", []) if c in meta)
        child_prefix = prefix + ("    " if is_last else "│   ")
        for i, child in enumerate(children):
            render(child, child_prefix, i == len(children) - 1)

    for i, root in enumerate(roots):
        render(root, "", i == len(roots) - 1)
    return lines


def _color_sharer(text):
    try:
        from gaia_cli.formatting import _fg, _reset, COLOR_CONTRIBUTOR

        return f"{_fg(*COLOR_CONTRIBUTOR)}{text}{_reset()}"
    except Exception:  # noqa: BLE001
        return text


def _dim(text):
    try:
        from gaia_cli.formatting import _use_color

        return f"\033[2m{text}\033[22m" if _use_color() else text
    except Exception:  # noqa: BLE001
        return text


def _color_label(label, level, named):
    try:
        from gaia_cli.formatting import _fg, _reset, RANK_COLORS, COLOR_CONTRIBUTOR

        if named:
            color = COLOR_CONTRIBUTOR
        else:
            color = RANK_COLORS.get(level, RANK_COLORS.get("0★", (148, 163, 184)))
        return f"{_fg(*color)}{label}{_reset()}"
    except Exception:  # noqa: BLE001
        return label


def render_bundle_tree(bundle, color=False):
    return "\n".join(render_bundle_tree_lines(bundle, color=color))


# ─── consumer: guided install flow ─────────────────────────────────────────────


def _prompt_choice(input_fn):
    prompt = "Install? [A]ll  [P]ick  [V]iew only  [Q]uit: "
    try:
        raw = (input_fn(prompt) or "").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return "quit"
    if raw in ("a", "all"):
        return "all"
    if raw in ("p", "pick"):
        return "pick"
    if raw in ("q", "quit", ""):
        return "quit"
    return "view"


def _prompt_picks(manifest, input_fn):
    try:
        raw = input_fn("Enter numbers to install (space/comma separated): ").strip()
    except (EOFError, KeyboardInterrupt):
        return []
    picks = []
    for tok in re.split(r"[\s,]+", raw):
        if not tok:
            continue
        try:
            idx = int(tok) - 1
        except ValueError:
            continue
        if 0 <= idx < len(manifest):
            picks.append(idx)
    return picks


def _install_entry(entry, registry_path, location):
    """Resolve and install a single manifest entry.

    Reuse the registry resolution path (`gaia skills install`) when the skill
    exists in the consumer's registry; otherwise install directly from the
    bundle's source URL (the multi-repo / foreign-skill case).

    Returns "installed", "failed", or "unresolved".
    """
    from gaia_cli.install import (
        _install_single,
        install_skill,
        resolve_named_skill_reference,
    )

    sid = entry.get("id")
    resolved_id, _meta = resolve_named_skill_reference(sid, registry_path)
    if resolved_id:
        return "installed" if install_skill(resolved_id, registry_path, location=location) else "failed"

    github = entry.get("github")
    if github:
        meta = {"links": {"github": github}}
        if entry.get("suiteComponents"):
            meta["suiteComponents"] = entry["suiteComponents"]
        return "installed" if _install_single(sid, meta, registry_path, set(), location=location) else "failed"

    return "unresolved"


def install_bundle(
    bundle_ref,
    registry_path,
    location="local",
    auto=None,
    input_fn=None,
    out=print,
):
    """Render the sharer's tree, then walk the A/P/V/Q install flow.

    Args:
        bundle_ref: file path, URL, or an already-loaded bundle dict.
        auto: skip the prompt with a fixed choice ("all"/"pick"/"view"/"quit").
            When None and stdin is not a TTY, defaults to "view" (no surprise
            installs in automation).
        input_fn: injectable input() for tests.

    Returns a summary dict: {installed, skipped, unresolved, failed} lists of ids.
    """
    import sys

    if input_fn is None:
        input_fn = input

    bundle = bundle_ref if isinstance(bundle_ref, dict) else load_bundle(bundle_ref)

    sharer = bundle.get("sharer", "someone")
    manifest = bundle.get("install", [])

    out(f"\nShared skill tree from {sharer}:\n")
    for line in render_bundle_tree_lines(bundle, color=_can_color()):
        out(line)
    out("")

    if not manifest:
        out("This bundle has no installable skills (preview only).")
        return {"installed": [], "skipped": [], "unresolved": [], "failed": []}

    out(f"{len(manifest)} installable skill(s):")
    for i, entry in enumerate(manifest, 1):
        src = entry.get("github", "suite" if entry.get("suiteComponents") else "?")
        out(f"  {i:>2}. {entry['id']}  ({entry.get('level', '?')})  → {src}")
    out("")

    choice = auto
    if choice is None:
        choice = _prompt_choice(input_fn) if sys.stdin.isatty() else "view"

    if choice == "quit":
        out("Quit — nothing installed.")
        return {
            "installed": [],
            "skipped": [e["id"] for e in manifest],
            "unresolved": [],
            "failed": [],
        }
    if choice == "view":
        out("View only — nothing installed.")
        return {
            "installed": [],
            "skipped": [e["id"] for e in manifest],
            "unresolved": [],
            "failed": [],
        }

    if choice == "pick":
        picks = _prompt_picks(manifest, input_fn)
        chosen_idx = set(picks)
    else:  # all
        chosen_idx = set(range(len(manifest)))

    summary = {"installed": [], "skipped": [], "unresolved": [], "failed": []}
    for i, entry in enumerate(manifest):
        if i not in chosen_idx:
            summary["skipped"].append(entry["id"])
            continue
        result = _install_entry(entry, registry_path, location)
        summary[result].append(entry["id"])

    _print_summary(summary, out)
    return summary


def _print_summary(summary, out):
    out("\nSummary:")
    out(f"  installed:  {len(summary['installed'])}  {', '.join(summary['installed'])}".rstrip())
    out(f"  skipped:    {len(summary['skipped'])}  {', '.join(summary['skipped'])}".rstrip())
    unresolved = summary["unresolved"] + summary["failed"]
    out(f"  unresolved: {len(unresolved)}  {', '.join(unresolved)}".rstrip())


def _can_color():
    try:
        from gaia_cli.formatting import _use_color

        return _use_color()
    except Exception:  # noqa: BLE001
        return False
