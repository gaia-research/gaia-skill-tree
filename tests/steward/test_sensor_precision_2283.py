"""Sensor precision fixes S1-S9 (#2283 ROOTCAUSE-PLAN section 10).

Every fix is paired: a true-positive test proving the defect is still reported,
and a precision test for the false positive or the added annotation. Debt ids
depend only on (kind, subject); none of these fixes changes a subject or a kind.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
import yaml

from gaia_cli.steward.models import debtIdFor
from gaia_cli.steward.sensors import FrozenSkillIntegritySensor, TrustCalibrationDriftSensor
from gaia_cli.steward.sensors_code import DeadCodeSensor, ErrorHandlingSensor
from gaia_cli.steward.sensors_security import BrowserSinkSensor, _UnsafeVisitor
from tests.steward.sensor_fixtures import make_repo, track_all
from tests.steward.test_sensors_code import handler_source, of_kind, repo
from tests.steward.test_sensors_security import _dev_init, _execution, _gating, _mutation
from tests.steward.test_trust_calibration_regression import PARENT

NOW = "2026-11-08T00:00:00Z"


def _browser(tmp_path: Path, source: str, name: str = "docs/a.js"):
    root = make_repo(tmp_path / "repo", {"docs/keep.js": "var ok = 1;\n", name: source})
    return BrowserSinkSensor().scan(root, NOW)


# --------------------------------------------------------------------------
# S1: escaper detection recognises the house helper esc(
# --------------------------------------------------------------------------


class TestS1Escaper:
    def test_true_positive_without_escaper_is_unchanged(self, tmp_path: Path) -> None:
        (item,) = _browser(tmp_path, "el.innerHTML = '<b>' + name;\n")
        assert item.observed_state["escaperPresent"] is False
        assert item.confidence == 0.6

    def test_local_esc_helper_counts_as_escaper_but_the_sink_is_still_reported(self, tmp_path: Path) -> None:
        source = "function esc(s) { return String(s); }\nel.innerHTML = '<b>' + esc(name) + '</b>';\n"
        (item,) = _browser(tmp_path, source)
        assert item.observed_state["escaperPresent"] is True
        assert item.observed_state["findingCount"] == 1
        assert item.confidence == 0.4

    @pytest.mark.parametrize("word", ["desc(x)", "rescue(x)", "escrow = 1"])
    def test_words_containing_esc_are_not_escapers(self, tmp_path: Path, word: str) -> None:
        (item,) = _browser(tmp_path, f"var v = {word};\nel.innerHTML = '<b>' + v;\n")
        assert item.observed_state["escaperPresent"] is False


# --------------------------------------------------------------------------
# S2: the repository's audited marker is an annotation, never a filter
# --------------------------------------------------------------------------


class TestS2AcknowledgedMarker:
    def test_marked_sink_is_still_reported_and_counted_as_acknowledged(self, tmp_path: Path) -> None:
        source = "el.innerHTML = `<i>${x}</i>`;  // gaia-html-sink-ok: x is a fixed enum\n"
        (item,) = _browser(tmp_path, source)
        assert item.status == "drift"
        (finding,) = item.observed_state["findings"]
        assert finding["acknowledged"] is True
        assert finding["acknowledgedReason"] == "x is a fixed enum"
        assert item.observed_state["acknowledgedCount"] == 1

    @pytest.mark.parametrize(
        "source",
        [
            "el.innerHTML = `<b>${x}</b>`;  // gaia-html-sink-ok:\n",
            "el.innerHTML = `<b>${x}</b>`;  // gaia-html-sink-ok:   \n",
            "el.innerHTML = `<b>${x}</b>`;\n",
        ],
    )
    def test_bare_or_missing_marker_is_not_acknowledged(self, tmp_path: Path, source: str) -> None:
        (item,) = _browser(tmp_path, source)
        (finding,) = item.observed_state["findings"]
        assert "acknowledged" not in finding
        assert item.observed_state["acknowledgedCount"] == 0

    def test_marker_does_not_acknowledge_non_html_sinks(self, tmp_path: Path) -> None:
        (item,) = _browser(tmp_path, "eval(code);  // gaia-html-sink-ok: not an html sink\n")
        (finding,) = item.observed_state["findings"]
        assert finding["pattern"] == "eval"
        assert "acknowledged" not in finding

    def test_html_comment_trailer_is_trimmed_from_the_reason(self, tmp_path: Path) -> None:
        source = "<script>el.innerHTML = `<b>${x}</b>`; /* gaia-html-sink-ok: build constant */</script>\n"
        (item,) = _browser(tmp_path, source, name="docs/a.html")
        (finding,) = item.observed_state["findings"]
        assert finding["acknowledgedReason"] == "build constant"


# --------------------------------------------------------------------------
# S3: per-site shape annotation (no re-keying; the subject stays the file)
# --------------------------------------------------------------------------


class TestS3SinkShape:
    @pytest.mark.parametrize(
        "source, shape",
        [
            ("el.innerHTML = `<b>${name}</b>`;\n", "template-interpolation"),
            ("el.innerHTML = `\n<b>${name}</b>\n`;\n", "template-interpolation"),
            ("el.innerHTML = '<b>' + name;\n", "string-concatenation"),
            ("el.innerHTML =\n  '<b>' +\n  name;\n", "string-concatenation"),
            ("el.innerHTML = rankBadge + '<b>';\n", "string-concatenation"),
            ("el.innerHTML = html;\n", "expression"),
            ("el.innerHTML = parts.join('');\n", "expression"),
            ("el.insertAdjacentHTML('beforeend', `<i>${x}</i>`);\n", "template-interpolation"),
            ("document.write('<b>' + x);\n", "string-concatenation"),
        ],
    )
    def test_every_sink_is_still_reported_with_its_shape(self, tmp_path: Path, source: str, shape: str) -> None:
        (item,) = _browser(tmp_path, source)
        (finding,) = item.observed_state["findings"]
        assert finding["shape"] == shape
        assert item.observed_state["shapeCounts"] == {shape: 1}

    def test_generator_changelog_template_true_positive_is_template_interpolation(self, tmp_path: Path) -> None:
        # The exact sink shape scripts/add_post.py emits into every meta report.
        source = (
            "item.innerHTML = `<div>${new Date(ev.timestamp).toLocaleDateString()} · "
            "${ev.action.toUpperCase()}</div><div>${ev.skillName}</div><div>${ev.details}</div>`;\n"
        )
        (item,) = _browser(tmp_path, source, name="docs/meta/reports/r.html")
        (finding,) = item.observed_state["findings"]
        assert finding["pattern"] == "innerHTML-assignment"
        assert finding["shape"] == "template-interpolation"

    def test_subject_and_debt_id_are_unchanged(self, tmp_path: Path) -> None:
        (item,) = _browser(tmp_path, "a.innerHTML = x;\nb.innerHTML = `${y}`;\n")
        assert item.subject.id == "docs/a.js"
        assert item.debt_id == debtIdFor("browser_sink_risk", item.subject)


# --------------------------------------------------------------------------
# S4: a ruff noqa with a written reason is an intent record
# --------------------------------------------------------------------------


class TestS4DocumentedBroadExcept:
    @pytest.mark.parametrize(
        "handler",
        [
            "except Exception:  # noqa: BLE001",
            "except Exception:  # noqa",
            "except Exception:  # noqa: BLE001 -",
            "except Exception:  # noqa: E501 - a long line, not a broad except",
            "except Exception:  # ignore",
        ],
    )
    def test_undocumented_or_wrong_code_still_flags(self, tmp_path: Path, handler: str) -> None:
        root = repo(tmp_path, {"src/gaia_cli/risky.py": handler_source(handler, "pass")})
        (observation,) = ErrorHandlingSensor().scan(root, NOW)
        assert observation.observed_state["findingCount"] == 1

    @pytest.mark.parametrize(
        "handler",
        [
            "except Exception:  # noqa: BLE001 - an unknown closer is a fact, not an error",
            "except Exception:  # noqa: S110 — optional cache, absence is normal",
            "except Exception:  # noqa: BLE001, S110 optional telemetry",
            "except Exception:  # steward: best-effort: optional cache",
        ],
    )
    def test_documented_handler_is_not_reported(self, tmp_path: Path, handler: str) -> None:
        root = repo(tmp_path, {"src/gaia_cli/risky.py": handler_source(handler, "pass")})
        assert ErrorHandlingSensor().scan(root, NOW) == []

    def test_one_documented_handler_does_not_hide_its_undocumented_neighbour(self, tmp_path: Path) -> None:
        source = (
            "def f():\n    try:\n        a()\n    except Exception:  # noqa: BLE001 - documented\n        pass\n"
            "    try:\n        b()\n    except Exception:\n        pass\n"
        )
        root = repo(tmp_path, {"src/gaia_cli/risky.py": source})
        (observation,) = ErrorHandlingSensor().scan(root, NOW)
        assert [item["line"] for item in observation.observed_state["findings"]] == [8]


# --------------------------------------------------------------------------
# S5: module-local safe yaml loaders
# --------------------------------------------------------------------------


def _unsafe(source: str) -> list[str]:
    return [item["pattern"] for item in _UnsafeVisitor(ast.parse(source)).findings()]


class TestS5YamlLoaderResolution:
    @pytest.mark.parametrize(
        "source",
        [
            "import yaml\nloader = getattr(yaml, 'CSafeLoader', yaml.Loader)\nyaml.load(t, Loader=loader)\n",
            "import yaml\nloader = yaml.SafeLoader\nloader = yaml.Loader\nyaml.load(t, Loader=loader)\n",
            "import yaml\nL = yaml.SafeLoader\ndef f(L):\n    return yaml.load(t, Loader=L)\n",
            "import yaml\nclass S(yaml.FullLoader):\n    pass\nyaml.load(t, Loader=S)\n",
            "import yaml\nclass S(yaml.SafeLoader):\n    pass\nS.add_constructor('!py', f)\nyaml.load(t, Loader=S)\n",
            "import yaml\nclass S(yaml.SafeLoader):\n    yaml_constructors = {}\nyaml.load(t, Loader=S)\n",
            "import yaml\nclass S(yaml.SafeLoader):\n    pass\nS = yaml.UnsafeLoader\nyaml.load(t, Loader=S)\n",
            "import yaml\ndef f(loader):\n    return yaml.load(t, Loader=loader)\n",
            "import yaml\nyaml.load(t, Loader=yaml.Loader)\n",
            # #2372 review P1: one unsafe base keeps the class unsafe.
            "import yaml\nclass M(yaml.UnsafeLoader, yaml.SafeLoader):\n    pass\nyaml.load(t, Loader=M)\n",
            "import yaml\nclass M(yaml.SafeLoader, yaml.UnsafeLoader):\n    pass\nyaml.load(t, Loader=M)\n",
            "import yaml\nclass M(yaml.SafeLoader, Mixin):\n    pass\nyaml.load(t, Loader=M)\n",
            "import yaml\nclass M(yaml.SafeLoader, metaclass=Meta):\n    pass\nyaml.load(t, Loader=M)\n",
            # Constructor registration through an alias, yaml.add_constructor, the
            # constructor table, or on SafeLoader itself.
            "import yaml\nclass S(yaml.SafeLoader):\n    pass\nA = S\nA.add_constructor('!x', f)\nyaml.load(t, Loader=S)\n",
            "import yaml\nclass S(yaml.SafeLoader):\n    pass\nyaml.add_constructor('!x', f, Loader=S)\nyaml.load(t, Loader=S)\n",
            "import yaml\nclass S(yaml.SafeLoader):\n    pass\nyaml.add_constructor('!x', f, S)\nyaml.load(t, Loader=S)\n",
            "import yaml\nclass S(yaml.SafeLoader):\n    pass\nS.yaml_constructors['!x'] = f\nyaml.load(t, Loader=S)\n",
            "import yaml\nclass S(yaml.SafeLoader):\n    pass\nclass T(S):\n    pass\nS.add_constructor('!x', f)\n"
            "yaml.load(t, Loader=T)\n",
            "import yaml\nyaml.SafeLoader.add_constructor('!x', f)\nyaml.load(t, Loader=yaml.SafeLoader)\n",
            "import yaml\nyaml.add_constructor('!x', f, Loader=yaml.SafeLoader)\nyaml.load(t, Loader=yaml.SafeLoader)\n",
        ],
    )
    def test_unsafe_or_unresolved_loaders_are_still_reported(self, source: str) -> None:
        assert _unsafe(source) == ["yaml-load-unsafe-loader"]

    @pytest.mark.parametrize(
        "source",
        [
            # src/gaia_cli/frontierMatch.py:91-93
            "import yaml\nloader = getattr(yaml, 'CSafeLoader', yaml.SafeLoader)\nyaml.load(t, Loader=loader)\n",
            # src/gaia_cli/steward/workflowproof.py:46,91
            "import yaml\nclass _Strict(yaml.SafeLoader):\n    def construct_mapping(self, node, deep=False):\n"
            "        return super().construct_mapping(node, deep)\nyaml.load(t, Loader=_Strict)\n",
            "import yaml\nclass A(yaml.SafeLoader):\n    pass\nclass B(A):\n    pass\nyaml.load(t, Loader=B)\n",
            "import yaml\nclass S(yaml.SafeLoader, yaml.CSafeLoader):\n    pass\nyaml.load(t, Loader=S)\n",
            # yaml.add_constructor without Loader= never targets a safe loader.
            "import yaml\nyaml.add_constructor('!x', f)\nyaml.load(t, Loader=yaml.SafeLoader)\n",
            "from yaml import SafeLoader, load\nload(t, Loader=SafeLoader)\n",
        ],
    )
    def test_provably_safe_loaders_are_not_reported(self, source: str) -> None:
        assert _unsafe(source) == []

    def test_through_the_sensor(self, tmp_path: Path) -> None:
        safe = "import yaml\nloader = getattr(yaml, 'CSafeLoader', yaml.SafeLoader)\nyaml.load(t, Loader=loader)\n"
        _, observations = _mutation(tmp_path, **{"scripts/tool.py": safe})
        assert _execution(observations) == []


# --------------------------------------------------------------------------
# S6: handler-entry guard is annotated, the set drift is still reported
# --------------------------------------------------------------------------


def _with_handler(tmp_path: Path, body: str):
    files = {
        "src/gaia_cli/commands/dev/__init__.py": _dev_init(
            parsers="add rm list export",
            dispatch={
                "add": "gaia_cli.commands.dev.writer:addCommand",
                "rm": "gaia_cli.commands.dev.writer:rmCommand",
                "list": "gaia_cli.commands.dev.reader:listCommand",
                "export": "gaia_cli.commands.dev.exporter:exportCommand",
            },
        ),
        "src/gaia_cli/commands/dev/exporter.py": "from pathlib import Path\n\n\ndef exportCommand(args):\n" + body,
    }
    _, observations = _mutation(tmp_path, **files)
    (item,) = _gating(observations)
    return item


class TestS6GatedInHandler:
    def test_entry_guard_is_annotated_and_still_drift(self, tmp_path: Path) -> None:
        body = (
            "    from gaia_cli.authz import require_operator\n"
            "    command = args.export_command\n"
            "    require_operator(f'dev export {command}', args.registry)\n"
            "    Path(args.registry).joinpath('out.json').write_text('{}')\n"
        )
        item = _with_handler(tmp_path, body)
        assert item.subject.id == "dev:export"
        assert item.status == "drift"
        assert item.observed_state["gated"] is False
        assert item.observed_state["gatedInHandler"] is True
        assert item.observed_state["inCanonicalSet"] is False
        assert item.observed_state["findings"][0]["gatedInHandler"] is True

    @pytest.mark.parametrize(
        "body",
        [
            "    Path(args.registry).joinpath('out.json').write_text('{}')\n",
            "    if args.force:\n        require_operator('x', args.registry)\n"
            "    Path(args.registry).joinpath('out.json').write_text('{}')\n",
            "    Path(args.registry).joinpath('out.json').write_text('{}')\n    require_operator('x', args.registry)\n",
            "    root = resolve(args)\n    require_operator('x', args.registry)\n"
            "    Path(root).joinpath('out.json').write_text('{}')\n",
        ],
    )
    def test_missing_conditional_or_late_guard_is_not_entry_gated(self, tmp_path: Path, body: str) -> None:
        item = _with_handler(tmp_path, body)
        assert item.status == "drift"
        assert item.observed_state["gatedInHandler"] is False


# --------------------------------------------------------------------------
# S7: frozen drift never proposes a write; history is acknowledged by record
# --------------------------------------------------------------------------

FROZEN = (
    "---\n"
    "id: owner/frozen\n"
    "name: Frozen\n"
    "status: named\n"
    "level: {level}\n"
    "installable: false\n"
    "timeline:\n"
    "  - timestamp: '2026-06-20T00:00:00Z'\n"
    "    action: rank_up\n"
    "    details: Level updated to 3★\n"
    "  - timestamp: '2026-08-19T00:00:00Z'\n"
    "    action: upstream_deprecated\n"
    "    details: superseded\n"
    "  - timestamp: '2026-09-02T00:00:00Z'\n"
    "    action: rank_up\n"
    "    details: {first}\n"
    "  - timestamp: '2026-09-11T00:00:00Z'\n"
    "    action: demote\n"
    "    details: Calibrated level from 4★ to 3★\n"
    "{extra}"
    "---\n"
)


def _frozen_repo(tmp_path: Path, *, level: str = "3★", first: str = "Calibrated level from 3★ to 4★",
                 record: dict | None = None, extra: str = "") -> Path:
    path = tmp_path / "registry/named/owner/frozen.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(FROZEN.format(level=level, first=first, extra=extra), encoding="utf-8")
    if record is not None:
        target = tmp_path / "founder/steward/decisions" / f"{record['id']}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(record), encoding="utf-8")
    track_all(tmp_path)
    return tmp_path


def _record(events: list[dict], **overrides: object) -> dict:
    sensor = FrozenSkillIntegritySensor
    record = {
        "schemaVersion": "steward-decision-v1",
        "id": sensor.acknowledgementRecordId("owner/frozen"),
        "status": "decided",
        "resolution": "acknowledged",
        "decision": "Acknowledge the corrected post-freeze history of owner/frozen?",
        "whyItMatters": "Timeline history is append-only and cannot be repaired.",
        "evidence": [sensor.acknowledgementLine("owner/frozen", event) for event in events],
        "recommended": "Acknowledge.",
        "alternative": "Leave open.",
        "unblocks": "frozen_skill_drift for owner/frozen.",
        "links": ["registry/named/owner/frozen.md"],
    }
    record.update(overrides)
    return record


E1 = {"timestamp": "2026-09-02T00:00:00Z", "action": "rank_up", "details": "Calibrated level from 3★ to 4★"}
E2 = {"timestamp": "2026-09-11T00:00:00Z", "action": "demote", "details": "Calibrated level from 4★ to 3★"}
BOTH = [E1, E2]
# Same timestamp and action as E1, different content (the #2372 review repro).
TWIN = (
    "  - timestamp: '2026-09-02T00:00:00Z'\n"
    "    action: rank_up\n"
    "    details: An unapproved second promotion\n"
)
# Byte-identical copy of E1.
COPY = (
    "  - timestamp: '2026-09-02T00:00:00Z'\n"
    "    action: rank_up\n"
    "    details: Calibrated level from 3★ to 4★\n"
)


class TestS7FrozenHistory:
    def test_history_without_record_is_drift_with_no_write_command(self, tmp_path: Path) -> None:
        (obs,) = FrozenSkillIntegritySensor().scan(_frozen_repo(tmp_path), NOW)
        assert obs.status == "drift"
        state = obs.observed_state
        assert "remediationCommand" not in state
        assert state["levelMismatch"] is False
        assert state["postFreezeEvents"] == ["rank_up", "demote"]
        assert state["unacknowledgedEventCount"] == 2
        assert state["acknowledgementRecordPresent"] is False
        assert state["acknowledgementRecord"] == "steward-frozen-history-owner.frozen"
        assert state["remediation"].startswith("founder acknowledgement")

    def test_decided_record_acknowledging_every_event_makes_it_healthy(self, tmp_path: Path) -> None:
        root = _frozen_repo(tmp_path, record=_record(BOTH))
        (obs,) = FrozenSkillIntegritySensor().scan(root, NOW)
        assert obs.status == "healthy"
        assert all(event["acknowledged"] for event in obs.observed_state["postFreezeHistory"])
        assert obs.debt_id == debtIdFor("frozen_skill_drift", obs.subject)

    def test_record_covering_only_some_events_leaves_the_rest_reported(self, tmp_path: Path) -> None:
        root = _frozen_repo(tmp_path, record=_record(BOTH[:1]))
        (obs,) = FrozenSkillIntegritySensor().scan(root, NOW)
        assert obs.status == "drift"
        assert obs.observed_state["unacknowledgedEventCount"] == 1

    @pytest.mark.parametrize(
        "overrides",
        [
            {"status": "open"},
            {"resolution": "approved"},
            {"frozenHistory": ["owner/frozen"]},  # unknown key: malformed record
            {"id": "steward-frozen-history-someone.else"},  # id does not match the file name
        ],
    )
    def test_invalid_or_undecided_record_fails_closed(self, tmp_path: Path, overrides: dict) -> None:
        record = _record(BOTH)
        name = record["id"]
        record.update(overrides)
        path = tmp_path / "founder/steward/decisions" / f"{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record), encoding="utf-8")
        (obs,) = FrozenSkillIntegritySensor().scan(_frozen_repo(tmp_path), NOW)
        assert obs.status == "drift"
        assert obs.observed_state["acknowledgementRecordPresent"] is False

    def test_free_text_founder_override_no_longer_exempts(self, tmp_path: Path) -> None:
        root = _frozen_repo(tmp_path, first="founder override, calibrated level from 3★ to 4★")
        (obs,) = FrozenSkillIntegritySensor().scan(root, NOW)
        assert obs.status == "drift"
        assert obs.observed_state["postFreezeEvents"] == ["rank_up", "demote"]

    def test_level_mismatch_stays_drift_even_with_acknowledged_history(self, tmp_path: Path) -> None:
        root = _frozen_repo(tmp_path, level="1★", record=_record(BOTH))
        (obs,) = FrozenSkillIntegritySensor().scan(root, NOW)
        assert obs.status == "drift"
        assert obs.observed_state["levelMismatch"] is True
        assert "remediationCommand" not in obs.observed_state
        assert obs.observed_state["remediation"].startswith("founder decision")

    def test_scan_publishes_the_exact_line_a_record_must_carry(self, tmp_path: Path) -> None:
        (obs,) = FrozenSkillIntegritySensor().scan(_frozen_repo(tmp_path), NOW)
        lines = [event["acknowledgementLine"] for event in obs.observed_state["postFreezeHistory"]]
        assert lines == _record(BOTH)["evidence"]
        assert all(line.split()[-1].startswith("sha256:") for line in lines)

    def test_twin_event_with_same_timestamp_and_action_is_not_acknowledged(self, tmp_path: Path) -> None:
        # #2372 review P1: a second, different event sharing (timestamp, action)
        # must not ride on the first event's acknowledgement.
        root = _frozen_repo(tmp_path, record=_record(BOTH), extra=TWIN)
        (obs,) = FrozenSkillIntegritySensor().scan(root, NOW)
        assert obs.status == "drift"
        history = obs.observed_state["postFreezeHistory"]
        assert [event["acknowledged"] for event in history] == [True, True, False]
        assert obs.observed_state["unacknowledgedEventCount"] == 1

    def test_byte_identical_duplicate_needs_its_own_line(self, tmp_path: Path) -> None:
        root = _frozen_repo(tmp_path, record=_record(BOTH), extra=COPY)
        (obs,) = FrozenSkillIntegritySensor().scan(root, NOW)
        assert obs.status == "drift"
        assert obs.observed_state["unacknowledgedEventCount"] == 1
        root2 = _frozen_repo(tmp_path / "again", record=_record([E1, E2, E1]), extra=COPY)
        (obs2,) = FrozenSkillIntegritySensor().scan(root2, NOW)
        assert obs2.status == "healthy"

    def test_unreadable_record_is_a_visible_skip(self, tmp_path: Path) -> None:
        root = _frozen_repo(tmp_path)
        broken = root / "registry/named/owner/broken.md"
        broken.write_text("---\nid: [unclosed\n---\n", encoding="utf-8")
        nofence = root / "registry/named/owner/nofence.md"
        nofence.write_text("no frontmatter here\n", encoding="utf-8")
        track_all(root)
        scan = FrozenSkillIntegritySensor().scan_detailed(root, NOW)
        skipped = {item["subjectId"] for item in scan.skipped}
        assert {"registry/named/owner/broken.md", "registry/named/owner/nofence.md"} <= skipped
        assert [obs.subject.id for obs in scan.observations] == ["owner/frozen"]


# --------------------------------------------------------------------------
# S8: trust drift annotations from the canonical calibrate predicates
# --------------------------------------------------------------------------


def _trust_repo(tmp_path: Path, **named: dict) -> Path:
    files = {"registry/nodes/fusion/parent-platform.json": json.dumps(PARENT)}
    for skill_id, fields in named.items():
        skill = {
            "id": skill_id,
            "name": skill_id.split("/")[-1],
            "status": "named",
            "genericSkillRef": "parent-platform",
            "evidence": [{"type": "github-stars-own", "source": f"https://github.com/{skill_id}", "stars": 100}],
            **fields,
        }
        files[f"registry/named/{skill_id}.md"] = "---\n" + yaml.safe_dump(skill, sort_keys=False, allow_unicode=True) + "---\n"
    return make_repo(tmp_path / "repo", files)


BLOB = {"github": "https://github.com/owner/repo/blob/main/SKILL.md"}


class TestS8TrustAnnotations:
    def test_ceiling_exceeded_is_still_reported_with_command_and_direction(self, tmp_path: Path) -> None:
        root = _trust_repo(tmp_path, **{"owner/child": {"level": "5★", "links": BLOB}})
        (obs,) = TrustCalibrationDriftSensor().scan(root, NOW)
        state = obs.observed_state
        assert state["targetLevel"] == "3★"
        assert state["calibrationCommand"] == "gaia dev calibrate owner/child 3★"
        assert state["direction"] == "ceiling-exceeded"
        assert state["gatesUnmet"] == []
        assert state["commandWouldBeRefused"] is False
        assert state["priorGovernedDemotion"] is None
        assert state["frozen"] is False

    def test_promotion_candidate_reports_the_gates_the_cli_would_refuse(self, tmp_path: Path) -> None:
        root = _trust_repo(
            tmp_path,
            **{
                "owner/child": {
                    "level": "1★",
                    "status": "awakened",
                    "timeline": [
                        {"timestamp": "2026-09-04T00:00:00Z", "action": "demote", "details": "Demoted to 1★; prompt wrapper"}
                    ],
                }
            },
        )
        (obs,) = TrustCalibrationDriftSensor().scan(root, NOW)
        state = obs.observed_state
        assert obs.kind == "trust_calibration_drift"
        assert state["direction"] == "promotion-candidate"
        assert [gate["gate"] for gate in state["gatesUnmet"]] == ["star-bar-blob-link", "calibrate-status"]
        assert state["commandWouldBeRefused"] is True
        assert state["priorGovernedDemotion"] == {
            "timestamp": "2026-09-04T00:00:00Z",
            "details": "Demoted to 1★; prompt wrapper",
        }

    def test_frozen_by_canonical_definition_is_annotated_not_filtered(self, tmp_path: Path) -> None:
        # frozen: true is frozen per gaia_cli.frozen; the drift skip rule (only
        # upstream_deprecated) is unchanged, so the finding is still reported.
        root = _trust_repo(tmp_path, **{"owner/child": {"level": "5★", "links": BLOB, "frozen": True}})
        (obs,) = TrustCalibrationDriftSensor().scan(root, NOW)
        assert obs.observed_state["frozen"] is True
        assert obs.observed_state["gatesUnmet"][0]["gate"] == "named-skill-frozen"

    def test_star_gate_is_the_canonical_predicate_reusing_the_scan_context(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from gaia_cli.commands.dev import helpers

        seen: list[dict] = []

        def spy(skill_id, skill_data, level, registry_path, *, mergedMap=None, originPool=None):
            seen.append({"level": level, "mergedMap": mergedMap is not None, "pool": originPool})
            helpers._fail_dev_preflight("star gate says no")

        monkeypatch.setattr(helpers, "_preflight_star_gate", spy)
        monkeypatch.setattr("gaia_cli.origin.contenderPool", lambda root, merged: {"pool": True})
        root = _trust_repo(tmp_path, **{"owner/child": {"level": "1★", "links": BLOB, "evidence": [
            {"type": "github-stars-own", "source": "https://github.com/owner/child", "stars": 100000}
        ]}})
        (obs,) = TrustCalibrationDriftSensor().scan(root, NOW)
        assert obs.observed_state["targetLevel"] in {"4★", "5★"}
        assert seen and seen[0]["mergedMap"] is True and seen[0]["pool"] == {"pool": True}
        assert obs.observed_state["gatesUnmet"] == [{"gate": "star-gate", "message": "star gate says no"}]

    def test_unexpected_preflight_error_is_recorded_not_fatal_not_swallowed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from gaia_cli.commands.dev import helpers

        def broken(skill_id, skill_data, level):
            raise KeyError("boom")

        monkeypatch.setattr(helpers, "_preflight_starbar_blob_link", broken)
        root = _trust_repo(tmp_path, **{"owner/child": {"level": "5★", "links": BLOB}})
        scan = TrustCalibrationDriftSensor().scan_detailed(root, NOW)
        (obs,) = scan.observations  # the finding is still reported
        assert obs.observed_state["gatesUnmet"] == [{"gate": "star-bar-blob-link", "preflightError": "KeyError"}]
        assert obs.observed_state["commandWouldBeRefused"] is None
        assert {"subjectType": "calibration-gate", "subjectId": "owner/child:star-bar-blob-link",
                "reason": "preflight raised KeyError"} in scan.skipped

    def test_sensor_stays_read_only(self, tmp_path: Path) -> None:
        from tests.steward.sensor_fixtures import tree_digest

        root = _trust_repo(tmp_path, **{"owner/child": {"level": "1★", "status": "awakened"}})
        before = tree_digest(root)
        TrustCalibrationDriftSensor().scan(root, NOW)
        assert tree_digest(root) == before


# --------------------------------------------------------------------------
# S9: stdlib imports are not labelled side-effect-possible
# --------------------------------------------------------------------------


class TestS9SideEffectLabel:
    @pytest.mark.parametrize(
        "statement, expected",
        [
            ("import os", False),
            ("import xml.etree.ElementTree", False),
            ("import requests", True),  # third party: still possibly side-effecting
            ("import readline", True),  # stdlib that acts on import
            ("import gaia_cli.plugins", True),
        ],
    )
    def test_label(self, tmp_path: Path, statement: str, expected: bool) -> None:
        root = repo(tmp_path, {"src/gaia_cli/extra.py": f"{statement}\n\nVALUE = 1\n"})
        observations = [
            item for item in of_kind(DeadCodeSensor().scan(root, NOW), "unused_import")
            if item.subject.id == "src/gaia_cli/extra.py"
        ]
        (observation,) = observations  # the unused import is still reported
        (finding,) = observation.observed_state["findings"]
        assert finding["sideEffectPossible"] is expected


# --------------------------------------------------------------------------
# F4: one decision record may acknowledge several frozen skills' history
# --------------------------------------------------------------------------


class TestF4SharedAcknowledgement:
    def test_one_record_acknowledges_another_skills_events_only_by_their_own_lines(self, tmp_path: Path) -> None:
        root = _frozen_repo(tmp_path)
        other = (root / "registry/named/owner/frozen.md").read_text(encoding="utf-8").replace(
            "id: owner/frozen", "id: owner/other"
        )
        (root / "registry/named/owner/other.md").write_text(other, encoding="utf-8")
        record = _record(BOTH, id="steward-frozen-history-batch")
        # Lines for owner/frozen only: owner/other has identical events but is
        # not named, so it must stay unacknowledged.
        target = root / "founder/steward/decisions/steward-frozen-history-batch.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(record), encoding="utf-8")
        track_all(root)
        observations = {obs.subject.id: obs for obs in FrozenSkillIntegritySensor().scan(root, NOW)}
        assert observations["owner/frozen"].status == "healthy"
        assert observations["owner/frozen"].observed_state["acknowledgementRecords"] == ["steward-frozen-history-batch"]
        assert observations["owner/other"].status == "drift"
        assert observations["owner/other"].observed_state["acknowledgementRecordPresent"] is False

    def test_records_outside_the_prefix_never_acknowledge(self, tmp_path: Path) -> None:
        record = _record(BOTH, id="steward-some-other-decision")
        root = _frozen_repo(tmp_path)
        target = root / "founder/steward/decisions/steward-some-other-decision.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(record), encoding="utf-8")
        track_all(root)
        (obs,) = FrozenSkillIntegritySensor().scan(root, NOW)
        assert obs.status == "drift"

    def test_repeating_a_line_in_two_records_does_not_cover_an_extra_duplicate(self, tmp_path: Path) -> None:
        root = _frozen_repo(tmp_path, record=_record(BOTH), extra=COPY)
        second = _record([E1], id="steward-frozen-history-second")
        (root / "founder/steward/decisions/steward-frozen-history-second.json").write_text(
            json.dumps(second), encoding="utf-8"
        )
        track_all(root)
        (obs,) = FrozenSkillIntegritySensor().scan(root, NOW)
        assert obs.status == "drift"
        assert obs.observed_state["unacknowledgedEventCount"] == 1

    def test_live_f4_record_resolves_the_four_mattpocock_findings(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        observations = {obs.subject.id: obs for obs in FrozenSkillIntegritySensor().scan(repo_root, NOW)}
        for skill in ("diagnose", "edit-article", "obsidian-vault", "ubiquitous-language"):
            obs = observations[f"mattpocock/{skill}"]
            assert obs.status == "healthy", skill
            assert obs.observed_state["levelMismatch"] is False
            assert obs.observed_state["acknowledgementRecords"] == ["steward-frozen-history-2026-11-08"]


# --------------------------------------------------------------------------
# F6: scoped benchmark exception for HumanEval's in-process exec
# --------------------------------------------------------------------------

HUMANEVAL = "scripts/benchmarks/humaneval/run.py"
F6_RECORD = "founder/steward/decisions/steward-humaneval-exec-benchmark-exception.json"
EXEC_IN_HARNESS = (
    "def _execAndCheck(problem, completion):\n"
    "    namespace = {}\n"
    "    exec(compile(completion, '<humaneval>', 'exec'), namespace)\n"
    "    return True\n"
)


def _f6(tmp_path: Path, files: dict[str, str], *, decided: bool = True):
    overrides = dict(files)
    if decided is not None:
        overrides[F6_RECORD] = json.dumps(
            {"id": "steward-humaneval-exec-benchmark-exception", "status": "decided" if decided else "open"}
        )
    _, observations = _mutation(tmp_path, **overrides)
    return {item.subject.id: item for item in _execution(observations)}


class TestF6ScopedExecException:
    def test_covered_exec_is_listed_acknowledged_and_the_file_is_healthy(self, tmp_path: Path) -> None:
        item = _f6(tmp_path, {HUMANEVAL: EXEC_IN_HARNESS})[HUMANEVAL]
        assert item.status == "healthy"
        (finding,) = item.observed_state["findings"]  # never silently dropped
        assert finding["pattern"] == "exec-nonliteral"
        assert finding["acknowledged"] is True
        assert finding["decisionRecord"] == F6_RECORD
        assert item.observed_state["acknowledgedCount"] == 1

    def test_same_exec_outside_the_benchmark_path_still_flags(self, tmp_path: Path) -> None:
        items = _f6(tmp_path, {"scripts/other/run.py": EXEC_IN_HARNESS})
        item = items["scripts/other/run.py"]
        assert item.status == "drift"
        assert "acknowledged" not in item.observed_state["findings"][0]

    def test_exec_in_another_function_of_the_benchmark_file_still_flags(self, tmp_path: Path) -> None:
        source = EXEC_IN_HARNESS + "\n\ndef helper(code):\n    exec(code)\n"
        item = _f6(tmp_path, {HUMANEVAL: source})[HUMANEVAL]
        assert item.status == "drift"
        flags = {(f["line"], bool(f.get("acknowledged"))) for f in item.observed_state["findings"]}
        assert flags == {(3, True), (8, False)}

    def test_other_patterns_in_the_covered_function_still_flag(self, tmp_path: Path) -> None:
        source = EXEC_IN_HARNESS.replace("    return True\n", "    eval(completion)\n    return True\n")
        item = _f6(tmp_path, {HUMANEVAL: source})[HUMANEVAL]
        assert item.status == "drift"
        assert [f["pattern"] for f in item.observed_state["findings"] if not f.get("acknowledged")] == ["eval-nonliteral"]

    @pytest.mark.parametrize("decided", [False, None])
    def test_without_a_decided_record_the_exception_does_not_hold(self, tmp_path: Path, decided) -> None:
        item = _f6(tmp_path, {HUMANEVAL: EXEC_IN_HARNESS}, decided=decided)[HUMANEVAL]
        assert item.status == "drift"
        assert item.observed_state["acknowledgedCount"] == 0


class TestF6QualifiedScope:
    """#2372 review: the exception binds the module-level function only."""

    def test_same_named_method_is_not_covered(self, tmp_path: Path) -> None:
        source = EXEC_IN_HARNESS + "\n\nclass Other:\n    def _execAndCheck(self, code):\n        exec(code)\n"
        item = _f6(tmp_path, {HUMANEVAL: source})[HUMANEVAL]
        assert item.status == "drift"
        flags = {(f["line"], bool(f.get("acknowledged"))) for f in item.observed_state["findings"]}
        assert flags == {(3, True), (9, False)}

    def test_nested_function_of_the_same_name_is_not_covered(self, tmp_path: Path) -> None:
        source = (
            "def runner(code):\n"
            "    def _execAndCheck(problem, completion):\n"
            "        exec(completion)\n"
            "    return _execAndCheck\n"
        )
        item = _f6(tmp_path, {HUMANEVAL: source})[HUMANEVAL]
        assert item.status == "drift"
        assert item.observed_state["acknowledgedCount"] == 0

    def test_def_nested_inside_the_covered_function_is_not_covered(self, tmp_path: Path) -> None:
        source = (
            "def _execAndCheck(problem, completion):\n"
            "    def inner(code):\n"
            "        exec(code)\n"
            "    return inner\n"
        )
        item = _f6(tmp_path, {HUMANEVAL: source})[HUMANEVAL]
        assert item.status == "drift"
        assert item.observed_state["acknowledgedCount"] == 0

    def test_second_top_level_redefinition_fails_closed_for_both(self, tmp_path: Path) -> None:
        source = EXEC_IN_HARNESS + "\n\n" + EXEC_IN_HARNESS
        item = _f6(tmp_path, {HUMANEVAL: source})[HUMANEVAL]
        assert item.status == "drift"
        assert item.observed_state["acknowledgedCount"] == 0
