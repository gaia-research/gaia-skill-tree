"""Regression coverage for the Trust Magnitude inspection report."""

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_inspector_does_not_treat_tm_floor_as_s_grade_without_gate():
    """Yggdrasil III: TM >= 250 can remain A until independently witnessed."""
    result = subprocess.run(
        [sys.executable, "scripts/inspectTrustMagnitude.py", "--skill", "garrytan/gstack"],
        cwd=ROOT,
        env={**os.environ, "GAIA_OPERATOR_OVERRIDE": "1"},
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "Trust Grade:    A" in result.stdout
    assert "Next grade: S" in result.stdout
    assert "TM floor met; S still requires" in result.stdout
    assert "Already at top grade" not in result.stdout
