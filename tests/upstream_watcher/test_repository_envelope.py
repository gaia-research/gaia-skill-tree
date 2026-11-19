"""Offline repository-envelope protocol/planner proofs; no canonical mutations."""
import copy
import hashlib
import json
import socket

import pytest

from scripts.upstream_watcher import batch, envelope as wire, repository_batch as rb
from scripts.upstream_watcher.approval import PayloadError
from scripts.upstream_watcher.live import read_live
from upstream_fakes import FakeGh


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("offline envelope test attempted network")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)


def authority():
    return {name: {"id": name, "suiteRef": "owner/a", "links": {"github": f"https://github.com/{repo}"}}
            for name, repo in [("owner/a", "owner/repo"), ("owner/b", "owner/repo"),
                               ("owner/nested", "owner/nested")]}


def finding(name="owner/a", version="v1", adds=("same",), repo="owner/repo"):
    return {"finding_type": "update", "skillId": name, "currentVersion": "v0", "newVersion": version,
            "sourceUrl": f"https://github.com/{repo}/releases/tag/{version}",
            "releasedAt": "2026-11-20T00:00:00Z", "mode": "components",
            "componentAdds": list(adds), "componentRemoves": [], "linkLiveness": [], "nameDrift": []}


def run(gh, findings=None, apply=False, **kwargs):
    return rb.run_repository_batch(findings or [finding(), finding("owner/b")], gh, apply, authority(),
                                   index_loader=lambda: {"byId": {}, "bySlug": {}}, policy={}, **kwargs)


def payloads():
    plans = [batch.plan_suite(finding(name), {"issues": [], "closedUmbrellas": []},
                             {"byId": {}, "bySlug": {}})["payload"] for name in ("owner/a", "owner/b")]
    for plan in plans:
        for row in plan["candidates"]:
            row["evidenceUrl"] = row["evidenceUrl"].replace("/blob/main/", "/blob/v1/")
        plan["payloadSha256"] = wire.canonical_hash(plan)
    return plans


def issue(payload, number=10, state="open"):
    return {"number": number, "state": state, "title": wire.title(payload),
            "body": wire.render(payload), "labels": ["upstream:release"]}


def test_two_named_findings_in_one_envelope_keep_exact_identity_and_digests():
    gh = FakeGh()
    report, code = run(gh)
    assert code == 0 and report["unknownEvidence"] == []
    assert report["issuesCreated"] == 1 and report["issuesUpdated"] == 0
    assert report["dryRun"] is True and gh.writes == []
    envelope = report["repositories"][0]["payload"]
    assert [f["skillId"] for f in envelope["findings"]] == ["owner/a", "owner/b"]
    assert all(f["payloadSha256"] == batch.canonical_hash(f) for f in envelope["findings"])
    assert wire.build("OWNER/REPO", reversed(envelope["findings"]), authority()) == envelope
    assert wire.scope_key("owner/a", "owner/repo:same") != wire.scope_key("owner/b", "owner/repo:same")


def test_nested_topology_does_not_change_own_release_repository():
    report, code = run(FakeGh(), [finding(), finding("owner/nested", repo="owner/nested")])
    assert code == 0
    assert [p["repository"] for p in report["repositories"]] == ["owner/nested", "owner/repo"]
    assert report["issuesCreated"] == 2


def test_native_envelope_apply_then_rerun_writes_one_umbrella_and_no_children():
    gh = FakeGh()
    report, code = run(gh, apply=True)
    assert code == 0 and len(gh.writes) == 1
    assert report["dryRun"] is False
    saved = copy.deepcopy(gh.issues)
    gh.writes.clear()
    again, code = run(gh, apply=True)
    assert code == 0 and gh.writes == [] and gh.issues == saved
    assert again["repositories"][0]["outcome"] == "noop"


def test_identical_duplicate_inputs_dedup_but_conflicts_fail_before_any_write():
    one = finding()
    gh = FakeGh()
    report, code = run(gh, [one, copy.deepcopy(one)])
    assert code == 0 and len(report["repositories"][0]["payload"]["findings"]) == 1
    conflict = {**one, "newVersion": "v2", "sourceUrl": "https://github.com/owner/repo/releases/tag/v2"}
    report, code = run(gh, [one, conflict], apply=True)
    assert code == 3 and report["unknownEvidence"] and gh.writes == []


@pytest.mark.parametrize("change", [
    lambda p: p.update(repository="foreign/repo"),
    lambda p: p["findings"][0].update(sourceUrl="https://github.com/foreign/repo/releases/tag/v1"),
    lambda p: p["findings"].append(copy.deepcopy(p["findings"][0])),
    lambda p: p["findings"][0].update(skillId="OWNER/a"),
    lambda p: p.update(envelopeVersion=999),
])
def test_corrupt_envelopes_are_unknown_not_legacy_holds(change):
    payload = wire.build("owner/repo", payloads(), authority())
    change(payload)
    payload = wire.seal(payload)
    # render intentionally doesn't validate: model a malicious body on GitHub.
    gh = FakeGh([{"number": 10, "state": "open", "title": "[upstream] owner/repo → v1",
                  "body": batch.payload_block(payload), "labels": ["upstream:release"]}])
    report, code = run(gh, apply=True)
    assert code == 3 and report["unknownEvidence"] and report["knownLegacyHolds"] == []
    assert gh.writes == []


@pytest.mark.parametrize("url", [
    "https://github.com.evil/owner/repo/releases/tag/v1",
    "https://github.com/owner/repo/releases/tag/v1?next=evil",
    "https://github.com/owner/repo/releases/tag/v1#evil",
    "https://github.com/owner/repo/releases/tag/v10",
    "https://user@github.com/owner/repo/releases/tag/v1",
    "https://github.com/owner/repo/blob/v1/README.md",
    "https://github.com/owner/repo/releases/tag/v1\nINJECT=x",
])
def test_release_url_injection_rejected(url):
    with pytest.raises(PayloadError):
        wire.release_repository(url, "v1")


def legacy_issue(name="owner/a", repo="owner/repo"):
    payload = {k: v for k, v in finding(name, repo=repo).items() if k not in {"finding_type", "currentVersion"}}
    payload["previousVersion"] = "v0"
    return {"number": 42, "state": "open", "title": f"[upstream] {repo} → v1",
            "body": "Original legacy history\n" + batch.payload_block(payload), "labels": ["upstream:release"]}


def test_valid_legacy_plan_is_lossless_digest_bound_and_apply_cannot_mutate():
    old = legacy_issue()
    gh = FakeGh([old])
    before = copy.deepcopy(gh.issues)
    report, code = run(gh, apply=True)
    assert code == 0 and report["unknownEvidence"] == []
    assert report["writeReadiness"] is False
    assert report["issuesUpdated"] == 1  # logical plan, not a physical mutator count
    assert gh.writes == [] and gh.issues == before
    hold = report["knownLegacyHolds"][0]
    assert hold["originalPayload"] == batch.parse_payload(old["body"])
    assert hold["bodySha256"] == hashlib.sha256(old["body"].encode()).hexdigest()
    assert hold["writeReadiness"] is False and hold["deploymentOrder"]
    assert [f["skillId"] for f in report["repositories"][0]["payload"]["findings"]] == ["owner/a", "owner/b"]


def test_foreign_legacy_needs_historical_authority_and_saved_plans_bind_raw_body():
    old = legacy_issue("owner/nested")
    policy = {"issueBodySha256": hashlib.sha256(old["body"].encode()).hexdigest()}
    history = {"owner/nested": {"id": "owner/nested", "links": {"github": "https://github.com/owner/repo"}}}
    gh = FakeGh([old])
    report, code = rb.run_repository_batch([finding(), finding("owner/b")], gh, True, authority(),
        policy=policy, historical_loader=lambda _: history,
        index_loader=lambda: {"byId": {}, "bySlug": {}})
    assert code == 0 and not report["writeReadiness"] and gh.writes == []
    assert report["knownLegacyHolds"][0]["legacyNamedId"] == "owner/nested"
    assert all(f["skillId"] != "owner/nested" for f in report["repositories"][0]["payload"]["findings"])
    old_plan = report["knownLegacyHolds"][0]
    assert wire.verify_migration_reference(old_plan, gh.issues[42])
    gh.issues[42]["body"] += "\nchanged"
    with pytest.raises(PayloadError, match="stale"):
        wire.verify_migration_reference(old_plan, gh.issues[42])
    # A new reference may describe valid historical data, but neither reference
    # nor the direction record can authorize its execution.
    report, code = rb.run_repository_batch([finding()], gh, True, authority(), policy=policy,
        historical_loader=lambda _: history, index_loader=lambda: {"byId": {}, "bySlug": {}})
    assert code == 0 and not report["writeReadiness"] and gh.writes == []
    assert report["knownLegacyHolds"][0]["bodySha256"] != old_plan["bodySha256"]


@pytest.mark.parametrize("body", ["not a payload", "<!-- gaia-upstream-payload\n{bad\n-->",
    '<!-- gaia-upstream-payload\n{"skillId":"unknown/name","newVersion":"v1",'
    '"sourceUrl":"https://github.com/owner/repo/releases/tag/v1"}\n-->'])
def test_malformed_or_unknown_legacy_claims_fail_closed(body):
    old = legacy_issue()
    old["body"] = body
    gh = FakeGh([old])
    report, code = run(gh, apply=True)
    assert code == 3 and report["knownLegacyHolds"] == [] and gh.writes == []


def test_historical_named_scope_also_holds_its_distinct_current_release_repository():
    old = legacy_issue("owner/nested")
    history = {"owner/nested": {"id": "owner/nested", "links": {"github": "https://github.com/owner/repo"}}}
    gh = FakeGh([old])
    report, code = rb.run_repository_batch([finding(), finding("owner/b"),
        finding("owner/nested", repo="owner/nested")], gh, True, authority(), policy={},
        historical_loader=lambda _: history, index_loader=lambda: {"byId": {}, "bySlug": {}})
    assert code == 0 and report["unknownEvidence"] == [] and gh.writes == []
    assert len(report["repositories"]) == 2 and len(report["knownLegacyHolds"]) == 1
    assert all(not p["writeReadiness"] for p in report["repositories"])
    assert report["issuesCreated"] == report["issuesUpdated"] == 1
    # --skill/one-scope polling cannot bypass the same historical named hold.
    limited, code = rb.run_repository_batch([finding("owner/nested", repo="owner/nested")], gh,
        True, authority(), policy={}, historical_loader=lambda _: history,
        index_loader=lambda: {"byId": {}, "bySlug": {}})
    assert code == 0 and not limited["writeReadiness"] and gh.writes == []


def test_lowest_canonical_legacy_cannot_be_bypassed_by_later_native_envelope():
    payload = wire.build("owner/repo", payloads(), authority())
    old = legacy_issue()
    old["number"] = 1
    gh = FakeGh([old, issue(payload, 10)])
    report, code = run(gh, apply=True)
    assert code == 0 and report["repositories"][0]["umbrella"] == 1
    assert report["duplicateOpenUmbrellas"][0]["duplicates"][0]["number"] == 10
    assert report["writeReadiness"] is False and gh.writes == []


def test_per_named_selector_requires_exact_id_digest_and_source():
    payload = wire.build("owner/repo", payloads(), authority())
    a, b = payload["findings"]
    body = wire.render(payload)
    selected, digest = wire.select(body, authority(), identifier=a["skillId"], digest=a["payloadSha256"],
                                   source=a["sourceUrl"], title_text=wire.title(payload))
    assert selected == a and digest != b["payloadSha256"]
    for identifier, sha, source in [("", a["payloadSha256"], a["sourceUrl"]),
        (a["skillId"], "", a["sourceUrl"]), (b["skillId"], a["payloadSha256"], a["sourceUrl"]),
        (a["skillId"], "0" * 64, a["sourceUrl"]),
        (a["skillId"], a["payloadSha256"], a["sourceUrl"] + "?evil=1")]:
        with pytest.raises(PayloadError):
            wire.select(body, authority(), identifier=identifier, digest=sha, source=source)


def test_processed_history_never_suppresses_a_sibling():
    payload = wire.build("owner/repo", [payloads()[0]], authority())
    gh = FakeGh([issue(payload, state="closed")])
    report, code = run(gh)
    assert code == 0
    plans = report["repositories"][0]["findings"]
    assert plans[0]["action"] == "suppressed-processed"
    assert plans[1]["action"] == "create"
    # A's unresolved rows are carried as A, never used as B's processed proof.
    assert [p["skillId"] for p in report["repositories"][0]["payload"]["findings"]] == ["owner/a", "owner/b"]


def test_sibling_carry_forward_is_never_imported():
    a, b = payloads()
    a["candidates"][0]["firstSeenVersion"] = "v0-a"
    a["candidates"][0]["evidenceUrl"] = a["candidates"][0]["evidenceUrl"].replace("/blob/v1/", "/blob/v0-a/")
    a = wire.seal(a)
    b["candidates"][0]["firstSeenVersion"] = "v0-b"
    b["candidates"][0]["evidenceUrl"] = b["candidates"][0]["evidenceUrl"].replace("/blob/v1/", "/blob/v0-b/")
    b = wire.seal(b)
    payload = wire.build("owner/repo", [a, b], authority())
    gh = FakeGh([issue(payload, state="closed")])
    report, code = run(gh, [finding("owner/a", "v2", adds=()), finding("owner/b", "v2", adds=())])
    assert code == 0
    a, b = report["repositories"][0]["payload"]["findings"]
    assert a["candidates"][0]["firstSeenVersion"] == "v0-a"
    assert b["candidates"][0]["firstSeenVersion"] == "v0-b"


def test_real_normal_transport_keeps_siblings_and_own_source_with_legacy_hold(monkeypatch, tmp_path):
    from scripts.lib import named_iterator
    from scripts.upstream_watcher import watcher
    from scripts.upstream_watcher.live import LiveGh
    from test_count_2278 import ConnectionRunner, mixedRows
    import subprocess
    import urllib.request

    named = tmp_path / "named"
    named.mkdir()
    for identifier, meta in authority().items():
        repo = wire.authority_repository(identifier, authority())
        (named / (identifier.replace("/", "-") + ".md")).write_text(
            f'---\nid: {identifier}\nname: Fixture\nlevel: "2★"\n'
            f'suiteRef: owner/a\nsuiteComponents: [owner/component]\n'
            f'links:\n  github: https://github.com/{repo}\n'
            f'upstream:\n  repo: {repo}\n  version: v0\n---\n', encoding="utf-8")
    monkeypatch.setattr(named_iterator, "_DEFAULT_NAMED_DIR", named)
    def release(url, **kwargs):
        repo = url.removeprefix("https://api.github.com/repos/").removesuffix("/releases/latest")
        assert repo in {"owner/repo", "owner/nested"}
        assert kwargs == {"strict": True}
        return {"tag_name": "v1", "published_at": "2026-11-20T00:00:00Z",
                "html_url": f"https://github.com/{repo}/releases/tag/v1"}
    monkeypatch.setattr(watcher, "fetch_json", release)
    def forbidden(*args, **kwargs):
        raise AssertionError("unexpected HTTP/network")
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    rows = mixedRows()
    old = legacy_issue()
    rows[0].update(title=old["title"], body=old["body"], labels=[{"name": "upstream:release"}])
    before = copy.deepcopy(rows)
    runner = ConnectionRunner(rows, open_count=226)
    def transport(args, **kwargs):
        assert args[:2] == ["gh", "api"]
        query = next((a for a in args if a.startswith("query=")), "")
        assert "mutation" not in query.lower()
        method_flag = next((flag for flag in ("--method", "-X") if flag in args), None)
        assert method_flag is None or args[args.index(method_flag) + 1] == "GET"
        return runner(args, **kwargs)
    monkeypatch.setattr(subprocess, "run", transport)
    monkeypatch.setattr(watcher, "LiveGh", LiveGh)
    target = tmp_path / "report.json"
    assert watcher.main(["--child-mode", "batch", "--dry-run", "--report", str(target)]) == 0
    report = json.loads(target.read_text())
    assert report["dryRun"] is True and report["unknownEvidence"] == []
    assert report["writeReadiness"] is False
    assert report["executionHold"] == "watcher-plan-only-guard-blocks-envelope-apply"
    assert len(report["observedFindings"]) == 3
    assert len(report["repositories"]) == 2 and len(report["suites"]) == 3
    repo = next(p for p in report["repositories"] if p["repository"] == "owner/repo")
    other = next(p for p in report["repositories"] if p["repository"] != "owner/repo")
    assert [f["skillId"] for f in repo["payload"]["findings"]] == ["owner/a", "owner/b"]
    assert len(repo["knownLegacyHolds"]) == 1 and repo["outcome"] == "held"
    assert other["outcome"] == "planned" and other["writeReadiness"] is False
    assert (report["issuesCreated"], report["issuesUpdated"]) == (1, 1)
    assert rows == before and runner.writes == []


def test_unsupported_fanout_execution_is_explicit_hold_not_legacy_fallback():
    gh = FakeGh()
    report, code = run(gh, apply=True, mode="fanout")
    assert code == 4 and not report["writeReadiness"] and gh.writes == []
    assert report["executionHold"] and report["repositories"][0]["executionHold"]
    assert report["actualIssuesCreated"] == 0 and report["actualIssuesUpdated"] == 0
    dry_report, dry_code = run(gh, apply=False, mode="fanout")
    assert dry_code == 0 and not dry_report["writeReadiness"] and dry_report["executionHold"]
    assert dry_report["actualIssuesCreated"] == 0 and dry_report["actualIssuesUpdated"] == 0


def test_shallow_clone_fetches_pinned_historical_authority_and_missing_pin_fails_closed(monkeypatch, tmp_path):
    import subprocess
    origin = tmp_path / "origin"
    origin.mkdir()
    def git(cwd, *args):
        return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    git(origin, "init", "-b", "main")
    git(origin, "config", "user.name", "Test")
    git(origin, "config", "user.email", "test@example.com")
    named_file = origin / "registry/named/owner/nested.md"
    named_file.parent.mkdir(parents=True)
    named_file.write_text(
        '---\nid: owner/nested\nname: Nested\nlinks:\n  github: https://github.com/owner/repo\n---\n',
        encoding="utf-8",
    )
    git(origin, "add", ".")
    git(origin, "commit", "-m", "pin")
    pinned = git(origin, "rev-parse", "HEAD").stdout.strip()
    named_file.write_text(
        '---\nid: owner/nested\nname: Nested\nlinks:\n  github: https://github.com/owner/nested\n---\n',
        encoding="utf-8",
    )
    git(origin, "add", ".")
    git(origin, "commit", "-m", "move")
    shallow = tmp_path / "shallow"
    git(tmp_path, "clone", "--depth=1", f"file://{origin}", str(shallow))
    monkeypatch.setattr(rb, "ROOT", shallow)
    monkeypatch.setattr(rb, "plan_policy", lambda: {
        "planPolicyVersion": 1, "planOnly": True,
        "directionRecord": "founder/reports/upstream-backlog-2026-11/P1_IDENTITY_FOUNDER_DECISIONS.json",
        "historicalAuthorityCommit": pinned,
    })
    with pytest.raises(PayloadError, match="unavailable"):
        rb.historical_authority("owner/nested")
    # Bounded exact-pin fetch recovers the historical blob without broadening to unrelated refs.
    git(shallow, "fetch", "--depth=1", "--no-tags", "origin", pinned)
    loaded = rb.historical_authority("owner/nested")
    assert loaded["owner/nested"]["links"]["github"] == "https://github.com/owner/repo"


def test_repo_rejected_label_on_closed_envelope_does_not_silently_settle_sibling_rows():
    """A repo-level upstream:rejected label on a closed envelope cannot settle sibling childless rows."""
    a_old = wire.seal({
        "payloadVersion": 2, "skillId": "owner/a", "previousVersion": "v1.0.0", "newVersion": "v1.1.0",
        "releasedAt": "2026-11-18T00:00:00Z", "sourceUrl": "https://github.com/owner/repo/releases/tag/v1.1.0",
        "mode": "version-only", "componentAdds": [], "componentRemoves": [], "linkLiveness": [],
        "nameDrift": [], "candidates": [{
            "id": "owner/repo:alpha", "slug": "alpha", "suggestedId": "owner/alpha",
            "evidenceUrl": "https://github.com/owner/repo/blob/v1.1.0/skills/alpha/SKILL.md",
            "status": "new", "child": None, "firstSeenVersion": "v1.1.0", "lastSeenVersion": "v1.1.0",
        }],
    })
    b_old = wire.seal({
        "payloadVersion": 2, "skillId": "owner/b", "previousVersion": "v1.0.0", "newVersion": "v1.1.0",
        "releasedAt": "2026-11-18T00:00:00Z", "sourceUrl": "https://github.com/owner/repo/releases/tag/v1.1.0",
        "mode": "version-only", "componentAdds": [], "componentRemoves": [], "linkLiveness": [],
        "nameDrift": [], "candidates": [{
            "id": "owner/repo:beta", "slug": "beta", "suggestedId": "owner/beta",
            "evidenceUrl": "https://github.com/owner/repo/blob/v1.1.0/skills/beta/SKILL.md",
            "status": "new", "child": None, "firstSeenVersion": "v1.1.0", "lastSeenVersion": "v1.1.0",
        }],
    })
    closed_env = wire.build("owner/repo", [a_old, b_old], authority())
    closed_issue = {
        "number": 55, "state": "closed", "title": wire.title(closed_env),
        "body": wire.render(closed_env),
        "labels": [{"name": "upstream:release"}, {"name": "upstream:rejected"}],
    }
    gh = FakeGh([closed_issue])
    # Only owner/a has a new release v2.0.0; owner/b is an unpolled sibling with a carried row.
    incoming_a = finding("owner/a", version="v2.0.0", adds=())
    report, code = run(gh, [incoming_a], apply=False, historical_loader=lambda _: {})
    assert code == 0 and report["unknownEvidence"] == []
    repo_plan = report["repositories"][0]
    by_id = {f["skillId"]: f for f in repo_plan["payload"]["findings"]}
    # Both incoming owner/a and unpolled sibling owner/b retain their childless rows as unresolved, NOT rejected.
    a_row = next(r for r in by_id["owner/a"]["candidates"] if r["id"] == "owner/repo:alpha")
    b_row = next(r for r in by_id["owner/b"]["candidates"] if r["id"] == "owner/repo:beta")
    assert a_row["status"] == "new" and "rejectedBy" not in a_row and a_row["carriedFrom"] == "#55"
    assert b_row["status"] == "new" and "rejectedBy" not in b_row and b_row["carriedFrom"] == "#55"
