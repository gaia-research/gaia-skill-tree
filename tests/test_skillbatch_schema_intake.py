"""Schema-reconciliation tests for registry/schema/skillBatch.schema.json (RFC3).

RFC3 §3.5 re-enabled `gaia dev validate --intake` in CI. That check runs the
skill-batch schema against every batch under registry-for-review/skill-batches/.
The schema had drifted from its two real producers — the legacy
`gaia push --from-file` path (commands/pushFromFile.py) and the RFC2-B
discovery-packet adapter (intakeAdapter.py) — so a real intake batch failed with
"Additional properties are not allowed ('attribution', 'named', 'prerequisites'
were unexpected)".

These tests pin the reconciliation:
  (a) the shipped 20260711 --from-file fixture validates,
  (b) an adapter-produced batch (packet -> buildIntakeYaml -> from-file batch)
      validates,
  (c) additionalProperties:false STILL rejects a genuinely-unknown field (the
      guard RFC3 turned on was declared-around, not neutered).
"""

import hashlib
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

jsonschema = pytest.importorskip("jsonschema")

from gaia_cli.intakeAdapter import buildIntakeYaml  # noqa: E402
from gaia_cli.commands.pushFromFile import _skillEntryToProposed  # noqa: E402


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCHEMA_PATH = os.path.join(
    REPO_ROOT, "registry", "schema", "skillBatch.schema.json"
)
MIRROR_SCHEMA_PATH = os.path.join(
    REPO_ROOT, "src", "gaia_cli", "data", "registry", "schema",
    "skillBatch.schema.json",
)
FIXTURE_BATCH = os.path.join(
    REPO_ROOT, "registry-for-review", "skill-batches",
    "20260711142506-gaia-research-from-file.json",
)


def _loadSchema():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def _basePacket(**overrides):
    packet = {
        "contractVersion": "discovery-packet-v2",
        "candidateId": "alice/some-skill",
        "lifecycle": [
            "discovered", "fetched", "parsed", "normalized", "deduped",
            "mapped", "review-ready",
        ],
        "source": {
            "canonicalUrl": (
                "https://github.com/alice/some-skill/blob/main/SKILL.md"
            ),
            "frontmatter": {
                "name": "Some Skill",
                "description": "Does a thing well and is at least ten chars.",
            },
        },
        "normalized": {
            "name": "Some Skill",
            "description": "Does a thing well and is at least ten chars.",
        },
        "mappingOptions": [{
            "genericId": "research", "rationale": "Frozen strong match.",
            "similarity": 0.9, "matchTier": "strong",
        }],
        "decision": {
            "value": "MAP",
            "reasonCode": "strong-match",
            "genericId": "research",
        },
    }
    packet.update(overrides)
    generics = [{"id": "research", "kind": "generic"}]
    digest = lambda value: hashlib.sha256(  # noqa: E731
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    packet.setdefault("genericSnapshot", {
        "capturedAt": "2026-07-29T00:00:00Z",
        "command": "gaia dev list --generic --json",
        "generics": generics,
        "contentSha256": digest(generics),
        "mappingOptionsSha256": digest(packet.get("mappingOptions", [])),
    })
    packet.setdefault("l4Resolution", {
        "status": "approved",
        "generic": {
            "id": (packet.get("decision") or {}).get("genericId", "new-generic"),
            "name": "Some Capability",
            "description": "A vendor-neutral capability description for intake.",
            "type": "basic",
            "prerequisites": [],
        },
        "named": {"contributor": "alice", "skillName": "some-skill"},
        "skillFileUrl": "https://github.com/alice/some-skill/blob/main/SKILL.md",
    })
    return packet


def _adapterBatchFromPackets(packets):
    """Run packets through the adapter, then the --from-file proposedSkills
    shaping (which adds sourceRepo + lifecycle), producing a full batch dict."""
    intake = buildIntakeYaml(packets)
    sourceRepo = "gaia-research/gaia-skill-tree"
    proposed = [
        _skillEntryToProposed(entry, sourceRepo) for entry in intake["skills"]
    ]
    return {
        "batchId": "20260729000000-alice-from-file",
        "userId": "alice",
        "sourceRepo": sourceRepo,
        "generatedAt": "2026-07-29T00:00:00Z",
        "fromFile": True,
        "knownSkills": [],
        "proposedSkills": proposed,
        "curationHandoff": intake["curationHandoff"],
        # No similarity — a --from-file batch legitimately omits it.
    }


def test_shipped_fromfile_fixture_validates():
    """The real 20260711 --from-file batch must validate against the schema."""
    schema = _loadSchema()
    with open(FIXTURE_BATCH, encoding="utf-8") as f:
        batch = json.load(f)
    jsonschema.validate(instance=batch, schema=schema)


def test_adapter_produced_batch_validates():
    """A batch built from discovery packets via the adapter must validate.

    Exercises the adapter-specific keys (candidateId, mapsToGeneric, suite,
    attributionScope) plus the --from-file-added sourceRepo/lifecycle, and the
    fromFile=true similarity relaxation.
    """
    schema = _loadSchema()
    component = _basePacket(
        candidateId="alice/component-a",
        suite={"role": "component", "suiteId": "alice-suite"},
    )
    capstone = _basePacket(
        candidateId="alice/capstone",
        suite={
            "role": "capstone",
            "suiteId": "alice-suite",
            "componentCandidateIds": ["alice/component-a"],
        },
    )
    batch = _adapterBatchFromPackets([component, capstone])
    jsonschema.validate(instance=batch, schema=schema)


def test_fromfile_batch_may_omit_similarity():
    """fromFile=true relaxes the top-level similarity requirement."""
    schema = _loadSchema()
    batch = _adapterBatchFromPackets([_basePacket()])
    assert "similarity" not in batch
    jsonschema.validate(instance=batch, schema=schema)


def test_scan_batch_still_requires_similarity():
    """A non-fromFile (scan-produced) batch still requires similarity."""
    schema = _loadSchema()
    batch = {
        "batchId": "20260729000000-alice-scan",
        "userId": "alice",
        "sourceRepo": "alice/repo",
        "generatedAt": "2026-07-29T00:00:00Z",
        "knownSkills": [],
        "proposedSkills": [
            {
                "id": "some-skill",
                "name": "Some Skill",
                "type": "basic",
                "description": "A ten-plus-char description here.",
                "sourceRepo": "alice/repo",
            }
        ],
        # No fromFile, no similarity → must fail.
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=batch, schema=schema)


def test_additional_properties_guard_still_rejects_unknown_field():
    """additionalProperties:false must still reject a truly-unknown per-skill
    field — the guard was declared-around, not neutered."""
    schema = _loadSchema()
    batch = _adapterBatchFromPackets([_basePacket()])
    batch["proposedSkills"][0]["totallyUnknownField"] = "nope"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=batch, schema=schema)


def test_schema_mirrors_are_byte_identical():
    """registry/schema and the bundled src/gaia_cli/data mirror must not drift
    (scripts/validate.py meta-sync check)."""
    with open(SCHEMA_PATH, "rb") as f:
        canonical = f.read()
    with open(MIRROR_SCHEMA_PATH, "rb") as f:
        mirror = f.read()
    assert canonical == mirror
