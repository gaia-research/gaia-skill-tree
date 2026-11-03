"""--challenge-only is the contents:write job's entry point: challenge watch and nothing else."""

from __future__ import annotations

from types import SimpleNamespace

from scripts.upstream_watcher import watcher


def test_challenge_only_runs_the_watch_and_never_polls_or_writes_issues(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(watcher, "_build_registry_map", lambda root=None: {"a/b": {}})
    monkeypatch.setattr(
        watcher,
        "runChallengeWatchStep",
        lambda args, registry_map, verbose: calls.append(args.challenge_output)
        or SimpleNamespace(packets=[1, 2], active_count=3),
    )

    def boom(*_a, **_k):
        raise AssertionError("must not poll suites or write issues")

    monkeypatch.setattr(watcher, "iter_suite_skills", boom)
    monkeypatch.setattr(watcher, "create_issues", boom)
    monkeypatch.setattr(watcher, "run_batch", boom)
    monkeypatch.setattr(watcher, "LiveGh", boom)

    assert watcher.main(["--challenge-only", "--apply", "--challenge-output", "out"]) == 0
    assert calls == ["out"]
    assert "2 verification packet(s) written" in capsys.readouterr().out


def test_challenge_only_refuses_to_combine_with_escalation(capsys):
    assert watcher.main(["--challenge-only", "--escalate", "a/b:c"]) == 1
    assert "cannot be combined" in capsys.readouterr().err
