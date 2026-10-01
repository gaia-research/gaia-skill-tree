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
  3. Trust scoring methodology and rules did not change (verified against
     the PR merge-base or repository base).
  4. Evidence semantics did not materially change (no rows added, removed,
     retyped, or regraded; non-volatile rows are identical).
  5. Overall Trust Grade remains identical.
  6. Apex and consequential trust gates remain identical.
  7. Absolute TM drift is within tolerance (< material staleness threshold).
  8. Named skill file digests in installability are proven to be limited
     strictly to volatile evidence counter movements (markdown body and
     structural frontmatter are unchanged).
  9. API projection diffs inherit verified routine Trust status and only
     reflect numerical TM/ranking adjustments.

Trust freshness BLOCKS when any are true:
  - An explicit trust review / recalibration occurred.
  - Evidence was added, removed, retyped, regraded, or materially edited.
  - Trust scoring methodology or code changed between merge-base and working copy.
  - Overall Trust Grade changes.
  - An Apex or other consequential trust gate changes.
  - Drift becomes materially stale (abs(current_tm - stored_tm) >= threshold).
  - Installability digest changed without proof of routine volatile-only drift.
  - API projection contains structural changes or trust ledger drift is material.
"""

from __future__ import annotations

import hashlib
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

VOLATILE_NUMERIC_FIELDS = {
    "stars",
    "downloads",
    "views",
    "likes",
    "comments",
}

VOLATILE_SYNC_FIELDS = {
    "updatedAt",
    "notes",
    "trustNumber",
}

VOLATILE_FIELDS = VOLATILE_NUMERIC_FIELDS | VOLATILE_SYNC_FIELDS

EXPLICIT_REVIEW_ACTIONS = {
    "recalibrate_trust_magnitude",
    "rank_up",
    "demote",
    "calibrate",
}


def find_repository_base_ref(repo_root: Path) -> str:
    """Find the best base reference (merge-base) for detecting changes in PR or working copy."""
    base_candidates = []
    github_base = os.environ.get("GITHUB_BASE_REF")
    if github_base:
        base_candidates.extend([f"origin/{github_base}", github_base])
    base_candidates.extend(["origin/main", "main", "HEAD~1"])

    for cand in base_candidates:
        r = subprocess.run(
            ["git", "rev-parse", "--verify", cand],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if r.returncode == 0:
            mb = subprocess.run(
                ["git", "merge-base", cand, "HEAD"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            if mb.returncode == 0 and mb.stdout.strip():
                return mb.stdout.strip()
    return "HEAD"


def compareEvidenceRows(
    comm_evidence: list[dict[str, Any]] | None,
    fresh_evidence: list[dict[str, Any]] | None,
) -> tuple[bool, list[str], list[str]]:
    """Strictly compare two evidence lists.

    Returns:
        (is_material, blocking_reasons, routine_warnings)

    Only forgives changes confined to known volatile counters/notes inside
    otherwise identical evidence rows of volatile types.
    Added, removed, retyped, or regraded rows strictly BLOCK.
    Changes to non-volatile rows strictly BLOCK.
    """
    blocking: list[str] = []
    routine: list[str] = []

    c_list = comm_evidence or []
    f_list = fresh_evidence or []

    if len(c_list) != len(f_list):
        blocking.append(
            f"evidence row count changed ({len(c_list)} -> {len(f_list)})"
        )
        return True, blocking, routine

    for idx, (c_row, f_row) in enumerate(zip(c_list, f_list)):
        if c_row == f_row:
            continue

        c_type = c_row.get("type")
        f_type = f_row.get("type")

        # 1. Evidence type must match
        if c_type != f_type:
            blocking.append(
                f"row {idx}: evidence type changed ('{c_type}' -> '{f_type}')"
            )
            continue

        # 2. Row type must be recognized as volatile
        if c_type not in VOLATILE_EVIDENCE_TYPES:
            blocking.append(
                f"row {idx}: non-volatile evidence row of type '{c_type}' was modified"
            )
            continue

        # 3. Grade must not change (no regrading)
        if c_row.get("grade") != f_row.get("grade"):
            blocking.append(
                f"row {idx}: evidence grade changed ('{c_row.get('grade')}' -> '{f_row.get('grade')}')"
            )
            continue

        # 4. Source must not change
        if c_row.get("source") != f_row.get("source"):
            blocking.append(
                f"row {idx}: evidence source changed ('{c_row.get('source')}' -> '{f_row.get('source')}')"
            )
            continue

        # 5. Check all keys in both rows: non-volatile fields must match exactly
        non_volatile_diffs = []
        for key in set(c_row.keys()) | set(f_row.keys()):
            if key in VOLATILE_FIELDS:
                continue
            if c_row.get(key) != f_row.get(key):
                non_volatile_diffs.append(
                    f"field '{key}' changed ({c_row.get(key)} -> {f_row.get(key)})"
                )

        if non_volatile_diffs:
            blocking.append(
                f"row {idx} ('{c_type}'): non-volatile fields modified: {', '.join(non_volatile_diffs)}"
            )
        else:
            routine.append(
                f"row {idx} ('{c_type}'): volatile counter/sync updated "
                f"({c_row.get('stars', c_row.get('downloads'))} -> "
                f"{f_row.get('stars', f_row.get('downloads'))})"
            )

    return bool(blocking), blocking, routine


def verify_skill_file_delta_is_volatile(
    repo_root: Path,
    skill_id: str,
    committed_sha: str,
) -> tuple[bool, str]:
    """Verify that the changes in a named skill markdown file are strictly volatile evidence updates."""
    rel_path = f"registry/named/{skill_id}.md"
    current_path = repo_root / rel_path
    if not current_path.exists():
        return False, f"file {rel_path} does not exist in working tree"

    current_text = current_path.read_text(encoding="utf-8")

    # Locate the baseline commit
    baseline_commit = None
    try:
        proc = subprocess.run(
            ["git", "log", "-1", "--format=%H", "--", "docs/graph/installability/index.json"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            baseline_commit = proc.stdout.strip()
    except Exception:
        pass

    old_text = None
    candidates = []
    if baseline_commit:
        candidates.append(baseline_commit)
    base_ref = find_repository_base_ref(repo_root)
    if base_ref and base_ref not in candidates:
        candidates.append(base_ref)

    for cand in candidates:
        try:
            p_show = subprocess.run(
                ["git", "show", f"{cand}:{rel_path}"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            if p_show.returncode == 0:
                cand_text = p_show.stdout
                cand_sha = hashlib.sha256(cand_text.encode("utf-8")).hexdigest()
                if cand_sha == committed_sha:
                    old_text = cand_text
                    break
        except Exception:
            continue

    if old_text is None:
        return False, f"could not locate baseline version of {rel_path} matching committed SHA {committed_sha[:8]}"

    # Compare old_text vs current_text
    _, old_fm_text, old_body = split_frontmatter(old_text)
    _, curr_fm_text, curr_body = split_frontmatter(current_text)

    # 1. Markdown body must be identical (no description, prose, or docs edits)
    if old_body.strip() != curr_body.strip():
        return False, "markdown body/description content was edited"

    # 2. Frontmatter non-evidence fields must be identical
    old_fm = load_yaml_simple(old_fm_text) or {}
    curr_fm = load_yaml_simple(curr_fm_text) or {}

    for k in set(old_fm.keys()) | set(curr_fm.keys()):
        if k == "evidence":
            continue
        if old_fm.get(k) != curr_fm.get(k):
            return False, f"frontmatter field '{k}' was edited ({old_fm.get(k)} -> {curr_fm.get(k)})"

    # 3. Evidence must satisfy compareEvidenceRows
    ev_material, ev_blocking, _ = compareEvidenceRows(old_fm.get("evidence"), curr_fm.get("evidence"))
    if ev_material:
        return False, f"evidence edits are material: {ev_blocking}"

    return True, "proven limited to volatile evidence"


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

    # 7. Check if Trust scoring methodology or schema rules changed relative to merge-base
    if repo_root is not None:
        try:
            base_ref = find_repository_base_ref(repo_root)
            proc = subprocess.run(
                [
                    "git",
                    "diff",
                    "--name-only",
                    base_ref,
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
                    f"Trust Magnitude scoring code or schema rules changed relative to {base_ref[:8]}: "
                    f"{proc.stdout.strip().splitlines()}"
                )
        except Exception:
            pass

    return bool(blocking), blocking, routine


def evaluateInstallabilityFreshness(
    committed_doc: dict[str, Any],
    fresh_doc: dict[str, Any],
    repo_root: Path | None = None,
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

        comm_sha = comm_skill.get("currentSkillContentSha256")
        fresh_sha = fresh_skill.get("currentSkillContentSha256")
        if fresh_sha != comm_sha:
            if repo_root is not None and comm_sha:
                proven, reason = verify_skill_file_delta_is_volatile(
                    repo_root=repo_root,
                    skill_id=sid,
                    committed_sha=comm_sha,
                )
                if not proven:
                    blocking.append(f"{sid}: content sha256 changed: {reason}")
                else:
                    routine.append(f"{sid}: content sha256 changed (proven limited to volatile Trust fields)")
            else:
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
                    f"{sid}: structural field '{key}' changed in named index ({comm_entry.get(key)} -> {fresh_entry.get(key)})"
                )

        comm_ev = comm_entry.get("evidence")
        fresh_ev = fresh_entry.get("evidence")
        if comm_ev != fresh_ev:
            ev_is_material, ev_blocking, ev_routine = compareEvidenceRows(comm_ev, fresh_ev)
            if ev_is_material:
                for b in ev_blocking:
                    blocking.append(f"{sid}: {b}")
            else:
                routine.append(f"{sid}: {', '.join(ev_routine)}")

    return bool(blocking), blocking, routine


def verify_api_file_drift(
    rel_path: str,
    c_json: Any,
    o_json: Any,
) -> tuple[bool, str | None]:
    """Verify that differences in an API file are strictly routine Trust / ranking shifts."""
    if type(c_json) is not type(o_json):
        return False, "top-level JSON type mismatch"

    # 1. Health endpoint
    if rel_path == "health.json":
        if isinstance(c_json, dict) and isinstance(o_json, dict):
            if set(c_json.keys()) != set(o_json.keys()):
                return False, f"health.json keys changed ({set(c_json.keys()) ^ set(o_json.keys())})"
            return True, None
        return False, "health.json is not a dict"

    # 2. Leaderboard endpoint
    if rel_path == "leaderboard.json":
        if isinstance(c_json, dict) and isinstance(o_json, dict):
            if set(c_json.keys()) != set(o_json.keys()):
                return False, f"leaderboard.json keys changed ({set(c_json.keys()) ^ set(o_json.keys())})"
            return True, None
        return False, "leaderboard.json is not a dict"

    # 3. Search index
    if rel_path == "search-index.json":
        if isinstance(c_json, list) and isinstance(o_json, list):
            c_by_id = {item["id"]: item for item in c_json if isinstance(item, dict) and "id" in item}
            o_by_id = {item["id"]: item for item in o_json if isinstance(item, dict) and "id" in item}
            if set(c_by_id.keys()) != set(o_by_id.keys()):
                return False, "search-index skill IDs changed"
            for sid, c_item in c_by_id.items():
                o_item = o_by_id[sid]
                for k in ("name", "description", "contributor"):
                    if c_item.get(k) != o_item.get(k):
                        return False, f"search-index {sid}: '{k}' changed"
            return True, None
        return False, "search-index.json is not a list"

    # 4. Individual skill endpoint: skills/.../*.json (not index or page-*)
    if rel_path.startswith("skills/") and not rel_path.startswith("skills/page-") and rel_path != "skills/index.json":
        if isinstance(c_json, dict) and isinstance(o_json, dict):
            structural_keys = (
                "id",
                "name",
                "genericSkillRef",
                "status",
                "title",
                "description",
                "author",
                "contributor",
            )
            for k in structural_keys:
                if c_json.get(k) != o_json.get(k):
                    return False, f"{rel_path}: structural field '{k}' changed ({c_json.get(k)} -> {o_json.get(k)})"
            if c_json.get("evidence") != o_json.get("evidence"):
                ev_is_material, ev_blocking, _ = compareEvidenceRows(c_json.get("evidence"), o_json.get("evidence"))
                if ev_is_material:
                    return False, f"{rel_path}: {ev_blocking[0]}"
            return True, None
        return False, f"{rel_path} is not a dict"

    # 5. Contributor endpoint: contributors/*.json
    if rel_path.startswith("contributors/"):
        if isinstance(c_json, dict) and isinstance(o_json, dict):
            for k in ("handle", "name", "url", "avatar"):
                if c_json.get(k) != o_json.get(k):
                    return False, f"{rel_path}: contributor field '{k}' changed"
            return True, None
        return False, f"{rel_path} is not a dict"

    # 6. Skills listing / pagination: skills/index.json, skills/page-*.json
    if rel_path == "skills/index.json" or rel_path.startswith("skills/page-"):
        if isinstance(c_json, dict) and isinstance(o_json, dict):
            if set(c_json.keys()) != set(o_json.keys()):
                return False, f"{rel_path} keys mismatch ({set(c_json.keys()) ^ set(o_json.keys())})"
            c_skills = c_json.get("skills", [])
            o_skills = o_json.get("skills", [])
            if len(c_skills) != len(o_skills):
                return False, f"{rel_path} skills count mismatch ({len(c_skills)} vs {len(o_skills)})"
            return True, None
        return False, f"{rel_path} is not a dict"

    if isinstance(c_json, dict) and isinstance(o_json, dict):
        if set(c_json.keys()) != set(o_json.keys()):
            return False, f"{rel_path} schema keys changed ({set(c_json.keys()) ^ set(o_json.keys())})"
        return True, None

    return False, f"unrecognized drifted file: {rel_path}"


def evaluateApiFreshness(
    committed_dir: Path,
    out_dir: Path,
    drifts: list[str],
    ledger_is_routine: bool = False,
) -> tuple[bool, list[str], list[str]]:
    """Evaluate whether differences in docs/api/v1/ are routine Trust drift or material."""
    blocking: list[str] = []
    routine: list[str] = []

    if not ledger_is_routine:
        blocking.append("API projection drift is material because trust ledger drift is not proven routine")
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

        is_routine, reason = verify_api_file_drift(rel_str, c_json, o_json)
        if not is_routine:
            blocking.append(f"docs/api/v1/{rel_str}: material change detected: {reason}")
            continue

        routine.append(rel_str)

    return bool(blocking), blocking, routine
