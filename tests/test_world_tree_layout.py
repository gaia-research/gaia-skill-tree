"""Run the browser-neutral World Tree layout contract through Node."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
LAYOUT = ROOT / "docs" / "js" / "world-tree-layout.js"


def test_world_tree_layout_node_contract() -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is required for the World Tree layout contract")
    subprocess.run(
        [node, "--test", str(ROOT / "tests" / "world-tree-layout.test.js")],
        cwd=ROOT,
        check=True,
    )


def _runlayout(script: str) -> dict:
    """Evaluate `script` against the layout module and return its JSON result."""
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is required for the World Tree layout contract")
    program = (
        "const L = require(%s);\n"
        "const out = (function(){ %s })();\n"
        "process.stdout.write(JSON.stringify(out));\n"
    ) % (json.dumps(str(LAYOUT)), script)
    proc = subprocess.run(
        [node, "-e", program],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(proc.stdout)


def test_resolver_semantic_contract_both_metas() -> None:
    """resolveSemantics returns the frozen §3 contract under Ygg I and Ygg II."""
    result = _runlayout(
        """
        const yggOne = [
          { type: 'basic' }, { type: 'extra' }, { type: 'ultimate' }, { type: 'unique' },
        ];
        const yggTwo = [
          { type: 'basic' }, { type: 'fusion' },
          { type: 'fusion', suiteComponents: ['x'] }, { type: 'basic' },
        ];
        const metaOne = L.detectMetaIsYggI(yggOne);
        const metaTwo = L.detectMetaIsYggI(yggTwo);
        return {
          metaOne, metaTwo,
          i_basic: L.resolveSemantics({ type: 'basic', cluster: 'a' }, 2, metaOne),
          i_extra: L.resolveSemantics({ type: 'extra', cluster: 'a' }, 4, metaOne),
          i_ult: L.resolveSemantics({ type: 'ultimate', cluster: 'a' }, 6, metaOne),
          i_uniq: L.resolveSemantics({ type: 'unique', cluster: 'b' }, 3, metaOne),
          ii_basic: L.resolveSemantics({ type: 'basic', cluster: 'a' }, 2, metaTwo),
          ii_fusion: L.resolveSemantics({ type: 'fusion', cluster: 'a' }, 4, metaTwo),
          ii_suite: L.resolveSemantics({ type: 'fusion', cluster: 'a', suiteComponents: ['x'] }, 6, metaTwo),
          ii_uniq: L.resolveSemantics({ type: 'basic', cluster: 'b' }, 5, metaTwo),
        };
        """
    )
    assert result["metaOne"] is True
    assert result["metaTwo"] is False

    assert result["i_basic"]["hemisphere"] == "root"
    assert result["i_basic"]["glyph"] == "○"  # ○
    assert result["i_extra"]["hemisphere"] == "crown"
    assert result["i_extra"]["glyph"] == "◇"  # ◇
    assert result["i_ult"]["isSuite"] is True
    assert result["i_ult"]["glyph"] == "◆"  # ◆
    assert result["i_uniq"]["hemisphere"] == "outside"
    assert result["i_uniq"]["isUnique"] is True
    assert result["i_uniq"]["glyph"] == "◉"  # ◉

    assert result["ii_basic"]["hemisphere"] == "root"
    assert result["ii_fusion"]["hemisphere"] == "crown"
    assert result["ii_fusion"]["isSuite"] is False
    assert result["ii_suite"]["isSuite"] is True
    # §3.2 read order: a high-rank basic w/o suiteComponents short-circuits to outside.
    assert result["ii_uniq"]["hemisphere"] == "outside"
    assert result["ii_uniq"]["isUnique"] is True


def test_coreness_monotonicity_and_floor() -> None:
    """§4: 0-1★ -> 0, strictly increasing 2..6, clamped, 6★ -> 1."""
    result = _runlayout(
        "return [0,1,2,3,4,5,6,9].map((r) => L.corenessFromRank(r));"
    )
    assert result[0] == 0
    assert result[1] == 0  # 1★ still on the bark
    assert result[2] > 0
    assert result[6] == 1
    assert result[7] == 1  # rank 9 clamped
    ramp = result[2:7]
    assert all(b > a for a, b in zip(ramp, ramp[1:])), "coreness must rise with rank"


def test_ghost_armature_excluded_and_uniques_outside() -> None:
    """§5.1 ghost exclusion + §2.2 unique-outside placement + determinism."""
    result = _runlayout(
        """
        const graph = { skills: [
          { id: 'ygg2-basic', type: 'basic', cluster: 'a', prerequisites: [], effectiveRank: 2 },
          { id: 'ygg2-fusion', type: 'fusion', cluster: 'a', prerequisites: ['ygg2-basic'], effectiveRank: 4 },
          { id: 'ygg2-unique', type: 'basic', cluster: 'b', prerequisites: ['ygg2-basic'], effectiveRank: 5 },
        ] };
        const r = L.buildWorldTreeLayout(graph);
        const rev = L.buildWorldTreeLayout({ skills: graph.skills.slice().reverse() });
        const ghostKeys = Object.keys(r.ghostPose);
        return {
          nodeCount: r.nodes.length,
          ghostCount: ghostKeys.length,
          ghostLeaksIntoNodes: r.nodes.some((n) => n.id.startsWith(L.GHOST_PREFIX)),
          ghostLeaksIntoEdges: r.edges.some((e) =>
            e.source.startsWith(L.GHOST_PREFIX) || e.target.startsWith(L.GHOST_PREFIX)),
          roles: Array.from(new Set(ghostKeys.map((k) => r.ghostPose[k].role))).sort(),
          uniqueHemisphere: r.nodeMeta['ygg2-unique'].hemisphere,
          uniqueOutside: !!r.heroPose['ygg2-unique'].outside,
          uniqueX: r.heroPose['ygg2-unique'].x,
          outsideAllPositive: ghostKeys
            .filter((k) => r.ghostPose[k].role === 'outside')
            .every((k) => r.ghostPose[k].x > 0),
          deterministic: JSON.stringify(r.nodeMeta) === JSON.stringify(rev.nodeMeta)
            && JSON.stringify(r.ghostPose) === JSON.stringify(rev.ghostPose),
        };
        """
    )
    assert result["nodeCount"] == 3, "ghosts must not be counted as nodes"
    assert result["ghostCount"] > 0, "armature is always present"
    assert result["ghostLeaksIntoNodes"] is False
    assert result["ghostLeaksIntoEdges"] is False
    for role in ("spine", "bough", "root", "taproot", "outside"):
        assert role in result["roles"], f"armature must include {role}"
    assert result["uniqueHemisphere"] == "outside"
    assert result["uniqueOutside"] is True
    assert result["uniqueX"] > 0, "unique lands single-side (positive x)"
    assert result["outsideAllPositive"] is True
    assert result["deterministic"] is True

