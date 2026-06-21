"""Registry health summary for ``gaia stats``."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Iterable

from gaia_cli.formatting import (
    TIER_COLORS,
    RANK_COLORS,
    TYPE_SYMBOLS,
    _use_color,
    _fg,
    _reset,
)
from gaia_cli.leveling import demerit_penalty, effective_level
from gaia_cli.registry import (
    named_skills_dir,
    registry_graph_path,
    named_skills_index_path,
)

TYPE_LABELS = {
    "basic": "Basic Skill",
    "extra": "Extra Skill",
    "unique": "Unique Skill",
    "ultimate": "Ultimate Skill",
}

LEVEL_LABELS = {
    "0★": "Basic",
    "1★": "Awakened",
    "2★": "Named",
    "3★": "Evolved",
    "4★": "Hardened",
    "5★": "Transcendent",
    "6★": "Apex",
}

LEVEL_ORDER = ("0★", "1★", "2★", "3★", "4★", "5★", "6★")
TYPE_ORDER = ("basic", "extra", "unique", "ultimate")
EVIDENCE_ORDER = ("A", "B", "C")
_EVIDENCE_RANK = {
    klass: rank for rank, klass in enumerate(reversed(EVIDENCE_ORDER), start=1)
}
_LEVEL_INDEX = {level: idx for idx, level in enumerate(LEVEL_ORDER)}


def _load_json(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _graph_path(registry_path: str | Path) -> Path:
    root = Path(registry_path)
    current = Path(registry_graph_path(root))
    if current.exists():
        return current
    return root / "graph" / "gaia.json"


def _named_dir(registry_path: str | Path) -> Path:
    root = Path(registry_path)
    current = Path(named_skills_dir(root))
    if current.is_dir():
        return current
    return root / "graph" / "named"


def _parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    frontmatter, sep, _body = text[4:].partition("\n---")
    if not sep:
        return {}
    data: dict[str, str] = {}
    for line in frontmatter.splitlines():
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def _iter_named_skill_metadata(registry_path: str | Path) -> Iterable[dict[str, str]]:
    index_path = Path(named_skills_index_path(registry_path))
    if index_path.is_file():
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            items = []
            for bucket in data.get("buckets", {}).values():
                items.extend(bucket)
            items.extend(data.get("awaitingClassification", []))
            return items
        except OSError:
            pass

    root = _named_dir(registry_path)
    if not root.is_dir():
        return []
    items = []
    for path in sorted(root.rglob("*.md")):
        try:
            items.append(_parse_frontmatter(path.read_text(encoding="utf-8")))
        except OSError:
            continue
    return items


_SLOT_LEVEL_RANK = {l: i for i, l in enumerate(["0★", "1★", "2★", "3★", "4★", "5★", "6★"])}


def _slot_levels(registry_path: str | Path) -> dict[str, str]:
    """Map generic skill id → highest named-variant level (0★ if unclaimed)."""
    slot_level: dict[str, str] = {}
    for item in _iter_named_skill_metadata(registry_path):
        ref = item.get("genericSkillRef")
        lv = item.get("level")
        if not ref or not lv or lv not in _SLOT_LEVEL_RANK:
            continue
        if item.get("status", "named") != "named":
            continue
        if _SLOT_LEVEL_RANK[lv] > _SLOT_LEVEL_RANK.get(slot_level.get(ref, "0★"), 0):
            slot_level[ref] = lv
    return slot_level


def _best_evidence_class(skill: dict) -> str | None:
    best: str | None = None
    for evidence in skill.get("evidence", []) or []:
        klass = str(evidence.get("class", "")).upper()
        if klass not in _EVIDENCE_RANK:
            continue
        if best is None or _EVIDENCE_RANK[klass] > _EVIDENCE_RANK[best]:
            best = klass
    return best


def collect_stats(registry_path: str | Path) -> dict:
    """Collect registry counts used by the stats command."""
    graph = _load_json(_graph_path(registry_path))
    skills = graph.get("skills", [])
    edges = graph.get("edges")
    if edges is None:
        edges = [
            {"source": prereq, "target": skill.get("id")}
            for skill in skills
            for prereq in (skill.get("prerequisites", []) or [])
        ]

    type_counts = Counter(skill.get("type", "unknown") for skill in skills)

    slot_lvls = _slot_levels(registry_path)
    level_counts = Counter(
        slot_lvls.get(skill.get("id", ""), "0★") for skill in skills if skill.get("id")
    )
    effective_level_counts = Counter()
    demerit_counts: Counter[str] = Counter()
    skills_with_demerits = 0

    best_evidence_counts: Counter[str] = Counter()
    for skill in skills:
        best = _best_evidence_class(skill)
        if best:
            best_evidence_counts[best] += 1
        sid = skill.get("id", "")
        enriched = {**skill, "level": slot_lvls.get(sid, "0★")}
        effective_level_counts[effective_level(enriched)] += 1
        raw_demerits = list(skill.get("demerits", []) or [])
        if raw_demerits:
            skills_with_demerits += 1
            for demerit in raw_demerits:
                demerit_counts[demerit] += 1

    named_items = [
        item
        for item in _iter_named_skill_metadata(registry_path)
        if item.get("id")
        and item.get("genericSkillRef")
        and item.get("status", "named") == "named"
    ]
    named_slots = {item["genericSkillRef"] for item in named_items}
    # All generic slots are eligible for naming (none are retired/locked at 0★ by intent)
    eligible_slots = {skill["id"] for skill in skills if skill.get("id")}

    return {
        "total_skills": len(skills),
        "total_edges": len(edges),
        "type_counts": dict(type_counts),
        "level_counts": dict(level_counts),
        "effective_level_counts": dict(effective_level_counts),
        "demerit_counts": dict(demerit_counts),
        "skills_with_demerits": skills_with_demerits,
        "skills_with_effective_drop": sum(
            1
            for skill in skills
            if skill.get("id")
            and _LEVEL_INDEX.get(effective_level({**skill, "level": slot_lvls.get(skill.get("id", ""), "0★")}), -1)
            < _LEVEL_INDEX.get(slot_lvls.get(skill.get("id", ""), "0★"), -1)
        ),
        "demerit_penalty_total": sum(
            demerit_penalty({**skill, "level": slot_lvls.get(skill.get("id", ""), "0★")})
            for skill in skills if skill.get("id")
        ),
        "evidence_counts": {
            klass: best_evidence_counts.get(klass, 0) for klass in EVIDENCE_ORDER
        },
        "skills_with_evidence": sum(best_evidence_counts.values()),
        "named_implemented": len(named_items),
        "named_slots": len(named_slots),
        "named_eligible": len(eligible_slots),
        "named_unclaimed": max(len(eligible_slots - named_slots), 0),
    }


def _bar(count: int, total: int, width: int = 25) -> str:
    if total <= 0:
        filled = 0
    else:
        filled = round((count / total) * width)
    filled = max(0, min(width, filled))
    return "█" * filled + "░" * (width - filled)


def _percent(count: int, total: int) -> int:
    return round((count / total) * 100) if total else 0


def render_stats(stats: dict) -> str:
    """Render a human-readable stats report."""
    total = stats["total_skills"]
    use_color = _use_color()
    rst = _reset() if use_color else ""
    lines = [f"Gaia Registry — {total} skills  {stats['total_edges']} edges", ""]

    lines.append("Type breakdown")
    for skill_type in TYPE_ORDER:
        label = TYPE_LABELS[skill_type]
        glyph = TYPE_SYMBOLS.get(skill_type, " ")
        count = stats["type_counts"].get(skill_type, 0)
        bar = _bar(count, total)
        if use_color:
            color = _fg(*TIER_COLORS[skill_type])
            lines.append(
                f"  {color}{glyph} {label:<14}{rst} {count:>4}  {color}{bar}{rst}  {_percent(count, total):>3}%"
            )
        else:
            lines.append(
                f"  {glyph} {label:<14} {count:>4}  {bar}  {_percent(count, total):>3}%"
            )
    for skill_type, count in sorted(stats["type_counts"].items()):
        if skill_type not in TYPE_LABELS:
            lines.append(
                f"  {skill_type:<14} {count:>4}  {_bar(count, total)}  {_percent(count, total):>3}%"
            )

    lines.extend(["", "Level breakdown"])
    for level in LEVEL_ORDER:
        label = LEVEL_LABELS[level]
        count = stats["level_counts"].get(level, 0)
        suffix = ""
        if level == "0★" and stats.get("named_unclaimed", 0):
            suffix = f"  ({stats['named_unclaimed']} unclaimed)"
        if use_color:
            color = _fg(*RANK_COLORS.get(level, RANK_COLORS["0★"]))
            lines.append(f"  {color}{level:<3} {label:<14}{rst} {count:>4}{suffix}")
        else:
            lines.append(f"  {level:<3} {label:<14} {count:>4}{suffix}")
    for level, count in sorted(stats["level_counts"].items()):
        if level not in LEVEL_LABELS:
            lines.append(f"  {level:<3} {'Unknown':<14} {count:>4}")

    lines.extend(["", "Effective level breakdown"])
    for level in LEVEL_ORDER:
        label = LEVEL_LABELS[level]
        count = stats.get("effective_level_counts", {}).get(level, 0)
        if use_color:
            color = _fg(*RANK_COLORS.get(level, RANK_COLORS["0★"]))
            lines.append(f"  {color}{level:<3} {label:<14}{rst} {count:>4}")
        else:
            lines.append(f"  {level:<3} {label:<14} {count:>4}")
    for level, count in sorted(stats.get("effective_level_counts", {}).items()):
        if level not in LEVEL_LABELS:
            lines.append(f"  {level:<3} {'Unknown':<14} {count:>4}")

    lines.extend(["", "Demerits"])
    lines.append(
        f"  Skills with demerits      {stats.get('skills_with_demerits', 0):>4}"
    )
    lines.append(
        f"  Effective level drops     {stats.get('skills_with_effective_drop', 0):>4}"
    )
    lines.append(
        f"  Total demerit penalties   {stats.get('demerit_penalty_total', 0):>4}"
    )
    for demerit, count in sorted(stats.get("demerit_counts", {}).items()):
        lines.append(f"  {demerit:<24} {count:>4}")

    lines.extend(["", "Evidence coverage"])
    lines.append(f"  With evidence {stats['skills_with_evidence']:>4} / {total}")
    for klass in EVIDENCE_ORDER:
        lines.append(f"  Class {klass:<7} {stats['evidence_counts'].get(klass, 0):>4}")

    eligible = stats.get("named_eligible", 0)
    implemented = stats.get("named_implemented", 0)
    lines.extend(["", "Named skills"])
    lines.append(
        f"  Implemented  {implemented:>4} / {eligible} eligible ({_percent(implemented, eligible)}%)"
    )
    return "\n".join(lines) + "\n"


def stats_command(args) -> None:
    print(render_stats(collect_stats(args.registry)), end="")


class StatsCommand:
    name = "stats"
    help = "Registry health summary"

    def configure(self, parser) -> None:
        pass

    def execute(self, args) -> int | None:
        stats_command(args)
        return 0


COMMAND = StatsCommand()

