"""Run the browser-neutral World Tree layout contract through Node."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def test_world_tree_layout_node_contract() -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is required for the World Tree layout contract")
    subprocess.run(
        [node, "--test", str(ROOT / "tests" / "world-tree-layout.test.js")],
        cwd=ROOT,
        check=True,
    )
