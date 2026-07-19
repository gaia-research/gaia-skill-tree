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
          ii_fusion: L.resolveSemantics({ type: 'fusion', cluster: 'a', branch: 'standard' }, 4, metaTwo),
          ii_suite: L.resolveSemantics({ type: 'fusion', cluster: 'a', branch: 'suite', suiteComponents: ['x'] }, 6, metaTwo),
          ii_uniq: L.resolveSemantics({ type: 'basic', cluster: 'b', branch: 'unique' }, 5, metaTwo),
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
    # Ygg II is TYPE-BLIND: membership is READ from the emitted branch. A node
    # carrying branch:'unique' short-circuits to outside regardless of type.
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
          { id: 'ygg2-unique', type: 'basic', cluster: 'b', prerequisites: ['ygg2-basic'], effectiveRank: 5, branch: 'unique' },
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
          outsideAllFinite: ghostKeys
            .filter((k) => r.ghostPose[k].role === 'outside')
            .every((k) => Number.isFinite(r.ghostPose[k].x) && Number.isFinite(r.ghostPose[k].y)),
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
    # ygg2-unique carries the emitted branch:'unique' — the resolver reads it and
    # seats it in the outside under-canopy constellation (centred on the spine).
    assert result["uniqueHemisphere"] == "outside"
    assert result["uniqueOutside"] is True
    assert result["uniqueX"] == result["uniqueX"], "unique x is a finite number"
    assert result["outsideAllFinite"] is True
    assert result["deterministic"] is True


def test_coreness_pulls_high_rank_toward_heartwood_core() -> None:
    """§4 Fix #3: effective rank pulls a node's POSITION toward the heartwood
    core (a CYLINDER radial target + vertical centre), monotone in rank,
    deterministic."""
    result = _runlayout(
        """
        // Hold the graph shape fixed and vary ONLY the crown node's rank so the
        // DAG-depth base pose is identical across variants; any |y-coreY| /
        // |pose-cylinderTarget| change is purely the coreness-pull. coreY =
        // treeHeight * CORE_Y_RATIO (0.13). The radial target is a point on a
        // cylinder of radius CORE_MIN_RADIUS * width (0.10 * 760) at a
        // deterministic per-node angle θ; holding the id fixed keeps θ fixed.
        const coreY = 680 * 0.13;
        const coreRadius = 0.10 * 760;
        const theta = (L.stableHash('crown:core-theta') / 4294967295) * Math.PI * 2;
        const targetX = coreRadius * Math.cos(theta);
        const targetZ = coreRadius * Math.sin(theta);
        const variant = (rank) => L.buildWorldTreeLayout({ skills: [
          { id: 'seed', type: 'basic', cluster: 'a', prerequisites: [] },
          { id: 'crown', type: 'extra', cluster: 'a', prerequisites: ['seed'], effectiveRank: rank },
        ] });
        const rows = [0, 2, 4, 6].map((rank) => {
          const p = variant(rank).fieldPose['crown'];
          return {
            rank,
            dy: Math.abs(p.y - coreY),
            dTarget: Math.hypot(p.x - targetX, (p.z || 0) - targetZ),
          };
        });
        // Distinct 6★ nodes spread AROUND the axis on the cylinder barrel rather
        // than collapsing to one identical point — that spread IS the un-pinch.
        const spread = L.buildWorldTreeLayout({ skills: [
          { id: 'core-seed', type: 'basic', cluster: 'a', prerequisites: [] },
          { id: 'apex-one', type: 'extra', cluster: 'a', prerequisites: ['core-seed'], effectiveRank: 6 },
          { id: 'apex-two', type: 'extra', cluster: 'a', prerequisites: ['core-seed'], effectiveRank: 6 },
          { id: 'apex-three', type: 'extra', cluster: 'a', prerequisites: ['core-seed'], effectiveRank: 6 },
        ] });
        const apexes = ['apex-one', 'apex-two', 'apex-three'].map((id) => spread.fieldPose[id]);
        let maxSeparation = 0;
        for (let i = 0; i < apexes.length; i += 1) {
          for (let j = i + 1; j < apexes.length; j += 1) {
            maxSeparation = Math.max(maxSeparation,
              Math.hypot(apexes[i].x - apexes[j].x, (apexes[i].z || 0) - (apexes[j].z || 0)));
          }
        }
        return { rows, coreRadius, maxSeparation };
        """
    )
    rows = result["rows"]
    dys = [r["dy"] for r in rows]
    dtargets = [r["dTarget"] for r in rows]
    assert all(b < a for a, b in zip(dys, dys[1:])), "higher rank sits closer to coreY"
    assert all(
        b < a for a, b in zip(dtargets, dtargets[1:])
    ), "higher rank sits closer to the core cylinder"
    # distinct 6★ nodes occupy distinct barrel positions, not a collapsed point.
    assert result["maxSeparation"] > result["coreRadius"] * 0.5, "6★ spread around the cylinder"

