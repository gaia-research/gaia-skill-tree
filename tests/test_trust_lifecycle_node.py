"""Run the trust-lifecycle Node suites under pytest so CI executes them.

CI runs `pytest tests/`; nothing else invokes `node --test` for these files.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("suite", ["test_trust_lifecycle.js", "test_trust_lifecycle_unavailable.js"])
def test_trust_lifecycle_node_suite(suite: str) -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is required for the trust-lifecycle browser-module suites")
    result = subprocess.run(
        [node, "--test", str(ROOT / "tests" / suite)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-2000:]
