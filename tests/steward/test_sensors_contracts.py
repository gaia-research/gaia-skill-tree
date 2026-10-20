"""Mandatory sensor categories for the contract sensor family (handover §3)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gaia_cli.steward.primitives import SensorUnavailable
from gaia_cli.steward.sensors_contracts import (
    FrontendContractSensor,
    SchemaValiditySensor,
    TimelineCausalitySensor,
)
from tests.steward.sensor_fixtures import commit_all, make_repo, tree_digest, write_files

NOW = "2026-10-20T12:00:00Z"

VALID_SCHEMA = json.dumps(
    {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "https://example.invalid/schema/alpha.schema.json",
        "type": "object",
        "definitions": {"name": {"type": "string"}},
        "properties": {"name": {"$ref": "#/definitions/name"}},
    }
)


def _plain_dir(root: Path, files: dict[str, str]) -> Path:
    """A directory that is not a Git worktree."""

    root.mkdir(parents=True, exist_ok=True)
    write_files(root, files)
    return root


def _findings(observations) -> list[tuple[str, str, dict]]:
    return [
        (obs.kind, obs.subject.id, finding)
        for obs in observations
        for finding in obs.observed_state["findings"]
    ]


# ---------------------------------------------------------------------------
# schema-validity
# ---------------------------------------------------------------------------


def test_schema_clean_registry_is_zero(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path / "repo",
        {
            "registry/schema/alpha.schema.json": VALID_SCHEMA,
            "registry/schema/beta.schema.json": json.dumps({"type": "string"}),
        },
    )
    assert SchemaValiditySensor().scan(repo, NOW) == []


def test_schema_invalid_json_exact_finding(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path / "repo",
        {"registry/schema/broken.schema.json": '{"type": "object",}\n'},
    )
    observations = SchemaValiditySensor().scan(repo, NOW)
    assert len(observations) == 1
    obs = observations[0]
    assert obs.kind == "schema_contract_drift"
    assert obs.subject.type == "schema"
    assert obs.subject.id == "registry/schema/broken.schema.json"
    assert obs.observed_state["findingCount"] == 1
    finding = obs.observed_state["findings"][0]
    assert finding["rule"] == "invalid-json"
    # The stdlib wording varies by Python release; the position is the contract.
    assert finding["detail"].endswith("at line 1 column 18")


def test_schema_invalid_schema_exact_finding(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path / "repo",
        {"registry/schema/bad-type.schema.json": json.dumps({"type": "nonsense"})},
    )
    observations = SchemaValiditySensor().scan(repo, NOW)
    assert [(item[0], item[2]["rule"]) for item in _findings(observations)] == [
        ("schema_contract_drift", "invalid-schema")
    ]


def test_schema_unresolved_file_ref_exact_finding(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path / "repo",
        {
            "registry/schema/alpha.schema.json": json.dumps(
                {"type": "object", "properties": {"x": {"$ref": "missing.schema.json"}}}
            )
        },
    )
    observations = SchemaValiditySensor().scan(repo, NOW)
    found = _findings(observations)
    assert [(item[1], item[2]["rule"]) for item in found] == [
        ("registry/schema/alpha.schema.json", "unresolved-local-ref")
    ]
    assert "missing.schema.json" in found[0][2]["detail"]


def test_schema_unresolved_pointer_exact_finding(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path / "repo",
        {
            "registry/schema/alpha.schema.json": json.dumps(
                {
                    "type": "object",
                    "definitions": {"name": {"type": "string"}},
                    "properties": {"x": {"$ref": "#/definitions/absent"}},
                }
            )
        },
    )
    found = _findings(SchemaValiditySensor().scan(repo, NOW))
    assert [item[2]["rule"] for item in found] == ["unresolved-local-ref"]
    assert "#/definitions/absent" in found[0][2]["detail"]


def test_schema_duplicate_id_attaches_to_both(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path / "repo",
        {
            "registry/schema/alpha.schema.json": VALID_SCHEMA,
            "registry/schema/gamma.schema.json": VALID_SCHEMA,
        },
    )
    observations = SchemaValiditySensor().scan(repo, NOW)
    assert sorted(obs.subject.id for obs in observations) == [
        "registry/schema/alpha.schema.json",
        "registry/schema/gamma.schema.json",
    ]
    for obs in observations:
        rules = [item["rule"] for item in obs.observed_state["findings"]]
        assert rules == ["duplicate-id"]


def test_schema_near_misses_are_not_findings(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path / "repo",
        {
            "registry/schema/alpha.schema.json": json.dumps(
                {
                    "type": "object",
                    "definitions": {"name": {"type": "string"}},
                    # A ref to an existing sibling file is resolved, not flagged.
                    "properties": {
                        "sibling": {"$ref": "beta.schema.json"},
                        "name": {"$ref": "#/definitions/name"},
                        # A remote ref is never fetched, so it is out of scope.
                        "remote": {"$ref": "https://example.invalid/other.json#/x"},
                        # A plain-name anchor is not a JSON pointer and is not verified.
                        "anchored": {"$ref": "#named-anchor"},
                    },
                    # A literal "$ref" inside example data is not a reference.
                    "examples": [{"$ref": "not-a-file.json"}],
                }
            ),
            "registry/schema/beta.schema.json": json.dumps({"type": "string"}),
        },
    )
    assert SchemaValiditySensor().scan(repo, NOW) == []


def test_schema_nested_evidence_schema_is_not_inventoried(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path / "repo",
        {
            "registry/schema/alpha.schema.json": VALID_SCHEMA,
            "registry/schema/evidence/nested.schema.json": '{"broken":',
        },
    )
    assert SchemaValiditySensor().scan(repo, NOW) == []


def test_schema_non_utf8_is_a_finding_not_a_crash(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    make_repo(repo, {"registry/schema/alpha.schema.json": VALID_SCHEMA})
    (repo / "registry/schema/latin.schema.json").write_bytes(b'{"title": "caf\xe9"}')
    commit_all(repo, "add latin-1 schema")
    found = _findings(SchemaValiditySensor().scan(repo, NOW))
    assert [(item[1], item[2]["rule"]) for item in found] == [
        ("registry/schema/latin.schema.json", "invalid-json")
    ]


def test_schema_missing_inventory_is_unavailable(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo", {"README.md": "no schemas here\n"})
    with pytest.raises(SensorUnavailable):
        SchemaValiditySensor().scan(repo, NOW)


def test_schema_oversize_input_is_unavailable(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path / "repo",
        {"registry/schema/alpha.schema.json": VALID_SCHEMA},
    )
    (repo / "registry/schema/huge.schema.json").write_text(
        " " * (2 * 1024 * 1024 + 1), encoding="utf-8"
    )
    commit_all(repo, "add oversize schema")
    with pytest.raises(SensorUnavailable):
        SchemaValiditySensor().scan(repo, NOW)


def test_schema_non_git_is_unavailable(tmp_path: Path) -> None:
    plain = _plain_dir(tmp_path / "plain", {"registry/schema/alpha.schema.json": VALID_SCHEMA})
    with pytest.raises(SensorUnavailable):
        SchemaValiditySensor().scan(plain, NOW)


def test_schema_repeat_scan_is_identical(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path / "repo",
        {
            "registry/schema/alpha.schema.json": VALID_SCHEMA,
            "registry/schema/gamma.schema.json": VALID_SCHEMA,
            "registry/schema/bad.schema.json": "{",
        },
    )
    sensor = SchemaValiditySensor()
    first = [obs.to_dict() for obs in sensor.scan(repo, NOW)]
    second = [obs.to_dict() for obs in sensor.scan(repo, NOW)]
    assert first and first == second


def test_schema_scan_is_read_only(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path / "repo",
        {"registry/schema/bad.schema.json": '{"type": "nonsense"}'},
    )
    before = tree_digest(repo)
    SchemaValiditySensor().scan(repo, NOW)
    assert tree_digest(repo) == before


def test_schema_recovery_removes_finding(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path / "repo",
        {"registry/schema/bad.schema.json": "{"},
    )
    assert len(SchemaValiditySensor().scan(repo, NOW)) == 1
    write_files(repo, {"registry/schema/bad.schema.json": json.dumps({"type": "string"})})
    commit_all(repo, "repair schema")
    assert SchemaValiditySensor().scan(repo, NOW) == []


# ---------------------------------------------------------------------------
# timeline-causality
# ---------------------------------------------------------------------------


def _skill(identity: str | None, timeline: str) -> str:
    header = f"id: {identity}\n" if identity is not None else ""
    return f"---\n{header}name: sample\ntimeline:\n{timeline}---\n\nBody text.\n"


def _event(stamp: str, action: str = "note") -> str:
    return f"- timestamp: {stamp}\n  action: {action}\n"


def test_timeline_clean_skill_is_zero(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path / "repo",
        {
            "registry/named/owner/alpha.md": _skill(
                "owner/alpha",
                _event("'2026-06-10T05:38:16Z'") + _event("'2026-06-11T05:38:16Z'"),
            )
        },
    )
    assert TimelineCausalitySensor().scan(repo, NOW) == []


def test_timeline_out_of_order_exact_finding(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path / "repo",
        {
            "registry/named/owner/alpha.md": _skill(
                "owner/alpha",
                _event("'2026-06-11T00:00:00Z'") + _event("'2026-06-10T00:00:00Z'"),
            )
        },
    )
    observations = TimelineCausalitySensor().scan(repo, NOW)
    assert len(observations) == 1
    obs = observations[0]
    assert obs.kind == "timeline_causality_drift"
    assert obs.subject.type == "named-skill"
    assert obs.subject.id == "owner/alpha"
    assert obs.observed_state["findings"] == [
        {
            "rule": "out-of-order",
            "detail": "event 1 at 2026-06-10T00:00:00Z precedes event 0 at 2026-06-11T00:00:00Z",
        }
    ]


def test_timeline_future_timestamp_exact_finding(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path / "repo",
        {"registry/named/owner/alpha.md": _skill("owner/alpha", _event("'2026-12-01T00:00:00Z'"))},
    )
    found = _findings(TimelineCausalitySensor().scan(repo, NOW))
    assert [item[2]["rule"] for item in found] == ["future-timestamp"]


def test_timeline_unparseable_and_missing_timestamps(tmp_path: Path) -> None:
    timeline = _event("'not-a-date'") + "- action: note\n  details: no stamp\n"
    repo = make_repo(
        tmp_path / "repo",
        {"registry/named/owner/alpha.md": _skill("owner/alpha", timeline)},
    )
    found = _findings(TimelineCausalitySensor().scan(repo, NOW))
    assert [item[2]["rule"] for item in found] == ["unparseable-timestamp", "unparseable-timestamp"]
    assert "event 0" in found[0][2]["detail"]
    assert "event 1" in found[1][2]["detail"]


def test_timeline_equal_timestamps_are_in_order(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path / "repo",
        {
            "registry/named/owner/alpha.md": _skill(
                "owner/alpha",
                _event("'2026-06-10T05:38:16Z'") + _event("'2026-06-10T05:38:16Z'"),
            )
        },
    )
    assert TimelineCausalitySensor().scan(repo, NOW) == []


def test_timeline_date_only_values_compare_by_day(tmp_path: Path) -> None:
    # Unquoted YAML dates parse to date objects. Same-day mixing with a full
    # timestamp is in order; a later day is still caught as out-of-order.
    same_day = make_repo(
        tmp_path / "same",
        {
            "registry/named/owner/alpha.md": _skill(
                "owner/alpha",
                _event("2026-06-10") + _event("'2026-06-10T09:00:00Z'"),
            )
        },
    )
    assert TimelineCausalitySensor().scan(same_day, NOW) == []

    earlier_day = make_repo(
        tmp_path / "earlier",
        {
            "registry/named/owner/alpha.md": _skill(
                "owner/alpha",
                _event("'2026-06-12T09:00:00Z'") + _event("2026-06-10"),
            )
        },
    )
    found = _findings(TimelineCausalitySensor().scan(earlier_day, NOW))
    assert [item[2]["rule"] for item in found] == ["out-of-order"]


def test_timeline_unparseable_frontmatter_is_skipped_and_counted(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path / "repo",
        {
            "registry/named/owner/broken.md": "---\nid: owner/broken\ntimeline: [unclosed\n---\nBody\n",
            "registry/named/owner/no-fence.md": "id: owner/no-fence\nno fences here\n",
            "registry/named/owner/good.md": _skill("owner/good", _event("'2026-06-10T00:00:00Z'")),
        },
    )
    observations, stats = TimelineCausalitySensor().scan_with_stats(repo, NOW)
    assert observations == []
    assert stats["skippedUnparseableFrontmatter"] == 2
    assert stats["skillsWithTimeline"] == 1


def test_timeline_id_falls_back_to_path_and_collisions_split(tmp_path: Path) -> None:
    bad_order = _event("'2026-06-11T00:00:00Z'") + _event("'2026-06-10T00:00:00Z'")
    repo = make_repo(
        tmp_path / "repo",
        {
            "registry/named/owner/no-id.md": _skill(None, bad_order),
            "registry/named/owner/twin-a.md": _skill("owner/twin", bad_order),
            "registry/named/owner/twin-b.md": _skill("owner/twin", bad_order),
        },
    )
    ids = sorted(obs.subject.id for obs in TimelineCausalitySensor().scan(repo, NOW))
    assert ids == [
        "registry/named/owner/no-id.md",
        "registry/named/owner/twin-a.md",
        "registry/named/owner/twin-b.md",
    ]


def test_timeline_missing_inventory_is_unavailable(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo", {"README.md": "nothing\n"})
    with pytest.raises(SensorUnavailable):
        TimelineCausalitySensor().scan(repo, NOW)


def test_timeline_unparseable_observed_at_is_unavailable(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path / "repo",
        {"registry/named/owner/alpha.md": _skill("owner/alpha", _event("'2026-06-10T00:00:00Z'"))},
    )
    with pytest.raises(SensorUnavailable):
        TimelineCausalitySensor().scan(repo, "yesterday")


def test_timeline_non_git_is_unavailable(tmp_path: Path) -> None:
    plain = _plain_dir(
        tmp_path / "plain",
        {"registry/named/owner/alpha.md": _skill("owner/alpha", _event("'2026-06-10T00:00:00Z'"))},
    )
    with pytest.raises(SensorUnavailable):
        TimelineCausalitySensor().scan(plain, NOW)


def test_timeline_repeat_scan_is_identical(tmp_path: Path) -> None:
    bad_order = _event("'2026-06-11T00:00:00Z'") + _event("'2026-06-10T00:00:00Z'")
    repo = make_repo(
        tmp_path / "repo",
        {
            "registry/named/owner/a.md": _skill("owner/a", bad_order),
            "registry/named/owner/b.md": _skill("owner/b", _event("'2099-01-01T00:00:00Z'")),
        },
    )
    sensor = TimelineCausalitySensor()
    first = [obs.to_dict() for obs in sensor.scan(repo, NOW)]
    second = [obs.to_dict() for obs in sensor.scan(repo, NOW)]
    assert len(first) == 2 and first == second


def test_timeline_scan_is_read_only(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path / "repo",
        {
            "registry/named/owner/a.md": _skill(
                "owner/a", _event("'2026-06-11T00:00:00Z'") + _event("'2026-06-10T00:00:00Z'")
            )
        },
    )
    before = tree_digest(repo)
    TimelineCausalitySensor().scan(repo, NOW)
    assert tree_digest(repo) == before


def test_timeline_recovery_removes_finding(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path / "repo",
        {
            "registry/named/owner/a.md": _skill(
                "owner/a", _event("'2026-06-11T00:00:00Z'") + _event("'2026-06-10T00:00:00Z'")
            )
        },
    )
    assert len(TimelineCausalitySensor().scan(repo, NOW)) == 1
    write_files(
        repo,
        {
            "registry/named/owner/a.md": _skill(
                "owner/a", _event("'2026-06-10T00:00:00Z'") + _event("'2026-06-11T00:00:00Z'")
            )
        },
    )
    commit_all(repo, "reorder timeline")
    assert TimelineCausalitySensor().scan(repo, NOW) == []


# ---------------------------------------------------------------------------
# frontend-contract
# ---------------------------------------------------------------------------

CLEAN_PAGE = (
    "<!doctype html>\n"
    '<html lang="en">\n'
    "<head>\n"
    '<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
    "<title>Clean page</title>\n"
    "</head>\n"
    "<body><img src=\"a.png\" alt=\"A diagram\"></body>\n"
    "</html>\n"
)


def test_frontend_clean_page_is_zero(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo", {"docs/clean.html": CLEAN_PAGE})
    assert FrontendContractSensor().scan(repo, NOW) == []


def test_frontend_missing_lang_exact_finding(tmp_path: Path) -> None:
    page = CLEAN_PAGE.replace('<html lang="en">', "<html>")
    repo = make_repo(tmp_path / "repo", {"docs/page.html": page})
    observations = FrontendContractSensor().scan(repo, NOW)
    assert len(observations) == 1
    obs = observations[0]
    assert obs.kind == "frontend_contract_drift"
    assert obs.subject.type == "html-page"
    assert obs.subject.id == "docs/page.html"
    assert obs.observed_state["findings"] == [{"rule": "missing-lang", "line": 2}]


def test_frontend_missing_viewport_reports_head_line(tmp_path: Path) -> None:
    page = CLEAN_PAGE.replace(
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n', ""
    )
    repo = make_repo(tmp_path / "repo", {"docs/page.html": page})
    found = _findings(FrontendContractSensor().scan(repo, NOW))
    assert found == [("frontend_contract_drift", "docs/page.html", {"rule": "missing-viewport", "line": 3})]


def test_frontend_missing_or_blank_title(tmp_path: Path) -> None:
    no_title = CLEAN_PAGE.replace("<title>Clean page</title>\n", "")
    blank_title = CLEAN_PAGE.replace("<title>Clean page</title>", "<title>   </title>")
    repo = make_repo(
        tmp_path / "repo",
        {"docs/no-title.html": no_title, "docs/blank-title.html": blank_title},
    )
    found = _findings(FrontendContractSensor().scan(repo, NOW))
    assert sorted((item[1], item[2]["rule"]) for item in found) == [
        ("docs/blank-title.html", "missing-title"),
        ("docs/no-title.html", "missing-title"),
    ]


def test_frontend_img_missing_alt_exact_finding(tmp_path: Path) -> None:
    page = CLEAN_PAGE.replace('<body><img src="a.png" alt="A diagram"></body>', "<body>\n<img src=\"b.png\">\n</body>")
    repo = make_repo(tmp_path / "repo", {"docs/page.html": page})
    found = _findings(FrontendContractSensor().scan(repo, NOW))
    assert found == [("frontend_contract_drift", "docs/page.html", {"rule": "img-missing-alt", "line": 9})]


def test_frontend_empty_alt_is_not_a_finding(tmp_path: Path) -> None:
    page = CLEAN_PAGE.replace('alt="A diagram"', 'alt=""')
    repo = make_repo(tmp_path / "repo", {"docs/decorative.html": page})
    assert FrontendContractSensor().scan(repo, NOW) == []


def test_frontend_fragment_is_skipped_and_counted(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path / "repo",
        {
            "docs/partials/card.html": '<div class="card"><img src="x.png"></div>\n',
            "docs/clean.html": CLEAN_PAGE,
        },
    )
    observations, stats = FrontendContractSensor().scan_with_stats(repo, NOW)
    assert observations == []
    assert stats["skippedFragment"] == 1


def test_frontend_excluded_generated_directories_are_not_scanned(tmp_path: Path) -> None:
    broken = "<html><body><img src=\"x.png\"></body></html>\n"
    repo = make_repo(
        tmp_path / "repo",
        {
            "docs/u/someone/index.html": broken,
            "docs/api/index.html": broken,
            "docs/og/card.html": broken,
            "docs/graph/index.html": broken,
            "docs/okf/index.html": broken,
            "docs/experiments/lab/index.html": broken,
            "docs/clean.html": CLEAN_PAGE,
        },
    )
    assert FrontendContractSensor().scan(repo, NOW) == []


def test_frontend_missing_inventory_is_unavailable(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path / "repo",
        {"docs/u/someone/index.html": CLEAN_PAGE, "README.md": "nothing\n"},
    )
    with pytest.raises(SensorUnavailable):
        FrontendContractSensor().scan(repo, NOW)


def test_frontend_non_utf8_page_is_skipped_and_counted(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    make_repo(repo, {"docs/clean.html": CLEAN_PAGE})
    (repo / "docs/latin.html").write_bytes(b"<html><title>caf\xe9</title></html>")
    commit_all(repo, "add latin-1 page")
    observations, stats = FrontendContractSensor().scan_with_stats(repo, NOW)
    assert observations == []
    assert stats["skippedUndecodable"] == 1


def test_frontend_non_git_is_unavailable(tmp_path: Path) -> None:
    plain = _plain_dir(tmp_path / "plain", {"docs/clean.html": CLEAN_PAGE})
    with pytest.raises(SensorUnavailable):
        FrontendContractSensor().scan(plain, NOW)


def test_frontend_repeat_scan_is_identical(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path / "repo",
        {
            "docs/a.html": CLEAN_PAGE.replace(' lang="en"', ""),
            "docs/b.html": CLEAN_PAGE.replace('alt="A diagram"', ""),
        },
    )
    sensor = FrontendContractSensor()
    first = [obs.to_dict() for obs in sensor.scan(repo, NOW)]
    second = [obs.to_dict() for obs in sensor.scan(repo, NOW)]
    assert len(first) == 2 and first == second


def test_frontend_scan_is_read_only(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo", {"docs/a.html": "<html><body></body></html>\n"})
    before = tree_digest(repo)
    FrontendContractSensor().scan(repo, NOW)
    assert tree_digest(repo) == before


def test_frontend_recovery_removes_finding(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo", {"docs/a.html": "<html><body></body></html>\n"})
    assert len(FrontendContractSensor().scan(repo, NOW)) == 1
    write_files(repo, {"docs/a.html": CLEAN_PAGE})
    commit_all(repo, "fix page")
    assert FrontendContractSensor().scan(repo, NOW) == []
