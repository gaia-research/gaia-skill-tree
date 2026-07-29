"""Tests for `gaia dev validate --intake` discovery-packet-v2 wiring (RFC3 §3.5)."""

import json
import shutil
from pathlib import Path

from gaia_cli.prefill import validateDiscoveryPackets

FIXTURE = Path(__file__).parent / "fixtures" / "discovery-packet-v2-valid.json"


def _packetsDir(root: Path) -> Path:
    d = root / "registry-for-review" / "discovery-packets"
    d.mkdir(parents=True, exist_ok=True)
    return d


def test_no_packets_dir_is_clean(tmp_path):
    errors, count = validateDiscoveryPackets(str(tmp_path))
    assert errors == []
    assert count == 0


def test_valid_packet_passes(tmp_path):
    d = _packetsDir(tmp_path)
    shutil.copy(FIXTURE, d / "testcontrib-test-skill.json")
    errors, count = validateDiscoveryPackets(str(tmp_path))
    assert count == 1
    assert errors == []


def test_malformed_packet_reported(tmp_path):
    d = _packetsDir(tmp_path)
    (d / "broken.json").write_text("{ not valid json", encoding="utf-8")
    errors, count = validateDiscoveryPackets(str(tmp_path))
    assert count == 1
    assert any("MALFORMED_PACKET" in e for e in errors)


def test_invalid_packet_reported(tmp_path):
    d = _packetsDir(tmp_path)
    packet = json.loads(FIXTURE.read_text(encoding="utf-8"))
    # Break the source lane — a stable validator error code.
    packet["source"]["sourceLane"] = "not-a-lane"
    (d / "bad.json").write_text(json.dumps(packet), encoding="utf-8")
    errors, count = validateDiscoveryPackets(str(tmp_path))
    assert count == 1
    assert any("INVALID_SOURCE_LANE" in e for e in errors)
