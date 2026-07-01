import sys
import datetime
import json
import os
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
    _run_dev_preflights,
    _preflight_evidence_static,
    _preflight_evidence_index_bounds,
)


def _preflight_benchmark_percentile(args) -> None:
    """Backward-compatible wrapper for the shared evidence preflight."""
    _run_dev_preflights([
        lambda: _preflight_evidence_static(args, ("benchmark-result", "repo-own")),
    ])


def meta_evidence_command(args):
    """Attach evidence to a generic ref (capability, inherited) or a named skill.

    A bare id (``research``) targets the generic skill ref — capability-level
    evidence that every named implementation inherits. A ``contributor/skill``
    id targets that specific named implementation (e.g. its GitHub repo demo).
    """
    from gaia_cli.grading import derive_grade, load_grade_thresholds, load_evidence_types, load_per_row_grade_thresholds, derive_row_grade

    registry_path = args.registry
    skill_id = args.skill_id.lstrip("/")

    # --trust + --type are the canonical interface.
    trust_number = getattr(args, "trust", None)
    evidence_type = getattr(args, "evidence_type", None)

    valid_types = load_evidence_types(registry_path)
    _run_dev_preflights([
        lambda: _preflight_evidence_static(args, valid_types),
    ])

    source_started_at = getattr(args, "source_started_at", None)

    # Derive grade from trust number (legacy fallback used when no type+artifact info available)
    derived_grade: str | None = None
    if trust_number is not None:
        thresholds = load_grade_thresholds(registry_path)
        derived_grade = derive_grade(trust_number, thresholds)

    # --index re-grades an existing entry in place (class→grade backfill);
    # otherwise a new entry is appended.
    index = getattr(args, "index", None)

    evidence: dict = {
        "source": args.source,
        "evaluator": getattr(args, "evaluator", None) or _get_contributor(),
        "date": getattr(args, "date", None) or datetime.date.today().isoformat(),
    }
    # Write new fields
    if evidence_type is not None:
        evidence["type"] = evidence_type
    if trust_number is not None:
        evidence["trustNumber"] = trust_number
    if derived_grade is not None:
        evidence["grade"] = derived_grade
    if getattr(args, "notes", None):
        evidence["notes"] = args.notes
    # Numeric payload fields (type-specific magnitude drivers)
    if getattr(args, "stars", None) is not None:
        evidence["stars"] = args.stars
    if getattr(args, "views", None) is not None:
        evidence["views"] = args.views
    if getattr(args, "citations", None) is not None:
        evidence["citations"] = args.citations
    if getattr(args, "reviewers", None) is not None:
        evidence["reviewers"] = args.reviewers
    if getattr(args, "commits", None) is not None:
        evidence["commits"] = args.commits
    if getattr(args, "contributors", None) is not None:
        evidence["contributors"] = args.contributors
    if getattr(args, "skill_count_in_repo", None) is not None:
        evidence["skillCountInRepo"] = args.skill_count_in_repo
    if getattr(args, "percentile", None) is not None:
        evidence["percentile"] = args.percentile
    if source_started_at is not None:
        evidence["sourceStartedAt"] = source_started_at

    # Re-derive grade using per-type artifact_score thresholds (Issue #761).
    # This replaces the skill-aggregate TM threshold used above so grade pills
    # are meaningful per-row rather than all showing "—".
    # Fallback: when no magnitude drivers are present (artifact_score == 0),
    # use the --trust value via aggregate thresholds to preserve backward compat.
    if evidence_type is not None:
        from gaia_cli.trustMagnitude import computeArtifactScoreOrNone
        from gaia_cli.grading import load_evidence_types_full
        per_row_thresholds = load_per_row_grade_thresholds(registry_path)
        artifact_score = computeArtifactScoreOrNone(evidence) or 0.0
        ev_types_full = load_evidence_types_full(registry_path)
        ceiling = next(
            (t.get("gradeCeiling") for t in ev_types_full if t.get("id") == evidence_type),
            None,
        )
        if artifact_score > 0.0:
            row_grade = derive_row_grade(artifact_score, evidence_type, per_row_thresholds, ceiling)
            if row_grade is not None:
                evidence["grade"] = row_grade
            elif "grade" in evidence:
                del evidence["grade"]
        elif derived_grade is not None:
            # No magnitude drivers — fall back to trustNumber-derived grade
            evidence["grade"] = derived_grade
        else:
            evidence.pop("grade", None)

    def _apply(ev_list: list) -> dict:
        """Append the new entry, or update the entry at ``index`` in place.

        In-place mode only touches the fields explicitly supplied, preserving
        the existing entry's other fields (notably the deprecated ``class``,
        plus ``evaluator``/``date``/``source``). Returns the resulting entry.
        """
        if index is None:
            ev_list.append(evidence)
            return evidence
        if index < 0 or index >= len(ev_list):
            print(
                f"Error: Evidence index {index} out of range "
                f"(skill '{skill_id}' has {len(ev_list)} entries).",
                file=sys.stderr,
            )
            sys.exit(1)
        entry = ev_list[index]
        if evidence_type is not None:
            entry["type"] = evidence_type
        if trust_number is not None:
            entry["trustNumber"] = trust_number
        # Re-derive grade using per-type artifact_score thresholds (Issue #761).
        # Runs whenever type or any numeric payload changes — not just when --trust supplied.
        row_type = entry.get("type")
        if row_type is not None:
            from gaia_cli.trustMagnitude import computeArtifactScoreOrNone
            from gaia_cli.grading import load_evidence_types_full
            per_row_thresholds = load_per_row_grade_thresholds(registry_path)
            artifact_score = computeArtifactScoreOrNone(entry) or 0.0
            ev_types_full = load_evidence_types_full(registry_path)
            ceiling = next(
                (t.get("gradeCeiling") for t in ev_types_full if t.get("id") == row_type),
                None,
            )
            new_row_grade = derive_row_grade(artifact_score, row_type, per_row_thresholds, ceiling)
            if new_row_grade is not None:
                entry["grade"] = new_row_grade
            elif artifact_score == 0.0 and derived_grade is not None:
                # No magnitude drivers (e.g. arxiv with no citations) — fall back
                # to the trustNumber-derived aggregate grade so an explicit --trust
                # value is still reflected in the entry.
                entry["grade"] = derived_grade
            else:
                entry.pop("grade", None)
        elif trust_number is not None:
            # No type info — fall back to skill-aggregate threshold
            if derived_grade is not None:
                entry["grade"] = derived_grade
            else:
                entry.pop("grade", None)
        if getattr(args, "notes", None):
            entry["notes"] = args.notes
        if getattr(args, "evaluator", None):
            entry["evaluator"] = args.evaluator
        if getattr(args, "date", None):
            entry["date"] = args.date
        # Numeric payload fields — also patchable via --index
        if getattr(args, "stars", None) is not None:
            entry["stars"] = args.stars
        if getattr(args, "views", None) is not None:
            entry["views"] = args.views
        if getattr(args, "citations", None) is not None:
            entry["citations"] = args.citations
        if getattr(args, "reviewers", None) is not None:
            entry["reviewers"] = args.reviewers
        if getattr(args, "commits", None) is not None:
            entry["commits"] = args.commits
        if getattr(args, "contributors", None) is not None:
            entry["contributors"] = args.contributors
        if getattr(args, "skill_count_in_repo", None) is not None:
            entry["skillCountInRepo"] = args.skill_count_in_repo
        if getattr(args, "percentile", None) is not None:
            entry["percentile"] = args.percentile
        if source_started_at is not None:
            entry["sourceStartedAt"] = source_started_at
        return entry

    if "/" in skill_id:
        # Named implementation → write into the named .md frontmatter.
        named_dir = Path(named_skills_dir(registry_path))
        named_file = _find_named_file(named_dir, skill_id)
        if not named_file:
            print(f"Error: Named skill '{skill_id}' not found.")
            sys.exit(1)
        meta, body = _parse_md(named_file)
        _run_dev_preflights([
            lambda: _preflight_evidence_index_bounds(skill_id, meta.get("evidence") or [], index),
        ])
        result_entry = _apply(meta.setdefault("evidence", []))
        # Stamp tenure baseline on the first evidence-add only.
        if index is None:
            from gaia_cli.verification import stampFirstEvidenceAt

            stampFirstEvidenceAt(meta)
        meta["updatedAt"] = datetime.date.today().isoformat()
        _write_md(named_file, meta, body)
    else:
        nodes_dir = Path(registry_nodes_dir(registry_path))
        node_file = None
        for p in nodes_dir.glob("**/*.json"):
            with open(p, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    if data.get("id") == skill_id:
                        node_file = p
                        break
                except json.JSONDecodeError:
                    continue

        if not node_file:
            print(f"Error: Skill '{skill_id}' not found.")
            sys.exit(1)

        with open(node_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        _run_dev_preflights([
            lambda: _preflight_evidence_index_bounds(skill_id, data.get("evidence") or [], index),
        ])
        result_entry = _apply(data.setdefault("evidence", []))
        # Stamp tenure baseline on the first evidence-add only.
        if index is None:
            from gaia_cli.verification import stampFirstEvidenceAt

            stampFirstEvidenceAt(data)
        data["updatedAt"] = datetime.date.today().isoformat()
        with open(node_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")

    grade_label = result_entry.get("grade") or "ungraded"
    type_label = f" [{result_entry.get('type')}]" if result_entry.get("type") else ""
    verb = "Re-graded evidence entry" if index is not None else "Added evidence to skill"
    suffix = f" #{index}" if index is not None else ""
    print(f"{verb}{suffix}: {skill_id}{type_label} (grade: {grade_label})")

    contributor = _get_contributor()
    src = result_entry.get("source")
    if index is not None:
        # In-place re-grade: a single evidence_graded event captures the change,
        # fired whenever a trust number was supplied (graded or ungraded) so the
        # backfill always leaves an audit trail.
        if trust_number is not None:
            append_skill_event(
                skill_id,
                "evidence_graded",
                contributor,
                f"Re-graded evidence from {src} as {grade_label} "
                f"(trustNumber: {trust_number})",
                registry_path=registry_path,
            )
    else:
        append_skill_event(
            skill_id,
            "evidence_added",
            contributor,
            f"Added evidence from {src}"
            + (f" (type: {evidence_type})" if evidence_type else ""),
            registry_path=registry_path,
        )
        # Fire evidence_graded whenever a grade was derived from a trust number
        if derived_grade is not None:
            append_skill_event(
                skill_id,
                "evidence_graded",
                contributor,
                f"Graded evidence from {src} as {derived_grade} "
                f"(trustNumber: {trust_number})",
                registry_path=registry_path,
            )

    if not getattr(args, "no_build", False):
        print("Regenerating registry and documentation...")
        _run_docs_build(args.registry)
    else:
        print("Skipping documentation rebuild as requested (--no-build).")


def meta_rm_evidence_command(args):
    """Remove an evidence entry from a generic ref or a named skill.

    Identify the entry by ``--index N`` (its position in the evidence array) or
    by ``--source URL`` (exact match; removes every entry with that source).
    Use this to strip dead / broken evidence links flagged by the liveness
    checker. A bare id targets the generic node; ``contributor/skill`` targets
    the named markdown frontmatter.
    """
    registry_path = args.registry
    skill_id = args.skill_id.lstrip("/")

    _confirm_destructive(
        f"Remove evidence from '{skill_id}'? This cannot be undone.",
        args,
    )
    index = getattr(args, "index", None)
    source = getattr(args, "source", None)
    if index is None and not source:
        print("Error: provide --index N or --source URL to identify the evidence entry.")
        sys.exit(1)

    def _filter(evlist):
        evlist = evlist or []
        if index is not None:
            if index < 0 or index >= len(evlist):
                print(f"Error: evidence index {index} out of range (0..{len(evlist) - 1}).")
                sys.exit(1)
            removed = [evlist[index]]
            kept = [e for i, e in enumerate(evlist) if i != index]
        else:
            removed = [e for e in evlist if e.get("source") == source]
            kept = [e for e in evlist if e.get("source") != source]
        return kept, removed

    if "/" in skill_id:
        named_dir = Path(named_skills_dir(registry_path))
        named_file = _find_named_file(named_dir, skill_id)
        if not named_file:
            print(f"Error: Named skill '{skill_id}' not found.")
            sys.exit(1)
        meta, body = _parse_md(named_file)
        kept, removed = _filter(meta.get("evidence", []))
        if not removed:
            print(f"No matching evidence on '{skill_id}'.")
            return
        meta["evidence"] = kept
        meta["updatedAt"] = datetime.date.today().isoformat()
        _write_md(named_file, meta, body)
    else:
        nodes_dir = Path(registry_nodes_dir(registry_path))
        node_file = None
        for p in nodes_dir.glob("**/*.json"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                continue
            if data.get("id") == skill_id:
                node_file = p
                break
        if not node_file:
            print(f"Error: Skill '{skill_id}' not found.")
            sys.exit(1)
        with open(node_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        kept, removed = _filter(data.get("evidence", []))
        if not removed:
            print(f"No matching evidence on '{skill_id}'.")
            return
        data["evidence"] = kept
        data["updatedAt"] = datetime.date.today().isoformat()
        with open(node_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")

    srcs = ", ".join(e.get("source", "?") for e in removed)
    plural = "entry" if len(removed) == 1 else "entries"
    print(f"Removed {len(removed)} evidence {plural} from {skill_id}: {srcs}")
    append_skill_event(
        skill_id,
        "evidence_removed",
        _get_contributor(),
        f"Removed dead/invalid evidence: {srcs}",
        registry_path=registry_path,
    )

    if not getattr(args, "no_build", False):
        print("Regenerating registry and documentation...")
        _run_docs_build(args.registry)
    else:
        print("Skipping documentation rebuild as requested (--no-build).")
