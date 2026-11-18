"""Execute the real workflow extraction and sync step against temporary data.

No canonical writes, remote gh or Python/CLI argument stand-in. Existing gh-only
transport fake supplies issue data; the selected sync uses the real CLI engine.
"""
import copy
import json
import os
from pathlib import Path
import shutil

import pytest
import yaml

from scripts.upstream_watcher import envelope
from test_upstream_approve_workflow import run_step, world

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/upstream-approve.yml"


def step(name, job="approve"):
    job = yaml.safe_load(WORKFLOW.read_text())["jobs"][job]
    return next(s["run"] for s in job["steps"] if s.get("name") == name)


def fixture_tree(tmp_path):
    root = tmp_path / "checkout"
    root.mkdir()
    (root / "sitecustomize.py").write_text(
        'import socket, urllib.request\n'
        'def forbidden(*args, **kwargs):\n    raise AssertionError("offline workflow fixture attempted network")\n'
        'socket.socket.connect = forbidden\nsocket.socket.connect_ex = forbidden\nurllib.request.urlopen = forbidden\n'
        'from scripts.upstream_watcher import live\nlive.RETRY_SLEEP = lambda _: None\n')
    for folder in ("scripts/lib", "scripts/upstream_watcher"):
        target = root / folder
        target.mkdir(parents=True)
        for source in (ROOT / folder).glob("*.py"):
            shutil.copy(source, target / source.name)
    (root / "scripts/__init__.py").write_text("")
    shutil.copy(ROOT / "scripts/steward_issue_census.py", root / "scripts/steward_issue_census.py")
    config = ROOT / "scripts/upstream_watcher/legacy_plan_policy.json"
    shutil.copy(config, root / "scripts/upstream_watcher/legacy_plan_policy.json")
    record = Path(json.loads(config.read_text())["directionRecord"])
    (root / record).parent.mkdir(parents=True)
    shutil.copy(ROOT / record, root / record)
    named = root / "registry/named/fixture"
    named.mkdir(parents=True)
    authority = {}
    for slug in ("a", "b"):
        meta = {"id": f"fixture/{slug}", "name": f"Fixture {slug}", "contributor": "fixture",
                "title": f"The Fixture {slug}", "genericSkillRef": "fixture-skill", "status": "named", "origin": True,
                "level": "2★", "description": "A temporary workflow integration test fixture.",
                "links": {"github": "https://github.com/fixture/repository/blob/main/SKILL.md"},
                "createdAt": "2026-01-01", "updatedAt": "2026-01-01", "timeline": [],
                "upstream": {"repo": "fixture/repository", "version": "v1.0.0", "mode": "version-only",
                    "sourceUrl": "https://github.com/fixture/repository/releases/tag/v1.0.0",
                    "releasedAt": "2026-01-01T00:00:00Z", "syncedAt": "2026-01-01T00:00:00Z"}}
        authority[meta["id"]] = meta
        (named / f"{slug}.md").write_text("---\n" + yaml.safe_dump(meta, allow_unicode=True) + "---\n\nFixture body.\n")
    schema = root / "registry/schema"
    schema.mkdir()
    shutil.copy(ROOT / "registry/schema/namedSkill.schema.json", schema / "namedSkill.schema.json")
    (schema / "meta.json").write_text("{}")
    (root / "registry/nodes").mkdir()
    findings = [envelope.seal({"payloadVersion": 2, "skillId": identifier,
        "previousVersion": "v1.0.0", "newVersion": "v2.0.0",
        "releasedAt": "2026-11-20T00:00:00Z", "sourceUrl": "https://github.com/fixture/repository/releases/tag/v2.0.0",
        "mode": "version-only", "componentAdds": [], "componentRemoves": [], "linkLiveness": [],
        "nameDrift": [], "candidates": []}) for identifier in authority]
    payload = envelope.build("fixture/repository", findings, authority)
    issue = {"number": 100, "state": "open", "title": envelope.title(payload), "body": envelope.render(payload),
             "labels": [{"name": "upstream:release"}, {"name": "upstream:approved"}]}
    a = payload["findings"][0]
    env = {"EVENT_NAME": "workflow_dispatch", "INPUT_REFIRE": "false", "NAMED_SKILL_ID": a["skillId"],
           "FINDING_SHA256": a["payloadSha256"], "APPROVED_SOURCE_URL": a["sourceUrl"], "ISSUE_NUMBER": "100",
           "PYTHONPATH": os.pathsep.join([str(root), str(ROOT / "src")]), "GAIA_OPERATOR_OVERRIDE": "1"}
    return root, issue, payload, env


def phase(tmp_path, name):
    target = tmp_path / name
    target.mkdir()
    return target


def test_workflow_extraction_and_real_cli_sync_mutate_only_exact_selected_named_record(tmp_path):
    root, issue, payload, env = fixture_tree(tmp_path)
    sibling = root / "registry/named/fixture/b.md"
    before_b = sibling.read_bytes()
    preflight = run_step(phase(tmp_path, "preflight"),
        step("Verify repository-envelope selection before any approval-path write"), world(issue), env, cwd=root)
    assert preflight.code == 0, preflight.output
    authorized = run_step(phase(tmp_path, "authorize"), step("Check labeler is a Verifier"), world(issue),
        {**env, "LABELER": "mbtiongson1", "LABELER_TYPE": "User", "LABELER_ID": "153011150"}, cwd=root)
    assert authorized.code == 0, authorized.output
    assert all(c[:2] in (["issue", "view"], ["api", "repos/gaia-research/gaia-skill-tree/issues/100/events"])
               for c in authorized.calls)
    selected = run_step(phase(tmp_path, "extract"), step("Extract payload from issue body"), world(issue), env, cwd=root)
    assert selected.code == 0, selected.output
    assert selected.outputs["skill_id"] == "fixture/a"
    assert json.loads(selected.outputs["payload"]) == payload["findings"][0]
    assert selected.outputs["payload_sha256"] == env["FINDING_SHA256"]
    assert selected.outputs["new_version"] == "v2.0.0"
    assert all(call[:2] == ["issue", "view"] for call in selected.calls)
    approved = run_step(phase(tmp_path, "approve"), step("Check approval covers this payload"), world(issue),
        {**env, "PAYLOAD_SHA": selected.outputs["payload_sha256"]}, cwd=root)
    assert approved.code == 0, approved.output
    markers = [c for c in approved.calls if c[:2] == ["issue", "comment"]]
    assert len(markers) == 1 and env["FINDING_SHA256"] in markers[0][-1]
    assert payload["findings"][1]["payloadSha256"] not in markers[0][-1]
    comments = {"100": [{"id": 1, "body": markers[0][-1],
                          "user": {"login": "github-actions[bot]", "type": "Bot"}}]}
    rechecked = run_step(phase(tmp_path, "reverify"), step("Re-verify approval before sync"),
        world(issue, comment_rows=comments), {**env, "PAYLOAD_SHA": env["FINDING_SHA256"]}, cwd=root)
    assert rechecked.code == 0, rechecked.output
    sync_env = {**env, **{key.upper(): value for key, value in selected.outputs.items()},
                "SOURCE_URL": selected.outputs["source_url"], "RELEASED_AT": selected.outputs["released_at"]}
    synced = run_step(phase(tmp_path, "sync"), step("Run gaia dev sync-upstream"), world(issue), sync_env, cwd=root)
    assert synced.code == 0, synced.output
    text = (root / "registry/named/fixture/a.md").read_text()
    assert "v2.0.0" in text and "upstream_synced" in text
    assert sibling.read_bytes() == before_b
    assert synced.calls == []  # sync has no repowide/latest gh lookup


@pytest.mark.parametrize("change", [
    {"NAMED_SKILL_ID": ""}, {"FINDING_SHA256": ""}, {"APPROVED_SOURCE_URL": ""},
    {"NAMED_SKILL_ID": "fixture/b"}, {"FINDING_SHA256": "0" * 64},
    {"NAMED_SKILL_ID": "fixture/a\nINJECT=1"}, {"EVENT_NAME": "issues"},
    {"INPUT_REFIRE": "true"},
    {"APPROVED_SOURCE_URL": "https://github.com/fixture/repository/releases/tag/v3.0.0"},
    {"APPROVED_SOURCE_URL": "https://github.com/fixture/repository/releases/tag/v2.0.0?evil=1"},
])
def test_actual_workflow_extraction_fails_closed_for_missing_stale_or_malicious_selectors(tmp_path, change):
    root, issue, payload, env = fixture_tree(tmp_path)
    before = {p: p.read_bytes() for p in (root / "registry/named").rglob("*.md")}
    preflight = run_step(phase(tmp_path, "preflight"),
        step("Verify repository-envelope selection before any approval-path write"), world(issue),
        {**env, **change}, cwd=root)
    assert preflight.code != 0 and "Traceback" not in preflight.output
    assert all(call[:2] == ["issue", "view"] for call in preflight.calls)
    result = run_step(phase(tmp_path, "extract"), step("Extract payload from issue body"), world(issue),
                      {**env, **change}, cwd=root)
    assert result.code != 0 and "skill_id" not in result.outputs
    assert "Traceback" not in result.output
    assert "Payload integrity failure" in result.output or "explicit" in result.output or "selector" in result.output
    assert {p: p.read_bytes() for p in before} == before
    # A failure comment is not authority and never runs a CLI/branch/PR action.
    assert not any(c[0] in {"pr", "workflow"} for c in result.calls)


def test_new_inputs_do_not_change_actor_authority_or_permissions():
    doc = yaml.safe_load(WORKFLOW.read_text())
    job = doc["jobs"]["approve"]
    names = [s.get("name") for s in job["steps"]]
    assert names.index("Check labeler is a Verifier") < names.index("Extract payload from issue body")
    assert names.index("Check approval covers this payload") < names.index("Run gaia dev sync-upstream")
    assert doc["permissions"] == {"issues": "write", "contents": "write", "pull-requests": "write"}
    assert "permissions" not in job
    assert doc["jobs"]["legacy-approve"]["steps"][0]["name"] == "Repository-envelope compatibility hold"
    assert names.index("Verify repository-envelope selection before any approval-path write") < names.index("Check labeler is a Verifier")


def test_actual_actor_guard_denies_self_declared_approval_and_skip_bypass(tmp_path):
    root, issue, payload, env = fixture_tree(tmp_path)
    payload["findings"][0]["approval"] = True  # untrusted data is never actor authority
    payload["findings"][0] = envelope.seal(payload["findings"][0])
    payload = envelope.seal(payload)
    issue["body"] = envelope.render(payload)
    env["FINDING_SHA256"] = payload["findings"][0]["payloadSha256"]
    rejected = run_step(phase(tmp_path, "deny"), step("Check labeler is a Verifier"), world(issue),
        {**env, "LABELER": "mallory", "LABELER_TYPE": "User", "LABELER_ID": "2"}, cwd=root)
    assert rejected.code != 0 and "deny-missing-index" in rejected.output
    assert any("Authorization failure" in text for text in rejected.comments())
    assert not any(c[0] in {"pr", "workflow"} for c in rejected.calls)
    bypass = run_step(phase(tmp_path, "skip-deny"), step("Check skip-child-gate labeler", "skip-child-gate-guard"),
        world(issue), {**env, "LABELER": "mallory", "LABELER_TYPE": "User", "LABELER_ID": "2"}, cwd=root)
    assert bypass.code != 0
    assert any(c[:2] == ["issue", "edit"] and "--remove-label" in c for c in bypass.calls)


@pytest.mark.parametrize("child_owner", ["a", "b"])
def test_actual_child_gate_reads_selected_rows_not_sibling_links(tmp_path, child_owner):
    root, issue, payload, env = fixture_tree(tmp_path)
    row = {"id": "fixture/repository:pending", "slug": "pending", "suggestedId": "fixture/pending",
           "evidenceUrl": "https://github.com/fixture/repository/blob/v2.0.0/skills/pending/SKILL.md",
           "status": "tracked", "child": 101, "firstSeenVersion": "v2.0.0", "lastSeenVersion": "v2.0.0"}
    index = 0 if child_owner == "a" else 1
    payload["findings"][index]["candidates"] = [row]
    payload["findings"][index] = envelope.seal(payload["findings"][index])
    payload = envelope.seal(payload)
    issue["body"] = envelope.render(payload)
    child = {"number": 101, "state": "open", "title": "[intake] fixture/pending",
             "labels": [{"name": "upstream:child"}], "body": "No unscoped umbrella cross-link."}
    result = run_step(phase(tmp_path, "gate"), step("Check child gate"), world(issue, child),
        {**env, "SELECTED_PAYLOAD": json.dumps(payload["findings"][0])}, cwd=root)
    assert result.code == 0, result.output
    assert result.outputs["gate_passed"] == ("false" if child_owner == "a" else "true")
    child_gets = [c for c in result.calls if c[0] == "api" and c[-1].endswith("/issues/101")]
    assert bool(child_gets) is (child_owner == "a")


@pytest.mark.parametrize("earlier_kind", ["native", "legacy"])
def test_actual_preflight_cannot_bypass_canonical_or_legacy_hold_with_a_later_payload(tmp_path, earlier_kind):
    root, issue, payload, env = fixture_tree(tmp_path)
    earlier = copy.deepcopy(issue)
    earlier["number"] = 42
    if earlier_kind == "legacy":
        previous = copy.deepcopy(payload["findings"][0])
        earlier["body"] = "<!-- gaia-upstream-payload\n" + json.dumps(previous) + "\n-->"
    result = run_step(phase(tmp_path, "preflight"),
        step("Verify repository-envelope selection before any approval-path write"), world(earlier, issue), env, cwd=root)
    assert result.code != 0 and "Traceback" not in result.output
    assert ("not the lowest canonical" if earlier_kind == "native" else "migration hold") in result.output
    assert not any(c[:2] in (["issue", "edit"], ["issue", "comment"]) for c in result.calls)


def test_b_approval_receipt_does_not_cover_selected_a(tmp_path):
    root, issue, payload, env = fixture_tree(tmp_path)
    b_sha = payload["findings"][1]["payloadSha256"]
    comments = {"100": [{"id": 1, "body": f"<!-- gaia-upstream-approval payload={b_sha} -->",
                          "user": {"login": "github-actions[bot]", "type": "Bot"}}]}
    result = run_step(phase(tmp_path, "reverify"), step("Re-verify approval before sync"),
        world(issue, comment_rows=comments), {**env, "PAYLOAD_SHA": env["FINDING_SHA256"]}, cwd=root)
    assert result.code != 0 and "no approval record covers this payload" in result.output
    assert not any(c[0] in {"pr", "workflow"} for c in result.calls)
