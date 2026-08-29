from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from gaia_cli.steward.sensors import (
    AgentSkillMirrorSensor,
    BundledSchemaMirrorSensor,
    DiscoveryGenericMappingSensor,
    EvidenceLinkHealthSensor,
    RegistryIntegritySensor,
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


def test_all_sensors_report_healthy_on_clean_fixture(tmp_path: Path) -> None:
    _make_clean_repo(tmp_path)

    observations = [
        BundledSchemaMirrorSensor().scan(tmp_path, NOW)[0],
        AgentSkillMirrorSensor().scan(tmp_path, NOW)[0],
        RegistryIntegritySensor().scan(tmp_path, NOW)[0],
        EvidenceLinkHealthSensor().scan(tmp_path, NOW)[0],
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
