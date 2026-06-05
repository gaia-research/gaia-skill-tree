#!/usr/bin/env python3
"""Trace a skill's rank history and backfill missing user-tree timeline events.

Rank changes (especially demotions) are frequently applied on the **registry
node** (``registry/named/<contrib>/<skill>.md`` ``timeline:``) without being
mirrored onto the contributor's **user tree**
(``skill-trees/<owner>/skill-tree.json``) — which is what the profile's Hero's
Journey and rank chart actually read. The result: a skill silently charts at its
old rank (e.g. a 3★→1★ demotion that never shows).

This tool reconciles the two. For a given skill (or every drifting skill) it:

  1. Reads the authoritative level-change events from the registry ``.md``
     timeline (``demote`` / ``rank_up``, parsing "from X★ to Y★").
  2. Appends any that are missing from the user tree (matched by
     ``skillId`` + ``timestamp`` + ``action``) — with ``previousValue`` /
     ``newValue`` so the rank chart plots them.
  3. Sets ``unlockedSkills[].level`` to the current registry level and rebuilds
     its ``levelHistory`` from the register event + level changes.

Use ``gaia dev timeline`` for one-off appends; this is the bulk auditor/fixer
behind the ``/gaia-trace-timeline`` skill and the ``validate_timelines`` gate.

Usage:
    python scripts/trace_timeline.py <handle/slug>      # dry-run trace
    python scripts/trace_timeline.py <handle/slug> --apply
    python scripts/trace_timeline.py --all              # dry-run every drift
    python scripts/trace_timeline.py --all --apply      # fix every drift
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
NAMED_JSON = REPO_ROOT / "registry" / "named-skills.json"
NAMED_DIR = REPO_ROOT / "registry" / "named"
TREES_DIR = REPO_ROOT / "skill-trees"

_FROM_TO = re.compile(r"from\s*(\d+)\D*\s*to\s*(\d+)", re.I)


def _after(iso_ts: str) -> str:
    """Return an ISO-8601 timestamp one second after ``iso_ts`` (UTC 'Z')."""
    from datetime import datetime, timedelta, timezone
    s = (iso_ts or "").strip().strip("'\"").replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        dt = datetime(2026, 6, 2, tzinfo=timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (dt + timedelta(seconds=1)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _norm(level) -> str:
    digits = "".join(c for c in str(level or "") if c.isdigit())
    return f"{digits}★" if digits else ""


def registry_levels() -> dict[str, str]:
    data = json.loads(NAMED_JSON.read_text(encoding="utf-8"))
    entries = [e for arr in (data.get("buckets") or {}).values() for e in arr]
    entries += data.get("awaitingClassification") or []
    return {e["id"]: _norm(e.get("level")) for e in entries if e.get("id")}


def _frontmatter(md_path: Path) -> str:
    m = re.search(r"^---\n(.*?)\n---", md_path.read_text(encoding="utf-8"), re.S)
    return m.group(1) if m else ""


def md_updated_at(skill_id: str) -> str:
    """Best-available timestamp for a registry node (its updatedAt), used to
    date a synthesized reconciliation event. Falls back to a fixed audit date."""
    md = find_md(skill_id)
    if md:
        m = re.search(r"^updatedAt:\s*(.+)$", _frontmatter(md), re.M)
        if m:
            ts = m.group(1).strip().strip("'\"")
            return ts if "T" in ts else ts + "T00:00:00Z"
    return "2026-06-02T00:00:00Z"


def find_md(skill_id: str) -> Path | None:
    """Locate the registry .md whose frontmatter id == skill_id."""
    handle = skill_id.split("/", 1)[0]
    d = NAMED_DIR / handle
    if not d.is_dir():
        return None
    for md in sorted(d.glob("*.md")):
        if re.search(rf"^id:\s*{re.escape(skill_id)}\s*$", _frontmatter(md), re.M):
            return md
    return None


def md_level_events(skill_id: str) -> list[dict]:
    """Return the registry node's level-change events for a skill, oldest first:
    [{timestamp, action, previousValue, newValue, details}]."""
    md = find_md(skill_id)
    if not md:
        return []
    fm = _frontmatter(md)
    block = re.search(r"\ntimeline:\n(.*?)(?:\n[A-Za-z_][\w-]*:\s|\Z)", fm, re.S)
    if not block:
        return []
    out: list[dict] = []
    # Split into "- timestamp:" records.
    for rec in re.split(r"\n(?=- timestamp:)", block.group(1)):
        ts = re.search(r"timestamp:\s*'?([^'\n]+)'?", rec)
        action = re.search(r"action:\s*(\w+)", rec)
        details = re.search(r"details:\s*(.+)", rec)
        if not (ts and action):
            continue
        act = action.group(1)
        if act not in ("demote", "rank_up"):
            continue
        det = (details.group(1).strip() if details else "")
        ft = _FROM_TO.search(det)
        if not ft:
            continue  # a demote/rank_up with no parseable "from X to Y" (e.g.
                      # "Origin status set to true") is not a real level change.
        out.append({"timestamp": ts.group(1).strip(), "action": act,
                    "previousValue": f"{ft.group(1)}★", "newValue": f"{ft.group(2)}★",
                    "details": det})
    out.sort(key=lambda e: e["timestamp"])
    return out


def reconcile(skill_id: str, apply: bool) -> tuple[int, list[str]]:
    """Backfill one skill. Returns (events_added, log_lines)."""
    owner = skill_id.split("/", 1)[0]
    tree_path = TREES_DIR / owner / "skill-tree.json"
    log: list[str] = []
    if not tree_path.exists():
        return 0, [f"  no user tree at {tree_path.relative_to(REPO_ROOT)}"]
    reg = registry_levels()
    current = reg.get(skill_id)
    if current is None:
        return 0, [f"  {skill_id} not in registry (removed/fused) — skipping"]

    tree = json.loads(tree_path.read_text(encoding="utf-8"))
    timeline = tree.setdefault("timeline", [])
    have = {(e.get("skillId"), e.get("timestamp"), e.get("action")) for e in timeline}

    # Level events already on the tree (e.g. the register event) → starting point.
    tree_evs = sorted((e for e in timeline
                       if e.get("skillId") == skill_id and e.get("newValue")),
                      key=lambda e: str(e.get("timestamp", "")))
    tree_last = _norm(tree_evs[-1]["newValue"]) if tree_evs else None

    # Documented registry-node level changes, deduped against the tree.
    to_add = [ev for ev in md_level_events(skill_id)
              if (skill_id, ev["timestamp"], ev["action"]) not in have]

    # Does the documented record reach the current level? If not (an
    # undocumented registry-side recalibration), synthesize ONE clearly-labeled
    # reconciliation event so the timeline explains the rank.
    reached = _norm(to_add[-1]["newValue"]) if to_add else tree_last
    if reached != current:
        prev = reached or tree_last or "0★"
        act = "rank_up" if int(_norm(current).rstrip("★") or 0) > int(prev.rstrip("★") or 0) else "demote"
        # Date the reconciliation strictly AFTER every existing/added event for
        # this skill so it is the latest level the timeline records.
        prior_ts = ([e.get("timestamp", "") for e in tree_evs]
                    + [e["timestamp"] for e in to_add] + [md_updated_at(skill_id)])
        to_add.append({
            "timestamp": _after(max(prior_ts)), "action": act,
            "previousValue": prev, "newValue": current,
            "details": (f"Reconciled to current registry level {current} "
                        f"(registry-side recalibration; no source event recorded)."),
            "_synth": True,
        })

    for ev in to_add:
        log.append(f"  {ev['timestamp']}  {ev['action']:7} "
                   f"{ev['previousValue']}→{ev['newValue']}"
                   f"{'  (reconciled)' if ev.get('_synth') else '  (from registry node)'}")

    if apply and to_add:
        for ev in to_add:
            timeline.append({k: v for k, v in ev.items() if k != "_synth"} | {"skillId": skill_id})
        timeline.sort(key=lambda e: str(e.get("timestamp", "")))
        # Rebuild the owned skill's level + levelHistory from its full event run.
        runs = sorted((e for e in timeline
                       if e.get("skillId") == skill_id and e.get("newValue")),
                      key=lambda e: str(e.get("timestamp", "")))
        for entry in tree.get("unlockedSkills", []):
            if entry.get("skillId") != skill_id:
                continue
            entry["level"] = current
            entry["levelHistory"] = [
                {"level": _norm(e["newValue"]),
                 "achievedAt": e["timestamp"],
                 "source": "demote" if e.get("action") == "demote" else "promotion"}
                for e in runs
            ]
        tree_path.write_text(json.dumps(tree, indent=2, ensure_ascii=False) + "\n",
                             encoding="utf-8")
    return len(to_add), log


def drifting_skills() -> list[str]:
    """Owned named skills whose tree level or timeline disagrees with registry."""
    reg = registry_levels()
    out: list[str] = []
    for tree_path in sorted(TREES_DIR.glob("*/skill-tree.json")):
        tree = json.loads(tree_path.read_text(encoding="utf-8"))
        owner = tree.get("userId") or tree_path.parent.name
        timeline = tree.get("timeline", []) or []
        for entry in tree.get("unlockedSkills", []) or []:
            sid = entry.get("skillId", "")
            if "/" not in sid or sid.split("/", 1)[0] != owner or sid not in reg:
                continue
            evs = sorted((e for e in timeline
                          if e.get("skillId") == sid and e.get("newValue")),
                         key=lambda e: str(e.get("timestamp", "")))
            tl = _norm(evs[-1]["newValue"]) if evs else None
            if _norm(entry.get("level")) != reg[sid] or tl != reg[sid]:
                out.append(sid)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("skill_id", nargs="?", help="handle/slug to trace")
    ap.add_argument("--all", action="store_true", help="trace every drifting skill")
    ap.add_argument("--apply", action="store_true", help="write the backfill (else dry-run)")
    args = ap.parse_args()

    if not args.skill_id and not args.all:
        ap.error("provide a <handle/slug> or --all")

    targets = drifting_skills() if args.all else [args.skill_id]
    if not targets:
        print("No drifting skills — every timeline already explains its rank.")
        return 0

    total = 0
    for sid in targets:
        print(f"\n● {sid}  (current registry level: {registry_levels().get(sid, '?')})")
        added, log = reconcile(sid, args.apply)
        for line in log:
            print(line)
        total += added
    verb = "Appended" if args.apply else "Would append"
    print(f"\n{verb} {total} missing timeline event(s) across {len(targets)} skill(s).")
    if not args.apply and total:
        print("Re-run with --apply to write them, then `gaia docs build`.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
