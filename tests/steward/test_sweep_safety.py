"""A corrupted subject must never turn UNKNOWN into PASS.

Exhaustive sensors sweep (resolve) open debt they stop observing. That is only
sound when the sensor really looked at every subject. Each case below follows
the same shape: a fixture with a real finding, one controller scan that opens
the debt, a corruption of exactly that subject, a second scan, and the proof
that the debt is still open and the receipt lists the sensor under
``partialCoverage``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

import pytest

from gaia_cli.steward import sensors_security
from gaia_cli.steward.controller import ScanResult, StewardController
from gaia_cli.steward.debt import reconcile_debt
from gaia_cli.steward.models import Observation, SensorScan, Subject
from gaia_cli.steward.policy import POLICY_RELATIVE_PATH, StewardPolicy
from gaia_cli.steward.primitives import SensorUnavailable, SkipLog
from gaia_cli.steward.primitives.files import SKIP_CAP
from gaia_cli.steward.sensors import (
    TaxonomyScriptDriftSensor,
    TrustCalibrationDriftSensor,
)
from gaia_cli.steward.sensors_code import (
    CodeStructureSensor,
    DeadCodeSensor,
    ErrorHandlingSensor,
)
from gaia_cli.steward.sensors_security import (
    BrowserSinkSensor,
    MutationBoundarySensor,
    SecretScanSensor,
)
from gaia_cli.steward.sensors_tests import TestIsolationSensor, TestPortfolioSensor
from tests.steward.sensor_fixtures import (
    FIXTURE_EVIDENCE_META,
    TRUST_MAGNITUDE_STUB,
    make_repo,
    write_files,
)
from tests.steward.test_sensors_code import BASE as CODE_BASE
from tests.steward.test_sensors_security import _dev_init, _github_token, _mutation_files
from tests.steward.test_sensors_tests import CLEAN_TEST, PYPROJECT

REPO_ROOT = Path(__file__).resolve().parents[2]
NOW = "2026-10-20T00:00:00Z"
START = datetime(2026, 10, 20, tzinfo=timezone.utc)


class Clock:
    """One minute per read, so every run is distinct."""

    def __init__(self) -> None:
        self.now = START

    def __call__(self) -> datetime:
        self.now += timedelta(minutes=1)
        return self.now


def install(root: Path, policy_edit: Callable[[str], str] | None = None) -> Path:
    destination = root / POLICY_RELATIVE_PATH
    destination.parent.mkdir(parents=True, exist_ok=True)
    text = (REPO_ROOT / POLICY_RELATIVE_PATH).read_text(encoding="utf-8")
    destination.write_text(policy_edit(text) if policy_edit else text, encoding="utf-8")
    return root


def fixture(tmp_path: Path, files: dict[str, str]) -> Path:
    return install(make_repo(tmp_path / "repo", files))


def open_ids(result: ScanResult, kind: str) -> set[str]:
    return {debt.subject.id for debt in result.open_debts if debt.kind == kind}


def partial(result: ScanResult) -> dict[str, dict]:
    return {item["sensor"]: item for item in result.receipt.partial_coverage}


def assert_unswept(first: ScanResult, second: ScanResult, kind: str, subject: str, sensor: str) -> None:
    assert subject in open_ids(first, kind)
    assert subject in open_ids(second, kind), "a skipped subject's debt was swept as resolved"
    debt = next(item for item in second.debts if item.kind == kind and item.subject.id == subject)
    assert debt.status == "open" and debt.resolution is None
    assert sensor in partial(second)
    assert partial(second)[sensor]["skippedCount"] >= 1
    assert second.receipt.to_dict()["partialCoverage"]
    # The sensor completed, so its coverage is known: partial, not unknown.
    assert sensor in second.receipt.coverage_known
    assert sensor not in second.receipt.coverage_unknown


def scan_twice(
    root: Path, sensor: object, corrupt: Callable[[Path], None]
) -> tuple[ScanResult, ScanResult]:
    controller = StewardController(sensors=[sensor], clock=Clock())
    first = controller.scan(root)
    assert not first.receipt.partial_coverage
    corrupt(root)
    return first, controller.scan(root)


# ---------------------------------------------------------------- controller


@dataclass
class DriftSensor:
    id: str
    subjects: list[str] = field(default_factory=list)
    skipped: list[dict[str, str]] = field(default_factory=list)
    resolution_scope: str | None = "exhaustive"
    detailed: bool = True

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        return list(self._observations(observed_at))

    def scan_detailed(self, repo_root: Path, observed_at: str) -> SensorScan:
        return SensorScan(tuple(self._observations(observed_at)), tuple(self.skipped))

    def _observations(self, observed_at: str) -> list[Observation]:
        return [
            Observation(
                kind="trust_calibration_drift",
                subject=Subject(type="named-skill", id=name),
                observed_at=observed_at,
                source=self.id,
                status="drift",
                current_state={"level": "3★"},
                observed_state={"targetLevel": "2★"},
                confidence=1.0,
            )
            for name in self.subjects
        ]


class LegacySensor(DriftSensor):
    """Defines only ``scan``, as every sensor did before this protocol."""

    scan_detailed = None  # type: ignore[assignment]


def skip(identity: str) -> dict[str, str]:
    return {"subjectType": "source-file", "subjectId": identity, "reason": "not UTF-8"}


def bare(tmp_path: Path) -> Path:
    return install(tmp_path)


def test_a_sensor_with_a_skipped_subject_sweeps_nothing_but_keeps_its_observations(tmp_path: Path) -> None:
    root = bare(tmp_path)
    sensor = DriftSensor("fixture-partial", ["owner/a", "owner/b"])
    controller = StewardController(sensors=[sensor], clock=Clock())
    first = controller.scan(root)
    assert open_ids(first, "trust_calibration_drift") == {"owner/a", "owner/b"}

    sensor.subjects = ["owner/a"]
    sensor.skipped = [skip("owner/b")]
    second = controller.scan(root)

    assert open_ids(second, "trust_calibration_drift") == {"owner/a", "owner/b"}
    assert second.receipt.debt_resolved == ()
    assert partial(second)["fixture-partial"]["skippedCount"] == 1
    assert partial(second)["fixture-partial"]["skipped"] == [skip("owner/b")]
    assert "fixture-partial" in second.receipt.coverage_known

    sensor.skipped = []
    third = controller.scan(root)
    assert open_ids(third, "trust_calibration_drift") == {"owner/a"}
    assert third.receipt.partial_coverage == ()


def test_a_legacy_sensor_returning_a_plain_list_still_sweeps(tmp_path: Path) -> None:
    root = bare(tmp_path)
    sensor = LegacySensor("fixture-legacy", ["owner/a", "owner/b"])
    controller = StewardController(sensors=[sensor], clock=Clock())
    controller.scan(root)
    sensor.subjects = ["owner/a"]
    second = controller.scan(root)
    assert open_ids(second, "trust_calibration_drift") == {"owner/a"}
    assert second.receipt.partial_coverage == ()


def test_scan_returning_a_sensor_scan_is_accepted(tmp_path: Path) -> None:
    root = bare(tmp_path)

    class Returns(LegacySensor):
        def scan(self, repo_root: Path, observed_at: str):  # type: ignore[override]
            return SensorScan(tuple(self._observations(observed_at)), (skip("owner/x"),))

    result = StewardController(sensors=[Returns("fixture-returns", ["owner/a"])], clock=Clock()).scan(root)
    assert "fixture-returns" in partial(result)


def test_receipt_lists_only_the_first_twenty_skips_but_counts_all(tmp_path: Path) -> None:
    root = bare(tmp_path)
    sensor = DriftSensor("fixture-many", skipped=[skip(f"f{index:03d}.py") for index in range(SKIP_CAP + 5)])
    result = StewardController(sensors=[sensor], clock=Clock()).scan(root)
    entry = partial(result)["fixture-many"]
    assert entry["skippedCount"] == SKIP_CAP + 5
    assert len(entry["skipped"]) == SKIP_CAP


def test_partial_coverage_is_part_of_the_run_identity(tmp_path: Path) -> None:
    fixed = lambda: START  # noqa: E731 - identical clock on purpose
    plain = StewardController(sensors=[DriftSensor("fixture-id", ["owner/a"])], clock=fixed).scan(
        bare(tmp_path / "a")
    )
    skipping = StewardController(
        sensors=[DriftSensor("fixture-id", ["owner/a"], skipped=[skip("owner/b")])], clock=fixed
    ).scan(bare(tmp_path / "b"))
    assert plain.receipt.run_id != skipping.receipt.run_id


def test_a_malformed_skip_record_makes_the_sensor_unknown_not_partial(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        SensorScan((), ({"subjectType": "x", "subjectId": "", "reason": "r"},))
    root = bare(tmp_path)

    class Broken(LegacySensor):
        def scan(self, repo_root: Path, observed_at: str):  # type: ignore[override]
            return SensorScan((), ({"subjectType": "x"},))  # type: ignore[arg-type]

    result = StewardController(sensors=[Broken("fixture-broken")], clock=Clock()).scan(root)
    assert result.receipt.coverage_unknown == ("fixture-broken",)


def test_reconcile_debt_still_sweeps_exactly_the_sources_it_is_given(tmp_path: Path) -> None:
    root = bare(tmp_path)
    controller = StewardController(sensors=[DriftSensor("fixture-sweep", ["owner/a"])], clock=Clock())
    seeded = controller.scan(root)
    policy = StewardPolicy.load(root)
    held = reconcile_debt([], {debt.id: debt for debt in seeded.debts}, policy, exhaustive_sources=())
    assert [debt.status for debt in held.debts] == ["open"]


def test_the_sensor_that_crosses_the_observation_budget_becomes_unknown_and_others_keep_theirs(
    tmp_path: Path,
) -> None:
    root = install(tmp_path, lambda text: text.replace("maxObservationsPerRun: 1000", "maxObservationsPerRun: 6"))
    small = DriftSensor("fixture-small", ["owner/a", "owner/b"])
    large = DriftSensor("fixture-large", [f"owner/l{index}" for index in range(8)])
    after = DriftSensor("fixture-after", ["owner/z"])
    result = StewardController(sensors=[small, large, after], clock=Clock()).scan(root)

    assert result.receipt.coverage_unknown == ("fixture-large",)
    assert set(result.receipt.coverage_known) == {"fixture-small", "fixture-after"}
    assert open_ids(result, "trust_calibration_drift") == {"owner/a", "owner/b", "owner/z"}
    error = next(
        item.observed_state["error"]
        for item in result.observations
        if item.kind == "sensor_coverage_unknown" and item.status == "drift"
    )
    assert "budget exceeded" in error and "fixture-large" in error


def test_an_over_budget_sensor_does_not_sweep_its_existing_debt(tmp_path: Path) -> None:
    root = install(tmp_path, lambda text: text.replace("maxObservationsPerRun: 1000", "maxObservationsPerRun: 6"))
    large = DriftSensor("fixture-large", ["owner/a"])
    controller = StewardController(sensors=[large], clock=Clock())
    controller.scan(root)
    large.subjects = [f"owner/l{index}" for index in range(8)]
    second = controller.scan(root)
    assert "owner/a" in open_ids(second, "trust_calibration_drift")
    assert second.receipt.coverage_unknown == ("fixture-large",)


# ------------------------------------------------------------------- skiplog


def test_skip_log_deduplicates_sorts_and_bounds_reasons() -> None:
    log = SkipLog()
    log.add("source-file", "b.py", "x" * 500)
    log.add("source-file", "a.py", "first")
    log.add("source-file", "a.py", "ignored duplicate")
    entries = log.entries()
    assert [item["subjectId"] for item in entries] == ["a.py", "b.py"]
    assert entries[0]["reason"] == "first"
    assert len(entries[1]["reason"]) == 200
    log.require_coverage(5, "files")
    with pytest.raises(SensorUnavailable):
        log.require_coverage(2, "files")
    SkipLog().require_coverage(0, "files")


# ------------------------------------------------------------ secret scanning


SECRET_FILES = {"README.md": "clean\n", "src/a.py": f"k = '{_github_token()}'\n"}


def test_secret_scan_appended_non_utf8_byte_does_not_hide_the_leak(tmp_path: Path) -> None:
    root = fixture(tmp_path, SECRET_FILES)

    def corrupt(path: Path) -> None:
        with (path / "src/a.py").open("ab") as handle:
            handle.write(b"\xff")

    first, second = scan_twice(root, SecretScanSensor(), corrupt)
    assert "src/a.py" in open_ids(first, "credential_leak")
    assert "src/a.py" in open_ids(second, "credential_leak")
    assert second.receipt.partial_coverage == ()


def test_secret_scan_oversize_file_keeps_its_debt_and_reports_partial_coverage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sensors_security, "_SECRET_MAX_BYTES", 400)
    root = fixture(tmp_path, SECRET_FILES)

    def corrupt(path: Path) -> None:
        with (path / "src/a.py").open("a", encoding="utf-8") as handle:
            handle.write("#" * 600)

    first, second = scan_twice(root, SecretScanSensor(), corrupt)
    assert_unswept(first, second, "credential_leak", "src/a.py", "secret-scan")
    assert partial(second)["secret-scan"]["skipped"][0]["subjectId"] == "src/a.py"


def test_secret_scan_with_every_file_too_large_is_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sensors_security, "_SECRET_MAX_BYTES", 1)
    root = fixture(tmp_path, SECRET_FILES)
    with pytest.raises(SensorUnavailable, match="could not be evaluated"):
        SecretScanSensor().scan(root, NOW)


# --------------------------------------------------------------- browser sink


BROWSER_FILES = {
    "docs/js/app.js": "el.innerHTML = userInput;\n",
    "docs/js/other.js": "document.title = 'ok';\n",
}


@pytest.mark.parametrize("how", ["non-utf8", "oversize"])
def test_browser_sink_corrupted_file_keeps_its_debt(tmp_path: Path, how: str) -> None:
    root = fixture(tmp_path, BROWSER_FILES)

    def corrupt(path: Path) -> None:
        target = path / "docs/js/app.js"
        if how == "non-utf8":
            target.write_bytes(b"el.innerHTML = userInput;\n\xff\xfe")
        else:
            target.write_text("el.innerHTML = userInput;\n" + "//" + "x" * (2 * 1024 * 1024), encoding="utf-8")

    first, second = scan_twice(root, BrowserSinkSensor(), corrupt)
    assert_unswept(first, second, "browser_sink_risk", "docs/js/app.js", "browser-sink")


def test_browser_sink_with_every_file_unreadable_is_unavailable(tmp_path: Path) -> None:
    root = fixture(tmp_path, {"docs/js/app.js": "el.innerHTML = userInput;\n"})
    (root / "docs/js/app.js").write_bytes(b"\xff\xfe")
    with pytest.raises(SensorUnavailable, match="could not be evaluated"):
        BrowserSinkSensor().scan(root, NOW)


# --------------------------------------------------------- code-analysis trio


def code_fixture(tmp_path: Path, extra: dict[str, str]) -> Path:
    return fixture(tmp_path, {**CODE_BASE, **extra})


def break_syntax(relative: str) -> Callable[[Path], None]:
    def corrupt(path: Path) -> None:
        (path / relative).write_text("def broken(:\n", encoding="utf-8")

    return corrupt


def test_dead_code_syntax_error_keeps_its_unused_import_debt(tmp_path: Path) -> None:
    root = code_fixture(tmp_path, {"src/gaia_cli/dirty.py": "import os\n\nVALUE = 1\n"})
    first, second = scan_twice(root, DeadCodeSensor(), break_syntax("src/gaia_cli/dirty.py"))
    assert_unswept(first, second, "unused_import", "src/gaia_cli/dirty.py", "dead-code")


def test_dead_code_syntax_error_in_a_test_consumer_is_also_reported(tmp_path: Path) -> None:
    root = code_fixture(
        tmp_path,
        {"src/gaia_cli/dirty.py": "import os\n\nVALUE = 1\n", "tests/test_other.py": "def test_x():\n    assert True\n"},
    )
    first, second = scan_twice(root, DeadCodeSensor(), break_syntax("tests/test_core.py"))
    assert partial(second)["dead-code"]["skipped"][0]["subjectId"] == "tests/test_core.py"
    assert "src/gaia_cli/dirty.py" in open_ids(second, "unused_import")


CYCLE = {
    "src/gaia_cli/cyc_a.py": "from gaia_cli import cyc_b\n\n\ndef fa():\n    return cyc_b\n",
    "src/gaia_cli/cyc_b.py": "from gaia_cli import cyc_a\n\n\ndef fb():\n    return cyc_a\n",
}


def test_code_structure_syntax_error_keeps_its_import_cycle_debt(tmp_path: Path) -> None:
    root = code_fixture(tmp_path, CYCLE)
    first, second = scan_twice(root, CodeStructureSensor(), break_syntax("src/gaia_cli/cyc_a.py"))
    cycle = next(item for item in open_ids(first, "import_cycle"))
    assert_unswept(first, second, "import_cycle", cycle, "code-structure")


SWALLOW = "def f():\n    try:\n        return 1\n    except Exception:\n        pass\n"


def test_error_handling_syntax_error_keeps_its_swallowed_exception_debt(tmp_path: Path) -> None:
    root = code_fixture(tmp_path, {"src/gaia_cli/swallow.py": SWALLOW})
    first, second = scan_twice(root, ErrorHandlingSensor(), break_syntax("src/gaia_cli/swallow.py"))
    assert_unswept(first, second, "swallowed_exception", "src/gaia_cli/swallow.py", "error-handling")


@pytest.mark.parametrize("sensor", [DeadCodeSensor, CodeStructureSensor, ErrorHandlingSensor])
def test_code_sensors_with_every_python_file_unparseable_are_unavailable(tmp_path: Path, sensor) -> None:
    root = fixture(
        tmp_path,
        {
            "pyproject.toml": CODE_BASE["pyproject.toml"],
            "src/gaia_cli/only.py": "def broken(:\n",
            "scripts/only.py": "def broken(:\n",
        },
    )
    with pytest.raises(SensorUnavailable, match="failed to parse"):
        sensor().scan(root, NOW)


# ------------------------------------------------------------- test sensors


PORTFOLIO = {
    "pyproject.toml": PYPROJECT,
    "tests/test_clean.py": CLEAN_TEST,
    "tests/test_dup.py": "def test_a():\n    pass\n\n\ndef test_a():\n    pass\n",
}


@pytest.mark.parametrize("how", ["syntax", "non-utf8"])
def test_test_portfolio_corrupted_file_keeps_its_debt(tmp_path: Path, how: str) -> None:
    root = fixture(tmp_path, PORTFOLIO)

    def corrupt(path: Path) -> None:
        if how == "syntax":
            (path / "tests/test_dup.py").write_text("def test_a(:\n", encoding="utf-8")
        else:
            (path / "tests/test_dup.py").write_bytes(b"\xff\xfe\x00")

    first, second = scan_twice(root, TestPortfolioSensor(), corrupt)
    assert_unswept(first, second, "shadowed_test", "tests/test_dup.py", "test-portfolio")


ISOLATION = {
    "pyproject.toml": PYPROJECT,
    "tests/test_clean.py": CLEAN_TEST,
    "tests/test_iso.py": "import time\n\n\ndef test_a():\n    time.sleep(3)\n",
}


@pytest.mark.parametrize("how", ["syntax", "non-utf8"])
def test_test_isolation_corrupted_file_keeps_its_debt(tmp_path: Path, how: str) -> None:
    root = fixture(tmp_path, ISOLATION)

    def corrupt(path: Path) -> None:
        if how == "syntax":
            (path / "tests/test_iso.py").write_text("def (:\n", encoding="utf-8")
        else:
            (path / "tests/test_iso.py").write_bytes(b"\xff\xfe\x00")

    first, second = scan_twice(root, TestIsolationSensor(), corrupt)
    assert_unswept(first, second, "test_isolation_risk", "tests/test_iso.py", "test-isolation")


@pytest.mark.parametrize("sensor", [TestPortfolioSensor, TestIsolationSensor])
def test_test_sensors_with_every_file_unreadable_are_unavailable(tmp_path: Path, sensor) -> None:
    root = fixture(tmp_path, {"pyproject.toml": PYPROJECT, "tests/test_only.py": CLEAN_TEST})
    (root / "tests/test_only.py").write_bytes(b"\xff\xfe\x00")
    with pytest.raises(SensorUnavailable, match="could not be evaluated"):
        sensor().scan(root, NOW)


# --------------------------------------------------------- mutation boundary


def test_mutation_boundary_syntax_error_keeps_its_unsafe_execution_debt(tmp_path: Path) -> None:
    root = fixture(tmp_path, _mutation_files(**{"scripts/tool.py": "eval(x)\n"}))
    first, second = scan_twice(root, MutationBoundarySensor(), break_syntax("scripts/tool.py"))
    assert_unswept(first, second, "unsafe_execution", "scripts/tool.py", "mutation-boundary")


EXPORTER = (
    "from pathlib import Path\n\n\n"
    "def exportCommand(args):\n"
    "    Path(args.registry).joinpath('out.json').write_text('{}')\n"
)


def exporter_files() -> dict[str, str]:
    return _mutation_files(
        **{
            "src/gaia_cli/commands/dev/__init__.py": _dev_init(
                parsers="add rm list export",
                dispatch={
                    "add": "gaia_cli.commands.dev.writer:addCommand",
                    "rm": "gaia_cli.commands.dev.writer:rmCommand",
                    "list": "gaia_cli.commands.dev.reader:listCommand",
                    "export": "gaia_cli.commands.dev.exporter:exportCommand",
                },
            ),
            "src/gaia_cli/commands/dev/exporter.py": EXPORTER,
        }
    )


def test_mutation_boundary_unanalysable_handler_keeps_its_ungated_mutation_debt(tmp_path: Path) -> None:
    root = fixture(tmp_path, exporter_files())
    first, second = scan_twice(
        root, MutationBoundarySensor(), break_syntax("src/gaia_cli/commands/dev/exporter.py")
    )
    assert_unswept(first, second, "ungated_mutation", "dev:export", "mutation-boundary")


def test_mutation_boundary_command_with_no_dispatch_handler_is_reported(tmp_path: Path) -> None:
    files = exporter_files()
    root = fixture(tmp_path, files)

    def corrupt(path: Path) -> None:
        write_files(
            path,
            {
                "src/gaia_cli/commands/dev/__init__.py": _dev_init(
                    parsers="add rm list export",
                    dispatch={
                        "add": "gaia_cli.commands.dev.writer:addCommand",
                        "rm": "gaia_cli.commands.dev.writer:rmCommand",
                        "list": "gaia_cli.commands.dev.reader:listCommand",
                    },
                )
            },
        )

    first, second = scan_twice(root, MutationBoundarySensor(), corrupt)
    assert_unswept(first, second, "ungated_mutation", "dev:export", "mutation-boundary")
    assert partial(second)["mutation-boundary"]["skipped"][0]["subjectId"] == "dev:export"


# ------------------------------------------------------- trust calibration


STALE = (
    "---\n"
    "id: owner/stale\nname: Stale\nstatus: named\nlevel: 5★\n"
    "evidence:\n  - type: github-stars-own\n    source: https://github.com/owner/repo\n    stars: 10000\n---\n"
)


@pytest.mark.parametrize("how", ["unclosed-fence", "no-id"])
def test_trust_calibration_unscorable_record_keeps_its_debt(tmp_path: Path, how: str) -> None:
    root = fixture(tmp_path, {"registry/named/owner/stale.md": STALE})

    def corrupt(path: Path) -> None:
        text = STALE.replace("id: owner/stale\n", "") if how == "no-id" else STALE[: -len("---\n")]
        (path / "registry/named/owner/stale.md").write_text(text, encoding="utf-8")

    first, second = scan_twice(root, TrustCalibrationDriftSensor(), corrupt)
    assert_unswept(first, second, "trust_calibration_drift", "owner/stale", "trust-calibration-drift")


# ----------------------------------------------------------------- taxonomy


TAXONOMY = {
    "registry/schema/meta.json": json.dumps(FIXTURE_EVIDENCE_META),
    "src/gaia_cli/trustMagnitude.py": TRUST_MAGNITUDE_STUB,
    "scripts/check.py": "KNOWN_EVIDENCE_TYPES = ['not-a-real-type']\n",
}


def test_taxonomy_unparseable_script_stays_drift_instead_of_reading_healthy(tmp_path: Path) -> None:
    # The sensor emits one aggregate observation. Skipping the broken file used
    # to leave that observation healthy and resolve the open debt. A file whose
    # evidence-type lists cannot be checked is itself a finding, exactly like
    # the unparseable trustMagnitude.py case, so the surface stays inconsistent.
    root = fixture(tmp_path, TAXONOMY)
    first, second = scan_twice(root, TaxonomyScriptDriftSensor(), break_syntax("scripts/check.py"))
    assert "taxonomy-script-surface" in open_ids(first, "taxonomy_script_drift")
    assert "taxonomy-script-surface" in open_ids(second, "taxonomy_script_drift")
    kinds = {item["kind"] for item in next(
        debt for debt in second.debts if debt.kind == "taxonomy_script_drift"
    ).observed_state["violations"]}
    assert "parse-error" in kinds


# ----------------------------------------------------------- named records


NAMED = {
    "registry/named/owner/stale.md": STALE,
    "registry/named/owner/other.md": STALE.replace("owner/stale", "owner/other"),
}


def test_a_truncated_named_checkout_makes_the_sensor_blind_not_clean(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "repo", NAMED)
    (root / "registry/named/owner/other.md").unlink()
    with pytest.raises(SensorUnavailable, match="named-skill records are missing"):
        TrustCalibrationDriftSensor().scan(root, NOW)


def test_named_records_that_are_only_untracked_do_not_count_as_a_domain(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "repo", {"README.md": "x\n"})
    write_files(root, NAMED)
    with pytest.raises(SensorUnavailable, match="named-skill records are missing"):
        TrustCalibrationDriftSensor().scan(root, NOW)


def test_named_records_outside_a_git_worktree_are_unavailable(tmp_path: Path) -> None:
    root = tmp_path / "plain"
    write_files(root, NAMED)
    with pytest.raises(SensorUnavailable, match="named-skill records are missing"):
        TrustCalibrationDriftSensor().scan(root, NOW)


def test_a_truncated_named_checkout_keeps_existing_trust_debt_open(tmp_path: Path) -> None:
    root = fixture(tmp_path, NAMED)
    sensor = TrustCalibrationDriftSensor()
    controller = StewardController(sensors=[sensor], clock=Clock())
    first = controller.scan(root)
    assert {"owner/stale", "owner/other"} <= open_ids(first, "trust_calibration_drift")
    (root / "registry/named/owner/other.md").unlink()
    second = controller.scan(root)
    assert {"owner/stale", "owner/other"} <= open_ids(second, "trust_calibration_drift")
    assert second.receipt.coverage_unknown == ("trust-calibration-drift",)
