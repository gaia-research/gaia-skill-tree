from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from gaia_cli.steward.sensors import (
    AgentSkillMirrorSensor,
    BenchmarkFreshnessSensor,
    BundledSchemaMirrorSensor,
    CliContractSensor,
    DiscoveryGenericMappingSensor,
    EvidenceLinkHealthSensor,
    GeneratedProjectionsSensor,
    KnowledgeContradictionSensor,
    RegistryIntegritySensor,
    TaxonomyScriptDriftSensor,
    UpstreamWatcherSensor,
    default_sensors,
)


NOW = "2026-08-09T00:00:00Z"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _named_markdown(skill_id: str, generic_ref: str) -> str:
    return (
        "---\n"
        f"id: {skill_id}\n"
        f"name: Representative Skill\n"
        f"genericSkillRef: {generic_ref}\n"
        "status: named\n"
        "---\n\n"
        "## Overview\n"
    )


def _named_skill_with_evidence(skill_id: str, evidence: list[dict[str, object]]) -> str:
    import yaml

    fm = {
        "id": skill_id,
        "name": "Test Skill",
        "genericSkillRef": "example",
        "status": "named",
        "evidence": evidence,
    }
    return f"---\n{yaml.dump(fm, sort_keys=False)}---\n\n## Overview\n"


def _make_clean_repo(root: Path) -> None:
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": ["id", "type", "prerequisites", "derivatives"],
        "properties": {
            "id": {"type": "string"},
            "type": {"enum": ["basic", "fusion"]},
            "prerequisites": {"type": "array", "items": {"type": "string"}},
            "derivatives": {"type": "array", "items": {"type": "string"}},
        },
    }
    schema_text = json.dumps(schema, sort_keys=True)
    _write(root / "registry/schema/skill.schema.json", schema_text)
    _write(root / "src/gaia_cli/data/registry/schema/skill.schema.json", schema_text)
    meta_text = json.dumps({
        "types": {"minPrereqs": {"basic": 0, "fusion": 1}, "order": ["basic", "fusion"]},
        "levels": {"order": ["0★", "1★", "2★", "3★", "4★", "5★", "6★"], "labels": {
            "0★": "Seedling", "1★": "Sprout", "2★": "Established", "3★": "Deepened", "4★": "Advanced", "5★": "Apex", "6★": "Transcendent"
        }},
        "evidenceTypes": [
            "github-stars-own", "repo-own", "social-signal", "benchmark-result",
            "peer-review", "arxiv", "self-attestation", "fusion-recipe",
            "verifier-attestation", "proxy-containment"
        ]
    })
    _write(root / "registry/schema/meta.json", meta_text)
    _write(root / "src/gaia_cli/data/registry/schema/meta.json", meta_text)
    node = {"id": "example", "type": "basic", "prerequisites": [], "derivatives": []}
    _write(root / "registry/nodes/basic/example.json", json.dumps(node))
    _write(root / ".agents/skills/example/SKILL.md", "# Example\n")
    _write(root / ".claude/skills/example/SKILL.md", "# Example\n")
    _write(root / "docs/graph/gaia.json", json.dumps({"nodes": [], "edges": []}))
    _write(root / "docs/graph/named/index.json", json.dumps({"buckets": {}, "awaitingClassification": [], "byContributor": {}}))
    _write(root / "docs/api/v1/health.json", json.dumps({"status": "ok"}))
    catalog_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": ["schemaVersion", "benchmarks"],
        "properties": {
            "schemaVersion": {"type": "string"},
            "benchmarks": {"type": "array"}
        }
    }
    catalog_schema_text = json.dumps(catalog_schema, sort_keys=True)
    _write(root / "registry/schema/benchmarkSourceCatalog.schema.json", catalog_schema_text)
    _write(root / "src/gaia_cli/data/registry/schema/benchmarkSourceCatalog.schema.json", catalog_schema_text)
    catalog_benchmarks = [
        {
            "id": "humaneval@v1.0",
            "name": "HumanEval",
            "status": "verified",
            "scoring": {"scoresTrustMagnitude": True, "requiredFields": ["runAt", "attestor", "datasetHash", "benchmarkInputHash"]},
            "push": {"enabled": False, "aliases": []}
        }
    ]
    _write(root / "registry/benchmark-sources.json", json.dumps({"schemaVersion": "1.0.0", "benchmarks": catalog_benchmarks}))
    policy_yaml = """version: 1
authority:
  bundled_schema_mirror_drift: A
  agent_skill_mirror_drift: A
  registry_integrity_failed: B
  sensor_coverage_unknown: B
  cli_contract_drift: B
  knowledge_contradiction: B
  taxonomy_script_drift: B
  upstream_drift: B
  evidence_link_drift: B
  generated_projection_drift: B
  benchmark_source_drift: B
  generic_mapping: C
priority:
  bundled_schema_mirror_drift:
    importance: 0.8
    decisionImpact: 0.7
    exposure: 0.8
    freshnessNeed: 1.0
    expectedCost: 0.1
  agent_skill_mirror_drift:
    importance: 0.7
    decisionImpact: 0.5
    exposure: 0.8
    freshnessNeed: 1.0
    expectedCost: 0.1
  registry_integrity_failed:
    importance: 1.0
    decisionImpact: 1.0
    exposure: 1.0
    freshnessNeed: 1.0
    expectedCost: 0.4
  sensor_coverage_unknown:
    importance: 0.8
    decisionImpact: 0.8
    exposure: 0.8
    freshnessNeed: 1.0
    expectedCost: 0.3
  cli_contract_drift:
    importance: 0.7
    decisionImpact: 0.6
    exposure: 0.8
    freshnessNeed: 0.8
    expectedCost: 0.4
  knowledge_contradiction:
    importance: 0.7
    decisionImpact: 0.8
    exposure: 0.6
    freshnessNeed: 0.6
    expectedCost: 0.5
  taxonomy_script_drift:
    importance: 0.8
    decisionImpact: 0.8
    exposure: 0.8
    freshnessNeed: 0.8
    expectedCost: 0.4
  upstream_drift:
    importance: 0.8
    decisionImpact: 0.7
    exposure: 0.8
    freshnessNeed: 0.9
    expectedCost: 0.3
  evidence_link_drift:
    importance: 0.8
    decisionImpact: 0.7
    exposure: 0.8
    freshnessNeed: 0.8
    expectedCost: 0.3
  generated_projection_drift:
    importance: 0.9
    decisionImpact: 0.8
    exposure: 0.9
    freshnessNeed: 0.9
    expectedCost: 0.2
  benchmark_source_drift:
    importance: 0.8
    decisionImpact: 0.8
    exposure: 0.7
    freshnessNeed: 0.7
    expectedCost: 0.4
  generic_mapping:
    importance: 0.9
    decisionImpact: 1.0
    exposure: 0.7
    freshnessNeed: 0.5
    expectedCost: 0.8
"""
    _write(root / "founder/steward/POLICY.yaml", policy_yaml)
    meta_md = """# Meta
| **0★** | **Seedling** |
| **1★** | **Sprout** |
| **2★** | **Established** |
| **3★** | **Deepened** |
| **4★** | **Advanced** |
| **5★** | **Apex** |
| **6★** | **Transcendent** |
- **`basic`** — 0 prerequisite
- **`fusion`** — ≥ 1 prerequisite
"""
    _write(root / "META.md", meta_md)
    claude_md = """# Claude
| **schema/** | `registry/schema/`, `src/gaia_cli/data/registry/schema/` |
"""
    _write(root / "CLAUDE.md", claude_md)


def test_all_sensors_report_healthy_on_clean_fixture(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)

    sensors = [
        BundledSchemaMirrorSensor(),
        AgentSkillMirrorSensor(),
        RegistryIntegritySensor(),
        TaxonomyScriptDriftSensor(),
        UpstreamWatcherSensor(),
        KnowledgeContradictionSensor(),
        EvidenceLinkHealthSensor(),
        GeneratedProjectionsSensor(),
        BenchmarkFreshnessSensor(),
    ]

    observations = [sensor.scan(tmp_path, NOW)[0] for sensor in sensors]
    assert [observation.status for observation in observations] == ["healthy"] * len(sensors)


def test_discovery_sensor_excludes_archived_and_processed_packets_and_targets_exact_candidate(tmp_path: Path) -> None:
    archived = {"sourceRepo": "example/repo", "sourceState": "current", "disposition": "unresolved", "proposedSkills": [{"id": "archived"}]}
    processed = {"sourceRepo": "example/repo", "sourceState": "current", "disposition": "accepted", "proposedSkills": [{"id": "processed"}]}
    current = {"sourceRepo": "example/repo", "sourceState": "current", "disposition": "unresolved", "proposedSkills": [{"id": "alpha"}, {"id": "beta"}]}
    _write(tmp_path / "registry-for-review/archive/old.json", json.dumps(archived))
    _write(tmp_path / "registry-for-review/discovery-packets/processed.json", json.dumps(processed))
    _write(tmp_path / "registry-for-review/discovery-packets/current.json", json.dumps(current))

    observations = DiscoveryGenericMappingSensor().scan(tmp_path, NOW)

    assert [item.subject.id for item in observations] == ["alpha", "beta"]
    assert [item.observed_state["decisionTarget"] for item in observations] == [
        "generic-mapping/alpha", "generic-mapping/beta",
    ]
    assert all(item.observed_state["sourceState"] == "current" for item in observations)




def test_discovery_sensor_deduplicates_repeated_exact_candidate_question(tmp_path: Path) -> None:
    packet = {"sourceRepo": "example/repo", "sourceState": "current", "disposition": "unresolved", "proposedSkills": [{"id": "owner/open"}]}
    _write(tmp_path / "registry-for-review/discovery-packets/one.json", json.dumps(packet))
    _write(tmp_path / "registry-for-review/discovery-packets/two.json", json.dumps(packet))

    observations = DiscoveryGenericMappingSensor().scan(tmp_path, NOW)

    assert len(observations) == 1
    assert observations[0].observed_state["decisionTarget"] == "generic-mapping/owner/open"




def test_discovery_sensor_excludes_exact_candidate_with_canonical_mapping(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    packet = {"sourceRepo": "example/repo", "sourceState": "current", "disposition": "unresolved", "proposedSkills": [{"id": "owner/covered"}, {"id": "owner/open"}]}
    _write(tmp_path / "registry-for-review/discovery-packets/current.json", json.dumps(packet))
    _write(
        tmp_path / "registry/named/owner/covered.md",
        _named_markdown("owner/covered", "example"),
    )

    observations = DiscoveryGenericMappingSensor().scan(tmp_path, NOW)

    assert [item.subject.id for item in observations] == ["owner/open"]




def test_discovery_sensor_accepts_only_explicit_current_local_input(tmp_path: Path) -> None:
    _write(tmp_path / ".gaia/steward/discovery-mapping-input.json", json.dumps({
        "schemaVersion": "steward-discovery-mapping-input-v1",
        "candidates": [
            {"candidateId": "owner/open", "sourceRepo": "owner/repo", "sourceState": "current", "disposition": "unresolved"},
            {"candidateId": "owner/done", "sourceRepo": "owner/repo", "sourceState": "current", "disposition": "accepted"},
        ],
    }))

    observations = DiscoveryGenericMappingSensor().scan(tmp_path, NOW)

    assert [item.subject.id for item in observations] == ["owner/open"]
    assert observations[0].provenance["inputPath"] == ".gaia/steward/discovery-mapping-input.json"




def test_discovery_sensor_casefolds_before_canonical_mapping_lookup(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    _write(tmp_path / "registry-for-review/discovery-packets/current.json", json.dumps({
        "sourceRepo": "example/repo", "sourceState": "current", "disposition": "unresolved",
        "proposedSkills": [{"id": "Owner/Open"}],
    }))
    _write(
        tmp_path / "registry/named/owner/open.md",
        _named_markdown("owner/open", "example"),
    )

    assert DiscoveryGenericMappingSensor().scan(tmp_path, NOW) == []




def test_discovery_sensor_supports_legacy_json_canonical_mapping(tmp_path: Path) -> None:
    _write(tmp_path / "registry-for-review/discovery-packets/current.json", json.dumps({
        "sourceRepo": "example/repo", "sourceState": "current", "disposition": "unresolved",
        "proposedSkills": [{"id": "owner/covered"}],
    }))
    _write(tmp_path / "registry/named/owner/covered.json", json.dumps({
        "id": "owner/covered", "targetSkillId": "example",
    }))

    assert DiscoveryGenericMappingSensor().scan(tmp_path, NOW) == []




def test_discovery_sensor_groups_equivalent_candidate_identifiers_by_canonical_identity(tmp_path: Path) -> None:
    _write(tmp_path / "registry-for-review/discovery-packets/one.json", json.dumps({
        "sourceRepo": "example/repo", "sourceState": "current", "disposition": "unresolved",
        "proposedSkills": [{"id": " Owner/Open "}],
    }))
    _write(tmp_path / "registry-for-review/discovery-packets/two.json", json.dumps({
        "sourceRepo": "example/repo", "sourceState": "current", "disposition": "unresolved",
        "proposedSkills": [{"id": "owner/open"}],
    }))

    observations = DiscoveryGenericMappingSensor().scan(tmp_path, NOW)

    assert len(observations) == 1
    assert observations[0].subject.id == "owner/open"
    assert observations[0].observed_state["decisionTarget"] == "generic-mapping/owner/open"
    assert observations[0].observed_state["candidateDisplayId"] == "Owner/Open"


@pytest.mark.parametrize("candidate_id", ["owner//open", "zzreview/ſ", "owner/K", "owner/ß"])


def test_discovery_sensor_fails_closed_for_malformed_controlled_candidate(
    tmp_path: Path, candidate_id: str,
) -> None:
    _write(tmp_path / ".gaia/steward/discovery-mapping-input.json", json.dumps({
        "schemaVersion": "steward-discovery-mapping-input-v1",
        "candidates": [{
            "candidateId": candidate_id, "sourceRepo": "owner/repo",
            "sourceState": "current", "disposition": "unresolved",
        }],
    }))

    with pytest.raises(ValueError, match="invalid current unresolved local discovery candidate"):
        DiscoveryGenericMappingSensor().scan(tmp_path, NOW)


@pytest.mark.parametrize("candidate_id", ["owner//open", "zzreview/ſ", "owner/K", "owner/ß"])


def test_discovery_sensor_fails_closed_for_malformed_current_packet_candidate(
    tmp_path: Path, candidate_id: str,
) -> None:
    _write(tmp_path / "registry-for-review/discovery-packets/current.json", json.dumps({
        "sourceRepo": "owner/repo", "sourceState": "current", "disposition": "unresolved",
        "proposedSkills": [{"id": candidate_id}],
    }))

    with pytest.raises(ValueError, match="invalid current unresolved discovery candidate"):
        DiscoveryGenericMappingSensor().scan(tmp_path, NOW)


@pytest.mark.parametrize(
    ("canonical_id", "controlled_id"),
    [("zzreview/ſ", "zzreview/s"), ("owner/K", "owner/k"), ("owner/ß", "owner/ss")],
)


def test_discovery_sensor_rejects_non_ascii_canonical_markdown_collision(
    tmp_path: Path, canonical_id: str, controlled_id: str,
) -> None:
    _make_clean_repo(tmp_path)
    _write(tmp_path / "registry-for-review/discovery-packets/current.json", json.dumps({
        "sourceRepo": "example/repo", "sourceState": "current", "disposition": "unresolved",
        "proposedSkills": [{"id": controlled_id}],
    }))
    _write(
        tmp_path / "registry/named/owner/collision.md",
        _named_markdown(canonical_id, "example"),
    )

    with pytest.raises(ValueError, match="invalid canonical named skill id"):
        DiscoveryGenericMappingSensor().scan(tmp_path, NOW)




def test_discovery_sensor_skips_malformed_archived_local_candidate(tmp_path: Path) -> None:
    _write(tmp_path / ".gaia/steward/discovery-mapping-input.json", json.dumps({
        "schemaVersion": "steward-discovery-mapping-input-v1",
        "candidates": [{
            "candidateId": "owner//archived", "sourceRepo": "owner/repo",
            "sourceState": "archived", "disposition": "unresolved",
        }],
    }))

    assert DiscoveryGenericMappingSensor().scan(tmp_path, NOW) == []




def test_discovery_sensor_fails_closed_for_malformed_canonical_identity(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    _write(tmp_path / "registry/named/owner/open.json", json.dumps({
        "id": "owner//open", "targetSkillId": "example",
    }))
    _write(tmp_path / "registry-for-review/discovery-packets/current.json", json.dumps({
        "sourceRepo": "example/repo", "sourceState": "current", "disposition": "unresolved",
        "proposedSkills": [{"id": "owner/open"}],
    }))

    with pytest.raises(ValueError, match="invalid canonical named skill id"):
        DiscoveryGenericMappingSensor().scan(tmp_path, NOW)




def test_discovery_sensor_hashes_exact_controlled_input_bytes_once_under_mutation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / ".gaia/steward/discovery-mapping-input.json"
    original = json.dumps({
        "schemaVersion": "steward-discovery-mapping-input-v1",
        "candidates": [{
            "candidateId": "Owner/Open", "sourceRepo": "owner/repo",
            "sourceState": "current", "disposition": "unresolved",
        }],
    }).encode("utf-8")
    replacement = json.dumps({
        "schemaVersion": "steward-discovery-mapping-input-v1", "candidates": [],
    })
    path.parent.mkdir(parents=True)
    path.write_bytes(original)
    original_read_bytes = Path.read_bytes
    reads: list[Path] = []

    def mutate_after_read(self: Path) -> bytes:
        if self == path:
            reads.append(self)
            path.write_text(replacement, encoding="utf-8")
            return original
        return original_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", mutate_after_read)
    observations = DiscoveryGenericMappingSensor().scan(tmp_path, NOW)

    assert reads == [path]
    assert observations[0].subject.id == "owner/open"
    assert observations[0].observed_state["inputDigest"] == hashlib.sha256(original).hexdigest()




def test_schema_drift_is_deterministic_and_semantically_stable(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    bundled = tmp_path / "src/gaia_cli/data/registry/schema/skill.schema.json"
    bundled.write_text("{}", encoding="utf-8")
    sensor = BundledSchemaMirrorSensor()

    first = sensor.scan(tmp_path, NOW)[0]
    second = sensor.scan(tmp_path, "2026-08-10T00:00:00Z")[0]

    assert first.status == "drift"
    assert first.observed_state["contentMismatch"] == ["skill.schema.json"]
    assert first.debt_id == second.debt_id
    assert first.current_state == second.current_state
    assert first.observed_state == second.observed_state




def test_schema_sensor_detects_files_present_on_only_one_side(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    _write(tmp_path / "registry/schema/nested/canonical.json", "{}")
    _write(tmp_path / "src/gaia_cli/data/registry/schema/bundled-only.json", "{}")

    observation = BundledSchemaMirrorSensor().scan(tmp_path, NOW)[0]

    assert observation.status == "drift"
    assert observation.observed_state["missingFromMirror"] == ["nested/canonical.json"]
    assert observation.observed_state["extraInMirror"] == ["bundled-only.json"]




def test_agent_skill_mirror_detects_drift(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    _write(tmp_path / ".claude/skills/example/SKILL.md", "# Changed\n")

    observation = AgentSkillMirrorSensor().scan(tmp_path, NOW)[0]

    assert observation.status == "drift"
    assert observation.observed_state["contentMismatch"] == ["example/SKILL.md"]




def test_registry_integrity_reports_schema_and_reference_failures(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    broken = {
        "id": "wrong-id",
        "type": "basic",
        "prerequisites": ["missing"],
        "derivatives": [],
    }
    _write(tmp_path / "registry/nodes/basic/broken.json", json.dumps(broken))

    observation = RegistryIntegritySensor().scan(tmp_path, NOW)[0]

    assert observation.status == "drift"
    errors = [entry["error"] for entry in observation.observed_state["violations"]]
    assert any("filename does not match" in error for error in errors)
    assert any("references missing id" in error for error in errors)




def test_registry_integrity_reports_schema_valid_dependency_cycle(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    alpha = {
        "id": "alpha",
        "type": "fusion",
        "prerequisites": ["beta"],
        "derivatives": ["beta"],
    }
    beta = {
        "id": "beta",
        "type": "fusion",
        "prerequisites": ["alpha"],
        "derivatives": ["alpha"],
    }
    _write(tmp_path / "registry/nodes/basic/alpha.json", json.dumps(alpha))
    _write(tmp_path / "registry/nodes/basic/beta.json", json.dumps(beta))

    observation = RegistryIntegritySensor().scan(tmp_path, NOW)[0]

    assert observation.status == "drift"
    errors = [entry["error"] for entry in observation.observed_state["violations"]]
    assert "dependency cycle detected: alpha -> beta -> alpha" in errors


@pytest.mark.parametrize(
    ("node", "expected"),
    [
        (
            {"id": "empty-fusion", "type": "fusion", "prerequisites": [], "derivatives": []},
            "fusion skill 'empty-fusion' needs >=1 prerequisites (has 0)",
        ),
        (
            {
                "id": "dependent-basic",
                "type": "basic",
                "prerequisites": ["example"],
                "derivatives": [],
            },
            "basic skill 'dependent-basic' must have 0 prerequisites (has 1)",
        ),
    ],
)


def test_registry_integrity_enforces_canonical_prerequisite_count_rules(
    tmp_path: Path,
    node: dict[str, object],
    expected: str,
) -> None:
    _make_clean_repo(tmp_path)
    _write(
        tmp_path / f"registry/nodes/{node['type']}/{node['id']}.json",
        json.dumps(node),
    )

    observation = RegistryIntegritySensor().scan(tmp_path, NOW)[0]

    assert observation.status == "drift"
    errors = [entry["error"] for entry in observation.observed_state["violations"]]
    assert expected in errors




def test_registry_integrity_accepts_basic_and_fusion_prerequisite_boundaries(
    tmp_path: Path,
) -> None:
    _make_clean_repo(tmp_path)
    fusion = {
        "id": "one-parent-fusion",
        "type": "fusion",
        "prerequisites": ["example"],
        "derivatives": [],
    }
    _write(tmp_path / "registry/nodes/fusion/one-parent-fusion.json", json.dumps(fusion))

    observation = RegistryIntegritySensor().scan(tmp_path, NOW)[0]

    assert observation.status == "healthy"




def test_taxonomy_script_drift_sensor_in_default_sensors() -> None:
    sensor_types = [type(s) for s in default_sensors()]
    assert TaxonomyScriptDriftSensor in sensor_types




def test_taxonomy_script_drift_sensor_reports_healthy_on_clean_repo(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    meta = {
        "types": {"minPrereqs": {"basic": 0, "fusion": 1}},
        "evidence": {
            "types": [
                {"id": "github-stars-own"},
                {"id": "repo-own"},
                {"id": "self-attestation"},
            ]
        },
    }
    _write(tmp_path / "registry/schema/meta.json", json.dumps(meta))
    _write(
        tmp_path / "src/gaia_cli/trustMagnitude.py",
        "TYPE_WEIGHTS = {\n"
        "    'github-stars-own': 1.0,\n"
        "    'repo-own': 0.6,\n"
        "    'self-attestation': 0.5,\n"
        "}\n",
    )
    _write(
        tmp_path / "scripts/inspectTrustMagnitude.py",
        "from gaia_cli.taxonomy import rankWord, branchFor\n"
        "# Comment referencing Transcendent or node.type == 'ultimate'\n"
        "def inspect(skill):\n"
        "    branch = branchFor(skill)\n"
        "    word = rankWord(skill.get('rank', 0), branch)\n"
        "    return word\n",
    )

    observations = TaxonomyScriptDriftSensor().scan(tmp_path, NOW)
    assert len(observations) == 1
    obs = observations[0]
    assert obs.kind == "taxonomy_script_drift"
    assert obs.status == "healthy"
    assert obs.observed_state["consistent"] is True
    assert obs.observed_state["violationCount"] == 0
    assert obs.confidence == 1.0




def test_taxonomy_script_drift_sensor_detects_dead_type_comparison(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    _write(
        tmp_path / "scripts/inspectTrustMagnitude.py",
        "def check_type(node):\n"
        "    if node.type == 'ultimate':\n"
        "        return 'suite'\n",
    )

    obs = TaxonomyScriptDriftSensor().scan(tmp_path, NOW)[0]
    assert obs.status == "drift"
    assert obs.observed_state["consistent"] is False
    violations = obs.observed_state["violations"]
    assert len(violations) == 1
    assert violations[0]["kind"] == "type-branch"
    assert violations[0]["path"] == "scripts/inspectTrustMagnitude.py"




def test_taxonomy_script_drift_sensor_detects_deleted_resolver_shims(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    _write(
        tmp_path / "scripts/trust_appraise.py",
        "import gaia_cli.trustMagnitude\n"
        "def run(skill):\n"
        "    branch = gaia_cli.trustMagnitude.computeBranch(skill)\n"
        "    word = rank_word(3)\n"
        "    label = format_rank_label(4)\n"
        "    return branch, word, label\n",
    )

    obs = TaxonomyScriptDriftSensor().scan(tmp_path, NOW)[0]
    assert obs.status == "drift"
    violations = obs.observed_state["violations"]
    kinds = [v["kind"] for v in violations]
    assert kinds.count("deleted-shim") == 3
    assert all(v["path"] == "scripts/trust_appraise.py" for v in violations)




def test_taxonomy_script_drift_sensor_detects_banned_rank_vocabulary(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    _write(
        tmp_path / "scripts/check_something.py",
        "RANK_MAP = {5: 'Transcendent', 4: 'Hardened'}\n",
    )

    obs = TaxonomyScriptDriftSensor().scan(tmp_path, NOW)[0]
    assert obs.status == "drift"
    violations = obs.observed_state["violations"]
    assert len(violations) == 1
    assert violations[0]["kind"] == "banned-vocabulary"
    assert violations[0]["path"] == "scripts/check_something.py"




def test_taxonomy_script_drift_sensor_detects_evidence_type_mismatch(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    meta = {
        "types": {"minPrereqs": {"basic": 0, "fusion": 1}},
        "evidence": {
            "types": [
                {"id": "github-stars-own"},
                {"id": "repo-own"},
            ]
        },
    }
    _write(tmp_path / "registry/schema/meta.json", json.dumps(meta))
    _write(
        tmp_path / "src/gaia_cli/trustMagnitude.py",
        "TYPE_WEIGHTS = {\n"
        "    'github-stars-own': 1.0,\n"
        "    'unknown-type': 0.5,\n"
        "}\n",
    )

    obs = TaxonomyScriptDriftSensor().scan(tmp_path, NOW)[0]
    assert obs.status == "drift"
    violations = obs.observed_state["violations"]
    assert any(v["kind"] == "evidence-type-mismatch" for v in violations)
    assert any("TYPE_WEIGHTS keys diverge" in v["detail"] for v in violations)




def test_taxonomy_script_drift_sensor_detects_unknown_evidence_type_in_script(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    meta = {
        "types": {"minPrereqs": {"basic": 0, "fusion": 1}},
        "evidence": {
            "types": [
                {"id": "github-stars-own"},
                {"id": "repo-own"},
            ]
        },
    }
    _write(tmp_path / "registry/schema/meta.json", json.dumps(meta))
    _write(
        tmp_path / "src/gaia_cli/trustMagnitude.py",
        "TYPE_WEIGHTS = {'github-stars-own': 1.0, 'repo-own': 0.6}\n",
    )
    _write(
        tmp_path / "scripts/trust_appraise.py",
        "ALLOWED_EVIDENCE_TYPES = ('github-stars-own', 'bogus-evidence-type')\n",
    )

    obs = TaxonomyScriptDriftSensor().scan(tmp_path, NOW)[0]
    assert obs.status == "drift"
    violations = obs.observed_state["violations"]
    assert any(v["kind"] == "unknown-evidence-type" for v in violations)
    assert any("bogus-evidence-type" in v["detail"] for v in violations)




def test_taxonomy_script_drift_sensor_on_real_repo() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    obs = TaxonomyScriptDriftSensor().scan(repo_root, NOW)[0]
    assert obs.status == "healthy"
    assert obs.observed_state["consistent"] is True
    assert obs.observed_state["violationCount"] == 0



def test_default_sensors_contains_upstream_watcher_sensor() -> None:
    sensors = default_sensors()
    assert any(sensor.id == "upstream-watcher" for sensor in sensors)
    matching = [s for s in sensors if isinstance(s, UpstreamWatcherSensor)]
    assert len(matching) == 1




def test_upstream_watcher_reports_healthy_on_clean_fixture(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    obs = UpstreamWatcherSensor().scan(tmp_path, NOW)[0]
    assert obs.status == "healthy"
    assert obs.kind == "upstream_drift"
    assert obs.subject.id == "upstream-watcher"
    assert obs.observed_state["consistent"] is True
    assert obs.observed_state["trackedCount"] == 0
    assert obs.observed_state["violationCount"] == 0
    assert obs.observed_state["driftCount"] == 0




def test_upstream_watcher_reports_healthy_on_valid_named_skill_with_upstream(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    content = (
        "---\n"
        "id: testowner/testsuite\n"
        "name: Test Suite\n"
        "level: 3★\n"
        "genericSkillRef: test-generic\n"
        "links:\n"
        "  github: https://github.com/testowner/testsuite\n"
        "upstream:\n"
        "  repo: testowner/testsuite\n"
        "  version: v1.2.0\n"
        "  mode: components\n"
        "  sourceUrl: https://github.com/testowner/testsuite/releases/tag/v1.2.0\n"
        "---\n\n"
        "# Test Suite\n"
    )
    _write(tmp_path / "registry/named/testowner/testsuite.md", content)

    obs = UpstreamWatcherSensor().scan(tmp_path, NOW)[0]
    assert obs.status == "healthy"
    assert obs.observed_state["trackedCount"] == 1
    assert obs.observed_state["trackedSkills"] == ["testowner/testsuite"]
    assert obs.observed_state["violations"] == []
    assert obs.observed_state["drift"] == []




def test_upstream_watcher_detects_malformed_upstream_repo(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    content = (
        "---\n"
        "id: testowner/testskill\n"
        "name: Test Skill\n"
        "level: 2★\n"
        "upstream:\n"
        "  repo: invalid_no_slash\n"
        "  version: v1.0.0\n"
        "---\n"
    )
    _write(tmp_path / "registry/named/testowner/testskill.md", content)

    obs = UpstreamWatcherSensor().scan(tmp_path, NOW)[0]
    assert obs.status == "drift"
    assert obs.observed_state["violationCount"] == 1
    assert any("upstream.repo must match owner/repo pattern" in v["error"] for v in obs.observed_state["violations"])




def test_upstream_watcher_detects_missing_version(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    content = (
        "---\n"
        "id: testowner/testskill\n"
        "name: Test Skill\n"
        "level: 2★\n"
        "upstream:\n"
        "  repo: testowner/testrepo\n"
        "  version: ''\n"
        "---\n"
    )
    _write(tmp_path / "registry/named/testowner/testskill.md", content)

    obs = UpstreamWatcherSensor().scan(tmp_path, NOW)[0]
    assert obs.status == "drift"
    assert any("upstream.version must be a non-empty string" in v["error"] for v in obs.observed_state["violations"])




def test_upstream_watcher_detects_invalid_mode(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    content = (
        "---\n"
        "id: testowner/testskill\n"
        "name: Test Skill\n"
        "level: 2★\n"
        "upstream:\n"
        "  repo: testowner/testrepo\n"
        "  version: v1.0.0\n"
        "  mode: unsupported-mode\n"
        "---\n"
    )
    _write(tmp_path / "registry/named/testowner/testskill.md", content)

    obs = UpstreamWatcherSensor().scan(tmp_path, NOW)[0]
    assert obs.status == "drift"
    assert any("upstream.mode must be 'components' or 'version-only'" in v["error"] for v in obs.observed_state["violations"])




def test_upstream_watcher_detects_under_level_tracking(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    content = (
        "---\n"
        "id: testowner/testskill\n"
        "name: Test Skill\n"
        "level: 1★\n"
        "upstream:\n"
        "  repo: testowner/testrepo\n"
        "  version: v1.0.0\n"
        "---\n"
    )
    _write(tmp_path / "registry/named/testowner/testskill.md", content)

    obs = UpstreamWatcherSensor().scan(tmp_path, NOW)[0]
    assert obs.status == "drift"
    assert any("below required 2★" in v["error"] for v in obs.observed_state["violations"])




def test_upstream_watcher_detects_repo_mismatch_without_canonical_opt_out(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    content = (
        "---\n"
        "id: testowner/testskill\n"
        "name: Test Skill\n"
        "level: 2★\n"
        "links:\n"
        "  github: https://github.com/foo/bar\n"
        "upstream:\n"
        "  repo: baz/qux\n"
        "  version: v1.0.0\n"
        "---\n"
    )
    _write(tmp_path / "registry/named/testowner/testskill.md", content)

    obs = UpstreamWatcherSensor().scan(tmp_path, NOW)[0]
    assert obs.status == "drift"
    assert any("does not match links.github repo" in v["error"] for v in obs.observed_state["violations"])




def test_upstream_watcher_permits_repo_mismatch_with_canonical_opt_out(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    content = (
        "---\n"
        "id: testowner/testskill\n"
        "name: Test Skill\n"
        "level: 2★\n"
        "links:\n"
        "  github: https://github.com/foo/bar\n"
        "  canonicalRepo: https://github.com/baz/qux\n"
        "upstream:\n"
        "  repo: baz/qux\n"
        "  version: v1.0.0\n"
        "---\n"
    )
    _write(tmp_path / "registry/named/testowner/testskill.md", content)

    obs = UpstreamWatcherSensor().scan(tmp_path, NOW)[0]
    assert obs.status == "healthy"




def test_upstream_watcher_detects_invalid_github_url(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    content = (
        "---\n"
        "id: testowner/testskill\n"
        "name: Test Skill\n"
        "links:\n"
        "  github: not a url\n"
        "---\n"
    )
    _write(tmp_path / "registry/named/testowner/testskill.md", content)

    obs = UpstreamWatcherSensor().scan(tmp_path, NOW)[0]
    assert obs.status == "drift"
    assert any("invalid links.github URL" in v["error"] for v in obs.observed_state["violations"])




def test_upstream_watcher_detects_invalid_source_url(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    content = (
        "---\n"
        "id: testowner/testskill\n"
        "name: Test Skill\n"
        "level: 2★\n"
        "upstream:\n"
        "  repo: testowner/testrepo\n"
        "  version: v1.0.0\n"
        "  sourceUrl: ftp://invalid-schema\n"
        "---\n"
    )
    _write(tmp_path / "registry/named/testowner/testskill.md", content)

    obs = UpstreamWatcherSensor().scan(tmp_path, NOW)[0]
    assert obs.status == "drift"
    assert any("upstream.sourceUrl must be a valid URL" in v["error"] for v in obs.observed_state["violations"])




def test_upstream_watcher_detects_drift_from_watcher_manifest(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    manifest = {
        "findings": [
            {
                "skillId": "mattpocock/skills",
                "currentVersion": "v1.2.0",
                "newVersion": "v1.3.0",
                "finding_type": "update",
            }
        ]
    }
    _write(tmp_path / ".gaia/upstream-watcher/findings.json", json.dumps(manifest))

    obs = UpstreamWatcherSensor().scan(tmp_path, NOW)[0]
    assert obs.status == "drift"
    assert obs.observed_state["driftCount"] == 1
    drift = obs.observed_state["drift"][0]
    assert drift["skillId"] == "mattpocock/skills"
    assert drift["findingType"] == "update"
    assert drift["currentVersion"] == "v1.2.0"
    assert drift["newVersion"] == "v1.3.0"




def test_upstream_watcher_detects_bootstrap_finding(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    manifest = [
        {
            "skillId": "obra/superpowers",
            "currentVersion": None,
            "newVersion": "v6.2.0",
            "finding_type": "bootstrap",
        }
    ]
    _write(tmp_path / ".gaia/upstream-watcher/releases.json", json.dumps(manifest))

    obs = UpstreamWatcherSensor().scan(tmp_path, NOW)[0]
    assert obs.status == "drift"
    assert obs.observed_state["driftCount"] == 1
    assert obs.observed_state["drift"][0]["skillId"] == "obra/superpowers"
    assert obs.observed_state["drift"][0]["findingType"] == "bootstrap"




def test_upstream_watcher_detects_name_and_component_drift(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    manifest = {
        "skills": [
            {
                "skillId": "ruvnet/ruflo",
                "nameDrift": True,
                "addedComponents": ["ruvnet/new-subskill"],
            }
        ]
    }
    _write(tmp_path / ".gaia/upstream-watcher/state.json", json.dumps(manifest))

    obs = UpstreamWatcherSensor().scan(tmp_path, NOW)[0]
    assert obs.status == "drift"
    finding_types = [d["findingType"] for d in obs.observed_state["drift"]]
    assert "name_drift" in finding_types
    assert "component_drift" in finding_types




def test_upstream_watcher_detects_corrupt_watcher_json(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    _write(tmp_path / ".gaia/upstream-watcher/corrupt.json", "{not-valid-json")

    obs = UpstreamWatcherSensor().scan(tmp_path, NOW)[0]
    assert obs.status == "drift"
    assert obs.observed_state["violationCount"] == 1
    assert any("invalid upstream watcher manifest" in v["error"] for v in obs.observed_state["violations"])




def test_upstream_watcher_detects_malformed_upstream_block_type(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    content = (
        "---\n"
        "id: testowner/testskill\n"
        "name: Test Skill\n"
        "level: 2★\n"
        "upstream: not-a-mapping\n"
        "---\n"
    )
    _write(tmp_path / "registry/named/testowner/testskill.md", content)

    obs = UpstreamWatcherSensor().scan(tmp_path, NOW)[0]
    assert obs.status == "drift"
    assert any("upstream block must be a mapping" in v["error"] for v in obs.observed_state["violations"])




def test_upstream_watcher_on_real_repo() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    obs = UpstreamWatcherSensor().scan(repo_root, NOW)[0]
    assert obs.status == "healthy"
    assert obs.observed_state["consistent"] is True
    assert obs.observed_state["violationCount"] == 0
    assert obs.observed_state["driftCount"] == 0
    assert obs.observed_state["trackedCount"] > 0



def test_default_sensors_contains_knowledge_contradiction_sensor() -> None:
    sensors = default_sensors()
    assert any(sensor.id == "knowledge-contradiction" for sensor in sensors)
    matching = [s for s in sensors if isinstance(s, KnowledgeContradictionSensor)]
    assert len(matching) == 1




def test_knowledge_contradiction_sensor_healthy_on_real_repo() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    observations = KnowledgeContradictionSensor().scan(repo_root, NOW)

    assert len(observations) == 1
    obs = observations[0]
    assert obs.kind == "knowledge_contradiction"
    assert obs.subject.id == "governance-policy"
    assert obs.status == "healthy"
    assert obs.confidence == 1.0
    assert obs.observed_state["consistent"] is True
    assert obs.observed_state["violationCount"] == 0
    assert obs.observed_state["violations"] == []




def test_knowledge_contradiction_detects_unknown_debt_kind(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    policy_yaml = (
        "authority:\n"
        "  unknown_bogus_drift: B\n"
        "priority:\n"
        "  unknown_bogus_drift:\n"
        "    importance: 0.5\n"
        "    decisionImpact: 0.5\n"
        "    exposure: 0.5\n"
        "    freshnessNeed: 0.5\n"
        "    expectedCost: 0.5\n"
    )
    _write(tmp_path / "founder/steward/POLICY.yaml", policy_yaml)

    obs = KnowledgeContradictionSensor().scan(tmp_path, NOW)[0]
    assert obs.status == "drift"
    assert obs.observed_state["consistent"] is False
    violations = obs.observed_state["violations"]
    assert any(v["rule"] == "registered-debt-kinds" and "unknown_bogus_drift" in v["detail"] for v in violations)




def test_knowledge_contradiction_detects_invalid_authority_class(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    policy_yaml = (
        "authority:\n"
        "  cli_contract_drift: X\n"
        "priority:\n"
        "  cli_contract_drift:\n"
        "    importance: 0.5\n"
        "    decisionImpact: 0.5\n"
        "    exposure: 0.5\n"
        "    freshnessNeed: 0.5\n"
        "    expectedCost: 0.5\n"
    )
    _write(tmp_path / "founder/steward/POLICY.yaml", policy_yaml)

    obs = KnowledgeContradictionSensor().scan(tmp_path, NOW)[0]
    assert obs.status == "drift"
    violations = obs.observed_state["violations"]
    assert any(v["rule"] == "valid-authority-class" and "invalid authority class 'X'" in v["detail"] for v in violations)




def test_knowledge_contradiction_detects_authority_priority_mismatch(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    policy_yaml = (
        "authority:\n"
        "  cli_contract_drift: B\n"
        "  knowledge_contradiction: B\n"
        "priority:\n"
        "  cli_contract_drift:\n"
        "    importance: 0.5\n"
        "    decisionImpact: 0.5\n"
        "    exposure: 0.5\n"
        "    freshnessNeed: 0.5\n"
        "    expectedCost: 0.5\n"
    )
    _write(tmp_path / "founder/steward/POLICY.yaml", policy_yaml)

    obs = KnowledgeContradictionSensor().scan(tmp_path, NOW)[0]
    assert obs.status == "drift"
    violations = obs.observed_state["violations"]
    assert any(v["rule"] == "authority-priority-alignment" for v in violations)




def test_knowledge_contradiction_detects_repair_executor_authority_mismatch(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    policy_yaml = (
        "authority:\n"
        "  registry_integrity_failed: B\n"
        "priority:\n"
        "  registry_integrity_failed:\n"
        "    importance: 0.5\n"
        "    decisionImpact: 0.5\n"
        "    exposure: 0.5\n"
        "    freshnessNeed: 0.5\n"
        "    expectedCost: 0.5\n"
        "repairs:\n"
        "  executors:\n"
        "    bad-executor:\n"
        "      debtKind: registry_integrity_failed\n"
        "      authority: B\n"
    )
    _write(tmp_path / "founder/steward/POLICY.yaml", policy_yaml)

    obs = KnowledgeContradictionSensor().scan(tmp_path, NOW)[0]
    assert obs.status == "drift"
    violations = obs.observed_state["violations"]
    assert any(v["rule"] == "repair-executor-authority" for v in violations)




def test_knowledge_contradiction_detects_dispatch_rule_authority_mismatch(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    policy_yaml = (
        "authority:\n"
        "  bundled_schema_mirror_drift: A\n"
        "priority:\n"
        "  bundled_schema_mirror_drift:\n"
        "    importance: 0.5\n"
        "    decisionImpact: 0.5\n"
        "    exposure: 0.5\n"
        "    freshnessNeed: 0.5\n"
        "    expectedCost: 0.5\n"
        "routing:\n"
        "  dispatchRules:\n"
        "    bad-dispatch:\n"
        "      debtKind: bundled_schema_mirror_drift\n"
        "      authority: A\n"
    )
    _write(tmp_path / "founder/steward/POLICY.yaml", policy_yaml)

    obs = KnowledgeContradictionSensor().scan(tmp_path, NOW)[0]
    assert obs.status == "drift"
    violations = obs.observed_state["violations"]
    assert any(v["rule"] == "dispatch-rule-authority" for v in violations)




def test_knowledge_contradiction_detects_founder_rule_authority_mismatch(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    policy_yaml = (
        "authority:\n"
        "  cli_contract_drift: B\n"
        "priority:\n"
        "  cli_contract_drift:\n"
        "    importance: 0.5\n"
        "    decisionImpact: 0.5\n"
        "    exposure: 0.5\n"
        "    freshnessNeed: 0.5\n"
        "    expectedCost: 0.5\n"
        "routing:\n"
        "  founderRules:\n"
        "    bad-founder:\n"
        "      debtKind: cli_contract_drift\n"
        "      authority: B\n"
    )
    _write(tmp_path / "founder/steward/POLICY.yaml", policy_yaml)

    obs = KnowledgeContradictionSensor().scan(tmp_path, NOW)[0]
    assert obs.status == "drift"
    violations = obs.observed_state["violations"]
    assert any(v["rule"] == "founder-rule-authority" for v in violations)




def test_knowledge_contradiction_detects_skill_type_enum_mismatch(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    schema = {
        "properties": {
            "type": {"enum": ["basic", "fusion", "custom_invalid"]},
        },
    }
    _write(tmp_path / "registry/schema/skill.schema.json", json.dumps(schema))

    obs = KnowledgeContradictionSensor().scan(tmp_path, NOW)[0]
    assert obs.status == "drift"
    violations = obs.observed_state["violations"]
    assert any(v["rule"] == "skill-type-enum-alignment" for v in violations)




def test_knowledge_contradiction_detects_meta_tier_label_contradiction(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    meta_json = {
        "levels": {
            "order": ["0★", "1★"],
            "labels": {"0★": "Basic", "1★": "Awakened"},
        },
    }
    _write(tmp_path / "registry/schema/meta.json", json.dumps(meta_json))
    meta_md = (
        "| Level | Label |\n"
        "|---|---|\n"
        "| **0★** | **Master** |\n"
        "| **1★** | **Awakened** |\n"
    )
    _write(tmp_path / "META.md", meta_md)

    obs = KnowledgeContradictionSensor().scan(tmp_path, NOW)[0]
    assert obs.status == "drift"
    violations = obs.observed_state["violations"]
    assert any(v["rule"] == "meta-tier-label-contradiction" and "Master" in v["detail"] for v in violations)




def test_knowledge_contradiction_detects_meta_node_type_contradiction(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    meta_json = {
        "types": {
            "order": ["basic", "fusion"],
            "minPrereqs": {"basic": 0, "fusion": 1},
        },
    }
    _write(tmp_path / "registry/schema/meta.json", json.dumps(meta_json))
    meta_md = (
        "- **`basic`** — 0 prerequisites.\n"
        "- **`advanced`** — ≥ 1 prerequisite.\n"
    )
    _write(tmp_path / "META.md", meta_md)

    obs = KnowledgeContradictionSensor().scan(tmp_path, NOW)[0]
    assert obs.status == "drift"
    violations = obs.observed_state["violations"]
    assert any(v["rule"] == "meta-node-type-contradiction" for v in violations)




def test_knowledge_contradiction_detects_claude_schema_scope_contradiction(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    claude_md = (
        "## Branch Scope\n\n"
        "| Scope | Allowed Directories |\n"
        "|---|---|\n"
        "| **schema/** | `registry/schema/` only |\n"
    )
    _write(tmp_path / "CLAUDE.md", claude_md)

    obs = KnowledgeContradictionSensor().scan(tmp_path, NOW)[0]
    assert obs.status == "drift"
    violations = obs.observed_state["violations"]
    assert any(v["rule"] == "claude-schema-scope-contradiction" for v in violations)



def test_default_sensors_contains_evidence_link_health_sensor() -> None:
    sensors = default_sensors()
    assert any(isinstance(s, EvidenceLinkHealthSensor) for s in sensors)




def test_evidence_link_health_reports_healthy_on_valid_evidence(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    _write(tmp_path / "docs/evidence.json", "{}")
    content = _named_skill_with_evidence(
        "author/tool",
        [
            {
                "type": "repo",
                "source": "https://github.com/author/tool/blob/main/SKILL.md",
                "grade": "B",
            },
            {
                "type": "repo",
                "source": "https://github.com/author/tool/tree/main/skills",
                "grade": "B",
            },
            {
                "type": "benchmark-result",
                "source": "https://example.com/benchmarks/report",
                "harnessUrl": "https://github.com/author/tool/blob/main/benchmarks/run.py",
                "artifact": "docs/evidence.json",
                "grade": "A",
            },
        ],
    )
    _write(tmp_path / "registry/named/author/tool.md", content)

    observation = EvidenceLinkHealthSensor().scan(tmp_path, NOW)[0]

    assert observation.status == "healthy"
    assert observation.kind == "evidence_link_drift"
    assert observation.observed_state["healthy"] is True
    assert observation.observed_state["scannedFiles"] == 1
    assert observation.observed_state["checkedLinks"] == 5
    assert observation.observed_state["violationCount"] == 0
    assert observation.observed_state["violations"] == []




def test_evidence_link_health_detects_insecure_http_protocol(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    content = _named_skill_with_evidence(
        "author/insecure",
        [{"type": "repo", "source": "http://example.com/skill", "grade": "B"}],
    )
    _write(tmp_path / "registry/named/author/insecure.md", content)

    observation = EvidenceLinkHealthSensor().scan(tmp_path, NOW)[0]

    assert observation.status == "drift"
    assert observation.observed_state["healthy"] is False
    assert observation.observed_state["violationCount"] == 1
    error = observation.observed_state["violations"][0]["error"]
    assert "insecure protocol scheme 'http://'" in error




def test_evidence_link_health_detects_unsupported_protocol(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    content = _named_skill_with_evidence(
        "author/ftp",
        [{"type": "repo", "source": "ftp://example.com/archive.zip", "grade": "B"}],
    )
    _write(tmp_path / "registry/named/author/ftp.md", content)

    observation = EvidenceLinkHealthSensor().scan(tmp_path, NOW)[0]

    assert observation.status == "drift"
    assert observation.observed_state["healthy"] is False
    assert observation.observed_state["violationCount"] == 1
    error = observation.observed_state["violations"][0]["error"]
    assert "unsupported protocol scheme 'ftp'" in error




def test_evidence_link_health_detects_malformed_url_syntax(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    content = _named_skill_with_evidence(
        "author/malformed",
        [
            {"type": "repo", "source": "https://", "grade": "B"},
            {"type": "repo", "source": "https://example.com/foo bar", "grade": "B"},
        ],
    )
    _write(tmp_path / "registry/named/author/malformed.md", content)

    observation = EvidenceLinkHealthSensor().scan(tmp_path, NOW)[0]

    assert observation.status == "drift"
    assert observation.observed_state["violationCount"] == 2
    errors = [v["error"] for v in observation.observed_state["violations"]]
    assert any("missing domain/netloc" in err for err in errors)
    assert any("contains whitespace" in err for err in errors)




def test_evidence_link_health_detects_github_tree_single_file_link(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    content = _named_skill_with_evidence(
        "author/badtree",
        [
            {
                "type": "repo",
                "source": "https://github.com/author/badtree/tree/main/skills/foo/SKILL.md",
                "grade": "B",
            }
        ],
    )
    _write(tmp_path / "registry/named/author/badtree.md", content)

    observation = EvidenceLinkHealthSensor().scan(tmp_path, NOW)[0]

    assert observation.status == "drift"
    assert observation.observed_state["violationCount"] == 1
    error = observation.observed_state["violations"][0]["error"]
    assert "github.com single file link uses '/tree/' instead of '/blob/'" in error




def test_evidence_link_health_detects_missing_relative_artifact(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    content = _named_skill_with_evidence(
        "author/missing-art",
        [
            {
                "type": "benchmark-result",
                "source": "https://example.com/benchmarks",
                "artifact": "nonexistent/benchmarks/results.json",
                "grade": "A",
            }
        ],
    )
    _write(tmp_path / "registry/named/author/missing-art.md", content)

    observation = EvidenceLinkHealthSensor().scan(tmp_path, NOW)[0]

    assert observation.status == "drift"
    assert observation.observed_state["violationCount"] == 1
    error = observation.observed_state["violations"][0]["error"]
    assert "relative artifact does not exist: nonexistent/benchmarks/results.json" in error




def test_evidence_link_health_checks_links_subdict(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    content = _named_skill_with_evidence(
        "author/links-subdict",
        [
            {
                "type": "repo",
                "source": "https://github.com/author/tool",
                "links": {
                    "canonicalRepo": "http://insecure.example.com/repo",
                },
                "grade": "B",
            }
        ],
    )
    _write(tmp_path / "registry/named/author/links-subdict.md", content)

    observation = EvidenceLinkHealthSensor().scan(tmp_path, NOW)[0]

    assert observation.status == "drift"
    assert observation.observed_state["violationCount"] == 1
    v = observation.observed_state["violations"][0]
    assert v["field"] == "evidence[0].links.canonicalRepo"
    assert "insecure protocol scheme 'http://'" in v["error"]




def test_evidence_link_health_handles_empty_or_missing_named_directory(tmp_path: Path) -> None:
    observation = EvidenceLinkHealthSensor().scan(tmp_path, NOW)[0]
    assert observation.status == "healthy"
    assert observation.observed_state["scannedFiles"] == 0
    assert observation.observed_state["violationCount"] == 0




def test_evidence_link_health_reports_malformed_frontmatter(tmp_path: Path) -> None:
    _write(tmp_path / "registry/named/broken/corrupt.md", "---not yaml---")

    observation = EvidenceLinkHealthSensor().scan(tmp_path, NOW)[0]
    assert observation.status == "drift"
    assert observation.observed_state["violationCount"] == 1
    assert "invalid frontmatter" in observation.observed_state["violations"][0]["error"]


def test_default_sensors_contains_generated_projections_sensor() -> None:
    sensors = default_sensors()
    assert any(sensor.id == "generated-projections" for sensor in sensors)
    matching = [s for s in sensors if isinstance(s, GeneratedProjectionsSensor)]
    assert len(matching) == 1




def test_generated_projections_reports_healthy_on_clean_fixture(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)

    obs = GeneratedProjectionsSensor().scan(tmp_path, NOW)[0]

    assert obs.status == "healthy"
    assert obs.kind == "generated_projection_drift"
    assert obs.subject.id == "class-s-projections"
    assert obs.observed_state["consistent"] is True
    assert obs.observed_state["violationCount"] == 0
    assert obs.observed_state["canonicalNamedCount"] == 0
    assert obs.observed_state["indexedNamedCount"] == 0
    assert obs.confidence == 1.0




def test_generated_projections_with_matching_named_skills(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    _write(
        tmp_path / "registry/named/alice/my-tool.md",
        _named_markdown("alice/my-tool", "example"),
    )
    _write(
        tmp_path / "registry/named/bob/helper.md",
        _named_markdown("bob/helper", "example"),
    )
    index_data = {
        "buckets": {
            "example": [
                {"id": "alice/my-tool", "level": "1★"},
            ]
        },
        "awaitingClassification": [
            {"id": "bob/helper", "level": "0★"},
        ],
        "byContributor": {
            "alice": ["alice/my-tool"],
            "bob": ["bob/helper"],
        },
    }
    _write(tmp_path / "docs/graph/named/index.json", json.dumps(index_data))

    obs = GeneratedProjectionsSensor().scan(tmp_path, NOW)[0]

    assert obs.status == "healthy"
    assert obs.observed_state["canonicalNamedCount"] == 2
    assert obs.observed_state["indexedNamedCount"] == 2
    assert obs.observed_state["missingFromIndex"] == []
    assert obs.observed_state["extraInIndex"] == []
    assert obs.observed_state["violationCount"] == 0


@pytest.mark.parametrize(
    "missing_file",
    [
        "docs/graph/gaia.json",
        "docs/graph/named/index.json",
        "docs/api/v1/health.json",
    ],
)


def test_generated_projections_detects_missing_artifact(tmp_path: Path, missing_file: str) -> None:
    _make_clean_repo(tmp_path)
    (tmp_path / missing_file).unlink()

    obs = GeneratedProjectionsSensor().scan(tmp_path, NOW)[0]

    assert obs.status == "drift"
    assert missing_file in obs.observed_state["missingArtifacts"]
    assert any("required Class S artifact missing" in v["error"] and v["path"] == missing_file for v in obs.observed_state["violations"])


@pytest.mark.parametrize(
    "empty_file",
    [
        "docs/graph/gaia.json",
        "docs/graph/named/index.json",
        "docs/api/v1/health.json",
    ],
)


def test_generated_projections_detects_empty_artifact(tmp_path: Path, empty_file: str) -> None:
    _make_clean_repo(tmp_path)
    _write(tmp_path / empty_file, "")

    obs = GeneratedProjectionsSensor().scan(tmp_path, NOW)[0]

    assert obs.status == "drift"
    assert empty_file in obs.observed_state["emptyArtifacts"]
    assert any("Class S artifact is empty" in v["error"] and v["path"] == empty_file for v in obs.observed_state["violations"])




def test_generated_projections_detects_invalid_json(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    _write(tmp_path / "docs/graph/gaia.json", "{not valid json")

    obs = GeneratedProjectionsSensor().scan(tmp_path, NOW)[0]

    assert obs.status == "drift"
    assert "docs/graph/gaia.json" in obs.observed_state["corruptedArtifacts"]
    assert any("invalid JSON" in v["error"] and v["path"] == "docs/graph/gaia.json" for v in obs.observed_state["violations"])




def test_generated_projections_detects_non_object_json(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    _write(tmp_path / "docs/api/v1/health.json", '"plain string"')

    obs = GeneratedProjectionsSensor().scan(tmp_path, NOW)[0]

    assert obs.status == "drift"
    assert "docs/api/v1/health.json" in obs.observed_state["corruptedArtifacts"]
    assert any("must be a JSON object or array" in v["error"] for v in obs.observed_state["violations"])




def test_generated_projections_detects_missing_from_index(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    _write(
        tmp_path / "registry/named/alice/my-tool.md",
        _named_markdown("alice/my-tool", "example"),
    )
    _write(
        tmp_path / "registry/named/bob/unindexed.md",
        _named_markdown("bob/unindexed", "example"),
    )
    # Index only includes alice/my-tool
    index_data = {
        "buckets": {
            "example": [
                {"id": "alice/my-tool", "level": "1★"},
            ]
        },
        "awaitingClassification": [],
        "byContributor": {},
    }
    _write(tmp_path / "docs/graph/named/index.json", json.dumps(index_data))

    obs = GeneratedProjectionsSensor().scan(tmp_path, NOW)[0]

    assert obs.status == "drift"
    assert obs.observed_state["canonicalNamedCount"] == 2
    assert obs.observed_state["indexedNamedCount"] == 1
    assert obs.observed_state["missingFromIndex"] == ["bob/unindexed"]
    assert obs.observed_state["extraInIndex"] == []
    assert any("canonical named skill 'bob/unindexed' is missing from projection index" in v["error"] for v in obs.observed_state["violations"])




def test_generated_projections_detects_extra_in_index(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    _write(
        tmp_path / "registry/named/alice/my-tool.md",
        _named_markdown("alice/my-tool", "example"),
    )
    # Index includes phantom skill
    index_data = {
        "buckets": {
            "example": [
                {"id": "alice/my-tool", "level": "1★"},
                {"id": "charlie/phantom", "level": "2★"},
            ]
        },
        "awaitingClassification": [],
        "byContributor": {},
    }
    _write(tmp_path / "docs/graph/named/index.json", json.dumps(index_data))

    obs = GeneratedProjectionsSensor().scan(tmp_path, NOW)[0]

    assert obs.status == "drift"
    assert obs.observed_state["canonicalNamedCount"] == 1
    assert obs.observed_state["indexedNamedCount"] == 2
    assert obs.observed_state["missingFromIndex"] == []
    assert obs.observed_state["extraInIndex"] == ["charlie/phantom"]
    assert any("projection index contains extra un-canonical skill 'charlie/phantom'" in v["error"] for v in obs.observed_state["violations"])




def test_generated_projections_detects_malformed_named_frontmatter(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    _write(tmp_path / "registry/named/alice/broken.md", "---\nid:\n---\n")

    obs = GeneratedProjectionsSensor().scan(tmp_path, NOW)[0]

    assert obs.status == "drift"
    assert any("missing or invalid skill id" in v["error"] for v in obs.observed_state["violations"])




def test_generated_projections_is_deterministic(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    _write(
        tmp_path / "registry/named/alice/my-tool.md",
        _named_markdown("alice/my-tool", "example"),
    )
    sensor = GeneratedProjectionsSensor()

    obs1 = sensor.scan(tmp_path, NOW)[0]
    obs2 = sensor.scan(tmp_path, "2026-08-10T12:00:00Z")[0]

    assert obs1.debt_id == obs2.debt_id
    assert obs1.current_state == obs2.current_state
    assert obs1.observed_state == obs2.observed_state




def test_generated_projections_on_real_repo() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    obs = GeneratedProjectionsSensor().scan(repo_root, NOW)[0]

    assert obs.status == "healthy"
    assert obs.observed_state["consistent"] is True
    assert obs.observed_state["violationCount"] == 0
    assert obs.observed_state["canonicalNamedCount"] > 0
    assert obs.observed_state["indexedNamedCount"] > 0
    assert obs.observed_state["canonicalNamedCount"] == obs.observed_state["indexedNamedCount"]



def test_benchmark_freshness_sensor_on_clean_fixture(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)

    obs = BenchmarkFreshnessSensor().scan(tmp_path, NOW)[0]

    assert obs.status == "healthy"
    assert obs.kind == "benchmark_source_drift"
    assert obs.subject.id == "benchmark-sources"
    assert obs.observed_state["consistent"] is True
    assert obs.observed_state["violationCount"] == 0
    assert obs.observed_state["catalogBenchmarkCount"] == 1
    assert obs.observed_state["scannedRowsCount"] == 0




def test_benchmark_freshness_sensor_with_valid_named_benchmark(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    skill_content = (
        "---\n"
        "id: example/code-eval\n"
        "name: Code Eval\n"
        "genericSkillRef: example\n"
        "evidence:\n"
        "  - type: benchmark-result\n"
        "    benchmarkId: humaneval@v1.0\n"
        "    score: 0.85\n"
        "    unit: pass@1\n"
        "    provenance: verified\n"
        "    runAt: '2026-08-01T00:00:00Z'\n"
        "    attestor: https://ci.example.test/run/1\n"
        "    datasetHash: deadbeef1234\n"
        "    benchmarkInputHash: feedface5678\n"
        "    percentile: 95.5\n"
        "---\n\n"
        "## Overview\n"
    )
    _write(tmp_path / "registry/named/example/code-eval.md", skill_content)

    obs = BenchmarkFreshnessSensor().scan(tmp_path, NOW)[0]

    assert obs.status == "healthy"
    assert obs.observed_state["scannedRowsCount"] == 1
    assert obs.observed_state["violationCount"] == 0




def test_benchmark_freshness_sensor_reports_missing_catalog(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    (tmp_path / "registry/benchmark-sources.json").unlink()

    obs = BenchmarkFreshnessSensor().scan(tmp_path, NOW)[0]

    assert obs.status == "drift"
    assert obs.observed_state["violationCount"] == 1
    assert any("required catalog file does not exist" in v["error"] for v in obs.observed_state["violations"])




def test_benchmark_freshness_sensor_reports_invalid_json_catalog(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    _write(tmp_path / "registry/benchmark-sources.json", "not valid json {")

    obs = BenchmarkFreshnessSensor().scan(tmp_path, NOW)[0]

    assert obs.status == "drift"
    assert any("invalid JSON" in v["error"] for v in obs.observed_state["violations"])




def test_benchmark_freshness_sensor_reports_schema_violations(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    catalog_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": ["schemaVersion", "benchmarks"],
        "properties": {
            "schemaVersion": {"type": "string"},
            "benchmarks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "status"],
                    "properties": {
                        "id": {"type": "string"},
                        "status": {"enum": ["verified", "reported", "rejected"]},
                    },
                },
            },
        },
    }
    _write(tmp_path / "registry/schema/benchmarkSourceCatalog.schema.json", json.dumps(catalog_schema))
    broken_catalog = {
        "schemaVersion": "1.0.0",
        "benchmarks": [
            {"id": "test@v1.0", "status": "invalid-status"},
        ],
    }
    _write(tmp_path / "registry/benchmark-sources.json", json.dumps(broken_catalog))

    obs = BenchmarkFreshnessSensor().scan(tmp_path, NOW)[0]

    assert obs.status == "drift"
    assert any("schema /benchmarks/0/status" in v["error"] for v in obs.observed_state["violations"])




def test_benchmark_freshness_sensor_reports_duplicate_benchmark_ids_and_aliases(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    catalog = {
        "schemaVersion": "1.0.0",
        "benchmarks": [
            {
                "id": "humaneval@v1.0",
                "name": "HumanEval",
                "status": "reported",
                "mode": "external",
                "unit": "pass@1",
                "sourceUrl": "https://example.test",
                "methodologyUrl": "/benchmarks/he/",
                "aliases": ["shared-alias"],
            },
            {
                "id": "humaneval@v1.0",
                "name": "Duplicate ID",
                "status": "reported",
                "mode": "external",
                "unit": "pass@1",
                "sourceUrl": "https://example.test",
                "methodologyUrl": "/benchmarks/he2/",
                "aliases": [],
            },
            {
                "id": "other@v1.0",
                "name": "Other Benchmark",
                "status": "reported",
                "mode": "external",
                "unit": "pct",
                "sourceUrl": "https://example.test",
                "methodologyUrl": "/benchmarks/other/",
                "aliases": ["shared-alias"],
            },
        ],
    }
    _write(tmp_path / "registry/benchmark-sources.json", json.dumps(catalog))

    obs = BenchmarkFreshnessSensor().scan(tmp_path, NOW)[0]

    assert obs.status == "drift"
    errors = [v["error"] for v in obs.observed_state["violations"]]
    assert any("duplicate benchmarkId in catalog: 'humaneval@v1.0'" in err for err in errors)
    assert any("duplicate benchmark alias 'shared-alias'" in err for err in errors)




def test_benchmark_freshness_sensor_reports_unregistered_benchmark_id(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    skill_content = (
        "---\n"
        "id: example/unregistered\n"
        "name: Unregistered Benchmark Row\n"
        "genericSkillRef: example\n"
        "evidence:\n"
        "  - type: benchmark-result\n"
        "    benchmarkId: unknown-benchmark@v1.0\n"
        "    score: 99.0\n"
        "    unit: pct\n"
        "    provenance: reported\n"
        "---\n\n"
        "## Overview\n"
    )
    _write(tmp_path / "registry/named/example/unregistered.md", skill_content)

    obs = BenchmarkFreshnessSensor().scan(tmp_path, NOW)[0]

    assert obs.status == "drift"
    errors = [v["error"] for v in obs.observed_state["violations"]]
    assert any("references unregistered benchmarkId 'unknown-benchmark@v1.0'" in err for err in errors)




def test_benchmark_freshness_sensor_reports_missing_benchmark_id(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    skill_content = (
        "---\n"
        "id: example/missing-id\n"
        "name: Missing BenchmarkId\n"
        "genericSkillRef: example\n"
        "evidence:\n"
        "  - type: benchmark-result\n"
        "    score: 50.0\n"
        "    unit: pct\n"
        "---\n\n"
        "## Overview\n"
    )
    _write(tmp_path / "registry/named/example/missing-id.md", skill_content)

    obs = BenchmarkFreshnessSensor().scan(tmp_path, NOW)[0]

    assert obs.status == "drift"
    errors = [v["error"] for v in obs.observed_state["violations"]]
    assert any("missing benchmarkId" in err for err in errors)




def test_benchmark_freshness_sensor_reports_forbidden_self_attested(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    skill_content = (
        "---\n"
        "id: example/self-attested\n"
        "name: Self-Attested Benchmark\n"
        "genericSkillRef: example\n"
        "evidence:\n"
        "  - type: benchmark-result\n"
        "    benchmarkId: humaneval@v1.0\n"
        "    score: 0.9\n"
        "    unit: pass@1\n"
        "    provenance: self-attested\n"
        "---\n\n"
        "## Overview\n"
    )
    _write(tmp_path / "registry/named/example/self-attested.md", skill_content)

    obs = BenchmarkFreshnessSensor().scan(tmp_path, NOW)[0]

    assert obs.status == "drift"
    errors = [v["error"] for v in obs.observed_state["violations"]]
    assert any("forbidden provenance 'self-attested'" in err for err in errors)


@pytest.mark.parametrize("percentile_val", [-5.0, 105.0, "invalid-pct"])


def test_benchmark_freshness_sensor_reports_invalid_percentiles(tmp_path: Path, percentile_val: object) -> None:
    _make_clean_repo(tmp_path)
    skill_content = (
        "---\n"
        "id: example/bad-percentile\n"
        "name: Bad Percentile\n"
        "genericSkillRef: example\n"
        "evidence:\n"
        "  - type: benchmark-result\n"
        "    benchmarkId: humaneval@v1.0\n"
        "    score: 0.9\n"
        "    unit: pass@1\n"
        "    provenance: reported\n"
        f"    percentile: {percentile_val}\n"
        "---\n\n"
        "## Overview\n"
    )
    _write(tmp_path / "registry/named/example/bad-percentile.md", skill_content)

    obs = BenchmarkFreshnessSensor().scan(tmp_path, NOW)[0]

    assert obs.status == "drift"
    errors = [v["error"] for v in obs.observed_state["violations"]]
    assert any("percentile" in err for err in errors)




def test_benchmark_freshness_sensor_reports_missing_verified_receipt_fields(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    skill_content = (
        "---\n"
        "id: example/missing-receipt-fields\n"
        "name: Missing Verified Receipt Fields\n"
        "genericSkillRef: example\n"
        "evidence:\n"
        "  - type: benchmark-result\n"
        "    benchmarkId: humaneval@v1.0\n"
        "    score: 0.8\n"
        "    unit: pass@1\n"
        "    provenance: verified\n"
        "    runAt: '2026-08-01T00:00:00Z'\n"
        "    attestor: https://ci.example.test\n"
        "    # datasetHash and benchmarkInputHash missing\n"
        "---\n\n"
        "## Overview\n"
    )
    _write(tmp_path / "registry/named/example/missing-receipt-fields.md", skill_content)

    obs = BenchmarkFreshnessSensor().scan(tmp_path, NOW)[0]

    assert obs.status == "drift"
    errors = [v["error"] for v in obs.observed_state["violations"]]
    assert any("missing required field 'datasetHash'" in err for err in errors)
    assert any("missing required field 'benchmarkInputHash'" in err for err in errors)




def test_benchmark_freshness_sensor_reports_policy_inconsistencies(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    catalog = {
        "schemaVersion": "1.0.0",
        "benchmarks": [
            {
                "id": "candidate-scoring@v1.0",
                "name": "Candidate Scoring",
                "status": "candidate",
                "mode": "external",
                "unit": "pct",
                "sourceUrl": "https://example.test",
                "methodologyUrl": "/benchmarks/cs/",
                "scoring": {"scoresTrustMagnitude": True},
            },
            {
                "id": "push-not-ci@v1.0",
                "name": "Push Not Internal CI",
                "status": "reported",
                "mode": "external",
                "unit": "pct",
                "sourceUrl": "https://example.test",
                "methodologyUrl": "/benchmarks/pnc/",
                "push": {"enabled": True, "aliases": ["pnc"]},
            },
        ],
    }
    _write(tmp_path / "registry/benchmark-sources.json", json.dumps(catalog))

    obs = BenchmarkFreshnessSensor().scan(tmp_path, NOW)[0]

    assert obs.status == "drift"
    errors = [v["error"] for v in obs.observed_state["violations"]]
    assert any("candidate-scoring@v1.0: status 'candidate' must not score Trust Magnitude" in err for err in errors)
    assert any("push-not-ci@v1.0: push aliases require verified internal-ci status" in err for err in errors)




def test_benchmark_freshness_sensor_is_deterministic(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)
    sensor = BenchmarkFreshnessSensor()

    obs1 = sensor.scan(tmp_path, NOW)[0]
    obs2 = sensor.scan(tmp_path, "2026-08-10T12:00:00Z")[0]

    assert obs1.debt_id == obs2.debt_id
    assert obs1.current_state == obs2.current_state
    assert obs1.observed_state == obs2.observed_state

