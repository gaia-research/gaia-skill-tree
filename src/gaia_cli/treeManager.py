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
            for e in entries:
                if e.get("id"):
                    result[e["id"]] = e
            origin = next((e for e in entries if e.get("origin")), entries[0])
            result[ref] = origin
    return result


_SKILL_MD_CANDIDATES = ("skill.md", "SKILL.md", "README.md", "readme.md")


def _iter_manifest_refs(registry_path):
    """Yield (ref, entry) for each installed skill. Ref can be genericSkillRef or named ID."""
    manifest_path = os.path.join(".gaia", "install-manifest.json")
    if not os.path.exists(manifest_path):
        return
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    for entry in manifest.get("installed", []):
        sid = entry.get("id", "")
        if sid:
            yield sid, entry

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




def _is_named(skill_id, named_by_ref, local_by_ref):
    if "/" in skill_id and not skill_id.startswith("/"):
        return True
    bare = skill_id.lstrip('/')
    return skill_id in named_by_ref or skill_id in local_by_ref or bare in named_by_ref or bare in local_by_ref


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


def _color_entry(symbol, plain_label, tier, is_named, level, current_user=None, is_unowned=False, is_custom=False, is_origin=False, is_fused=False):
    from gaia_cli.cardRenderer import fg, reset, bold, _use_color, TIER_COLORS, RANK_COLORS, COLOR_CONTRIBUTOR, COLOR_LOCAL_USER, COLOR_REDACTED, REDACTED_BLOCK
    
    if not _use_color():
        return f"{symbol} {plain_label}"
        
    if is_unowned:
        rc = RANK_COLORS.get(level, RANK_COLORS.get("0★", (148, 163, 184)))
        return f"{fg(*rc)}{symbol} {plain_label}{reset()}"

    rc = RANK_COLORS.get(level, RANK_COLORS.get("0★", (148, 163, 184)))

    is_named_display = (is_origin or is_named) and not plain_label.startswith('/')

    # Priority 1 & 2: ORIGIN & Named
    if is_named_display:
        if level in _TRANSCENDENT_LEVELS:
            colored = _gradient_text(f"{symbol} {plain_label}", _GRAD_GOLD, _GRAD_RED)
            return f"{bold()}{colored}{reset()}"
        
        if "/" in plain_label and not plain_label.startswith("/"):
            parts = plain_label.split("/", 1)
            handle = parts[0]
            rest = parts[1]
            
            handle_color = COLOR_CONTRIBUTOR
            
            # Split off the star if present
            star_part = ""
            nickname = rest
            if " " in nickname:
                nickname, star_part = nickname.rsplit(" ", 1)
            
            return f"{fg(*handle_color)}{symbol} {handle}{reset()}/{fg(*rc)}{nickname}{reset()}{f' {fg(*rc)}{star_part}{reset()}' if star_part else ''}"
        
        return f"{bold()}{fg(*COLOR_CONTRIBUTOR)}{symbol} {plain_label}{reset()}"

    # Priority 3: Starless Generic
    if not is_fused and not is_custom and not is_named_display:
        if level == "0★" or level == "?":
            slate_blue = (148, 163, 184)
            return f"{fg(*slate_blue)}{symbol} {plain_label}{reset()}"

    # Priority 4: Fused custom
    if is_fused:
        fuse_purple = TIER_COLORS.get("extra", (192, 132, 252))
        return f"{fg(*fuse_purple)}{symbol} {plain_label}{reset()}"

    # Priority 5: Custom
    if is_custom:
        return f"{fg(*COLOR_LOCAL_USER)}{symbol} {plain_label}{reset()}"

    return f"{fg(*rc)}{symbol} {plain_label}{reset()}"


def _render_legend():
    from gaia_cli.cardRenderer import fg, reset, bold, COLOR_CONTRIBUTOR, COLOR_LOCAL_USER, RANK_COLORS, _use_color
    if not _use_color():
        return

    slate_blue = (148, 163, 184)
    
    print("  " + f"{fg(*slate_blue)}○ starless{reset()}  " +
          f"{bold()}{fg(*COLOR_CONTRIBUTOR)}○ named{reset()}  " +
          f"{fg(*COLOR_LOCAL_USER)}○ custom{reset()}")
    
    ranks = []
    for r in ["1★", "2★", "3★", "4★", "5★", "6★"]:
        color = RANK_COLORS.get(r, slate_blue)
        ranks.append(f"{fg(*color)}[{r}]{reset()}")
    print("  " + " ".join(ranks))
    print()


def _dim(text):
    from gaia_cli.cardRenderer import _use_color
    return f"\033[2m{text}\033[22m" if _use_color() else text


# ─── label helpers ────────────────────────────────────────────────────────────

_TYPE_SYMBOL = {"basic": "○", "extra": "◇", "ultimate": "◆"}


def _plain_label(skill_id, skill_map, named_by_ref, local_by_ref, mode, canon=False, current_user=None):
    level = skill_map.get(skill_id, {}).get("level", "?")
    star = f" {level}" if level and level != "0★" else ""
    bare_skill = skill_id.lstrip('/')

    if canon:
        return f"/{bare_skill}{star}"
    
    if mode == "title":
        name = skill_map.get(skill_id, {}).get("name", bare_skill)
        return f"{name}{star}"
    
    local = local_by_ref.get(skill_id) or local_by_ref.get(skill_id.lstrip('/'))
    named = named_by_ref.get(skill_id) or named_by_ref.get(skill_id.lstrip('/'))
    
    specific = local or named
    if specific:
        level = specific.get("level", level)
        star = f" {level}" if level and level != "0★" else ""
        full_id = specific.get("id")
        if full_id:
            if not full_id.startswith("/"):
                return f"{full_id}{star}"
            return f"{full_id}{star}"

    if "/" in bare_skill:
        return f"{bare_skill}{star}"
    return f"/{bare_skill}{star}"


# ─── recursive renderer ───────────────────────────────────────────────────────

def _render_subtree(skill_id, skill_map, display_ids, named_by_ref, local_by_ref, mode, prefix, is_last, seen, unlocked_ids, custom_nodes, canon=False, current_user=None, fusion_nodes=None, origin_ids=None):
    if fusion_nodes is None:
        fusion_nodes = set()
    if origin_ids is None:
        origin_ids = set()

    skill = skill_map.get(skill_id, {})
    tier = skill.get("type", "basic")
    level = skill.get("level", "?")
    named = _is_named(skill_id, named_by_ref, local_by_ref)
    
    specific = local_by_ref.get(skill_id) or local_by_ref.get(skill_id.lstrip('/')) or named_by_ref.get(skill_id) or named_by_ref.get(skill_id.lstrip('/'))
    if specific:
        level = specific.get("level", level)
        if specific.get("tier"):
            tier = specific.get("tier")

    symbol = _TYPE_SYMBOL.get(tier, "○")
    
    is_unowned = skill_id not in unlocked_ids and skill_id not in custom_nodes
    is_custom = skill_id in custom_nodes or skill_id.lstrip('/') in custom_nodes
    is_fused = skill_id in fusion_nodes or skill_id.lstrip('/') in fusion_nodes
    
    is_orig = (skill_id in origin_ids) or (skill_id.lstrip('/') in origin_ids)
    if not is_orig:
        if isinstance(specific, dict):
            if specific.get("role") == "origin" or specific.get("origin") is True:
                is_orig = True

    if is_unowned:
        label = "/???"
    else:
        label = _plain_label(skill_id, skill_map, named_by_ref, local_by_ref, mode, canon=canon, current_user=current_user)
        if skill_id in seen:
            label += " (see above)"
        
    connector = "└── " if is_last else "├── "
    lines = [_dim(prefix + connector) + _color_entry(symbol, label, tier, named, level, current_user=current_user, is_unowned=is_unowned, is_custom=is_custom, is_origin=is_orig, is_fused=is_fused)]
    
    if skill_id in seen:
        return lines

    seen.add(skill_id)

    child_prefix = prefix + ("    " if is_last else "│   ")
    prereqs = skill.get("prerequisites", [])
    if mode == "named":
        prereqs = [p for p in prereqs if p in display_ids]
    
    owned_prereqs = []
    unowned_prereqs = []
    for p in prereqs:
        if p in unlocked_ids or p in custom_nodes:
            owned_prereqs.append(p)
        else:
            unowned_prereqs.append(p)
            
    def sort_key(cid):
        tier = skill_map.get(cid, {}).get("type", "basic")
        tier_order = {"ultimate": 0, "extra": 1, "basic": 2}
        return (1 if (cid in custom_nodes or cid.lstrip('/') in custom_nodes) else 0, tier_order.get(tier, 3), cid)

    owned_prereqs.sort(key=sort_key)
    unowned_prereqs.sort(key=sort_key)

    children_to_render = []
    children_to_render.extend(owned_prereqs)
    
    grouped_unowned_count = 0
    if len(unowned_prereqs) > 5:
        children_to_render.extend(unowned_prereqs[:5])
        grouped_unowned_count = len(unowned_prereqs) - 5
    else:
        children_to_render.extend(unowned_prereqs)
        
    total_children = len(children_to_render) + (1 if grouped_unowned_count > 0 else 0)
    
    for i, child_id in enumerate(children_to_render):
        child_is_last = (i == total_children - 1) and (grouped_unowned_count == 0)
        lines.extend(
            _render_subtree(
                child_id, skill_map, display_ids, named_by_ref, local_by_ref,
                mode, child_prefix, child_is_last, seen, unlocked_ids, custom_nodes, canon=canon, current_user=current_user,
                fusion_nodes=fusion_nodes, origin_ids=origin_ids
            )
        )
        
    if grouped_unowned_count > 0:
        conn2 = "└── "
        lines.append(
            _dim(child_prefix + conn2) + _dim(f"○ /??? (+{grouped_unowned_count} skills)")
        )

    return lines


# ─── public entry point ───────────────────────────────────────────────────────

def show_tree(tree_data, graph_data=None, registry_path=".", mode="default", canon=False, custom=False):
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
    custom_nodes = set()
    custom_skills = []
    fusions = {}
    scanned_nodes = set()
    
    custom_state_path = os.path.join(".gaia", "custom_state.json")
    if os.path.exists(custom_state_path):
        try:
            with open(custom_state_path, "r", encoding="utf-8") as f:
                cstate = json.load(f)
                custom_skills = cstate.get("customSkills", [])
                fusions = cstate.get("customFusions", {})
                for target, data in fusions.items():
                    if isinstance(data, dict):
                        sources = data.get("sources", [])
                        level = data.get("level", "1★")
                        stype = data.get("type", "extra")
                    else:
                        sources = data
                        level = "1★"
                        stype = "extra"
                    
                    skill_map[target] = {
                        "id": target,
                        "name": target,
                        "description": "Custom Fusion",
                        "type": stype,
                        "level": level,
                        "prerequisites": sources,
                    }
                    scanned_nodes.add(target)
                    if target not in unlocked_ids:
                        unlocked.append({"skillId": target})
                        unlocked_ids.add(target)
        except Exception:
            pass

    if custom:
        if not os.path.exists(custom_state_path):
            from gaia_cli.scanner import scan_skill_mds
            local_skills = scan_skill_mds(global_search=False)
            custom_skills = [{
                "id": sk["id"],
                "name": sk.get("name", sk["id"]),
                "description": sk.get("description", ""),
                "mapped_to": sk["id"],
                "prerequisites": sk.get("prerequisites", [])
            } for sk in local_skills]

        for csk in custom_skills:
            cid = csk["id"]
            m_type = csk.get("match_type")
            mapped_to = csk.get("mapped_to")
            
            node_id = mapped_to if mapped_to else cid
            
            if node_id not in skill_map:
                skill_map[node_id] = {
                    "id": node_id,
                    "name": csk.get("name", node_id),
                    "description": csk.get("description", ""),
                    "prerequisites": csk.get("prerequisites", []),
                    "level": csk.get("canon_level", csk.get("level", "?")),
                    "type": "custom" if m_type not in ("origin", "named", "generic", "exact_generic") else "basic"
                }
            else:
                target = skill_map[node_id]
                target["name"] = csk.get("name", target.get("name", ""))
                target["level"] = csk.get("canon_level", target.get("level", "?"))
                target["prerequisites"] = list(set(target.get("prerequisites", []) + csk.get("prerequisites", [])))
                
            skill_map[cid] = skill_map[node_id]
            
            scanned_nodes.add(node_id)
            
            if m_type in ("generic", "exact_generic") and mapped_to:
                local_by_ref[node_id] = {"id": cid}
                
            if m_type not in ("origin", "named", "generic", "exact_generic"):
                custom_nodes.add(node_id)
                
        for fname in fusions.keys():
            if fname in custom_nodes:
                custom_nodes.remove(fname)
        
        display_ids = set()
        queue = list(scanned_nodes)
        visited = set()
        while queue:
            curr = queue.pop(0)
            if curr in visited:
                continue
            visited.add(curr)
            display_ids.add(curr)
            for prereq in skill_map.get(curr, {}).get("prerequisites", []):
                queue.append(prereq)
                
        display_ids = {sid for sid in display_ids if sid in unlocked_ids or sid in scanned_nodes}
        # Inject all locally scanned skills into unlocked so they can act as roots if they have no prereqs
        for cid in scanned_nodes:
            if cid not in unlocked_ids:
                unlocked.append({"skillId": cid})
                unlocked_ids.add(cid)
    elif mode == "named":
        display_ids = {sid for sid in unlocked_ids if _is_named(sid, named_by_ref, local_by_ref)}
    else:
        display_ids = unlocked_ids

    # Allow roots to not be strictly filtered by `display_ids` if we are showing full prereqs
    # We still need to find roots based on unlocked skills.
    all_prereqs = set()
    for sid in display_ids:
        for p in skill_map.get(sid, {}).get("prerequisites", []):
            all_prereqs.add(p)

    roots = [s for s in unlocked if s["skillId"] in display_ids and s["skillId"] not in all_prereqs]
    tier_order = {"ultimate": 0, "extra": 1, "basic": 2}
    roots.sort(key=lambda s: (1 if (s["skillId"] in custom_nodes or s["skillId"].lstrip('/') in custom_nodes) else 0, tier_order.get(skill_map.get(s["skillId"], {}).get("type", "basic"), 2), s["skillId"]))

    # Populate fusion_nodes and origin_ids
    fusion_nodes = {f for f in fusions.keys()} | {f.lstrip('/') for f in fusions.keys()}
    origin_ids = set()
    for entry in named_by_ref.values():
        if isinstance(entry, dict) and entry.get("id"):
            origin_ids.add(entry["id"])
            origin_ids.add(entry["id"].lstrip('/'))
    for csk in custom_skills:
        if csk.get("match_type") == "origin":
            origin_ids.add(csk["id"])
            origin_ids.add(csk["id"].lstrip('/'))
            if csk.get("mapped_to"):
                origin_ids.add(csk["mapped_to"])
                origin_ids.add(csk["mapped_to"].lstrip('/'))

    from gaia_cli.formatting import _fg, _reset, COLOR_CONTRIBUTOR
    # Use a direct ANSI code to ensure color even if _use_color() fails in a subshell/pipe
    username_colored = f"\033[38;2;{COLOR_CONTRIBUTOR[0]};{COLOR_CONTRIBUTOR[1]};{COLOR_CONTRIBUTOR[2]}m{username}\033[0m"
    print(username_colored)
    seen: set[str] = set()
    for i, entry in enumerate(roots):
        sid = entry["skillId"]
        is_last = i == len(roots) - 1
        for line in _render_subtree(sid, skill_map, display_ids, named_by_ref, local_by_ref, mode, "", is_last, seen, unlocked_ids, custom_nodes, canon=canon, current_user=username, fusion_nodes=fusion_nodes, origin_ids=origin_ids):
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
