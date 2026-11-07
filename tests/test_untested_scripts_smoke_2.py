"""Focused smoke tests for four more scripts that had no coverage (Refs #2283).

Subjects, each named explicitly below so `grep -rln <stem> tests` finds them:

* scripts/migrate_taxonomy_v6.py
* scripts/prepare_l4_october.py
* scripts/verify_review_findings.py
* scripts/crawlers/skillsmp/crawler.py

Other Steward unused-import candidates were checked first and are already covered
(see the PR body table): upstream_watcher/transport.py, upstream_watcher/batch.py,
steward_issue_reconcile.py, generateProfilePages.py, commands/dev/timeline.py,
commands/dev/verify.py and commands/misc.py.

Every test is hermetic: scripts are loaded with importlib and pointed at synthetic
fixtures under tmp_path (with the verification probe using ephemeral system temporary
directories cleaned on exit), the network is never touched (requests is stubbed,
and subprocess is stubbed in business-logic tests with only a benign `--help` invocation
exercising a real process), and neither the live registry nor founder reports are read
or written. The subject scripts are intentionally NOT modified.
"""

from __future__ import annotations

import ast
import csv
import importlib.util
import json
import py_compile
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

repoRoot = Path(__file__).resolve().parent.parent
migrateScript = repoRoot / "scripts" / "migrate_taxonomy_v6.py"
l4Script = repoRoot / "scripts" / "prepare_l4_october.py"
reviewScript = repoRoot / "scripts" / "verify_review_findings.py"
smpScript = repoRoot / "scripts" / "crawlers" / "skillsmp" / "crawler.py"


def loadScript(path: Path, name: str):
    """Load a script as a throwaway module without registering it in sys.modules."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def hasMainGuard(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if (
            isinstance(test, ast.Compare)
            and isinstance(test.left, ast.Name)
            and test.left.id == "__name__"
            and len(test.comparators) == 1
            and isinstance(test.comparators[0], ast.Constant)
            and test.comparators[0].value == "__main__"
        ):
            return True
    return False


@pytest.fixture(autouse=True)
def isolatedPath(monkeypatch):
    """Restore sys.modules, sys.path, and module state changed during tests."""
    saved_modules = dict(sys.modules)
    saved_path = list(sys.path)
    saved_module_dicts = {
        name: dict(mod.__dict__)
        for name, mod in sys.modules.items()
        if hasattr(mod, "__dict__")
        and (name == "common" or name.startswith("common.") or name == "gaia_cli" or name.startswith("gaia_cli."))
    }
    monkeypatch.setattr(sys, "path", list(sys.path))
    yield
    # 1. Restore sys.modules keys and values exactly
    for name in list(sys.modules):
        if name not in saved_modules:
            del sys.modules[name]
        elif sys.modules[name] is not saved_modules[name]:
            sys.modules[name] = saved_modules[name]
    for name, mod in saved_modules.items():
        if name not in sys.modules:
            sys.modules[name] = mod

    # 2. Restore module attributes for pre-existing common / gaia_cli modules
    for name, orig_dict in saved_module_dicts.items():
        if name in sys.modules and sys.modules[name] is saved_modules[name]:
            mod = sys.modules[name]
            for attr in list(mod.__dict__):
                if attr not in orig_dict:
                    try:
                        delattr(mod, attr)
                    except (AttributeError, TypeError):
                        pass
                elif mod.__dict__[attr] is not orig_dict[attr]:
                    try:
                        setattr(mod, attr, orig_dict[attr])
                    except (AttributeError, TypeError):
                        pass

    # 3. Restore sys.path in place
    sys.path[:] = saved_path


@pytest.mark.parametrize(
    "script",
    [migrateScript, l4Script, reviewScript, smpScript],
    ids=["migrate_taxonomy_v6", "prepare_l4_october", "verify_review_findings", "skillsmp_crawler"],
)
def test_subject_compiles_and_guards_main(script, tmp_path):
    assert script.is_file()
    py_compile.compile(str(script), cfile=str(tmp_path / "out.pyc"), doraise=True)
    assert hasMainGuard(script), f"{script.name} must guard its entrypoint"


# ---------------------------------------------------------------------------
# scripts/migrate_taxonomy_v6.py
# ---------------------------------------------------------------------------

BATCH = "yggdrasil-ii@2026-01-01"


def writeNode(directory: Path, nodeId: str, nodeType: str, prereqs: list[str], timeline=None) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    node = {"id": nodeId, "name": nodeId, "type": nodeType, "prerequisites": prereqs, "timeline": timeline or []}
    path = directory / f"{nodeId}.json"
    path.write_text(json.dumps(node, indent=2), encoding="utf-8")
    return path


def writeNamed(root: Path, contributor: str, slug: str, frontmatter: dict, body: str = "Body text.\n") -> Path:
    directory = root / contributor
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{slug}.md"
    path.write_text(f"---\n{yaml.dump(frontmatter, allow_unicode=True, sort_keys=False)}---\n{body}", encoding="utf-8")
    return path


@pytest.fixture
def migrate(tmp_path, monkeypatch, isolatedPath):
    """The migration module re-pointed at a synthetic registry under tmp_path."""
    module = loadScript(migrateScript, "migrateTaxonomyV6UnderTest")
    nodes = tmp_path / "registry" / "nodes"
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(module, "NODES_DIR", nodes)
    monkeypatch.setattr(module, "BASIC_DIR", nodes / "basic")
    monkeypatch.setattr(module, "EXTRA_DIR", nodes / "extra")
    monkeypatch.setattr(module, "ULTIMATE_DIR", nodes / "ultimate")
    monkeypatch.setattr(module, "FUSION_DIR", nodes / "fusion")
    monkeypatch.setattr(module, "NAMED_DIR", tmp_path / "registry" / "named")
    monkeypatch.setattr(module, "OUT_DIR", tmp_path / "generated-output")

    def fakeGitMove(src: Path, dst: Path, dry_run: bool) -> None:
        # Stand-in for `git mv`: the tmp registry is not a git repository.
        if dry_run:
            print(f"  [dry] git mv {src.relative_to(tmp_path)} -> {dst.relative_to(tmp_path)}")
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dst)

    monkeypatch.setattr(module, "_git_mv", fakeGitMove)
    module.nodes = nodes
    return module


def seedLegacyNodes(nodes: Path) -> None:
    writeNode(nodes / "basic", "alpha", "basic", [])
    writeNode(nodes / "extra", "beta", "extra", ["alpha"])
    writeNode(nodes / "ultimate", "gamma", "ultimate", ["beta"])
    writeNode(nodes / "extra", "delta", "extra", [])  # legacy extra with no prerequisites: anomaly


def test_migrate_taxonomy_v6_pure_helpers(migrate):
    assert migrate.LEGACY_TO_V6 == {"basic": "basic", "extra": "fusion", "unique": "basic", "ultimate": "fusion"}
    assert migrate.META_EPOCH == "yggdrasil-ii"
    assert migrate._default_migration_batch().startswith("yggdrasil-ii@")

    assert migrate._derive_v6_type({"type": "extra", "prerequisites": ["a"]}, Path("x")) == ("fusion", None)
    assert migrate._derive_v6_type({"type": "basic", "prerequisites": []}, Path("x")) == ("basic", None)
    derived, anomaly = migrate._derive_v6_type({"type": "extra", "prerequisites": []}, Path("x"))
    assert derived == "basic" and "flagged for manual review" in anomaly
    derived, anomaly = migrate._derive_v6_type({"type": "fusion", "prerequisites": []}, Path("x"))
    assert derived == "basic" and "structural inconsistency" in anomaly
    assert migrate._derive_v6_type({"type": "fusion", "prerequisites": ["a"]}, Path("x")) == ("fusion", None)
    assert migrate._derive_v6_type({"type": "mystery", "prerequisites": ["a"]}, Path("x"))[1].startswith("Unknown legacy type")

    assert migrate._generic_type_after_migration({"type": "ultimate"}) == "fusion"
    assert migrate._generic_type_after_migration({"type": "already-v6"}) == "already-v6"


def test_migrate_taxonomy_v6_provenance_helpers(migrate):
    legacy = {"action": "type_change", "details": "Reclassified (Yggdrasil II taxonomy migration #997)"}
    unrelated = {"action": "rank_up", "details": "Yggdrasil II mention but wrong action"}
    assert migrate._is_migration_event(legacy)
    assert not migrate._is_migration_event(unrelated)
    assert not migrate._is_migration_event("not a dict")

    timeline = [dict(legacy), dict(unrelated)]
    assert migrate._has_upgradable_events(timeline)
    assert not migrate._already_batched(timeline, BATCH)
    assert migrate._upgrade_legacy_events(timeline, BATCH) == 1
    assert timeline[0]["migrationBatch"] == BATCH and timeline[0]["metaEpoch"] == "yggdrasil-ii"
    assert "migrationBatch" not in timeline[1]
    assert timeline[0]["details"] == legacy["details"], "details prose must stay byte-identical"
    assert migrate._already_batched(timeline, BATCH)
    assert not migrate._has_upgradable_events(timeline)
    assert migrate._upgrade_legacy_events(timeline, BATCH) == 0, "upgrade is idempotent"

    stamped = migrate._stamp({"action": "type_change"}, BATCH)
    assert stamped["migrationBatch"] == BATCH


def test_migrate_taxonomy_v6_load_save_and_maps(migrate, tmp_path):
    nodePath = writeNode(migrate.nodes / "basic", "alpha", "basic", [])
    data = migrate._load_node(nodePath)
    data["description"] = "ünïcode ★"
    migrate._save_node(nodePath, data)
    assert migrate._load_node(nodePath)["description"] == "ünïcode ★"
    assert nodePath.read_text(encoding="utf-8").endswith("\n")

    named = writeNamed(migrate.NAMED_DIR, "acme", "tool", {"id": "acme/tool", "level": "2★"}, body="Hello\n")
    fm, body = migrate._load_named_skill(named)
    assert fm["id"] == "acme/tool" and body == "Hello\n"
    fm["note"] = "kept"
    migrate._save_named_skill(named, fm, body)
    fm2, body2 = migrate._load_named_skill(named)
    assert fm2["note"] == "kept" and body2 == "Hello\n"

    plain = migrate.NAMED_DIR / "acme" / "plain.md"
    plain.write_text("no frontmatter here\n", encoding="utf-8")
    assert migrate._load_named_skill(plain)[0] is None

    assert set(migrate._build_generic_skill_map(migrate.NODES_DIR)) == {"alpha"}
    assert set(migrate._build_named_skill_map(migrate.NAMED_DIR)) == {"acme/tool"}


def test_migrate_taxonomy_v6_phase_a_dry_run_changes_nothing(migrate, capsys):
    seedLegacyNodes(migrate.nodes)
    before = sorted(p.relative_to(migrate.nodes).as_posix() for p in migrate.nodes.rglob("*.json"))
    contents = {p: p.read_bytes() for p in migrate.nodes.rglob("*.json")}

    stats: dict = {}
    legacy = migrate.migrate_starless_nodes(dry_run=True, stats=stats, migration_batch=BATCH)

    assert legacy == {"alpha": "basic", "beta": "extra", "gamma": "ultimate", "delta": "extra"}
    assert sorted(p.relative_to(migrate.nodes).as_posix() for p in migrate.nodes.rglob("*.json")) == before
    assert all(p.read_bytes() == raw for p, raw in contents.items())
    assert not migrate.FUSION_DIR.exists()
    phaseA = stats["phaseA"]
    assert {m["nodeId"] for m in phaseA["moved"]} == {"beta", "gamma", "delta"}
    assert {r["nodeId"] for r in phaseA["retyped"]} == {"beta", "gamma", "delta"}
    assert [a["nodeId"] for a in phaseA["anomalies"]] == ["delta"]
    assert "[dry] git mv" in capsys.readouterr().out


def test_migrate_taxonomy_v6_phase_a_apply_moves_retypes_and_is_idempotent(migrate):
    seedLegacyNodes(migrate.nodes)
    stats: dict = {}
    migrate.migrate_starless_nodes(dry_run=False, stats=stats, migration_batch=BATCH)

    beta = migrate._load_node(migrate.FUSION_DIR / "beta.json")
    assert beta["type"] == "fusion"
    assert not (migrate.EXTRA_DIR / "beta.json").exists()
    assert (migrate.FUSION_DIR / "gamma.json").is_file()
    # the anomalous prereq-less legacy extra node lands in basic/ with a derived basic type
    delta = migrate._load_node(migrate.BASIC_DIR / "delta.json")
    assert delta["type"] == "basic"
    assert migrate._load_node(migrate.BASIC_DIR / "alpha.json")["timeline"] == [], "unchanged basic node gets no event"

    event = beta["timeline"][-1]
    assert event["action"] == "type_change"
    assert event["migrationBatch"] == BATCH and event["metaEpoch"] == "yggdrasil-ii"
    assert "extra to fusion" in event["details"]
    assert len(beta["timeline"]) == 1

    # A second run over the same tree must not append anything or move anything.
    snapshot = {p: p.read_bytes() for p in migrate.nodes.rglob("*.json")}
    migrate.migrate_starless_nodes(dry_run=False, stats={}, migration_batch=BATCH)
    assert {p: p.read_bytes() for p in migrate.nodes.rglob("*.json")} == snapshot


def test_migrate_taxonomy_v6_phase_a_upgrades_legacy_events_in_place(migrate):
    legacy = {
        "timestamp": "2026-07-01T00:00:00Z",
        "action": "type_change",
        "contributor": "mbtiongson1",
        "details": "Reclassified from extra to fusion (Yggdrasil II taxonomy migration #997)",
    }
    writeNode(migrate.nodes / "extra", "beta", "extra", ["alpha"], timeline=[dict(legacy)])
    stats: dict = {}
    migrate.migrate_starless_nodes(dry_run=False, stats=stats, migration_batch=BATCH)

    node = migrate._load_node(migrate.FUSION_DIR / "beta.json")
    assert len(node["timeline"]) == 1, "legacy event is stamped, never duplicated"
    assert node["timeline"][0]["migrationBatch"] == BATCH
    assert node["timeline"][0]["details"] == legacy["details"]
    assert stats["phaseA"]["alreadyDone"] == 1


def test_migrate_taxonomy_v6_phase_b_reports_gates_without_writing(migrate):
    writeNode(migrate.nodes / "basic", "plain-generic", "basic", [])
    fusionNode = writeNode(migrate.nodes / "fusion", "fused-generic", "fusion", ["plain-generic"])
    del fusionNode
    writeNamed(migrate.NAMED_DIR, "acme", "four", {
        "id": "acme/four", "level": "4★", "genericSkillRef": "plain-generic", "origin": True, "timeline": [],
    })
    writeNamed(migrate.NAMED_DIR, "acme", "five", {
        "id": "acme/five", "level": "5★", "genericSkillRef": "fused-generic", "timeline": [],
    })
    writeNamed(migrate.NAMED_DIR, "acme", "two", {
        "id": "acme/two", "level": "2★", "genericSkillRef": "plain-generic", "timeline": [],
    })
    before = {p: p.read_bytes() for p in migrate.NAMED_DIR.rglob("*.md")}

    gmap = migrate._build_generic_skill_map(migrate.NODES_DIR)
    nmap = migrate._build_named_skill_map(migrate.NAMED_DIR)
    stats: dict = {}
    migrate.migrate_named_skills(
        dry_run=True, allow_5star_demote=False, genericSkillMap=gmap, namedSkillMap=nmap,
        legacy_type_map={}, stats=stats, migration_batch=BATCH,
    )

    assert {p: p.read_bytes() for p in migrate.NAMED_DIR.rglob("*.md")} == before, "dry-run writes nothing"
    phaseB = stats["phaseB"]
    touched = {t["skillId"] for t in phaseB["typeChanges"]}
    assert touched == {"acme/four", "acme/five"}, "only 4-star and 5-star named skills are considered"
    # With no evidence, Trust Magnitude is far below both floors.
    assert [d["skillId"] for d in phaseB["demotions"]] == ["acme/four"]
    assert [c["skillId"] for c in phaseB["founderCheckpoints"]] == ["acme/five"]
    assert phaseB["founderCheckpoints"][0]["tmFloor"] == migrate.TM_FLOOR_5STAR


def test_migrate_taxonomy_v6_origin_gate_for_basic_parent(migrate):
    generic = {"id": "g", "prerequisites": []}
    assert migrate._origin_ok_for_unique({"origin": True}, generic, {"g": generic}, {}) is True
    assert migrate._origin_ok_for_unique({"origin": False}, generic, {"g": generic}, {}) is False
    assert migrate._origin_ok_for_unique({}, generic, {"g": generic}, {}) is False


def test_migrate_taxonomy_v6_backfill_only_main_stamps_legacy_events(migrate, monkeypatch, capsys):
    legacy = {
        "timestamp": "2026-07-01T00:00:00Z",
        "action": "demote",
        "details": "Demoted 4 to 3 (Yggdrasil II taxonomy migration #997)",
    }
    nodePath = writeNode(migrate.nodes / "fusion", "beta", "fusion", ["alpha"], timeline=[dict(legacy)])
    namedPath = writeNamed(migrate.NAMED_DIR, "acme", "four", {"id": "acme/four", "level": "3★", "timeline": [dict(legacy)]})

    monkeypatch.setattr(sys, "argv", ["migrate_taxonomy_v6.py", "--backfill-only", "--apply", "--batch", BATCH])
    assert migrate.main() == 0

    assert migrate._load_node(nodePath)["timeline"][0]["migrationBatch"] == BATCH
    assert migrate._load_named_skill(namedPath)[0]["timeline"][0]["migrationBatch"] == BATCH
    report = json.loads((migrate.OUT_DIR / "taxonomy_v6_report.json").read_text(encoding="utf-8"))
    assert report["backfillOnly"] is True and report["backfill"]["nodesUpgraded"] == 1
    assert "SUMMARY (backfill-only)" in capsys.readouterr().out

    # re-running is a no-op
    before = nodePath.read_bytes()
    monkeypatch.setattr(sys, "argv", ["migrate_taxonomy_v6.py", "--backfill-only", "--apply", "--batch", BATCH])
    assert migrate.main() == 0
    assert nodePath.read_bytes() == before
    assert json.loads((migrate.OUT_DIR / "taxonomy_v6_report.json").read_text(encoding="utf-8"))["backfill"]["nodesUpgraded"] == 0


def test_migrate_taxonomy_v6_default_main_is_a_dry_run_and_writes_report(migrate, monkeypatch, capsys):
    seedLegacyNodes(migrate.nodes)
    contents = {p: p.read_bytes() for p in migrate.nodes.rglob("*.json")}
    monkeypatch.setattr(sys, "argv", ["migrate_taxonomy_v6.py", "--batch", BATCH])

    assert migrate.main() == 0

    assert {p: p.read_bytes() for p in migrate.nodes.rglob("*.json")} == contents
    out = capsys.readouterr().out
    assert "(DRY-RUN)" in out and "Pass --apply to write changes." in out
    report = json.loads((migrate.OUT_DIR / "taxonomy_v6_report.json").read_text(encoding="utf-8"))
    assert report["mode"] == "DRY-RUN" and report["migrationBatch"] == BATCH
    rows = list(csv.DictReader((migrate.OUT_DIR / "taxonomy_v6_report.csv").open(encoding="utf-8")))
    assert {r["skillId"] for r in rows if r["event"] == "moved"} == {"beta", "gamma", "delta"}
    assert {r["skillId"] for r in rows if r["event"] == "anomaly"} == {"delta"}


def test_migrate_taxonomy_v6_help_exits_zero():
    proc = subprocess.run(
        [sys.executable, str(migrateScript), "--help"],
        capture_output=True, text=True, timeout=60, cwd=repoRoot,
    )
    assert proc.returncode == 0
    assert "--apply" in proc.stdout and "--backfill-only" in proc.stdout


# ---------------------------------------------------------------------------
# scripts/prepare_l4_october.py
# ---------------------------------------------------------------------------


@pytest.fixture
def l4(tmp_path, monkeypatch, isolatedPath):
    """prepare_l4_october re-pointed at a synthetic founder report tree under tmp_path."""
    module = loadScript(l4Script, "prepareL4OctoberUnderTest")
    report = tmp_path / "founder" / "reports" / "yggdrasil-iv-october-2026"
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "REPORT", report)
    monkeypatch.setattr(module, "PREP", report / "l4-preparation")
    monkeypatch.setattr(module, "RECEIPTS_DIR", report / "reconciliation" / "intake-receipts")
    (report / "reconciliation").mkdir(parents=True)
    return module


def buildL4Fixture(module, *, rowCount: int = 76):
    """Write a CAMPAIGN.md with `rowCount` choice rows plus a matching intake-triage.json."""
    rows = [("(7 parked drafts)", "approve", "", "")]
    for skill in module.OTHER_MAPS:
        rows.append((skill, "other", "", "founder note"))
    for skill in module.NEW:
        rows.append((skill, "new", "", ""))
    for skill in module.DEFAULT_APPROVE_MAPS:
        rows.append((skill, "approve", "", ""))
    rows.append(("zhaoxuya520/reverse-skill", "approve", "", ""))
    rows.append(("synthetic/declined-one", "decline", "", "Support skill, not a capability."))
    rows.append(("synthetic/declined-two", "decline", "", ""))
    rows.append(("synthetic/existing-one", "approve", "", ""))
    rows.append(("synthetic/frozen-one", "approve", "", ""))
    rows.append(("synthetic/no-source", "approve", "", ""))
    index = 0
    while len(rows) < rowCount:
        rows.append((f"synthetic/filler-{index:02d}", "approve", "", ""))
        index += 1
    rows = rows[:rowCount]

    table = "\n".join(f"| `{skill}` | {choice} | {generic} | {note} |" for skill, choice, generic, note in rows)
    campaign = (
        "# Campaign\n\nintro\n\n## L4 topology choices\n\n"
        "| Skill | Choice | Generic | Note |\n|---|---|---|---|\n"
        f"{table}\n\n## Founder rulings\n\nrulings text\n"
    )
    (module.REPORT / "CAMPAIGN.md").write_text(campaign, encoding="utf-8")

    items = []
    for skill, choice, _generic, _note in rows:
        if skill == "(7 parked drafts)":
            continue
        items.append({
            "skill": skill,
            "ref": f"#{100 + len(items)}",
            "source": None if skill == "synthetic/no-source" else f"https://github.com/synthetic/repo/blob/main/{skill.split('/')[-1]}/SKILL.md",
            "description": f"Synthetic description for {skill}.",
            "name": skill.split("/")[-1],
            "license": "MIT",
            "repoStars": 12,
            "receipts": {"prefill": None, "assessment": None},
            "disposition": "ready",
            "proposedGeneric": "synthetic-generic",
        })
    (module.REPORT / "reconciliation" / "intake-triage.json").write_text(json.dumps({"items": items}), encoding="utf-8")

    named = module.ROOT / "registry" / "named" / "synthetic"
    named.mkdir(parents=True, exist_ok=True)
    (named / "existing-one.md").write_text("---\nid: synthetic/existing-one\nlevel: 2★\n---\nbody\n", encoding="utf-8")
    (named / "frozen-one.md").write_text("---\nid: synthetic/frozen-one\nfrozen: true\nsuiteComponents: [a, b]\n---\nbody\n", encoding="utf-8")
    return rows


def test_prepare_l4_october_read_frontmatter(l4, tmp_path):
    good = tmp_path / "good.md"
    good.write_text("---\nid: a/b\nfrozen: true\n---\nbody\n", encoding="utf-8")
    assert l4.read_frontmatter(good) == {"id": "a/b", "frozen": True}
    for name, text in (("none.md", "no frontmatter\n"), ("open.md", "---\nid: a/b\nnever closed\n"), ("bad.md", "---\n: : :\n  - [\n---\n")):
        path = tmp_path / name
        path.write_text(text, encoding="utf-8")
        assert l4.read_frontmatter(path) == {}


def test_prepare_l4_october_parse_choices_and_row_count_guard(l4):
    buildL4Fixture(l4)
    choices = l4.parse_choices()
    assert len(choices) == 76
    first = choices[0]
    assert first == {"choiceId": "(7 parked drafts)", "founderChoice": "approve", "founderGeneric": None, "founderNote": None}
    other = next(c for c in choices if c["founderChoice"] == "other")
    assert other["founderNote"] == "founder note"
    assert {c["founderChoice"] for c in choices} == {"approve", "other", "new", "decline"}

    buildL4Fixture(l4, rowCount=75)
    with pytest.raises(SystemExit, match="Expected 76 human choice rows, found 75"):
        l4.parse_choices()


def test_prepare_l4_october_inventory_dispositions(l4):
    buildL4Fixture(l4)
    inv = l4.inventory()

    assert inv["contract"] == "yggiv-l4-decision-inventory-v1"
    assert inv["choiceRows"] == 76
    assert inv["concreteInventoryRows"] == 76 - 1 + len(l4.PARKED), "parked group expands to its named records"
    assert sum(inv["countsByFounderChoice"].values()) == 76
    assert inv["countsByFounderChoice"]["decline"] == 2

    byId = {item["skillId"]: item for item in inv["items"]}
    assert byId["k-dense-ai/pymc"]["disposition"] == "skip-existing"
    assert byId["anthropics/creating-financial-models"]["disposition"] == "approved-source-preparation"
    assert byId["synthetic/declined-one"]["disposition"] == "decline-support"
    assert byId["synthetic/declined-one"]["declineReason"] == "Support skill, not a capability."
    assert byId["synthetic/declined-two"]["declineReason"] == "Founder choice: decline; support skill."
    assert byId["synthetic/existing-one"]["disposition"] == "skip-existing" and byId["synthetic/existing-one"]["alreadyNamed"]
    assert byId["synthetic/frozen-one"]["disposition"] == "skip-frozen" and byId["synthetic/frozen-one"]["suiteComponentCount"] == 2
    assert byId["synthetic/filler-00"]["disposition"] == "approved-map" and byId["synthetic/filler-00"]["proposedGeneric"] == "synthetic-generic"
    firstOther = next(iter(l4.OTHER_MAPS))
    assert byId[firstOther]["proposedGeneric"] == l4.OTHER_MAPS[firstOther][0]
    firstNew = next(iter(l4.NEW))
    assert byId[firstNew]["disposition"] == "approved-new-generic" and byId[firstNew]["proposedGeneric"] == l4.NEW[firstNew]["id"]
    approve = next(iter(l4.DEFAULT_APPROVE_MAPS))
    assert byId[approve]["proposedGeneric"] == l4.DEFAULT_APPROVE_MAPS[approve][0]
    assert byId["zhaoxuya520/reverse-skill"]["proposedGeneric"] == l4.REVERSE_SKILL_METADATA["proposedGeneric"]

    import hashlib
    assert inv["sourceApproval"]["sha256"] == hashlib.sha256((l4.REPORT / "CAMPAIGN.md").read_bytes()).hexdigest()


def test_prepare_l4_october_inventory_rejects_choice_without_triage_record(l4):
    buildL4Fixture(l4)
    triagePath = l4.REPORT / "reconciliation" / "intake-triage.json"
    doc = json.loads(triagePath.read_text(encoding="utf-8"))
    doc["items"] = [i for i in doc["items"] if i["skill"] != "synthetic/filler-00"]
    triagePath.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(SystemExit, match="No original intake-triage record for synthetic/filler-00"):
        l4.inventory()


def test_prepare_l4_october_command_spine_covers_only_actionable_rows(l4):
    buildL4Fixture(l4)
    inv = l4.inventory()
    l4.PREP.mkdir(parents=True)  # main() creates this directory; the spine writer expects it to exist
    path = l4.generate_command_spine(inv)

    assert path == l4.PREP / "command-spine.sh"
    text = path.read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env bash") and "set -euo pipefail" in text
    assert path.stat().st_mode & 0o111, "spine must be executable"
    assert "--named --contributor synthetic --generic-ref synthetic-generic" in text
    assert "--id filler-00" in text
    # skipped and declined rows never get registration or evidence commands
    for skipped in ("existing-one", "frozen-one", "declined-one", "declined-two"):
        assert f"--id {skipped} " not in text
    assert "gh issue close" in text and "Declined at October 2026 L4 topology review" in text
    assert "GAIA dev fuse product-design-review" in text
    assert "--suite-ref garrytan/gbrain" in text
    assert "--type github-stars-own --stars 12" in text


def test_prepare_l4_october_main_writes_inventory_and_spine_only(l4, monkeypatch, capsys):
    buildL4Fixture(l4)
    monkeypatch.setattr(sys, "argv", ["prepare_l4_october.py"])
    l4.main()

    inventory = json.loads((l4.PREP / "decision-inventory.json").read_text(encoding="utf-8"))
    assert inventory["choiceRows"] == 76
    assert (l4.PREP / "command-spine.sh").is_file()
    assert not (l4.PREP / "packets").exists(), "no packets without --prepare"
    assert "Wrote command spine" in capsys.readouterr().out


def test_prepare_l4_october_prepare_flow_with_stubbed_cli(l4, monkeypatch, capsys):
    buildL4Fixture(l4)
    ratify = importlib.import_module("gaia_cli.commands.dev.ratify")
    monkeypatch.setattr(ratify, "buildGenericSnapshot", lambda root: {"generics": [], "snapshotId": "synthetic"})

    # one candidate already has a prefill receipt; the rest go through the stubbed CLI
    receiptDir = l4.RECEIPTS_DIR
    receiptDir.mkdir(parents=True)
    (receiptDir / "synthetic__filler-00.prefill.json").write_text(
        json.dumps({"source": {"contentSha256": "f" * 64, "fetchedAt": "2026-11-01T00:00:00Z"}, "mappingOptions": []}),
        encoding="utf-8",
    )

    calls: list[list[str]] = []

    def fakeRun(cmd, cwd=None, env=None, text=None, capture_output=None, **kwargs):
        calls.append(list(cmd))
        if "prefill" in cmd:
            packet = {"source": {"contentSha256": "a" * 64, "fetchedAt": "2026-11-02T00:00:00Z"}, "mappingOptions": []}
            return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(packet), stderr="")
        if "assess" in cmd:
            out = Path(cmd[cmd.index("--output") + 1])
            out.write_text(json.dumps({"advisory": True}), encoding="utf-8")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        raise AssertionError(f"unexpected subprocess: {cmd}")

    monkeypatch.setattr(l4.subprocess, "run", fakeRun)
    monkeypatch.setattr(sys, "argv", ["prepare_l4_october.py", "--prepare"])
    l4.main()

    captured = capsys.readouterr()
    assert "Preparation Summary" in captured.out
    assert "BLOCKED synthetic/no-source: no source URL" in captured.err
    prefillTargets = [c[c.index("prefill") + 1] for c in calls if "prefill" in c]
    assert "synthetic/filler-00" not in prefillTargets, "existing receipt is reused, not re-fetched"
    assert prefillTargets and all("--allow-stale" in c for c in calls if "prefill" in c)
    assert not any("--yes" in c or "calibrate" in " ".join(c) for c in calls), "no canonical mutation verbs"

    inventory = json.loads((l4.PREP / "decision-inventory.json").read_text(encoding="utf-8"))
    prepared = [i for i in inventory["items"] if i.get("preparedPacket")]
    assert prepared
    receiptItem = next(i for i in inventory["items"] if i["skillId"] == "synthetic/filler-00")
    assert receiptItem["preparedSourceSha256"] == "f" * 64
    firstNew = next(iter(l4.NEW))
    newPacket = json.loads((l4.PREP / "packets" / f"{firstNew.replace('/', '__')}.json").read_text(encoding="utf-8"))
    assert newPacket["decision"]["value"] == "NEW_GENERIC" and newPacket["artifactGate"] == "valid-skill"
    mapPacket = json.loads((l4.PREP / "packets" / "synthetic__filler-00.json").read_text(encoding="utf-8"))
    assert mapPacket["decision"] == {"value": "MAP", "reasonCode": "FOUNDER_L4_APPROVED_MAP_PREP", "genericId": "synthetic-generic"}
    assert (l4.PREP / "assessments" / "synthetic__filler-00.assessment.json").is_file()
    assert not (l4.ROOT / "generated-output" / "curation").exists(), "scratch output is cleaned up"
    skipped = {"synthetic/existing-one", "synthetic/frozen-one", "synthetic/declined-one"}
    assert not skipped & {i["skillId"] for i in prepared}


def test_prepare_l4_october_verify_packets_path(l4, monkeypatch, capsys):
    prefill = importlib.import_module("gaia_cli.prefill")
    adapter = importlib.import_module("gaia_cli.intakeAdapter")
    monkeypatch.setattr(prefill, "buildGenericSnapshot", lambda root: {"generics": ["g"]})
    verdicts = {"errors": []}
    monkeypatch.setattr(adapter, "validateL4Resolution", lambda doc, **kw: list(verdicts["errors"]))
    monkeypatch.setattr(prefill, "selfValidatePacket", lambda doc, **kw: [])

    packets = l4.PREP / "packets"
    packets.mkdir(parents=True)
    (packets / "a.json").write_text(json.dumps({"id": "a"}), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["prepare_l4_october.py", "--verify-packets"])

    l4.main()
    assert "Verified 1 L4 ratified packets with 0 errors." in capsys.readouterr().out

    verdicts["errors"] = ["bad mapping"]
    with pytest.raises(SystemExit, match="L4 packet verification failed"):
        l4.main()


# ---------------------------------------------------------------------------
# scripts/verify_review_findings.py
# ---------------------------------------------------------------------------
# The script is a self-contained probe suite: every probe builds its own throwaway
# repository under tempfile and asserts the post-remediation behaviour of
# gaia_cli.prefill / the fan-out reconciler. It never touches the live registry
# or the network, so running its real main() in-process is hermetic.


@pytest.fixture
def review(monkeypatch):
    monkeypatch.setattr(sys, "path", list(sys.path))  # the script inserts "src" at import
    module = loadScript(reviewScript, "verifyReviewFindingsUnderTest")
    module.RESULTS.clear()
    yield module
    module.RESULTS.clear()


def test_verify_review_findings_check_records_and_prints(review, capsys):
    review.check("good probe", True, "fine")
    review.check("bad probe", False)
    assert review.RESULTS == [("good probe", True, "fine"), ("bad probe", False, "")]
    out = capsys.readouterr().out
    assert "[PASS] good probe" in out and "fine" in out
    assert "[FAIL] bad probe" in out


def test_verify_review_findings_real_probes_all_pass(review, capsys):
    assert review.main() == 0

    assert len(review.RESULTS) >= 13
    failed = [label for label, ok, _detail in review.RESULTS if not ok]
    assert failed == []
    labels = " | ".join(label for label, _ok, _detail in review.RESULTS)
    for finding in ("symlinked", "FAN-OUT", "forged review-ready report"):
        assert finding in labels, f"probe for {finding!r} did not run"
    out = capsys.readouterr().out
    assert "All three reviewed findings are closed." in out
    assert f"{len(review.RESULTS)}/{len(review.RESULTS)} checks passed" in out


def test_verify_review_findings_main_reports_failure(review, monkeypatch, capsys):
    monkeypatch.setattr(review, "probe_symlinked_output_directory", lambda: review.check("synthetic failing probe", False, "boom"))
    monkeypatch.setattr(review, "probe_fanout_conflict_loss", lambda: review.check("synthetic passing probe", True))
    monkeypatch.setattr(review, "probe_row_to_packet_binding", lambda: None)

    assert review.main() == 1
    out = capsys.readouterr().out
    assert "1/2 checks passed" in out
    assert "FAILED: synthetic failing probe" in out
    assert "All three reviewed findings are closed." not in out


# ---------------------------------------------------------------------------
# scripts/crawlers/skillsmp/crawler.py
# ---------------------------------------------------------------------------


@pytest.fixture
def smp(isolatedPath):
    # Unbind any pre-existing common / common.* modules from sys.modules so the crawler
    # imports its own scripts/crawlers/common package rather than binding to an unrelated
    # pre-existing package on sys.path or in sys.modules.
    # The autouse isolatedPath fixture restores pre-existing bindings exactly at teardown.
    for name in list(sys.modules):
        if name == "common" or name.startswith("common."):
            del sys.modules[name]
    return loadScript(smpScript, "skillsmpCrawlerUnderTest")


def fakeHttp(smp, responses):
    """Stand-in for the `requests` module: replays `responses` and records calls."""
    import requests as realRequests

    seen: list = []
    queue = list(responses)

    def get(url, params=None, timeout=None):
        seen.append((url, params, timeout))
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    return SimpleNamespace(get=get, RequestException=realRequests.RequestException), seen


def response(status=200, payload=None, headers=None):
    return SimpleNamespace(status_code=status, headers=headers or {}, json=lambda: payload)


def test_skillsmp_crawler_extract_skill_info(smp):
    info = smp.extract_skill_info({
        "title": "Fallback Title", "description": "d" * 300, "starCount": 77,
        "categories": ["a", "b"], "link": "https://example.invalid/s", "skillMd": "# content",
    })
    assert info["name"] == "Fallback Title"
    assert len(info["description"]) == 200
    assert info["stars"] == 77 and info["categories"] == ["a", "b"]
    assert info["url"] == "https://example.invalid/s" and info["has_content"] is True

    bare = smp.extract_skill_info({"name": "Bare"})
    assert bare == {"name": "Bare", "description": "", "stars": 0, "categories": [], "url": "", "has_content": False}
    assert smp.extract_skill_info({"description": "nameless"}) is None


def test_skillsmp_crawler_client_search_shapes_and_budget(smp, monkeypatch, capsys):
    http, seen = fakeHttp(smp, [
        response(payload=[{"name": "listShape"}], headers={"X-RateLimit-Daily-Remaining": "33"}),
        response(payload={"skills": [{"name": "skillsKey"}]}),
        response(payload={"results": [{"name": "resultsKey"}]}),
        response(status=500),
    ])
    monkeypatch.setattr(smp, "requests", http)
    client = smp.SkillsMPClient()

    assert client.search("alpha") == [{"name": "listShape"}]
    assert "API budget remaining: 33" in capsys.readouterr().out
    assert client.search("beta") == [{"name": "skillsKey"}]
    assert client.search("gamma") == [{"name": "resultsKey"}]
    assert client.search("delta") == []
    assert client.requests_made == 4
    assert seen[0] == (f"{smp.BASE_URL}/skills/search", {"q": "alpha"}, smp.REQUEST_TIMEOUT)

    client.requests_made = client.max_requests
    with pytest.raises(smp.BudgetExhausted):
        client.search("never-sent")
    assert len(seen) == 4, "an exhausted budget must not issue a request"


def test_skillsmp_crawler_client_search_rate_limit_and_transport_errors(smp, monkeypatch):
    import requests as realRequests

    http, _seen = fakeHttp(smp, [response(status=429), realRequests.ConnectionError("down")])
    monkeypatch.setattr(smp, "requests", http)
    client = smp.SkillsMPClient()

    with pytest.raises(smp.BudgetExhausted, match="429"):
        client.search("limited")
    assert client.requests_made == 1
    assert client.search("flaky") == []
    assert client.requests_made == 2, "a failed request still spends budget"
    assert client.max_requests == smp.DAILY_BUDGET - smp.RESERVE_REQUESTS


def stubMain(smp, monkeypatch, searchImpl):
    state = {"calls": [], "slept": 0, "proposed": None}

    class FakeClient:
        requests_made = 0

        def search(self, query):
            state["calls"].append(query)
            FakeClient.requests_made += 1
            return searchImpl(len(state["calls"]), query)

    def fakeSleep(seconds):
        state["slept"] += 1

    def fakePropose(candidates, source):
        state["proposed"] = (list(candidates), source)
        return "proposals/skillsmp-test.json"

    monkeypatch.setattr(smp, "SkillsMPClient", FakeClient)
    monkeypatch.setattr(smp.time, "sleep", fakeSleep)
    monkeypatch.setattr(smp, "deduplicate", lambda candidates: list(candidates))
    monkeypatch.setattr(smp, "write_proposals", fakePropose)
    return state


def test_skillsmp_crawler_main_scores_dedups_and_proposes(smp, monkeypatch, capsys):
    strong = {"name": "Web Scraper Pro", "description": "scrapes pages", "stars": 64, "categories": ["web"], "skillMd": "# x", "url": "https://skillsmp.com/skills/web-scraper-pro"}
    weak = {"name": "Weak Entry", "description": "little evidence", "stars": 1}
    state = stubMain(smp, monkeypatch, lambda n, q: [strong, weak, {"description": "no name"}])

    smp.main()

    assert len(state["calls"]) == 40, "main searches the first 40 taxonomy keywords"
    assert state["slept"] == 40
    candidates, source = state["proposed"]
    assert source == "skillsmp"
    assert len(candidates) == 1, "identical hits across keywords collapse; the weak entry scores under the threshold"
    candidate = candidates[0]
    assert candidate["id"].endswith("-smp-web-scraper-pro")
    assert candidate["status"] == "provisional" and candidate["type"] == "basic"
    assert candidate["evidence"][0]["class"] == "C"
    assert candidate["evidence"][0]["source"] == "https://skillsmp.com/skills/web-scraper-pro"
    assert candidate["evidence"][0]["source_type"] == "skillsmp"
    out = capsys.readouterr().out
    assert "Raw candidates: 40" in out and "After dedup: 1" in out and "Output: proposals/skillsmp-test.json" in out


def test_skillsmp_crawler_main_stops_when_budget_exhausted(smp, monkeypatch, capsys):
    def search(n, query):
        if n == 3:
            raise smp.BudgetExhausted("Budget exhausted (3/50)")
        return []

    state = stubMain(smp, monkeypatch, search)
    smp.main()

    assert len(state["calls"]) == 3
    assert state["proposed"] is None
    out = capsys.readouterr().out
    assert "Budget exhausted (3/50)" in out and "No new candidates to propose." in out


def test_skillsmp_crawler_main_skips_proposals_when_everything_is_known(smp, monkeypatch, capsys):
    strong = {"name": "Known Skill", "description": "already in registry", "stars": 64, "categories": ["x"], "skillMd": "# x"}
    state = stubMain(smp, monkeypatch, lambda n, q: [strong])
    monkeypatch.setattr(smp, "deduplicate", lambda candidates: [])

    smp.main()

    assert state["proposed"] is None
    assert "No new candidates to propose." in capsys.readouterr().out
