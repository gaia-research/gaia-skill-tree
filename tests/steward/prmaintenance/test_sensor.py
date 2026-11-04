"""PR-maintenance sensor: observation, classification, and every way a pull request must NOT be called ready."""

from __future__ import annotations

import json

import pytest

from gaia_cli.steward.prmaintenance import evaluate as ev
from gaia_cli.steward.prmaintenance.producers import RegistryError, loadRegistry, matchProducer, parseRegistry
from gaia_cli.steward.prmaintenance.sensor import PrMaintenanceSensor
from gaia_cli.steward.primitives import SensorNotEvaluated, SensorUnavailable

from tests.steward.prmaintenance import helpers as h

NOW = "2026-11-04T18:30:00Z"


@pytest.fixture(scope="module")
def fx(tmp_path_factory):
    return h.makeRepo(tmp_path_factory.mktemp("sensor"))


def observe(fx, rows, **over):
    h.writeCensus(fx, h.census(rows, over.pop("tip", fx.base), **over))
    scan = PrMaintenanceSensor().scan_detailed(fx.root, NOW)
    return {o.observed_state["number"]: o for o in scan.observations}


def kind(fx, rows, number=2270, **over):
    return observe(fx, rows, **over)[number].kind


def docsRow(fx, **over):
    value = h.row(fx, fx.base, "2026-44", number=2235, author={"login": "mbtiongson1", "id": 153011150, "type": "User"},
                  headRef="docs/routines/064", labels=["human-proposal"], draft=False,
                  commits=[{"sha": fx.base, "authorLogin": "claude", "authorId": 81847, "authorType": "User", "committerLogin": "claude",
                            "committerName": "Claude", "parents": 1, "message": "docs"}],
                  files=[{"path": "docs/en/DOCS.md", "status": "modified", "additions": 2, "deletions": 1, "blobSha": "0" * 40}])
    value.update(over)
    return value


def test_valid_automated_pr_is_merge_ready_but_only_mechanically(fx):
    head = fx.head("2026-44")
    seen = observe(fx, [h.row(fx, head, "2026-44")])[2270]
    assert seen.kind == ev.KIND_MERGE
    assert seen.observed_state["authority"] == "B"
    assert {g["name"]: g["state"] for g in seen.observed_state["gates"]}["rendered-html"] == "pass"
    assert "independent verification is still required" in seen.observed_state["reasons"][0]


def test_forged_identity_is_provenance_unknown_never_ready(fx):
    head = fx.head("2026-44")
    forged = h.row(fx, head, "2026-44", author={"login": "github-actions", "id": 7, "type": "User"})
    assert kind(fx, [forged]) == ev.KIND_PROVENANCE
    wrongId = h.row(fx, head, "2026-44", author={"login": "github-actions[bot]", "id": 999, "type": "Bot"})
    assert kind(fx, [wrongId]) == ev.KIND_PROVENANCE


def test_fork_head_or_missing_label_is_forged(fx):
    head = fx.head("2026-44")
    assert kind(fx, [h.row(fx, head, "2026-44", headRepo="evil/gaia-skill-tree")]) == ev.KIND_PROVENANCE
    assert kind(fx, [h.row(fx, head, "2026-44", labels=[])]) == ev.KIND_PROVENANCE


def test_foreign_commit_in_a_bot_branch_is_provenance_failure(fx):
    head = fx.head("2026-44")
    commits = [{"sha": head, "authorLogin": "mallory", "authorId": 5, "authorType": "User", "committerLogin": "mallory",
                "committerName": "Mallory", "parents": 1, "message": "sneak"}]
    assert kind(fx, [h.row(fx, head, "2026-44", commits=commits)]) == ev.KIND_PROVENANCE


def test_founder_web_merge_commit_from_main_is_allowed(fx):
    head = fx.head("2026-44")
    commits = [h.row(fx, head, "2026-44")["commits"][0],
               {"sha": "b" * 40, "authorLogin": "mbtiongson1", "authorId": 1, "authorType": "User", "committerLogin": "web-flow",
                "committerName": "GitHub", "parents": 2, "verified": True, "message": "Merge branch 'main'"}]
    assert kind(fx, [h.row(fx, head, "2026-44", commits=commits)]) == ev.KIND_MERGE


def test_unknown_automation_producer_is_reported_human_pr_is_ignored(fx):
    head = fx.head("2026-44")
    bot = h.row(fx, head, "2026-44", number=3001, headRef="bot/crawl-things")
    human = h.row(fx, head, "2026-44", number=3002, headRef="feat/my-feature", author={"login": "someone", "id": 3, "type": "User"})
    seen = observe(fx, [bot, human])
    assert seen[3001].kind == ev.KIND_PROVENANCE
    assert 3002 not in seen


def test_draft_content_engine_pr_is_never_ready(fx):
    head = fx.head("2026-44")
    seen = observe(fx, [h.row(fx, head, "2026-44", draft=True)])[2270]
    assert seen.kind != ev.KIND_MERGE
    assert {g["name"]: g["state"] for g in seen.observed_state["gates"]}["draft"] == "fail"


def test_explicit_founder_hold_is_class_c_with_a_decision_target(fx):
    head = fx.head("2026-44")
    seen = observe(fx, [h.row(fx, head, "2026-44", labels=["content-engine", "needs-review"])])[2270]
    assert seen.kind == ev.KIND_FOUNDER and seen.observed_state["authority"] == "C"
    assert seen.observed_state["decisionTarget"] == "routine-pr/gaia-research/gaia-skill-tree/2270"
    assert "Steward will not merge or close" in seen.observed_state["question"]


def test_maintainer_steward_hold_comment_is_a_hold_but_a_stranger_cannot_hold(fx):
    head = fx.head("2026-44")
    held = [{"id": 1, "user": "mbtiongson1", "body": "steward-hold: wait for me", "authorAssociation": "MEMBER"}]
    assert kind(fx, [h.row(fx, head, "2026-44", comments=held)]) == ev.KIND_FOUNDER
    stranger = [{"id": 2, "user": "rando", "body": "steward-hold", "authorAssociation": "NONE"}]
    assert kind(fx, [h.row(fx, head, "2026-44", comments=stranger)]) == ev.KIND_MERGE


def test_changes_requested_is_a_hold(fx):
    head = fx.head("2026-44")
    reviews = [{"user": "mbtiongson1", "state": "CHANGES_REQUESTED", "commitId": head, "authorAssociation": "MEMBER", "submittedAt": "2026-11-04T10:00:00Z"}]
    assert kind(fx, [h.row(fx, head, "2026-44", reviews=reviews)]) == ev.KIND_FOUNDER


def test_failed_ci_is_verification_failed_and_unrun_ci_is_blocked_not_ready(fx):
    head = fx.head("2026-44")
    failing = h.passing()
    failing[0] = {**failing[0], "conclusion": "failure"}
    assert kind(fx, [h.row(fx, head, "2026-44", checkRuns=failing)]) == ev.KIND_VERIFY
    assert kind(fx, [h.row(fx, head, "2026-44", checkRuns=[])]) == ev.KIND_BLOCKED
    running = [{**r, "status": "in_progress", "conclusion": None} for r in h.passing()]
    assert kind(fx, [h.row(fx, head, "2026-44", checkRuns=running)]) == ev.KIND_BLOCKED


def test_missing_required_approval_on_docs_routine_escalates_to_class_c(fx):
    seen = observe(fx, [docsRow(fx)])[2235]
    assert seen.kind == ev.KIND_FOUNDER
    assert {g["name"]: g["state"] for g in seen.observed_state["gates"]}["approvals"] == "fail"


def test_draft_docs_routine_is_a_founder_hold_never_consent(fx):
    seen = observe(fx, [docsRow(fx, draft=True, labels=["human-proposal", "needs-review"])])[2235]
    assert seen.kind == ev.KIND_FOUNDER
    assert "never read as consent" in " ".join(seen.observed_state["reasons"])


def test_approved_docs_routine_still_needs_independent_accuracy_verification(fx):
    reviews = [{"user": "mbtiongson1", "state": "APPROVED", "commitId": fx.base, "authorAssociation": "MEMBER", "submittedAt": "2026-11-04T10:00:00Z"}]
    seen = observe(fx, [docsRow(fx, reviews=reviews)])[2235]
    assert seen.kind == ev.KIND_BLOCKED
    assert {g["name"]: g["state"] for g in seen.observed_state["gates"]}["docs-accuracy"] == "unknown"


def test_approval_on_an_older_head_does_not_count(fx):
    reviews = [{"user": "mbtiongson1", "state": "APPROVED", "commitId": "c" * 40, "authorAssociation": "MEMBER", "submittedAt": "2026-11-04T10:00:00Z"}]
    assert kind(fx, [docsRow(fx, reviews=reviews)], 2235) == ev.KIND_FOUNDER


def test_unexpected_protected_file_mutation_is_refused_and_not_reconcilable(fx):
    head = fx.head("2026-44", extraFile=".github/workflows/evil.yml")
    seen = observe(fx, [h.row(fx, head, "2026-44")])[2270]
    assert seen.kind == ev.KIND_VERIFY
    assert {g["name"]: g["state"] for g in seen.observed_state["gates"]}["scope"] == "fail"
    assert seen.observed_state["reconcile"] is None


def test_removing_a_historical_report_is_a_scope_failure(fx):
    head = fx.head("2026-44")
    files = h.filesOf(fx, head) + [{"path": "docs/reports/2026-43/index.html", "status": "removed", "additions": 0, "deletions": 5, "blobSha": "0" * 40}]
    seen = observe(fx, [h.row(fx, head, "2026-44", files=files)])[2270]
    assert {g["name"]: g["state"] for g in seen.observed_state["gates"]}["scope"] == "fail"


def test_conflicting_shared_index_that_drops_history_fails_but_is_reconcilable(fx):
    head = fx.head("2026-44", dropIndexRow="2026-43")
    seen = observe(fx, [h.row(fx, head, "2026-44")])[2270]
    assert seen.kind == ev.KIND_VERIFY
    assert {g["name"]: g["state"] for g in seen.observed_state["gates"]}["index-rebuild"] == "fail"
    assert seen.observed_state["reconcile"] == "content-engine-cachebust"


def test_github_reported_conflict_is_conflict_kind(fx):
    head = fx.head("2026-44")
    assert kind(fx, [h.row(fx, head, "2026-44", mergeable=False, mergeableState="dirty")]) == ev.KIND_CONFLICT


def test_tampered_html_is_not_a_template_instance_and_not_reconcilable(fx):
    head = fx.head("2026-44", tamper=True)
    seen = observe(fx, [h.row(fx, head, "2026-44")])[2270]
    states = {g["name"]: g["state"] for g in seen.observed_state["gates"]}
    assert states["rendered-html"] == "fail" and states["rendered-surface"] == "fail"
    assert seen.kind == ev.KIND_FOUNDER  # a design change is a founder gate, never a Steward merge
    assert seen.observed_state["reconcile"] is None


def test_stale_version_stamps_and_stale_base_are_reconcilable_not_ready(fx):
    head = fx.head("2026-44", version="8.29.1")
    seen = observe(fx, [h.row(fx, head, "2026-44", baseSha="e" * 40)])[2270]
    states = {g["name"]: g["state"] for g in seen.observed_state["gates"]}
    assert states["cache-bust-current"] == "fail" and states["base-currency"] == "fail"
    assert seen.kind == ev.KIND_VERIFY and seen.observed_state["reconcile"] == "content-engine-cachebust"


def test_old_report_after_a_newer_one_passes_only_when_history_is_preserved(tmp_path):
    fx = h.makeRepo(tmp_path, labels=("2026-42", "2026-44"))
    good = fx.head("2026-43")
    assert kind(fx, [h.row(fx, good, "2026-43")]) == ev.KIND_MERGE
    bad = fx.head("2026-43", dropIndexRow="2026-44")
    seen = observe(fx, [h.row(fx, bad, "2026-43")])[2270]
    assert seen.kind == ev.KIND_VERIFY
    assert {g["name"]: g["state"] for g in seen.observed_state["gates"]}["index-rebuild"] == "fail"


def test_label_mismatch_between_branch_and_report_fails_the_canonical_json(tmp_path):
    fx = h.makeRepo(tmp_path)
    head = fx.head("2026-44", name="docs/content-engine-2026-45")
    seen = observe(fx, [h.row(fx, head, "2026-45", files=h.filesOf(fx, head))])[2270]
    assert seen.kind != ev.KIND_MERGE


def closedReplacement(number, original):
    return {"number": number, "state": "closed", "mergedAt": "2026-11-04T17:59:00Z", "mergeCommitSha": "d" * 40,
            "headRef": f"steward/b/pr-{original}", "title": "replacement", "closedAt": "2026-11-04T18:00:00Z",
            "body": f"Replaces the original.\n<!-- gaia-steward:replaces repo={h.REPO} pr={original} -->"}


def test_superseded_pr_with_merged_marked_replacement_and_identical_payload_is_closure_ready(tmp_path):
    fx = h.makeRepo(tmp_path, labels=("2026-42", "2026-43", "2026-44"))
    head = fx.head("2026-44")  # same payload as the base's published 2026-44
    seen = observe(fx, [h.row(fx, head, "2026-44")], closed=[closedReplacement(2400, 2270)])[2270]
    assert seen.kind == ev.KIND_CLOSURE
    assert seen.observed_state["closureReason"] == "label-already-published" and seen.observed_state["replacement"] == 2400


def test_superseded_without_a_merged_replacement_or_with_changed_payload_is_not_closure_ready(tmp_path):
    fx = h.makeRepo(tmp_path, labels=("2026-42", "2026-43", "2026-44"))
    head = fx.head("2026-44")
    assert kind(fx, [h.row(fx, head, "2026-44")]) == ev.KIND_SUPERSEDED
    fx.branch("docs/content-engine-2026-44")
    path = fx.root / "docs/api/v1/reports/2026-44.json"
    path.write_text(path.read_text(encoding="utf-8").replace("2026-10-", "2026-09-"), encoding="utf-8")
    different = fx.commit("changed payload")
    # a changed payload is never closable: the HTML no longer matches its JSON, which is a founder gate, not a closure
    assert kind(fx, [h.row(fx, different, "2026-44")], closed=[closedReplacement(2400, 2270)]) in (ev.KIND_SUPERSEDED, ev.KIND_FOUNDER)


def test_duplicate_open_pr_for_the_same_report_is_superseded_not_ready(fx):
    head = fx.head("2026-44")
    older = h.row(fx, head, "2026-44", number=2157)
    newer = h.row(fx, head, "2026-44", number=2300)
    seen = observe(fx, [older, newer])
    assert seen[2157].kind == ev.KIND_MERGE
    assert seen[2300].kind == ev.KIND_SUPERSEDED and seen[2300].observed_state["closureReason"] == "duplicate-of-open-sibling"


def test_invalid_and_stale_census_never_yields_debt_or_health(fx):
    head = fx.head("2026-44")
    rows = [h.row(fx, head, "2026-44")]
    with pytest.raises(SensorUnavailable, match="stale"):
        observe(fx, rows, fetched="2026-11-04T10:00:00Z")
    with pytest.raises(SensorUnavailable, match="incomplete"):
        observe(fx, rows, completeness={"pulls": {"complete": False, "pagesFetched": 1, "expectedPages": 2, "itemCount": 1},
                                        "details": {"complete": True, "expected": 1, "fetched": 1}})
    with pytest.raises(SensorUnavailable, match="duplicate"):
        observe(fx, rows + rows, completeness=h.census(rows * 2, fx.base)["completeness"])
    tampered = h.row(fx, head, "2026-44")
    tampered["bodySha256"] = "0" * 64
    with pytest.raises(SensorUnavailable, match="body-sha256"):
        observe(fx, [tampered])
    with pytest.raises(SensorUnavailable, match="schema"):
        observe(fx, rows, schemaVersion="steward-pr-census-v0")
    with pytest.raises(SensorUnavailable, match="details"):
        observe(fx, rows, completeness={**h.census(rows, fx.base)["completeness"], "details": {"complete": False, "expected": 1, "fetched": 0}})


def test_census_missing_is_not_evaluated_never_healthy(fx):
    path = fx.root / ".gaia/steward/inputs/github-prs.json"
    path.unlink(missing_ok=True)
    with pytest.raises(SensorNotEvaluated):
        PrMaintenanceSensor().scan_detailed(fx.root, NOW)


def test_deferred_repository_is_refused_and_unknown_never_healthy(fx):
    head = fx.head("2026-44")
    with pytest.raises(SensorUnavailable, match="not an enabled"):
        observe(fx, [h.row(fx, head, "2026-44")], repo="gaia-research/gaia-skill-heaven")
    registry = loadRegistry(fx.root)
    assert registry.deferredFor("gaia-research/gaia-skill-heaven") is not None
    assert matchProducer(registry, "gaia-research/gaia-skill-heaven", h.row(fx, head, "2026-44")).status == "deferred"
    seen = observe(fx, [h.row(fx, head, "2026-44")])[2270]
    assert seen.provenance["deferredRepos"] == [{"repo": "gaia-research/gaia-skill-heaven", "coverage": "unknown"}]
    assert seen.provenance["organisationWideDiscovery"] == "deferred"


def test_registry_never_represents_squash_or_unscoped_enablement():
    raw = json.loads((h.SOURCE / "founder/steward/pr-producers.json").read_text(encoding="utf-8"))
    raw["producers"][0]["mergeMethod"] = "squash"
    with pytest.raises(RegistryError, match="squash"):
        parseRegistry(raw)
    raw = json.loads((h.SOURCE / "founder/steward/pr-producers.json").read_text(encoding="utf-8"))
    raw["producers"][0]["repo"] = "gaia-research/elsewhere"
    with pytest.raises(RegistryError, match="outside scope"):
        parseRegistry(raw)
    raw = json.loads((h.SOURCE / "founder/steward/pr-producers.json").read_text(encoding="utf-8"))
    raw["scope"]["enabledRepos"].append("gaia-research/gaia-skill-heaven")
    with pytest.raises(RegistryError, match="both enabled and deferred"):
        parseRegistry(raw)


def test_observation_is_stable_and_idempotent(fx):
    head = fx.head("2026-44")
    rows = [h.row(fx, head, "2026-44")]
    first = observe(fx, rows)[2270]
    second = observe(fx, rows)[2270]
    assert first.debt_id == second.debt_id
    assert first.observed_state["evaluationSha256"] == second.observed_state["evaluationSha256"]


def withCommits(fx, head, commits, **over):
    return h.row(fx, head, "2026-44", commits=commits, **over)


def botCommit(head, **over):
    value = {"sha": head, "authorLogin": h.BOT["login"], "authorId": h.BOT["id"], "authorType": "Bot", "committerLogin": h.BOT["login"],
             "committerName": h.BOT["login"], "parents": 1, "message": "feat\n\nAuto-generated by .github/workflows/weekly-content-engine.yml."}
    value.update(over)
    return value


def test_a_merge_commit_needs_a_web_flow_login_and_a_verified_signature_never_a_free_text_name(fx):
    head = fx.head("2026-44")
    spoof = {"sha": "b" * 40, "authorLogin": "mallory", "authorId": 5, "authorType": "User", "committerLogin": None, "committerName": "GitHub",
             "parents": 2, "verified": False, "message": "Merge"}
    assert kind(fx, [withCommits(fx, head, [botCommit(head), spoof])]) == ev.KIND_PROVENANCE
    unsigned = {**spoof, "committerLogin": "web-flow", "verified": False}
    assert kind(fx, [withCommits(fx, head, [botCommit(head), unsigned])]) == ev.KIND_PROVENANCE
    signed = {**spoof, "committerLogin": "web-flow", "verified": True}
    assert kind(fx, [withCommits(fx, head, [botCommit(head), signed])]) == ev.KIND_MERGE


def test_no_commit_evidence_or_the_wrong_commit_identity_type_or_workflow_is_a_provenance_failure(fx):
    head = fx.head("2026-44")
    assert kind(fx, [withCommits(fx, head, [])]) == ev.KIND_PROVENANCE  # missing evidence never passes vacuously
    assert kind(fx, [withCommits(fx, head, [botCommit(head, authorType="User")])]) == ev.KIND_PROVENANCE
    assert kind(fx, [withCommits(fx, head, [botCommit(head, authorId=999)])]) == ev.KIND_PROVENANCE
    assert kind(fx, [withCommits(fx, head, [botCommit(head, message="feat: weekly report from some other workflow")])]) == ev.KIND_PROVENANCE


def test_unresolved_review_threads_block_and_unknown_threads_are_never_zero(fx):
    head = fx.head("2026-44")
    assert kind(fx, [h.row(fx, head, "2026-44", reviewThreadsUnresolved=2)]) == ev.KIND_FOUNDER
    unknown = observe(fx, [h.row(fx, head, "2026-44", reviewThreadsUnresolved=None)])[2270]
    assert unknown.kind == ev.KIND_BLOCKED and {g["name"]: g["state"] for g in unknown.observed_state["gates"]}["review-threads"] == "unknown"


def test_an_untrusted_approver_cannot_satisfy_a_required_approval_and_labels_match_case_insensitively(fx):
    stranger = [{"user": "rando", "state": "APPROVED", "commitId": fx.base, "authorAssociation": "NONE", "submittedAt": "2026-11-04T10:00:00Z"}]
    assert kind(fx, [docsRow(fx, reviews=stranger)], 2235) == ev.KIND_FOUNDER
    head = fx.head("2026-44")
    assert kind(fx, [h.row(fx, head, "2026-44", labels=["content-engine", "NEEDS-REVIEW"])]) == ev.KIND_FOUNDER


def test_a_hold_in_a_trusted_review_body_counts_and_only_the_registered_apps_checks_count(fx):
    head = fx.head("2026-44")
    review = [{"user": "mbtiongson1", "state": "COMMENTED", "commitId": head, "authorAssociation": "MEMBER", "submittedAt": "2026-11-04T10:00:00Z",
               "body": "steward-hold until Friday"}]
    assert kind(fx, [h.row(fx, head, "2026-44", reviews=review)]) == ev.KIND_FOUNDER
    spoofed = [{**r, "app": "some-other-app"} for r in h.passing()]
    assert kind(fx, [h.row(fx, head, "2026-44", checkRuns=spoofed)]) == ev.KIND_BLOCKED  # a lookalike check never satisfies a required one


def test_a_check_still_running_is_unknown_and_a_removed_historical_file_is_refused_per_status(fx):
    head = fx.head("2026-44")
    running = [{**h.passing()[0], "status": "queued", "conclusion": None}, h.passing()[1]]
    seen = observe(fx, [h.row(fx, head, "2026-44", checkRuns=running)])[2270]
    assert {g["name"]: g["state"] for g in seen.observed_state["gates"]}["ci:Schema + DAG + Integrity Checks"] == "unknown"
    renamed = h.filesOf(fx, head) + [{"path": "docs/reports/2026-42/index.html", "status": "renamed", "additions": 0, "deletions": 0, "blobSha": "0" * 40}]
    assert {g["name"]: g["state"] for g in observe(fx, [h.row(fx, head, "2026-44", files=renamed)])[2270].observed_state["gates"]}["scope"] == "fail"


def test_protected_paths_are_refused_even_when_they_overlap_an_allowed_pattern(fx):
    head = fx.head("2026-44")
    overlap = h.filesOf(fx, head) + [{"path": "docs/js/site-nav.js", "status": "modified", "additions": 1, "deletions": 0, "blobSha": "0" * 40}]
    seen = observe(fx, [h.row(fx, head, "2026-44", files=overlap)])[2270]
    assert {g["name"]: g["state"] for g in seen.observed_state["gates"]}["scope"] == "fail" and seen.kind == ev.KIND_VERIFY


def test_a_superseded_marker_must_match_the_pull_request_number_exactly(tmp_path):
    fx = h.makeRepo(tmp_path, labels=("2026-42", "2026-43", "2026-44"))
    head = fx.head("2026-44")
    wrong = {"number": 2400, "state": "closed", "mergedAt": "2026-11-04T17:59:00Z", "mergeCommitSha": "d" * 40, "headRef": "steward/b/x",
             "title": "r", "closedAt": "2026-11-04T18:00:00Z", "body": f"<!-- gaia-steward:replaces repo={h.REPO} pr=22700 head=abcdef123456 -->"}
    assert kind(fx, [h.row(fx, head, "2026-44", number=2270)], closed=[wrong]) == ev.KIND_SUPERSEDED  # pr=22700 is not pr=2270
    prefix = {**wrong, "body": f"<!-- gaia-steward:replaces repo={h.REPO} pr=227 head=abcdef123456 -->"}
    assert kind(fx, [h.row(fx, head, "2026-44", number=22700)], 22700, closed=[prefix]) == ev.KIND_SUPERSEDED


# --- second independent verification: payload and rendered-surface injection, scope and check mutations ---------------

def test_a_payload_that_injects_into_an_attribute_or_script_is_refused_even_though_the_render_reproduces_it(fx):
    for field, value in (("trustGrade", 'A" onmouseover="fetch(1)" x="'), ("generatorVersion", '"; fetch(1); "'),
                         ("canonical", "//evil.example/x"), ("canonical", "javascript:alert(1)")):
        head = fx.head("2026-44", mutate=lambda report, f=field, v=value: h.inject(report, f, v))
        seen = observe(fx, [h.row(fx, head, "2026-44")])[2270]
        assert seen.kind != ev.KIND_MERGE, (field, value)
        assert {g["name"]: g["state"] for g in seen.observed_state["gates"]}["report-json"] == "fail", (field, value)


def test_the_rendered_page_must_use_only_the_published_attribute_and_host_set():
    from gaia_cli.steward.prmaintenance import proofs

    assert proofs.surfaceProblems('<a href="/reports/" class="x" data-grade="S">ok</a>') == []
    assert proofs.surfaceProblems('<div onmouseover="x()">') and proofs.surfaceProblems('<a href="//evil.example/x">')
    assert proofs.surfaceProblems('<a href="https://evil.example/">') and proofs.surfaceProblems('<span data-grade="A&quot; x">')
    assert proofs.surfaceProblems('<a href="javascript:alert(1)">')
    assert proofs.payloadProblems({"generatorVersion": "9.0.0", "urls": {"canonical": "/reports/2026-44/"}, "name": "plain text"}) == []
    for bad in ('say "hi"', "it's", "a`b", "a=b", "a&b", "back\\slash", "<b>", "data:text/html,x"):
        assert proofs.payloadProblems({"summary": bad}), bad


def test_a_replacement_cannot_publish_a_report_whose_original_the_founder_holds(tmp_path):
    from gaia_cli.steward.prmaintenance import reconcile

    fx = h.makeRepo(tmp_path / "w")
    original = fx.head("2026-44", version="8.26.10")
    made = reconcile.buildReplacement(fx.root, h.REPO, 2157, original, "2026-44", fx.base, tmp_path / "wt")
    claude = {"sha": made.commit, "authorLogin": "claude", "authorId": 81847, "authorType": "User", "committerLogin": "claude",
              "committerName": "Claude", "parents": 1, "message": "replacement"}

    def both(**originalOver):
        first = h.row(fx, original, "2026-44", number=2157, **originalOver)
        second = h.row(fx, made.commit, "2026-44", number=2290, author={"login": "mbtiongson1", "id": 153011150, "type": "User"}, labels=[],
                       headRef=made.branch, body=made.body, commits=[claude])
        return [first, second]

    assert observe(fx, both())[2290].kind == ev.KIND_MERGE
    for over in ({"labels": ["content-engine", "founder-hold"]}, {"draft": True}, {"reviewThreadsUnresolved": 1},
                 {"comments": [{"id": 1, "user": "mbtiongson1", "body": "steward-hold: do not publish", "authorAssociation": "OWNER"}]},
                 {"reviews": [{"user": "mbtiongson1", "state": "CHANGES_REQUESTED", "commitId": original, "authorAssociation": "MEMBER",
                               "submittedAt": "2026-11-04T10:00:00Z"}]}):
        seen = observe(fx, both(**over))
        assert seen[2290].kind == ev.KIND_FOUNDER, over  # the hold binds the replacement, including one placed after it was built
        assert seen[2157].kind in (ev.KIND_FOUNDER, ev.KIND_VERIFY)  # a draft content-engine PR is ineligible (B); every other hold is Class C
    foreign = [{"sha": original, "authorLogin": "mallory", "authorId": 5, "authorType": "User", "committerLogin": "mallory", "committerName": "M",
                "parents": 1, "message": "payload"}]
    assert observe(fx, both(commits=foreign))[2290].kind != ev.KIND_MERGE  # an unproven original cannot launder a payload


def test_a_removed_file_inside_the_allowed_paths_and_a_protected_overlap_are_each_refused_on_their_own():
    import dataclasses

    registry = loadRegistry(h.SOURCE)
    producer = registry.producer("weekly-content-engine")
    removed = {"files": [{"path": "docs/reports/index.html", "status": "removed", "additions": 0, "deletions": 3, "blobSha": "0" * 40}]}
    assert ev.scopeGate(removed, producer, "2026-44").state == "fail" and "removed" in ev.scopeGate(removed, producer, "2026-44").detail
    wide = dataclasses.replace(producer, allowedFiles=("docs/**",))  # an allow-list that overlaps a protected area
    overlap = {"files": [{"path": "docs/graph/gaia.json", "status": "modified", "additions": 1, "deletions": 0, "blobSha": "0" * 40}]}
    assert ev.scopeGate(overlap, wide, "2026-44").state == "fail"


def test_a_same_named_check_still_running_is_unknown_even_beside_a_success(fx):
    head = fx.head("2026-44")
    mixed = [{**h.passing()[0], "status": "in_progress", "conclusion": None}, h.passing()[0], h.passing()[1]]
    seen = observe(fx, [h.row(fx, head, "2026-44", checkRuns=mixed)])[2270]
    assert {g["name"]: g["state"] for g in seen.observed_state["gates"]}["ci:Schema + DAG + Integrity Checks"] == "unknown"
    assert seen.kind == ev.KIND_BLOCKED


def test_a_url_key_that_holds_a_list_is_refused_not_ignored():
    from gaia_cli.steward.prmaintenance import proofs

    assert proofs.payloadProblems({"url": ["//evil.example/x"]}) and proofs.payloadProblems({"canonical": 7})
    assert proofs.payloadProblems({"urls": {"canonical": "/reports/2026-44/"}}) == []
