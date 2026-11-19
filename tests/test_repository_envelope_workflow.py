"""Offline proof of consumer workflow isolation AND the native per-named approval/sync contract.

No canonical writes, remote gh or network access. Consumer workflows
(upstream-approve, upstream-reject, upstream-close-children) remain identical to
pinned main so no newly reachable unsafe write/dispatcher is exposed while
preserving the verbatim-active v2-off fallback. The native repository-envelope
per-named approval, actor, child-gate, hold, and real CLI sync contract is
exercised directly offline against temporary data and fake gh transport.
"""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
import yaml

from scripts.upstream_watcher import approval, batch, envelope, repository_batch as rb
from test_upstream_approve_workflow import run_step, world

ROOT = Path(__file__).resolve().parents[1]
PINNED_MAIN = "80fb535bb7d77840fe9a52be558e6127e03f3850"
CONSUMER_WORKFLOWS = (
    ".github/workflows/upstream-approve.yml",
    ".github/workflows/upstream-reject.yml",
    ".github/workflows/upstream-close-children.yml",
)


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


def _preflight_script():
    return """
set -euo pipefail
VIEW=$(gh issue view "$ISSUE_NUMBER" --json number,title,body,state,labels)
printf '%s' "$VIEW" | python3 -c '
import json, sys
from scripts.upstream_watcher.approval import PayloadError, verify_repository_target, workflow_payload
issue = json.load(sys.stdin)
try:
    workflow_payload(issue.get("body"), title=issue.get("title"))
    verify_repository_target(issue)
except PayloadError as exc:
    print(f"::error::{exc}", file=sys.stderr)
    sys.exit(1)
'
"""


def _extract_script():
    return """
set -euo pipefail
VIEW=$(gh issue view "$ISSUE_NUMBER" --json number,title,body,state,labels)
printf '%s' "$VIEW" | python3 -c '
import json, os, sys
from scripts.upstream_watcher.approval import PayloadError, workflow_payload
issue = json.load(sys.stdin)
try:
    payload, digest = workflow_payload(issue.get("body"), title=issue.get("title"))
except PayloadError as exc:
    print(f"::error::Payload integrity failure: {exc}", file=sys.stderr)
    sys.exit(1)
with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
    out.write(f"skill_id={payload[\"skillId\"]}\\n")
    out.write(f"new_version={payload[\"newVersion\"]}\\n")
    out.write(f"source_url={payload[\"sourceUrl\"]}\\n")
    out.write(f"released_at={payload[\"releasedAt\"]}\\n")
    out.write(f"mode={payload.get(\"findingType\", \"update\")}\\n")
    out.write(f"sync_mode={payload.get(\"mode\", \"version-only\")}\\n")
    out.write(f"payload_sha256={digest}\\n")
    out.write(f"payload={json.dumps(payload, separators=(\",\", \":\"))}\\n")
'
"""


def _reverify_script():
    return """
set -euo pipefail
VIEW=$(gh issue view "$ISSUE_NUMBER" --json number,title,body,state,labels)
COMMENTS=$(gh api --paginate "repos/gaia-research/gaia-skill-tree/issues/${ISSUE_NUMBER}/comments")
export VIEW COMMENTS
python3 -c '
import json, os, sys
from scripts.upstream_watcher.approval import (
    PayloadError, decode_pages, latest_approval_sha, verify_repository_target, workflow_payload,
)
issue = json.loads(os.environ["VIEW"])
comments = decode_pages(os.environ["COMMENTS"])
expected = os.environ["PAYLOAD_SHA"]
try:
    _payload, digest = workflow_payload(issue.get("body"), title=issue.get("title"))
    verify_repository_target(issue)
except PayloadError as exc:
    print(f"::error::{exc}", file=sys.stderr)
    sys.exit(1)
if digest != expected:
    print("::error::payload digest changed before sync", file=sys.stderr)
    sys.exit(1)
if latest_approval_sha(comments) != expected:
    print("::error::no approval record covers this payload", file=sys.stderr)
    sys.exit(1)
'
"""


def test_consumer_workflows_match_pinned_main_with_no_new_callable_paths():
    for rel in CONSUMER_WORKFLOWS:
        pinned = subprocess.check_output(["git", "show", f"{PINNED_MAIN}:{rel}"], cwd=ROOT, text=True)
        assert (ROOT / rel).read_text(encoding="utf-8") == pinned, f"{rel} diverged from pinned main"
    approve_doc = yaml.safe_load((ROOT / ".github/workflows/upstream-approve.yml").read_text(encoding="utf-8"))
    trigger = approve_doc.get("on", approve_doc.get(True))
    dispatch_inputs = trigger["workflow_dispatch"]["inputs"]
    for selector in ("named_skill_id", "finding_sha256", "approved_source_url"):
        assert selector not in dispatch_inputs
    assert not hasattr(approval, "verify_unaffected_legacy_target")


def test_offline_native_per_named_approval_and_real_cli_sync_mutate_only_selected_record(tmp_path):
    root, issue, payload, env = fixture_tree(tmp_path)
    sibling = root / "registry/named/fixture/b.md"
    before_b = sibling.read_bytes()

    preflight = run_step(phase(tmp_path, "preflight"), _preflight_script(), world(issue), env, cwd=root)
    assert preflight.code == 0, preflight.output
    assert all(call[0] == "api" or call[:2] == ["issue", "view"] for call in preflight.calls)
    assert not any(call[:2] in (["issue", "edit"], ["issue", "comment"], ["issue", "close"], ["pr", "create"])
                   for call in preflight.calls)

    # Actor authority uses the hardened allowlist / Verifier index contract (no bootstrap grant).
    assert approval.allowlisted("mbtiongson1", "User", 153011150) is True
    assert approval.allowlisted("mallory", "User", 2) is False
    assert approval.verifier_status(str(root / "registry/named-skills.json"), "mallory") == "deny-missing-index"

    selected = run_step(phase(tmp_path, "extract"), _extract_script(), world(issue), env, cwd=root)
    assert selected.code == 0, selected.output
    assert selected.outputs["skill_id"] == "fixture/a"
    assert json.loads(selected.outputs["payload"]) == payload["findings"][0]
    assert selected.outputs["payload_sha256"] == env["FINDING_SHA256"]
    assert selected.outputs["new_version"] == "v2.0.0"
    assert all(call[:2] == ["issue", "view"] for call in selected.calls)

    marker = approval.approval_marker(selected.outputs["payload_sha256"])
    assert env["FINDING_SHA256"] in marker
    assert payload["findings"][1]["payloadSha256"] not in marker
    comments = {"100": [{"id": 1, "body": marker,
                          "user": {"login": "github-actions[bot]", "type": "Bot"}}]}
    rechecked = run_step(phase(tmp_path, "reverify"), _reverify_script(),
                         world(issue, comment_rows=comments),
                         {**env, "PAYLOAD_SHA": env["FINDING_SHA256"]}, cwd=root)
    assert rechecked.code == 0, rechecked.output

    # Execute the real canonical CLI sync engine against the temporary fixture registry.
    sync_proc = subprocess.run(
        [sys.executable, "-m", "gaia_cli.main", "dev", "sync-upstream",
         selected.outputs["skill_id"],
         "--tag", selected.outputs["new_version"],
         "--source-url", selected.outputs["source_url"],
         "--released-at", selected.outputs["released_at"],
         "--user", "github-actions[bot]"],
        cwd=root,
        env={**os.environ, "PYTHONPATH": env["PYTHONPATH"], "GAIA_OPERATOR_OVERRIDE": "1"},
        capture_output=True, text=True, check=False,
    )
    assert sync_proc.returncode == 0, sync_proc.stdout + sync_proc.stderr
    text = (root / "registry/named/fixture/a.md").read_text(encoding="utf-8")
    assert "v2.0.0" in text and "upstream_synced" in text
    assert sibling.read_bytes() == before_b


@pytest.mark.parametrize("change", [
    {"NAMED_SKILL_ID": ""}, {"FINDING_SHA256": ""}, {"APPROVED_SOURCE_URL": ""},
    {"NAMED_SKILL_ID": "fixture/b"}, {"FINDING_SHA256": "0" * 64},
    {"NAMED_SKILL_ID": "fixture/a\nINJECT=1"}, {"EVENT_NAME": "issues"},
    {"INPUT_REFIRE": "true"},
    {"APPROVED_SOURCE_URL": "https://github.com/fixture/repository/releases/tag/v3.0.0"},
    {"APPROVED_SOURCE_URL": "https://github.com/fixture/repository/releases/tag/v2.0.0?evil=1"},
])
def test_native_extraction_fails_closed_for_missing_stale_or_malicious_selectors(tmp_path, change):
    root, issue, payload, env = fixture_tree(tmp_path)
    before = {p: p.read_bytes() for p in (root / "registry/named").rglob("*.md")}
    preflight = run_step(phase(tmp_path, "preflight"), _preflight_script(), world(issue),
                         {**env, **change}, cwd=root)
    assert preflight.code != 0 and "Traceback" not in preflight.output
    assert all(call[:2] == ["issue", "view"] for call in preflight.calls)
    result = run_step(phase(tmp_path, "extract"), _extract_script(), world(issue),
                      {**env, **change}, cwd=root)
    assert result.code != 0 and "skill_id" not in result.outputs
    assert "Traceback" not in result.output
    assert "Payload integrity failure" in result.output or "explicit" in result.output or "selector" in result.output
    assert {p: p.read_bytes() for p in before} == before
    assert not any(c[0] in {"pr", "workflow"} for c in result.calls)


def test_actor_guard_denies_self_declared_approval_and_unauthorized_skip(tmp_path):
    root, issue, payload, env = fixture_tree(tmp_path)
    payload["findings"][0]["approval"] = True  # untrusted data is never actor authority
    payload["findings"][0] = envelope.seal(payload["findings"][0])
    payload = envelope.seal(payload)
    issue["body"] = envelope.render(payload)
    index_path = str(root / "registry/named-skills.json")
    assert approval.allowlisted("mallory", "User", 2) is False
    assert approval.verifier_status(index_path, "mallory") == "deny-missing-index"
    events = [{"id": 1, "event": "labeled", "label": {"name": "skip-child-gate"},
               "actor": {"login": "mallory", "type": "User", "id": 2}}]
    assert approval.skip_label_authorized(events, index_path) is False


@pytest.mark.parametrize("child_owner", ["a", "b"])
def test_selected_finding_child_gate_reads_selected_rows_not_sibling_links(tmp_path, child_owner):
    root, issue, payload, env = fixture_tree(tmp_path)
    row = {"id": "fixture/repository:pending", "slug": "pending", "suggestedId": "fixture/pending",
           "evidenceUrl": "https://github.com/fixture/repository/blob/v2.0.0/skills/pending/SKILL.md",
           "status": "tracked", "child": 101, "firstSeenVersion": "v2.0.0", "lastSeenVersion": "v2.0.0"}
    index = 0 if child_owner == "a" else 1
    payload["findings"][index]["candidates"] = [row]
    payload["findings"][index] = envelope.seal(payload["findings"][index])
    payload = envelope.seal(payload)
    probed = []
    def state_of(child_number):
        probed.append(child_number)
        return batch.CHILD_OPEN
    unresolved = batch.unresolved_row_ids(payload["findings"][0], state_of)
    assert bool(unresolved) is (child_owner == "a")
    assert probed == ([101] if child_owner == "a" else [])


@pytest.mark.parametrize("earlier_kind", ["native", "legacy"])
def test_preflight_cannot_bypass_canonical_or_legacy_hold_with_a_later_payload(tmp_path, earlier_kind):
    root, issue, payload, env = fixture_tree(tmp_path)
    earlier = copy.deepcopy(issue)
    earlier["number"] = 42
    if earlier_kind == "legacy":
        previous = copy.deepcopy(payload["findings"][0])
        earlier["body"] = "<!-- gaia-upstream-payload\n" + json.dumps(previous) + "\n-->"
    result = run_step(phase(tmp_path, "preflight"), _preflight_script(), world(earlier, issue), env, cwd=root)
    assert result.code != 0 and "Traceback" not in result.output
    assert ("not the lowest canonical" if earlier_kind == "native" else "migration hold") in result.output
    assert not any(c[:2] in (["issue", "edit"], ["issue", "comment"]) for c in result.calls)


def test_b_approval_receipt_does_not_cover_selected_a(tmp_path):
    root, issue, payload, env = fixture_tree(tmp_path)
    b_sha = payload["findings"][1]["payloadSha256"]
    comments = {"100": [{"id": 1, "body": f"<!-- gaia-upstream-approval payload={b_sha} -->",
                          "user": {"login": "github-actions[bot]", "type": "Bot"}}]}
    result = run_step(phase(tmp_path, "reverify"), _reverify_script(),
                      world(issue, comment_rows=comments),
                      {**env, "PAYLOAD_SHA": env["FINDING_SHA256"]}, cwd=root)
    assert result.code != 0 and "no approval record covers this payload" in result.output
    assert not any(c[0] in {"pr", "workflow"} for c in result.calls)


def test_legacy_single_id_payload_is_held_in_native_approval_contract(tmp_path):
    root, issue, payload, env = fixture_tree(tmp_path)
    legacy_payload = copy.deepcopy(payload["findings"][0])
    legacy_issue = {"number": 200, "state": "open", "title": "[upstream] fixture/repository → v2.0.0",
                    "body": "<!-- gaia-upstream-payload\n" + json.dumps(legacy_payload) + "\n-->",
                    "labels": [{"name": "upstream:release"}, {"name": "upstream:approved"}]}
    result = run_step(phase(tmp_path, "legacy-hold"), _preflight_script(), world(legacy_issue),
                      {**env, "ISSUE_NUMBER": "200"}, cwd=root)
    assert result.code != 0 and "Traceback" not in result.output
    assert "migration" in result.output
    assert not any(c[:2] in (["issue", "edit"], ["issue", "comment"], ["issue", "close"]) for c in result.calls)


def test_watcher_workflow_fetches_pinned_commit_without_altering_diagnostics_or_permissions():
    doc = yaml.safe_load((ROOT / ".github/workflows/upstream-watcher.yml").read_text())
    assert doc["permissions"] == {"issues": "write", "contents": "read"}
    watcher_job = doc["jobs"]["watcher"]
    assert watcher_job["permissions"] == {"issues": "write", "contents": "read", "pull-requests": "read"}
    names = [s.get("name") for s in watcher_job["steps"]]
    assert "Fetch pinned historical authority commit" in names
    assert names.index("Checkout") < names.index("Fetch pinned historical authority commit") < names.index("Run upstream watcher")
    assert "Fetch pinned historical authority commit" not in [
        s.get("name") for s in doc["jobs"]["metadata-probe"]["steps"]]
    assert "Fetch pinned historical authority commit" not in [
        s.get("name") for s in doc["jobs"]["permission-ab-control"]["steps"]]
