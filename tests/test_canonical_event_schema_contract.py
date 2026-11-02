"""Strict schema proposal for canonical workflow timeline events.

These tests exercise the real staged event field shapes without invoking the
workflow or granting approval. Schema acceptance is contract coverage only.
"""
import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
MIRRORS = {
    "namedSkill.schema.json": [
        ROOT / "registry/schema/namedSkill.schema.json",
        ROOT / "src/gaia_cli/data/registry/schema/namedSkill.schema.json",
        ROOT / "docs/schema/namedSkill.schema.json",
    ],
    "skillTree.schema.json": [
        ROOT / "registry/schema/skillTree.schema.json",
        ROOT / "src/gaia_cli/data/registry/schema/skillTree.schema.json",
        ROOT / "docs/schema/skillTree.schema.json",
    ],
    "graph.schema.json": [
        ROOT / "registry/schema/graph.schema.json",
        ROOT / "src/gaia_cli/data/registry/schema/graph.schema.json",
        ROOT / "docs/schema/graph.schema.json",
    ],
    "skill.schema.json": [
        ROOT / "registry/schema/skill.schema.json",
        ROOT / "src/gaia_cli/data/registry/schema/skill.schema.json",
        ROOT / "docs/schema/skill.schema.json",
    ],
}
ACTIONS = (
    "migrate_evidence",
    "assertion_transition",
    "metric_refresh",
    "reconcile_owner",
)
EVENT_ID = "a" * 64


def load_schema(family):
    return json.loads(MIRRORS[family][0].read_bytes())


def canonical_event(action, *, tree=False):
    event = {
        "timestamp": "2026-11-03T12:34:56Z",
        "action": action,
        "decisionRef": "decision:test-2176",
        "eventId": EVENT_ID,
        "details": "Prepared canonical decision; no historical approval or award inferred.",
        "previousValue": "b" * 64,
        "newValue": "c" * 64,
    }
    if tree:
        event["skillId"] = "owner/skill"
    if action == "reconcile_owner":
        event["previousValue"] = "3★" if tree else "3★"
        event["newValue"] = "3★"
    return event


@pytest.mark.parametrize("family", MIRRORS)
def test_all_three_schema_mirrors_are_byte_identical_and_draft7_valid(family):
    mirrors = MIRRORS[family]
    canonical = mirrors[0].read_bytes()
    for mirror in mirrors[1:]:
        assert mirror.read_bytes() == canonical, f"schema mirror drift: {mirror}"
    jsonschema.Draft7Validator.check_schema(json.loads(canonical))


@pytest.mark.parametrize("family", MIRRORS)
@pytest.mark.parametrize("action", ACTIONS)
def test_real_canonical_action_shapes_validate_in_every_schema_family(family, action):
    schema = load_schema(family)
    event_schema = schema["definitions"]["timelineEvent"]
    validator = jsonschema.Draft7Validator(event_schema, format_checker=jsonschema.FormatChecker())
    event = canonical_event(action, tree=(family == "skillTree.schema.json"))
    errors = list(validator.iter_errors(event))
    assert not errors, [error.message for error in errors]


@pytest.mark.parametrize("family", MIRRORS)
@pytest.mark.parametrize("action", ACTIONS)
@pytest.mark.parametrize("missing", ["decisionRef", "eventId"])
def test_canonical_action_requires_each_linkage_field(family, action, missing):
    event = canonical_event(action, tree=(family == "skillTree.schema.json"))
    del event[missing]
    validator = jsonschema.Draft7Validator(load_schema(family)["definitions"]["timelineEvent"])
    assert any(missing in error.message for error in validator.iter_errors(event))


@pytest.mark.parametrize("family", MIRRORS)
@pytest.mark.parametrize(
    "mutate",
    [
        lambda event: event.update(eventId="A" * 64),
        lambda event: event.update(eventId="not-a-sha256"),
        lambda event: event.update(decisionRef="  "),
        lambda event: event.update(unknownLinkage="invented"),
    ],
)
def test_canonical_event_rejects_malformed_or_unknown_linkage(family, mutate):
    event = canonical_event("metric_refresh", tree=(family == "skillTree.schema.json"))
    mutate(event)
    validator = jsonschema.Draft7Validator(load_schema(family)["definitions"]["timelineEvent"])
    assert list(validator.iter_errors(event))


@pytest.mark.parametrize("family", MIRRORS)
def test_legacy_events_remain_valid_without_canonical_linkage(family):
    event = {"timestamp": "2026-11-03T12:34:56Z", "action": "rank_up"}
    if family == "skillTree.schema.json":
        event["skillId"] = "owner/skill"
    validator = jsonschema.Draft7Validator(
        load_schema(family)["definitions"]["timelineEvent"],
        format_checker=jsonschema.FormatChecker(),
    )
    assert not list(validator.iter_errors(event))


def test_evidence_revision_and_lifecycle_contract_remains_unchanged():
    """The event proposal does not widen or weaken the existing evidence contract."""
    import subprocess

    for filename in ("namedSkill.schema.json", "graph.schema.json", "skill.schema.json"):
        original = json.loads(subprocess.check_output(
            ["git", "show", f"HEAD:{MIRRORS[filename][0].relative_to(ROOT).as_posix()}"]
        ))
        proposed = load_schema(filename)
        assert proposed["definitions"]["evidenceEntry"] == original["definitions"]["evidenceEntry"]
