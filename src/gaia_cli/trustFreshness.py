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
     reflect numerical TM/ranking adjustments: every changed leaf is proven
     Trust-derived (trustMagnitude, prestigeScore, per-type typeBreakdown
     contributions, volatile counters inside volatile evidence rows) or a
     reorder of a ranking list with unchanged membership. Same-shape JSON is
     not sufficient; grade, level, gate, distribution, fusion and static
     endpoint changes block.

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

    # 6. Explicit Trust review/recalibration is independently material.
    # Do not scope this to skills that also happened to move numerically: a review
    # should require a fresh projection even when TM stays identical after review.
    if repo_root is not None:
        generated_at = committed_data.get("generatedAt")
        if generated_at:
            for sid in fresh_skills:
                if "/" not in sid:
                    continue
                contributor, skill_slug = sid.split("/", 1)
                md_path = repo_root / "registry" / "named" / contributor / f"{skill_slug}.md"
                if not md_path.exists():
                    continue
                try:
                    _, fm_text, _ = split_frontmatter(md_path.read_text(encoding="utf-8"))
                    fm = load_yaml_simple(fm_text) or {}
                    for ev in fm.get("timeline", []):
                        if not isinstance(ev, dict) or ev.get("action") not in EXPLICIT_REVIEW_ACTIONS:
                            continue
                        ev_ts = str(ev.get("timestamp", ""))
                        if ev_ts and ev_ts > str(generated_at):
                            blocking.append(
                                f"{sid}: explicit review event '{ev.get('action')}' "
                                f"recorded at {ev_ts} (after {generated_at}) requires fresh projection"
                            )
                            break
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
                blocking.append(
                    f"{sid}: content sha256 changed but volatile-only provenance could not be verified"
                )

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


# Leaf keys whose value is a pure function of Trust Magnitude (numeric only).
# A routine adoption-counter refresh may move these and nothing else.
API_TRUST_DERIVED_NUMERIC_KEYS = {
    "trustMagnitude",
    "prestigeScore",
}

# Subtrees whose numeric leaves are per-type TM contributions. Their key set
# (which evidence types are present) must stay identical.
API_TRUST_DERIVED_NUMERIC_SUBTREES = {
    "typeBreakdown",
}

# Keys that identify a member of a ranking-ordered list. Lists whose items are
# all keyed by one of these may reorder (TM ranking), but membership is fixed.
API_RANKING_IDENTITY_KEYS = ("id", "handle")

# Volatile health metadata (release stamp / generation timestamp).
API_HEALTH_VOLATILE_KEYS = {"version", "registryGeneratedAt"}


def isNumber(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def rankingKey(items: list[Any]) -> str | None:
    if not items or not all(isinstance(item, dict) for item in items):
        return None
    for key in API_RANKING_IDENTITY_KEYS:
        values = [item.get(key) for item in items]
        if all(isinstance(v, str) and v for v in values) and len(set(values)) == len(values):
            return key
    return None


def trustOnlyDiff(comm: Any, fresh: Any, path: str) -> str | None:
    """Return the first non-Trust-derived difference between two JSON values.

    ``None`` means every difference is proven to be a Trust/ranking-derived
    value: a numeric change under an allowlisted key, a numeric per-type TM
    contribution, a volatile counter inside an otherwise identical volatile
    evidence row, or a reorder of a ranking list whose membership is unchanged.
    Anything else (new/removed keys, type changes, string/bool changes, grade
    or gate changes, membership changes) is reported as material.
    """
    if comm == fresh:
        return None
    if isinstance(comm, dict) and isinstance(fresh, dict):
        if set(comm.keys()) != set(fresh.keys()):
            return f"{path or '<root>'}: keys changed ({sorted(set(comm.keys()) ^ set(fresh.keys()))})"
        for key in comm:
            cv, fv = comm[key], fresh[key]
            if cv == fv:
                continue
            sub = f"{path}.{key}" if path else key
            if key in API_TRUST_DERIVED_NUMERIC_KEYS and isNumber(cv) and isNumber(fv):
                continue
            if key in API_TRUST_DERIVED_NUMERIC_SUBTREES:
                if not (isinstance(cv, dict) and isinstance(fv, dict)):
                    return f"{sub}: not a mapping"
                if set(cv.keys()) != set(fv.keys()):
                    return f"{sub}: evidence types changed ({sorted(set(cv.keys()) ^ set(fv.keys()))})"
                for tkey in cv:
                    if cv[tkey] != fv[tkey] and not (isNumber(cv[tkey]) and isNumber(fv[tkey])):
                        return f"{sub}.{tkey}: non-numeric change"
                continue
            if key == "evidence" and isinstance(cv, list) and isinstance(fv, list):
                ev_is_material, ev_blocking, _ = compareEvidenceRows(cv, fv)
                if ev_is_material:
                    return f"{sub}: {ev_blocking[0]}"
                continue
            reason = trustOnlyDiff(cv, fv, sub)
            if reason:
                return reason
        return None
    if isinstance(comm, list) and isinstance(fresh, list):
        key = rankingKey(comm)
        if key is not None and rankingKey(fresh) == key:
            c_by = {item[key]: item for item in comm}
            f_by = {item[key]: item for item in fresh}
            if set(c_by) != set(f_by):
                return f"{path or '<root>'}: ranking membership changed ({sorted(set(c_by) ^ set(f_by))})"
            for ident, c_item in c_by.items():
                reason = trustOnlyDiff(c_item, f_by[ident], f"{path}[{ident}]")
                if reason:
                    return reason
            return None
        if len(comm) != len(fresh):
            return f"{path or '<root>'}: list length changed ({len(comm)} -> {len(fresh)})"
        for idx, (cv, fv) in enumerate(zip(comm, fresh)):
            reason = trustOnlyDiff(cv, fv, f"{path}[{idx}]")
            if reason:
                return reason
        return None
    return f"{path or '<root>'}: value changed ({comm!r} -> {fresh!r})"


def topSkillIsRankingDerived(top: Any, skills: list[Any]) -> bool:
    """A moved ``topSkill`` is routine only if it is the TM-max member of ``skills``."""
    if not isinstance(top, dict) or not skills:
        return False
    by_id = {s.get("id"): s for s in skills if isinstance(s, dict)}
    member = by_id.get(top.get("id"))
    if member is None:
        return False
    if member.get("level") != top.get("level") or member.get("trustMagnitude") != top.get("trustMagnitude"):
        return False
    best = max((s.get("trustMagnitude", 0) for s in by_id.values()), default=0)
    return top.get("trustMagnitude") == best


def contributorSkills(generated_root: Path | None, handle: Any) -> list[Any]:
    if generated_root is None or not isinstance(handle, str) or "/" in handle or not handle:
        return []
    detail = generated_root / "contributors" / f"{handle}.json"
    try:
        data = json.loads(detail.read_text(encoding="utf-8"))
    except Exception:
        return []
    skills = data.get("namedSkills") if isinstance(data, dict) else None
    return skills if isinstance(skills, list) else []


def withoutTopSkill(entry: Any) -> Any:
    if isinstance(entry, dict):
        return {k: v for k, v in entry.items() if k != "topSkill"}
    return entry


def verify_api_file_drift(
    rel_path: str,
    c_json: Any,
    o_json: Any,
    generated_root: Path | None = None,
    page_collection_proven: bool = False,
) -> tuple[bool, str | None]:
    """Verify that differences in an API file are strictly routine Trust / ranking shifts.

    Every changed value must be proven Trust/ranking-derived (see
    ``trustOnlyDiff``); same-shape JSON is no longer sufficient. Files with no
    Trust-derived content (``evidence-types.json``, ``openapi.json``, …) therefore
    block on any change. ``generated_root`` lets contributor files prove a moved
    ``topSkill`` against the generated per-contributor skill list; without it a
    moved ``topSkill`` in ``contributors/index.json`` fails closed.
    """
    if type(c_json) is not type(o_json):
        return False, "top-level JSON type mismatch"

    # 1. Health endpoint: only the release stamp / generation timestamp may move.
    if rel_path == "health.json":
        if isinstance(c_json, dict) and isinstance(o_json, dict):
            if set(c_json.keys()) != set(o_json.keys()):
                return False, f"health.json keys changed ({set(c_json.keys()) ^ set(o_json.keys())})"
            for k in c_json:
                if k not in API_HEALTH_VOLATILE_KEYS and c_json[k] != o_json[k]:
                    return False, f"health.json: '{k}' changed ({c_json[k]!r} -> {o_json[k]!r})"
            return True, None
        return False, "health.json is not a dict"

    # 2. Leaderboard: distribution (grade/flag counts) is gate-bearing and must be
    #    identical; rows may reorder and move only TM / typeBreakdown values.
    if rel_path == "leaderboard.json":
        if isinstance(c_json, dict) and isinstance(o_json, dict):
            if set(c_json.keys()) != set(o_json.keys()):
                return False, f"leaderboard.json keys changed ({set(c_json.keys()) ^ set(o_json.keys())})"
            if c_json.get("distribution") != o_json.get("distribution"):
                return False, "leaderboard.json: distribution (grade / rank-floor / implied-promotion counts) changed"
            reason = trustOnlyDiff(c_json, o_json, "")
            if reason:
                return False, f"leaderboard.json {reason}"
            return True, None
        return False, "leaderboard.json is not a dict"

    # 3. Search index: keyed by id; name/description/contributor/tokens/grade fixed.
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
            reason = trustOnlyDiff(c_json, o_json, "")
            if reason:
                return False, f"search-index {reason}"
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
            reason = trustOnlyDiff(c_json, o_json, "")
            if reason:
                return False, f"{rel_path}: {reason}"
            return True, None
        return False, f"{rel_path} is not a dict"

    # 5. Contributor endpoints: contributors/index.json and contributors/<handle>.json
    if rel_path.startswith("contributors/"):
        if isinstance(c_json, dict) and isinstance(o_json, dict):
            if rel_path == "contributors/index.json":
                c_rows = c_json.get("contributors")
                o_rows = o_json.get("contributors")
                if isinstance(c_rows, list) and isinstance(o_rows, list):
                    c_by = {r.get("handle"): r for r in c_rows if isinstance(r, dict)}
                    o_by = {r.get("handle"): r for r in o_rows if isinstance(r, dict)}
                    for handle, c_row in c_by.items():
                        o_row = o_by.get(handle)
                        if o_row is None or c_row.get("topSkill") == o_row.get("topSkill"):
                            continue
                        if not topSkillIsRankingDerived(
                            o_row.get("topSkill"), contributorSkills(generated_root, handle)
                        ):
                            return False, f"{rel_path}: topSkill for '{handle}' changed without ranking proof"
                    c_cmp = dict(c_json, contributors=[withoutTopSkill(r) for r in c_rows])
                    o_cmp = dict(o_json, contributors=[withoutTopSkill(r) for r in o_rows])
                    reason = trustOnlyDiff(c_cmp, o_cmp, "")
                    if reason:
                        return False, f"{rel_path}: {reason}"
                    return True, None
                return False, f"{rel_path}: contributors list missing"
            for k in ("handle", "name", "url", "avatar"):
                if c_json.get(k) != o_json.get(k):
                    return False, f"{rel_path}: contributor field '{k}' changed"
            if c_json.get("topSkill") != o_json.get("topSkill") and not topSkillIsRankingDerived(
                o_json.get("topSkill"), o_json.get("namedSkills") or []
            ):
                return False, f"{rel_path}: topSkill changed without ranking proof"
            reason = trustOnlyDiff(withoutTopSkill(c_json), withoutTopSkill(o_json), "")
            if reason:
                return False, f"{rel_path}: {reason}"
            return True, None
        return False, f"{rel_path} is not a dict"

    # 6. Skills listing / pagination: skills/index.json, skills/page-*.json.
    #    Page membership can legitimately shift when TM re-ranks skills, so
    #    membership is proven across the whole page collection by
    #    ``evaluateApiFreshness``; here the envelope must be identical and the
    #    page's own entries must differ only in Trust-derived values.
    if rel_path == "skills/index.json" or rel_path.startswith("skills/page-"):
        if isinstance(c_json, dict) and isinstance(o_json, dict):
            if set(c_json.keys()) != set(o_json.keys()):
                return False, f"{rel_path} keys mismatch ({set(c_json.keys()) ^ set(o_json.keys())})"
            c_skills = c_json.get("skills", [])
            o_skills = o_json.get("skills", [])
            if len(c_skills) != len(o_skills):
                return False, f"{rel_path} skills count mismatch ({len(c_skills)} vs {len(o_skills)})"
            for k in c_json:
                if k != "skills" and c_json[k] != o_json[k]:
                    return False, f"{rel_path}: page envelope '{k}' changed"
            if page_collection_proven:
                return True, None
            reason = trustOnlyDiff(c_skills, o_skills, "skills")
            if reason:
                return False, f"{rel_path}: {reason}"
            return True, None
        return False, f"{rel_path} is not a dict"

    # 7. Anything else: no same-shape pass. Every changed value must be proven
    #    Trust/ranking-derived, so static endpoints block on any change.
    if isinstance(c_json, (dict, list)):
        reason = trustOnlyDiff(c_json, o_json, "")
        if reason:
            return False, f"{rel_path}: {reason}"
        return True, None

    return False, f"unrecognized drifted file: {rel_path}"


def skillsPageCollection(root: Path) -> tuple[list[Any], list[str]] | None:
    skills_dir = root / "skills"
    names = ["index.json"] + sorted(
        (p.name for p in skills_dir.glob("page-*.json")),
        key=lambda n: int(n[len("page-"):-len(".json")]) if n[len("page-"):-len(".json")].isdigit() else 0,
    )
    entries: list[Any] = []
    for name in names:
        path = skills_dir / name
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        if not isinstance(data, dict) or not isinstance(data.get("skills"), list):
            return None
        entries.extend(data["skills"])
    return entries, names


def verifySkillsPageCollection(committed_dir: Path, out_dir: Path) -> str | None:
    """Prove a cross-page re-ranking: same membership, Trust-only value changes."""
    comm = skillsPageCollection(committed_dir)
    fresh = skillsPageCollection(out_dir)
    if comm is None or fresh is None:
        return "skills page collection unreadable"
    if comm[1] != fresh[1]:
        return f"skills page set changed ({comm[1]} -> {fresh[1]})"
    return trustOnlyDiff(comm[0], fresh[0], "skills[*]")


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

    page_drifts = {
        d for d in drifts if d == "skills/index.json" or d.startswith("skills/page-")
    }
    page_collection_reason: str | None = None
    if page_drifts:
        page_collection_reason = verifySkillsPageCollection(committed_dir, out_dir)

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

        if rel_str in page_drifts and page_collection_reason is not None:
            blocking.append(
                f"docs/api/v1/{rel_str}: material change detected: {page_collection_reason}"
            )
            continue

        is_routine, reason = verify_api_file_drift(
            rel_str,
            c_json,
            o_json,
            generated_root=out_dir,
            page_collection_proven=rel_str in page_drifts,
        )
        if not is_routine:
            blocking.append(f"docs/api/v1/{rel_str}: material change detected: {reason}")
            continue

        routine.append(rel_str)

    return bool(blocking), blocking, routine
