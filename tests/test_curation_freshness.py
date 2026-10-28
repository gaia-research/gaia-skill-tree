import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gaia_cli.curation.freshness import verifyPacketFreshness
from gaia_cli.intakeAdapter import _canonicalDigest


def _fixture(tmp_path):
    root = tmp_path
    nodes = root / "registry" / "nodes" / "basic"
    nodes.mkdir(parents=True)
    definition = {"id": "generic", "name": "Generic", "description": "A generic capability.", "type": "basic", "prerequisites": []}
    (nodes / "generic.json").write_text(json.dumps(definition), encoding="utf-8")
    gaia = root / "registry" / "gaia.json"
    gaia.parent.mkdir(exist_ok=True)
    gaia.write_text(json.dumps({"skills": [definition]}), encoding="utf-8")
    (root / "registry" / "named").mkdir()
    generics = [{"id": "generic", "name": "Generic", "kind": "generic"}]
    content = b"---\nname: Candidate\ndescription: Source.\n---\n"
    packet = {
        "contractVersion": "discovery-packet-v2",
        "candidateId": "author/candidate",
        "lifecycle": ["discovered", "fetched", "parsed", "normalized", "deduped"],
        "source": {
            "canonicalUrl": "https://github.com/author/candidate/blob/main/SKILL.md",
            "hostRepository": "https://github.com/author/candidate",
            "contentSha256": hashlib.sha256(content).hexdigest(),
            "fetchedAt": "2026-01-02T03:04:05+00:00",
        },
        "genericSnapshot": {
            "generics": generics,
            "contentSha256": _canonicalDigest(generics),
            "semanticGenerics": {"generic": definition},
            "semanticCatalogSha256": _canonicalDigest({"generic": definition}),
        },
        "exactDedupe": {"matched": False, "checked": True},
    }
    return root, packet, content


def test_verify_packet_freshness_accepts_consistent_synthetic_sources(tmp_path):
    root, packet, content = _fixture(tmp_path)
    errors = verifyPacketFreshness(packet, root, fetcher=lambda _url: content)
    assert errors == []


def test_verify_packet_freshness_rejects_stale_generic_snapshot(tmp_path):
    root, packet, content = _fixture(tmp_path)
    packet["genericSnapshot"]["generics"][0]["id"] = "old-generic"
    packet["genericSnapshot"]["contentSha256"] = _canonicalDigest(packet["genericSnapshot"]["generics"])
    errors = verifyPacketFreshness(packet, root, fetcher=lambda _url: content)
    assert "generic snapshot is stale" in errors


def test_verify_packet_freshness_rejects_description_only_snapshot_drift(tmp_path):
    root, packet, content = _fixture(tmp_path)
    packet["genericSnapshot"]["generics"][0]["name"] = "Changed"
    packet["genericSnapshot"]["contentSha256"] = _canonicalDigest(packet["genericSnapshot"]["generics"])
    errors = verifyPacketFreshness(packet, root, fetcher=lambda _url: content)
    assert "generic snapshot is stale" in errors


def test_verify_packet_freshness_rejects_description_only_selected_definition_drift(tmp_path):
    root, packet, content = _fixture(tmp_path)
    packet["mappingOptions"] = [{"genericId": "generic"}]
    packet["genericSnapshot"]["semanticGenerics"]["generic"]["description"] = "Changed meaning."
    errors = verifyPacketFreshness(packet, root, fetcher=lambda _url: content)
    assert "selected generic semantic definition is stale" in errors


def test_verify_packet_freshness_fails_closed_on_canonical_parse_failure(tmp_path):
    root, packet, content = _fixture(tmp_path)
    (root / "registry/nodes/basic/generic.json").write_text("{")
    errors = verifyPacketFreshness(packet, root, fetcher=lambda _url: content)
    assert any("unavailable or malformed" in error for error in errors)


def test_verify_packet_freshness_rejects_stale_source_digest(tmp_path):
    root, packet, _content = _fixture(tmp_path)
    errors = verifyPacketFreshness(packet, root, fetcher=lambda _url: b"new source bytes")
    assert "source content digest mismatch (stale snapshot)" in errors


def test_verify_packet_freshness_fails_closed_when_fetch_unavailable(tmp_path):
    root, packet, _content = _fixture(tmp_path)
    errors = verifyPacketFreshness(packet, root, fetcher=lambda _url: (_ for _ in ()).throw(OSError("offline")))
    assert "source freshness verification unavailable" in errors


def test_verify_packet_freshness_rejects_unexecuted_dedupe_lifecycle(tmp_path):
    root, packet, content = _fixture(tmp_path)
    packet["exactDedupe"] = {"matched": False}
    errors = verifyPacketFreshness(packet, root, fetcher=lambda _url: content)
    assert "deduped lifecycle lacks executed exact-dedupe check" in errors
