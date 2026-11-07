"""Contract tests for gaia_cli.structuredRead (#2283 canonical loader).

Every failure fixture (missing, malformed, permission, encoding) is exercised
in every mode: required raises, optional defaults only on absence, bestEffort
always defaults with a diagnostic, authority always fails closed.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from gaia_cli import structuredRead as sr
from gaia_cli.structuredRead import (
    AuthorityInputError,
    DiagnosticLog,
    InputReadError,
    ReadDiagnostic,
    readFrontmatter,
    readJson,
    readText,
    readYaml,
)


def _permission_denied_supported() -> bool:
    if sys.platform.startswith("win"):
        return False
    return not (hasattr(os, "geteuid") and os.geteuid() == 0)


@pytest.fixture
def fixtures(tmp_path: Path) -> dict[str, Path]:
    good = tmp_path / "good.json"
    good.write_text('{"a": 1}', encoding="utf-8")
    malformed = tmp_path / "malformed.json"
    malformed.write_text('{"a": 1,', encoding="utf-8")
    encoding = tmp_path / "latin1.json"
    encoding.write_bytes(b'{"a": "caf\xe9"}')
    denied = tmp_path / "denied.json"
    denied.write_text('{"a": 1}', encoding="utf-8")
    denied.chmod(0)
    yield {
        "good": good,
        "missing": tmp_path / "missing.json",
        "malformed": malformed,
        "permission": denied,
        "encoding": encoding,
    }
    denied.chmod(0o600)


FAILURES = {
    "missing": "missing",
    "malformed": "malformed",
    "permission": "unreadable",
    "encoding": "encoding",
}


def _skip_permission(name: str) -> None:
    if name == "permission" and not _permission_denied_supported():
        pytest.skip("permission errors cannot be produced here (root or Windows)")


# ---------------------------------------------------------------- happy path


@pytest.mark.parametrize("mode", ["required", "authority"])
def test_good_input_parses_in_strict_modes(fixtures, mode: str) -> None:
    assert readJson(fixtures["good"], mode=mode) == {"a": 1}


@pytest.mark.parametrize("mode", ["optional", "bestEffort"])
def test_good_input_parses_without_a_diagnostic(fixtures, mode: str) -> None:
    log = DiagnosticLog()
    assert readJson(fixtures["good"], mode=mode, default={}, onDiagnostic=log) == {"a": 1}
    assert len(log) == 0


# ------------------------------------------------------------- failure matrix


@pytest.mark.parametrize("name", list(FAILURES))
def test_required_raises_a_typed_error_with_path_and_kind(fixtures, name: str) -> None:
    _skip_permission(name)
    with pytest.raises(InputReadError) as caught:
        readJson(fixtures[name], mode="required")
    error = caught.value
    assert not isinstance(error, AuthorityInputError)
    assert error.kind == FAILURES[name]
    assert error.path == str(fixtures[name])
    assert error.mode == "required"
    assert str(fixtures[name]) in str(error)


@pytest.mark.parametrize("name", list(FAILURES))
def test_authority_always_fails_closed(fixtures, name: str) -> None:
    _skip_permission(name)
    with pytest.raises(AuthorityInputError) as caught:
        readJson(fixtures[name], mode="authority")
    assert caught.value.kind == FAILURES[name]


@pytest.mark.parametrize("name", list(FAILURES))
def test_best_effort_returns_the_default_and_reports(fixtures, name: str) -> None:
    _skip_permission(name)
    log = DiagnosticLog()
    assert readJson(fixtures[name], mode="bestEffort", default={"fallback": True}, onDiagnostic=log) == {
        "fallback": True
    }
    (diagnostic,) = log.entries
    assert diagnostic == ReadDiagnostic(
        path=str(fixtures[name]), kind=FAILURES[name], mode="bestEffort", detail=diagnostic.detail
    )
    assert diagnostic.detail


def test_optional_defaults_only_when_the_file_is_absent(fixtures) -> None:
    log = DiagnosticLog()
    assert readJson(fixtures["missing"], mode="optional", default={"installed": []}, onDiagnostic=log) == {
        "installed": []
    }
    assert [entry.kind for entry in log.entries] == ["missing"]


@pytest.mark.parametrize("name", ["malformed", "permission", "encoding"])
def test_optional_never_replaces_a_present_but_broken_file(fixtures, name: str) -> None:
    _skip_permission(name)
    log = DiagnosticLog()
    with pytest.raises(InputReadError) as caught:
        readJson(fixtures[name], mode="optional", default={}, onDiagnostic=log)
    assert caught.value.kind == FAILURES[name]
    assert caught.value.mode == "optional"
    assert len(log) == 0


# ------------------------------------------------------------- the contract


def test_mode_is_required_and_validated(fixtures) -> None:
    with pytest.raises(TypeError):
        readJson(fixtures["good"])  # type: ignore[call-arg]
    with pytest.raises(ValueError):
        readJson(fixtures["good"], mode="lenient")


@pytest.mark.parametrize("mode", ["required", "authority"])
def test_strict_modes_refuse_a_default(fixtures, mode: str) -> None:
    with pytest.raises(TypeError):
        readJson(fixtures["missing"], mode=mode, default={})


@pytest.mark.parametrize("mode", ["optional", "bestEffort"])
def test_defaulting_modes_need_an_explicit_default_and_a_sink(fixtures, mode: str) -> None:
    with pytest.raises(TypeError, match="explicit default"):
        readJson(fixtures["missing"], mode=mode, onDiagnostic=DiagnosticLog())
    with pytest.raises(TypeError, match="never silent"):
        readJson(fixtures["missing"], mode=mode, default={})
    with pytest.raises(TypeError, match="never silent"):
        readJson(fixtures["missing"], mode=mode, default={}, onDiagnostic="log")


def test_contract_is_checked_before_any_read(fixtures) -> None:
    # A misused call fails even when the file is fine: misuse is never latent.
    with pytest.raises(TypeError):
        readJson(fixtures["good"], mode="bestEffort", default={})


def test_default_is_copied_so_callers_cannot_share_mutable_state(fixtures) -> None:
    default = {"items": []}
    first = readJson(fixtures["missing"], mode="bestEffort", default=default, onDiagnostic=DiagnosticLog())
    first["items"].append(1)
    assert default == {"items": []}


def test_shape_mismatch_is_a_failure_handled_by_the_mode(tmp_path: Path) -> None:
    listed = tmp_path / "list.json"
    listed.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(InputReadError) as caught:
        readJson(listed, mode="required", expect=dict)
    assert caught.value.kind == "shape"
    log = DiagnosticLog()
    assert readJson(listed, mode="bestEffort", default={}, onDiagnostic=log, expect=dict) == {}
    assert log.entries[0].kind == "shape"
    with pytest.raises(InputReadError):
        readJson(listed, mode="optional", default={}, onDiagnostic=log, expect=dict)


def test_oversize_input_is_refused(tmp_path: Path) -> None:
    big = tmp_path / "big.json"
    big.write_text('{"a": "' + "x" * 100 + '"}', encoding="utf-8")
    with pytest.raises(InputReadError) as caught:
        readJson(big, mode="required", maxBytes=50)
    assert caught.value.kind == "oversize"


def test_directory_is_unreadable_not_missing(tmp_path: Path) -> None:
    with pytest.raises(InputReadError) as caught:
        readJson(tmp_path, mode="required")
    assert caught.value.kind == "unreadable"


def test_diagnostics_never_echo_file_content(tmp_path: Path) -> None:
    sample = tmp_path / "sample.json"
    sample.write_text('{"content": "do-not-print-me", ', encoding="utf-8")
    log = DiagnosticLog()
    readJson(sample, mode="bestEffort", default={}, onDiagnostic=log)
    assert "do-not-print-me" not in str(log.entries[0])
    with pytest.raises(InputReadError) as caught:
        readJson(sample, mode="required")
    assert "do-not-print-me" not in str(caught.value)


def test_utf8_bom_is_accepted(tmp_path: Path) -> None:
    bom = tmp_path / "bom.json"
    bom.write_bytes(b"\xef\xbb\xbf" + b'{"a": 1}')
    assert readJson(bom, mode="required") == {"a": 1}


def test_log_diagnostic_sink_logs_absence_at_info_and_damage_at_warning(fixtures, caplog) -> None:
    caplog.set_level("INFO", logger="gaia_cli.structuredRead")
    readJson(fixtures["missing"], mode="bestEffort", default={}, onDiagnostic=sr.logDiagnostic)
    readJson(fixtures["malformed"], mode="bestEffort", default={}, onDiagnostic=sr.logDiagnostic)
    levels = [(record.levelname, "missing" in record.getMessage()) for record in caplog.records]
    assert levels == [("INFO", True), ("WARNING", False)]


# ------------------------------------------------------- text / yaml / frontmatter


def test_read_text_modes(fixtures) -> None:
    assert readText(fixtures["good"], mode="required") == '{"a": 1}'
    with pytest.raises(InputReadError) as caught:
        readText(fixtures["encoding"], mode="required")
    assert caught.value.kind == "encoding"
    log = DiagnosticLog()
    assert readText(fixtures["missing"], mode="optional", default="", onDiagnostic=log) == ""


def test_read_yaml_uses_safe_load_and_reports_malformed(tmp_path: Path) -> None:
    good = tmp_path / "a.yaml"
    good.write_text("a: 1\n", encoding="utf-8")
    assert readYaml(good, mode="required", expect=dict) == {"a": 1}
    unsafe = tmp_path / "unsafe.yaml"
    unsafe.write_text("!!python/object/apply:os.system ['true']\n", encoding="utf-8")
    with pytest.raises(InputReadError) as caught:
        readYaml(unsafe, mode="required")
    assert caught.value.kind == "malformed"
    broken = tmp_path / "broken.yaml"
    broken.write_text("a: [1,\n", encoding="utf-8")
    with pytest.raises(AuthorityInputError):
        readYaml(broken, mode="authority")


def test_read_frontmatter(tmp_path: Path) -> None:
    named = tmp_path / "skill.md"
    named.write_text("---\nid: owner/skill\nlevel: 2★\n---\nBody text\n", encoding="utf-8")
    meta, body = readFrontmatter(named, mode="required")
    assert meta == {"id": "owner/skill", "level": "2★"}
    assert body == "Body text\n"
    fenceless = tmp_path / "nofence.md"
    fenceless.write_text("just text\n", encoding="utf-8")
    with pytest.raises(InputReadError) as caught:
        readFrontmatter(fenceless, mode="required")
    assert caught.value.kind == "malformed"
    scalar = tmp_path / "scalar.md"
    scalar.write_text("---\njust a string\n---\n", encoding="utf-8")
    log = DiagnosticLog()
    assert readFrontmatter(scalar, mode="bestEffort", default=({}, ""), onDiagnostic=log) == ({}, "")
    assert log.entries[0].kind == "shape"


# ------------------------------------------------- shared proof fixtures (F0-F6)


def test_shared_proof_fixtures_produce_the_documented_kinds(tmp_path: Path) -> None:
    from tests.structured_read_fixtures import EXPECTED_KIND, jsonFixtures, restorePermissions

    paths = jsonFixtures(tmp_path / "fx")
    try:
        assert readJson(paths["F0-good"], mode="required", expect=dict) == {"a": 1}
        assert readJson(paths["F6-incomplete"], mode="required", expect=dict) == {"items": [{}]}
        for name, kind in EXPECTED_KIND.items():
            if paths[name] is None:
                continue
            log = DiagnosticLog()
            assert readJson(paths[name], mode="bestEffort", default={}, onDiagnostic=log, expect=dict) == {}
            assert [entry.kind for entry in log.entries] == [kind], name
    finally:
        restorePermissions(paths)
