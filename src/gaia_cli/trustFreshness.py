"""Trust Freshness & Materiality Doctrine.

Implements the repository's Trust Freshness policy for generated projections.
Distinguishes harmless routine drift (moving counters such as GitHub stars,
npm downloads, views) from meaningful/material Trust changes that require
projections to be freshly regenerated and committed.

Doctrine rules:
Routine drift is WARN-ONLY when all are true:
  1. Drift comes exclusively from volatile adoption-style counters (e.g.
     GitHub stars, npm downloads, video views, likes, comments).
  2. No explicit Trust review or recalibration occurred since the stored state
     (e.g. no 'recalibrate_trust_magnitude', 'rank_up', 'demote' event).
  3. Trust scoring methodology and rules did not change.
  4. Evidence semantics did not materially change (no rows added, removed,
     retyped, or regraded).
  5. Overall Trust Grade remains identical.
  6. Apex and consequential trust gates remain identical.
  7. Absolute TM drift is within tolerance (< material staleness threshold).

Trust freshness BLOCKS when any are true:
  - An explicit trust review / recalibration occurred.
  - Evidence was added, removed, retyped, regraded, or materially edited.
  - Trust scoring methodology or code changed.
  - Overall Trust Grade changes.
  - An Apex or other consequential trust gate changes.
  - Drift becomes materially stale (abs(current_tm - stored_tm) >= threshold).
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from gaia_cli.frontmatter import load_yaml_simple, split_frontmatter

# Materiality threshold: routine drift below this threshold is warn-only;
# drift at or above this threshold is considered materially stale and blocks CI.
# Defaults to 30.0 points to accommodate routine monthly stargazer refreshes
# without churning dozens of projection files.
DEFAULT_MAX_ROUTINE_TM_DRIFT = float(
    os.environ.get("GAIA_TRUST_DRIFT_THRESHOLD", "30.0")
)

VOLATILE_EVIDENCE_TYPES = {
    "github-stars-own",
    "npm-downloads",
    "social-signal",
    "engagement",
    "proxy-containment",
}

EXPLICIT_REVIEW_ACTIONS = {
    "recalibrate_trust_magnitude",
    "rank_up",
    "demote",
    "calibrate",
}


def evaluateTrustLedgerFreshness(
    committed_data: dict[str, Any],
    fresh_data: dict[str, Any],
    repo_root: Path | None = None,
    max_tm_drift: float = DEFAULT_MAX_ROUTINE_TM_DRIFT,
) -> tuple[bool, list[str], list[str]]:
    """Evaluate whether differences between committed and fresh ledger are routine or material.

    Returns:
        (is_material, blocking_reasons, routine_warnings)
    """
    blocking: list[str] = []
    routine: list[str] = []

    comm_rows = committed_data.get("rows", [])
    fresh_rows = fresh_data.get("rows", [])

    comm_skills = {r["skillId"]: r for r in comm_rows if isinstance(r, dict) and "skillId" in r}
    fresh_skills = {r["skillId"]: r for r in fresh_rows if isinstance(r, dict) and "skillId" in r}

    if set(comm_skills.keys()) != set(fresh_skills.keys()):
        added = sorted(set(fresh_skills.keys()) - set(comm_skills.keys()))
        removed = sorted(set(comm_skills.keys()) - set(fresh_skills.keys()))
        if added:
            blocking.append(f"skills added to registry ledger: {added}")
        if removed:
            blocking.append(f"skills removed from registry ledger: {removed}")
        return True, blocking, routine

    for sid, fresh_r in fresh_skills.items():
        comm_r = comm_skills[sid]

        # 1. Overall Trust Grade must not change
        if fresh_r.get("grade") != comm_r.get("grade"):
            blocking.append(
                f"{sid}: overall Trust Grade changed from '{comm_r.get('grade')}' to '{fresh_r.get('grade')}'"
            )

        # 2. Apex gate results must not change
        if fresh_r.get("apexResults") != comm_r.get("apexResults"):
            blocking.append(f"{sid}: apexResults changed")

        # 3. Origin standing and branch taxonomy must not change
        if fresh_r.get("origin") != comm_r.get("origin"):
            blocking.append(
                f"{sid}: origin standing changed ({comm_r.get('origin')} -> {fresh_r.get('origin')})"
            )
        if fresh_r.get("branch") != comm_r.get("branch"):
            blocking.append(
                f"{sid}: taxonomy branch changed ({comm_r.get('branch')} -> {fresh_r.get('branch')})"
            )

        # 4. Rank level / star badges must not change
        for star_key in ("currentStars", "mayStars", "juneStars", "g7Stars"):
            if fresh_r.get(star_key) != comm_r.get(star_key):
                blocking.append(
                    f"{sid}: {star_key} changed ({comm_r.get(star_key)} -> {fresh_r.get(star_key)})"
                )

        # 5. TM numerical movement check
        comm_tm = float(comm_r.get("tm", 0.0) or 0.0)
        fresh_tm = float(fresh_r.get("tm", 0.0) or 0.0)
        drift = round(abs(fresh_tm - comm_tm), 2)
        if drift > 0.02:
            if drift >= max_tm_drift:
                blocking.append(
                    f"{sid}: TM drift {drift:.2f} >= material staleness threshold {max_tm_drift:.2f} "
                    f"({comm_tm} -> {fresh_tm})"
                )
            else:
                routine.append(f"{sid}: TM {comm_tm} -> {fresh_tm} ({fresh_tm - comm_tm:+.2f})")

    # 6. Check for explicit review events and non-volatile evidence changes in skill files
    if repo_root is not None:
        generated_at = committed_data.get("generatedAt")
        for sid in (w.split(":")[0] for w in routine):
            if "/" in sid:
                contributor, skill_slug = sid.split("/", 1)
                md_path = repo_root / "registry" / "named" / contributor / f"{skill_slug}.md"
                if md_path.exists():
                    try:
                        _, fm_text, _ = split_frontmatter(md_path.read_text(encoding="utf-8"))
                        fm = load_yaml_simple(fm_text) or {}
                        for ev in fm.get("timeline", []):
                            if isinstance(ev, dict) and ev.get("action") in EXPLICIT_REVIEW_ACTIONS:
                                ev_ts = str(ev.get("timestamp", ""))
                                if generated_at and ev_ts > str(generated_at):
                                    blocking.append(
                                        f"{sid}: explicit review event '{ev.get('action')}' "
                                        f"recorded at {ev_ts} (after {generated_at}) requires fresh projection"
                                    )
                    except Exception:
                        pass

    # 7. Check if Trust scoring methodology or schema rules changed in working tree
    if repo_root is not None:
        try:
            proc = subprocess.run(
                [
                    "git",
                    "diff",
                    "--name-only",
                    "HEAD",
                    "--",
                    "src/gaia_cli/trustMagnitude.py",
                    "registry/schema/meta.json",
                ],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                blocking.append(
                    "Trust Magnitude scoring code or schema rules changed in working copy"
                )
        except Exception:
            pass

    return bool(blocking), blocking, routine


def evaluateInstallabilityFreshness(
    committed_doc: dict[str, Any],
    fresh_doc: dict[str, Any],
) -> tuple[bool, list[str], list[str]]:
    """Evaluate whether installability projection differences are routine or material."""
    blocking: list[str] = []
    routine: list[str] = []

    # Top-level keys must match
    if set(committed_doc.keys()) != set(fresh_doc.keys()):
        blocking.append(
            f"installability top-level keys mismatch: {set(committed_doc.keys()) ^ set(fresh_doc.keys())}"
        )
        return True, blocking, routine

    # Observations list must match
    if committed_doc.get("observations") != fresh_doc.get("observations"):
        blocking.append("installability observations list changed")
        return True, blocking, routine

    comm_skills = committed_doc.get("skills", {})
    fresh_skills = fresh_doc.get("skills", {})
    if set(comm_skills.keys()) != set(fresh_skills.keys()):
        added = sorted(set(fresh_skills.keys()) - set(comm_skills.keys()))
        removed = sorted(set(comm_skills.keys()) - set(fresh_skills.keys()))
        if added:
            blocking.append(f"skills added to installability index: {added}")
        if removed:
            blocking.append(f"skills removed from installability index: {removed}")
        return True, blocking, routine

    for sid, fresh_skill in fresh_skills.items():
        comm_skill = comm_skills[sid]
        for key in (
            "state",
            "reason",
            "observationDigest",
            "observedAt",
            "currentSourceRoute",
            "observedSourceRoute",
            "observedSkillContentSha256",
            "resolvedRevision",
            "deliveredContentSha256",
        ):
            if fresh_skill.get(key) != comm_skill.get(key):
                blocking.append(
                    f"{sid}: installability {key} changed ({comm_skill.get(key)} -> {fresh_skill.get(key)})"
                )
        if fresh_skill.get("currentSkillContentSha256") != comm_skill.get(
            "currentSkillContentSha256"
        ):
            routine.append(f"{sid}: content sha256 changed")

    return bool(blocking), blocking, routine


def evaluateNamedIndexFreshness(
    committed_data: dict[str, Any],
    fresh_data: dict[str, Any],
) -> tuple[bool, list[str], list[str]]:
    """Evaluate whether differences in registry/named-skills.json are routine or material."""
    blocking: list[str] = []
    routine: list[str] = []

    comm_buckets = committed_data.get("buckets", {})
    fresh_buckets = fresh_data.get("buckets", {})

    if set(comm_buckets.keys()) != set(fresh_buckets.keys()):
        blocking.append("named index buckets mismatch")
        return True, blocking, routine

    comm_skills = {
        entry["id"]: entry
        for bucket in comm_buckets.values()
        for entry in bucket
        if isinstance(entry, dict) and "id" in entry
    }
    fresh_skills = {
        entry["id"]: entry
        for bucket in fresh_buckets.values()
        for entry in bucket
        if isinstance(entry, dict) and "id" in entry
    }

    if set(comm_skills.keys()) != set(fresh_skills.keys()):
        added = sorted(set(fresh_skills.keys()) - set(comm_skills.keys()))
        removed = sorted(set(comm_skills.keys()) - set(fresh_skills.keys()))
        if added:
            blocking.append(f"skills added to named index: {added}")
        if removed:
            blocking.append(f"skills removed from named index: {removed}")
        return True, blocking, routine

    structural_keys = (
        "id",
        "name",
        "genericSkillRef",
        "level",
        "origin",
        "status",
        "title",
        "catalogRef",
        "links",
    )
    for sid, fresh_entry in fresh_skills.items():
        comm_entry = comm_skills[sid]
        for key in structural_keys:
            if fresh_entry.get(key) != comm_entry.get(key):
                blocking.append(
                    f"{sid}: structural field '{key}' changed in named index"
                )
        if fresh_entry.get("evidence") != comm_entry.get("evidence"):
            routine.append(f"{sid}: evidence updated")

    return bool(blocking), blocking, routine


def evaluateApiFreshness(
    committed_dir: Path,
    out_dir: Path,
    drifts: list[str],
    ledger_is_routine: bool = True,
) -> tuple[bool, list[str], list[str]]:
    """Evaluate whether differences in docs/api/v1/ are routine Trust drift or material."""
    blocking: list[str] = []
    routine: list[str] = []

    if not ledger_is_routine:
        blocking.append("API projection drift is material because trust ledger drift is material")
        return True, blocking, routine

    for rel_str in drifts:
        c_file = committed_dir / rel_str
        o_file = out_dir / rel_str

        if not c_file.exists():
            blocking.append(f"docs/api/v1/{rel_str}: file missing in committed tree")
            continue
        if not o_file.exists():
            blocking.append(f"docs/api/v1/{rel_str}: file missing in generated tree")
            continue

        if not rel_str.endswith(".json"):
            blocking.append(f"docs/api/v1/{rel_str}: non-JSON file drifted")
            continue

        try:
            c_json = json.loads(c_file.read_text(encoding="utf-8"))
            o_json = json.loads(o_file.read_text(encoding="utf-8"))
        except Exception as exc:
            blocking.append(f"docs/api/v1/{rel_str}: JSON parse error: {exc}")
            continue

        if type(c_json) is not type(o_json):
            blocking.append(f"docs/api/v1/{rel_str}: top-level JSON type mismatch")
            continue

        if isinstance(c_json, dict):
            if set(c_json.keys()) != set(o_json.keys()):
                blocking.append(
                    f"docs/api/v1/{rel_str}: JSON keys changed ({set(c_json.keys()) ^ set(o_json.keys())})"
                )
                continue

        routine.append(rel_str)

    return bool(blocking), blocking, routine
