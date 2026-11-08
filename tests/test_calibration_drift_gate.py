"""Tests for scripts/check_calibration_drift.py, the calibration drift prevention gate (#2283)."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts import check_calibration_drift as gate

REPO_ROOT = Path(__file__).resolve().parents[1]

# Two real, small, aligned 2★ (grade C) records and their generic parents.
FIXTURE_FILES = (
    "registry/nodes/basic/retrieve.json",
    "registry/named/arcmira/find-quotes.md",
    "registry/nodes/fusion/causal-inference.json",
    "registry/named/aj-geddes/causal-inference.md",
)
QUOTES = "registry/named/arcmira/find-quotes.md"
CAUSAL = "registry/named/aj-geddes/causal-inference.md"


# --- pure comparison ----------------------------------------------------------------


def _state(target: str, *, frozen: bool = False) -> dict:
    return {"targetLevel": target, "frozen": frozen, "trustGrade": "C", "trustMagnitude": 30.0,
            "direction": "ceiling-exceeded"}


def test_evaluate_ratchets_only_new_drift() -> None:
    base = {
        ("a/old", "3★", "2★"): _state("2★"),        # tolerated: unchanged at head
        ("a/fixed", "4★", "3★"): _state("3★"),      # resolved: recalibrated by the PR
        ("a/moved", "2★", "3★"): _state("3★"),      # the PR changed its target: new
    }
    head = {
        ("a/old", "3★", "2★"): _state("2★"),
        ("a/moved", "2★", "4★"): _state("4★"),
        ("a/new", "1★", "2★"): _state("2★"),        # F1 below-ceiling promotion: new
        ("a/frozen", "5★", "2★"): _state("2★", frozen=True),
    }
    new, tolerated, resolved, frozen = gate.evaluate(base, head)
    assert [key[0] for key, _ in new] == ["a/moved", "a/new"]
    assert (tolerated, resolved, frozen) == (1, 2, 1)


# --- synthetic base/head pair through the real sensor ----------------------------------


def _set_level(root: Path, rel: str, level: str, *, frozen: bool = False) -> None:
    path = root / rel
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"^level: .*$", f"level: {level}", text, count=1, flags=re.MULTILINE)
    if frozen:
        text = text.replace("\nstatus: named\n", "\nstatus: named\nfrozen: true\n", 1)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def pair(tmp_path, monkeypatch):
    for name in ("GITHUB_BASE_REF", "GITHUB_EVENT_NAME", "GITHUB_EVENT_PATH"):
        monkeypatch.delenv(name, raising=False)
    root = tmp_path / "repo"
    for rel in FIXTURE_FILES:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO_ROOT / rel, root / rel)
    monkeypatch.setattr(gate, "REPO_ROOT", root)

    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()

    git("init", "-q", "-b", "main")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "T")
    git("config", "commit.gpgsign", "false")
    _set_level(root, CAUSAL, "3★")  # drift that already exists at the base
    git("add", ".")
    git("commit", "-qm", "base")
    git("update-ref", "refs/remotes/origin/main", git("rev-parse", "HEAD"))

    def head(message: str) -> None:
        git("commit", "-qam", message)

    return root, head


def _run(capsys, *args: str) -> tuple[int, str, str]:
    code = gate.main(["--base", "origin/main", *args])
    out = capsys.readouterr()
    return code, out.out, out.err


def test_unchanged_head_tolerates_base_drift(pair, capsys) -> None:
    code, out, _ = _run(capsys)
    assert code == 0
    assert "New drift:            0" in out and "Tolerated (at base):  1" in out


@pytest.mark.parametrize("level, direction", [("3★", "ceiling-exceeded"), ("1★", "promotion-candidate")])
def test_new_drift_fails_with_the_calibrate_command(pair, capsys, level, direction) -> None:
    root, head = pair
    _set_level(root, QUOTES, level)
    head("stored level moved without recalibration")
    code, out, err = _run(capsys)
    assert code == 1
    assert "New drift:            1" in out and "Tolerated (at base):  1" in out
    assert f"stored {level}" in err and direction in err
    assert "Run in this PR: gaia dev calibrate arcmira/find-quotes 2★" in err


def test_recalibrating_base_drift_shrinks_the_set(pair, capsys) -> None:
    root, head = pair
    _set_level(root, CAUSAL, "2★")
    head("recalibrate")
    code, out, _ = _run(capsys)
    assert code == 0
    assert "Resolved since base:  1" in out and "Tolerated (at base):  0" in out


def test_frozen_skill_is_skipped(pair, capsys) -> None:
    root, head = pair
    _set_level(root, QUOTES, "3★", frozen=True)
    head("frozen record")
    code, out, _ = _run(capsys)
    assert code == 0
    assert "Frozen (skipped):     1" in out


def test_gate_never_writes_the_repository(pair, capsys) -> None:
    root, head = pair
    _set_level(root, QUOTES, "3★")
    head("drift")
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file() and ".git" not in p.parts}
    assert _run(capsys)[0] == 1
    after = {p: p.read_bytes() for p in root.rglob("*") if p.is_file() and ".git" not in p.parts}
    assert before == after
    worktrees = subprocess.run(["git", "worktree", "list"], cwd=root, capture_output=True, text=True, check=True).stdout
    assert len(worktrees.strip().splitlines()) == 1  # the temporary base checkout is gone


@pytest.mark.parametrize("context", ["unresolvable", "no-context", "push-without-payload"])
def test_unresolvable_base_fails_closed(pair, capsys, monkeypatch, context) -> None:
    if context == "unresolvable":
        args = ["--base", "origin/no-such-branch"]
    else:
        args = []
        if context == "push-without-payload":
            monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
    assert gate.main(args) == 2
    assert "fail closed" in capsys.readouterr().err


def test_pull_request_base_comes_from_github_base_ref(pair, capsys, monkeypatch) -> None:
    root, head = pair
    _set_level(root, QUOTES, "3★")
    head("drift")
    monkeypatch.setenv("GITHUB_BASE_REF", "main")
    assert gate.main([]) == 1
    assert "GITHUB_BASE_REF (origin/main)" in capsys.readouterr().out


def test_unscorable_head_record_fails_closed(pair, capsys) -> None:
    root, head = pair
    (root / QUOTES).write_text((root / QUOTES).read_text(encoding="utf-8").replace("---", "", 1), encoding="utf-8")
    head("broken fence")
    code, _, err = _run(capsys)
    assert code == 2
    assert "UNEVALUATED" in err or "fail closed" in err


def test_unexpected_error_is_exit_2_never_a_verdict(pair, capsys, monkeypatch) -> None:
    def boom(root):
        raise KeyError("unexpected")

    monkeypatch.setattr(gate, "scan_drift", boom)
    assert _run(capsys)[0] == 2


def test_fast_yaml_is_restored(pair) -> None:
    import yaml

    original = yaml.safe_load
    with gate.fast_yaml(True):
        assert yaml.safe_load("a: 1") == {"a": 1}
    assert yaml.safe_load is original
