import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "evidence", "scripts"))

from compile_data_lake import compileDataLake  # noqa: E402
from peer_review_source_packets import (  # noqa: E402
    MANIFEST_CONTRACT_VERSION,
    PACKET_CONTRACT_VERSION,
    expandPacket,
    iterPackets,
    loadManifest,
    validatePacket,
    writePeerReviewPartition,
)


def _base_packet(**overrides):
    packet = {
        "contractVersion": PACKET_CONTRACT_VERSION,
        "id": "rachel-addy-review-2026",
        "evidenceType": "peer-review",
        "source": {
            "url": "https://example.com/review",
            "title": "Detailed Peer Review",
            "author": "Rachel Addy",
            "date": "2026-07-31",
            "reviewers": 1,
            "independence": "independent-third-party",
        },
        "targets": [
            {
                "skillId": "alice/planning-skill",
                "genericSkillRef": "vertical-slice-planning",
                "primaryRepo": "https://github.com/alice/skills/blob/main/planning/SKILL.md",
                "attributionScope": "standalone",
                "confidence": "high",
                "notes": "Strong planning coverage.",
            },
            {
                "skillId": "bob/planning-skill",
                "genericSkillRef": "vertical-slice-planning",
                "primaryRepo": "https://github.com/bob/skills/blob/main/planning/SKILL.md",
                "attributionScope": "standalone",
                "confidence": "high",
                "notes": "Also reviewed independently.",
            },
        ],
    }
    packet.update(overrides)
    return packet


def _write_manifest(tmp_path, payload):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_valid_packet_expands_to_multiple_rows_and_preserves_peer_review_metadata(tmp_path):
    manifest_path = _write_manifest(
        tmp_path,
        {
            "contractVersion": MANIFEST_CONTRACT_VERSION,
            "packets": [_base_packet()],
        },
    )

    manifest = loadManifest(str(manifest_path))
    packets = list(iterPackets(manifest))
    assert len(packets) == 1

    rows = expandPacket(packets[0])
    assert [row["skillId"] for row in rows] == [
        "alice/planning-skill",
        "bob/planning-skill",
    ]
    assert all(row["source"] == "https://example.com/review" for row in rows)
    assert all(row["reviewers"] == 1 for row in rows)
    assert all(row["packetId"] == "rachel-addy-review-2026" for row in rows)
    assert all(row["genericSkillRef"] == "vertical-slice-planning" for row in rows)
    assert rows[0]["notes"] == "Strong planning coverage."
    assert rows[1]["notes"] == "Also reviewed independently."

    partition_path = writePeerReviewPartition(str(tmp_path / "by-type"), rows)
    partition_text = open(partition_path, encoding="utf-8").read()
    assert partition_text.count("## Skill: `") == 2
    assert partition_text.count("[https://example.com/review](https://example.com/review)") == 2
    assert "- **Reviewers:** 1" in partition_text
    assert "- **Packet ID:** `rachel-addy-review-2026`" in partition_text
    assert "- **Generic Skill Ref:** `vertical-slice-planning`" in partition_text
    assert "Strong planning coverage." in partition_text
    assert "Also reviewed independently." in partition_text


def test_peer_review_partition_compiles_into_unified_lake_with_separate_skill_sections(tmp_path):
    rows = expandPacket(_base_packet())
    by_type = tmp_path / "evidence" / "by-type"
    lake_dir = tmp_path / "evidence"
    collectors_dir = tmp_path / "evidence" / "collectors"

    partition_path = writePeerReviewPartition(str(by_type), rows)
    assert partition_path.endswith(os.path.join("by-type", "peer-review.md"))

    skills = compileDataLake(
        sourcesDir=str(by_type),
        collectorsDir=str(collectors_dir),
        lakeDir=str(lake_dir),
    )

    assert set(skills) == {"alice/planning-skill", "bob/planning-skill"}
    assert skills["alice/planning-skill"]["evidenceTypes"] == ["peer-review"]
    assert skills["bob/planning-skill"]["evidenceTypes"] == ["peer-review"]

    lake_text = (lake_dir / "unified_evidence_lake.md").read_text(encoding="utf-8")
    assert "## Skill: <a name=\"skill-aliceplanning-skill\"></a>`alice/planning-skill`" in lake_text
    assert "## Skill: <a name=\"skill-bobplanning-skill\"></a>`bob/planning-skill`" in lake_text
    assert "#### E1: `peer-review` (peer-review)" in lake_text
    assert "- **Packet ID:** `rachel-addy-review-2026`" in lake_text
    assert "- **Generic Skill Ref:** `vertical-slice-planning`" in lake_text
    assert "Strong planning coverage." in lake_text
    assert "Also reviewed independently." in lake_text


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (lambda packet: packet.update({"evidenceType": "benchmark-result"}), "exactly 'peer-review'"),
        (lambda packet: packet.update({"targets": []}), "non-empty list"),
        (
            lambda packet: packet["targets"][0].update({"skillId": "not-a-valid-skill-id"}),
            "contributor/skill format",
        ),
        (
            lambda packet: packet["source"].update({"stars": 5}),
            "forbidden strength fields",
        ),
    ],
)
def test_validate_packet_rejects_invalid_packets(mutator, message):
    packet = _base_packet()
    mutator(packet)
    with pytest.raises(ValueError, match=message):
        validatePacket(packet)
