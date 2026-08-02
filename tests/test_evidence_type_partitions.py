import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "evidence", "scripts"))

from evidence_type_partitions import (  # noqa: E402
    CANONICAL_EVIDENCE_TYPES,
    byTypeDir,
    evidenceTypeFilename,
    iterTypePartitionPaths,
    normalizeEvidenceType,
    typeOutputPath,
)


def test_canonical_order_matches_evidence_seed_vocabulary():
    assert CANONICAL_EVIDENCE_TYPES == (
        "repo-own",
        "github-stars-own",
        "social-signal",
        "benchmark-result",
        "arxiv",
        "peer-review",
        "proxy-containment",
        "verifier-attestation",
        "fusion-recipe",
        "self-attestation",
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("repo-own", "repo-own"),
        ("github-stars-own", "github-stars-own"),
        ("repo", "repo-own"),
        ("github-stars", "github-stars-own"),
    ],
)
def test_normalize_evidence_type_accepts_canonical_and_legacy_aliases(raw, expected):
    assert normalizeEvidenceType(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "not-a-type"])
def test_normalize_evidence_type_rejects_unknown_or_empty(raw):
    with pytest.raises(ValueError):
        normalizeEvidenceType(raw)


def test_evidence_type_paths_are_deterministic(tmp_path):
    evidence_root = tmp_path / "evidence"
    assert byTypeDir(evidence_root) == os.path.join(str(evidence_root), "by-type")
    assert evidenceTypeFilename("repo") == "repo-own.md"
    assert typeOutputPath(evidence_root, "github-stars") == os.path.join(
        str(evidence_root), "by-type", "github-stars-own.md"
    )
    assert typeOutputPath(evidence_root / "by-type", "arxiv") == os.path.join(
        str(evidence_root), "by-type", "arxiv.md"
    )


def test_iter_type_partition_paths_uses_canonical_order(tmp_path):
    by_type = tmp_path / "evidence" / "by-type"
    paths = list(iterTypePartitionPaths(by_type))
    assert paths[0].endswith(os.path.join("by-type", "repo-own.md"))
    assert paths[1].endswith(os.path.join("by-type", "github-stars-own.md"))
    assert paths[-1].endswith(os.path.join("by-type", "self-attestation.md"))
    assert len(paths) == len(CANONICAL_EVIDENCE_TYPES)


def _write_minimal_registry(tmp_path):
    registry = tmp_path / "registry"
    named_dir = registry / "named"
    named_dir.mkdir(parents=True)
    (registry / "named-skills.json").write_text("{}", encoding="utf-8")
    (registry / "gaia.json").write_text(
        '{"skills":[{"id":"generic-skill","evidence":[{"type":"benchmark-result","source":"https://example.com/bench","date":"2026-01-01","notes":"bench"}]}]}',
        encoding="utf-8",
    )
    (named_dir / "alice.md").write_text(
        "---\n"
        "id: alice-skill\n"
        "name: Alice Skill\n"
        "contributor: alice\n"
        "level: 3★\n"
        "genericSkillRef: generic-skill\n"
        "evidence:\n"
        "  - type: repo\n"
        "    source: https://github.com/alice/tool\n"
        "    date: 2026-01-02\n"
        "    notes: repo row\n"
        "  - type: github-stars-own\n"
        "    source: https://github.com/alice/tool\n"
        "    date: 2026-01-03\n"
        "    notes: stars row\n"
        "---\nbody\n",
        encoding="utf-8",
    )
    return registry, named_dir


def test_generate_source_dump_writes_by_type_and_report_without_legacy_tiers(tmp_path):
    from generate_source_dump import buildSourceDump  # noqa: E402

    registry, named_dir = _write_minimal_registry(tmp_path)
    evidence = tmp_path / "evidence"
    report = evidence / "source_report_test.md"

    result = buildSourceDump(
        namedSkillsJson=str(registry / "named-skills.json"),
        gaiaJson=str(registry / "gaia.json"),
        namedDir=str(named_dir),
        outputDir=str(evidence),
        byTypeDirectory=str(evidence / "by-type"),
        reportPath=str(report),
        skipLiveStars=True,
        noLegacyTiers=True,
        reportDate="2026-07-31",
    )

    assert result is not None
    repo_partition = (evidence / "by-type" / "repo-own.md").read_text(encoding="utf-8")
    stars_partition = (evidence / "by-type" / "github-stars-own.md").read_text(encoding="utf-8")
    bench_partition = (evidence / "by-type" / "benchmark-result.md").read_text(encoding="utf-8")
    assert "## Skill: `alice-skill`" in repo_partition
    assert "- **Original Type:** `repo`" in repo_partition
    assert "stars row" in stars_partition
    assert "bench" in bench_partition
    assert not list(evidence.glob("tier_*.md"))

    report_text = report.read_text(encoding="utf-8")
    assert "evidence/by-type/<canonical-evidence-type>.md" in report_text
    assert "repo-own Source Dump" in report_text
    assert "Legacy `tier_*.md` emission was disabled" in report_text


def test_compile_data_lake_ingests_by_type_and_ignores_stale_tiers_by_default(tmp_path):
    from compile_data_lake import compileDataLake  # noqa: E402

    evidence = tmp_path / "evidence"
    by_type = evidence / "by-type"
    by_type.mkdir(parents=True)
    (by_type / "repo-own.md").write_text(
        "# Evidence Sources: repo-own\n\n"
        "## Skill: `fresh-skill`\n"
        "- **Name:** Fresh\n"
        "- **Contributor:** `alice`\n\n"
        "### Evidence Rows:\n\n"
        "#### E1: `repo-own`\n"
        "- **Source:** [https://example.com/fresh](https://example.com/fresh)\n\n"
        "---\n",
        encoding="utf-8",
    )
    (evidence / "tier_1.md").write_text(
        "# Evidence Sources: Tier 1★\n\n"
        "## Skill: `stale-skill`\n"
        "- **Name:** Stale\n"
        "- **Contributor:** `bob`\n\n"
        "### Evidence Rows:\n\n"
        "#### E1: `repo-own`\n"
        "- **Source:** [https://example.com/stale](https://example.com/stale)\n\n"
        "---\n",
        encoding="utf-8",
    )

    skills = compileDataLake(
        sourcesDir=str(by_type),
        collectorsDir=str(evidence / "collectors"),
        lakeDir=str(evidence),
    )
    lake_text = (evidence / "unified_evidence_lake.md").read_text(encoding="utf-8")
    assert set(skills) == {"fresh-skill"}
    assert "fresh-skill" in lake_text
    assert "stale-skill" not in lake_text


def test_compile_data_lake_uses_legacy_fallback_only_when_by_type_absent(tmp_path):
    from compile_data_lake import compileDataLake  # noqa: E402

    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "tier_1.md").write_text(
        "# Evidence Sources: Tier 1★\n\n"
        "## Skill: `legacy-skill`\n"
        "- **Name:** Legacy\n"
        "- **Contributor:** `bob`\n\n"
        "### Evidence Rows:\n\n"
        "#### E1: `repo-own`\n"
        "- **Source:** [https://example.com/legacy](https://example.com/legacy)\n\n"
        "---\n",
        encoding="utf-8",
    )

    no_fallback = compileDataLake(
        sourcesDir=str(evidence / "by-type"),
        collectorsDir=str(evidence / "collectors"),
        lakeDir=str(evidence),
    )
    assert no_fallback == {}

    fallback = compileDataLake(
        sourcesDir=str(evidence / "by-type"),
        collectorsDir=str(evidence / "collectors"),
        lakeDir=str(evidence),
        legacyTierFallback=True,
    )
    assert set(fallback) == {"legacy-skill"}
