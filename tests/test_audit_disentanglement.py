from dataclasses import asdict
import os
import textwrap
import pytest

from scripts import check_audit_disentanglement as cad


def _write_named_skill(named_dir, contributor, slug, skill_id, body, level="1★", installable=None, links=None):
    contributor_dir = os.path.join(named_dir, contributor)
    os.makedirs(contributor_dir, exist_ok=True)
    
    installable_str = f"installable: {str(installable).lower()}\n" if installable is not None else ""
    links_str = ""
    if links:
        links_str = "links:\n"
        for k, v in links.items():
            links_str += f"  {k}: {v}\n"

    header = textwrap.dedent(f"""\
        ---
        id: {skill_id}
        name: Test Skill
        contributor: {contributor}
        level: {level}
        {installable_str}{links_str}---
        """)
    content = header + body + "\n"
    path = os.path.join(contributor_dir, f"{slug}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def test_classify_tier_2_packaging_gap():
    meta = {
        "id": "rico-favor/test-skill",
        "contributor": "rico-favor",
        "level": "1★",
        "installable": False,
    }
    tier = cad.classify_audit_tier("rico-favor/test-skill", meta, "## Overview\nValid body")
    assert tier == cad.AuditTier.TIER_2_PACKAGING_GAP


def test_classify_tier_3_early_stage_stub():
    meta = {
        "id": "alice/early-prototype",
        "contributor": "alice",
        "level": "1★",
        "links": {"github": "https://github.com/alice/repo/blob/main/SKILL.md"},
    }
    tier = cad.classify_audit_tier("alice/early-prototype", meta, "## Installation\nAdd installation instructions here.")
    assert tier == cad.AuditTier.TIER_3_UNDER_EVIDENCED


def test_classify_tier_4_product_coupled():
    meta = {
        "id": "acme/deepchem",
        "contributor": "acme",
        "level": "2★",
        "links": {"github": "https://github.com/acme/repo/blob/main/SKILL.md"},
    }
    tool_map = {"acme/deepchem": {"tool": "DeepChem", "makers": ["DeepChem project"]}}
    tier = cad.classify_audit_tier("acme/deepchem", meta, "## Overview\nWrapper for DeepChem", tool_map)
    assert tier == cad.AuditTier.TIER_4_PRODUCT_COUPLED


def test_contributor_check_flagged_for_known_contributors():
    item = {
        "meta": {
            "id": "rico-favor/implement-with-discernment",
            "contributor": "rico-favor",
            "level": "1★",
            "installable": False,
        },
        "body": "## Overview\nDeliberate engineering restraint.",
        "path": "registry/named/rico-favor/implement-with-discernment.md",
    }
    res = cad.evaluate_skill("rico-favor/implement-with-discernment", item)
    assert res.contributor_check_required is True
    assert res.is_protected_exempt is True
    assert res.status == "PASS"


def test_flags_violation_for_high_star_installable_false():
    item = {
        "meta": {
            "id": "bob/unlinked-evolved",
            "contributor": "bob",
            "level": "3★",
            "installable": False,
        },
        "body": "## Overview\nHigh rank without repository link.",
        "path": "registry/named/bob/unlinked-evolved.md",
    }
    res = cad.evaluate_skill("bob/unlinked-evolved", item)
    assert res.status == "VIOLATION"
    assert "Star Bar requires <= 2★" in res.notes


def test_verify_exempt_skills_detected_when_missing():
    # Only supply gaiabot, omit rico-favor
    mock_results = [
        cad.DisentanglementResult(
            skill_id="gaiabot/repo-docs-before-pr",
            contributor="gaiabot",
            level="1★",
            stars=1,
            installable=False,
            tier=cad.AuditTier.TIER_2_PACKAGING_GAP.value,
            is_protected_exempt=True,
            contributor_check_required=True,
            status="PASS",
            notes="",
            path="",
        )
    ]
    missing = cad.verify_exempt_skills_exist(mock_results)
    assert len(missing) == 1
    assert "rico-favor/implement-with-discernment" in missing[0]


def test_run_audit_idempotent():
    first = [asdict(r) for r in cad.run_audit()]
    second = [asdict(r) for r in cad.run_audit()]
    assert len(first) > 0
    assert first == second


def test_generate_report_strict_exit_code_zero_on_clean_registry():
    results = cad.run_audit()
    missing_exempt = cad.verify_exempt_skills_exist(results)
    report = cad.generate_report(results, missing_exempt, output_dir=None)
    assert report["violationsCount"] == 0
