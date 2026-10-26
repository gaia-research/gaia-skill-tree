"""Short strict-publication regressions; full corpus replay belongs to parent."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from scripts import publication_context as pc

UTC = "2026-10-25T12:00:00Z"
REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def fast_runtime(monkeypatch):
    monkeypatch.setattr(pc, "runtime_identity", lambda: {"python": "synthetic-unit-runtime"})


def _context(tmp_path):
    source = tmp_path / "context-source"
    source.mkdir(exist_ok=True)
    (source / "input.json").write_text('{"fixed":true}')
    return pc.create_context(source, tmp_path / "context-output", UTC)


def _outputs(root):
    for rel in pc.GENERATED_OUTPUTS:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{}\n')


def _stages():
    return {name: {"status": "success", "outputs": {(selectors[0] + "fixture.json" if selectors[0].endswith("/") else selectors[0]): "synthetic"},
                   "executions": [{"generator": script, "status": "success"}] if script else []}
            for name, (script, selectors) in pc.STAGE_SPECS.items()}


def test_context_binds_dirty_untracked_bytes_runtime_and_revision(tmp_path, fast_runtime, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    path = source / "skill-trees/untracked/skill-tree.json"
    path.parent.mkdir(parents=True)
    path.write_text('{"level":1}')
    first = pc.create_context(source, tmp_path / "a", UTC)
    path.write_text('{"level":2}')
    second = pc.create_context(source, tmp_path / "b", UTC)
    assert first["snapshotId"] != second["snapshotId"]
    monkeypatch.setattr(pc, "runtime_identity", lambda: {"python": "changed"})
    assert second["snapshotId"] != pc.create_context(source, tmp_path / "c", UTC)["snapshotId"]
    copied = tmp_path / "copied"
    shutil.copytree(source, copied)
    pc.verify_copied_inputs(copied, second)
    (copied / "extra").touch()
    with pytest.raises(ValueError, match="extra"):
        pc.verify_copied_inputs(copied, second)


def test_context_rejects_overlap_symlink_and_foreign_worktree(tmp_path, fast_runtime):
    source = tmp_path / "source"
    source.mkdir()
    with pytest.raises(ValueError, match="disjoint"):
        pc.create_context(source, source / "inside", UTC)
    link = tmp_path / "link"
    link.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        pc.create_context(source, link / "child", UTC)
    foreign = next((Path(line[9:]) for line in subprocess.run(
        ["git", "worktree", "list", "--porcelain"], cwd=REPO, capture_output=True, text=True
    ).stdout.splitlines() if line.startswith("worktree ") and Path(line[9:]).resolve() != REPO), None)
    if foreign:
        with pytest.raises(ValueError, match="every repository worktree"):
            pc.create_context(REPO, foreign / "publication-fixture", UTC)


def test_external_manifest_exact_inventory_and_corruption(tmp_path, fast_runtime, monkeypatch):
    # Integrity unit test only; real semantic generation tested below.
    monkeypatch.setattr(pc, "_check_semantic_parity", lambda root: None)
    output = tmp_path / "output"
    output.mkdir()
    _outputs(output)
    context = _context(tmp_path)
    before = (output / pc.GENERATED_OUTPUTS[0]).read_bytes()
    pc.stamp_outputs(output, context, _stages())
    assert (output / pc.GENERATED_OUTPUTS[0]).read_bytes() == before
    assert pc.verify_outputs(output, context["snapshotId"])
    assert not pc.verify_outputs(output, "wrong-expected-identity")
    (output / "docs/extra.json").write_text('{}')
    assert not pc.verify_outputs(output)
    (output / "docs/extra.json").unlink()
    payload = json.loads((output / "publication-context.json").read_text())
    payload["engineIdentity"] = "corrupted"
    (output / "publication-context.json").write_text(json.dumps(payload))
    assert not pc.verify_outputs(output)


@pytest.mark.parametrize("corruption", ["skipped", "no-execution", "traversal", "wrong-owner"])
def test_stale_files_cannot_substitute_for_execution(tmp_path, fast_runtime, monkeypatch, corruption):
    monkeypatch.setattr(pc, "_check_semantic_parity", lambda root: None)
    output = tmp_path / "output"
    output.mkdir()
    _outputs(output)
    stages = _stages()
    if corruption == "skipped":
        stages["badges"]["status"] = "skipped"
    elif corruption == "no-execution":
        stages["badges"]["executions"] = []
    elif corruption == "traversal":
        stages["badges"]["outputs"] = {"../outside": "digest"}
    else:
        stages["badges"]["outputs"] = {"registry/named-skills.json": "digest"}
    with pytest.raises(ValueError):
        pc.stamp_outputs(output, _context(tmp_path), stages)
    assert not (output / "publication-artifacts.json").exists()


@pytest.mark.parametrize("code,log", [(1, "broken"), (0, "Warning: skipped required output"), (0, "Error: bad data")])
def test_generator_failures_fail_closed_even_with_old_files(tmp_path, code, log):
    (tmp_path / "old.json").write_text('{}')
    pc.begin_stage("probe", tmp_path)
    with pytest.raises(ValueError, match="failed/warned/skipped"):
        pc.record_execution(Path("broken.py"), [], code, log)


def test_stage_does_not_certify_skipped_script(tmp_path):
    script = tmp_path / "scripts/generateNamedIndex.py"
    script.parent.mkdir()
    script.touch()
    (tmp_path / "registry").mkdir()
    (tmp_path / "registry/named-skills.json").write_text('{"old":true}')
    pc.begin_stage("named-index", tmp_path)
    with pytest.raises(ValueError, match="skipped"):
        pc.finish_stage("named-index", tmp_path)


@pytest.mark.parametrize("rel", ["../x", "/absolute", "docs/../x", "docs//x", "docs/./x", "docs\\x"])
def test_context_traversal_rejected_before_file_reads(tmp_path, fast_runtime, rel):
    payload = _context(tmp_path)
    payload["inputDigests"] = {rel: "a" * 64}
    payload["snapshotId"] = pc._snapshot_id(payload["inputDigests"], payload["sourceRevision"], UTC, payload["runtimeIdentity"])
    path = tmp_path / "context.json"
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError):
        pc.load_context(path)


def test_pinned_datetime_and_absence_default(tmp_path, fast_runtime, monkeypatch):
    monkeypatch.delenv("GAIA_PUBLICATION_CONTEXT", raising=False)
    assert pc.evaluation_at_utc_from_env() is None
    assert pc.evaluation_datetime_from_env() is None
    context = _context(tmp_path)
    path = tmp_path / "context.json"
    path.write_text(json.dumps(context))
    monkeypatch.setenv("GAIA_PUBLICATION_CONTEXT", str(path))
    assert pc.evaluation_at_utc_from_env() == UTC
    assert pc.evaluation_datetime_from_env().isoformat() == "2026-10-25T12:00:00+00:00"
    path.write_text('{}')
    with pytest.raises(ValueError):
        pc.evaluation_at_utc_from_env()


DRIVER = r'''
import json
from pathlib import Path
import build_docs as b
from publication_context import begin_stage, finish_stage, STAGE_SPECS
b._STRICT_REHEARSAL = True
stages = {}
for name in STAGE_SPECS:
    begin_stage(name, b.ROOT)
    getattr(b, 'build_' + {'named-index':'named_index', 'docs-named-index':'docs_named_index',
        'trust-ledger':'trust_ledger', 'api-projection':'api_projection', 'profiles':'profile_pages',
        'og-cards':'og_cards', 'tree-md':'tree_md', 'docs-graph-assets':'docs_graph_assets'}.get(name, name))(False)
    stages[name] = finish_stage(name, b.ROOT)
(b.ROOT / 'publication-stages.json').write_text(json.dumps(stages, sort_keys=True))
'''


def _fixture_source(root):
    for directory in ("scripts", "src"):
        shutil.copytree(REPO / directory, root / directory,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".gaia", "node_modules"))
    for rel in ("pyproject.toml", "META.md", "GOVERNANCE.md", "registry/schema/meta.json", "docs/css/tokens.css"):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / rel, path)
    (root / "registry/nodes").mkdir(parents=True)
    (root / "registry/nodes/tool.json").write_text(json.dumps({"id": "tool", "name": "Tool", "type": "basic", "prerequisites": [], "description": "Synthetic fixture capability"}))
    (root / "registry/named/author").mkdir(parents=True)
    (root / "registry/nodes/component.json").write_text(json.dumps({"id": "component", "name": "Component", "type": "basic", "prerequisites": [], "description": "Synthetic component"}))
    (root / "registry/named/author/component.md").write_text('''---
id: author/component
name: Component
contributor: author
origin: true
genericSkillRef: component
status: named
level: 2★
description: Synthetic suite component
---
''')
    # Deliberately low TM, stored 4 stars, dated evidence, historical 5-star
    # award, and incumbent Origin. Not an approval or a live challenge fixture.
    (root / "registry/named/author/tool.md").write_text('''---
id: author/tool
name: Synthetic Tool
contributor: author
origin: true
genericSkillRef: tool
status: named
level: 4★
suiteComponents:
  - author/component
description: Explicitly synthetic rehearsal fixture
createdAt: '2025-01-01'
links:
  github: https://github.com/example/tool/blob/main/SKILL.md
evidence:
  - type: peer-review
    source: https://example.invalid/synthetic-review
    reviewers: 1
    grade: A
    sourceStartedAt: '2025-01-01T00:00:00Z'
    lastVerified: '2025-01-01T00:00:00Z'
timeline:
  - action: rank_up
    timestamp: '2025-01-01T00:00:00Z'
    previousValue: 3★
    newValue: 5★
---
\n## Installation\nSynthetic fixture only.\n''')
    tree = root / "skill-trees/author/skill-tree.json"
    tree.parent.mkdir(parents=True)
    tree.write_text(json.dumps({"userId": "author", "unlockedSkills": [{"skillId": "author/tool", "level": "4★", "unlockedAt": "2025-01-01T00:00:00Z", "levelHistory": [{"level": "5★", "achievedAt": "2025-01-01T00:00:00Z"}]}], "timeline": [{"skillId": "author/tool", "action": "rank_up", "timestamp": "2025-01-01T00:00:00Z", "previousValue": "3★", "newValue": "5★"}]}))


def test_real_bounded_builders_double_replay_and_surface_corruption(tmp_path, monkeypatch):
    # No model/network/full-corpus calls. Actual existing builders, two roots.
    source = tmp_path / "source"
    _fixture_source(source)
    manifests = []
    roots = []
    for name in ("first", "second"):
        root = tmp_path / name
        context = pc.create_context(source, root, UTC)
        shutil.copytree(source, root)
        pc.verify_copied_inputs(root, context)
        (root / "publication-context.json").write_text(json.dumps(context))
        env = {**os.environ, "PYTHONPATH": os.pathsep.join((str(root), str(root / "src"), str(root / "scripts"))),
               "GAIA_PUBLICATION_CONTEXT": str(root / "publication-context.json"), "PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1"}
        result = subprocess.run([sys.executable, "-c", DRIVER], cwd=root, env=env, capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr
        stages = json.loads((root / "publication-stages.json").read_text())
        # Run the semantic oracle once per complete build; this is not a stub.
        manifests.append(pc.stamp_outputs(root, context, stages))
        roots.append(root)
    assert manifests[0]["snapshotId"] == manifests[1]["snapshotId"]
    assert manifests[0]["artifacts"] == manifests[1]["artifacts"]
    root = roots[0]
    named = json.loads((root / "registry/named-skills.json").read_text())["buckets"]["tool"][0]
    assert named["level"] == "4★" and named["origin"] is True
    assert named["eligibilityProposal"]["status"] == "shadow"
    assert named["branch"] == "suite"
    assert named["apexGateStatus"]["sourceTenureDaysGte180AorS"] is True
    assert named["trustMagnitude"] < 25  # pinned dated freshness, not live clock
    assert "5★" in (root / "docs/u/author/index.html").read_text()
    # Reuse the same real generated fixture for per-surface semantic attacks.
    for rel, old, new in (
        ("docs/graph/named/index.json", '"origin": true', '"origin": false'),
        ("docs/graph/gaia.json", '"namedMaxLevel": "4★"', '"namedMaxLevel": "3★"'),
        ("docs/graph/ledger/data.json", '"currentStars": "4★"', '"currentStars": "3★"'),
        ("docs/api/v1/skills/author/tool.json", '"trustMagnitude":', '"wrongTM":'),
        ("docs/u/author/index.html", '5★', '6★'),
        ("docs/badges/registry.json", '"rank": 4', '"rank": 3'),
        ("docs/badges/_assets/author/tool.svg", '4 stars', '3 stars'),
    ):
        path = root / rel
        before = path.read_text()
        assert old in before, rel
        path.write_text(before.replace(old, new))
        with pytest.raises(ValueError, match="mismatch"):
            pc._check_semantic_parity(root)
        path.write_text(before)
    assert pc.verify_outputs(root, manifests[0]["snapshotId"])
