"""Single render contract for canonical and per-user tree.md.

Both _generate_tree (canonical) and the per-user block in
generateProjections.py funnel through render_tree().  The function is also
importable from src/gaia_cli/ for a future `gaia tree --md` flag.
"""
from __future__ import annotations

import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC_DIR = os.path.join(_REPO_ROOT, "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

# Legend emitted only in canonical mode.
_LEGEND = (
    "◆ Ultimate · ◉ Unique · ◇ Extra · ○ Basic"
    "   ·   [N★] = top named-variant stars (blank = no named implementation yet)"
    " · (↑ see above) = shared prerequisite"
)

_LEVEL_ORDER = ["2★", "3★", "4★", "5★", "6★"]


def _star_pill(named_level_map, sid) -> str:
    """Inline star pill from the top named variant, or empty when unclaimed."""
    star = (named_level_map or {}).get(sid)
    return f"  [{star}]" if star else ""

# Section separators.
_SEP70 = "═" * 70
_SEP65 = "─" * 65


def _get_level_label(meta: dict, level) -> str:
    return str(level)


def _get_tier_label(meta: dict, level) -> str:
    return meta.get("levelLabels", {}).get(str(level), str(level))


def _get_tier_symbol(skill_type: str) -> str:
    return {"basic": "○", "extra": "◇", "unique": "◉", "ultimate": "◆"}.get(
        skill_type, "·"
    )


def _inline_rank_pill(meta: dict, level) -> str:
    """Return the inline rank pill, using [N★ · Pure] for 0★ skills."""
    label = _get_level_label(meta, level)
    if str(level) == "0★":
        return f"[{label} · Pure]"
    return f"[{label}]"


def _fmt_row(
    glyph: str,
    display: str,
    level_label: str,
    tier_label: str,
    *,
    marker: str = "",
    pill_suffix: str = "",
    is_unique: bool = False,
    is_basic: bool = False,
) -> str:
    """Format a single skill row for the Ultimates/Extras/Unique/Basics section."""
    if is_unique:
        return f"  {marker}{glyph} {display}  [{level_label} · {tier_label}]{pill_suffix}"
    if is_basic:
        return f"  {marker}{glyph} {display}  {pill_suffix}" if pill_suffix else f"  {marker}{glyph} {display}  [{level_label} · {tier_label}]"
    return f"{marker}{glyph} {display}  [{level_label}]{pill_suffix}"


def render_tree(
    skills: list,
    *,
    mode: str = "canonical",
    owned_ids: set | None = None,
    named_map: dict | None = None,
    named_level_map: dict | None = None,
    meta: dict | None = None,
    version: str = "",
    date_str: str = "",
    user_id: str = "",
    skill_map: dict | None = None,
    # Internal helpers injected by generateProjections (avoids circular import)
    get_effective_level_label=None,
    get_demerit_suffix=None,
    build_skill_display=None,
    render_subtree=None,
    sorted_ultimates=None,
) -> str:
    """Single render contract for canonical and per-user tree.md.

    Parameters
    ----------
    skills:
        Full skill list.
    mode:
        ``"canonical"`` (default) or ``"user"``.  Canonical includes the
        legend block; user includes owned markers and Pending Combinations.
    owned_ids:
        Set of skill IDs the user owns (user mode only).
    named_map:
        Mapping from skill_id → contributor/name string.
    meta:
        ``gaia.json`` meta block.
    version / date_str:
        Canonical header metadata.
    user_id:
        User handle shown in the user-mode header.
    skill_map:
        ``{id: skill}`` dict (needed for subtree rendering).
    get_effective_level_label / get_demerit_suffix / build_skill_display /
    render_subtree / sorted_ultimates:
        Helper callables injected from generateProjections to avoid duplicating
        them here.  All have sensible fallbacks.
    """
    if meta is None:
        meta = {}
    if named_map is None:
        named_map = {}
    if named_level_map is None:
        named_level_map = {}
    if skill_map is None:
        skill_map = {s["id"]: s for s in skills}
    if owned_ids is None:
        owned_ids = set()

    # Fallback helpers (used when not injected — e.g. in tests).
    def _eff_level_label(m, sk):
        return _get_level_label(m, sk.get("level", ""))

    def _demerit(sk):
        return ""

    def _disp(sid, stype, nm=None, hr=None):
        nid = (nm or {}).get(sid)
        if nid:
            return nid
        return f"/{sid}"

    def _subtree(rid, sm, m, prefix, is_last, seen, u_ids=None, uid=None, nm=None,
                 named_level_map=None, hr=None):
        return []

    def _sorted_ults(sks):
        # Generic refs are rank-less — order ultimates by top named-variant star
        # (descending), then name. Unclaimed ultimates sort last.
        def _key(s):
            star = named_level_map.get(s.get("id"))
            rank = _LEVEL_ORDER.index(star) if star in _LEVEL_ORDER else -1
            return (-rank, s.get("name", ""))
        return sorted(
            [s for s in sks if s.get("type") == "ultimate"],
            key=_key,
        )

    _ell = get_effective_level_label or _eff_level_label
    _dem = get_demerit_suffix or _demerit
    _bsd = build_skill_display or _disp
    _rst = render_subtree or _subtree
    _srt = sorted_ultimates or _sorted_ults

    # Compute orphan basics (no prereqs, not a prereq of anyone).
    all_prereq_ids: set = set()
    for s in skills:
        for pid in s.get("prerequisites", []):
            all_prereq_ids.add(pid)

    legendaries = _srt(skills)
    unique_skills = sorted(
        [s for s in skills if s.get("type") == "unique"],
        key=lambda s: s.get("id", ""),
    )
    basic_orphans = sorted(
        [
            s
            for s in skills
            if s.get("type") == "basic"
            and s["id"] not in all_prereq_ids
            and not s.get("prerequisites")
        ],
        key=lambda s: s.get("id", ""),
    )

    is_user = mode == "user"
    # In user mode show owned / unowned markers; in canonical, no markers.
    handle_rel = None  # canonical; per-user trees have no profile links

    lines: list[str] = []

    # ── Header block ──────────────────────────────────────────────────────
    if not is_user:
        lines.append(_SEP70)
        lines.append(f"GAIA SKILL TREE  v{version}  ·  generated {date_str}")
        lines.append(_SEP70)
        lines.append(_LEGEND)
        lines.append("Shared prerequisites marked (↑ see above) on second occurrence.")
        lines.append(_SEP70)
        lines.append("")
    else:
        lines.append(f"GAIA SKILL TREE — {user_id}  ·  generated {date_str}")
        lines.append(_SEP70)
        lines.append(
            "✓ = owned   · = unowned   "
            + _LEGEND
        )
        lines.append("Shared prerequisites marked (↑ see above) on second occurrence.")
        lines.append(_SEP70)
        lines.append("")

    # ── Ultimates (upgrade paths) ─────────────────────────────────────────
    for legendary in legendaries:
        lid = legendary.get("id")
        prereq_ids = legendary.get("prerequisites", [])
        display = _bsd(lid, "ultimate", named_map, handle_rel)

        # Unclaimed ultimates: no named implementation yet → no star
        is_unclaimed = not (named_map or {}).get(lid)
        star_pill = _star_pill(named_level_map, lid)

        if is_user:
            check = "✓ " if lid in owned_ids else "· "
        else:
            check = ""

        if is_unclaimed:
            lines.append(f"{check}◆ {display}  [Unclaimed]")
        else:
            lines.append(f"{check}◆ {display}{star_pill}")
        if not is_user:
            lines.append(_SEP65)

        seen: set = {lid}
        for i, prereq_id in enumerate(prereq_ids):
            is_last = i == len(prereq_ids) - 1
            for sl in _rst(
                prereq_id,
                skill_map,
                meta,
                "  ",
                is_last,
                seen,
                unlocked_ids=owned_ids if is_user else None,
                user_id=user_id if is_user else None,
                named_map=named_map,
                named_level_map=named_level_map,
                handle_rel=handle_rel,
            ):
                lines.append(sl)
        lines.append("")

    # ── Unique Skills ─────────────────────────────────────────────────────
    if unique_skills:
        lines.append(_SEP70)
        lines.append(
            "Uniques — graph-isolated Basic Skills that reached elite mastery"
            " (4★+) through depth alone, with no fusion path forward."
        )
        lines.append(_SEP70)
        lines.append("")
        for us in unique_skills:
            uid_s = us.get("id")
            display = _bsd(uid_s, "unique", named_map, handle_rel)
            star_pill = _star_pill(named_level_map, uid_s)
            if is_user:
                marker = "✓ " if uid_s in owned_ids else "· "
            else:
                marker = ""
            lines.append(f"  {marker}◉ {display}{star_pill}")
        lines.append("")

    # ── Basics (orphan basics) ────────────────────────────────────────────
    if basic_orphans:
        lines.append(_SEP70)
        lines.append(
            "Basics — basic-tier skills not wired into an upgrade path yet."
            "  ([N★] = top named-variant stars; blank = no named implementation.)"
        )
        lines.append(_SEP70)
        lines.append("")
        for ps in basic_orphans:
            pid = ps.get("id")
            display = _bsd(pid, "basic", named_map, handle_rel)
            star_pill = _star_pill(named_level_map, pid)
            if is_user:
                marker = "✓ " if pid in owned_ids else "· "
            else:
                marker = ""
            lines.append(f"  {marker}○ {display}{star_pill}")
        lines.append("")

    return "\n".join(lines)
