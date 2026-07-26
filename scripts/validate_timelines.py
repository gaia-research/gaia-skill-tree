#!/usr/bin/env python3
"""Transparency Gate — prove user-tree timelines explain each skill's current rank.

Gaia's mindset: **every event is on the record.** No rank change is untracked —
each promotion or demotion must leave an auditable timeline event so the Hero's
Journey tells the whole truth. This gate enforces that mindset in CI; see
CONTEXT.md § Transparency, PRODUCT.md Design Principle 6, and CONTRIBUTING.md.

The Hero's Journey shown on a contributor profile is rendered from that
contributor's **user tree** (``skill-trees/<user>/skill-tree.json``) — its
``timeline[]`` and ``unlockedSkills[]``. Rank changes (promotions, and
especially **demotions**) are often applied on the **registry node**
(``registry/named/<contrib>/<skill>.md``) without being mirrored onto the user
tree. When that happens a skill silently sits at its old rank on the profile —
e.g. a skill demoted 3★→1★ still charts at 3★ with no demote event.

This gate makes that drift impossible to merge. For every named skill a
contributor owns in their own tree it asserts:

  1. ``unlockedSkills[].level`` == the skill's **current registry level**
     (the tree isn't stale), and
  2. the **latest level-bearing timeline event** (``newValue``) for that skill
     == that current level (the timeline actually *explains* the rank — a
     missing demote/rank_up is caught here).

Only a contributor's **own** named skills (``<owner>/slug``) are checked, since
those are the ones whose rank history the profile presents. Canonical/foreign/
fused entries and skills no longer in the registry are skipped.

Exit code 0 = every timeline explains its rank; 1 = drift (each printed).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
NAMED_JSON = REPO_ROOT / "registry" / "named-skills.json"
TREES_DIR = REPO_ROOT / "skill-trees"


def _norm(level) -> str:
    """Normalize a level to the canonical 'N★' form (digits only → 'N★')."""
    digits = "".join(c for c in str(level or "") if c.isdigit())
    return f"{digits}★" if digits else ""


def _registry_levels() -> dict[str, str]:
    data = json.loads(NAMED_JSON.read_text(encoding="utf-8"))
    entries = [e for arr in (data.get("buckets") or {}).values() for e in arr]
    entries += data.get("awaitingClassification") or []
    return {e["id"]: _norm(e.get("level")) for e in entries if e.get("id")}


def _latest_level_event(timeline: list, skill_id: str) -> str | None:
    """Return the newValue of the most recent level-bearing event, or None."""
    evs = [e for e in timeline
           if e.get("skillId") == skill_id and e.get("newValue")]
    if not evs:
        return None
    evs.sort(key=lambda e: str(e.get("timestamp", "")))
    return _norm(evs[-1].get("newValue"))


def _named_registry_entries() -> list:
    """All registry named-skill index entries (buckets + awaiting classification)."""
    data = json.loads(NAMED_JSON.read_text(encoding="utf-8"))
    entries = [e for arr in (data.get("buckets") or {}).values() for e in arr]
    entries += data.get("awaitingClassification") or []
    return entries


def check_migration_provenance() -> list[str]:
    """Structural, meta-agnostic migration-provenance invariant (#1189).

    Scans **registry named-skill** timelines only (from ``registry/named-skills.json``).
    For every ``demote`` event that carries a ``migrationBatch``, the SAME skill must
    also have a ``type_change`` event whose ``migrationBatch`` is identical. This pairs
    a taxonomy reclassification with the demotion it triggered, so provenance is
    verifiable from structured fields alone.

    The rule is deliberately meta-agnostic: no epoch is hardcoded and no time window
    is applied. Events lacking a ``migrationBatch`` (e.g. pre-provenance Yggdrasil I
    demotions) are **exempt by absence** — the invariant never fires on them.

    User-tree timelines are out of scope (their action enum has no ``type_change``).

    Returns a list of human-readable violation strings (empty when the invariant holds).
    """
    violations: list[str] = []
    entries = _named_registry_entries()
    demotes_checked = 0

    for e in entries:
        sid = e.get("id") or "<unknown>"
        timeline = e.get("timeline") or []
        # migrationBatch values present on this skill's type_change events
        type_change_batches = {
            ev.get("migrationBatch")
            for ev in timeline
            if isinstance(ev, dict)
            and ev.get("action") == "type_change"
            and ev.get("migrationBatch")
        }
        for ev in timeline:
            if not isinstance(ev, dict) or ev.get("action") != "demote":
                continue
            batch = ev.get("migrationBatch")
            if not batch:
                continue  # exempt by absence
            demotes_checked += 1
            if batch not in type_change_batches:
                violations.append(
                    f"[{sid}] demote carries migrationBatch '{batch}' but no "
                    f"type_change on this skill shares that batch"
                )

    print(f"Migration-provenance invariant: {demotes_checked} batched demote(s) "
          f"checked across {len(entries)} registry named skill(s).")
    return violations


def main() -> int:
    if not NAMED_JSON.exists():
        print(f"timelines: cannot find {NAMED_JSON}", file=sys.stderr)
        return 1
    reg = _registry_levels()
    violations: list[str] = []
    trees_checked = skills_checked = 0

    for tree_path in sorted(TREES_DIR.glob("*/skill-tree.json")):
        try:
            tree = json.loads(tree_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            violations.append(f"[{tree_path.parent.name}] unreadable tree: {exc}")
            continue
        trees_checked += 1
        owner = tree.get("userId") or tree_path.parent.name
        timeline = tree.get("timeline", []) or []
        rel = tree_path.relative_to(REPO_ROOT)

        for entry in tree.get("unlockedSkills", []) or []:
            sid = entry.get("skillId", "")
            if "/" not in sid or sid.split("/", 1)[0] != owner:
                continue  # only the owner's own named skills
            if sid not in reg:
                violations.append(f"[{tree_path.parent.name}] '{sid}' does not exist in registry (phantom skill)")
                continue
            skills_checked += 1
            current = reg[sid]
            tree_level = _norm(entry.get("level"))
            if tree_level != current:
                violations.append(
                    f"[{rel}] '{sid}': unlockedSkills level {tree_level or '∅'} "
                    f"≠ current registry level {current}"
                )
            timeline_level = _latest_level_event(timeline, sid)
            if timeline_level is None:
                violations.append(
                    f"[{rel}] '{sid}': no level-bearing timeline event "
                    f"(cannot explain rank {current})"
                )
            elif timeline_level != current:
                violations.append(
                    f"[{rel}] '{sid}': timeline ends at {timeline_level} but the "
                    f"skill is {current} now — a rank_up/demote event is missing"
                )

    print(f"Transparency Gate — timeline integrity: {skills_checked} owned named "
          f"skill(s) across {trees_checked} tree(s).")
    failed = False
    if violations:
        print(f"\n✗ {len(violations)} untracked rank change(s) — transparency violated:\n")
        for v in violations:
            print(f"  • {v}")
        print("\nEvery rank change must leave a timeline event. Backfill with the "
              "/gaia-trace-timeline skill or `gaia dev timeline <id> --user <owner> "
              "--action demote|rank_up --timestamp <iso> --notes \"…\"`, then "
              "`gaia docs build`.")
        failed = True
    else:
        print("✓ Transparency Gate: every user-tree timeline explains its skill's "
              "current rank — no untracked rank changes.")

    # Migration-provenance invariant (#1189) — registry named-skill timelines only.
    prov_violations = check_migration_provenance()
    if prov_violations:
        print(f"\n✗ {len(prov_violations)} migration-provenance violation(s):\n")
        for v in prov_violations:
            print(f"  • {v}")
        print("\nEvery batched demote must be paired with a same-skill type_change "
              "sharing its migrationBatch (structured migration provenance, #1189).")
        failed = True
    else:
        print("✓ Migration-provenance invariant: every batched demote is paired with "
              "a same-skill type_change sharing its migrationBatch.")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
