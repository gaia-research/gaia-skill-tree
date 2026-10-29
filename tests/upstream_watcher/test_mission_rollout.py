"""Staging is not rollout: main's scheduled/default and event jobs stay active."""
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from tests.upstream_watcher.test_watcher_workflows import _run_block_with

ROOT = Path(__file__).resolve().parents[2]


def load(name):
    return yaml.safe_load((ROOT / f".github/workflows/upstream-{name}.yml").read_text())


@pytest.mark.parametrize("name,digest", [
    ("approve", "ea9fa2a719ccbf654b1f1ff57b97c16fe0b508b8cd9175264756139b2261456c"),
    ("reject", "18e30d1c75318486bddd8e9b08c58c7748f54697e773c1c43ab323fabdf77c8c"),
    ("close-children", "5d97163a06c49888c1e4752291e25f1fe5216909a0891ca716876daf4834b7d7"),
])
def test_deployed_main_job_steps_retained_verbatim_until_opt_in(name, digest):
    jobs = load(name)["jobs"]
    legacy = jobs[f"legacy-{name}"]
    assert "vars.STEWARD_ISSUE_HYGIENE_V2 != 'true'" in legacy["if"]
    assert hashlib.sha256(json.dumps(legacy["steps"], sort_keys=True).encode()).hexdigest() == digest
    for key, job in jobs.items():
        if not key.startswith("legacy-"):
            assert "vars.STEWARD_ISSUE_HYGIENE_V2 == 'true'" in job["if"]
    if name in ("reject", "close-children"):
        assert jobs[name]["permissions"] == {"issues": "write", "actions": "write", "contents": "read"}
    if name == "close-children":
        assert legacy["permissions"] == {"issues": "write"}


def test_schedule_and_manual_default_stay_fanout_even_if_batch_input_present(tmp_path):
    result, calls = _run_block_with(tmp_path, "schedule", {"INPUT_CHILD_MODE": "batch"})
    assert result.returncode == 0 and "--child-mode fanout" in calls[0]
    doc = load("watcher")
    triggers = doc.get("on", doc.get(True))
    assert triggers["schedule"] == [{"cron": "0 6 * * *"}]
    assert triggers["workflow_dispatch"]["inputs"]["child_mode"]["default"] == "fanout"
    assert doc["concurrency"] == "upstream-watcher"


def test_batch_apply_requires_explicit_opt_in_but_dry_run_is_available(tmp_path):
    result, calls = _run_block_with(tmp_path, "workflow_dispatch", {
        "INPUT_CHILD_MODE": "batch", "INPUT_APPLY": "true", "V2_ENABLED": ""})
    assert result.returncode == 1 and calls == []


def test_opted_in_manual_batch_keeps_no_implicit_closure(tmp_path):
    result, calls = _run_block_with(tmp_path, "workflow_dispatch", {
        "INPUT_CHILD_MODE": "batch", "INPUT_APPLY": "true", "V2_ENABLED": "true"})
    assert result.returncode == 0 and "--child-mode batch" in calls[0]
    assert "closure" not in calls[0]


def test_default_cli_invocation_is_legacy_not_batch(monkeypatch):
    from scripts.upstream_watcher import watcher
    monkeypatch.setattr(watcher, "_build_registry_map", lambda: {})
    monkeypatch.setattr(watcher, "iter_suite_skills", lambda: [])
    monkeypatch.setattr(watcher, "create_issues", lambda *a, **k: [])
    monkeypatch.setattr(watcher, "run_batch", lambda *a, **k: pytest.fail("implicit batch activation"))
    assert watcher.main(["--apply"]) == 0
