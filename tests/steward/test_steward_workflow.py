"""Hermetic checks for the paused Steward workflow's agent opt-in boundary."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
WORKFLOW = REPO / ".github/workflows/steward-full.yml"


def drive_script() -> str:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["drive"]["steps"]
    return next(step["run"] for step in steps if step.get("name") == "Drive the pipeline")


def invoke_drive(tmp_path: Path, agent: str) -> list[str]:
    """Run the workflow step with a fake python executable and no network."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True)
    capture = tmp_path / "args.txt"
    python = bin_dir / "python"
    python.write_text(
        "#!/bin/bash\nprintf '%s\\n' \"$@\" > \"$CAPTURE_ARGS\"\nexit 0\n",
        encoding="utf-8",
    )
    python.chmod(0o755)
    # The existence of claude and the normal local fallback credentials must not
    # override an empty workflow selection; this tests the actual step shell.
    claude = bin_dir / "claude"
    claude.write_text("#!/bin/sh\nexit 99\n", encoding="utf-8")
    claude.chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ.get('PATH', '')}",
        "CAPTURE_ARGS": str(capture),
        "STEWARD_AGENT": agent,
        "STEWARD_SONNET_MODEL_ID": "sonnet-test-id",
        "ANTHROPIC_API_KEY": "test-only",
        "INTEGRATION_BRANCH": "dev/steward-test",
    }
    result = subprocess.run(
        ["bash", "-c", drive_script()], cwd=REPO, env=env,
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    return capture.read_text(encoding="utf-8").splitlines()


def test_empty_or_whitespace_agent_selection_forces_no_agents_and_keeps_driver(tmp_path):
    for selection in ("", "   \t\n"):
        args = invoke_drive(tmp_path / ("empty" if not selection else "whitespace"), selection)
        assert "scripts/steward_drive.py" in args
        assert "--no-agents" in args
        assert "--integration-branch" in args


def test_explicit_agent_selection_does_not_force_no_agents(tmp_path):
    args = invoke_drive(tmp_path / "selected", "claude")
    assert "scripts/steward_drive.py" in args
    assert "--no-agents" not in args


def test_workflow_stays_founder_paused():
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    # PyYAML's YAML 1.1 parser maps the GitHub Actions `on` key to True.
    assert "workflow_dispatch" in workflow[True]
    assert workflow["jobs"]["drive"]["if"] == "${{ false }}"
    assert workflow["jobs"]["drive"]["env"]["STEWARD_AGENT"] == "${{ inputs.agent || vars.STEWARD_AGENT || '' }}"
