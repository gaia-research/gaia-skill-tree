"""Real CLI subprocess rehearsal; no live registry and no genuine issuer claims."""
import base64
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
# These tests chain several CLI subprocesses; under load they can outlast the global 60s
# thread timeout and kill the session before the failing assertion is reported.
pytestmark = pytest.mark.timeout(600)
CLI_TIMEOUT_SECONDS = 120


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
    # Strict held-proposal bytes ONLY inside this explicitly disposable root.
    # The actual native schema reader/validator and context digest remain intact.
    for name in ("namedSkill.schema.json", "skillTree.schema.json"):
        shutil.copyfile(REPO / "tests/fixtures/canonical-proposed-schema" / name,
                        root / "registry/schema" / name)
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


def _text(value):
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return value


def cli(root, *args, mode=None, grant=None):
    env = os.environ.copy()
    env.update(PYTHONPATH=str(REPO / "src"), PYTHONDONTWRITEBYTECODE="1", GAIA_OPERATOR_OVERRIDE="1", GAIA_HOME=str(root / "isolated-home"))
    command = [sys.executable, "-m", "gaia_cli"]
    if mode:
        command = [sys.executable, str(REPO / "tests/fixtures/canonical_cli_bootstrap.py"), mode, str(grant)]
    started = time.monotonic()
    timedOut = None
    try:
        return subprocess.run(command + ["--registry", str(root), "dev", *args], env=env, cwd=root,
                              text=True, capture_output=True, timeout=CLI_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as exc:
        timedOut = exc
    # Fail outside the except block so the report is not chained to the raw TimeoutExpired.
    elapsed = time.monotonic() - started
    pytest.fail(
        f"CLI subprocess timed out after {elapsed:.1f}s (limit {CLI_TIMEOUT_SECONDS}s, mode={mode!r}): "
        f"dev {' '.join(args)}\n"
        f"partial stdout:\n{_text(timedOut.stdout)}\n"
        f"partial stderr:\n{_text(timedOut.stderr)}",
        pytrace=False)


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


def test_production_refuses_unadopted_schema_without_writes(fixtureRepo):
    root = fixtureRepo
    for name in ("namedSkill.schema.json", "skillTree.schema.json"):
        shutil.copyfile(REPO / "registry/schema" / name, root / "registry/schema" / name)
    before = sources(root)
    plan, path, _ = makePlan(root)
    assert sources(root) == before
    assert plan["summary"]["legacyBeforeTM"] == plan["summary"]["legacyAfterTM"]
    for verb in ("validate", "apply"):
        result = cli(root, "canonical", verb, "--plan", str(path))
        assert result.returncode == 1 and "schema adoption held" in result.stderr
    assert sources(root) == before
    assert not list((root / ".gaia/canonical-transactions").glob("*.json"))


def test_strict_proposal_validation_is_not_a_production_approval(fixtureRepo):
    import hashlib
    root = fixtureRepo
    before = sources(root)
    plan, path, _ = makePlan(root)
    for name in ("namedSkill.schema.json", "skillTree.schema.json"):
        data = (REPO / "tests/fixtures/canonical-proposed-schema" / name).read_bytes()
        assert plan["context"]["files"]["registry/schema/" + name] == hashlib.sha256(data).hexdigest()
    result = cli(root, "canonical", "validate", "--plan", str(path))
    assert result.returncode == 0, result.stderr
    assert "validation is not approval" in json.loads(result.stdout)["approval"]
    result = cli(root, "canonical", "apply", "--plan", str(path))
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
    applied = sources(root)
    refused = cli(root, "canonical", "rollback", "--plan", str(path), "--journal", journal)
    assert refused.returncode == 1 and "No trusted canonical transaction issuer" in refused.stderr
    assert sources(root) == applied
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
    assert result.returncode == 73  # abrupt child death after the first durable replacement
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


@pytest.mark.parametrize("mutation", ["target", "policy", "schema", "revision", "plan", "grant"])
def test_stale_inputs_forged_plans_and_grants_refuse(fixtureRepo, mutation):
    root = fixtureRepo
    plan, path, grant = makePlan(root)
    if mutation == "target":
        with (root / "registry/named/alice/tool.md").open("a") as stream:
            stream.write("outside edit\n")
    elif mutation == "policy":
        (root / "META.md").write_text("changed policy")
    elif mutation == "schema":
        schemaPath = root / "registry/schema/namedSkill.schema.json"
        schema = json.loads(schemaPath.read_bytes())
        schema["description"] = "changed schema input"
        dump(schemaPath, schema)
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
    if mutation in {"policy", "schema"}:
        # Refused for the bound-context reason, not incidentally (e.g. a validation error).
        assert "changed or are stale" in result.stderr, result.stderr
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


def test_interrupted_rollback_is_pending_and_can_be_completed(fixtureRepo):
    root = fixtureRepo
    before = sources(root)
    _, path, grant = makePlan(root)
    result = cli(root, "canonical", "apply", "--plan", str(path), mode="approved", grant=grant)
    assert result.returncode == 0, result.stderr
    journal = json.loads(result.stdout)["journal"]
    result = cli(root, "canonical", "rollback", "--plan", str(path), "--journal", journal,
                 mode="interrupt-rollback", grant=grant)
    assert result.returncode == 74
    snapshot = json.loads(cli(root, "canonical", "status").stdout)
    assert snapshot["pending"] and set(snapshot["receipts"][0]["targets"].values()) == {"before", "after"}
    pending = snapshot["receipts"][0]["journal"]
    result = cli(root, "canonical", "rollback", "--plan", str(path), "--journal", pending, mode="approved", grant=grant)
    assert result.returncode == 0, result.stderr
    assert sources(root) == before
    # A consumed decision cannot replay after exact preimage restoration.
    result = cli(root, "canonical", "apply", "--plan", str(path), mode="approved", grant=grant)
    assert result.returncode == 1 and "previously journaled plan" in result.stderr
    assert sources(root) == before


def test_cli_revision_transitions_preserve_payloads_and_have_no_score_authority(fixtureRepo):
    root = fixtureRepo
    _, path, grant = makePlan(root)
    result = cli(root, "canonical", "apply", "--plan", str(path), mode="approved", grant=grant)
    assert result.returncode == 0, result.stderr
    first = copy.deepcopy(loadNamed(root)["evidence"][0])
    plan, path, grant = makePlan(root, "assertion-transition", evidenceId=first["evidenceId"], targetState="revoked")
    assert "scoreAuthority" in plan["summary"]
    result = cli(root, "canonical", "apply", "--plan", str(path), mode="approved", grant=grant)
    assert result.returncode == 0, result.stderr
    rows = loadNamed(root)["evidence"]
    assert rows[0] == first and rows[1]["assertionState"] == "revoked" and rows[1]["revision"] == 2
    assert loadNamed(root)["level"] == "4★" and loadNamed(root)["origin"] is True
    # Restoration is a successor, not deletion of the historical revocation.
    _, path, grant = makePlan(root, "assertion-transition", evidenceId=first["evidenceId"], targetState="active")
    result = cli(root, "canonical", "apply", "--plan", str(path), mode="approved", grant=grant)
    assert result.returncode == 0, result.stderr
    restored = copy.deepcopy(loadNamed(root))
    assert len(restored["evidence"]) == 3 and restored["evidence"][-1]["revision"] == 3
    _, path, grant = makePlan(root, "metric-refresh", evidenceId=first["evidenceId"], metrics={"commits": 500},
        observationProvenance={"metricMethod": "reported", "observationState": "changed", "lastObservedAt": "2026-10-27T12:00:00Z",
            "contentDigest": "unknown", "sourceRevision": "fixture-v2", "measurementScope": "repository"})
    result = cli(root, "canonical", "apply", "--plan", str(path), mode="approved", grant=grant)
    assert result.returncode == 0, result.stderr
    refreshed = loadNamed(root)
    assert refreshed["evidence"][:-1] == restored["evidence"]
    assert refreshed["evidence"][-1]["commits"] == 500 and refreshed["evidence"][-1]["revision"] == 4
    assert refreshed["level"] == "4★" and refreshed["origin"] is True


def test_invalid_staged_schema_refused_even_with_fixture_issuer(fixtureRepo):
    root = fixtureRepo
    treePath = root / "skill-trees/alice/skill-tree.json"
    tree = json.loads(treePath.read_bytes())
    tree["unsupportedCanonicalField"] = True
    dump(treePath, tree)
    _, path, grant = makePlan(root)
    before = sources(root)
    result = cli(root, "canonical", "apply", "--plan", str(path), mode="approved", grant=grant)
    assert result.returncode == 1 and "invalid staged output" in result.stderr
    assert sources(root) == before


def test_shared_writer_seams_refuse_pending_journal(fixtureRepo):
    from gaia_cli import canonicalTransaction as tx
    from gaia_cli.commands.dev.helpers import _write_md
    from gaia_cli.timeline import append_skill_event, append_skill_tree_event
    from gaia_cli.treeManager import save_tree
    root = fixtureRepo
    # An unknown/corrupt pending record must block, not silently clear itself.
    state = root / tx.STATE_DIR
    state.mkdir(parents=True)
    (state / "unknown.pending.json").write_text("corrupt")
    before = sources(root)
    for writer in (lambda: _write_md(root / "registry/named/alice/tool.md", {}, ""),
                   lambda: append_skill_event("tool", "add", "alice", "fixture", root),
                   lambda: append_skill_tree_event("alice", "alice/tool", "rank_up", "fixture", root),
                   lambda: save_tree("alice", {}, root)):
        with pytest.raises(tx.TransactionError, match="pending canonical transaction"):
            writer()
        assert sources(root) == before


def test_two_process_lock_then_pending_guard_blocks_native_writer(fixtureRepo):
    root = fixtureRepo
    env = os.environ.copy()
    env.update(PYTHONPATH=str(REPO / "src"), PYTHONDONTWRITEBYTECODE="1", GAIA_OPERATOR_OVERRIDE="1", GAIA_HOME=str(root / "isolated-home"))
    holderCode = '''
import sys, time
from pathlib import Path
from gaia_cli.canonicalTransaction import _lock
root = Path(sys.argv[1])
with _lock(root) as state:
    (root / "ready").touch()
    end = time.monotonic() + 10
    while not (root / "release").exists():
        if time.monotonic() > end:
            raise RuntimeError("fixture timed out")
        time.sleep(0.02)
    (state / "unknown.pending.json").write_text("corrupt fixture blocks safely")
'''
    before = sources(root)
    holder = subprocess.Popen([sys.executable, "-c", holderCode, str(root)], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    writer = None
    try:
        end = time.monotonic() + 5
        while not (root / "ready").exists() and time.monotonic() < end:
            assert holder.poll() is None
            time.sleep(0.02)
        assert (root / "ready").exists()
        grant = root.parent / "lock-observation.json"
        dump(grant, {"root": str(root)})
        writer = subprocess.Popen([sys.executable, str(REPO / "tests/fixtures/canonical_cli_bootstrap.py"), "observe-lock", str(grant),
            "--registry", str(root), "dev", "evidence", "alice/tool",
            "https://example.invalid/new", "--type", "repo-own", "--commits", "1", "--contributors", "1", "--no-build"],
            env=env, cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        end = time.monotonic() + 5
        while not (root / "writer-lock-attempt").exists() and time.monotonic() < end:
            assert writer.poll() is None
            time.sleep(0.02)
        assert (root / "writer-lock-attempt").exists()
        time.sleep(0.1)
        assert writer.poll() is None  # observed at lock boundary, still blocked on the other interpreter
        assert sources(root) == before
        (root / "release").touch()
        holder.communicate(timeout=10)
        assert holder.returncode == 0
        _, stderr = writer.communicate(timeout=15)
        assert writer.returncode == 1 and "pending canonical transaction" in stderr
        assert sources(root) == before
    finally:
        for child in (writer, holder):
            if child and child.poll() is None:
                child.kill()  # only this test's own finite synthetic processes
                child.communicate(timeout=5)


def test_ordinary_authorized_legacy_evidence_still_works(fixtureRepo):
    root = fixtureRepo
    result = cli(root, "evidence", "alice/tool", "https://example.invalid/new", "--type", "repo-own", "--commits", "1", "--contributors", "1", "--no-build")
    assert result.returncode == 0, result.stderr
    assert len(loadNamed(root)["evidence"]) == 2


@pytest.mark.parametrize("owner", ["registry", "skill-trees"])
def test_native_legacy_writer_cannot_bypass_pending_guard_via_owner_name(fixtureRepo, owner):
    root = fixtureRepo
    named = loadNamed(root)
    named.update(id=f"{owner}/tool", contributor=owner)
    newNamed = root / "registry/named" / owner / "tool.md"
    newNamed.parent.mkdir()
    newNamed.write_text("---\n" + yaml.safe_dump(named, sort_keys=False, allow_unicode=True) + "---\n# Fixture\n")
    (root / "registry/named/alice/tool.md").unlink()
    oldTree = root / "skill-trees/alice/skill-tree.json"
    tree = json.loads(oldTree.read_bytes())
    tree["userId"] = owner
    tree["unlockedSkills"][0]["skillId"] = f"{owner}/tool"
    newTree = root / "skill-trees" / owner / "skill-tree.json"
    newTree.parent.mkdir()
    dump(newTree, tree)
    oldTree.unlink()
    state = root / ".gaia/canonical-transactions"
    state.mkdir(parents=True)
    (state / "unknown.pending.json").write_text("unknown pending must remain blocked")
    before = sources(root)

    result = cli(root, "evidence", f"{owner}/tool", "https://example.invalid/new",
                 "--type", "repo-own", "--commits", "1", "--contributors", "1", "--no-build")

    assert result.returncode == 1 and "pending canonical transaction" in result.stderr
    assert sources(root) == before
