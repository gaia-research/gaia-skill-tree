from dataclasses import asdict
import os
import pytest

from scripts import check_audit_disentanglement as cad


def _write_named_skill(named_dir, contributor, slug, skill_id, body, level="1★", installable=None, links=None):
    contributor_dir = os.path.join(named_dir, contributor)
    os.makedirs(contributor_dir, exist_ok=True)
    
    lines = [
        "---",
        f"id: {skill_id}",
        "name: Test Skill",
        f"contributor: {contributor}",
        f"level: {level}",
    ]
    if installable is not None:
        lines.append(f"installable: {str(installable).lower()}")
    if links:
        lines.append("links:")
        for k, v in links.items():
            lines.append(f"  {k}: {v}")
    lines.append("---")
    lines.append(body)
    lines.append("")
    
    content = "\n".join(lines)
    path = os.path.join(contributor_dir, f"{slug}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def test_load_named_skills_with_tmp_path(tmp_path):
    named_dir = tmp_path / "named"
    _write_named_skill(
        str(named_dir),
        "testauthor",
        "custom-skill",
        "testauthor/custom-skill",
        "## Overview\nA test skill for tmp_path loading.",
        level="2★",
        installable=False,
    )
    loaded = cad.load_named_skills(str(named_dir))
    assert "testauthor/custom-skill" in loaded
    assert loaded["testauthor/custom-skill"]["meta"]["contributor"] == "testauthor"
    assert loaded["testauthor/custom-skill"]["meta"]["level"] == "2★"
    assert loaded["testauthor/custom-skill"]["meta"]["installable"] is False
    assert "A test skill for tmp_path loading." in loaded["testauthor/custom-skill"]["body"]


def test_classify_tier_2_packaging_gap():
    meta = {
        "id": "rico-favor/test-skill",
        "contributor": "rico-favor",
        "level": "1★",
        "installable": False,
    }
    tier = cad.classify_audit_tier("rico-favor/test-skill", meta, "## Overview\nValid body")
    assert tier == cad.AuditTier.TIER_2_PACKAGING_GAP


def test_classify_tier_3_early_stage_stub_by_rank():
    meta = {
        "id": "alice/early-prototype",
        "contributor": "alice",
        "level": "1★",
        "links": {"github": "https://github.com/alice/repo/blob/main/SKILL.md"},
    }
    tier = cad.classify_audit_tier("alice/early-prototype", meta, "## Overview\nShort notes.")
    assert tier == cad.AuditTier.TIER_3_UNDER_EVIDENCED


def test_classify_tier_3_early_stage_stub_by_placeholder_body():
    # Test with level 2★ so stars <= 1 does not short-circuit placeholder body check
    meta = {
        "id": "alice/stub-skill",
        "contributor": "alice",
        "level": "2★",
        "links": {"github": "https://github.com/alice/repo/blob/main/SKILL.md"},
    }
    # Test with whitespace and newlines
    body = "\n\n  ## Installation\n\n  Add installation instructions here.  \n\n"
    tier = cad.classify_audit_tier("alice/stub-skill", meta, body)
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
    assert "Star Bar requires verified repo blob link" in res.notes


def test_classify_benchmark_authentic():
    meta = {
        "id": "carol/production-tool",
        "contributor": "carol",
        "level": "4★",
        "links": {"github": "https://github.com/carol/repo/blob/main/SKILL.md"},
    }
    tier = cad.classify_audit_tier("carol/production-tool", meta, "## Overview\nProduction tool implementation.")
    assert tier == cad.AuditTier.BENCHMARK_AUTHENTIC


def test_suite_exemptions_not_flagged_as_violations():
    suite_item = {
        "meta": {
            "id": "dan/suite-capstone",
            "contributor": "dan",
            "level": "5★",
            "suiteComponents": ["dan/comp-1", "dan/comp-2"],
            "installable": False,
        },
        "body": "## Overview\nSuite capstone installs via its components.",
        "path": "registry/named/dan/suite-capstone.md",
    }
    res = cad.evaluate_skill("dan/suite-capstone", suite_item)
    assert res.status == "PASS"

    suite_component_item = {
        "meta": {
            "id": "dan/comp-1",
            "contributor": "dan",
            "level": "4★",
            "suiteRef": "dan/suite-capstone",
            "installable": False,
        },
        "body": "## Overview\nComponent covered by suiteRef.",
        "path": "registry/named/dan/comp-1.md",
    }
    res_comp = cad.evaluate_skill("dan/comp-1", suite_component_item)
    assert res_comp.status == "PASS"


def test_parse_star():
    assert cad.parse_star("3★") == 3
    assert cad.parse_star("5*") == 5
    assert cad.parse_star("1") == 1
    assert cad.parse_star("") == 0
    assert cad.parse_star(None) == 0
    assert cad.parse_star("invalid") == 0


def test_verify_exempt_skills_skipped_for_custom_named_dir():
    results = []
    missing = cad.verify_exempt_skills_exist(results, named_dir="/some/other/dir")
    assert missing == []


def test_output_directory_report_written(tmp_path):
    out_dir = tmp_path / "reports"
    results = [
        cad.DisentanglementResult(
            skill_id="alice/demo",
            contributor="alice",
            level="1★",
            stars=1,
            installable=False,
            tier=cad.AuditTier.TIER_2_PACKAGING_GAP.value,
            is_protected_exempt=False,
            contributor_check_required=False,
            status="PASS",
            notes="OK",
            path="registry/named/alice/demo.md",
        )
    ]
    report = cad.generate_report(results, missing_exempt=[], output_dir=str(out_dir))
    assert report["checked"] == 1
    assert (out_dir / "audit-disentanglement.json").exists()


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
