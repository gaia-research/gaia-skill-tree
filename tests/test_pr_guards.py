"""scripts/pr_guards.py selects the same guards the six old workflows ran."""

import importlib.util
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("prguards", ROOT / "scripts" / "pr_guards.py")
prguards = importlib.util.module_from_spec(spec)
# @dataclass resolves its module through sys.modules, so register before exec.
sys.modules[spec.name] = prguards
spec.loader.exec_module(prguards)


def names(files):
    return {g.name for g in prguards.selectGuards(files)}


def test_glob_star_stops_at_slash_and_doublestar_does_not():
    assert prguards.matches("README.md", ["*.md"])
    assert not prguards.matches("docs/guide.md", ["*.md"])
    assert prguards.matches("docs/app.js", ["docs/**/*.js"])
    assert prguards.matches("docs/js/deep/app.js", ["docs/**/*.js"])
    assert not prguards.matches("docsx/app.js", ["docs/**/*.js"])
    assert prguards.matches("packages/cli-npm/README.md", ["packages/*/README.md"])
    assert not prguards.matches("packages/cli-npm/docs/README.md", ["packages/*/README.md"])


def test_selection_matches_old_workflow_triggers():
    assert names(["src/gaia_cli/main.py"]) == {"taxonomy-authority", "version-stamp"}
    assert names(["CLAUDE.md"]) == {"rank-vocabulary", "lexicon"}
    assert names(["docs/js/skill-graph.js"]) == {"html-sink", "taxonomy-authority"}
    assert names(["docs/graph/gaia.json"]) == {"license"}
    assert names(["registry/nodes/x.json"]) == {"rank-vocabulary"}
    assert names(["tests/test_push.py", "skill-trees/a/skill-tree.json"]) == set()


def test_runner_changes_and_unknown_diffs_run_everything():
    everything = {g.name for g in prguards.GUARDS}
    assert names(["scripts/pr_guards.py"]) == everything
    assert names([".github/workflows/pr-guards.yml"]) == everything
    assert {g.name for g in prguards.selectGuards(None)} == everything
    assert {g.name for g in prguards.selectGuards([], runAll=True)} == everything


def test_workflow_paths_equal_union_of_guard_globs():
    # BaseLoader keeps the `on:` key a string instead of YAML 1.1's True.
    workflow = yaml.load((ROOT / ".github/workflows/pr-guards.yml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    for event in ("pull_request", "push"):
        assert set(workflow["on"][event]["paths"]) == prguards.workflowPaths(), event


def test_workflow_defaults_to_read_only_token():
    workflow = yaml.load((ROOT / ".github/workflows/pr-guards.yml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    assert workflow["permissions"] == {"contents": "read"}
