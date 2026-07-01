import sys
import os
import json
import datetime
from pathlib import Path

from gaia_cli.registry import named_skills_dir, registry_nodes_dir
from gaia_cli.timeline import append_skill_event
from gaia_cli.commands.dev.helpers import (
    _find_named_file,
    _parse_md,
    _write_md,
    _is_verifier,
    _get_contributor,
    _run_docs_build,
    _run_dev_preflights,
    _preflight_verify_evidence,
)


def meta_verify_command(args):
    registry_path = args.registry
    skill_id = args.skill_id.lstrip("/")
    evidence_index = args.index
    is_dispute = getattr(args, "dispute", False)
    notes = getattr(args, "notes", None)
    v_source = getattr(args, "source", None)

    contributor = _get_contributor()
    if not _is_verifier(contributor, registry_path):
        print(f"Error: {contributor} is not a Verifier (no 4★+ skill found).")
        print(
            "Only contributors with at least one 4★ implementation can verify evidence."
        )
        sys.exit(1)

    # Defensive scan — surface any hostile content in the named-skill markdown
    # before the verifier signs off on an evidence claim.  This is read-only:
    # findings are printed but never block the verify action.
    try:
        from gaia_cli.securityScanner import (
            formatFindings,
            scanNamedSkillFiles,
        )

        named_dir_for_scan = Path(named_skills_dir(registry_path))
        scanTargets = []
        scanTarget = _find_named_file(named_dir_for_scan, skill_id)
        if scanTarget:
            scanTargets.append(str(scanTarget))
        if scanTargets:
            scanFindings = scanNamedSkillFiles(scanTargets)
            if scanFindings:
                print(formatFindings(scanFindings))
    except Exception as exc:  # pragma: no cover - defensive
        print(f"Security scanner skipped: {exc}")

    # 1. Check generic nodes
    nodes_dir = Path(registry_nodes_dir(registry_path))
    node_file = None
    skill_data = None
    for p in nodes_dir.glob("**/*.json"):
        with open(p, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                if data.get("id") == skill_id:
                    node_file = p
                    skill_data = data
                    break
            except json.JSONDecodeError:
                continue

    if node_file:
        evidence = skill_data.get("evidence", [])
        _run_dev_preflights([
            lambda: _preflight_verify_evidence(
                skill_id,
                evidence,
                evidence_index,
                is_dispute=is_dispute,
                source=v_source,
            ),
        ])

        ev = evidence[evidence_index]
        ev["verified"] = not is_dispute
        ev["disputed"] = is_dispute
        if notes:
            ev["notes"] = notes
        if v_source:
            ev["verificationSource"] = v_source

        skill_data["updatedAt"] = datetime.date.today().isoformat()
        with open(node_file, "w", encoding="utf-8") as f:
            json.dump(skill_data, f, indent=2, ensure_ascii=False)
            f.write("\n")

        action = "disputed" if is_dispute else "verified"
        print(
            f"{action.capitalize()} evidence index {evidence_index} for skill {skill_id}."
        )
        append_skill_event(
            skill_id,
            action,
            contributor,
            f"{action.capitalize()} evidence index {evidence_index} from {ev.get('source')}",
            registry_path=registry_path,
        )
    else:
        # 2. Check named skills
        named_dir = Path(named_skills_dir(registry_path))
        target_file = _find_named_file(named_dir, skill_id)
        if not target_file:
            print(f"Error: Skill '{skill_id}' not found.")
            sys.exit(1)

        meta, body = _parse_md(target_file)
        evidence = meta.get("evidence", [])
        _run_dev_preflights([
            lambda: _preflight_verify_evidence(
                skill_id,
                evidence,
                evidence_index,
                is_dispute=is_dispute,
                source=v_source,
            ),
        ])

        ev = evidence[evidence_index]
        ev["verified"] = not is_dispute
        ev["disputed"] = is_dispute
        if notes:
            ev["notes"] = notes
        if v_source:
            ev["verificationSource"] = v_source

        meta["updatedAt"] = datetime.date.today().isoformat()
        _write_md(target_file, meta, body)

        action = "disputed" if is_dispute else "verified"
        print(
            f"{action.capitalize()} evidence index {evidence_index} for named skill {skill_id}."
        )
        append_skill_event(
            skill_id,
            action,
            contributor,
            f"{action.capitalize()} evidence index {evidence_index} from {ev.get('source')}",
            registry_path=registry_path,
        )

    if not getattr(args, "no_build", False):
        print("Regenerating registry and documentation...")
        _run_docs_build(args.registry)


def _loadSkillForVerification(registry_path: str, skill_id: str):
    """Locate a skill's record + write-back closure for verification updates.

    Returns ``(record, writeback)`` where ``record`` is the in-memory dict
    (json node or YAML frontmatter) and ``writeback`` is a no-arg callable
    that persists the mutated ``record`` back to disk. Returns ``(None, None)``
    if the skill is not found.
    """
    if "/" in skill_id:
        named_dir = Path(named_skills_dir(registry_path))
        named_file = _find_named_file(named_dir, skill_id)
        if not named_file:
            return None, None
        meta, body = _parse_md(named_file)

        def writeNamed(captured_meta=meta, captured_body=body, captured_path=named_file):
            captured_meta["updatedAt"] = datetime.date.today().isoformat()
            _write_md(captured_path, captured_meta, captured_body)

        return meta, writeNamed

    nodes_dir = Path(registry_nodes_dir(registry_path))
    for p in nodes_dir.glob("**/*.json"):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("id") == skill_id:
            captured_path = p

            def writeGeneric(captured_data=data, p=captured_path):
                captured_data["updatedAt"] = datetime.date.today().isoformat()
                with open(p, "w", encoding="utf-8") as f:
                    json.dump(captured_data, f, indent=2, ensure_ascii=False)
                    f.write("\n")

            return data, writeGeneric
    return None, None


def meta_verify_tier_command(args):
    """Recompute and persist a skill's verification tier.

    Reads the skill's evidence list and timeline, evaluates the four tiers
    defined in ``gaia_cli.verification``, writes the resulting headline tier
    to ``record.verification.tier`` (with a fresh ``tierEvaluatedAt``), and
    prints the same pass/fail breakdown that ``gaia skills info`` surfaces.
    """
    from gaia_cli.verification import (
        filterScanEvents,
        resolveTier,
        utcNow,
    )

    registry_path = args.registry
    skill_id = args.skill_id.lstrip("/")

    record, writeback = _loadSkillForVerification(registry_path, skill_id)
    if record is None:
        print(f"Error: Skill '{skill_id}' not found.", file=sys.stderr)
        sys.exit(1)

    evidence = record.get("evidence") or []
    timeline = record.get("timeline") or []
    scanEvents = filterScanEvents(timeline)
    now = utcNow()

    highest, statusMap = resolveTier(record, evidence, scanEvents, now)

    verification = record.setdefault("verification", {})
    verification["tier"] = highest
    verification["tierEvaluatedAt"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    writeback()

    headline = highest if highest else "(none)"
    print(f"Verification: {headline}")
    # Print every tier so the operator sees the full breakdown.
    from gaia_cli.verification import TIER_ORDER

    for tier in reversed(TIER_ORDER):
        status = statusMap[tier]
        marker = "✓" if status["passed"] else "✗"
        print(f"  {marker} {tier} -- {status['reason']}")
