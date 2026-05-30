import json
import os
import re

from gaia_cli.registry import named_skills_index_path, user_tree_path

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$")
_TRANSCENDENT_LEVELS = {"5★", "6★"}

# Named-skill red and gradient endpoints
_COLOR_NAMED = (239, 68, 68)
_GRAD_GOLD = (245, 180, 30)
_GRAD_RED = (220, 38, 38)


def _check_username(username: str) -> None:
    if not username or not _USERNAME_RE.match(username):
        raise ValueError(f"Invalid username: {username!r}")


def load_tree(username, registry_path="."):
    _check_username(username)
    tree_path = user_tree_path(registry_path, username)
    if not os.path.exists(tree_path):
        return None
    with open(tree_path, 'r') as f:
        return json.load(f)

def save_tree(username, tree_data, registry_path="."):
    _check_username(username)
    tree_path = user_tree_path(registry_path, username)
    os.makedirs(os.path.dirname(tree_path), exist_ok=True)
    with open(tree_path, 'w') as f:
        json.dump(tree_data, f, indent=2)

def show_status(tree_data):
    if not tree_data:
        print("No skill tree found.")
        return
    print(f"User: {tree_data.get('userId')}")
    print(f"Last Updated: {tree_data.get('updatedAt')}")
    stats = tree_data.get('stats', {})
    print(f"Total Unlocked: {stats.get('totalUnlocked', 0)}")
    print(f"Highest Rarity: {stats.get('highestRarity', 'common').capitalize()}")
    pending = tree_data.get('pendingCombinations', [])
    if pending:
        print("\nPending Combinations:")
        for p in pending:
            print(f"- {p.get('candidateResult')} (Floor: {p.get('levelFloor')})")


# ─── named / local lookups ────────────────────────────────────────────────────

def _load_named_lookup(registry_path):
    index_path = named_skills_index_path(registry_path)
    if not os.path.exists(index_path):
        return {}
    with open(index_path, "r", encoding="utf-8") as f:
        index = json.load(f)
    result = {}
    for ref, entries in index.get("buckets", {}).items():
        if entries:
            origin = next((e for e in entries if e.get("origin")), entries[0])
            result[ref] = origin
    return result


_SKILL_MD_CANDIDATES = ("skill.md", "SKILL.md", "README.md", "readme.md")


def _iter_manifest_refs(registry_path):
    """Yield (generic_ref, entry) for each installed skill with a resolved genericSkillRef."""
    manifest_path = os.path.join(".gaia", "install-manifest.json")
    if not os.path.exists(manifest_path):
        return
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    for entry in manifest.get("installed", []):
        sid = entry.get("id", "")
        md_path = None

        # Modern manifests: localPath points to the installed/symlinked dir
        local_path = entry.get("localPath", "")
        if local_path and os.path.isdir(local_path):
            for candidate in _SKILL_MD_CANDIDATES:
                p = os.path.join(local_path, candidate)
                if os.path.isfile(p):
                    md_path = p
                    break

        # Fallback: registry/named/<contrib>/<name>.md
        if not md_path and sid and "/" in sid:
            contrib, name = sid.split("/", 1)
            p = os.path.join(registry_path, "registry", "named", contrib, f"{name}.md")
            if os.path.isfile(p):
                md_path = p

        # Legacy: sourceRef
        if not md_path:
            source_ref = entry.get("sourceRef", "")
            if source_ref:
                p = os.path.join(registry_path, source_ref)
                if os.path.isfile(p):
                    md_path = p

        if not md_path:
            continue

        try:
            with open(md_path, "r", encoding="utf-8") as sf:
                text = sf.read()
            m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
            if not m:
                continue
            try:
                import yaml
                fm = yaml.safe_load(m.group(1)) or {}
            except ImportError:
                fm = {}
                for line in m.group(1).split('\n'):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if ':' in line:
                        k, v = line.split(':', 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if v.lower() == 'true':
                            v = True
                        elif v.lower() == 'false':
                            v = False
                        fm[k] = v
            ref = fm.get("genericSkillRef")
            if ref:
                yield ref, entry
        except Exception:
            pass


def _load_local_lookup(registry_path):
    return {ref: entry for ref, entry in _iter_manifest_refs(registry_path)}


# ─── color helpers ────────────────────────────────────────────────────────────

def _gradient_text(text, start_rgb, end_rgb):
    from gaia_cli.cardRenderer import fg, reset, _use_color
    if not _use_color():
        return text
    n = max(len(text) - 1, 1)
    parts = []
    for i, ch in enumerate(text):
        t = i / n
        r = int(start_rgb[0] + t * (end_rgb[0] - start_rgb[0]))
        g = int(start_rgb[1] + t * (end_rgb[1] - start_rgb[1]))
        b = int(start_rgb[2] + t * (end_rgb[2] - start_rgb[2]))
        parts.append(fg(r, g, b) + ch)
    return "".join(parts) + reset()


def _color_entry(symbol, plain_label, tier, is_named, level, current_user=None):
    from gaia_cli.cardRenderer import fg, reset, bold, _use_color, TIER_COLORS, RANK_COLORS, COLOR_CONTRIBUTOR, COLOR_LOCAL_USER
    if not _use_color():
        return f"{symbol} {plain_label}"
    if is_named:
        if level in _TRANSCENDENT_LEVELS:
            colored = _gradient_text(f"{symbol} {plain_label}", _GRAD_GOLD, _GRAD_RED)
            return f"{bold()}{colored}{reset()}"
        
        # Named skills
        rc = RANK_COLORS.get(level, (148, 163, 184))
        
        # Check for contributor prefix
        parts = plain_label.split("[")[0].strip().split("/", 1)
        if len(parts) == 2 and parts[0]:
            contrib_part = parts[0]
            rest = parts[1]
            color = COLOR_LOCAL_USER if current_user and contrib_part == current_user else COLOR_CONTRIBUTOR
            return f"{fg(*color)}{symbol} {contrib_part}{reset()}/{fg(*rc)}{rest}{reset()}"
        
        # No contributor part (or leading slash)
        color = COLOR_CONTRIBUTOR
        if plain_label.startswith("/"):
            # If it starts with / but no contributor, it's a local/own nickname
            color = COLOR_LOCAL_USER
        
        return f"{bold()}{fg(*color)}{symbol} {plain_label}{reset()}"
    
    # Canon skills: rank color for entire label
    rc = RANK_COLORS.get(level, (148, 163, 184))
    return f"{fg(*rc)}{symbol} {plain_label}{reset()}"


def _dim(text):
    from gaia_cli.cardRenderer import _use_color
    return f"\033[2m{text}\033[22m" if _use_color() else text


# ─── label helpers ────────────────────────────────────────────────────────────

_TYPE_SYMBOL = {"basic": "○", "extra": "◇", "ultimate": "◆"}


def _plain_label(skill_id, skill_map, named_by_ref, local_by_ref, mode, canon=False, current_user=None):
    level = skill_map.get(skill_id, {}).get("level", "?")
    if canon:
        return f"/{skill_id}  [{level}]"
    
    if mode == "title":
        name = skill_map.get(skill_id, {}).get("name", skill_id)
        return f"{name}  [{level}]"
    
    local = local_by_ref.get(skill_id)
    named = named_by_ref.get(skill_id)
    
    specific = local or named
    if specific:
        full_id = specific.get("id")
        if full_id:
            if "/" in full_id:
                contrib, nickname = full_id.split("/", 1)
                if current_user and contrib == current_user:
                    return f"/{nickname}  [{level}]"
                return f"{full_id}  [{level}]"
            return f"/{full_id}  [{level}]"

    return f"/{skill_id}  [{level}]"


def _is_named(skill_id, named_by_ref, local_by_ref):
    return skill_id in named_by_ref or skill_id in local_by_ref


# ─── recursive renderer ───────────────────────────────────────────────────────

def _render_subtree(skill_id, skill_map, display_ids, named_by_ref, local_by_ref, mode, prefix, is_last, seen, canon=False, current_user=None):
    skill = skill_map.get(skill_id, {})
    tier = skill.get("type", "basic")
    level = skill.get("level", "?")
    symbol = _TYPE_SYMBOL.get(tier, "○")
    named = _is_named(skill_id, named_by_ref, local_by_ref)
    label = _plain_label(skill_id, skill_map, named_by_ref, local_by_ref, mode, canon=canon, current_user=current_user)
    connector = "└── " if is_last else "├── "
    lines = [_dim(prefix + connector) + _color_entry(symbol, label, tier, named, level, current_user=current_user)]
    seen.add(skill_id)

    child_prefix = prefix + ("    " if is_last else "│   ")
    prereqs = [p for p in skill.get("prerequisites", []) if p in display_ids]
    for i, child_id in enumerate(prereqs):
        child_is_last = i == len(prereqs) - 1
        child_skill = skill_map.get(child_id, {})
        child_tier = child_skill.get("type", "basic")
        child_level = child_skill.get("level", "?")
        child_sym = _TYPE_SYMBOL.get(child_tier, "○")
        child_named = _is_named(child_id, named_by_ref, local_by_ref)
        child_label = _plain_label(child_id, skill_map, named_by_ref, local_by_ref, mode, canon=canon, current_user=current_user)
        if child_id in seen:
            conn2 = "└── " if child_is_last else "├── "
            lines.append(
                _dim(child_prefix + conn2)
                + _color_entry(child_sym, child_label + " ...", child_tier, child_named, child_level, current_user=current_user)
            )
        else:
            lines.extend(
                _render_subtree(
                    child_id, skill_map, display_ids, named_by_ref, local_by_ref,
                    mode, child_prefix, child_is_last, seen, canon=canon, current_user=current_user
                )
            )
    return lines


# ─── public entry point ───────────────────────────────────────────────────────

def show_tree(tree_data, graph_data=None, registry_path=".", mode="default", canon=False):
    if not tree_data:
        print("No skill tree found.")
        return

    unlocked = tree_data.get("unlockedSkills", [])
    username = tree_data.get("userId", "unknown")

    skill_map = {}
    if graph_data:
        skill_map = {s["id"]: s for s in graph_data.get("skills", [])}

    named_by_ref = _load_named_lookup(registry_path)
    local_by_ref = _load_local_lookup(registry_path)

    unlocked_ids = {s["skillId"] for s in unlocked}
    if mode == "named":
        display_ids = {sid for sid in unlocked_ids if _is_named(sid, named_by_ref, local_by_ref)}
    else:
        display_ids = unlocked_ids

    all_prereqs = set()
    for sid in display_ids:
        for p in skill_map.get(sid, {}).get("prerequisites", []):
            if p in display_ids:
                all_prereqs.add(p)

    roots = [s for s in unlocked if s["skillId"] in display_ids and s["skillId"] not in all_prereqs]
    tier_order = {"ultimate": 0, "extra": 1, "basic": 2}
    roots.sort(key=lambda s: (tier_order.get(skill_map.get(s["skillId"], {}).get("type", "basic"), 2), s["skillId"]))

    from gaia_cli.formatting import _fg, _reset, COLOR_CONTRIBUTOR
    # Use a direct ANSI code to ensure color even if _use_color() fails in a subshell/pipe
    username_colored = f"\033[38;2;{COLOR_CONTRIBUTOR[0]};{COLOR_CONTRIBUTOR[1]};{COLOR_CONTRIBUTOR[2]}m{username}\033[0m"
    print(username_colored)
    seen: set[str] = set()
    for i, entry in enumerate(roots):
        sid = entry["skillId"]
        is_last = i == len(roots) - 1
        for line in _render_subtree(sid, skill_map, display_ids, named_by_ref, local_by_ref, mode, "", is_last, seen, canon=canon, current_user=username):
            print(line)


def show_color_check():
    """Self-test: print all tier glyphs and rank chips in their resolved colors.

    Run via ``gaia tree --check``.
    """
    from gaia_cli.cardRenderer import fg, reset, bold, _use_color, TIER_COLORS, RANK_COLORS

    TIER_GLYPHS = {
        "ultimate": "◆",
        "unique":   "◉",
        "extra":    "◇",
        "basic":    "○",
    }
    RANK_LABELS = ["0★", "1★", "2★", "3★", "4★", "5★", "6★"]

    print("─" * 48)
    print("  gaia tree --check  ·  color token self-test")
    print("─" * 48)

    print("\nTier glyphs (via TIER_COLORS from gaia.json):")
    for tier, glyph in TIER_GLYPHS.items():
        color = TIER_COLORS.get(tier, (148, 163, 184))
        print(f"  {fg(*color)}{glyph} {tier.capitalize()}{reset()}")

    print("\nRank chips (via RANK_COLORS from gaia.json):")
    for rank in RANK_LABELS:
        color = RANK_COLORS.get(rank, (148, 163, 184))
        print(f"  {fg(*color)}[{rank}]{reset()}")

    print("\n─" * 24)
    if _use_color():
        print("  Color output: ENABLED (truecolor or 256-color)")
    else:
        print("  Color output: DISABLED (set COLORTERM=truecolor for colors)")
    print("─" * 48)
