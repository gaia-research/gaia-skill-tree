"""Guard: the Python CI gate must collect scripts/upstream_watcher/tests.

`pytest tests/` never reaches that directory, which let a challenge-admission
regression go unnoticed.
"""
import pathlib

import yaml

WORKFLOW = pathlib.Path(__file__).resolve().parents[1] / ".github" / "workflows" / "python-package.yml"
WATCHER_TESTS = "scripts/upstream_watcher/tests"


def test_python_ci_collects_upstream_watcher_tests():
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    runs = [step.get("run", "") for job in doc["jobs"].values() for step in job.get("steps", [])]
    pytestRuns = [run for run in runs if "pytest" in run and WATCHER_TESTS in run]
    assert pytestRuns, f"no pytest step in python-package.yml collects {WATCHER_TESTS}"
    assert any("tests/" in run.split() for run in pytestRuns), "the fast gate must keep collecting tests/"
