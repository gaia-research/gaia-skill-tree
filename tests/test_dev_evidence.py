"""Unit tests for gaia dev evidence (#791).

Also covers the benchmark-result percentile pre-flight from #789 and
the --class removal from #790.
"""

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from gaia_cli.commands.dev.evidence import meta_evidence_command, _preflight_benchmark_percentile
pytestmark = [pytest.mark.integration]



# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_registry(tmp_path: Path, evidence: list | None = None) -> str:
    nodes = tmp_path / "registry" / "nodes" / "basic"
    nodes.mkdir(parents=True)
    schema = tmp_path / "registry" / "schema"
    schema.mkdir(parents=True)
    (schema / "meta.json").write_text(
        json.dumps({
            "evidence": {
                "gradeThresholds": {"S": 250, "A": 100, "B": 50, "C": 20},
                "types": [
                    {"id": "repo-own", "gradeCeiling": "S"},
                    {"id": "peer-review", "gradeCeiling": "S"},
                    {"id": "benchmark-result", "gradeCeiling": "A"},
                    {"id": "github-stars-own", "gradeCeiling": "B"},
                    {"id": "social-signal", "gradeCeiling": "A"},
                ],
                "perRowGradeThresholds": {},
            }
        })
    )
    node = {
        "id": "demo-skill",
        "name": "Demo Skill",
        "type": "basic",
        "description": "A demo skill for evidence tests.",
        "evidence": evidence or [],
        "timeline": [],
    }
    (nodes / "demo-skill.json").write_text(json.dumps(node, indent=2))
    return str(tmp_path)


def _load_node(root: str) -> dict:
    p = os.path.join(root, "registry", "nodes", "basic", "demo-skill.json")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _make_named_skill(root: str, evidence: list | None = None) -> Path:
    named = Path(root) / "registry" / "named" / "tester"
    named.mkdir(parents=True, exist_ok=True)
    path = named / "demo.md"
    path.write_text(
        "---\n"
        "id: tester/demo\n"
        "title: Demo\n"
        "status: named\n"
        "evidence:\n"
        + "".join(
            "  - source: {source}\n".format(source=row.get("source", "https://example.com/named"))
            + (
                "    sourceStartedAt: {sourceStartedAt}\n".format(
                    sourceStartedAt=row["sourceStartedAt"]
                )
                if "sourceStartedAt" in row
                else ""
            )
            for row in (evidence or [])
        )
        + "---\n\n# Demo\n",
        encoding="utf-8",
    )
    return path


def _args(root: str, *, skill_id: str = "demo-skill", source: str = "https://example.com/ev",
          **overrides) -> SimpleNamespace:
    base = dict(
        registry=root,
        skill_id=skill_id,
        source=source,
        index=None,
        evidence_type=None,
        trust=None,
        evaluator=None,
        date=None,
        notes=None,
        stars=None,
        views=None,
        citations=None,
        reviewers=None,
        commits=None,
        contributors=None,
        skill_count_in_repo=None,
        percentile=None,
        source_started_at=None,
        no_build=True,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.fixture(autouse=True)
def _patch_contributor(monkeypatch):
    monkeypatch.setattr("gaia_cli.commands.dev.evidence._get_contributor", lambda: "tester")
    monkeypatch.setattr("gaia_cli.commands.dev.evidence.append_skill_event", lambda *a, **kw: None)


# ---------------------------------------------------------------------------
# Happy path — append
# ---------------------------------------------------------------------------


def test_append_adds_evidence(tmp_path):
    root = _make_registry(tmp_path)
    meta_evidence_command(_args(root, trust=60.0))
    ev = _load_node(root)["evidence"]
    assert len(ev) == 1
    assert ev[0]["source"] == "https://example.com/ev"
    assert ev[0]["trustNumber"] == 60.0


def test_append_with_type(tmp_path):
    root = _make_registry(tmp_path)
    meta_evidence_command(_args(root, evidence_type="repo-own", trust=120.0, commits=50, contributors=2))
    ev = _load_node(root)["evidence"]
    assert ev[0]["type"] == "repo-own"


def test_append_with_notes(tmp_path):
    root = _make_registry(tmp_path)
    meta_evidence_command(_args(root, trust=30.0, notes="Solid reference"))
    ev = _load_node(root)["evidence"]
    assert ev[0]["notes"] == "Solid reference"


def test_timeline_event_fired(tmp_path, monkeypatch):
    root = _make_registry(tmp_path)
    events = []
    monkeypatch.setattr(
        "gaia_cli.commands.dev.evidence.append_skill_event",
        lambda *a, **kw: events.append(a),
    )
    meta_evidence_command(_args(root, trust=40.0))
    assert any("evidence_added" in str(e) for e in events)


# ---------------------------------------------------------------------------
# In-place re-grade (--index)
# ---------------------------------------------------------------------------


def test_index_updates_trust(tmp_path):
    root = _make_registry(tmp_path, [{"source": "https://x", "trustNumber": 10}])
    meta_evidence_command(_args(root, source="https://x", index=0, trust=120.0))
    entry = _load_node(root)["evidence"][0]
    assert entry["trustNumber"] == 120.0
    assert len(_load_node(root)["evidence"]) == 1


def test_index_source_started_at_emits_audit_event_without_trust(tmp_path, monkeypatch):
    root = _make_registry(tmp_path, [{"source": "https://example.com/ev"}])
    events = []
    monkeypatch.setattr(
        "gaia_cli.commands.dev.evidence.append_skill_event",
        lambda *a, **kw: events.append({"args": a, "kwargs": kw}),
    )

    meta_evidence_command(_args(root, index=0, source_started_at="2026-01-01"))

    entry = _load_node(root)["evidence"][0]
    assert entry["sourceStartedAt"] == "2026-01-01"
    assert len(events) == 1
    assert events[0]["args"][0] == "demo-skill"
    assert events[0]["args"][1] == "evidence_graded"
    assert "Updated evidence #0 metadata" in events[0]["args"][3]
    assert "sourceStartedAt" in events[0]["args"][3]
    assert "trustNumber" not in events[0]["args"][3]


def test_named_index_source_started_at_emits_audit_event_without_trust(tmp_path, monkeypatch):
    root = _make_registry(tmp_path)
    _make_named_skill(root, [{"source": "https://example.com/named"}])
    events = []
    monkeypatch.setattr(
        "gaia_cli.commands.dev.evidence.append_skill_event",
        lambda *a, **kw: events.append({"args": a, "kwargs": kw}),
    )

    meta_evidence_command(
        _args(
            root,
            skill_id="tester/demo",
            source="https://example.com/named",
            index=0,
            source_started_at="2026-01-01",
        )
    )

    assert len(events) == 1
    assert events[0]["args"][0] == "tester/demo"
    assert events[0]["args"][1] == "evidence_graded"
    assert "sourceStartedAt" in events[0]["args"][3]


def test_index_same_source_started_at_adds_no_audit_event(tmp_path, monkeypatch):
    root = _make_registry(
        tmp_path,
        [{"source": "https://example.com/ev", "sourceStartedAt": "2026-01-01"}],
    )
    before = _load_node(root)
    events = []
    monkeypatch.setattr(
        "gaia_cli.commands.dev.evidence.append_skill_event",
        lambda *a, **kw: events.append(a),
    )

    meta_evidence_command(_args(root, index=0, source_started_at="2026-01-01"))

    assert events == []
    assert _load_node(root) == before


def test_index_out_of_range_exits_before_write(tmp_path, capsys):
    root = _make_registry(tmp_path, [{"source": "https://x"}])
    before = _load_node(root)

    with pytest.raises(SystemExit) as exc:
        meta_evidence_command(_args(root, index=5, trust=80.0))

    assert exc.value.code != 0
    assert _load_node(root) == before
    err = capsys.readouterr().err
    assert "Evidence index 5 out of range" in err
    assert "--index" in err


def test_index_with_no_update_field_exits_before_write(tmp_path, capsys):
    root = _make_registry(tmp_path, [{"source": "https://x"}])
    before = _load_node(root)

    with pytest.raises(SystemExit) as exc:
        meta_evidence_command(_args(root, index=0))

    assert exc.value.code != 0
    assert _load_node(root) == before
    err = capsys.readouterr().err
    assert "--index requires at least one update field" in err
    assert "--trust" in err


# ---------------------------------------------------------------------------
# Pre-flight: benchmark-result percentile (#789)
# ---------------------------------------------------------------------------


def test_benchmark_without_percentile_exits_before_write(tmp_path, capsys):
    root = _make_registry(tmp_path)
    before = _load_node(root)

    with pytest.raises(SystemExit) as exc:
        meta_evidence_command(_args(root, evidence_type="benchmark-result", trust=80.0))

    assert exc.value.code != 0
    assert _load_node(root) == before
    err = capsys.readouterr().err
    assert "--type benchmark-result" in err
    assert "--percentile" in err


def test_benchmark_with_percentile_succeeds(tmp_path):
    root = _make_registry(tmp_path)
    meta_evidence_command(
        _args(root, evidence_type="benchmark-result", trust=80.0, percentile=92)
    )
    ev = _load_node(root)["evidence"]
    assert ev[0]["percentile"] == 92


def test_percentile_out_of_range_exits(tmp_path):
    root = _make_registry(tmp_path)
    with pytest.raises(SystemExit) as exc:
        meta_evidence_command(
            _args(root, evidence_type="benchmark-result", trust=80.0, percentile=101)
        )
    assert exc.value.code != 0


def test_non_benchmark_type_no_percentile_required(tmp_path):
    """Other types do not require --percentile."""
    root = _make_registry(tmp_path)
    meta_evidence_command(_args(root, evidence_type="peer-review", trust=80.0, reviewers=2))
    ev = _load_node(root)["evidence"]
    assert len(ev) == 1


def test_peer_review_requires_reviewers_before_write(tmp_path, capsys):
    root = _make_registry(tmp_path)
    before = _load_node(root)

    with pytest.raises(SystemExit) as exc:
        meta_evidence_command(_args(root, evidence_type="peer-review", trust=80.0))

    assert exc.value.code != 0
    assert _load_node(root) == before
    err = capsys.readouterr().err
    assert "--type peer-review" in err
    assert "--reviewers" in err


def test_negative_numeric_payload_rejected_before_write(tmp_path, capsys):
    root = _make_registry(tmp_path)
    before = _load_node(root)

    with pytest.raises(SystemExit) as exc:
        meta_evidence_command(_args(root, evidence_type="social-signal", views=-1))

    assert exc.value.code != 0
    assert _load_node(root) == before
    assert "--views must be >= 0" in capsys.readouterr().err


def test_invalid_source_url_rejected_before_write(tmp_path, capsys):
    root = _make_registry(tmp_path)
    before = _load_node(root)

    with pytest.raises(SystemExit) as exc:
        meta_evidence_command(_args(root, source="not-a-url", trust=20.0))

    assert exc.value.code != 0
    assert _load_node(root) == before
    assert "absolute http(s) URL" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# Class flag is removed (#790)
# ---------------------------------------------------------------------------


def test_no_class_field_written(tmp_path):
    """New entries must not write a 'class' field even if the namespace carries one."""
    root = _make_registry(tmp_path)
    meta_evidence_command(_args(root, trust=60.0))
    ev = _load_node(root)["evidence"]
    assert "class" not in ev[0]


def test_existing_class_field_preserved_on_regrade(tmp_path):
    """Pre-existing 'class' in evidence data is not wiped by --index regrade."""
    root = _make_registry(tmp_path, [{"source": "https://x", "class": "B", "trustNumber": 10}])
    meta_evidence_command(_args(root, source="https://x", index=0, trust=70.0))
    entry = _load_node(root)["evidence"][0]
    assert entry["class"] == "B"


# ---------------------------------------------------------------------------
# Invalid type rejected
# ---------------------------------------------------------------------------


def test_invalid_type_exits_before_write(tmp_path, capsys):
    root = _make_registry(tmp_path)
    before = _load_node(root)

    with pytest.raises(SystemExit) as exc:
        meta_evidence_command(_args(root, evidence_type="not-a-real-type", trust=50.0))

    assert exc.value.code != 0
    assert _load_node(root) == before
    err = capsys.readouterr().err
    assert "unknown evidence type 'not-a-real-type'" in err
    assert "repo-own" in err


def test_invalid_date_exits_before_write(tmp_path, capsys):
    root = _make_registry(tmp_path)
    before = _load_node(root)

    with pytest.raises(SystemExit) as exc:
        meta_evidence_command(_args(root, trust=50.0, date="2026/07/01"))

    assert exc.value.code != 0
    assert _load_node(root) == before
    err = capsys.readouterr().err
    assert "--date must be ISO YYYY-MM-DD" in err


def test_invalid_source_started_at_exits_before_write(tmp_path, capsys):
    root = _make_registry(tmp_path)
    before = _load_node(root)

    with pytest.raises(SystemExit) as exc:
        meta_evidence_command(_args(root, trust=50.0, source_started_at="July 1"))

    assert exc.value.code != 0
    assert _load_node(root) == before
    err = capsys.readouterr().err
    assert "--source-started-at must be ISO YYYY-MM-DD" in err


# ---------------------------------------------------------------------------
# Unit test for _preflight_benchmark_percentile directly
# ---------------------------------------------------------------------------


def test_preflight_benchmark_no_percentile_direct():
    ns = SimpleNamespace(evidence_type="benchmark-result", percentile=None)
    with pytest.raises(SystemExit):
        _preflight_benchmark_percentile(ns)


def test_preflight_benchmark_with_percentile_passes():
    ns = SimpleNamespace(evidence_type="benchmark-result", percentile=85)
    _preflight_benchmark_percentile(ns)  # must not raise


def test_preflight_non_benchmark_passes():
    ns = SimpleNamespace(evidence_type="repo-own", percentile=None, commits=1, contributors=1)
    _preflight_benchmark_percentile(ns)  # must not raise
