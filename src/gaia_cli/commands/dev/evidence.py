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
    _preflight_duplicate_evidence_source,
    _preflight_benchmark_row,
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

    # Sprint D W2a (#904) — benchmark-result reproducibility fingerprint fields.
    # Emitted only when the CLI caller passed the corresponding flag; the
    # _preflight_benchmark_row helper below enforces that all 8 mandatory
    # fields are present when evidence_type == 'benchmark-result'.
    if getattr(args, "benchmark_id", None) is not None:
        evidence["benchmarkId"] = args.benchmark_id
    if getattr(args, "score", None) is not None:
        evidence["score"] = args.score
    if getattr(args, "unit", None) is not None:
        evidence["unit"] = args.unit
    if getattr(args, "run_at", None) is not None:
        evidence["runAt"] = args.run_at
    if getattr(args, "provenance", None) is not None:
        evidence["provenance"] = args.provenance
    if getattr(args, "attestor", None) is not None:
        evidence["attestor"] = args.attestor
    if getattr(args, "dataset_hash", None) is not None:
        evidence["datasetHash"] = args.dataset_hash
    if getattr(args, "benchmark_input_hash", None) is not None:
        evidence["benchmarkInputHash"] = args.benchmark_input_hash
    if getattr(args, "harness_url", None) is not None:
        evidence["harnessUrl"] = args.harness_url

    # CLI Pre-Flight (root CLAUDE.md §CLI Pre-Flight Rule) — refuse to write a
    # benchmark-result row that would fail schema validation at merge time.
    # Only fires for the append path (--index re-grades an existing row and
    # doesn't accept benchmark-fingerprint flags).
    if evidence_type == "benchmark-result" and index is None:
        _run_dev_preflights([lambda: _preflight_benchmark_row(evidence)])

    # Re-derive grade using per-type artifact_score thresholds (Issue #761).
    # This replaces the skill-aggregate TM threshold used above so grade pills
    # are meaningful per-row rather than all showing —.
    # Fallback: when no magnitude drivers are present (artifact_score == 0),
    # use the --trust value via aggregate thresholds to preserve backward compat.
    #
    # Sprint D W2a (#904): mirrored and pending benchmark-result rows short-
    # circuit here. They are citations only and MUST NOT be graded —
    # computeArtifactScoreOrNone returns None for them (excluded from TM),
    # but without this guard the fallback `derived_grade` branch below would
    # still stamp a grade based on --trust. Strip any grade the caller supplied.
    is_mirrored_or_pending_benchmark = (
        evidence_type == "benchmark-result"
        and evidence.get("provenance") in ("mirrored", "pending")
    )
    if is_mirrored_or_pending_benchmark:
        evidence.pop("grade", None)
    elif evidence_type is not None:
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

    def _apply(ev_list: list) -> tuple[dict, dict | None, bool, list[str]]:
        """Append the new entry, or update the entry at ``index`` in place.

        In-place mode only touches the fields explicitly supplied, preserving
        the existing entry's other fields (notably the deprecated ``class``,
        plus ``source`` unless a future CLI flag explicitly supports it).
        Returns the resulting entry, the pre-update entry (if any), whether the
        evidence row changed, and the changed field names for audit logging.
        """
        if index is None:
            ev_list.append(evidence)
            return evidence, None, True, list(evidence.keys())
        if index < 0 or index >= len(ev_list):
            print(
                f"Error: Evidence index {index} out of range "
                f"(skill '{skill_id}' has {len(ev_list)} entries).",
                file=sys.stderr,
            )
            sys.exit(1)
        entry = ev_list[index]
        before = json.loads(json.dumps(entry, sort_keys=True))
        if evidence_type is not None:
            entry["type"] = evidence_type
        if trust_number is not None:
            entry["trustNumber"] = trust_number
        if getattr(args, "notes", None) is not None:
            entry["notes"] = args.notes
        if getattr(args, "evaluator", None) is not None:
            entry["evaluator"] = args.evaluator
        if getattr(args, "date", None) is not None:
            entry["date"] = args.date
        # Numeric payload fields — also patchable via --index.
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

        # Re-derive grade after all patch fields are applied. This runs whenever
        # type, trust, or numeric payload changes — not just when --trust is supplied.
        #
        # Sprint D W2a (#904): as with the append path above, mirrored and pending
        # benchmark-result rows are stripped of any grade — they are citations only
        # and are excluded from Trust Magnitude entirely.
        row_type = entry.get("type")
        row_provenance = entry.get("provenance")
        if row_type == "benchmark-result" and row_provenance in ("mirrored", "pending"):
            entry.pop("grade", None)
        elif row_type is not None:
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
            # No type info — fall back to skill-aggregate threshold.
            if derived_grade is not None:
                entry["grade"] = derived_grade
            else:
                entry.pop("grade", None)

        changed_fields = sorted(
            set(before.keys()) | set(entry.keys()),
            key=lambda name: name.lower(),
        )
        changed_fields = [name for name in changed_fields if before.get(name) != entry.get(name)]
        return entry, before, bool(changed_fields), changed_fields

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
            lambda: _preflight_duplicate_evidence_source(skill_id, meta.get("evidence") or [], args.source),
        ])
        result_entry, before_entry, evidence_changed, changed_fields = _apply(meta.setdefault("evidence", []))
        if not evidence_changed:
            print(f"No evidence changes for {skill_id} entry #{index}.")
            return
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
            lambda: _preflight_duplicate_evidence_source(skill_id, data.get("evidence") or [], args.source),
        ])
        result_entry, before_entry, evidence_changed, changed_fields = _apply(data.setdefault("evidence", []))
        if not evidence_changed:
            print(f"No evidence changes for {skill_id} entry #{index}.")
            return
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
    verb = "Updated evidence entry" if index is not None else "Added evidence to skill"
    suffix = f" #{index}" if index is not None else ""
    print(f"{verb}{suffix}: {skill_id}{type_label} (grade: {grade_label})")

    contributor = _get_contributor()
    src = result_entry.get("source")
    if index is not None:
        previous_grade = (before_entry or {}).get("grade")
        previous_trust = (before_entry or {}).get("trustNumber")
        grade_changed = previous_grade != result_entry.get("grade")
        trust_changed = previous_trust != result_entry.get("trustNumber")
        changed_label = ", ".join(changed_fields) if changed_fields else "metadata"
        if trust_changed or grade_changed:
            detail = f"Updated evidence #{index} from {src}; changed {changed_label}"
            if grade_changed:
                detail += f" (grade: {previous_grade or 'ungraded'} → {grade_label})"
            if trust_changed:
                detail += f" (trustNumber: {previous_trust} → {result_entry.get('trustNumber')})"
        else:
            detail = f"Updated evidence #{index} metadata from {src}; changed {changed_label}"
        append_skill_event(
            skill_id,
            "evidence_graded",
            contributor,
            detail,
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
