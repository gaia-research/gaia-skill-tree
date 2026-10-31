"""Regressions for the independent review of #2180 (probes p1..p4 and the P3 findings).

Everything runs against disposable roots; no genuine issuer exists or is claimed.
"""
import base64
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from gaia_cli import canonicalTransaction as tx
from gaia_cli import canonicalWorkflow as workflow

sys.path.insert(0, str(Path(__file__).parent))
from test_canonical_cli import (  # noqa: E402,F401
    REPO, cli, dump, fixtureRepo, installUnadoptedSchemas, makePlan, sources,
)


class Issuer:
    """Test-only stand-in for a future trusted issuer."""

    def __init__(self, operation="apply"):
        self.operation = operation

    def verify(self, request):
        return request.operation == self.operation


def pendingMarker(root):
    state = Path(root) / tx.STATE_DIR
    state.mkdir(parents=True, exist_ok=True)
    marker = state / "unknown.pending.json"
    marker.write_text("pending must block legacy writers")
    return marker


def simpleRoot(tmp_path, mode=0o644):
    root = tmp_path.resolve()
    target = root / "registry/named/alice/tool.md"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"orig\n")
    os.chmod(target, mode)
    return root, target


# --- finding 1 (P2): `gaia propose` raw writer must honour the pending guard ----------

def proposeEnv(root):
    env = os.environ.copy()
    env.update(PYTHONPATH=str(REPO / "src"), PYTHONDONTWRITEBYTECODE="1",
               GAIA_HOME=str(root.parent / "home"), GITHUB_REPOSITORY="alice/tool")
    return env


def propose(root):
    return subprocess.run(
        [sys.executable, "-m", "gaia_cli", "--registry", str(root), "propose", "tool",
         "--target", "alice/tool", "-y", "--no-pr"],
        env=proposeEnv(root), cwd=root, text=True, capture_output=True, timeout=60)


def proposeSetup(root):
    dump(root / "registry/gaia.json", {"skills": [
        {"id": "tool", "name": "Tool", "type": "basic", "description": "Fixture generic capability", "prerequisites": []}]})
    (root / ".gaia").mkdir(exist_ok=True)
    dump(root / ".gaia/config.json", {"gaiaUser": "alice"})


def test_propose_refuses_while_transaction_pending_without_any_write(fixtureRepo):
    root = fixtureRepo
    proposeSetup(root)
    pendingMarker(root)
    before = sources(root)
    result = propose(root)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "pending canonical transaction" in result.stderr
    assert sources(root) == before  # named file, tree and intake batch all untouched
    assert "Traceback" not in result.stderr


def test_promote_to_named_is_guarded_by_itself(fixtureRepo):
    from gaia_cli.name import promote_to_named
    root = fixtureRepo
    pendingMarker(root)
    before = sources(root)
    with pytest.raises(tx.TransactionError, match="pending canonical transaction"):
        promote_to_named({"id": "tool", "name": "Tool", "description": "Fixture generic capability"},
                         "alice", "tool", str(root))
    assert sources(root) == before


def test_reset_refuses_tree_removal_while_pending(fixtureRepo):
    root = fixtureRepo
    proposeSetup(root)
    pendingMarker(root)
    before = sources(root)
    result = subprocess.run(
        [sys.executable, "-m", "gaia_cli", "--registry", str(root), "reset", "-y"],
        env=proposeEnv(root), cwd=root, text=True, capture_output=True, timeout=60)
    assert result.returncode == 1, result.stdout + result.stderr  # exit status propagates
    assert "pending canonical transaction" in result.stderr
    assert (root / "skill-trees/alice/skill-tree.json").exists()
    assert sources(root) == before


# --- finding 2 (P3): journal mode is bound by the plan digest and range-checked -------

def tamperJournalMode(journal, mode):
    doc = json.loads(journal.read_bytes())
    doc.pop("journalDigest")
    doc["targets"][0]["mode"] = mode
    doc["journalDigest"] = hashlib.sha256(tx._canonical(doc)).hexdigest()
    journal.write_bytes(tx._canonical(doc) + b"\n")


@pytest.mark.parametrize("mode", [0o6777, 0o1777, 0o4755, -1, True, "0o644"])
def test_edited_journal_mode_with_recomputed_digest_is_refused(tmp_path, mode):
    root, target = simpleRoot(tmp_path)
    plan = tx.prepare(root, "p", "id-1", [tx.Change("registry/named/alice/tool.md", b"new\n")])
    journal = Path(tx.apply(plan, Issuer()))
    tamperJournalMode(journal, mode)
    with pytest.raises(tx.TransactionError):
        tx.rollback(root, journal, Issuer("rollback"))
    assert target.read_bytes() == b"new\n"


def test_in_range_but_different_journal_mode_is_refused_by_the_plan_digest(tmp_path):
    root, target = simpleRoot(tmp_path, mode=0o640)
    plan = tx.prepare(root, "p", "id-2", [tx.Change("registry/named/alice/tool.md", b"new\n")])
    journal = Path(tx.apply(plan, Issuer()))
    tamperJournalMode(journal, 0o777)  # valid permission bits, but not the approved ones
    with pytest.raises(tx.TransactionError, match="digest|mismatch"):
        tx.rollback(root, journal, Issuer("rollback"))
    assert target.read_bytes() == b"new\n"


def test_mode_is_part_of_the_plan_digest_and_roundtrips(tmp_path):
    root, target = simpleRoot(tmp_path, mode=0o640)
    plan = tx.prepare(root, "p", "id-3", [tx.Change("registry/named/alice/tool.md", b"new\n")])
    assert plan.targets[0].mode == 0o640
    other = tx.Target(plan.targets[0].path, plan.targets[0].before, plan.targets[0].after, 0o600)
    assert tx._plan_digest(plan.root, plan.purpose, plan.identity, (other,)) != plan.digest
    with pytest.raises(tx.TransactionError, match="mode"):
        tx._plan_digest(plan.root, plan.purpose, plan.identity,
                        (tx.Target(other.path, other.before, other.after, 0o6777),))
    journal = Path(tx.apply(plan, Issuer()))
    assert stat.S_IMODE(target.stat().st_mode) == 0o640
    tx.rollback(root, journal, Issuer("rollback"))
    assert target.read_bytes() == b"orig\n" and stat.S_IMODE(target.stat().st_mode) == 0o640


def test_mode_changed_after_planning_is_a_cas_conflict(tmp_path):
    root, target = simpleRoot(tmp_path, mode=0o640)
    plan = tx.prepare(root, "p", "id-4", [tx.Change("registry/named/alice/tool.md", b"new\n")])
    os.chmod(target, 0o600)
    with pytest.raises(tx.TransactionError, match="CAS conflict"):
        tx.apply(plan, Issuer())
    assert target.read_bytes() == b"orig\n"


def test_workflow_plan_binds_mode_and_tamper_is_stale(fixtureRepo):
    root = fixtureRepo
    plan, path, _ = makePlan(root)
    assert all(isinstance(t["mode"], int) for t in plan["targets"])
    plan["targets"][0]["mode"] = 0o6777
    dump(path, plan)
    result = cli(root, "canonical", "validate", "--plan", str(path))
    assert result.returncode == 1
    assert "changed or are stale" in result.stderr, result.stderr


# --- finding 3 (P3): status reports per journal and survives a corrupt one ------------

def test_status_reports_each_journal_and_survives_a_corrupt_or_oversize_one(fixtureRepo):
    root = fixtureRepo
    state = root / tx.STATE_DIR
    state.mkdir(parents=True)
    (state / ("a" * 64 + ".pending.json")).write_bytes(b"x" * (tx.MAX_JOURNAL_BYTES + 1))
    (state / ("b" * 64 + ".committed.json")).write_text("{}")
    result = cli(root, "canonical", "status")
    assert result.returncode == 0, result.stderr
    snapshot = json.loads(result.stdout)
    byId = {r["id"]: r for r in snapshot["receipts"]}
    assert set(byId) == {"a" * 64 + ".pending.json", "b" * 64 + ".committed.json"}
    assert all(r["status"] == "unreadable" and r["error"] for r in byId.values())
    assert snapshot["pending"] is True  # an unreadable pending journal still blocks writers


def test_status_still_reports_a_good_journal_next_to_a_corrupt_one(fixtureRepo):
    root = fixtureRepo
    _, path, grant = makePlan(root)
    result = cli(root, "canonical", "apply", "--plan", str(path), mode="approved", grant=grant)
    assert result.returncode == 0, result.stderr
    (root / tx.STATE_DIR / ("c" * 64 + ".pending.json")).write_text("not json")
    snapshot = json.loads(cli(root, "canonical", "status").stdout)
    statuses = sorted(r["status"] for r in snapshot["receipts"])
    assert statuses == ["committed", "unreadable"]


# --- finding 4 (P3): rollback resolves once and never re-follows an alias -------------

def test_rollback_does_not_follow_an_alias_retargeted_after_the_check(tmp_path, monkeypatch):
    root, target = simpleRoot(tmp_path)
    plan = tx.prepare(root, "p", "id-5", [tx.Change("registry/named/alice/tool.md", b"new\n")])
    journal = Path(tx.apply(plan, Issuer()))
    state = root / tx.STATE_DIR
    decoyDir = tmp_path / "decoy"
    decoyDir.mkdir()
    decoy = decoyDir / journal.name
    decoy.write_bytes(b"attacker journal must never be touched")
    alias = root / "alias"
    alias.symlink_to(state, target_is_directory=True)
    original = tx._read_journal

    def retargetAfterCheck(path, selected):
        result = original(path, selected)
        alias.unlink()
        alias.symlink_to(decoyDir, target_is_directory=True)  # the race
        return result

    monkeypatch.setattr(tx, "_read_journal", retargetAfterCheck)
    tx.rollback(root, alias / journal.name, Issuer("rollback"))
    assert decoy.read_bytes() == b"attacker journal must never be touched"
    assert sorted(p.name for p in decoyDir.iterdir()) == [journal.name]
    assert target.read_bytes() == b"orig\n"
    assert list(state.glob("*.rolled-back.json"))


def test_journal_symlink_is_refused_by_reader(tmp_path):
    root, _ = simpleRoot(tmp_path)
    plan = tx.prepare(root, "p", "id-6", [tx.Change("registry/named/alice/tool.md", b"new\n")])
    journal = Path(tx.apply(plan, Issuer()))
    link = journal.with_name("link.json")
    link.symlink_to(journal)
    with pytest.raises(tx.TransactionError, match="bounded regular file"):
        tx._read_journal(link, root)


# --- finding 5 (P3): tests that exercised the wrong mechanism --------------------------

@pytest.mark.parametrize("owner", ["registry", "skill-trees"])
@pytest.mark.parametrize("area", ["named", "tree"])
def test_namespace_matcher_alone_guards_reserved_looking_owners(tmp_path, owner, area):
    """Calls guardCanonicalPath directly: no dispatch-level lock, no save_tree lock."""
    root = tmp_path / "repo"
    pendingMarker(root)
    target = (root / "registry/named" / owner / "tool.md" if area == "named"
              else root / "skill-trees" / owner / "skill-tree.json")
    with pytest.raises(tx.TransactionError, match="pending canonical transaction"):
        with tx.guardCanonicalPath(target):
            raise AssertionError("body must not run while pending")
    # It selected the true root, not an owner-named inner directory.
    assert not (root / "registry/named/.gaia").exists()
    assert not (root / "skill-trees/.gaia").exists()


def test_namespace_matcher_ignores_non_canonical_paths(tmp_path):
    root = tmp_path / "repo"
    pendingMarker(root)
    for other in (root / "docs/x.md", root / "registry/gaia.json", root / "skill-trees/alice/other.json"):
        with tx.guardCanonicalPath(other):
            pass


def test_save_tree_for_a_reserved_looking_owner_is_guarded_through_its_explicit_lock(tmp_path):
    """save_tree takes canonicalTransactionLock(registry_path); the matcher is covered above."""
    from gaia_cli.treeManager import save_tree
    root = tmp_path / "repo"
    pendingMarker(root)
    with pytest.raises(tx.TransactionError, match="pending canonical transaction"):
        save_tree("registry", {"userId": "registry"}, root)
    assert not (root / "skill-trees/registry/skill-tree.json").exists()


def cliPlan(root, tmp_path):
    plan, path, _ = makePlan(root)
    return plan, path


def test_unadopted_schema_and_invalid_output_have_distinct_refusals(fixtureRepo):
    root = fixtureRepo
    # (a) Synthetic missing-field schema -> adoption held, NOT "invalid output".
    installUnadoptedSchemas(root)
    _, path, _ = makePlan(root)
    result = cli(root, "canonical", "validate", "--plan", str(path))
    assert result.returncode == 1
    assert "schema adoption held" in result.stderr and "invalid staged output" not in result.stderr
    assert "lacks" in result.stderr  # names the missing lifecycle fields

    # (b) The adopted production schema defines lifecycle fields; a stricter local
    # constraint then makes the staged output invalid.
    for name in ("namedSkill.schema.json", "skillTree.schema.json"):
        shutil.copyfile(REPO / "registry/schema" / name, root / "registry/schema" / name)
    schemaPath = root / "registry/schema/namedSkill.schema.json"
    schema = json.loads(schemaPath.read_bytes())
    schema["properties"]["description"] = dict(schema["properties"].get("description", {}), maxLength=3)
    dump(schemaPath, schema)
    subprocess.run(["git", "-C", str(root), "-c", "user.name=F", "-c", "user.email=f@e.invalid",
                    "commit", "-qam", "stricter schema"], check=True)
    _, path, _ = makePlan(root)
    result = cli(root, "canonical", "validate", "--plan", str(path))
    assert result.returncode == 1
    assert "invalid staged output" in result.stderr and "schema adoption held" not in result.stderr


def test_schema_adoption_gaps_names_the_missing_fields():
    adopted = {n: json.loads((REPO / "registry/schema" / n).read_bytes())
               for n in ("namedSkill.schema.json", "skillTree.schema.json")}
    unadopted = {n: json.loads((REPO / "tests/fixtures/canonical-unadopted-schema" / n).read_bytes())
                 for n in ("namedSkill.schema.json", "skillTree.schema.json")}
    adoptedEvidence = set(adopted["namedSkill.schema.json"]["definitions"]["evidenceEntry"]["properties"])
    unadoptedEvidence = set(unadopted["namedSkill.schema.json"]["definitions"]["evidenceEntry"]["properties"])
    assert workflow.LIFECYCLE_EVIDENCE_FIELDS <= adoptedEvidence
    assert not workflow.LIFECYCLE_EVIDENCE_FIELDS & unadoptedEvidence
    for name in adopted:
        adoptedTimeline = set(adopted[name]["definitions"]["timelineEvent"]["properties"])
        unadoptedTimeline = set(unadopted[name]["definitions"]["timelineEvent"]["properties"])
        assert workflow.LIFECYCLE_TIMELINE_FIELDS <= adoptedTimeline
        assert not workflow.LIFECYCLE_TIMELINE_FIELDS & unadoptedTimeline
    assert workflow.schemaAdoptionGaps(adopted) == []
    gaps = workflow.schemaAdoptionGaps(unadopted)
    assert any("evidenceId" in gap for gap in gaps)
    assert any("decisionRef" in gap and "eventId" in gap for gap in gaps)


# --- finding 6 (P3): stray interrupted-write temp files are reported, never deleted ----

def test_status_reports_stray_temp_files_without_deleting_them(fixtureRepo):
    root = fixtureRepo
    stray = root / "registry/named/alice/.tool.md.k3j2h1g0.tmp"
    stray.write_bytes(b"partial")
    snapshot = json.loads(cli(root, "canonical", "status").stdout)
    assert snapshot["strayTempFiles"] == ["registry/named/alice/.tool.md.k3j2h1g0.tmp"]
    assert stray.read_bytes() == b"partial"


def test_real_killed_atomic_write_leaves_a_reported_temp_file(fixtureRepo):
    root = fixtureRepo
    code = ("import os,sys\nfrom pathlib import Path\nfrom gaia_cli import canonicalTransaction as tx\n"
            "os.replace = lambda *a, **k: os._exit(9)\n"
            "tx._atomic(Path(sys.argv[1]), b'x', 0o644)\n")
    env = dict(os.environ, PYTHONPATH=str(REPO / "src"), PYTHONDONTWRITEBYTECODE="1")
    done = subprocess.run([sys.executable, "-c", code, str(root / "registry/named/alice/tool.md")],
                          env=env, timeout=30)
    assert done.returncode == 9
    snapshot = json.loads(cli(root, "canonical", "status").stdout)
    assert len(snapshot["strayTempFiles"]) == 1
    assert snapshot["strayTempFiles"][0].startswith("registry/named/alice/.tool.md.")
    assert (root / snapshot["strayTempFiles"][0]).exists()


# --- re-review P3s: stargazer script, FIFO journal, reset exit status ------------------

def loadStargazer():
    import importlib.util
    spec = importlib.util.spec_from_file_location("stargazerHeartbeatUnderTest", REPO / "scripts/stargazerHeartbeat.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stargazerRoot(tmp_path):
    root = tmp_path.resolve() / "repo"
    named = root / "registry/named/alice/tool.md"
    named.parent.mkdir(parents=True)
    named.write_text("---\nid: alice/tool\nname: Tool\nlinks:\n  github: https://github.com/alice/tool\n"
                     "evidence:\n- source: https://github.com/alice/tool\n  type: github-stars-own\n"
                     "  stars: 10\n---\n# Body\n", encoding="utf-8")
    return root, named


def runStargazer(module, root, monkeypatch):
    monkeypatch.setattr(module, "REPO_ROOT", root)
    monkeypatch.setattr(module, "NAMED_DIR", root / "registry/named")
    monkeypatch.setattr(module, "_fetch_stars", lambda owner, repo: 5000)
    monkeypatch.setattr(sys, "argv", ["stargazerHeartbeat.py", "--apply"])
    return module.main()


def test_stargazer_apply_refuses_cleanly_while_transaction_pending(tmp_path, monkeypatch, capsys):
    module = loadStargazer()
    root, named = stargazerRoot(tmp_path)
    pendingMarker(root)
    original = named.read_bytes()
    assert runStargazer(module, root, monkeypatch) == 1
    assert named.read_bytes() == original
    assert "pending canonical transaction" in capsys.readouterr().err


def test_stargazer_apply_still_writes_when_nothing_is_pending(tmp_path, monkeypatch):
    module = loadStargazer()
    root, named = stargazerRoot(tmp_path)
    assert runStargazer(module, root, monkeypatch) == 0
    assert "stars: 5000" in named.read_text(encoding="utf-8")


def test_stargazer_process_file_write_is_itself_guarded(tmp_path):
    module = loadStargazer()
    root, named = stargazerRoot(tmp_path)
    pendingMarker(root)
    module._fetch_stars = lambda owner, repo: 5000
    original = named.read_bytes()
    with pytest.raises(tx.TransactionError, match="pending canonical transaction"):
        module.process_file(named, apply=True)
    assert named.read_bytes() == original


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="POSIX FIFOs required")
def test_fifo_named_like_a_journal_cannot_hang_status_or_reads(fixtureRepo):
    root = fixtureRepo
    state = root / tx.STATE_DIR
    state.mkdir(parents=True)
    fifo = state / ("d" * 64 + ".pending.json")
    os.mkfifo(fifo)
    with pytest.raises(tx.TransactionError, match="bounded regular file"):
        tx._read_journal(fifo, root.resolve())
    result = cli(root, "canonical", "status")  # cli() has a 25s timeout: a hang fails the test
    assert result.returncode == 0, result.stderr
    snapshot = json.loads(result.stdout)
    assert snapshot["receipts"][0]["status"] == "unreadable" and snapshot["pending"] is True
