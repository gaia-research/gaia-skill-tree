"""Grade derivation and trust aggregation for the evidence grading pipeline.

Implements the trust-number → letter-grade mapping defined in registry/schema/meta.json
evidence.gradeThresholds, and the Overall Trust Grade aggregation / ultimate gate logic.
"""

from __future__ import annotations

import json
import os

_GRADE_ORDER = ["S", "A", "B", "C"]
# G7 Trust Magnitude floors (S≥250, A≥100, B≥50, C≥20). The legacy trustNumber
# thresholds (S≥90, A≥80, B≥60, C≥40) shipped with this file before the G7 cutover;
# they're now wrong because the trustNumber aggregate was replaced by Trust Magnitude
# (unbounded, set-bonus driven). The single source of truth is meta.json
# evidence.gradeThresholds; these defaults exist only as a last-resort fallback when
# meta.json is missing entirely (e.g. lib import outside a registry checkout).
_DEFAULT_THRESHOLDS = {"S": 250, "A": 100, "B": 50, "C": 20}
_DEFAULT_ULTIMATE_GATE = {
    "minEvidencedComponents": 3,
    "requiredComponentGrades": {"S": 1, "A": 2},
    "componentFloor": "C",
}


def _load_meta_evidence(registry_path=".") -> dict:
    meta_path = os.path.join(registry_path, "registry", "schema", "meta.json")
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f).get("evidence", {})
    except Exception:
        return {}


def load_grade_thresholds(registry_path=".") -> dict:
    """Return grade thresholds from meta.json, falling back to defaults."""
    return _load_meta_evidence(registry_path).get("gradeThresholds", _DEFAULT_THRESHOLDS)


def load_ultimate_gate(registry_path=".") -> dict:
    """Return ultimate gate config from meta.json, falling back to defaults."""
    return _load_meta_evidence(registry_path).get("ultimateGate", _DEFAULT_ULTIMATE_GATE)


def load_evidence_types(registry_path=".") -> list[str]:
    """Return valid evidence type IDs from meta.json.

    Handles both formats transparently:
    - Legacy format: ["arxiv", "repo", "github-stars"]  (list of strings)
    - G7 format:     [{"id": "arxiv", "magnitude": "...", ...}, ...]  (list of objects)

    Always returns a list of plain string IDs so call sites can do
    ``evidence_type in load_evidence_types()`` regardless of schema version.
    """
    raw = _load_meta_evidence(registry_path).get("types", ["arxiv", "repo", "github-stars"])
    if raw and isinstance(raw[0], dict):
        return [entry["id"] for entry in raw if "id" in entry]
    return list(raw)


def load_evidence_types_full(registry_path=".") -> list[dict]:
    """Return the full evidence type objects from meta.json (not just IDs).

    Unlike load_evidence_types() which normalises to strings, this returns the
    raw list of type dicts so callers can read allowedLayers, inheritMultiplier,
    and other per-type fields introduced by the v2 inheritance contract
    (Section H.2, G7_HANDOVER_DELTA_2026-06-17.md, ratified 2026-06-18).
    Falls back to an empty list if meta.json is missing.
    """
    raw = _load_meta_evidence(registry_path).get("types", [])
    if raw and isinstance(raw[0], dict):
        return list(raw)
    # Legacy string format -- wrap in minimal dicts so callers can iterate safely.
    return [{"id": t} for t in raw]


def derive_grade(trust_number: float | int, thresholds: dict | None = None) -> str | None:
    """Map a Trust Magnitude value to a grade letter (S/A/B/C) or None (ungraded).

    Thresholds are inclusive lower bounds (G7 RFC, ratified 2026-06-18):
      S ≥ 250, A ≥ 100, B ≥ 50, C ≥ 20, < 20 → None (ungraded).

    The ``trust_number`` parameter name is preserved for backward compatibility with
    callers that haven't migrated yet, but the value is now expected to be a Trust
    Magnitude (unbounded float), not the legacy bounded trustNumber.
    """
    if thresholds is None:
        thresholds = _DEFAULT_THRESHOLDS
    t = float(trust_number)
    for grade in _GRADE_ORDER:
        if t >= thresholds.get(grade, _DEFAULT_THRESHOLDS[grade]):
            return grade
    return None


def overall_trust_grade(
    evidence_list: list,
    skill: dict | None = None,
    legacy: bool = False,
    generic_skill_map: dict | None = None,
) -> str | None:
    """Return the Overall Trust Grade for a skill.

    With ``legacy=True`` (or when ``skill`` is None and only an evidence list
    is supplied), returns the highest Evidence Grade across all graded entries
    using the pre-G7 MAX-based reader. This path is preserved for callers that
    have not migrated to the Trust Magnitude formula.

    With ``legacy=False`` and a ``skill`` dict, computes the new G7 Overall
    Trust Grade from Trust Magnitude + diversity gate (RFC §3, §4) via the
    ``trustMagnitude`` module. Returns None when the skill is ungraded.
    """
    if not legacy and skill is not None:
        from .trustMagnitude import computeOverallTrustGradeFromSkill

        result = computeOverallTrustGradeFromSkill(skill, generic_skill_map)
        if result == "ungraded":
            return None
        return result

    best: str | None = None
    for entry in evidence_list or []:
        g = entry.get("grade")
        if g not in _GRADE_ORDER:
            continue
        if best is None or _GRADE_ORDER.index(g) < _GRADE_ORDER.index(best):
            best = g
    return best


def _component_grade(skill: dict) -> str | None:
    """Highest grade among a component skill's evidence entries."""
    return overall_trust_grade(skill.get("evidence") or [])


def check_ultimate_gate(
    skill: dict,
    generic_skills_map: dict,
    gate_config: dict | None = None,
) -> dict:
    """Evaluate the ultimate gate for a skill.

    For suite ultimates (has ``suiteComponents``): pillar rule from gate_config.
    For non-suite ultimates: direct-evidence equivalent (≥3 sources, ≥1 S, ≥2 A).

    Args:
        skill: The skill dict (from gaia.json or a node file).
        generic_skills_map: {skill_id: skill_dict} for looking up component evidence.
        gate_config: From meta.json.evidence.ultimateGate; uses defaults if None.

    Returns dict with keys: passes (bool), reason (str), details (dict).
    """
    if gate_config is None:
        gate_config = _DEFAULT_ULTIMATE_GATE

    floor = gate_config.get("componentFloor", "C")
    floor_idx = _GRADE_ORDER.index(floor) if floor in _GRADE_ORDER else len(_GRADE_ORDER) - 1
    min_evidenced = gate_config.get("minEvidencedComponents", 3)
    required_grades: dict = gate_config.get("requiredComponentGrades", {"S": 1, "A": 2})

    components = skill.get("suiteComponents") or []

    if components:
        # Suite ultimate: check component grades
        evidenced_components = []
        for cid in components:
            comp = generic_skills_map.get(cid)
            if comp is None:
                continue
            g = _component_grade(comp)
            if g is not None:
                evidenced_components.append((cid, g))

        details: dict = {
            "mode": "suite",
            "evidencedComponents": len(evidenced_components),
            "minEvidencedComponents": min_evidenced,
            "gradeCounts": {},
            "componentFloor": floor,
        }

        if len(evidenced_components) < min_evidenced:
            return {
                "passes": False,
                "reason": f"only {len(evidenced_components)}/{min_evidenced} components carry graded evidence",
                "details": details,
            }

        # Check floor — none may be below C
        below_floor = [(cid, g) for cid, g in evidenced_components if _GRADE_ORDER.index(g) > floor_idx]
        if below_floor:
            details["belowFloor"] = [cid for cid, _ in below_floor]
            return {
                "passes": False,
                "reason": f"component(s) below floor {floor}: {[cid for cid, _ in below_floor]}",
                "details": details,
            }

        grade_counts: dict[str, int] = {}
        for _, g in evidenced_components:
            grade_counts[g] = grade_counts.get(g, 0) + 1
        details["gradeCounts"] = grade_counts

        for req_grade, req_count in required_grades.items():
            actual = sum(
                cnt for g, cnt in grade_counts.items()
                if g in _GRADE_ORDER and _GRADE_ORDER.index(g) <= _GRADE_ORDER.index(req_grade)
            )
            if actual < req_count:
                return {
                    "passes": False,
                    "reason": f"need ≥{req_count} component(s) graded {req_grade}+, have {actual}",
                    "details": details,
                }

        return {"passes": True, "reason": "all pillars satisfied", "details": details}

    else:
        # Non-suite ultimate: direct evidence equivalent
        evidence = skill.get("evidence") or []
        graded = [e for e in evidence if e.get("grade") in _GRADE_ORDER]
        details = {
            "mode": "direct",
            "gradedSources": len(graded),
            "minSources": min_evidenced,
        }

        if len(graded) < min_evidenced:
            return {
                "passes": False,
                "reason": f"only {len(graded)}/{min_evidenced} graded evidence sources",
                "details": details,
            }

        grade_counts = {}
        for e in graded:
            g = e["grade"]
            grade_counts[g] = grade_counts.get(g, 0) + 1
        details["gradeCounts"] = grade_counts

        for req_grade, req_count in required_grades.items():
            actual = sum(
                cnt for g, cnt in grade_counts.items()
                if g in _GRADE_ORDER and _GRADE_ORDER.index(g) <= _GRADE_ORDER.index(req_grade)
            )
            if actual < req_count:
                return {
                    "passes": False,
                    "reason": f"need ≥{req_count} graded source(s) at {req_grade}+, have {actual}",
                    "details": details,
                }

        return {"passes": True, "reason": "direct evidence gate satisfied", "details": details}
