import json
import os
import datetime
import sys
import importlib.util

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from gaia_cli.leveling import effective_level
from gaia_cli.redaction import REDACTED_BLOCK, is_redacted  # single source of truth

# Phase 8d — pull in the markdown linked-handle helper so every named
# skill identifier (contributor/skill) emits a hover-underlined link to
# the contributor's profile page (docs/u/<handle>/).
_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)
from _atlas_helpers import markdown_handle_link  # noqa: E402
from _tree_renderer import render_tree  # noqa: E402
from build_layouts_3d import generate_layouts # noqa: E402


def _run_generate_named_index():
    """Invoke generateNamedIndex as a module to produce registry/named-skills.json."""
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    module_path = os.path.join(scripts_dir, "generateNamedIndex.py")
    if not os.path.isfile(module_path):
        print("Warning: generateNamedIndex.py not found — skipping named index.")
        return
    spec = importlib.util.spec_from_file_location("generateNamedIndex", module_path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
        repo_root = os.path.dirname(scripts_dir)
        named_dir = os.path.join(repo_root, "registry", "named")
        graph_path = os.path.join(repo_root, "registry", "gaia.json")
        output_path = os.path.join(repo_root, "registry", "named-skills.json")
        if os.path.isdir(named_dir) and os.path.isfile(graph_path):
            with open(graph_path, "r", encoding="utf-8") as gf:
                gdata = json.load(gf)
            ts = gdata.get("generatedAt", "")
            today = (ts.split("T")[0] if "T" in ts else ts) if ts else datetime.date.today().isoformat()
            named_skills = mod.load_named_skills(named_dir)
            errors, buckets, awaiting_classification, by_contributor = mod.validate_and_group(named_skills, gdata)
            if errors:
                print(f"Warning: named skill validation errors ({len(errors)}):")
                for err in errors:
                    print(f"  {err}")
            else:
                mod.write_index(buckets, awaiting_classification, by_contributor, output_path, today)
                total = sum(len(v) for v in buckets.values())
                print(f"Generated named index: {total} skill(s) across "
                      f"{len(buckets)} bucket(s).")
    except Exception as exc:
        print(f"Warning: could not generate named index — {exc}")


try:
    from generateRealSkills import generate_catalog_pages
except ModuleNotFoundError:
    from scripts.generateRealSkills import generate_catalog_pages


def get_type_label(meta, skill_type):
    return meta.get("typeLabels", {}).get(skill_type, skill_type.capitalize())


def get_level_label(meta, level):
    return str(level)


def get_effective_level_label(meta, skill):
    claimed = str(skill.get("level", ""))
    effective = effective_level(skill)
    if effective == claimed:
        return claimed
    return f"{claimed} → {effective}"


def get_demerit_suffix(skill):
    demerits = list(skill.get("demerits", []) or [])
    if not demerits:
        return ""
    return f"  (demerits: {', '.join(demerits)})"


def get_tier_label(meta, level):
    return meta.get("levelLabels", {}).get(str(level), str(level))


def get_tier_symbol(skill_type):
    return {"basic": "○", "extra": "◇", "unique": "◉", "ultimate": "◆"}.get(skill_type, "·")


def _link_named_id(named_id, handle_rel=None):
    """Wrap the contributor segment of ``handle/skill`` in a markdown link.

    For ``karpathy/autoresearch`` and ``handle_rel='u/'`` returns
    ``[karpathy](u/karpathy/)/autoresearch``. If ``handle_rel`` is None
    the original string is returned unchanged (preserves the old plain
    behaviour for callers that don't opt in).
    """
    if not named_id or handle_rel is None or "/" not in named_id:
        return named_id
    handle, _, tail = named_id.partition("/")
    if not handle or not tail:
        return named_id
    return f"{markdown_handle_link(handle, rel=handle_rel, with_at=False)}/{tail}"


def _build_skill_display(skill_id, skill_type, named_map=None, handle_rel=None,
                         named_level_map=None, named_entry_level=None):
    """Return canonical display string for a skill (no tier prefix).

    All rows:  glyph already encodes tier; the section header labels the group.
    Ultimate (unclaimed) → /slug [N★ · Unclaimed]

    Phase 8d — when ``handle_rel`` is set (e.g. ``'u/'`` for
    ``docs/tree.md`` or ``'../docs/u/'`` for registry markdown), the
    contributor segment of any claimed named id is wrapped in a
    markdown link to the contributor's profile page. Pass ``None``
    (the default) to keep the original plain-text behaviour.

    When ``named_level_map`` is provided, redacts handles for pre-named (≤1★) skills.
    Monospace contexts (markdown) use redaction blocks (████████).
    """
    named_id = (named_map or {}).get(skill_id)

    # Redact based on the RESOLVED named entry's OWN level — not the bucket's
    # effective (top) star. A 1★ entry that happens to sit in a bucket with a
    # 2★+ sibling must still be redacted (and should never have been chosen as
    # the representative; see generateNamedIndex champion ordering). Monospace
    # markdown uses the shared block bar; suppress the profile link too.
    if named_id and named_entry_level is not None:
        if is_redacted(named_entry_level.get(named_id)):
            _, _, tail = named_id.partition("/")
            named_id = f"{REDACTED_BLOCK}/{tail}" if tail else named_id
            handle_rel = None  # no profile link for anonymous contributor

    named_id_display = _link_named_id(named_id, handle_rel)
    if skill_type == "ultimate":
        if named_id:
            return named_id_display
        return f"/{skill_id}"
    if skill_type == "unique":
        return named_id_display if named_id else f"/{skill_id}"
    if skill_type == "extra":
        return named_id_display if named_id else f"/{skill_id}"
    return named_id_display if named_id else f"/{skill_id}"

def _sorted_ultimates(skills):
    # Generic refs are rank-less; order ultimates by name.
    return sorted(
        [s for s in skills if s.get("type") == "ultimate"],
        key=lambda s: s.get("name", "")
    )


def build_named_level_map(named_index):
    """Map generic skill id -> top (max) named-variant star across its bucket."""
    order = ["2★", "3★", "4★", "5★", "6★"]
    out = {}
    for ref, entries in (named_index.get("buckets", {}) or {}).items():
        levels = [e.get("level") for e in entries if e.get("level") in order]
        if levels:
            out[ref] = max(levels, key=lambda lv: order.index(lv))
    return out


def _render_subtree(root_id, skill_map, meta, prefix, is_last, seen,
                    unlocked_ids=None, user_id=None, named_map=None,
                    named_level_map=None, handle_rel=None, named_entry_level=None):
    skill = skill_map.get(root_id)
    if not skill:
        return []

    connector = "└─" if is_last else "├─"
    symbol = get_tier_symbol(skill.get("type"))

    skill_type = skill.get("type", "basic")
    display = _build_skill_display(root_id, skill_type, named_map, handle_rel,
                                   named_level_map=named_level_map,
                                   named_entry_level=named_entry_level)

    # Generic refs are rank-less — show the top named-variant star, if any.
    star = (named_level_map or {}).get(root_id)
    star_pill = f"  [{star}]" if star else ""

    already_seen = root_id in seen
    back_ref = "  (↑ see above)" if already_seen else ""

    check = ""
    if unlocked_ids is not None:
        check = "✓ " if root_id in unlocked_ids else "· "

    line = f"{prefix}{connector} {check}{symbol} {display}{star_pill}{back_ref}"
    lines = [line]

    if already_seen:
        return lines

    seen.add(root_id)

    if not skill.get("prerequisites"):
        return lines
    child_prefix = prefix + ("   " if is_last else "│  ")
    prereq_ids = skill.get("prerequisites", [])
    for i, prereq_id in enumerate(prereq_ids):
        is_last_child = (i == len(prereq_ids) - 1)
        lines.extend(_render_subtree(
            prereq_id, skill_map, meta, child_prefix, is_last_child, seen,
            unlocked_ids=unlocked_ids, user_id=user_id, named_map=named_map,
            named_level_map=named_level_map, handle_rel=handle_rel,
            named_entry_level=named_entry_level,
        ))

    return lines


def main():
    with open("registry/gaia.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # 4D Hyper-Atlas Integration: Generate layout data.
    # Per-skill cluster/positions are schema-addition-properties and must NOT
    # be written into registry/gaia.json (additionalProperties:false on Skill).
    # They are saved to generated-output/layouts.json and merged into
    # docs/graph/gaia.json by syncDocsGraphAssets.py at sync time.
    layout_data = generate_layouts()
    if layout_data:
        data["meta"]["clusterNames"] = layout_data.get("clusterNames", {})
        data["meta"]["centroids"] = layout_data.get("centroids", [])
        # Save registry/gaia.json with only meta additions — no per-skill fields
        with open("registry/gaia.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        # Write per-skill layout nodes to a generated artifact for the sync step
        generated_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "generated-output")
        os.makedirs(generated_dir, exist_ok=True)
        layouts_out = os.path.join(generated_dir, "layouts.json")
        with open(layouts_out, "w", encoding="utf-8") as f:
            json.dump(layout_data["nodes"], f, indent=2, ensure_ascii=False)
            f.write("\n")
        print("Saved 4D Hyper-Atlas layout nodes to generated-output/layouts.json")

    version = data.get("version", "0.1.0")
    timestamp = data.get("generatedAt", datetime.datetime.now().isoformat() + "Z")
    meta = data.get("meta", {})
    skills = data.get("skills", [])

    skills.sort(key=lambda x: x["id"])

    # Build named_map early so skill pages and registry can use it
    _run_generate_named_index()
    named_map = {}
    named_level_map = {}
    named_entry_level = {}  # named_id ("handle/slug") -> its OWN level string
    named_index_path = os.path.join("registry", "named-skills.json")
    if os.path.isfile(named_index_path):
        with open(named_index_path, "r", encoding="utf-8") as nf:
            nidx = json.load(nf)
        for _sid, entries in nidx.get("buckets", {}).items():
            if entries:
                # Buckets are champion-first (generateNamedIndex sort); prefer a
                # named origin, else the top-ranked entry. The representative may
                # still be ≤1★ if the whole bucket is pre-named — redaction keys
                # on the entry's own level, so that case is handled downstream.
                origin = next((e for e in entries if e.get("origin")), entries[0])
                named_map[_sid] = origin.get("id", "")
                for e in entries:
                    if e.get("id"):
                        named_entry_level[e["id"]] = e.get("level")
        named_level_map = build_named_level_map(nidx)

    os.makedirs("registry/skills/basic", exist_ok=True)
    os.makedirs("registry/skills/extra", exist_ok=True)
    os.makedirs("registry/skills/unique", exist_ok=True)
    os.makedirs("registry/skills/ultimate", exist_ok=True)

    skill_map = {s["id"]: s for s in skills}
    date_str = timestamp.split("T")[0] if "T" in timestamp else timestamp

    # Named-skill buckets for per-page "Named implementations" tables.
    named_buckets = nidx.get("buckets", {}) if os.path.isfile(named_index_path) else {}

    for skill in skills:
        skill_type = skill.get("type", "basic")
        skill_id = skill.get("id")
        skill_name = skill.get("name")
        file_path = f"registry/skills/{skill_type}/{skill_id}.md"

        type_label = get_type_label(meta, skill_type)
        top_star = named_level_map.get(skill_id)
        variants = named_buckets.get(skill_id, [])

        with open(file_path, "w", encoding="utf-8") as f:
            # Phase 8d — registry/skills/<type>/<id>.md sits three levels
            # deep under repo root. The contributor profile pages live at
            # docs/u/<handle>/, so the link from here is
            # ../../../docs/u/<handle>/.
            page_display = _build_skill_display(
                skill_id, skill_type, named_map,
                handle_rel="../../../docs/u/",
                named_level_map=named_level_map,
                named_entry_level=named_entry_level,
            )
            star_suffix = f"  [{top_star}]" if top_star else ""
            f.write(f"# {page_display}{star_suffix}\n")
            f.write(f"**ID:** {skill_id}  \n")
            f.write(f"**Type:** {type_label or 'Basic Skill'}  \n")
            f.write("**Rank:** _rank-less generic reference — stars are earned by named implementations_  \n")
            if top_star:
                f.write(f"**Top named variant:** {top_star}  \n")
            f.write(f"**Skill Call:** `/{skill_id}`\n\n")
            f.write("---\n\n")

            if "summary" in skill:
                f.write(f"**Summary:** {skill.get('summary')}\n\n")

            f.write("## Description\n")
            f.write(f"{skill.get('description', '')}\n\n")

            if "useCase" in skill:
                f.write("## Use Case\n")
                f.write(f"{skill.get('useCase', '')}\n\n")

            if "directives" in skill:
                f.write("## Directives\n")
                f.write(f"{skill.get('directives', '')}\n\n")

            f.write("## Prerequisites\n")
            prereqs = skill.get("prerequisites", [])
            if not prereqs:
                f.write("_None._\n\n")
            else:
                for prereq_id in prereqs:
                    prereq = skill_map.get(prereq_id)
                    if prereq:
                        prereq_type = prereq.get("type", "basic")
                        f.write(f"- [{prereq.get('name')}](../{prereq_type}/{prereq_id}.md)\n")
                    else:
                        f.write(f"- {prereq_id}\n")
                f.write("\n")

            f.write("## Unlocks\n")
            unlocks = skill.get("derivatives", [])
            if not unlocks:
                f.write("_None._\n\n")
            else:
                for unlock_id in unlocks:
                    unlock = skill_map.get(unlock_id)
                    if unlock:
                        unlock_type = unlock.get("type", "basic")
                        f.write(f"- [{unlock.get('name')}](../{unlock_type}/{unlock_id}.md)\n")
                    else:
                        f.write(f"- {unlock_id}\n")
                f.write("\n")

            if skill_type in ["extra", "ultimate"]:
                f.write("## Fusion Condition\n")
                conditions = skill.get("conditions", "")
                if not conditions:
                    f.write("_None specified._\n\n")
                else:
                    f.write(f"{conditions}\n\n")

            f.write("## Named Implementations\n")
            if not variants:
                f.write("_None yet — be the first to claim this skill._\n\n")
            else:
                f.write("| Named Skill | Contributor | Stars | Evidence |\n")
                f.write("|---|---|---|---|\n")
                for v in sorted(variants, key=lambda e: (not e.get("origin"), e.get("id", ""))):
                    ev_count = len(v.get("evidence", []) or [])
                    origin_mark = " ⭑" if v.get("origin") else ""
                    f.write(
                        f"| {v.get('id', '')}{origin_mark} | {v.get('contributor', '')} | "
                        f"{v.get('level', '')} | {ev_count} |\n"
                    )
                f.write("\n")

            f.write("## Evidence (inherited capability)\n")
            f.write("_Capability-level evidence for this generic reference. "
                    "Every named implementation above inherits it._\n\n")
            evidence = skill.get("evidence", [])
            if not evidence:
                f.write("_None._\n\n")
            else:
                f.write("| Class | Source | Evaluator | Date |\n")
                f.write("|---|---|---|---|\n")
                for ev in evidence:
                    f.write(f"| {ev.get('class', '')} | {ev.get('source', '')} | {ev.get('evaluator', '')} | {ev.get('date', '')} |\n")
                f.write("\n")

            f.write("## Known Agents\n")
            agents = skill.get("knownAgents", [])
            if not agents:
                f.write("_None verified yet._\n\n")
            else:
                for agent in agents:
                    f.write(f"- {agent}\n")
                f.write("\n")

            f.write("---\n")
            # f.write(f"*Generated from gaia.json v{version} on {date_str}. Do not edit directly.*\n")

    def _top_star(sid):
        """Top named-variant star for a generic id, or em-dash when unclaimed."""
        return named_level_map.get(sid, "—")

    # generate registry.md
    with open("registry/registry.md", "w", encoding="utf-8") as f:
        f.write("# Gaia Skill Registry\n\n")
        f.write("*Generic references are rank-less taxonomy. The Top ★ column shows the "
                "highest star among their named implementations (— = none yet).*\n\n")
        f.write("| Name | Class | Top ★ | Skill Call |\n")
        f.write("|---|---|---|---|\n")

        # collect orphaned basic IDs for the pure section
        all_prereq_ids = set()
        for skill in skills:
            for pid in skill.get("prerequisites", []):
                all_prereq_ids.add(pid)
        orphan_ids = {
            s["id"] for s in skills
            if s.get("type") == "basic"
            and s["id"] not in all_prereq_ids
            and not s.get("prerequisites")
        }

        # Phase 8d — registry/registry.md sits at registry/ which is one
        # level under repo root; profile pages are at docs/u/<handle>/.
        _REG_HANDLE_REL = "../docs/u/"
        for skill in skills:
            if skill["id"] in orphan_ids:
                continue
            skill_type = skill.get("type", "basic")
            symbol = get_tier_symbol(skill_type)
            type_label = get_type_label(meta, skill_type)
            reg_display = _build_skill_display(skill.get('id'), skill_type, named_map, _REG_HANDLE_REL,
                                               named_level_map=named_level_map,
                                               named_entry_level=named_entry_level)
            name_display = f"{symbol} {reg_display}"
            skill_call = f"`/{skill.get('id')}`"
            f.write(f"| {name_display} | {type_label or 'Basic Skill'} | {_top_star(skill['id'])} | {skill_call} |\n")

        f.write("\n")

        # Unique Skills section
        unique_skills = [s for s in skills if s.get("type") == "unique"]
        if unique_skills:
            f.write("## Uniques\n\n")
            f.write("*Singular mastery skills — graph-isolated, with named implementations. Promoted via `/gaia promote --unique`.*\n\n")
            f.write("| Name | Class | Top ★ | Skill Call |\n")
            f.write("|---|---|---|---|\n")
            for skill in unique_skills:
                reg_display = _build_skill_display(skill.get('id'), "unique", named_map, _REG_HANDLE_REL,
                                                   named_level_map=named_level_map,
                                               named_entry_level=named_entry_level)
                name_display = f"◉ {reg_display}"
                skill_call = f"`/{skill.get('id')}`"
                f.write(f"| {name_display} | Unique Skill | {_top_star(skill['id'])} | {skill_call} |\n")
            f.write("\n")

        f.write("## Basics\n\n")
        f.write("*Basic-tier skills with no connections to the upgrade graph — no prerequisites and not referenced as a component of any other skill.*\n\n")
        f.write("| Name | Class | Top ★ | Skill Call |\n")
        f.write("|---|---|---|---|\n")
        for skill in skills:
            if skill["id"] not in orphan_ids:
                continue
            if skill.get("type") == "unique":
                continue
            name_display = f"○ {skill.get('name')}"
            skill_call = f"`/{skill.get('id')}`"
            f.write(f"| {name_display} | Intrinsic Skill | {_top_star(skill['id'])} | {skill_call} |\n")

        f.write("\n")

        # Unclaimed Ultimates section
        unclaimed = [s for s in skills if s.get("type") == "ultimate" and s["id"] not in named_map]
        if unclaimed:
            f.write("## Ultimate Skills Awaiting Name\n\n")
            f.write(
                "*These Ultimate skills have no named implementation yet. "
                "The first contributor to submit a valid named implementation "
                "claims the title slot.  Submit with `gaia propose /<skill_id> --ultimate` and open a PR.*\n\n"
            )
            f.write("| Skill Call | Prerequisites |\n")
            f.write("|---|---|\n")
            for s in unclaimed:
                prereq_names = ", ".join(f"`/{p}`" for p in s.get("prerequisites", []))
                f.write(f"| `/{s['id']}` | {prereq_names} |\n")
            f.write("\n")

        # f.write(f"*Generated from gaia.json v{version}.*\n")

    # generate combinations.md
    with open("registry/combinations.md", "w", encoding="utf-8") as f:
        f.write("# Combinations\n\n")
        f.write("| Skill | Class | Prerequisites | Top ★ | Conditions |\n")
        f.write("|---|---|---|---|---|\n")
        # Phase 8d — same relative-path convention as registry.md.
        _COMBO_HANDLE_REL = "../docs/u/"
        for skill in skills:
            if skill.get("type") in ["extra", "ultimate"]:
                skill_type = skill.get("type")
                symbol = get_tier_symbol(skill_type)
                type_label = get_type_label(meta, skill_type)
                prereqs = [skill_map.get(pid, {}).get("name", pid) for pid in skill.get("prerequisites", [])]
                prereq_str = ", ".join(prereqs)
                combo_display = _build_skill_display(skill.get('id'), skill_type, named_map, _COMBO_HANDLE_REL,
                                                     named_level_map=named_level_map,
                                               named_entry_level=named_entry_level)
                name_display = f"{symbol} {combo_display}"
                f.write(f"| {name_display} | {type_label} | {prereq_str} | {_top_star(skill['id'])} | {skill.get('conditions', '')} |\n")
        # f.write(f"\n*Generated from gaia.json v{version}.*\n")

    # generate tree.md
    _generate_tree(skills, skill_map, meta, version, date_str, named_map, named_level_map,
                   named_entry_level=named_entry_level)

    catalog_path = 'registry/real-skills.json'
    if os.path.isfile(catalog_path):
        with open(catalog_path, 'r', encoding='utf-8') as cf:
            generate_catalog_pages(json.load(cf))

    # generate user skill tree markdown projections
    users_dir = "skill-trees"
    legendaries = _sorted_ultimates(skills)
    if os.path.isdir(users_dir):
        for username in sorted(os.listdir(users_dir)):
            user_dir = os.path.join(users_dir, username)
            tree_path = os.path.join(user_dir, "skill-tree.json")
            if not os.path.isfile(tree_path):
                continue
            with open(tree_path, "r", encoding="utf-8") as tf:
                tree = json.load(tf)

            md_path = os.path.join(user_dir, "skill-tree.md")
            with open(md_path, "w", encoding="utf-8") as f:
                user_id = tree.get("userId", username)
                stats = tree.get("stats", {})
                highest_level = stats.get("highestLevel", "")
                _raw_highest = get_tier_label(meta, highest_level) if highest_level else ""
                # Only use the label if it came from levelLabels; otherwise emit em dash
                highest_label = _raw_highest if (highest_level and highest_level in (meta.get("levelLabels") or {})) else "—"
                f.write(f"# Skill Tree — {user_id}\n")
                f.write(f"**Last Updated:** {tree.get('updatedAt', 'unknown')}\n")
                f.write(f"**Total Skills Unlocked:** {stats.get('totalUnlocked', 0)}\n")
                f.write(f"**Highest Tier:** {highest_label}\n")
                f.write(f"**Deepest Lineage:** {stats.get('deepestLineage', 0)}\n\n")
                f.write("---\n\n")

                f.write("## Unlocked Skills\n\n")
                unlocked = tree.get("unlockedSkills", [])
                if unlocked:
                    f.write("| Skill | Type | Rank | Tier name | Source | Date |\n")
                    f.write("|---|---|---|---|---|---|\n")
                    for us in unlocked:
                        sid = us.get("skillId", "")
                        sk = skill_map.get(sid, {})
                        sk_type = sk.get("type", "basic")
                        symbol = get_tier_symbol(sk_type)
                        type_label = get_type_label(meta, sk_type)
                        level = us.get("level") or named_level_map.get(sid, "")
                        level_label = get_level_label(meta, level)
                        tier_label = get_tier_label(meta, level)
                        name_display = f"{symbol} {sk.get('name', sid)}"
                        f.write(f"| {name_display} | {type_label} | "
                                f"{level_label} | {tier_label} | "
                                f"{us.get('unlockedIn', '')} | {us.get('unlockedAt', '')} |\n")
                else:
                    f.write("_No skills unlocked yet._\n")
                f.write("\n---\n\n")

                # Upgrade path tree — routed through shared render_tree contract
                unlocked_ids = {us.get("skillId") for us in unlocked}
                f.write("## Upgrade Path\n\n")
                f.write("```\n")
                tree_body = render_tree(
                    skills,
                    mode="user",
                    owned_ids=unlocked_ids,
                    named_map=named_map,
                    named_level_map=named_level_map,
                    named_entry_level=named_entry_level,
                    meta=meta,
                    version=version,
                    date_str=date_str,
                    user_id=user_id,
                    skill_map=skill_map,
                    build_skill_display=_build_skill_display,
                    render_subtree=_render_subtree,
                    sorted_ultimates=_sorted_ultimates,
                )
                f.write(tree_body)
                f.write("```\n\n")

                f.write("## Pending Combinations\n\n")
                pending = tree.get("pendingCombinations", [])
                if pending:
                    for pc in pending:
                        candidate = pc.get("candidateResult", "")
                        prereqs_list = ", ".join(f"`{s}`" for s in pc.get("detectedSkills", []))
                        level_floor = get_level_label(meta, pc.get("levelFloor", ""))
                        f.write(f"> **{candidate}** — combine {prereqs_list}\n")
                        f.write(f"> Level floor: {level_floor}\n")
                        f.write(f"> Run `gaia fuse {candidate}` to confirm.\n\n")
                else:
                    f.write("_No pending combinations._\n\n")

                f.write("---\n")
                f.write("*Generated from skill-tree.json. Do not edit directly.*\n")

    print(f"Generated projections for {len(skills)} skills.")


def _generate_tree(skills, skill_map, meta, version, date_str, named_map=None,
                   named_level_map=None, named_entry_level=None):
    """Render canonical tree.md via the shared render_tree contract."""
    body = render_tree(
        skills,
        mode="canonical",
        named_map=named_map,
        named_level_map=named_level_map,
        named_entry_level=named_entry_level,
        meta=meta,
        version=version,
        date_str=date_str,
        skill_map=skill_map,
        build_skill_display=_build_skill_display,
        render_subtree=_render_subtree,
        sorted_ultimates=_sorted_ultimates,
    )
    lines = [
        "# Gaia Skill Tree",
        "",
        "```",
        body.rstrip("\n"),
        "```",
        "",
        f"*Generated from gaia.json on {date_str}. Do not edit directly.*",
    ]
    os.makedirs("generated-output", exist_ok=True)
    with open("generated-output/tree.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
