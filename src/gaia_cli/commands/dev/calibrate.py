import os
import json
import sys
import datetime
from pathlib import Path

from gaia_cli.registry import named_skills_dir, registry_nodes_dir
from gaia_cli.timeline import append_skill_event
from gaia_cli.commands.dev.helpers import (
    _find_named_file,
    _parse_md,
    _write_md,
    _get_contributor,
    _run_docs_build,
    _confirm_destructive,
)


def _preflight_starbar(skill_data: dict, level: str) -> None:
    """Reject calibrations to 3★+ when the skill lacks a verified blob URL.

    Per META.md §2.4 "Star Bar": a named skill at 3★ or above must have a
    verified `links.github` pointing to a `blob/` URL. Without it the skill
    is uninstallable and fails the Star Bar gate.

    Raises SystemExit(1) if the invariant is violated.
    """
    three_star_plus = {"3★", "4★", "5★", "6★"}
    if level not in three_star_plus:
        return
    github_url = (skill_data.get("links") or {}).get("github", "")
    if not github_url or "/blob/" not in github_url:
        print(
            f"Error: Cannot calibrate to {level} — `links.github` is missing or not a "
            f"`blob/` URL. The Star Bar (META.md §2.4) requires a verified GitHub blob URL "
            f"for 3★+ skills.\n"
            f"  Current value: {github_url!r}\n"
            f"  Fix: `gaia dev update-named <skill> --github-link "
            f"https://github.com/<owner>/<repo>/blob/<branch>/<path-to-skill>`",
            file=sys.stderr,
        )
        sys.exit(1)


def meta_calibrate_command(args):
    registry_path = args.registry
    skill_id = args.skill_id.lstrip("/")
    level = args.level

    # Stars live only on named skills now. Calibrate operates on a named
    # implementation (contributor/skill), not a rank-less generic ref.
    ALLOWED_LEVELS = ["1★", "2★", "3★", "4★", "5★", "6★"]
    if level not in ALLOWED_LEVELS:
        print(f"Error: Named skill level must be one of: {', '.join(ALLOWED_LEVELS)}")
        sys.exit(1)

    if "/" not in skill_id:
        print(
            f"Error: '{skill_id}' is a generic skill reference, which is rank-less. "
            f"Calibrate a named implementation instead, e.g. "
            f"'gaia dev calibrate contributor/{skill_id} {level}'."
        )
        sys.exit(1)

    named_dir = Path(named_skills_dir(registry_path))
    node_file = _find_named_file(named_dir, skill_id)
    if not node_file:
        print(f"Error: Named skill '{skill_id}' not found.")
        sys.exit(1)

    skill_data, body = _parse_md(node_file)
    _preflight_starbar(skill_data, level)
    old_level = skill_data.get("level", "2★")
    skill_data["level"] = level
    skill_data["updatedAt"] = datetime.date.today().isoformat()
    _write_md(node_file, skill_data, body)

    level_num = ALLOWED_LEVELS.index(level)
    old_level_num = (
        ALLOWED_LEVELS.index(old_level) if old_level in ALLOWED_LEVELS else 0
    )
    action = "rank_up" if level_num > old_level_num else "demote"

    append_skill_event(
        skill_id,
        action,
        _get_contributor(),
        f"Calibrated level from {old_level} to {level}",
        registry_path=registry_path,
    )

    if not getattr(args, "no_build", False):
        print("Regenerating registry and documentation...")
        _run_docs_build(args.registry)
    else:
        print("Skipping documentation rebuild as requested (--no-build).")
    print(f"Successfully calibrated '{skill_id}' to {level}.")


def calibrate_evidence_grades_command(args):
    """Backfill per-row grade fields using per-type artifact_score thresholds.

    Iterates all generic node JSON files and named skill .md frontmatter,
    computing each evidence row's artifact_score and writing the correct grade.
    Auto-derived rows (_autoDerived: True) are skipped.
    """
    from gaia_cli.grading import load_per_row_grade_thresholds, derive_row_grade
    from gaia_cli.trustMagnitude import computeRowArtifactScores, computeArtifactScoreOrNone

    registry_path = args.registry
    dry_run = getattr(args, "dry_run", False)
    target_skill = getattr(args, "skill", None)
    scope = getattr(args, "scope", "all")

    per_row_thresholds = load_per_row_grade_thresholds(registry_path)
    if not per_row_thresholds:
        print("Error: perRowGradeThresholds not found in meta.json. Cannot proceed.", file=sys.stderr)
        sys.exit(1)

    if not dry_run:
        _confirm_destructive(
            f"Backfill evidence grades across all {scope} skills? This rewrites grade fields in-place.",
            args,
        )

    meta_path = os.path.join(registry_path, "registry", "schema", "meta.json")
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta_json = json.load(f)
    except Exception as e:
        print(f"Error: cannot read meta.json: {e}", file=sys.stderr)
        sys.exit(1)
    grade_ceiling_map = {}
    for ev_type in meta_json.get("evidence", {}).get("types", []):
        if isinstance(ev_type, dict) and "id" in ev_type and "gradeCeiling" in ev_type:
            grade_ceiling_map[ev_type["id"]] = ev_type["gradeCeiling"]

    nodes_dir = Path(registry_nodes_dir(registry_path))
    generic_skill_map = {}
    if nodes_dir.exists():
        for node_file in nodes_dir.rglob("*.json"):
            try:
                with open(node_file, "r", encoding="utf-8") as f:
                    skill = json.load(f)
                sid = skill.get("id")
                if sid:
                    generic_skill_map[sid] = skill
            except Exception:
                pass

    total_updated = 0
    total_skipped = 0
    total_errors = 0

    def _process_evidence_list(ev_list, skill_dict, label):
        nonlocal total_updated, total_skipped, total_errors
        changed = False
        rows_with_scores = computeRowArtifactScores(skill_dict, generic_skill_map)
        score_map = {}
        for row, score in rows_with_scores:
            if row.get("_autoDerived"):
                continue
            key = (row.get("type"), row.get("source"))
            score_map[key] = score

        for row in ev_list:
            if row.get("_autoDerived"):
                total_skipped += 1
                continue
            ev_type_raw = row.get("type")
            if not ev_type_raw:
                total_skipped += 1
                continue
            # Normalize legacy aliases: "repo" → "repo-own", "github-stars" → "github-stars-own"
            _ALIASES = {"repo": "repo-own", "github-stars": "github-stars-own"}
            ev_type = _ALIASES.get(ev_type_raw, ev_type_raw)
            source = row.get("source")
            score = score_map.get((ev_type_raw, source))
            if score is None:
                score_raw = computeArtifactScoreOrNone(row, generic_skill_map)
                score = 0.0 if score_raw is None else score_raw
            # Fallback: if magnitude drivers absent but trustNumber was supplied,
            # use trustNumber directly as the artifact_score proxy so existing
            # rows aren't left permanently ungraded (backward compat, Issue #761).
            # NOTE: trustNumber may be stale from before formula changes; prefer
            # adding metric fields (stars/citations/commits) to retire it.
            if score == 0.0 and row.get("trustNumber"):
                score = float(row["trustNumber"])
            ceiling = grade_ceiling_map.get(ev_type)
            new_grade = derive_row_grade(score, ev_type, per_row_thresholds, ceiling)
            old_grade = row.get("grade")
            if new_grade != old_grade:
                if not dry_run:
                    if new_grade is None:
                        row.pop("grade", None)
                    else:
                        row["grade"] = new_grade
                old_str = old_grade or "—"
                new_str = new_grade or "—"
                print(f"  {label} [{ev_type}] {source}: {old_str} → {new_str}")
                total_updated += 1
                changed = True
            else:
                total_skipped += 1
        return changed

    if scope in ("all", "generic") and nodes_dir.exists():
        for node_file in nodes_dir.rglob("*.json"):
            try:
                with open(node_file, "r", encoding="utf-8") as f:
                    skill = json.load(f)
                sid = skill.get("id")
                if target_skill and sid != target_skill:
                    continue
                ev_list = skill.get("evidence") or []
                if not ev_list:
                    continue
                changed = _process_evidence_list(ev_list, skill, sid or str(node_file.stem))
                if changed and not dry_run:
                    skill["updatedAt"] = datetime.date.today().isoformat()
                    with open(node_file, "w", encoding="utf-8") as f:
                        json.dump(skill, f, indent=2, ensure_ascii=False)
                        f.write("\n")
            except Exception as e:
                print(f"  Error processing {node_file}: {e}", file=sys.stderr)
                total_errors += 1

    if scope in ("all", "named"):
        named_dir = Path(named_skills_dir(registry_path))
        if named_dir.exists():
            for md_file in named_dir.rglob("*.md"):
                try:
                    meta_fm, body = _parse_md(md_file)
                    skill_id_nm = meta_fm.get("genericSkillRef") or meta_fm.get("id")
                    if target_skill:
                        named_id = meta_fm.get("id") or ""
                        if named_id != target_skill and skill_id_nm != target_skill:
                            continue
                    ev_list = meta_fm.get("evidence") or []
                    if not ev_list:
                        continue
                    parent_skill = generic_skill_map.get(skill_id_nm, {}) if skill_id_nm else {}
                    merged = dict(parent_skill)
                    merged["evidence"] = ev_list
                    changed = _process_evidence_list(ev_list, merged, str(md_file.stem))
                    if changed and not dry_run:
                        meta_fm["updatedAt"] = datetime.date.today().isoformat()
                        _write_md(md_file, meta_fm, body)
                except Exception as e:
                    print(f"  Error processing {md_file}: {e}", file=sys.stderr)
                    total_errors += 1

    mode = "[DRY RUN] " if dry_run else ""
    print(f"\n{mode}calibrate-evidence-grades complete: "
          f"{total_updated} updated, {total_skipped} unchanged, {total_errors} errors")

    if not dry_run and not getattr(args, "no_build", False):
        print("Regenerating registry and documentation...")
        _run_docs_build(registry_path)
    elif getattr(args, "no_build", False):
        print("Skipping documentation rebuild as requested (--no-build).")
