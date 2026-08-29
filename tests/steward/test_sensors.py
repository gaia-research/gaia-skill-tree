from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from gaia_cli.steward.sensors import (
    AgentSkillMirrorSensor,
    BenchmarkFreshnessSensor,
    BundledSchemaMirrorSensor,
    DiscoveryGenericMappingSensor,
    RegistryIntegritySensor,
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
    meta_text = json.dumps({"types": {"minPrereqs": {"basic": 0, "fusion": 1}}})
    _write(root / "registry/schema/meta.json", meta_text)
    _write(root / "src/gaia_cli/data/registry/schema/meta.json", meta_text)
    node = {"id": "example", "type": "basic", "prerequisites": [], "derivatives": []}
    _write(root / "registry/nodes/basic/example.json", json.dumps(node))
    _write(root / ".agents/skills/example/SKILL.md", "# Example\n")
    _write(root / ".claude/skills/example/SKILL.md", "# Example\n")
    catalog = {
        "schemaVersion": "1.0.0",
        "benchmarks": [
            {
                "id": "humaneval@v1.0",
                "name": "HumanEval",
                "status": "verified",
                "mode": "internal-ci",
                "unit": "pass@1",
                "sourceUrl": "https://github.com/openai/human-eval",
                "methodologyUrl": "/benchmarks/humaneval-v1/",
                "aliases": ["humaneval"],
                "defaultProvenance": "verified",
                "scoring": {"scoresTrustMagnitude": True, "requiredFields": []},
                "push": {"enabled": True, "aliases": ["humaneval"]},
            }
        ],
    }
    _write(root / "registry/benchmark-sources.json", json.dumps(catalog))


def test_all_sensors_report_healthy_on_clean_fixture(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)

    observations = [
        BundledSchemaMirrorSensor().scan(tmp_path, NOW)[0],
        AgentSkillMirrorSensor().scan(tmp_path, NOW)[0],
        RegistryIntegritySensor().scan(tmp_path, NOW)[0],
        BenchmarkFreshnessSensor().scan(tmp_path, NOW)[0],
    ]

    assert [observation.status for observation in observations] == ["healthy"] * 4


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

