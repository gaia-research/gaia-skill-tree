"""Tests for scripts/check_ruff.py multi-tier lint gate."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from scripts.check_ruff import (
    classify_code,
    evaluate_violations,
    find_stale_entries,
    get_changed_files,
    main as check_ruff_main,
    normalize_message,
)


def test_classify_code_tiers():
    """Verify classification of rules into blocking, ratchet, and advisory tiers."""
    # Blocking rules
    assert classify_code("F821") == "blocking"
    assert classify_code("F811") == "blocking"
    assert classify_code("F631") == "blocking"
    assert classify_code("F632") == "blocking"
    assert classify_code("F701") == "blocking"
    assert classify_code("F702") == "blocking"

    # Ratchet rules
    assert classify_code("F401") == "ratchet"
    assert classify_code("S110") == "ratchet"
    assert classify_code("S112") == "ratchet"
    assert classify_code("E722") == "ratchet"

    # Advisory rules
    assert classify_code("BLE001") == "advisory"

    # Other rules
    assert classify_code("E501") == "other"
    assert classify_code("W291") == "other"


def test_introduced_f821_fails_gate():
    """Verify that an introduced F821 (undefined name) fails the gate immediately."""
    violations = [
        {
            "code": "F821",
            "filename": "src/gaia_cli/sample.py",
            "location": {"row": 42, "column": 5},
            "message": "Undefined name `foo`",
        }
    ]
    baseline_data = {"version": 1, "violations": []}

    blocking, ratchet, advisory, _ = evaluate_violations(
        violations=violations,
        baseline_data=baseline_data,
        changed_files=None,
    )

    assert len(blocking) == 1
    assert blocking[0]["code"] == "F821"
    assert blocking[0]["file"] == "src/gaia_cli/sample.py"
    assert len(ratchet) == 0
    assert len(advisory) == 0


def test_introduced_new_f401_in_changed_file_fails_ratchet():
    """Verify that an introduced new F401 (unused import) in a changed file fails the ratchet."""
    violations = [
        {
            "code": "F401",
            "filename": "src/gaia_cli/modified.py",
            "location": {"row": 10, "column": 1},
            "message": "`os` imported but unused",
        }
    ]
    # Baseline has no entry for this file
    baseline_data = {"version": 1, "violations": []}
    changed_files = {"src/gaia_cli/modified.py"}

    blocking, ratchet, advisory, pre_existing = evaluate_violations(
        violations=violations,
        baseline_data=baseline_data,
        changed_files=changed_files,
    )

    assert len(blocking) == 0
    assert len(ratchet) == 1
    assert ratchet[0]["code"] == "F401"
    assert ratchet[0]["file"] == "src/gaia_cli/modified.py"
    assert pre_existing == 0


def test_untouched_preexisting_f401_does_not_fail():
    """Verify that untouched pre-existing F401 violations pass without failing."""
    violations = [
        {
            "code": "F401",
            "filename": "src/gaia_cli/untouched.py",
            "location": {"row": 5, "column": 1},
            "message": "`sys` imported but unused",
        }
    ]
    baseline_data = {
        "version": 1,
        "violations": [
            {
                "file": "src/gaia_cli/untouched.py",
                "code": "F401",
                "line": 5,
                "column": 1,
                "message": "`sys` imported but unused",
            }
        ],
    }
    # File is not in changed_files (untouched)
    changed_files = {"src/gaia_cli/other_file.py"}

    blocking, ratchet, advisory, pre_existing = evaluate_violations(
        violations=violations,
        baseline_data=baseline_data,
        changed_files=changed_files,
    )

    assert len(blocking) == 0
    assert len(ratchet) == 0
    assert len(advisory) == 0
    assert pre_existing == 1


def test_changed_file_with_preexisting_f401_in_baseline_does_not_fail():
    """Verify that a changed file containing a pre-existing baseline F401 does not fail ratchet."""
    violations = [
        {
            "code": "F401",
            "filename": "src/gaia_cli/touched.py",
            "location": {"row": 5, "column": 1},
            "message": "`sys` imported but unused",
        }
    ]
    baseline_data = {
        "version": 1,
        "violations": [
            {
                "file": "src/gaia_cli/touched.py",
                "code": "F401",
                "line": 5,
                "column": 1,
                "message": "`sys` imported but unused",
            }
        ],
    }
    # File IS in changed_files, but the violation was already recorded in baseline
    changed_files = {"src/gaia_cli/touched.py"}

    blocking, ratchet, advisory, pre_existing = evaluate_violations(
        violations=violations,
        baseline_data=baseline_data,
        changed_files=changed_files,
    )

    assert len(blocking) == 0
    assert len(ratchet) == 0
    assert pre_existing == 1


def test_advisory_ble001_warns_but_does_not_fail():
    """Verify that advisory BLE001 (blind exception) is categorized as advisory and does not fail."""
    violations = [
        {
            "code": "BLE001",
            "filename": "src/gaia_cli/handler.py",
            "location": {"row": 88, "column": 12},
            "message": "Do not catch blind exception: `Exception`",
        }
    ]
    baseline_data = {"version": 1, "violations": []}

    blocking, ratchet, advisory, _ = evaluate_violations(
        violations=violations,
        baseline_data=baseline_data,
        changed_files=None,
    )

    assert len(blocking) == 0
    assert len(ratchet) == 0
    assert len(advisory) == 1
    assert advisory[0]["code"] == "BLE001"
    assert advisory[0]["file"] == "src/gaia_cli/handler.py"


def test_cli_execution_with_temp_files(tmp_path: Path, capsys: pytest.CaptureFixture):
    """Integration test: exercise check_ruff CLI with temp baseline and files."""
    test_file = tmp_path / "sample.py"
    test_file.write_text("import sys\n\nx = 1\n", encoding="utf-8")
    baseline_path = tmp_path / "baseline.json"

    # Step 1: Generate baseline on sample.py
    code = check_ruff_main([
        "--update-baseline",
        "--baseline",
        str(baseline_path),
        str(test_file),
    ])
    assert code == 0
    assert baseline_path.is_file()
    baseline_content = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert baseline_content["total_ratchet_violations"] == 1
    assert baseline_content["counts_by_code"]["F401"] == 1

    # Step 2: Check again with baseline - should pass (ratchet allowed)
    code = check_ruff_main([
        "--baseline",
        str(baseline_path),
        str(test_file),
    ])
    assert code == 0

    # Step 3: Introduce F821 - should fail (blocking)
    test_file.write_text("import sys\n\nprint(undefined_variable)\n", encoding="utf-8")
    code = check_ruff_main([
        "--baseline",
        str(baseline_path),
        str(test_file),
    ])
    assert code == 1
    captured = capsys.readouterr()
    assert "F821" in captured.out or "F821" in captured.err
    assert "Blocking violations:  1" in captured.out


def test_exact_match_reserved_before_fallback():
    violations = [
        {"filename": "sample.py", "code": "F401", "message": "new"},
        {"filename": "sample.py", "code": "F401", "message": "existing"},
    ]
    baseline = {"violations": [{"file": "sample.py", "code": "F401", "message": "existing"}]}
    _, failures, _, count = evaluate_violations(violations, baseline, {"sample.py"})
    assert count == 1
    assert [v["message"] for v in failures] == ["new"]


def test_missing_baseline_fails_closed(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("scripts.check_ruff.run_ruff", lambda **kwargs: [])
    baseline = tmp_path / "missing.json"
    assert check_ruff_main(["--baseline", str(baseline)]) == 2
    assert not baseline.exists()
    assert "Error loading baseline" in capsys.readouterr().err


@pytest.fixture
def git_repo(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_EVENT_NAME", raising=False)
    monkeypatch.delenv("GITHUB_BASE_REF", raising=False)
    monkeypatch.setattr("scripts.check_ruff.REPO_ROOT", tmp_path)

    def git(*args):
        return subprocess.run(
            ["git", *args], cwd=tmp_path, check=True, capture_output=True, text=True
        ).stdout.strip()

    git("init")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "Test")
    (tmp_path / "baseline.json").write_text(json.dumps({"version": 1, "violations": []}))
    (tmp_path / "clean.py").write_text("value = 1\n")
    git("add", ".")
    git("commit", "-m", "baseline")
    return git


def test_git_discovers_untracked_nested_file_and_fails(tmp_path, git_repo, capsys):
    new_dir = tmp_path / "new_directory"
    new_dir.mkdir()
    (new_dir / "unused.py").write_text("import os\n")
    assert "new_directory/unused.py" in get_changed_files(tmp_path, base_ref="HEAD")
    assert check_ruff_main(["--baseline", str(tmp_path / "baseline.json"), "--base", "HEAD"]) == 1
    assert "F401" in capsys.readouterr().err


@pytest.mark.parametrize("new_branch", [False, True])
def test_git_push_payload_discovers_committed_files(tmp_path, git_repo, monkeypatch, new_branch):
    before = git_repo("rev-parse", "HEAD")
    (tmp_path / "first.py").write_text("import os\n")
    git_repo("add", "first.py")
    git_repo("commit", "-m", "first")
    (tmp_path / "second.py").write_text("value = 2\n")
    git_repo("add", "second.py")
    git_repo("commit", "-m", "second")
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"before": "0" * 40 if new_branch else before}))
    monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event))
    assert {"first.py", "second.py"} <= get_changed_files(tmp_path)
    assert check_ruff_main(["--baseline", str(tmp_path / "baseline.json")]) == 1


def test_advisory_cli_warning_exit_zero(tmp_path, monkeypatch, capsys):
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps({"version": 1, "violations": []}))
    monkeypatch.setattr("scripts.check_ruff.get_changed_files", lambda *args, **kwargs: set())
    monkeypatch.setattr("scripts.check_ruff.run_ruff", lambda **kwargs: [
        {"filename": "sample.py", "code": "BLE001", "message": "blind exception"}
    ])
    assert check_ruff_main(["--baseline", str(baseline)]) == 0
    assert "[ADVISORY]" in capsys.readouterr().out


def test_normalize_message():
    """Verify that normalize_message collapses whitespace and handles None/empty."""
    assert normalize_message("   hello   world   \n ") == "hello world"
    assert normalize_message("") == ""
    assert normalize_message(None) == ""


def test_find_stale_entries_direct():
    """Verify find_stale_entries correctly flags unobserved baseline entries in changed files."""
    baseline_data = {
        "version": 1,
        "violations": [
            {"file": "a.py", "code": "F401", "message": "import os"},
            {"file": "b.py", "code": "F401", "message": "import sys"},
        ],
    }
    stale = find_stale_entries(
        violations=[],
        baseline_data=baseline_data,
        changed_files={"a.py"},
        repo_root=Path.cwd(),
    )
    assert len(stale) == 1
    assert stale[0]["file"] == "a.py"


def test_fake_ruff_exit_1_empty_stdout_fails_closed(monkeypatch, capsys, tmp_path):
    """Verify that ruff exiting 1 with empty stdout fails closed with exit code 2."""
    fake_ruff = tmp_path / "fake_ruff_empty.sh"
    fake_ruff.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    fake_ruff.chmod(0o755)

    with pytest.raises(SystemExit) as exc_info:
        check_ruff_main(["--ruff-bin", str(fake_ruff), "--base", "HEAD"])
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "Error: ruff exited 1 with empty output" in captured.err


def test_fake_ruff_exit_1_empty_json_list_fails_closed(capsys, tmp_path):
    """Verify that ruff exiting 1 with empty JSON list [] fails closed with exit code 2."""
    fake_ruff = tmp_path / "fake_ruff_empty_list.sh"
    fake_ruff.write_text('#!/bin/sh\nprintf "[]\\n"\nexit 1\n', encoding="utf-8")
    fake_ruff.chmod(0o755)

    with pytest.raises(SystemExit) as exc_info:
        check_ruff_main(["--ruff-bin", str(fake_ruff), "--base", "HEAD"])
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "Error: ruff exited 1 with empty JSON list" in captured.err


@pytest.mark.parametrize("exit_code", [127, 2])
def test_fake_ruff_unexpected_exit_code_fails_closed(capsys, tmp_path, exit_code):
    """Verify that unexpected ruff exit codes fail closed with that exit code."""
    fake_ruff = tmp_path / f"fake_ruff_{exit_code}.sh"
    fake_ruff.write_text(f'#!/bin/sh\nprintf "error\\n" >&2\nexit {exit_code}\n', encoding="utf-8")
    fake_ruff.chmod(0o755)

    with pytest.raises(SystemExit) as exc_info:
        check_ruff_main(["--ruff-bin", str(fake_ruff), "--base", "HEAD"])
    assert exc_info.value.code == exit_code
    captured = capsys.readouterr()
    assert f"Error executing ruff (exit code {exit_code})" in captured.err


@pytest.mark.parametrize("bad_output", ["{}", "bad"])
def test_fake_ruff_non_list_json_fails_closed(capsys, tmp_path, bad_output):
    """Verify that non-list JSON or unparseable JSON output from ruff fails closed with code 2."""
    fake_ruff = tmp_path / "fake_ruff_bad.sh"
    # Escaping for printf
    safe_output = bad_output.replace('"', '\\"')
    fake_ruff.write_text(f'#!/bin/sh\nprintf "{safe_output}\\n"\nexit 1\n', encoding="utf-8")
    fake_ruff.chmod(0o755)

    with pytest.raises(SystemExit) as exc_info:
        check_ruff_main(["--ruff-bin", str(fake_ruff), "--base", "HEAD"])
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    if bad_output == "{}":
        assert "Error: ruff JSON output must be a list, got dict" in captured.err
    else:
        assert "Failed to parse ruff JSON output" in captured.err


def test_fake_ruff_invalid_record_in_list_fails_closed(capsys, tmp_path):
    """Verify that a list with invalid violation records fails closed with code 2."""
    fake_ruff = tmp_path / "fake_ruff_invalid_record.sh"
    fake_ruff.write_text('#!/bin/sh\nprintf "[{}]\\n"\nexit 1\n', encoding="utf-8")
    fake_ruff.chmod(0o755)

    with pytest.raises(SystemExit) as exc_info:
        check_ruff_main(["--ruff-bin", str(fake_ruff), "--base", "HEAD"])
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "Error: ruff record missing valid string 'code'" in captured.err


@pytest.mark.parametrize("bad_record, expected_err", [
    ('{"code": 123, "filename": "a.py", "message": "msg"}', "missing valid string 'code'"),
    ('{"code": "F401", "filename": 123, "message": "msg"}', "missing valid string filename/file"),
    ('{"code": "F401", "filename": "a.py", "message": 123}', "missing valid string 'message'"),
    ('{"code": "F401", "filename": "a.py", "message": null}', "missing valid string 'message'"),
    ('{"code": "F401", "filename": "a.py", "message": ""}', "missing valid string 'message'"),
    ('{"code": "F401", "filename": "a.py", "message": "msg", "location": "bad"}', "record 'location' must be a dict"),
    ('{"code": "F401", "filename": "a.py", "message": "msg", "location": {"row": "bad"}}', "location 'row' must be an int"),
])
def test_fake_ruff_malformed_record_types_fail_closed(capsys, tmp_path, bad_record, expected_err):
    """Verify that records with invalid field types fail closed with code 2."""
    fake_ruff = tmp_path / "fake_ruff_bad_type.sh"
    safe_record = bad_record.replace('"', '\\"')
    fake_ruff.write_text(f'#!/bin/sh\nprintf "[{safe_record}]\\n"\nexit 1\n', encoding="utf-8")
    fake_ruff.chmod(0o755)

    with pytest.raises(SystemExit) as exc_info:
        check_ruff_main(["--ruff-bin", str(fake_ruff), "--base", "HEAD"])
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert expected_err in captured.err


def test_update_baseline_scoped_paths_preserves_unscoped_entries(tmp_path: Path, monkeypatch):
    """Verify that --update-baseline on scoped path updates that path while preserving unscoped entries."""
    monkeypatch.setattr("scripts.check_ruff.REPO_ROOT", tmp_path)
    baseline_path = tmp_path / "baseline.json"
    file_a = tmp_path / "a.py"
    file_b = tmp_path / "b.py"
    file_a.write_text("import os\n", encoding="utf-8")
    file_b.write_text("import sys\n", encoding="utf-8")

    initial_baseline = {
        "version": 1,
        "violations": [
            {
                "file": "b.py",
                "code": "F401",
                "line": 1,
                "column": 1,
                "message": "`sys` imported but unused",
            },
        ],
    }
    baseline_path.write_text(json.dumps(initial_baseline), encoding="utf-8")

    code = check_ruff_main([
        "--update-baseline",
        "--baseline",
        str(baseline_path),
        str(file_a),
    ])
    assert code == 0
    updated = json.loads(baseline_path.read_text(encoding="utf-8"))
    files_in_baseline = {v["file"] for v in updated["violations"]}
    assert "a.py" in files_in_baseline
    assert "b.py" in files_in_baseline


def test_update_baseline_scoped_corrupt_baseline_fails_closed(tmp_path: Path, monkeypatch):
    """Verify that --update-baseline with scoped paths fails closed if existing baseline is corrupt."""
    monkeypatch.setattr("scripts.check_ruff.REPO_ROOT", tmp_path)
    baseline_path = tmp_path / "baseline.json"
    file_a = tmp_path / "a.py"
    file_a.write_text("import os\n", encoding="utf-8")
    corrupt_content = "{corrupt json"
    baseline_path.write_text(corrupt_content, encoding="utf-8")

    code = check_ruff_main([
        "--update-baseline",
        "--baseline",
        str(baseline_path),
        str(file_a),
    ])
    assert code == 2
    assert baseline_path.read_text(encoding="utf-8") == corrupt_content


def test_prune_baseline_relative_path_different_cwd(tmp_path: Path, monkeypatch, capsys: pytest.CaptureFixture):
    """Verify that relative paths resolve against repo_root even when cwd is different."""
    repo = tmp_path / "repo"
    other_cwd = tmp_path / "other"
    repo.mkdir()
    other_cwd.mkdir()
    monkeypatch.setattr("scripts.check_ruff.REPO_ROOT", repo)

    baseline_path = repo / "baseline.json"
    file_a = repo / "sub" / "a.py"
    file_a.parent.mkdir()
    file_a.write_text("x = 1\n", encoding="utf-8")

    initial_baseline = {
        "version": 1,
        "violations": [
            {
                "file": "sub/a.py",
                "code": "F401",
                "line": 1,
                "column": 1,
                "message": "`os` imported but unused",
            },
        ],
    }
    baseline_path.write_text(json.dumps(initial_baseline), encoding="utf-8")

    monkeypatch.chdir(other_cwd)
    code = check_ruff_main([
        "--prune-baseline",
        "--baseline",
        str(baseline_path),
        "sub/a.py",
    ])
    assert code == 0
    updated = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert len(updated["violations"]) == 0


def test_evaluate_violations_monotonic_ratchet_blocks_substitution():
    """Verify monotonic ratchet blocks substitution of new violation for resolved violation in same file."""
    base = {'violations': [{'file': 'a.py', 'code': 'F401', 'message': 'old import'}]}
    new = [{'filename': str(Path('a.py').resolve()), 'code': 'F401', 'message': 'different new import', 'location': {'row': 1, 'column': 1}}]
    assert len(evaluate_violations(new, base, {'a.py'}, Path.cwd())[1]) == 1


def test_prune_baseline(tmp_path: Path, monkeypatch, capsys: pytest.CaptureFixture):
    """Verify that --prune-baseline removes stale entries and updates the baseline file."""
    monkeypatch.setattr("scripts.check_ruff.REPO_ROOT", tmp_path)
    baseline_path = tmp_path / "baseline.json"
    file_a = tmp_path / "a.py"
    file_b = tmp_path / "b.py"
    file_a.write_text("import os\n", encoding="utf-8")
    file_b.write_text("x = 1\n", encoding="utf-8")

    initial_baseline = {
        "version": 1,
        "violations": [
            {
                "file": "a.py",
                "code": "F401",
                "line": 1,
                "column": 1,
                "message": "`os` imported but unused",
            },
            {
                "file": "b.py",
                "code": "F401",
                "line": 1,
                "column": 1,
                "message": "`sys` imported but unused",
            },
        ],
    }
    baseline_path.write_text(json.dumps(initial_baseline), encoding="utf-8")

    code = check_ruff_main([
        "--prune-baseline",
        "--baseline",
        str(baseline_path),
        str(file_a),
        str(file_b),
    ])
    assert code == 0
    captured = capsys.readouterr()
    assert "Pruned 1 stale entry; 1 entries remain." in captured.out

    updated_data = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert updated_data["total_ratchet_violations"] == 1
    assert len(updated_data["violations"]) == 1
    assert updated_data["violations"][0]["file"] == "a.py"


@pytest.mark.parametrize("stale_mode,expected_exit", [
    ("warn", 0),
    ("fail", 1),
    ("ignore", 0),
])
def test_stale_flag_behavior(tmp_path: Path, monkeypatch, capsys: pytest.CaptureFixture, stale_mode, expected_exit):
    """Verify --stale flag warn, fail, and ignore handling for stale baseline entries in changed files."""
    monkeypatch.setattr("scripts.check_ruff.REPO_ROOT", tmp_path)
    baseline_path = tmp_path / "baseline.json"
    file_a = tmp_path / "a.py"
    file_a.write_text("x = 1\n", encoding="utf-8")

    baseline_data = {
        "version": 1,
        "violations": [
            {
                "file": "a.py",
                "code": "F401",
                "line": 1,
                "column": 1,
                "message": "`os` imported but unused",
            }
        ],
    }
    baseline_path.write_text(json.dumps(baseline_data), encoding="utf-8")

    monkeypatch.setattr("scripts.check_ruff.get_changed_files", lambda *args, **kwargs: {"a.py"})
    monkeypatch.setattr("scripts.check_ruff.run_ruff", lambda **kwargs: [])

    code = check_ruff_main([
        "--baseline",
        str(baseline_path),
        "--stale",
        stale_mode,
        str(file_a),
    ])
    assert code == expected_exit
    captured = capsys.readouterr()
    if stale_mode == "ignore":
        assert "[STALE]" not in captured.out and "[STALE]" not in captured.err
    else:
        assert "[STALE]" in captured.out or "[STALE]" in captured.err
