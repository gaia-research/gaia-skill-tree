#!/usr/bin/env python3
"""Yggdrasil II (#997) — Taxonomy v6 migration.

Two-phase migration:

Phase A (starless nodes): Rewrite the ``type`` field on every generic node
from the legacy 4-value enum {basic, extra, unique, ultimate} to the
Yggdrasil II 2-value enum {basic, fusion}.  Files are moved from their
legacy directory (``registry/nodes/extra/``, ``registry/nodes/ultimate/``)
into ``registry/nodes/fusion/`` via git mv.  ``registry/nodes/basic/`` is
unchanged.  For each reclassified node a ``type_change`` timeline event is
appended.

Phase B (named skills at 4★/5★): Appends a ``type_change`` timeline event
to every named skill at 4★ or 5★ recording that its generic parent's type
was updated.  Evaluates each 4★ named skill against its branch gate:

    * Unique-branch 4★ (generic has no suiteComponents):
      - generic_prereqs == 0 → origin = named.origin is True
      - generic_prereqs  > 0 → origin = contributor holds origin on ≥1 prereq
      Gate: origin AND TM ≥ 100 (grade A)
    * Suite-branch 4★ (generic has suiteComponents): shares the Unique gate
      (ratified 2026-07-16) — origin AND TM ≥ 100 (grade A)
    * 5★ (any branch): NEVER auto-demote — recorded as FOUNDER_CHECKPOINT.
      --allow-5star-demote is provided but NOT passed in normal operation.

Idempotent: re-running on already-migrated data is a no-op.

Usage:
    python scripts/migrate_taxonomy_v6.py              # dry-run (default)
    python scripts/migrate_taxonomy_v6.py --apply      # write + git mv
    python scripts/migrate_taxonomy_v6.py --allow-5star-demote --apply

Report: generated-output/taxonomy_v6_report.{json,csv}  (gitignored dir)
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Repo-root + src on sys.path (mirrors migrateTrustMagnitude.py)
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from gaia_cli.trustMagnitude import computeBranch, computeTrustMagnitude  # noqa: E402
from gaia_cli.promotion import checkUniqueBranchGate  # noqa: E402

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
NODES_DIR       = REPO_ROOT / "registry" / "nodes"
BASIC_DIR       = NODES_DIR / "basic"
EXTRA_DIR       = NODES_DIR / "extra"
ULTIMATE_DIR    = NODES_DIR / "ultimate"
FUSION_DIR      = NODES_DIR / "fusion"
NAMED_DIR       = REPO_ROOT / "registry" / "named"
OUT_DIR         = REPO_ROOT / "generated-output"

# ---------------------------------------------------------------------------
# Taxonomy mapping (legacy → v6)
# ---------------------------------------------------------------------------
# extra (>=1 prereqs) → fusion
# ultimate (>=1 prereqs) → fusion
# basic (0 prereqs) → basic  (no change)
# unique (0 prereqs) → basic  (per Q4 — no unique nodes exist in practice)
LEGACY_TO_V6: dict[str, str] = {
    "basic":    "basic",
    "extra":    "fusion",
    "unique":   "basic",
    "ultimate": "fusion",
}

# Unique-branch TM floor (4★ = A = 100, 5★ = S = 250)
TM_FLOOR_4STAR = 100.0
TM_FLOOR_5STAR = 250.0

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)", re.DOTALL)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load_node(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _save_node(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _load_named_skill(path: Path) -> tuple[dict | None, str]:
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None, text
    fm = yaml.safe_load(m.group(1)) or {}
    return fm, m.group(2)


def _save_named_skill(path: Path, fm: dict, body: str) -> None:
    serialized = yaml.dump(fm, allow_unicode=True, sort_keys=False)
    path.write_text(f"---\n{serialized}---\n{body}", encoding="utf-8")


def _git_mv(src: Path, dst: Path, dry_run: bool) -> None:
    if dry_run:
        print(f"  [dry] git mv {src.relative_to(REPO_ROOT)} -> {dst.relative_to(REPO_ROOT)}")
        return
    result = subprocess.run(
        ["git", "mv", str(src), str(dst)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git mv failed: {result.stderr.strip()}")


def _build_generic_skill_map(nodes_dir: Path) -> dict[str, dict]:
    gmap: dict[str, dict] = {}
    for p in nodes_dir.rglob("*.json"):
        try:
            d = _load_node(p)
        except Exception:
            continue
        sid = d.get("id")
        if sid:
            gmap[sid] = d
    return gmap


def _build_named_skill_map(named_dir: Path) -> dict[str, dict]:
    nmap: dict[str, dict] = {}
    for p in named_dir.rglob("*.md"):
        try:
            fm, _ = _load_named_skill(p)
        except Exception:
            continue
        if fm is None:
            continue
        sid = fm.get("id")
        if sid:
            nmap[sid] = fm
    return nmap


# ---------------------------------------------------------------------------
# Phase A: Starless node type rewrite + directory reorganisation
# ---------------------------------------------------------------------------

def _derive_v6_type(data: dict, path: Path) -> tuple[str, str | None]:
    """Derive the Yggdrasil II type from prerequisites.

    Returns (derived_type, anomaly_description).
    anomaly_description is None if no anomaly.
    """
    prereqs = data.get("prerequisites") or []
    has_prereqs = bool(prereqs)
    legacy_type = data.get("type", "")

    # Structural derivation: basic (0 prereqs) or fusion (>=1 prereq)
    derived = "fusion" if has_prereqs else "basic"

    # Cross-check against legacy value
    expected_derived = LEGACY_TO_V6.get(legacy_type)
    if expected_derived is None:
        # Already migrated or unknown legacy type
        if legacy_type in ("basic", "fusion"):
            # Already v6 — no anomaly if consistent with prereqs
            if legacy_type != derived:
                return derived, (
                    f"Already-v6 node has type={legacy_type!r} but "
                    f"{'has' if has_prereqs else 'has no'} prerequisites "
                    f"(derived={derived!r}) — structural inconsistency"
                )
            return legacy_type, None  # already migrated, no change needed
        return derived, f"Unknown legacy type={legacy_type!r}; using derived={derived!r}"

    if expected_derived != derived:
        # Unexpected mismatch: e.g. basic WITH prerequisites or extra WITHOUT
        return derived, (
            f"Legacy type={legacy_type!r} expected derived={expected_derived!r} "
            f"but structural derivation gives derived={derived!r} "
            f"(prereqs={prereqs!r}) — flagged for manual review"
        )
    return derived, None


def migrate_starless_nodes(
    dry_run: bool,
    stats: dict[str, Any],
) -> dict[str, str]:
    """Phase A wrapper — returns a mapping of nodeId -> legacyType for Phase B."""
    """Phase A: rewrite type fields and reorganise directories."""
    print("\n=== Phase A: Starless node type rewrite + directory reorganisation ===")

    # Ensure fusion/ dir exists
    if not dry_run:
        FUSION_DIR.mkdir(parents=True, exist_ok=True)
    else:
        print(f"  [dry] mkdir {FUSION_DIR.relative_to(REPO_ROOT)}")

    all_source_dirs = [
        (BASIC_DIR, "basic"),
        (EXTRA_DIR, "extra"),
        (ULTIMATE_DIR, "ultimate"),
    ]

    moved:   list[dict] = []
    retyped: list[dict] = []
    anomalies: list[dict] = []
    already_done: int = 0
    # Track legacy type for each node (nodeId -> legacy type) for Phase B use
    legacy_type_map: dict[str, str] = {}

    for src_dir, dir_label in all_source_dirs:
        if not src_dir.exists():
            print(f"  [skip] {src_dir.relative_to(REPO_ROOT)} — directory not found")
            continue

        for node_path in sorted(src_dir.glob("*.json")):
            data = _load_node(node_path)
            node_id    = data.get("id", node_path.stem)
            legacy_type = data.get("type", "")
            prereqs    = data.get("prerequisites") or []

            # Track legacy type BEFORE any rewrite (used by Phase B for details text)
            legacy_type_map[node_id] = legacy_type

            # Idempotency: if already in fusion/ with type=fusion, skip
            if str(node_path).replace("\\", "/").find("/fusion/") != -1 and legacy_type == "fusion":
                already_done += 1
                continue

            v6_type, anomaly = _derive_v6_type(data, node_path)

            if anomaly:
                anomalies.append({
                    "nodeId": node_id,
                    "path": node_path.relative_to(REPO_ROOT).as_posix(),
                    "legacyType": legacy_type,
                    "derivedType": v6_type,
                    "description": anomaly,
                })
                print(f"  [ANOMALY] {node_id}: {anomaly}")
                # Still process: move file to correct dir, but flag the mismatch
                # The type assignment uses the derived value (structural truth)

            # Determine destination directory
            if v6_type == "basic":
                dst_dir = BASIC_DIR
            else:
                dst_dir = FUSION_DIR
            dst_path = dst_dir / node_path.name

            # File move (only if changing directory)
            needs_move = (node_path.parent != dst_dir)
            if needs_move:
                moved.append({
                    "nodeId": node_id,
                    "from": node_path.relative_to(REPO_ROOT).as_posix(),
                    "to": dst_path.relative_to(REPO_ROOT).as_posix(),
                    "legacyType": legacy_type,
                    "v6Type": v6_type,
                })
                if not dry_run:
                    if not FUSION_DIR.exists():
                        FUSION_DIR.mkdir(parents=True, exist_ok=True)
                    _git_mv(node_path, dst_path, dry_run=False)
                    print(f"  [mv]  {node_path.relative_to(REPO_ROOT)} -> {dst_path.relative_to(REPO_ROOT)}")
                else:
                    _git_mv(node_path, dst_path, dry_run=True)
                # After move, data is at dst_path
                active_path = dst_path
            else:
                active_path = node_path

            # Type rewrite
            if legacy_type == v6_type:
                # No type change needed
                continue

            # Append type_change timeline event
            timeline = data.get("timeline")
            if not isinstance(timeline, list):
                timeline = []

            # Idempotency: skip if already has a type_change for this migration
            already_changed = any(
                isinstance(e, dict) and e.get("action") == "type_change" and "Yggdrasil II" in (e.get("details") or "")
                for e in timeline
            )
            if already_changed:
                already_done += 1
                continue

            ts = _now_iso()
            timeline.append({
                "timestamp": ts,
                "action": "type_change",
                "contributor": "mbtiongson1",
                "details": (
                    f"Reclassified from {legacy_type} to {v6_type} "
                    f"(Yggdrasil II taxonomy migration #997)"
                ),
            })
            data["type"] = v6_type
            data["updatedAt"] = _today_iso()
            data["timeline"] = timeline

            retyped.append({
                "nodeId": node_id,
                "legacyType": legacy_type,
                "v6Type": v6_type,
                "prereqCount": len(prereqs),
            })

            if not dry_run:
                _save_node(active_path, data)
                print(f"  [ok]  {node_id}: {legacy_type} -> {v6_type}")
            else:
                print(f"  [dry] {node_id}: {legacy_type} -> {v6_type}")

    stats["phaseA"] = {
        "moved": moved,
        "retyped": retyped,
        "anomalies": anomalies,
        "alreadyDone": already_done,
    }

    print(f"\n  Moved:       {len(moved)} nodes (extra/→fusion/ + ultimate/→fusion/)")
    print(f"  Retyped:     {len(retyped)} nodes")
    print(f"  Anomalies:   {len(anomalies)}")
    print(f"  Already done:{already_done}")
    return legacy_type_map


# ---------------------------------------------------------------------------
# Phase B: Named-skill recalibration
# ---------------------------------------------------------------------------

def _generic_type_after_migration(generic: dict) -> str:
    """Return the v6 type a generic node WILL have after phase A."""
    legacy = generic.get("type", "")
    return LEGACY_TO_V6.get(legacy, legacy)


def _origin_ok_for_unique(
    named: dict,
    generic: dict,
    genericSkillMap: dict,
    namedSkillMap: dict,
) -> bool:
    """Evaluate 'origin present' for the Unique-branch 4★ gate.

    Strategy:
      - If the generic parent has NO prerequisites (basic type): origin is
        satisfied when the named skill itself carries ``origin: true``.
        Rationale: for basic-type generics there is no fusion structure; the
        named skill IS the origin artifact.
      - If the generic parent HAS prerequisites (fusion type): delegate to
        ``checkUniqueBranchGate``'s internal origin predicate via the full
        gate result (originPresent field).
    """
    prereqs = generic.get("prerequisites") or []
    if not prereqs:
        # Basic parent: fall back to named.origin flag
        return named.get("origin") is True
    # Fusion parent: use the gate function (which checks namedSkillMap)
    gate_result = checkUniqueBranchGate(
        named, "4★", genericSkillMap, namedSkillMap
    )
    return bool(gate_result.get("originPresent"))


def migrate_named_skills(
    dry_run: bool,
    allow_5star_demote: bool,
    genericSkillMap: dict,
    namedSkillMap: dict,
    legacy_type_map: dict[str, str],
    stats: dict[str, Any],
) -> None:
    """Phase B: append type_change events + evaluate 4★ branch gates."""
    print("\n=== Phase B: Named-skill recalibration ===")

    type_changes: list[dict] = []
    demotions:    list[dict] = []
    founder_checkpoints: list[dict] = []
    skipped:  int = 0
    errors:   list[dict] = []

    for path in sorted(NAMED_DIR.rglob("*.md")):
        fm, body = _load_named_skill(path)
        if fm is None:
            continue
        level = fm.get("level", "")
        if level not in ("4★", "5★"):
            continue

        skill_id = fm.get("id") or path.stem
        ref = fm.get("genericSkillRef") or ""
        generic = genericSkillMap.get(ref) or {}
        # Derive legacy description from structural truth:
        # - 0 prereqs: generic was basic → basic (unchanged)
        # - >=1 prereqs: generic was extra or ultimate → fusion (either way: type_change)
        # legacy_type_map captures the original type during Phase A; fall back to
        # structural inference when it is absent (idempotency re-runs).
        generic_prereqs_count = len(generic.get("prerequisites") or [])
        raw_legacy = legacy_type_map.get(ref, "")
        if raw_legacy:
            generic_legacy_type = raw_legacy
        elif generic_prereqs_count == 0:
            generic_legacy_type = "basic"
        else:
            # Was extra or ultimate — now fusion; we only know direction, not exact legacy
            generic_legacy_type = "extra/ultimate"
        generic_v6_type = LEGACY_TO_V6.get(generic_legacy_type, generic.get("type", "fusion") if generic_prereqs_count > 0 else "basic")

        # Idempotency: skip if already has type_change for Yggdrasil II migration
        timeline = fm.get("timeline")
        if not isinstance(timeline, list):
            timeline = []
        already_changed = any(
            isinstance(e, dict)
            and e.get("action") == "type_change"
            and "Yggdrasil II" in (e.get("details") or "")
            for e in timeline
        )
        if already_changed:
            skipped += 1
            continue

        ts = _now_iso()

        # --- type_change event for ALL 4★/5★ named skills ---
        if generic_prereqs_count > 0:
            # Parent was extra or ultimate — now fusion
            legacy_label = raw_legacy if raw_legacy else "extra/ultimate"
            type_change_details = (
                f"Generic parent '{ref}' type: {legacy_label} → fusion "
                f"(Yggdrasil II taxonomy migration #997)"
            )
        else:
            # Basic parent — type unchanged
            type_change_details = (
                f"Generic parent '{ref}' type: basic (unchanged; "
                f"Yggdrasil II taxonomy migration #997)"
            )
        type_change_event: dict = {
            "timestamp": ts,
            "action": "type_change",
            "contributor": "mbtiongson1",
            "details": type_change_details,
        }
        timeline.append(type_change_event)
        type_changes.append({"skillId": skill_id, "level": level, "details": type_change_details})

        # --- Gate evaluation ---
        branch = computeBranch(fm, genericSkillMap)
        tm = float(computeTrustMagnitude(fm, genericSkillMap, namedSkillMap))
        demoted = False

        if level == "5★":
            # FIVE-STAR HALT RULE
            suite_preserved = branch == "suite"  # Suite 5★ retained per #935
            gate_would_fail = tm < TM_FLOOR_5STAR
            if not suite_preserved and gate_would_fail:
                # Unique 5★ that would fail — FOUNDER_CHECKPOINT
                checkpoint = {
                    "skillId": skill_id,
                    "level": level,
                    "branch": branch,
                    "tm": round(tm, 2),
                    "tmFloor": TM_FLOOR_5STAR,
                    "reason": "TM below 5★ gate (250); retained by 5★ halt rule",
                }
                founder_checkpoints.append(checkpoint)
                print(f"  [FOUNDER_CHECKPOINT] {skill_id}: branch={branch} tm={tm:.1f} < {TM_FLOOR_5STAR}")
            elif suite_preserved and gate_would_fail:
                # Suite 5★ retained per #935
                checkpoint = {
                    "skillId": skill_id,
                    "level": level,
                    "branch": branch,
                    "tm": round(tm, 2),
                    "tmFloor": TM_FLOOR_5STAR,
                    "reason": "Suite 5★ retained per #935; TM below S threshold",
                }
                founder_checkpoints.append(checkpoint)
                print(f"  [FOUNDER_CHECKPOINT] {skill_id}: Suite 5★ retained per #935, tm={tm:.1f}")
            else:
                print(f"  [ok]  {skill_id}: 5★ gate PASSES (tm={tm:.1f})")

            if allow_5star_demote and gate_would_fail and not suite_preserved:
                # Only demote 5★ when explicitly requested AND it's not a Suite
                demote_event: dict = {
                    "timestamp": ts,
                    "action": "demote",
                    "contributor": "mbtiongson1",
                    "previousValue": "5★",
                    "newValue": "3★",
                    "details": (
                        f"Yggdrasil II recalibration: 5★ unique-branch gate failed "
                        f"(TM={tm:.1f} < {TM_FLOOR_5STAR}); "
                        "demoted via --allow-5star-demote"
                    ),
                }
                timeline.append(demote_event)
                fm["level"] = "3★"
                demoted = True
                demotions.append({
                    "skillId": skill_id,
                    "previousLevel": "5★",
                    "newLevel": "3★",
                    "branch": branch,
                    "tm": round(tm, 2),
                    "failedGate": "TM < 250",
                })

        elif level == "4★":
            # 4★ gate is identical for both branches (ratified 2026-07-16):
            # Extra (suite) shares the Unique gate — origin + TM >= 100.
            origin_ok: bool | None = _origin_ok_for_unique(
                fm, generic, genericSkillMap, namedSkillMap
            )
            tm_ok = tm >= TM_FLOOR_4STAR
            gate_pass = origin_ok and tm_ok
            gate_detail = (
                f"{branch}-branch origin={origin_ok} TM={tm:.1f} "
                f"({'≥' if tm_ok else '<'} {TM_FLOOR_4STAR})"
            )

            if gate_pass:
                print(f"  [PASS] {skill_id}: {level} {gate_detail}")
            else:
                # Demote to 3★ Evolved
                demote_event = {
                    "timestamp": ts,
                    "action": "demote",
                    "contributor": "mbtiongson1",
                    "previousValue": "4★",
                    "newValue": "3★",
                    "details": (
                        f"Yggdrasil II recalibration: 4★ {branch}-branch gate failed "
                        f"({gate_detail}) — demoted to 3★ Evolved"
                    ),
                }
                timeline.append(demote_event)
                fm["level"] = "3★"
                demoted = True
                demotions.append({
                    "skillId": skill_id,
                    "previousLevel": "4★",
                    "newLevel": "3★",
                    "branch": branch,
                    "tm": round(tm, 2),
                    "originOk": origin_ok,
                    "failedGate": gate_detail,
                })
                print(f"  [DEMOTE] {skill_id}: 4★ -> 3★  {gate_detail}")

        # Write back
        fm["timeline"] = timeline
        fm["updatedAt"] = _today_iso()

        if not dry_run:
            _save_named_skill(path, fm, body)
        else:
            pass  # dry-run: already printed above

    stats["phaseB"] = {
        "typeChanges": type_changes,
        "demotions": demotions,
        "founderCheckpoints": founder_checkpoints,
        "skipped": skipped,
        "errors": errors,
    }

    print(f"\n  type_change events appended: {len(type_changes)}")
    print(f"  4★ demoted to 3★:            {len([d for d in demotions if d['previousLevel'] == '4★'])}")
    print(f"  5★ demoted to 3★:            {len([d for d in demotions if d['previousLevel'] == '5★'])}")
    print(f"  5★ FOUNDER_CHECKPOINTs:      {len(founder_checkpoints)}")
    print(f"  Already done (skipped):      {skipped}")


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def write_report(stats: dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # JSON report
    json_path = OUT_DIR / "taxonomy_v6_report.json"
    json_path.write_text(json.dumps(stats, indent=2, sort_keys=False), encoding="utf-8")
    print(f"\n  Report (JSON) -> {json_path.relative_to(REPO_ROOT)}")

    # CSV report — flat rows for the migration
    csv_path = OUT_DIR / "taxonomy_v6_report.csv"
    rows: list[dict] = []

    # Phase A rows
    for item in stats.get("phaseA", {}).get("moved", []):
        rows.append({
            "phase": "A",
            "event": "moved",
            "skillId": item["nodeId"],
            "from": item["from"],
            "to": item["to"],
            "legacyType": item["legacyType"],
            "v6Type": item["v6Type"],
            "level": "",
            "branch": "",
            "tm": "",
            "notes": "",
        })
    for item in stats.get("phaseA", {}).get("retyped", []):
        rows.append({
            "phase": "A",
            "event": "retyped",
            "skillId": item["nodeId"],
            "from": item["legacyType"],
            "to": item["v6Type"],
            "legacyType": item["legacyType"],
            "v6Type": item["v6Type"],
            "level": "",
            "branch": "",
            "tm": "",
            "notes": f"prereqs={item['prereqCount']}",
        })
    for item in stats.get("phaseA", {}).get("anomalies", []):
        rows.append({
            "phase": "A",
            "event": "anomaly",
            "skillId": item["nodeId"],
            "from": item["legacyType"],
            "to": item["derivedType"],
            "legacyType": item["legacyType"],
            "v6Type": item["derivedType"],
            "level": "",
            "branch": "",
            "tm": "",
            "notes": item["description"],
        })

    # Phase B rows
    for item in stats.get("phaseB", {}).get("demotions", []):
        rows.append({
            "phase": "B",
            "event": "demoted",
            "skillId": item["skillId"],
            "from": item["previousLevel"],
            "to": item["newLevel"],
            "legacyType": "",
            "v6Type": "",
            "level": item["previousLevel"],
            "branch": item.get("branch", ""),
            "tm": item.get("tm", ""),
            "notes": item.get("failedGate", ""),
        })
    for item in stats.get("phaseB", {}).get("founderCheckpoints", []):
        rows.append({
            "phase": "B",
            "event": "FOUNDER_CHECKPOINT",
            "skillId": item["skillId"],
            "from": item["level"],
            "to": "(retained)",
            "legacyType": "",
            "v6Type": "",
            "level": item["level"],
            "branch": item.get("branch", ""),
            "tm": item.get("tm", ""),
            "notes": item.get("reason", ""),
        })

    if rows:
        fieldnames = ["phase", "event", "skillId", "from", "to", "legacyType", "v6Type",
                      "level", "branch", "tm", "notes"]
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"  Report (CSV)  -> {csv_path.relative_to(REPO_ROOT)}")
    else:
        print("  (No CSV rows — dry run or no changes)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Yggdrasil II — Taxonomy v6 migration (#997)"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Write changes to disk and run git mv (default: dry-run)",
    )
    parser.add_argument(
        "--allow-5star-demote",
        dest="allow5starDemote",
        action="store_true",
        default=False,
        help=(
            "Allow auto-demotion of 5★ skills that fail their gate. "
            "NOT passed in normal Yggdrasil II migration — founder reviews first."
        ),
    )
    args = parser.parse_args()
    dry_run = not args.apply

    mode = "DRY-RUN" if dry_run else "APPLY"
    print(f"=== Yggdrasil II taxonomy v6 migration ({mode}) ===")
    if dry_run:
        print("  Pass --apply to write changes.")
    if args.allow5starDemote:
        print("  WARNING: --allow-5star-demote is active. 5★ skills may be demoted.")

    stats: dict[str, Any] = {
        "startedAt": _now_iso(),
        "mode": mode,
        "allow5starDemote": args.allow5starDemote,
    }

    # Build maps using nodes as they currently exist on disk.
    # For Phase B we need genericSkillMap to reflect v6 types — but since Phase A
    # writes types in-place, we load AFTER Phase A completes.
    print("\nBuilding genericSkillMap (pre-migration snapshot)...")
    genericSkillMap_pre = _build_generic_skill_map(NODES_DIR)
    print(f"  loaded {len(genericSkillMap_pre)} generic skills")

    namedSkillMap = _build_named_skill_map(NAMED_DIR)
    print(f"Building namedSkillMap: {len(namedSkillMap)} named skills")

    # Phase A
    legacy_type_map = migrate_starless_nodes(dry_run=dry_run, stats=stats)

    # Reload genericSkillMap after phase A writes (types may have changed on disk)
    if not dry_run:
        print("\nReloading genericSkillMap after Phase A writes...")
        genericSkillMap = _build_generic_skill_map(NODES_DIR)
        print(f"  loaded {len(genericSkillMap)} generic skills")
    else:
        # In dry-run, simulate v6 types by patching the in-memory map
        genericSkillMap = {}
        for sid, node in genericSkillMap_pre.items():
            patched = dict(node)
            legacy = node.get("type", "")
            patched["type"] = LEGACY_TO_V6.get(legacy, legacy)
            genericSkillMap[sid] = patched

    # Phase B
    migrate_named_skills(
        dry_run=dry_run,
        allow_5star_demote=args.allow5starDemote,
        genericSkillMap=genericSkillMap,
        namedSkillMap=namedSkillMap,
        legacy_type_map=legacy_type_map,
        stats=stats,
    )

    stats["finishedAt"] = _now_iso()
    write_report(stats)

    # Summary
    pA = stats.get("phaseA", {})
    pB = stats.get("phaseB", {})
    print("\n=== SUMMARY ===")
    print(f"  Phase A — nodes moved:         {len(pA.get('moved', []))}")
    print(f"  Phase A — nodes retyped:       {len(pA.get('retyped', []))}")
    print(f"  Phase A — anomalies:           {len(pA.get('anomalies', []))}")
    print(f"  Phase B — type_change events:  {len(pB.get('typeChanges', []))}")
    print(f"  Phase B — 4★ demotions:        {len([d for d in pB.get('demotions', []) if d['previousLevel'] == '4★'])}")
    print(f"  Phase B — 5★ FOUNDER_CHECKs:  {len(pB.get('founderCheckpoints', []))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
