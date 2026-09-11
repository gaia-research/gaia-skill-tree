#!/usr/bin/env python3
"""Audit Disentanglement & Taxonomy Checker — ensure registry skills and audit
dispositions adhere to the Four-Tier Audit Taxonomy and anti-purge safeguards.

Class A detector (read-only, deterministic). Companion to check_product_attribution.py,
verify_evidence.py, and verify_lockstep.py. Never mutates the registry.

Taxonomy tiers (GOVERNANCE.md §4.2, CONTRIBUTING.md §12, META.md §2.4, RFC #1809):
    Tier 1 — Malicious / Imposter Squatter:
        Bad-faith aggregation, monorepo star hijacking, or falsified attribution.
        Action: Immediate expungement, blacklist.
    Tier 2 — Packaging / Install Shape Gap:
        Legitimate skill concept and author, but missing standard SKILL.md packaging
        upstream or circular/stale links.
        Action: Tag `installable: false` per CONTRIBUTING §12 (if <=2★). Retain in registry.
    Tier 3 — Early-Stage / Under-Evidenced Stub:
        Legitimate author, thin documentation or preliminary evidence.
        Action: Keep at baseline 1★ (Awakened), request doc enrichment, or tag `needs-info`.
        Do not purge.
    Tier 4 — Product-Coupled / Non-Generalized:
        Real tool documentation needing generalization or maker credit.
        Action: Route to generalization guidance per check_product_attribution.py.

Usage:
    python3 scripts/check_audit_disentanglement.py [--strict] [--output DIR]
    python3 scripts/check_audit_disentanglement.py --check-skill <contributor/skill>

Exit codes:
    0 — All checks pass (or --strict not set)
    1 — Invariant violations detected (only with --strict)
"""

import argparse
import glob
import json
import os
import sys
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Dict, List, Optional, Set

import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAMED_DIR = os.path.join(REPO_ROOT, "registry", "named")

# Known exempt self-hosted and prototype skills that are protected under Tier 2/3
KNOWN_EXEMPT_SKILLS = {
    "rico-favor/implement-with-discernment",
    "gaiabot/repo-docs-before-pr",
}

# Known core contributors / maintainers / team members subject to mandatory Contributor Check
KNOWN_CORE_CONTRIBUTORS: Set[str] = {
    "mbtiongson1",
    "rico-favor",
    "gaiabot",
    "gaia-research",
    "favorchurch",
}


class AuditTier(str, Enum):
    TIER_1_MALICIOUS = "Tier 1: Malicious / Imposter Squatter"
    TIER_2_PACKAGING_GAP = "Tier 2: Packaging / Install Shape Gap"
    TIER_3_UNDER_EVIDENCED = "Tier 3: Early-Stage / Under-Evidenced Stub"
    TIER_4_PRODUCT_COUPLED = "Tier 4: Product-Coupled / Non-Generalized"
    BENCHMARK_AUTHENTIC = "Authentic Production / Specialized Skill"


@dataclass
class DisentanglementResult:
    skill_id: str
    contributor: str
    level: str
    stars: int
    installable: Optional[bool]
    tier: str
    is_protected_exempt: bool
    contributor_check_required: bool
    status: str
    notes: str
    path: str


def parse_star(level_str: str) -> int:
    if not level_str:
        return 0
    clean = str(level_str).strip().replace("★", "").replace("*", "")
    try:
        return int(clean)
    except ValueError:
        return 0


def load_named_skills() -> Dict[str, dict]:
    named = {}
    for path in glob.glob(os.path.join(NAMED_DIR, "**", "*.md"), recursive=True):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if not content.startswith("---"):
            continue
        parts = content.split("---", 2)
        if len(parts) < 3:
            continue
        data = yaml.safe_load(parts[1])
        if not isinstance(data, dict) or "id" not in data:
            continue
        body = parts[2].strip()
        named[data["id"]] = {
            "meta": data,
            "body": body,
            "path": os.path.relpath(path, REPO_ROOT),
        }
    return named


def classify_audit_tier(
    skill_id: str,
    meta: dict,
    body: str,
    tool_maker_map: Optional[dict] = None,
) -> AuditTier:
    """Classify a skill into the Four-Tier Audit Taxonomy."""
    contributor = meta.get("contributor") or (skill_id.split("/")[0] if "/" in skill_id else "")
    stars = parse_star(meta.get("level", "0"))
    installable = meta.get("installable")
    links = meta.get("links", {}) or {}
    github_link = links.get("github", "") if isinstance(links, dict) else ""
    is_suite = bool(meta.get("suiteComponents"))
    suite_ref = meta.get("suiteRef")

    # Tier 4: Product-Coupled
    if tool_maker_map and skill_id in tool_maker_map:
        return AuditTier.TIER_4_PRODUCT_COUPLED

    # Tier 2: Packaging / Install Shape Gap
    # Skills marked installable: false, or lacking github link, or having circular link
    if installable is False or (not github_link and not is_suite and not suite_ref):
        return AuditTier.TIER_2_PACKAGING_GAP

    # Tier 3: Early-Stage / Under-Evidenced Stub
    # Baseline 1★ Awakened or thin placeholder body by authentic author
    if stars <= 1 or body in [
        "## Installation\nAdd installation instructions here.",
        "## Installation\n\nAdd installation instructions here.",
        "",
    ]:
        return AuditTier.TIER_3_UNDER_EVIDENCED

    return AuditTier.BENCHMARK_AUTHENTIC


def evaluate_skill(skill_id: str, item: dict, tool_maker_map: Optional[dict] = None) -> DisentanglementResult:
    meta = item["meta"]
    body = item["body"]
    contributor = meta.get("contributor") or (skill_id.split("/")[0] if "/" in skill_id else "")
    stars = parse_star(meta.get("level", "0"))
    installable = meta.get("installable")
    is_suite = bool(meta.get("suiteComponents"))
    suite_ref = meta.get("suiteRef")
    tier = classify_audit_tier(skill_id, meta, body, tool_maker_map)

    is_exempt = skill_id in KNOWN_EXEMPT_SKILLS
    contributor_check_required = contributor in KNOWN_CORE_CONTRIBUTORS

    violations = []
    # Invariant: installable: false non-suite skills must be <= 2★ per CONTRIBUTING §12
    if installable is False and stars > 2 and not is_suite and not suite_ref:
        violations.append(f"Declared installable: false at {stars}★ (Star Bar requires <= 2★ for registry-only)")

    status = "VIOLATION" if violations else "PASS"
    notes = "; ".join(violations) if violations else "Compliant with audit taxonomy"

    return DisentanglementResult(
        skill_id=skill_id,
        contributor=contributor,
        level=str(meta.get("level", "")),
        stars=stars,
        installable=installable,
        tier=tier.value,
        is_protected_exempt=is_exempt,
        contributor_check_required=contributor_check_required,
        status=status,
        notes=notes,
        path=item["path"],
    )


def run_audit() -> List[DisentanglementResult]:
    named = load_named_skills()

    # Attempt to import tool maker map for Tier 4 identification
    tool_maker_map = None
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from check_product_attribution import TOOL_MAKER_MAP
        tool_maker_map = TOOL_MAKER_MAP
    except Exception:
        pass

    results = []
    for skill_id, item in sorted(named.items()):
        res = evaluate_skill(skill_id, item, tool_maker_map)
        results.append(res)
    return results


def verify_exempt_skills_exist(results: List[DisentanglementResult]) -> List[str]:
    """Verify that all KNOWN_EXEMPT_SKILLS are present in the registry."""
    found_ids = {r.skill_id for r in results}
    missing = []
    for exempt_id in KNOWN_EXEMPT_SKILLS:
        if exempt_id not in found_ids:
            missing.append(f"Protected exempt skill '{exempt_id}' is missing from registry (improper purge)")
    return missing


def generate_report(results: List[DisentanglementResult], missing_exempt: List[str], output_dir: Optional[str]) -> dict:
    violations = [r for r in results if r.status == "VIOLATION"]
    tier_counts = {}
    for r in results:
        tier_counts[r.tier] = tier_counts.get(r.tier, 0) + 1

    report = {
        "checked": len(results),
        "violationsCount": len(violations) + len(missing_exempt),
        "violations": [asdict(v) for v in violations],
        "missingExemptSkills": missing_exempt,
        "tierBreakdown": tier_counts,
        "results": [asdict(r) for r in results],
    }

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, "audit-disentanglement.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"Wrote audit disentanglement report to {os.path.relpath(out_path, REPO_ROOT)}")

    print(f"Audit Disentanglement: Checked {report['checked']} named skill(s).")
    print(f"  Tier Breakdown:")
    for tier_name, count in sorted(tier_counts.items()):
        print(f"    - {tier_name}: {count}")

    if missing_exempt:
        print(f"❌ Missing protected exempt skills:")
        for m in missing_exempt:
            print(f"    - {m}")

    if violations:
        print(f"⚠️  {len(violations)} violation(s) detected:")
        for v in violations:
            print(f"    - {v.skill_id}: {v.notes} ({v.path})")
    elif not missing_exempt:
        print("✅ All skills and exempt prototypes conform to the Audit Disentanglement standards.")

    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="Exit 1 if any disentanglement violations found")
    parser.add_argument("--output", default=None, help="Directory to write audit-disentanglement.json report")
    parser.add_argument("--check-skill", default=None, help="Inspect audit classification for a single skill ID")
    args = parser.parse_args()

    results = run_audit()
    missing_exempt = verify_exempt_skills_exist(results)

    if args.check_skill:
        match = [r for r in results if r.skill_id == args.check_skill]
        if not match:
            print(f"Skill '{args.check_skill}' not found in registry.")
            sys.exit(1)
        res = match[0]
        print(json.dumps(asdict(res), indent=2))
        sys.exit(0)

    report = generate_report(results, missing_exempt, args.output)

    if args.strict and report["violationsCount"] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
