"""Real CLI subprocess rehearsal; no live registry and no genuine issuer claims."""
import base64
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def fixtureRepo(tmp_path):
    root = tmp_path / "repo"
    (root / "registry/named/alice").mkdir(parents=True)
    (root / "registry/nodes/basic").mkdir(parents=True)
    (root / "skill-trees/alice").mkdir(parents=True)
    shutil.copytree(REPO / "registry/schema", root / "registry/schema")
    (root / "DISPOSABLE_CANONICAL_FIXTURE").touch()
    named = {"id": "alice/tool", "name": "Fixture Tool", "contributor": "alice", "origin": True,
             "genericSkillRef": "tool", "status": "named", "level": "4★", "title": "Fixture",
             "description": "Disposable fixture implementation", "createdAt": "2026-01-01", "updatedAt": "2026-10-27",
             "evidence": [{"type": "repo-own", "source": "https://github.com/fixture/tool", "evaluator": "alice",
                           "date": "2026-01-01", "commits": 816, "contributors": 2}],
             "timeline": [{"timestamp": "2026-01-01T00:00:00Z", "action": "rank_up", "previousValue": "3★", "newValue": "4★"}]}
    (root / "registry/named/alice/tool.md").write_text("---\n" + yaml.safe_dump(named, sort_keys=False, allow_unicode=True) + "---\n# Historical body\n")
    dump(root / "registry/nodes/basic/tool.json", {"id": "tool", "name": "Tool", "type": "basic", "description": "Fixture generic capability", "prerequisites": []})
    tree = {"userId": "alice", "updatedAt": "2026-10-27", "unlockedSkills": [
        {"skillId": "alice/tool", "level": "3★", "unlockedAt": "2026-01-01", "unlockedIn": "fixture/tool",
         "levelHistory": [{"level": "3★", "achievedAt": "2026-01-01T00:00:00Z", "source": "promotion"}]}],
        "pendingCombinations": [], "stats": {"totalUnlocked": 1, "highestLevel": "3★"}, "timeline": []}
    # Use the real treeStats requirements, not a permissive hand-written schema.
    stats = json.loads((root / "registry/schema/skillTree.schema.json").read_bytes())["definitions"]["treeStats"]
    tree["stats"] = {key: 0 for key in stats.get("required", [])}
    dump(root / "skill-trees/alice/skill-tree.json", tree)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "fixture"], check=True)
    return root


def cli(root, *args, mode=None, grant=None):
    env = os.environ.copy()
    env.update(PYTHONPATH=str(REPO / "src"), PYTHONDONTWRITEBYTECODE="1", GAIA_OPERATOR_OVERRIDE="1", GAIA_HOME=str(root / "isolated-home"))
    command = [sys.executable, "-m", "gaia_cli"]
    if mode:
        command = [sys.executable, str(REPO / "tests/fixtures/canonical_cli_bootstrap.py"), mode, str(grant)]
    return subprocess.run(command + ["--registry", str(root), "dev", *args], env=env, cwd=root,
                          text=True, capture_output=True, timeout=25)


def makePlan(root, operation="migrate-evidence", **extra):
    request = {"operation": operation, "skillId": "alice/tool", "decisionRef": "fixture:decision-1",
               "evaluationAtUTC": "2026-10-27T12:00:00Z", "policyRevision": "yggdrasil-iii-frozen/fixture"}
    request.update(extra)
    requestPath = root.parent / "request.json"
    dump(requestPath, request)
    result = cli(root, "canonical", "plan", "--request", str(requestPath))
    assert result.returncode == 0, result.stderr
    plan = json.loads(result.stdout)
    planPath = root.parent / "plan.json"
    dump(planPath, plan)
    grant = root.parent / "fixture-grant.json"
    dump(grant, dict(root=str(root), planDigest=plan["planDigest"], context=plan["context"], request=request, operations=["apply", "rollback"]))
    return plan, planPath, grant


def sources(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for area in ("registry", "skill-trees") for p in (root / area).rglob("*") if p.is_file()}


def loadNamed(root):
    return yaml.safe_load((root / "registry/named/alice/tool.md").read_text().split("---", 2)[1])


def test_production_refuses_schema_and_missing_issuer_without_writes(fixtureRepo):
    root = fixtureRepo
    before = sources(root)
    plan, path, grant = makePlan(root)
    assert sources(root) == before
    assert plan["summary"]["legacyBeforeTM"] == plan["summary"]["legacyAfterTM"]
    for verb in ("validate", "apply"):
        result = cli(root, "canonical", verb, "--plan", str(path))
        assert result.returncode == 1 and "schema adoption held" in result.stderr
    # Even test-only schema extension cannot authenticate a production approval.
    result = cli(root, "canonical", "apply", "--plan", str(path), mode="schema-only", grant=grant)
    assert result.returncode == 1 and "No trusted canonical transaction issuer" in result.stderr
    assert sources(root) == before
    assert not list((root / ".gaia/canonical-transactions").glob("*.json"))
    result = cli(root, "canonical", "apply", "--plan", str(path), "--fixture-provider")
    assert result.returncode != 0 and "unrecognized arguments" in result.stderr


def test_migration_dual_histories_and_exact_byte_rollback(fixtureRepo):
    root = fixtureRepo
    before = sources(root)
    original = loadNamed(root)
    plan, path, grant = makePlan(root)
    result = cli(root, "canonical", "validate", "--plan", str(path), mode="approved", grant=grant)
    assert result.returncode == 0, result.stderr
    result = cli(root, "canonical", "apply", "--plan", str(path), mode="approved", grant=grant)
    assert result.returncode == 0, result.stderr
    journal = json.loads(result.stdout)["journal"]
    named = loadNamed(root)
    tree = json.loads((root / "skill-trees/alice/skill-tree.json").read_bytes())
    assert named["level"] == original["level"] and named["origin"] is True
    assert named["timeline"][:-1] == original["timeline"]
    assert named["timeline"][-1] == {k: v for k, v in tree["timeline"][-1].items() if k != "skillId"}
    assert named["timeline"][-1]["previousValue"] != named["timeline"][-1]["newValue"]
    assert named["timeline"][-1]["decisionRef"] == "fixture:decision-1"
    row = named["evidence"][0]
    assert row["assertionState"] == "active" and row["revision"] == 1
    assert "decisionRef" not in row  # no invented historical admission
    result = cli(root, "canonical", "status")
    assert json.loads(result.stdout)["receipts"][0]["status"] == "committed"
    replay = cli(root, "canonical", "apply", "--plan", str(path), mode="approved", grant=grant)
    assert replay.returncode == 1
    result = cli(root, "canonical", "rollback", "--plan", str(path), "--journal", journal, mode="approved", grant=grant)
    assert result.returncode == 0, result.stderr
    assert sources(root) == before


def test_current_drift_reconciliation_never_backfills_awards(fixtureRepo):
    root = fixtureRepo
    before = sources(root)
    oldTree = json.loads((root / "skill-trees/alice/skill-tree.json").read_bytes())
    plan, path, grant = makePlan(root, "reconcile-owner")
    result = cli(root, "canonical", "apply", "--plan", str(path), mode="approved", grant=grant)
    assert result.returncode == 0, result.stderr
    named = loadNamed(root)
    tree = json.loads((root / "skill-trees/alice/skill-tree.json").read_bytes())
    assert named["level"] == "4★" and tree["unlockedSkills"][0]["level"] == "4★"
    assert tree["unlockedSkills"][0]["levelHistory"] == oldTree["unlockedSkills"][0]["levelHistory"]
    assert tree["timeline"][-1]["previousValue"] == "3★" and tree["timeline"][-1]["newValue"] == "4★"
    assert named["timeline"][-1]["previousValue"] == named["timeline"][-1]["newValue"] == "4★"
    assert tree["timeline"][-1]["action"] == "reconcile_owner"
    nextPlan, _, _ = makePlan(root, "reconcile-owner")
    assert nextPlan["noChange"] and not nextPlan["targets"]
    # Recreate original grant overwritten by second plan.
    dump(grant, dict(root=str(root), planDigest=plan["planDigest"], context=plan["context"], request=plan["request"], operations=["rollback"]))
    dump(path, plan)
    result = cli(root, "canonical", "rollback", "--plan", str(path), "--journal", json.loads(result.stdout)["journal"], mode="approved", grant=grant)
    assert result.returncode == 0, result.stderr
    assert sources(root) == before


def test_interruption_guards_actual_legacy_cli_and_recovers(fixtureRepo):
    root = fixtureRepo
    before = sources(root)
    plan, path, grant = makePlan(root)
    result = cli(root, "canonical", "apply", "--plan", str(path), mode="interrupt", grant=grant)
    assert result.returncode == 1 and "TEST-ONLY interruption" in result.stderr
    status = json.loads(cli(root, "canonical", "status").stdout)
    assert status["pending"]
    assert set(status["receipts"][0]["targets"].values()) == {"before", "after"}
    partial = sources(root)
    for args in (("canonical", "plan", "--request", str(root.parent / "request.json")),
                 ("evidence", "alice/tool", "https://example.invalid/new", "--type", "repo-own", "--commits", "1", "--contributors", "1", "--no-build")):
        result = cli(root, *args)
        assert result.returncode == 1 and "pending canonical transaction" in result.stderr
        assert sources(root) == partial
    result = cli(root, "canonical", "rollback", "--plan", str(path), "--journal", status["receipts"][0]["journal"], mode="approved", grant=grant)
    assert result.returncode == 0, result.stderr
    assert sources(root) == before
    assert not json.loads(cli(root, "canonical", "status").stdout)["pending"]


@pytest.mark.parametrize("mutation", ["target", "policy", "revision", "plan", "grant"])
def test_stale_inputs_forged_plans_and_grants_refuse(fixtureRepo, mutation):
    root = fixtureRepo
    plan, path, grant = makePlan(root)
    if mutation == "target":
        with (root / "registry/named/alice/tool.md").open("a") as stream:
            stream.write("outside edit\n")
    elif mutation == "policy":
        (root / "META.md").write_text("changed policy")
    elif mutation == "revision":
        subprocess.run(["git", "-C", str(root), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "--allow-empty", "-qm", "new revision"], check=True)
    elif mutation == "plan":
        plan["targets"][0]["after"] = base64.b64encode(b"arbitrary forged output").decode()
        plan["approvedBy"] = "founder"
        dump(path, plan)
    else:
        g = json.loads(grant.read_bytes())
        g["planDigest"] = "0" * 64
        dump(grant, g)
    before = sources(root)
    result = cli(root, "canonical", "apply", "--plan", str(path), mode="approved", grant=grant)
    assert result.returncode == 1, result.stdout
    assert sources(root) == before


def test_rollback_outside_edit_preserves_every_other_target(fixtureRepo):
    root = fixtureRepo
    _, path, grant = makePlan(root)
    result = cli(root, "canonical", "apply", "--plan", str(path), mode="approved", grant=grant)
    assert result.returncode == 0, result.stderr
    journal = json.loads(result.stdout)["journal"]
    with (root / "skill-trees/alice/skill-tree.json").open("a") as stream:
        stream.write(" ")
    before = sources(root)
    result = cli(root, "canonical", "rollback", "--plan", str(path), "--journal", journal, mode="approved", grant=grant)
    assert result.returncode == 1 and "outside edit" in result.stderr
    assert sources(root) == before


def test_ordinary_authorized_legacy_evidence_still_works(fixtureRepo):
    root = fixtureRepo
    result = cli(root, "evidence", "alice/tool", "https://example.invalid/new", "--type", "repo-own", "--commits", "1", "--contributors", "1", "--no-build")
    assert result.returncode == 0, result.stderr
    assert len(loadNamed(root)["evidence"]) == 2
