from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts.steward_agent_dispatch import main

REPO = "gaia-research/gaia-skill-tree"
URL = "https://github.com/gaia-research/gaia-skill-tree/actions/runs/101"
BUILDWF = "steward-build-copilot.lock.yml"
VERIFYWF = "steward-verify-claude.lock.yml"
SUCCESS = {"status": "completed", "conclusion": "success", "url": URL}


def completed(returncode: int = 0, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def runsJson(*runs: tuple[int, str]) -> str:
    return json.dumps([{"databaseId": runId, "createdAt": created} for runId, created in runs])


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps: list[float] = []

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


class FakeGh:
    """Scripted stand-in for the gh CLI. Records every argv it is given."""

    def __init__(
        self,
        *,
        lists: list[str],
        views: list[dict] | None = None,
        dispatch: subprocess.CompletedProcess | None = None,
        outcomeText: str | None = None,
        downloadRc: int = 0,
        defaultBranch: str = "main",
    ):
        self.calls: list[list[str]] = []
        self.lists = list(lists)
        self.views = list(views or [])
        self.dispatch = dispatch or completed()
        self.outcomeText = outcomeText
        self.downloadRc = downloadRc
        self.defaultBranch = defaultBranch
        self.cancelRc = 0

    def __call__(self, argv):
        argv = list(argv)
        self.calls.append(argv)
        head = argv[:3]
        if head == ["gh", "workflow", "run"]:
            return self.dispatch
        if head == ["gh", "run", "list"]:
            text = self.lists.pop(0) if len(self.lists) > 1 else self.lists[0]
            return completed(0, text)
        if head == ["gh", "run", "view"]:
            if len(self.views) > 1:
                return completed(0, json.dumps(self.views.pop(0)))
            return completed(0, json.dumps(self.views[0]))
        if head == ["gh", "run", "cancel"]:
            return completed(self.cancelRc)
        if head == ["gh", "run", "download"]:
            target = Path(argv[argv.index("-D") + 1])
            if self.outcomeText is not None:
                target.mkdir(parents=True, exist_ok=True)
                (target / "outcome.json").write_text(self.outcomeText, encoding="utf-8")
            return completed(self.downloadRc, "", "download exploded" if self.downloadRc else "")
        if head == ["gh", "repo", "view"]:
            return completed(0, json.dumps({"defaultBranchRef": {"name": self.defaultBranch}}))
        raise AssertionError(f"unexpected gh call: {argv}")

    def callsFor(self, head: list[str]) -> list[list[str]]:
        return [call for call in self.calls if call[: len(head)] == head]


def promptFile(tmp_path: Path, text: str = "do the thing") -> Path:
    path = tmp_path / "prompt.md"
    path.write_text(text, encoding="utf-8")
    return path


def buildArgs(prompt: Path, *extra: str) -> list[str]:
    return [
        "--role", "build", "--engine", "copilot", "--prompt-path", str(prompt),
        "--dispatch-id", "d1", "--base", "dev/x", "--branch", "steward/x",
        "--ref", "main", "--timeout", "60", "--poll", "20", *extra,
    ]


def verifyArgs(prompt: Path, *extra: str) -> list[str]:
    return [
        "--role", "verify", "--engine", "claude", "--prompt-path", str(prompt),
        "--dispatch-id", "v1", "--timeout", "60", "--poll", "20", *extra,
    ]


def run(gh: FakeGh, clock: FakeClock, argv: list[str], env: dict | None = None) -> int:
    return main(
        argv,
        runner=gh,
        sleep=clock.sleep,
        clock=clock.clock,
        env=env if env is not None else {"GITHUB_REPOSITORY": REPO},
    )


def outcomeOf(capsys) -> dict:
    out = capsys.readouterr().out
    lines = out.splitlines()
    assert len(lines) == 1, out
    return json.loads(lines[0])


def test_happy_build_path(tmp_path, capsys):
    gh = FakeGh(
        lists=[runsJson((100, "2026-10-21T10:00:00Z")), runsJson((100, "2026-10-21T10:00:00Z"), (101, "2026-10-21T10:01:00Z"))],
        views=[SUCCESS],
        outcomeText=json.dumps({"verdict": "accept", "summary": "ok"}),
    )
    clock = FakeClock()
    rc = run(gh, clock, buildArgs(promptFile(tmp_path, "PROMPT")))

    assert rc == 0
    assert outcomeOf(capsys) == {
        "verdict": "accept",
        "summary": "ok",
        "engine": "copilot",
        "runId": 101,
        "runUrl": URL,
    }
    assert gh.callsFor(["gh", "workflow", "run"]) == [[
        "gh", "workflow", "run", BUILDWF, "--repo", REPO, "--ref", "main",
        "-f", "dispatch-id=d1", "-f", "prompt=PROMPT", "-f", "base=dev/x", "-f", "branch=steward/x",
    ]]
    assert gh.calls[0] == [
        "gh", "run", "list", "--workflow", BUILDWF, "--repo", REPO,
        "--event", "workflow_dispatch", "--limit", "30", "--json", "databaseId",
    ]
    download = gh.callsFor(["gh", "run", "download"])
    assert len(download) == 1
    assert download[0][:9] == ["gh", "run", "download", "101", "--repo", REPO, "-n", "steward-outcome", "-D"]


def test_happy_verify_path_has_no_base_or_branch(tmp_path, capsys, monkeypatch):
    gh = FakeGh(
        lists=[runsJson(), runsJson((55, "2026-10-21T11:00:00Z"))],
        views=[{**SUCCESS, "url": "https://example.test/runs/55"}],
        outcomeText=json.dumps({"verdict": "reject"}),
        defaultBranch="trunk",
    )
    clock = FakeClock()
    env = {"GITHUB_REPOSITORY": REPO}
    rc = run(gh, clock, verifyArgs(promptFile(tmp_path, "CHECK")), env=env)

    assert rc == 0
    out = outcomeOf(capsys)
    assert out["engine"] == "claude"
    assert out["runId"] == 55
    assert out["runUrl"] == "https://example.test/runs/55"
    assert gh.callsFor(["gh", "workflow", "run"]) == [[
        "gh", "workflow", "run", VERIFYWF, "--repo", REPO, "--ref", "trunk",
        "-f", "dispatch-id=v1", "-f", "prompt=CHECK",
    ]]
    assert gh.callsFor(["gh", "repo", "view"]) == [["gh", "repo", "view", REPO, "--json", "defaultBranchRef"]]


def test_ref_from_env_skips_repo_lookup(tmp_path, capsys):
    gh = FakeGh(
        lists=[runsJson(), runsJson((7, "2026-10-21T11:00:00Z"))],
        views=[SUCCESS],
        outcomeText="{}",
    )
    clock = FakeClock()
    env = {"GITHUB_REPOSITORY": REPO, "STEWARD_AGENT_REF": "dev/integration"}
    rc = run(gh, clock, verifyArgs(promptFile(tmp_path)), env=env)

    assert rc == 0
    assert gh.callsFor(["gh", "repo", "view"]) == []
    assert gh.callsFor(["gh", "workflow", "run"])[0][6:8] == ["--ref", "dev/integration"]


def test_prompt_too_long_is_refused_before_any_gh_call(tmp_path, capsys):
    gh = FakeGh(lists=[runsJson()])
    clock = FakeClock()
    rc = run(gh, clock, buildArgs(promptFile(tmp_path, "x" * 60001)))

    assert rc == 2
    assert gh.calls == []
    assert "60000" in capsys.readouterr().err


def test_dispatch_404_is_blocked_with_exact_stderr(tmp_path, capsys):
    stderr = "HTTP 404: workflow steward-build-copilot.lock.yml not found on the default branch"
    gh = FakeGh(lists=[runsJson()], dispatch=completed(1, "", stderr))
    clock = FakeClock()
    rc = run(gh, clock, buildArgs(promptFile(tmp_path)))

    captured = capsys.readouterr()
    assert rc == 3
    assert stderr in captured.err
    assert captured.out == ""
    assert gh.callsFor(["gh", "run", "view"]) == []
    assert gh.callsFor(["gh", "run", "download"]) == []


def test_no_new_run_times_out_without_cancel(tmp_path, capsys):
    gh = FakeGh(lists=[runsJson((100, "2026-10-21T10:00:00Z"))])
    clock = FakeClock()
    rc = run(gh, clock, buildArgs(promptFile(tmp_path)))

    assert rc == 4
    assert capsys.readouterr().out == ""
    assert gh.callsFor(["gh", "run", "cancel"]) == []
    assert clock.sleeps == [20.0, 20.0, 20.0]


def test_two_new_runs_picks_earliest(tmp_path, capsys):
    gh = FakeGh(
        lists=[
            runsJson((100, "2026-10-21T10:00:00Z")),
            runsJson((201, "2026-10-21T10:05:00Z"), (200, "2026-10-21T10:01:00Z"), (100, "2026-10-21T10:00:00Z")),
        ],
        views=[{**SUCCESS, "url": "https://example.test/runs/200"}],
        outcomeText=json.dumps({"verdict": "accept"}),
    )
    clock = FakeClock()
    rc = run(gh, clock, buildArgs(promptFile(tmp_path)))

    captured = capsys.readouterr()
    assert rc == 0
    assert "2 new runs" in captured.err
    assert "run 200" in captured.err
    assert json.loads(captured.out)["runId"] == 200
    assert gh.callsFor(["gh", "run", "view"])[0][3] == "200"


def test_run_concluded_failure_exits_one(tmp_path, capsys):
    failed = {"status": "completed", "conclusion": "failure", "url": URL}
    gh = FakeGh(lists=[runsJson(), runsJson((101, "2026-10-21T10:01:00Z"))], views=[failed])
    clock = FakeClock()
    rc = run(gh, clock, buildArgs(promptFile(tmp_path)))

    captured = capsys.readouterr()
    assert rc == 1
    assert URL in captured.err
    assert "failure" in captured.err
    assert captured.out == ""
    assert gh.callsFor(["gh", "run", "download"]) == []


def test_run_that_never_completes_is_cancelled_and_times_out(tmp_path, capsys):
    running = {"status": "in_progress", "conclusion": "", "url": URL}
    gh = FakeGh(lists=[runsJson(), runsJson((101, "2026-10-21T10:01:00Z"))], views=[running])
    clock = FakeClock()
    rc = run(gh, clock, buildArgs(promptFile(tmp_path)))

    assert rc == 4
    assert capsys.readouterr().out == ""
    assert gh.callsFor(["gh", "run", "cancel"]) == [["gh", "run", "cancel", "101", "--repo", REPO]]


@pytest.mark.parametrize(
    "outcomeText, reason",
    [
        (None, "no outcome.json"),
        ("{not json", "not valid JSON"),
        ("[1, 2]", "JSON object"),
    ],
)
def test_missing_or_invalid_outcome_exits_one(tmp_path, capsys, outcomeText, reason):
    gh = FakeGh(
        lists=[runsJson(), runsJson((101, "2026-10-21T10:01:00Z"))],
        views=[SUCCESS],
        outcomeText=outcomeText,
    )
    clock = FakeClock()
    rc = run(gh, clock, buildArgs(promptFile(tmp_path)))

    captured = capsys.readouterr()
    assert rc == 1
    assert reason in captured.err
    assert captured.out == ""


def test_download_failure_exits_one(tmp_path, capsys):
    gh = FakeGh(
        lists=[runsJson(), runsJson((101, "2026-10-21T10:01:00Z"))],
        views=[SUCCESS],
        outcomeText="{}",
        downloadRc=1,
    )
    clock = FakeClock()
    rc = run(gh, clock, buildArgs(promptFile(tmp_path)))

    assert rc == 1
    assert "download exploded" in capsys.readouterr().err


def test_outcome_cannot_overwrite_adapter_keys(tmp_path, capsys):
    hostile = {"runId": 999, "engine": "forged", "runUrl": "https://evil.test", "verdict": "reject"}
    gh = FakeGh(
        lists=[runsJson(), runsJson((101, "2026-10-21T10:01:00Z"))],
        views=[SUCCESS],
        outcomeText=json.dumps(hostile),
    )
    clock = FakeClock()
    rc = run(gh, clock, buildArgs(promptFile(tmp_path)))

    captured = capsys.readouterr()
    assert rc == 0
    out = json.loads(captured.out)
    assert out == {"verdict": "reject", "engine": "copilot", "runId": 101, "runUrl": URL}
    assert "reserved keys" in captured.err


@pytest.mark.parametrize(
    "argsBuilder",
    [
        lambda prompt: [a for a in buildArgs(prompt) if a not in ("--base", "dev/x", "--branch", "steward/x")],
        lambda prompt: [a for a in buildArgs(prompt) if a not in ("--branch", "steward/x")],
        lambda prompt: [a for a in buildArgs(prompt) if a not in ("--base", "dev/x")],
    ],
    ids=["no-base-and-branch", "no-branch", "no-base"],
)
def test_build_requires_base_and_branch(tmp_path, capsys, argsBuilder):
    gh = FakeGh(lists=[runsJson()])
    clock = FakeClock()
    rc = run(gh, clock, argsBuilder(promptFile(tmp_path)))

    assert rc == 2
    assert gh.calls == []
    assert "--base and --branch are required" in capsys.readouterr().err


def test_verify_rejects_base_and_branch(tmp_path, capsys):
    gh = FakeGh(lists=[runsJson()])
    clock = FakeClock()
    rc = run(gh, clock, verifyArgs(promptFile(tmp_path), "--base", "dev/x"))

    assert rc == 2
    assert gh.calls == []


def test_missing_repo_is_refused(tmp_path, capsys):
    gh = FakeGh(lists=[runsJson()])
    clock = FakeClock()
    rc = run(gh, clock, buildArgs(promptFile(tmp_path)), env={})

    assert rc == 2
    assert gh.calls == []
    assert "OWNER/NAME" in capsys.readouterr().err
