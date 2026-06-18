"""Schema validation helpers for the Gaia registry.

Implements validators wired into `gaia validate` for the v2 inheritance
contract (§ Section H.2, G7_HANDOVER_DELTA_2026-06-17.md, ratified 2026-06-18).
"""

from __future__ import annotations

import json
import os
from typing import Any


# ---------------------------------------------------------------------------
# Evidence-layer allowedLayers validator
# ---------------------------------------------------------------------------

def load_type_layer_policy(registry_path: str = ".") -> dict[str, dict]:
    """Return {type_id: {"allowedLayers": [...], "inheritMultiplier": float|None}}
    from meta.json evidence.types[].

    Used by check_evidence_layer_policy(). Returns an empty dict if meta.json
    is missing or malformed so callers degrade gracefully.
    """
    meta_path = os.path.join(registry_path, "registry", "schema", "meta.json")
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        types = meta.get("evidence", {}).get("types", [])
        policy: dict[str, dict] = {}
        for entry in types:
            if not isinstance(entry, dict) or "id" not in entry:
                continue
            policy[entry["id"]] = {
                "allowedLayers": entry.get("allowedLayers", ["generic", "named"]),
                "inheritMultiplier": entry.get("inheritMultiplier"),
            }
        return policy
    except Exception:
        return {}


def check_evidence_layer_policy(
    skill: dict[str, Any],
    skill_layer: str,
    type_policy: dict[str, dict],
) -> list[dict]:
    """Check that every evidence row's effective layer is in its type's allowedLayers.

    Args:
        skill: A skill node dict (generic or named).
        skill_layer: "generic" or "named" -- the containing skill's layer. Used as
            the default when an evidence row has no explicit ``layer`` field.
        type_policy: Output of load_type_layer_policy().

    Returns:
        List of violation dicts. Each has keys:
            - error_code: "evidence-layer-not-allowed" (publish blocker)
            - skill_id: str
            - evidence_index: int
            - evidence_type: str
            - row_layer: str (effective layer of the row)
            - allowed_layers: list[str]
            - message: human-readable description

    # TODO (I3 partition-repair pass): pre-G7 rows lacking explicit `layer` are
    # assigned layer="named" conservatively (Section H.4). Post-I3, the migration
    # script emits explicit layer fields on every row so this fallback is only
    # needed during the transition window between I1 (schema) and I3 (migration).
    """
    violations: list[dict] = []
    evidence = skill.get("evidence") or []
    skill_id = skill.get("id", "<unknown>")

    for idx, row in enumerate(evidence):
        if not isinstance(row, dict):
            continue
        evidence_type = row.get("type")
        if not evidence_type or evidence_type not in type_policy:
            # Unknown type -- skip (separate validator handles unknown types).
            continue
        row_layer = row.get("layer", skill_layer)
        allowed = type_policy[evidence_type]["allowedLayers"]
        if row_layer not in allowed:
            violations.append({
                "error_code": "evidence-layer-not-allowed",
                "skill_id": skill_id,
                "evidence_index": idx,
                "evidence_type": evidence_type,
                "row_layer": row_layer,
                "allowed_layers": allowed,
                "message": (
                    f"Evidence row {idx} (type={evidence_type!r}) on skill {skill_id!r} "
                    f"has layer={row_layer!r} but type only allows {allowed}."
                ),
            })
    return violations
