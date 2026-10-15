"""Contribution-channel policy tests (Issue #2074, Campaign #1817).

Every test is synthetic: a FakeGitHub transport serves canned REST responses and nothing can reach
the network (an autouse guard fails the test if any live transport, ``urlopen`` or ``gh`` is touched).
No external repository is contacted; names like ``bob/single`` are fixtures, and the Impeccable #1010
checks read only the committed ledger.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

import pytest
from test_badge_reconcile import (  # shared synthetic GitHub fixtures
    FIXED_NOW, REPO_ROOT, approve, badge_md, client, make_registry, now, patch_for, pr_payload, world,
)

from scripts import badge_policy as bp
from scripts import badge_reconcile as br
from scripts import plan_badge_provisioning as pbp

SINGLE = "bob/single"
PROPOSAL_ISSUE = "https://github.com/bob/single/issues/7"
APPROVAL_URL = f"{PROPOSAL_ISSUE}#issuecomment-555"
APPROVAL_TEXT = "Sounds good, please open a README PR."
OBSERVED = FIXED_NOW.isoformat()
HUMAN = "Pat Founder"


@pytest.fixture(autouse=True)
def no_live_calls(monkeypatch):
    """Hard guard: nothing in this module may touch the network, the local gh credential store or a live transport."""
    def boom(*a, **k):
        raise AssertionError("live network / gh access attempted in a synthetic policy test")
    monkeypatch.setattr("urllib.request.urlopen", boom)
    monkeypatch.setattr(br.UrllibTransport, "get", boom)
    monkeypatch.setattr(br.UrllibTransport, "_gh_token", staticmethod(boom))


@pytest.fixture
def registry() -> dict:
    return make_registry()


@pytest.fixture
def manifest(registry) -> dict:
    return pbp.plan_campaign(registry, {}, check_assets=False)


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def comment(cid, login, assoc, body, user_type="User", created="2026-10-11T03:04:32Z", repo=SINGLE, number=10):
    return {"id": cid, "user": {"login": login, "type": user_type}, "author_association": assoc, "body": body,
            "created_at": created, "html_url": f"https://github.com/{repo}/issues/{number}#issuecomment-{cid}"}


def item(number, repo=SINGLE, state="open", user="mbtiongson1", reason=None, pr=False, merged=False, title=None):
    kind = "pull" if pr else "issues"
    out = {"number": number, "html_url": f"https://github.com/{repo}/{kind}/{number}", "state": state,
           "state_reason": reason, "title": title or "Would a Gaia Skill Tree badge be welcome?", "body": "",
           "user": {"login": user}, "author_association": "NONE", "closed_at": "2026-10-12T00:00:00Z" if state == "closed" else None,
           "created_at": "2026-10-10T00:00:00Z"}
    if pr:
        out["pull_request"] = {"merged_at": "2026-10-12T00:00:00Z" if merged else None}
    return out


def prior(gh, items, canonical=SINGLE, name=None):
    """Serve search hits for the policy's cross-channel query (text query contains an OR)."""
    gh.add("/search/issues", {"total_count": len(items), "incomplete_results": False, "items": items},
           q=f"{name or canonical} (gaiaskilltree.com OR")


def comments(gh, number, items, repo=SINGLE):
    gh.add(f"/repos/{repo}/issues/{number}/comments", items)


def cfg(events=(), **kw):
    return br.PolicyConfig(events=tuple(events), **kw)


def scan(gh, manifest, registry, repo=SINGLE, events=(), **kw):
    key, rec = br.find_record(manifest, repo)
    return br.reconcile_repo(client(gh), key, rec, registry, now=now, policy=cfg(events, **kw))


def set_pr_open(manifest, repo=SINGLE, number=10):
    """Ledger: approved, PR opened (reservation gate bypassed with the admin override for fixtures only)."""
    approve(manifest, repo)
    pbp.record_outcome(manifest, repo, "PR_OPEN", pr_url=f"https://github.com/{repo}/pull/{number}", force=True)


def closed_pr_world(policy_files=None, bot_body=None, repo=SINGLE, number=10):
    """A ledger-recorded Gaia PR that upstream closed unmerged, plus the closure comment."""
    p = pr_payload(number, state="closed", merged=False)
    p["html_url"] = f"https://github.com/{repo}/pull/{number}"
    gh = world(repo, prs={number: (p, patch_for(badge_md("bob", "solo", repo)))}, policy_files=policy_files)
    if bot_body is not None:
        comments(gh, number, [comment(900, "github-actions[bot]", "NONE", bot_body, "Bot", repo=repo, number=number)], repo)
    else:
        comments(gh, number, [], repo)
    return gh


def by_effect(pol, effect):
    return [s for s in pol["sources"] if s["effect"] == effect]


# ---------------------------------------------------------------------------
# Pure signal extraction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("text,effect", [
    ("This repo is issue-first.", "ISSUE_FIRST"),
    ("Please open an issue first and wait for a maintainer.", "ISSUE_FIRST"),
    ("PRs require an issue approved by @alice or @bob before an outside PR.", "ISSUE_FIRST"),
    ("Pull requests without a linked issue will be closed.", "ISSUE_FIRST"),
    ("Discuss large changes in an issue before opening a pull request.", "ISSUE_FIRST"),
    ("We do not accept external pull requests.", "NO_OUTREACH"),
    ("External contributions are disabled.", "NO_OUTREACH"),
    ("Pull requests are not welcome.", "NO_OUTREACH"),
    ("AI-generated pull requests are not accepted.", "NO_OUTREACH"),
    ("Promotional PRs are not allowed.", "NO_OUTREACH"),
    ("Contributions are maintainers-only.", "NO_OUTREACH"),
    ("This is a read-only mirror.", "NO_OUTREACH"),
])
def test_restrictive_signals_from_contributing(text, effect):
    sigs = bp.extract_signals("contributing", text, "https://x/CONTRIBUTING.md", "CONTRIBUTING.md", OBSERVED)
    assert effect in {s["effect"] for s in sigs}, sigs
    assert all(s["source_url"] and s["excerpt"] and s["observed_at"] == OBSERVED for s in sigs)


@pytest.mark.parametrize("text", [
    "Pull requests are welcome!", "We welcome all contributions.", "Feel free to open a pull request.",
    "![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)",
    "Fork the repo, then open a pull request against main.",
])
def test_explicit_permission_phrases(text):
    sigs = bp.extract_signals("contributing", text, "u", "CONTRIBUTING.md", OBSERVED)
    assert any(s["effect"] == "PERMITS_PR" for s in sigs), text


@pytest.mark.parametrize("text", ["Pull requests are not welcome.", "We don't accept pull requests.",
                                  "Please do not send a pull request without an issue.", "No PRs welcome here."])
def test_negation_never_becomes_permission(text):
    sigs = bp.extract_signals("contributing", text, "u", "CONTRIBUTING.md", OBSERVED)
    assert not any(s["effect"] == "PERMITS_PR" for s in sigs), text


@pytest.mark.parametrize("kind", ["agents", "pr_template", "code_of_conduct", "security", "workflow", "issue_template"])
def test_permission_only_from_authoritative_kinds(kind):
    """Absence of prohibition is not permission, and only guidance/README/maintainer text can grant it."""
    sigs = bp.extract_signals(kind, "Pull requests are welcome.", "u", "p", OBSERVED)
    assert not any(s["effect"] == "PERMITS_PR" for s in sigs)


def test_comment_permission_needs_maintainer_authority():
    body = "Feel free to open a pull request."
    assert not any(s["effect"] == "PERMITS_PR" for s in bp.extract_signals("comment", body, "u", None, OBSERVED))
    assert not any(s["effect"] == "PERMITS_PR"
                   for s in bp.extract_signals("comment", body, "u", None, OBSERVED, comment_author_ok=False))
    assert any(s["effect"] == "PERMITS_PR"
               for s in bp.extract_signals("comment", body, "u", None, OBSERVED, comment_author_ok=True))


def test_named_approvers_extracted_from_issue_first_excerpt():
    sig = bp.extract_signals("comment", "It requires an issue approved by @PBakaus or @abdulwahabone before an outside PR.",
                             "u", None, OBSERVED, authority="policy_bot")[0]
    assert sig["effect"] == "ISSUE_FIRST" and sig["named_approvers"] == ["abdulwahabone", "pbakaus"]


def test_maintainer_only_text_closes_issue_channel_but_does_not_forbid_prs():
    sigs = bp.extract_signals("issue_template", "Issues are reserved for the maintainers.", "u", "t.md", OBSERVED)
    assert {s["effect"] for s in sigs} == {"ISSUES_CLOSED"}
    sigs = bp.extract_signals("contributing", "Issues are reserved for the maintainers.", "u", "CONTRIBUTING.md", OBSERVED)
    assert {s["effect"] for s in sigs} == {"NO_OUTREACH"}


# ---------------------------------------------------------------------------
# Channel scenarios (end to end through reconcile_repo, fake transport)
# ---------------------------------------------------------------------------


def test_pr_allowed_explicit_permission_and_receipt_fields(registry, manifest):
    e = scan(world(SINGLE), manifest, registry)
    assert e["policy_channel"] == "PR_ALLOWED"
    assert e["recommended_next_action"] == bp.ACTION_PR_PATH
    assert e["approval_required"] == {"campaign_human_approval": True, "maintainer_approval": False,
                                      "maintainer_approval_state": "NOT_APPLICABLE", "named_approvers": [],
                                      "satisfied": True}
    src = [s for s in e["policy_sources"] if s["decisive"]]
    assert src and src[0]["kind"] == "contributing" and src[0]["source_url"].endswith("CONTRIBUTING.md")
    assert "welcome" in src[0]["excerpt"].lower() and src[0]["observed_at"] == OBSERVED
    assert e["prior_issue_urls"] == [] and e["policy_complete"] is True
    assert e["policy_cost"]["api_calls"] <= e["policy_cost"]["budget"]


def test_pr_allowed_passes_the_dispatch_gate_only_after_campaign_approval(registry, manifest, tmp_path):
    v = br.predispatch_gate(client(world(SINGLE)), manifest, registry, SINGLE, "w", directory=tmp_path, now=now, policy=cfg())
    assert not v["allowed"] and any("human approval" in r for r in v["refusals"])
    approve(manifest, SINGLE)
    v = br.predispatch_gate(client(world(SINGLE)), manifest, registry, SINGLE, "w", directory=tmp_path, now=now, policy=cfg())
    assert v["allowed"], v["refusals"]
    assert v["entry"]["policy_channel"] == "PR_ALLOWED"


def test_issue_first_policy_bot_closing_a_pr(registry, manifest):
    """The #1010 shape: no CONTRIBUTING at all; an automated check closes the PR and states the policy."""
    set_pr_open(manifest)
    body = ("Thanks for the PR! This repository is issue-first: it requires an issue approved by "
            "@maint1 or @maint2 before an outside PR. Closing.")
    e = scan(closed_pr_world(policy_files={}, bot_body=body), manifest, registry)
    assert e["classification"] == "CLOSED_UNMERGED"
    assert e["policy_channel"] == "ISSUE_FIRST"
    dec = [s for s in e["policy_sources"] if s["decisive"]]
    assert dec and dec[0]["kind"] == "comment" and dec[0]["authority"] == "policy_bot"
    assert dec[0]["source_url"] == f"https://github.com/{SINGLE}/issues/10#issuecomment-900"
    assert "approved by" in dec[0]["excerpt"] and dec[0]["named_approvers"] == ["maint1", "maint2"]
    assert e["approval_required"]["maintainer_approval"] and e["approval_required"]["maintainer_approval_state"] == "MISSING"
    assert e["approval_required"]["named_approvers"] == ["maint1", "maint2"]
    assert e["recommended_next_action"] == bp.ACTION_DRAFT_ISSUE
    assert "CONTRIBUTING.md" in e["policy"]["files"]["absent"]  # absence of the file did not decide anything


def test_issue_first_without_contributing_but_explicit_maintainer_comment(registry, manifest):
    set_pr_open(manifest)
    gh = closed_pr_world(policy_files={})
    comments(gh, 10, [comment(901, "maint1", "MEMBER", "We only take outside PRs after an issue is open. "
                                                       "Please open an issue first.")])
    e = scan(gh, manifest, registry)
    assert e["policy_channel"] == "ISSUE_FIRST"
    assert [s["authority"] for s in e["policy_sources"] if s["decisive"]] == ["maintainer"]


def test_explicit_maintainer_pr_welcome_comment_without_contributing_is_pr_allowed_but_not_a_new_attempt(registry, manifest):
    gh = world(SINGLE, policy_files={})
    prior(gh, [item(7)])
    comments(gh, 7, [comment(910, "maint1", "OWNER", "Sure, feel free to open a pull request.", number=7)])
    e = scan(gh, manifest, registry)
    assert e["policy_channel"] == "PR_ALLOWED"
    assert e["recommended_next_action"] == bp.ACTION_EXISTING_OUTREACH  # the issue already used this attempt
    assert br.evaluate_dispatch(manifest, SINGLE, e)  # and the gate refuses


@pytest.mark.parametrize("author,assoc,utype", [
    ("randomuser", "CONTRIBUTOR", "User"), ("randomuser", "NONE", "User"), ("some-bot[bot]", "NONE", "Bot"),
])
def test_permission_comment_from_non_maintainer_or_bot_is_not_permission(registry, manifest, author, assoc, utype):
    gh = world(SINGLE, policy_files={})
    prior(gh, [item(7)])
    comments(gh, 7, [comment(911, author, assoc, "PRs welcome! Feel free to open a pull request.", utype, number=7)])
    e = scan(gh, manifest, registry)
    assert e["policy_channel"] == "UNKNOWN" and not e["policy_sources"]


FORMS = {
    "CONTRIBUTING.md": "Please open an issue first before opening a pull request.\n",
    ".github/ISSUE_TEMPLATE/config.yml": "blank_issues_enabled: false\n",
    ".github/ISSUE_TEMPLATE/bug_report.yml": "name: Bug report\ndescription: File a bug\nlabels: [bug]\n",
}


def test_issue_forms_restricted_to_bugs_with_issue_first_means_no_outreach(registry, manifest):
    e = scan(world(SINGLE, policy_files=FORMS), manifest, registry)
    assert e["policy_channel"] == "NO_OUTREACH"
    assert "issue_first_required_but_issue_channel_unavailable:issue_forms_restricted_to_bugs" in e["policy"]["channel_reasons"]
    assert e["policy"]["issue_channel"]["bug_only"] and e["policy"]["issue_channel"]["proposal_possible"] is False
    assert e["recommended_next_action"] == bp.ACTION_NO_OUTREACH  # no issue is manufactured into a bug form


def test_a_proposal_form_keeps_issue_first_open(registry, manifest):
    files = dict(FORMS) | {".github/ISSUE_TEMPLATE/feature_request.yml": "name: Feature request\nlabels: [enhancement]\n"}
    e = scan(world(SINGLE, policy_files=files), manifest, registry)
    assert e["policy_channel"] == "ISSUE_FIRST" and e["policy"]["issue_channel"]["proposal_possible"] is True
    assert e["recommended_next_action"] == bp.ACTION_DRAFT_ISSUE


def test_blank_issues_enabled_keeps_issue_first_open(registry, manifest):
    files = dict(FORMS) | {".github/ISSUE_TEMPLATE/config.yml": "blank_issues_enabled: true\n"}
    e = scan(world(SINGLE, policy_files=files), manifest, registry)
    assert e["policy_channel"] == "ISSUE_FIRST"


def test_issues_disabled_with_issue_first_means_no_outreach(registry, manifest):
    gh = world(SINGLE, policy_files={"CONTRIBUTING.md": "Open an issue first before sending a pull request."}, has_issues=False)
    e = scan(gh, manifest, registry)
    assert e["policy_channel"] == "NO_OUTREACH"
    assert any("issues_disabled" in r for r in e["policy"]["channel_reasons"])


def test_restricted_forms_alone_do_not_grant_or_forbid_anything(registry, manifest):
    files = {k: v for k, v in FORMS.items() if k != "CONTRIBUTING.md"}
    e = scan(world(SINGLE, policy_files=files), manifest, registry)
    assert e["policy_channel"] == "UNKNOWN"  # absence of a prohibition is not permission
    assert e["policy"]["issue_channel"]["bug_only"]


def test_issues_disabled_does_not_block_explicit_pr_permission(registry, manifest):
    e = scan(world(SINGLE, has_issues=False), manifest, registry)
    assert e["policy_channel"] == "PR_ALLOWED"


@pytest.mark.parametrize("path,text", [
    ("CONTRIBUTING.md", "We do not accept external pull requests at this time."),
    ("CONTRIBUTING.md", "This project is not accepting contributions."),
    ("CONTRIBUTING.md", "Contributions are maintainers-only."),
    ("AGENTS.md", "AI-generated pull requests are not accepted and will be closed."),
    ("README.md", "Promotional pull requests are not accepted."),
    ("README.md", "This is a read-only mirror of the upstream project."),
    (".github/PULL_REQUEST_TEMPLATE.md", "Do not submit unsolicited badge PRs."),
    ("CODE_OF_CONDUCT.md", "Spam and self-promotion is prohibited."),
    ("SECURITY.md", "AI-generated reports and PRs are not allowed."),
])
def test_no_outreach_from_any_policy_document(registry, manifest, path, text):
    files = {"CONTRIBUTING.md": "Pull requests are welcome."} | {path: text + "\n"}
    gh = world(SINGLE, policy_files=files, readme=text + "\n" if path == "README.md" else "# Title\n")
    e = scan(gh, manifest, registry)
    assert e["policy_channel"] == "NO_OUTREACH", (path, text, e["policy"]["channel_reasons"])
    assert e["recommended_next_action"] == bp.ACTION_NO_OUTREACH
    assert "restriction_overrides_other_signals" in e["policy"]["conflicts"] or path == "CONTRIBUTING.md"


def test_restriction_beats_pr_welcome_in_the_same_repo(registry, manifest):
    files = {"CONTRIBUTING.md": "Pull requests are welcome.", "AGENTS.md": "Automated pull requests are not accepted."}
    e = scan(world(SINGLE, policy_files=files), manifest, registry)
    assert e["policy_channel"] == "NO_OUTREACH" and "restriction_overrides_other_signals" in e["policy"]["conflicts"]


def test_issue_first_beats_general_pr_welcome(registry, manifest):
    files = {"CONTRIBUTING.md": "Pull requests are welcome! For anything big, please open an issue first."}
    e = scan(world(SINGLE, policy_files=files), manifest, registry)
    assert e["policy_channel"] == "ISSUE_FIRST" and "issue_first_overrides_general_pr_welcome" in e["policy"]["conflicts"]


def test_archived_repo_is_no_outreach(registry, manifest):
    e = scan(world(SINGLE, archived=True), manifest, registry)
    assert e["policy_channel"] == "NO_OUTREACH"


def test_prior_refusal_in_closure_comment_is_no_outreach_and_never_an_issue(registry, manifest):
    set_pr_open(manifest)
    e = scan(closed_pr_world(policy_files={"CONTRIBUTING.md": "Open an issue or a PR, whichever you prefer.\n"}),
             manifest, registry)
    # closed with NO explanation and no policy: UNKNOWN, and certainly not an issue to route around it
    assert e["policy_channel"] == "UNKNOWN" and e["recommended_next_action"] == bp.ACTION_EXISTING_OUTREACH
    gh = closed_pr_world(policy_files={"CONTRIBUTING.md": "Open an issue or a PR, whichever you prefer.\n"})
    comments(gh, 10, [comment(902, "maint1", "OWNER", "Thanks, but we're not interested in badge PRs.")])
    e = scan(gh, manifest, registry)
    assert e["policy_channel"] == "NO_OUTREACH" and e["recommended_next_action"] == bp.ACTION_NO_OUTREACH
    assert e["policy"]["issue_channel"]["proposal_possible"] is True  # issues are open, yet none is suggested
    assert e["policy"]["attempt"]["has_prior_outreach"]
    assert br.evaluate_dispatch(manifest, SINGLE, e)


def test_gaia_issue_closed_as_not_planned_is_a_refusal(registry, manifest):
    gh = world(SINGLE)
    prior(gh, [item(7, state="closed", reason="not_planned")])
    comments(gh, 7, [])
    e = scan(gh, manifest, registry)
    assert e["policy_channel"] == "NO_OUTREACH" and e["prior_issue_urls"] == [f"https://github.com/{SINGLE}/issues/7"]


@pytest.mark.parametrize("status", ["DECLINED", "OPTED_OUT", "NO_RESPONSE"])
def test_ledger_terminal_restrictions_are_no_outreach(registry, manifest, status):
    pbp.record_outcome(manifest, SINGLE, status, notes="terminal")
    e = scan(world(SINGLE), manifest, registry)
    assert e["policy_channel"] == "NO_OUTREACH" and e["terminal_restriction"] == status


def test_unknown_when_no_guidance_exists(registry, manifest):
    e = scan(world(SINGLE, policy_files={}), manifest, registry)
    assert e["policy_channel"] == "UNKNOWN" and e["policy"]["partial_channel"] is None
    assert "no_explicit_permission_found:absence_of_prohibition_is_not_permission" in e["policy"]["channel_reasons"]
    assert e["recommended_next_action"] == bp.ACTION_UNKNOWN and e["policy_complete"] is True
    assert e["policy"]["observed_at"] == OBSERVED and e["policy"]["files"]["absent"]


def test_unknown_when_guidance_is_silent_about_outside_prs(registry, manifest):
    e = scan(world(SINGLE, policy_files={"CONTRIBUTING.md": "Run `npm test` and keep commits small.\n"}), manifest, registry)
    assert e["policy_channel"] == "UNKNOWN"


def test_workflow_filename_alone_is_a_weak_hint_and_stays_unknown(registry, manifest):
    files = {".github/workflows/issue-first-check.yml": "name: ci\non: pull_request\njobs: {}\n"}
    e = scan(world(SINGLE, policy_files=files), manifest, registry)
    assert e["policy_channel"] == "UNKNOWN"
    assert [s["strength"] for s in e["policy_sources"]] == ["weak"]


def test_policy_workflow_content_confirms_issue_first(registry, manifest):
    wf = "name: Issue first\njobs:\n  check:\n    steps:\n      - run: echo 'PRs without a linked issue will be closed.'\n"
    e = scan(world(SINGLE, policy_files={".github/workflows/issue-first-check.yml": wf}), manifest, registry)
    assert e["policy_channel"] == "ISSUE_FIRST"
    assert {s["authority"] for s in e["policy_sources"] if s["decisive"]} == {"policy_workflow"}


# ---------------------------------------------------------------------------
# Duplicates across channels, one attempt, renames and migrations
# ---------------------------------------------------------------------------


def test_existing_duplicate_issue_blocks_everything_and_is_reported(registry, manifest):
    approve(manifest, SINGLE)
    gh = world(SINGLE)
    prior(gh, [item(7)])
    comments(gh, 7, [])
    e = scan(gh, manifest, registry)
    assert e["policy_channel"] == "PR_ALLOWED"  # guidance allows PRs, but the issue already used the attempt
    assert e["prior_issue_urls"] == ["https://github.com/bob/single/issues/7"]
    assert e["recommended_next_action"] == bp.ACTION_EXISTING_OUTREACH
    assert e["policy"]["attempt"]["has_prior_outreach"] and e["policy"]["attempt"]["issue_stage"] == "OPEN"
    refusals = br.evaluate_dispatch(manifest, SINGLE, e)
    assert any("cross-channel duplicate" in r for r in refusals)
    assert any(a["code"] == "prior_gaia_issue" for a in e["anomalies"])


def test_issue_first_with_open_proposal_waits_without_a_second_issue(registry, manifest):
    gh = world(SINGLE, policy_files={"CONTRIBUTING.md": "Please open an issue first.\n"})
    prior(gh, [item(7)])
    comments(gh, 7, [])
    e = scan(gh, manifest, registry)
    assert e["policy_channel"] == "ISSUE_FIRST" and e["recommended_next_action"] == bp.ACTION_WAIT_ISSUE
    assert e["approval_required"]["maintainer_approval_state"] == "MISSING"


def test_closed_issue_without_verified_approval_does_not_unlock_a_pr(registry, manifest):
    gh = world(SINGLE, policy_files={"CONTRIBUTING.md": "Please open an issue first.\n"})
    prior(gh, [item(7, state="closed", reason="completed")])
    gh.add(f"/repos/{SINGLE}/issues/7/comments", [comment(950, "maint1", "MEMBER", "Closing, thanks for asking.", number=7)])
    e = scan(gh, manifest, registry)
    assert e["recommended_next_action"] == bp.ACTION_ISSUE_CLOSED
    assert e["policy"]["attempt"]["issue_stage"] == "CLOSED_WITHOUT_VERIFIED_APPROVAL"


def test_an_unrelated_third_party_issue_that_mentions_gaia_still_counts_as_prior_discussion(registry, manifest):
    gh = world(SINGLE)
    other = item(8, user="some-user", title="Add the Gaia Skill Tree badge?")
    prior(gh, [other])
    e = scan(gh, manifest, registry)
    assert e["prior_issue_urls"] and e["policy"]["prior_issues"][0]["gaia_authored"] is True
    assert br.evaluate_dispatch(manifest, SINGLE, e)


def test_repo_rename_finds_prior_issue_under_the_old_name(registry, manifest):
    gh = world(SINGLE, canonical="bob/renamed")
    old = item(3, repo="bob/single")
    prior(gh, [old], canonical="bob/renamed", name="bob/single")
    gh.add("/repos/bob/single/issues/3/comments", [])
    e = scan(gh, manifest, registry)
    assert e["repository"] == "bob/renamed" and "bob/single" in e["aliases"]
    assert e["prior_issue_urls"] == ["https://github.com/bob/single/issues/3"]
    assert e["policy_complete"] is True


def test_unsearchable_old_alias_is_noted_not_fatal_but_rate_limit_is(registry, manifest):
    gh = world(SINGLE, canonical="bob/renamed")
    gh.add("/search/issues", {"message": "Validation Failed"}, status=422, q="repo:bob/single (gaiaskilltree.com OR")
    gh.add("/search/issues", {"message": "Validation Failed"}, status=422, q="repo:bob/single author:")
    e = scan(gh, manifest, registry)
    assert e["policy_complete"] is True and e["policy_channel"] == "PR_ALLOWED"
    gh2 = world(SINGLE, canonical="bob/renamed")
    gh2.add("/search/issues", {"message": "slow down"}, status=429, q="repo:bob/single (gaiaskilltree.com OR")
    assert scan(gh2, manifest, registry)["policy_channel"] == "UNKNOWN"


def test_ledger_history_follows_the_repo_across_a_rename_and_known_migration(tmp_path):
    ledger = tmp_path / "l.jsonl"
    bp.append_event(ledger, "safishamsi/graphify", "PRIOR_REFUSAL_RECORDED", "recorder",
                    {"source_url": "https://github.com/safishamsi/graphify/issues/1#issuecomment-1", "excerpt": "no thanks"})
    events = br.load_policy_events(ledger)
    for name in ("Graphify-Labs/graphify", "safishamsi/graphify", "GRAPHIFY-LABS/Graphify"):
        assert bp.ledger_state(list(events), [name], br.KNOWN_MIGRATIONS)["refusals"], name
    assert not bp.ledger_state(list(events), ["Graphify-Labs/graphify"], {})["refusals"]
    assert bp.repo_keys(["safishamsi/graphify"], br.KNOWN_MIGRATIONS) == {"safishamsi/graphify", "graphify-labs/graphify"}


def test_historical_closure_under_an_old_name_matches_the_renamed_upstream_pr(registry, manifest, tmp_path):
    set_pr_open(manifest, number=10)
    ledger = tmp_path / "l.jsonl"
    bp.append_event(ledger, "bob/old-name", "HISTORICAL_CLOSURE_RECORDED", "recorder", {
        "pr_url": "https://github.com/bob/old-name/pull/10", "state": "CLOSED_UNMERGED", "closed_at": "2026-10-11T03:04:32Z",
        "kind": "ISSUE_FIRST_REDIRECT", "excerpt": "Closed by the issue-first check.", "aliases": ["bob/single"]})
    e = scan(closed_pr_world(policy_files={}), manifest, registry, events=br.load_policy_events(ledger))
    assert e["policy_channel"] == "ISSUE_FIRST" and e["policy"]["historical_closures"]


# ---------------------------------------------------------------------------
# Approval provenance
# ---------------------------------------------------------------------------

POLICY_TEXT = "PRs require an issue approved by @maint1 before an outside PR.\n"


def approval_ledger(tmp_path, approver="maint1", authority="MEMBER", excerpt=APPROVAL_TEXT, evidence=APPROVAL_URL,
                    closure_pr=None):
    ledger = tmp_path / "ledger.jsonl"
    if closure_pr:
        bp.append_event(ledger, SINGLE, "HISTORICAL_CLOSURE_RECORDED", "recorder", {
            "pr_url": closure_pr, "state": "CLOSED_UNMERGED", "closed_at": "2026-10-11T03:04:32Z",
            "kind": "ISSUE_FIRST_REDIRECT", "excerpt": "Closed by the issue-first check."})
    bp.append_event(ledger, SINGLE, "ISSUE_PROPOSAL_SENT", HUMAN, {"issue_url": PROPOSAL_ISSUE})
    bp.append_event(ledger, SINGLE, "MAINTAINER_APPROVAL_RECORDED", HUMAN, {
        "issue_url": PROPOSAL_ISSUE, "approver": approver, "authority": authority,
        "evidence_url": evidence, "evidence_excerpt": excerpt})
    return ledger


def approval_world(extra_comments=(), issue_items=None, comment_override=None, files=None):
    gh = world(SINGLE, policy_files={"CONTRIBUTING.md": POLICY_TEXT} if files is None else files)
    prior(gh, [item(7)] if issue_items is None else issue_items)
    base = comment(555, "maint1", "MEMBER", APPROVAL_TEXT + " Thanks!", number=7)
    base.update(comment_override or {})
    gh.add(f"/repos/{SINGLE}/issues/7/comments", [base, *extra_comments])
    return gh


def test_explicit_approval_provenance_verified_opens_the_pr_path_through_the_normal_gate(registry, manifest, tmp_path):
    ledger = approval_ledger(tmp_path)
    approve(manifest, SINGLE)
    e = scan(approval_world(), manifest, registry, events=br.load_policy_events(ledger))
    appr = e["policy"]["approval"]
    assert appr["state"] == "VERIFIED" and not appr["failed_checks"]
    assert appr["record"]["approver"] == "maint1" and appr["record"]["authority"] == "MEMBER"
    assert appr["record"]["evidence_url"] == APPROVAL_URL and appr["record"]["recorded_by"] == HUMAN
    assert e["policy_channel"] == "ISSUE_FIRST" and e["recommended_next_action"] == bp.ACTION_PR_AFTER_APPROVAL
    assert e["approval_required"]["satisfied"] is True
    v = br.predispatch_gate(client(approval_world()), manifest, registry, SINGLE, "w", directory=tmp_path / "res", now=now,
                            policy=cfg(br.load_policy_events(ledger)))
    assert v["allowed"], v["refusals"]  # the README PR still goes through predispatch + campaign approval


def test_verified_approval_without_campaign_approval_is_still_refused(registry, manifest, tmp_path):
    ledger = approval_ledger(tmp_path)
    v = br.predispatch_gate(client(approval_world()), manifest, registry, SINGLE, "w", directory=tmp_path / "res", now=now,
                            policy=cfg(br.load_policy_events(ledger)))
    assert not v["allowed"] and any("human approval" in r for r in v["refusals"])


@pytest.mark.parametrize("kwargs,override,expect", [
    ({}, {"user": {"login": "someoneelse", "type": "User"}}, "evidence_comment_author_differs_from_recorded_approver"),
    ({}, {"author_association": "CONTRIBUTOR"}, "commenter_lacks_authority_association:CONTRIBUTOR"),
    ({}, {"author_association": "NONE"}, "commenter_lacks_authority_association:NONE"),
    ({}, {"body": "Looks interesting, will think about it."}, "recorded_excerpt_not_in_upstream_comment"),
    ({"evidence": f"{PROPOSAL_ISSUE}#issuecomment-999"}, {}, "evidence_comment_not_found_on_issue"),
    ({}, {"user": {"login": "maint1", "type": "Bot"}}, "evidence_comment_authored_by_bot"),
    ({"approver": "other", "authority": "COLLABORATOR"},
     {"user": {"login": "other", "type": "User"}, "author_association": "COLLABORATOR"}, "approver_not_named_by_repo_policy"),
])
def test_unverified_approvals_are_refused(registry, manifest, tmp_path, kwargs, override, expect):
    ledger = approval_ledger(tmp_path, **kwargs)
    approve(manifest, SINGLE)
    gh = approval_world(comment_override=override)
    e = scan(gh, manifest, registry, events=br.load_policy_events(ledger))
    assert e["policy"]["approval"]["state"] == "UNVERIFIED", e["policy"]["approval"]
    assert expect in e["policy"]["approval"]["failed_checks"]
    assert e["recommended_next_action"] == bp.ACTION_APPROVAL_UNVERIFIED
    assert any(a["code"] == "approval_unverified" and a["severity"] == "high" for a in e["anomalies"])
    assert br.evaluate_dispatch(manifest, SINGLE, e)


def test_approval_withdrawn_by_the_approver_is_refused(registry, manifest, tmp_path):
    ledger = approval_ledger(tmp_path)
    later = comment(556, "maint1", "MEMBER", "Actually, no - please don't open this.", number=7, created="2026-10-12T00:00:00Z")
    e = scan(approval_world(extra_comments=[later]), manifest, registry, events=br.load_policy_events(ledger))
    assert e["policy"]["approval"]["state"] == "WITHDRAWN" and e["recommended_next_action"] == bp.ACTION_APPROVAL_UNVERIFIED


def test_approval_issue_missing_upstream_or_not_ours_is_unverified(registry, manifest, tmp_path):
    ledger = approval_ledger(tmp_path)
    e = scan(approval_world(issue_items=[]), manifest, registry, events=br.load_policy_events(ledger))
    assert "approval_issue_not_found_among_upstream_issues" in e["policy"]["approval"]["failed_checks"]
    stranger = item(7, user="someone-else", title="Unrelated question")
    e = scan(approval_world(issue_items=[stranger]), manifest, registry, events=br.load_policy_events(ledger))
    assert "approval_issue_not_authored_by_campaign" in e["policy"]["approval"]["failed_checks"]


def test_unreadable_approval_comments_fail_closed_to_unknown(registry, manifest, tmp_path):
    ledger = approval_ledger(tmp_path)
    gh = approval_world()
    gh.add(f"/repos/{SINGLE}/issues/7/comments", {"message": "boom"}, status=403)
    e = scan(gh, manifest, registry, events=br.load_policy_events(ledger))
    assert e["policy_channel"] == "UNKNOWN" and not e["policy_complete"]
    assert e["policy"]["approval"]["state"] == "INCOMPLETE"


def test_revoked_approval_is_history_but_not_authority(registry, manifest, tmp_path):
    ledger = approval_ledger(tmp_path)
    appr = [e for e in bp.read_events(ledger) if e["event_type"] == "MAINTAINER_APPROVAL_RECORDED"][0]
    bp.append_event(ledger, SINGLE, "APPROVAL_REVOKED", HUMAN, {"target_hash": appr["hash"], "reason": "maintainer changed course"})
    events = br.load_policy_events(ledger)
    st = bp.ledger_state(list(events), [SINGLE])
    assert st["approvals"] and not st["active_approvals"]
    e = scan(approval_world(), manifest, registry, events=events)
    assert e["policy"]["approval"]["state"] == "MISSING" and e["recommended_next_action"] != bp.ACTION_PR_AFTER_APPROVAL


def test_approval_cannot_lift_a_recorded_refusal_or_a_second_issue(registry, manifest, tmp_path):
    ledger = approval_ledger(tmp_path)
    bp.append_event(ledger, SINGLE, "PRIOR_REFUSAL_RECORDED", "recorder",
                    {"source_url": "https://github.com/bob/single/issues/7#issuecomment-1", "excerpt": "not interested"})
    approve(manifest, SINGLE)
    e = scan(approval_world(), manifest, registry, events=br.load_policy_events(ledger))
    assert e["policy_channel"] == "NO_OUTREACH" and br.evaluate_dispatch(manifest, SINGLE, e)
    ledger2 = approval_ledger(tmp_path / "x")
    second = [item(7), item(9)]
    gh = approval_world(issue_items=second)
    gh.add(f"/repos/{SINGLE}/issues/9/comments", [])
    e = scan(gh, manifest, registry, events=br.load_policy_events(ledger2))
    assert any("only the single approved proposal" in r for r in br.evaluate_dispatch(manifest, SINGLE, e))


def test_pr_closed_by_the_issue_first_policy_does_not_block_the_one_approved_readme_pr(registry, manifest, tmp_path):
    """#1010 shape after approval: the closed PR was stage one of the same attempt."""
    pr_url = f"https://github.com/{SINGLE}/pull/10"
    ledger = approval_ledger(tmp_path, closure_pr=pr_url)
    set_pr_open(manifest, number=10)
    pbp.record_outcome(manifest, SINGLE, "POLICY_HOLD", notes="closed under issue-first policy", actor="lane")
    with pytest.raises(ValueError, match="fresh human approval"):
        pbp.record_outcome(manifest, SINGLE, "APPROVED")
    with pytest.raises(ValueError, match="POLICY_HOLD"):
        pbp.record_outcome(manifest, SINGLE, "PR_OPEN", pr_url="https://github.com/bob/single/pull/11")
    pbp.record_outcome(manifest, SINGLE, "APPROVED", approved_by="@founder-fresh")

    def build():
        p = pr_payload(10, state="closed", merged=False)
        p["html_url"] = pr_url
        gh = approval_world()
        gh.add(f"/repos/{SINGLE}/pulls/10", p)
        gh.add(f"/repos/{SINGLE}/pulls/10/files", patch_for(badge_md("bob", "solo", SINGLE)))
        comments(gh, 10, [comment(900, "github-actions[bot]", "NONE", "Closing: this repo is issue-first.", "Bot")])
        return gh

    events = br.load_policy_events(ledger)
    e = scan(build(), manifest, registry, events=events)
    assert e["classification"] == "CLOSED_UNMERGED" and e["policy"]["pr_history_waived"] is True
    v = br.predispatch_gate(client(build()), manifest, registry, SINGLE, "w", directory=tmp_path / "res", now=now,
                            policy=cfg(events))
    assert v["allowed"], v["refusals"]
    # Without the verified approval the same history is a hard hold.
    e2 = scan(build(), manifest, registry, events=[ev for ev in events if ev["event_type"] != "MAINTAINER_APPROVAL_RECORDED"])
    assert e2["policy"]["pr_history_waived"] is False
    assert br.evaluate_dispatch(manifest, SINGLE, e2)
    # The closure is still on the record, never erased by the later approval.
    assert [c["pr_url"] for c in e["policy"]["historical_closures"]] == [pr_url]


# ---------------------------------------------------------------------------
# Never manufacture an issue to bypass a PR rejection
# ---------------------------------------------------------------------------


def test_pr_rejection_with_open_issues_never_suggests_an_issue(registry, manifest):
    set_pr_open(manifest)
    gh = closed_pr_world(policy_files={"CONTRIBUTING.md": "We use issues for bugs; PRs are reviewed as time allows.\n"})
    comments(gh, 10, [comment(903, "maint1", "MEMBER", "Closing. We won't merge this badge.")])
    e = scan(gh, manifest, registry)
    assert e["policy_channel"] == "NO_OUTREACH"
    assert e["recommended_next_action"] not in (bp.ACTION_DRAFT_ISSUE,)
    assert "issue" not in e["policy"]["next_action_detail"].lower().replace("no issue", "")


def test_unexplained_closure_is_unknown_not_a_licence_for_an_issue(registry, manifest):
    set_pr_open(manifest)
    e = scan(closed_pr_world(policy_files={}), manifest, registry)
    assert e["policy_channel"] == "UNKNOWN"
    assert any(s["effect"] == "UNEXPLAINED_CLOSURE" for s in e["policy_sources"])
    assert e["recommended_next_action"] == bp.ACTION_EXISTING_OUTREACH


# ---------------------------------------------------------------------------
# Rate limits, incompleteness and the cost guard
# ---------------------------------------------------------------------------


def test_policy_search_rate_limit_degrades_to_unknown_and_is_flagged(registry, manifest):
    approve(manifest, SINGLE)
    gh = world(SINGLE)
    gh.add("/search/issues", {"message": "API rate limit exceeded"}, status=403, headers={"x-ratelimit-remaining": "0"},
           q="(gaiaskilltree.com OR")
    e = scan(gh, manifest, registry)
    assert e["classification"] == "READY_TO_APPROVE"  # the PR/README observation itself was complete
    assert e["policy_channel"] == "UNKNOWN" and e["policy_complete"] is False
    assert any(r.startswith("prior_search:RATE_LIMITED") for r in e["policy"]["completeness"]["incomplete_reasons"])
    assert e["policy"]["partial_channel"] == "PR_ALLOWED"  # shown to the reviewer, never acted on
    assert any(a["code"] == "policy_scan_incomplete" for a in e["anomalies"])
    assert e["recommended_next_action"] == bp.ACTION_INCOMPLETE
    assert any("policy evidence incomplete" in r for r in br.evaluate_dispatch(manifest, SINGLE, e))


@pytest.mark.parametrize("body", [
    {"total_count": 1, "incomplete_results": True, "items": []},
    {"total_count": 250, "incomplete_results": False, "items": [item(i) for i in range(1, 4)]},
])
def test_search_incompleteness_or_truncation_degrades_to_unknown(registry, manifest, body):
    gh = world(SINGLE)
    gh.add("/search/issues", body, q="(gaiaskilltree.com OR")
    for i in range(1, 4):
        gh.add(f"/repos/{SINGLE}/issues/{i}/comments", [])
    e = scan(gh, manifest, registry)
    assert e["policy_channel"] == "UNKNOWN" and "prior_search_incomplete" in e["policy"]["completeness"]["incomplete_reasons"]
    assert e["policy"]["completeness"]["searches_complete"] is False


def test_policy_file_permission_error_degrades_to_unknown(registry, manifest):
    gh = world(SINGLE)
    gh.add(f"/repos/{SINGLE}/contents/CONTRIBUTING.md", {"message": "Resource not accessible"}, status=403)
    e = scan(gh, manifest, registry)
    assert e["policy_channel"] == "UNKNOWN" and e["policy"]["partial_channel"] is None
    assert "policy_file:CONTRIBUTING.md:PERMISSION_DENIED" in e["policy"]["completeness"]["incomplete_reasons"]


def test_root_listing_failure_degrades_to_unknown(registry, manifest):
    gh = world(SINGLE)
    gh.add(f"/repos/{SINGLE}/contents", {"message": "server error"}, status=502)
    e = scan(gh, manifest, registry)
    assert e["policy_channel"] == "UNKNOWN" and any("policy_listing" in r for r in e["policy"]["completeness"]["incomplete_reasons"])


def test_call_budget_exhaustion_degrades_to_unknown_and_is_flagged(registry, manifest):
    gh = world(SINGLE)
    e = scan(gh, manifest, registry, call_budget=3)
    assert e["policy_channel"] == "UNKNOWN"
    assert e["policy_cost"]["budget_exhausted"] is True and e["policy_cost"]["api_calls"] == 3
    assert "policy_call_budget_exhausted" in e["policy"]["completeness"]["incomplete_reasons"]
    assert any(a["code"] == "policy_budget_exhausted" for a in e["anomalies"])


def test_unaffordable_file_set_is_incomplete_not_silently_truncated(registry, manifest):
    files = {"CONTRIBUTING.md": "Pull requests are welcome.", "AGENTS.md": "Keep commits small.", "SECURITY.md": "Report privately."}
    e = scan(world(SINGLE, policy_files=files), manifest, registry, max_files=1)
    assert e["policy_channel"] == "UNKNOWN"
    assert any(r.startswith("policy_file_budget_exceeded") for r in e["policy"]["completeness"]["incomplete_reasons"])
    assert len(e["policy"]["files"]["skipped"]) == 2


def test_default_scan_stays_inside_its_call_budget(registry, manifest):
    files = {"CONTRIBUTING.md": "Pull requests are welcome.", "AGENTS.md": "x", "SECURITY.md": "x", "CODE_OF_CONDUCT.md": "x",
             ".github/PULL_REQUEST_TEMPLATE.md": "x", ".github/ISSUE_TEMPLATE/config.yml": "blank_issues_enabled: true",
             ".github/ISSUE_TEMPLATE/bug.yml": "name: Bug", ".github/workflows/issue-first.yml": "name: x"}
    gh = world(SINGLE, policy_files=files)
    prior(gh, [item(7), item(8)])
    gh.add(f"/repos/{SINGLE}/issues/7/comments", [])
    gh.add(f"/repos/{SINGLE}/issues/8/comments", [])
    e = scan(gh, manifest, registry)
    c = e["policy_cost"]
    assert c["budget"] == br.PolicyConfig.call_budget and c["api_calls"] <= c["budget"] and not c["budget_exhausted"]
    assert c["files_fetched"] >= 7 and c["searches"] == 2 and c["comment_fetches"] == 2


def test_rate_limit_on_identity_gives_unknown_everywhere_and_stops_spending(registry, manifest):
    gh = world(SINGLE)
    gh.add(f"/repos/{SINGLE}", {"message": "API rate limit exceeded"}, status=429)
    e = scan(gh, manifest, registry)
    assert e["classification"] == "UNKNOWN" and e["policy_channel"] == "UNKNOWN"
    assert "identity_unresolved" in e["policy"]["completeness"]["incomplete_reasons"]
    assert e["policy_cost"]["api_calls"] == 0
    assert not any("/contents" in c or "/search" in c for c in gh.calls)


def test_unexpected_scan_error_fails_closed(registry, manifest, monkeypatch):
    def explode(*a, **k):
        raise KeyError("bad payload")
    monkeypatch.setattr(br, "gather_policy_raw", explode)
    e = scan(world(SINGLE), manifest, registry)
    assert e["policy_channel"] == "UNKNOWN" and "policy_scan_error:KeyError" in e["policy"]["completeness"]["incomplete_reasons"]


def test_incomplete_upstream_pr_evidence_also_blocks_the_channel(registry, manifest):
    gh = world(SINGLE)
    gh.add("/search/issues", {"total_count": 1, "incomplete_results": True, "items": []}, q="is:pr")
    e = scan(gh, manifest, registry)
    assert e["classification"] == "UNKNOWN" and e["policy_channel"] == "UNKNOWN"
    assert "upstream_pr_or_readme_evidence_incomplete" in e["policy"]["completeness"]["incomplete_reasons"]


# ---------------------------------------------------------------------------
# Receipts, scope and cost guard at the campaign / CLI level
# ---------------------------------------------------------------------------


def test_receipt_json_and_markdown_carry_the_policy_fields(registry, manifest, tmp_path):
    gh = world(SINGLE)
    prior(gh, [])
    r = br.reconcile_campaign(client(gh), manifest, registry, repos=[SINGLE], now=now, policy=cfg())
    e = r["repositories"][SINGLE]
    for key in ("policy_channel", "policy_sources", "prior_issue_urls", "approval_required", "recommended_next_action",
                "policy_complete", "policy_cost", "policy"):
        assert key in e, key
    assert r["summary"]["by_policy_channel"] == {"PR_ALLOWED": 1}
    assert r["cost"]["full_campaign_scan_required"] is False and r["cost"]["policy_repositories_scanned"] == 1
    assert 0 < r["cost"]["policy_api_calls"] <= r["cost"]["policy_call_budget_per_repo"]
    jp, mp = br.write_receipt(r, tmp_path)
    assert json.loads(jp.read_text())["repositories"][SINGLE]["policy_channel"] == "PR_ALLOWED"
    md = mp.read_text()
    assert "Contribution-channel policy (#2074)" in md and "PR_ALLOWED" in md and "CONTRIBUTING.md" in md
    assert "full-campaign scan required: no" in md


def test_receipt_is_idempotent_with_policy_on(registry, manifest):
    gh = world(SINGLE)
    c = client(gh)
    before = json.dumps(manifest, sort_keys=True)
    r1 = br.reconcile_campaign(c, manifest, registry, repos=[SINGLE], now=now, policy=cfg())
    r2 = br.reconcile_campaign(c, manifest, registry, repos=[SINGLE], now=now, policy=cfg())
    r1["cost"].pop("api_calls_total"), r2["cost"].pop("api_calls_total")
    assert r1 == r2 and json.dumps(manifest, sort_keys=True) == before


def test_unscanned_repos_report_unknown_and_never_dispatch(registry, manifest):
    approve(manifest, SINGLE)
    r = br.reconcile_campaign(client(world(SINGLE)), manifest, registry, repos=[SINGLE], now=now)  # policy not enabled
    e = r["repositories"][SINGLE]
    assert e["policy_channel"] == "UNKNOWN" and e["recommended_next_action"] == bp.ACTION_NOT_SCANNED
    assert r["cost"]["policy_repositories_scanned"] == 0 and r["cost"]["policy_api_calls"] == 0
    assert any("not scanned" in x for x in br.evaluate_dispatch(manifest, SINGLE, e))
    assert any(a["code"] == "policy_not_scanned" for a in e["anomalies"])


def _args(tmp_path, registry, manifest, **kw):
    mpath, reg = tmp_path / "manifest.json", tmp_path / "registry.json"
    mpath.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    reg.write_text(json.dumps(registry), encoding="utf-8")
    base = dict(manifest=mpath, registry=reg, campaign_author=None, repo=None, all=True, out_dir=tmp_path / "out",
                max_workers=2, open_scan_limit=100, policy="auto", policy_max_repos=10, policy_budget=36,
                policy_ledger=tmp_path / "ledger.jsonl")
    return Namespace(**(base | kw))


def test_cli_all_run_never_scans_policy_by_default_and_scoped_run_does(tmp_path, registry, manifest):
    gh = world(SINGLE)
    gh.add("/repos/Alice/Multi", {"message": "Not Found"}, status=404)
    assert pbp._cmd_reconcile(_args(tmp_path, registry, manifest), client(gh)) == 0
    data = json.loads((tmp_path / "out" / "receipt.json").read_text())
    assert data["cost"]["policy_repositories_scanned"] == 0 and data["summary"]["by_policy_channel"] == {"UNKNOWN": 2}
    assert not any("/search/issues" in c and "OR" in c for c in gh.calls)  # no policy search ran
    gh2 = world(SINGLE)
    assert pbp._cmd_reconcile(_args(tmp_path, registry, manifest, all=False, repo=[SINGLE]), client(gh2)) == 0
    data = json.loads((tmp_path / "out" / "receipt.json").read_text())
    assert data["cost"]["policy_repositories_scanned"] == 1 and data["summary"]["by_policy_channel"] == {"PR_ALLOWED": 1}


def test_cli_forced_policy_scan_refuses_an_unbounded_scope(tmp_path, registry, manifest, capsys):
    gh = world(SINGLE)
    assert pbp._cmd_reconcile(_args(tmp_path, registry, manifest, policy="on", policy_max_repos=1), client(gh)) == 64
    assert "cost guard" in capsys.readouterr().err and not gh.calls
    assert not (tmp_path / "out").exists()


def test_cli_does_not_build_a_live_client_when_one_is_injected(tmp_path, registry, manifest):
    # the autouse guard makes UrllibTransport.get and _gh_token blow up; an injected client must be enough
    assert pbp._cmd_reconcile(_args(tmp_path, registry, manifest, all=False, repo=[SINGLE]), client(world(SINGLE))) == 0


# ---------------------------------------------------------------------------
# Policy ledger: append-only, hash-chained, never erases history
# ---------------------------------------------------------------------------


def test_ledger_chain_detects_edit_deletion_and_reordering(tmp_path):
    ledger = tmp_path / "l.jsonl"
    for i in range(3):
        bp.append_event(ledger, SINGLE, "PRIOR_REFUSAL_RECORDED", "rec", {"source_url": f"https://x/{i}", "excerpt": f"no {i}"}, now=now)
    assert bp.verify_chain(bp.read_events(ledger)) == []
    lines = ledger.read_text().splitlines()
    ledger.write_text("\n".join([lines[0], lines[1].replace("no 1", "yes 1"), lines[2]]) + "\n")
    assert any("hash mismatch" in p for p in bp.verify_chain(bp.read_events(ledger)))
    ledger.write_text("\n".join([lines[0], lines[2]]) + "\n")  # deletion
    assert bp.verify_chain(bp.read_events(ledger))
    ledger.write_text("\n".join([lines[1], lines[0], lines[2]]) + "\n")  # reorder
    assert bp.verify_chain(bp.read_events(ledger))
    with pytest.raises(bp.LedgerError, match="tampered"):
        bp.append_event(ledger, SINGLE, "PRIOR_REFUSAL_RECORDED", "rec", {"source_url": "u", "excerpt": "e"})
    with pytest.raises(bp.LedgerError, match="chain broken"):
        br.load_policy_events(ledger)


def test_corrupt_ledger_line_fails_closed(tmp_path):
    ledger = tmp_path / "l.jsonl"
    ledger.write_text("{not json\n")
    with pytest.raises(bp.LedgerError, match="corrupt"):
        bp.read_events(ledger)


def test_predispatch_fails_closed_on_a_tampered_policy_ledger(registry, manifest, tmp_path):
    approve(manifest, SINGLE)
    ledger = tmp_path / "l.jsonl"
    ledger.write_text('{"seq": 1, "bogus": true}\n')
    v = br.predispatch_gate(client(world(SINGLE)), manifest, registry, SINGLE, "w", directory=tmp_path / "res", now=now,
                            ledger_path=ledger)
    assert not v["allowed"] and "gate error" in v["refusals"][0] and not list((tmp_path / "res").glob("*.lock"))


def test_history_is_never_erased_by_later_channel_or_approval_events(tmp_path):
    ledger = tmp_path / "l.jsonl"
    pr = "https://github.com/bob/single/pull/10"
    bp.append_event(ledger, SINGLE, "HISTORICAL_CLOSURE_RECORDED", "rec", {
        "pr_url": pr, "state": "CLOSED_UNMERGED", "closed_at": "2026-10-11T03:04:32Z", "kind": "ISSUE_FIRST_REDIRECT",
        "excerpt": "closed by the issue-first check"})
    bp.append_event(ledger, SINGLE, "PRIOR_REFUSAL_RECORDED", "rec", {"source_url": "u", "excerpt": "not interested"})
    bp.append_event(ledger, SINGLE, "CHANNEL_CLASSIFIED", "rec", {"channel": "ISSUE_FIRST", "observed_at": OBSERVED})
    bp.append_event(ledger, SINGLE, "CHANNEL_CLASSIFIED", "rec", {"channel": "PR_ALLOWED", "observed_at": OBSERVED})
    bp.append_event(ledger, SINGLE, "ISSUE_PROPOSAL_SENT", HUMAN, {"issue_url": PROPOSAL_ISSUE})
    bp.append_event(ledger, SINGLE, "MAINTAINER_APPROVAL_RECORDED", HUMAN, {
        "issue_url": PROPOSAL_ISSUE, "approver": "maint1", "authority": "OWNER", "evidence_url": APPROVAL_URL,
        "evidence_excerpt": APPROVAL_TEXT})
    st = bp.ledger_state(bp.read_events(ledger), [SINGLE])
    assert st["last_channel"] == "PR_ALLOWED" and len(st["channel_events"]) == 2
    assert [e["data"]["pr_url"] for e in st["historical_closures"]] == [pr]
    assert any(e["event_type"] == "PRIOR_REFUSAL_RECORDED" for e in st["refusals"])
    assert len(st["events"]) == 6 and bp.verify_chain(st["events"]) == []


@pytest.mark.parametrize("etype,data,actor,match", [
    ("MAINTAINER_APPROVAL_RECORDED", {"issue_url": PROPOSAL_ISSUE, "approver": "m", "authority": "MEMBER",
                                      "evidence_url": APPROVAL_URL, "evidence_excerpt": "ok"}, "claude-bot", "human"),
    ("MAINTAINER_APPROVAL_RECORDED", {"issue_url": PROPOSAL_ISSUE, "approver": "m", "authority": "MEMBER",
                                      "evidence_url": APPROVAL_URL, "evidence_excerpt": "ok"}, "ci[bot]", "human"),
    ("MAINTAINER_APPROVAL_RECORDED", {"issue_url": PROPOSAL_ISSUE, "approver": "m", "authority": "CONTRIBUTOR",
                                      "evidence_url": APPROVAL_URL, "evidence_excerpt": "ok"}, HUMAN, "authority"),
    ("MAINTAINER_APPROVAL_RECORDED", {"issue_url": PROPOSAL_ISSUE, "approver": "m[bot]", "authority": "MEMBER",
                                      "evidence_url": APPROVAL_URL, "evidence_excerpt": "ok"}, HUMAN, "bot"),
    ("MAINTAINER_APPROVAL_RECORDED", {"issue_url": PROPOSAL_ISSUE, "approver": "m", "authority": "MEMBER",
                                      "evidence_url": "https://github.com/bob/single/issues/99#issuecomment-1",
                                      "evidence_excerpt": "ok"}, HUMAN, "proposal issue"),
    ("MAINTAINER_APPROVAL_RECORDED", {"issue_url": PROPOSAL_ISSUE, "approver": "m", "authority": "MEMBER",
                                      "evidence_url": PROPOSAL_ISSUE, "evidence_excerpt": "ok"}, HUMAN, "comment URL"),
    ("MAINTAINER_APPROVAL_RECORDED", {"issue_url": PROPOSAL_ISSUE, "approver": "m", "authority": "MEMBER",
                                      "evidence_url": APPROVAL_URL}, HUMAN, "missing"),
    ("ISSUE_PROPOSAL_SENT", {"issue_url": "https://github.com/bob/single/pull/7"}, HUMAN, "issue URL"),
    ("ISSUE_PROPOSAL_SENT", {"issue_url": PROPOSAL_ISSUE}, "", "actor is required"),
    ("ISSUE_PROPOSAL_SENT", {"issue_url": PROPOSAL_ISSUE}, "Claude Code", "human"),
    ("ISSUE_PROPOSAL_DRAFTED", {"draft_path": "d.md", "draft_sha256": "x", "sent": True}, "rec", "sent=false"),
    ("HISTORICAL_CLOSURE_RECORDED", {"pr_url": "https://github.com/a/b/issues/1", "closed_at": "t", "kind": "REFUSAL",
                                     "excerpt": "e", "state": "CLOSED_UNMERGED"}, "rec", "pull request"),
    ("APPROVAL_REVOKED", {"target_hash": "nope", "reason": "r"}, HUMAN, "matches no ledger event"),
    ("NOT_A_TYPE", {}, "rec", "unknown event type"),
])
def test_ledger_rejects_unprovenanced_events(tmp_path, etype, data, actor, match):
    with pytest.raises(bp.LedgerError, match=match):
        bp.append_event(tmp_path / "l.jsonl", SINGLE, etype, actor, data)
    assert not (tmp_path / "l.jsonl").exists() or not (tmp_path / "l.jsonl").read_text()


# ---------------------------------------------------------------------------
# Draft proposal is local only; the tooling has no write path to GitHub
# ---------------------------------------------------------------------------


def test_draft_is_a_concise_local_proposal_not_a_claim_to_be_approved():
    text = bp.render_draft_proposal("pbakaus/impeccable", "Impeccable", "https://gaiaskilltree.com/named/#explorer/a/b",
                                    "https://gaiaskilltree.com/badges/_assets/a/b.svg?repo=a/b")
    assert text.startswith("<!-- DRAFT ONLY. LOCAL FILE. NEVER SENT.")
    assert bp.draft_word_count(text) <= 150
    assert "will not follow up" in text and "only open a PR if you tell us it is welcome" in text
    assert "approved" not in text.lower()


def test_no_module_in_the_policy_path_can_write_to_github():
    for mod in (bp, br, pbp):
        tree = ast.parse(Path(mod.__file__).read_text())
        imported = {n.names[0].name for n in ast.walk(tree) if isinstance(n, ast.Import)} | \
                   {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
        assert not imported & {"requests", "httpx", "http.client", "aiohttp", "github"}, (mod.__name__, imported)
    src = Path(bp.__file__).read_text()
    assert "urllib.request" not in src and "subprocess" not in src and "socket" not in src
    assert not any(hasattr(br.UrllibTransport, v) for v in ("post", "put", "patch", "delete"))
    for method in ('method="POST"', 'method="PUT"', 'method="PATCH"', 'method="DELETE"', "gh pr create", "gh issue create"):
        assert method not in Path(br.__file__).read_text()


# ---------------------------------------------------------------------------
# Manifest lifecycle: POLICY_HOLD keeps history; Impeccable #1010 reconciliation
# ---------------------------------------------------------------------------


def test_policy_hold_requires_notes_keeps_pr_history_and_is_preserved_by_replanning(registry, manifest):
    set_pr_open(manifest)
    with pytest.raises(ValueError, match="requires --notes"):
        pbp.record_outcome(manifest, SINGLE, "POLICY_HOLD")
    pbp.record_outcome(manifest, SINGLE, "POLICY_HOLD", notes="closed under issue-first policy", actor="Lane C")
    rec = manifest["repositories"][SINGLE]
    prov = rec["provisioning"]
    assert rec["status"] == "POLICY_HOLD" and prov["pr_url"].endswith("/pull/10") and prov["attempts"] == 1
    assert [h["to_status"] for h in prov["history"]] == ["APPROVED", "PR_OPEN", "POLICY_HOLD"]
    assert prov["history"][-1]["actor"] == "Lane C" and prov["approved_by"] == "@founder"  # approval fields untouched
    replanned = pbp.plan_campaign(registry, manifest, check_assets=False)
    assert replanned["repositories"][SINGLE]["status"] == "POLICY_HOLD"
    assert replanned["classification_counts"]["POLICY_HOLD"] == 1
    assert pbp.record_outcome(manifest, SINGLE, "APPROVED", approved_by="@fresh")["repositories"][SINGLE]["provisioning"]["approved_at"]


def test_committed_ledger_reconciles_impeccable_1010_as_closed_unmerged_policy_hold():
    events = br.load_policy_events()  # verifies the hash chain
    st = bp.ledger_state(list(events), ["pbakaus/impeccable"], br.KNOWN_MIGRATIONS)
    closure = st["historical_closures"][0]["data"]
    assert closure["pr_url"] == "https://github.com/pbakaus/impeccable/pull/1010"
    assert closure["state"] == "CLOSED_UNMERGED" and closure["kind"] == "ISSUE_FIRST_REDIRECT"
    assert closure["closed_at"] == "2026-10-11T03:04:32Z" and closure["live_verified"] is False
    assert st["last_channel"] == "ISSUE_FIRST"
    assert not st["proposals_sent"] and not st["approvals"]  # nothing was sent; nobody approved anything
    draft = st["drafts"][0]["data"]
    assert draft["sent"] is False
    text = (REPO_ROOT / draft["draft_path"]).read_text()
    assert text.startswith("<!-- DRAFT ONLY. LOCAL FILE. NEVER SENT.") and bp.draft_word_count(text) <= 150
    import hashlib
    assert hashlib.sha256(text.encode()).hexdigest() == draft["draft_sha256"]
    m = pbp.load_existing_manifest(pbp.DEFAULT_MANIFEST)["repositories"]["pbakaus/impeccable"]
    assert m["status"] == "POLICY_HOLD" and m["provisioning"]["pr_url"].endswith("/pull/1010")
    assert [h["to_status"] for h in m["provisioning"]["history"]][-2:] == ["PR_OPEN", "POLICY_HOLD"]  # #1010 not erased


def test_impeccable_end_to_end_with_synthetic_upstream_is_issue_first_hold_and_gate_refuses(tmp_path):
    manifest = pbp.load_existing_manifest(pbp.DEFAULT_MANIFEST)
    registry = pbp.load_registry(pbp.DEFAULT_REGISTRY)
    repo, number = "pbakaus/impeccable", 1010
    p = pr_payload(number, state="closed", merged=False)
    p["html_url"] = f"https://github.com/{repo}/pull/{number}"
    gh = world(repo, policy_files={}, prs={number: (p, patch_for(badge_md("pbakaus", "impeccable", repo)))})
    gh.add(f"/repos/{repo}/issues/{number}/comments", [comment(
        6104859751, "policy-bot[bot]", "NONE", "This repo is issue-first: PRs require an issue approved by @pbakaus or "
        "@abdulwahabone before an outside PR.", "Bot", repo=repo, number=number)])
    events = br.load_policy_events()
    key, rec = br.find_record(manifest, repo)
    e = br.reconcile_repo(client(gh), key, rec, registry, now=now, policy=cfg(events))
    assert e["classification"] == "CLOSED_UNMERGED" and e["policy_channel"] == "ISSUE_FIRST"
    assert e["approval_required"]["named_approvers"] == ["abdulwahabone", "pbakaus"]
    assert e["policy"]["historical_closures"][0]["pr_url"].endswith("/pull/1010")
    assert e["recommended_next_action"] == bp.ACTION_DRAFT_ISSUE and e["prior_issue_urls"] == []
    v = br.predispatch_gate(client(gh), manifest, registry, repo, "w", directory=tmp_path, now=now, policy=cfg(events))
    assert not v["allowed"] and any("ISSUE_FIRST" in r for r in v["refusals"])


# ---------------------------------------------------------------------------
# Offline policy CLI
# ---------------------------------------------------------------------------


def _policy_cli(tmp_path, manifest, *argv):
    mpath = tmp_path / "manifest.json"
    if not mpath.exists():
        mpath.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return subprocess.run([sys.executable, "scripts/plan_badge_provisioning.py", "policy", "--manifest", str(mpath),
                           "--ledger", str(tmp_path / "ledger.jsonl"), *argv],
                          cwd=REPO_ROOT, capture_output=True, text=True, timeout=60)


@pytest.mark.integration
def test_policy_cli_enforces_one_proposal_human_recording_and_attachment(tmp_path, manifest):
    run = lambda *a: _policy_cli(tmp_path, manifest, *a)  # noqa: E731
    r = run("approve", "--repo", SINGLE, "--issue-url", PROPOSAL_ISSUE, "--approver", "maint1", "--authority", "MEMBER",
            "--evidence-url", APPROVAL_URL, "--evidence-excerpt", APPROVAL_TEXT, "--recorded-by", HUMAN)
    assert r.returncode == 2 and "single proposal issue recorded" in r.stderr  # no approval without a recorded proposal
    assert run("record-sent", "--repo", SINGLE, "--issue-url", PROPOSAL_ISSUE, "--recorded-by", "claude-bot").returncode == 2
    assert run("record-sent", "--repo", SINGLE, "--issue-url", PROPOSAL_ISSUE, "--recorded-by", HUMAN).returncode == 0
    r = run("record-sent", "--repo", SINGLE, "--issue-url", "https://github.com/bob/single/issues/8", "--recorded-by", HUMAN)
    assert r.returncode == 2 and "exactly one proposal" in r.stderr
    r = run("draft", "--repo", SINGLE, "--recorded-by", HUMAN)
    assert r.returncode == 2 and "already recorded" in r.stderr
    ok = run("approve", "--repo", SINGLE, "--issue-url", PROPOSAL_ISSUE, "--approver", "maint1", "--authority", "MEMBER",
             "--evidence-url", APPROVAL_URL, "--evidence-excerpt", APPROVAL_TEXT, "--recorded-by", HUMAN)
    assert ok.returncode == 0, ok.stderr
    dup = run("approve", "--repo", SINGLE, "--issue-url", PROPOSAL_ISSUE, "--approver", "maint1", "--authority", "MEMBER",
              "--evidence-url", APPROVAL_URL, "--evidence-excerpt", APPROVAL_TEXT, "--recorded-by", HUMAN)
    assert dup.returncode == 2 and "active approval already exists" in dup.stderr
    status = json.loads(run("status", "--repo", SINGLE).stdout)
    assert status["approvals"][0]["active"] and status["approvals"][0]["approver"] == "maint1" and status["events"] == 2
    assert run("verify").returncode == 0


@pytest.mark.integration
def test_policy_cli_refusal_blocks_drafts_proposals_and_approvals(tmp_path, manifest):
    run = lambda *a: _policy_cli(tmp_path, manifest, *a)  # noqa: E731
    assert run("record-refusal", "--repo", SINGLE, "--source-url", "https://github.com/bob/single/pull/1#issuecomment-1",
               "--excerpt", "not interested", "--recorded-by", HUMAN).returncode == 0
    for cmd in (("draft", "--recorded-by", HUMAN), ("record-sent", "--issue-url", PROPOSAL_ISSUE, "--recorded-by", HUMAN)):
        r = run(cmd[0], "--repo", SINGLE, *cmd[1:])
        assert r.returncode == 2 and "refusal" in r.stderr, cmd


@pytest.mark.integration
def test_policy_cli_apply_records_only_channel_changes_from_a_receipt(tmp_path, registry, manifest):
    r = br.reconcile_campaign(client(world(SINGLE)), manifest, registry, repos=[SINGLE], now=now, policy=cfg())
    jp, _ = br.write_receipt(r, tmp_path / "receipt")
    run = lambda *a: _policy_cli(tmp_path, manifest, *a)  # noqa: E731
    first = run("apply", "--receipt", str(jp), "--recorded-by", HUMAN)
    assert first.returncode == 0 and "recorded 1 channel event" in first.stdout
    assert "recorded 0 channel event" in run("apply", "--receipt", str(jp), "--recorded-by", HUMAN).stdout  # idempotent
    events = bp.read_events(tmp_path / "ledger.jsonl")
    assert events[0]["event_type"] == "CHANNEL_CLASSIFIED" and events[0]["data"]["channel"] == "PR_ALLOWED"
    assert events[0]["data"]["previous_channel"] is None and events[0]["data"]["source_urls"]
    assert events[0]["data"]["receipt_sha256"]


@pytest.mark.integration
def test_policy_cli_draft_writes_a_local_file_and_a_sent_false_event(tmp_path, manifest):
    out = tmp_path / "draft.md"
    r = _policy_cli(tmp_path, manifest, "draft", "--repo", SINGLE, "--out", str(out), "--recorded-by", HUMAN)
    assert r.returncode == 0 and "never sent" in r.stdout
    assert out.read_text().startswith("<!-- DRAFT ONLY")
    ev = bp.read_events(tmp_path / "ledger.jsonl")[0]
    assert ev["event_type"] == "ISSUE_PROPOSAL_DRAFTED" and ev["data"]["sent"] is False


# ---------------------------------------------------------------------------
# Review hardening: untrusted upstream text, held repos never offered for approval, offline overlay
# ---------------------------------------------------------------------------


def test_upstream_excerpts_cannot_inject_markup_into_the_markdown_receipt(registry, manifest):
    evil = "We do not accept pull requests. ![x](https://evil.example/p.png) [click](https://evil.example) <script>x</script> | a | b |"
    gh = world(SINGLE, policy_files={"CONTRIBUTING.md": evil})
    r = br.reconcile_campaign(client(gh), manifest, registry, repos=[SINGLE], now=now, policy=cfg())
    assert r["repositories"][SINGLE]["policy_channel"] == "NO_OUTREACH"
    md = br.render_markdown(r)
    for bad in ("![x]", "](https://evil", "<script>", "evil.example/p.png)"):
        assert bad not in md, bad
    assert "@\u200bmaint" in br.md_untrusted("ask @maint about it") and "@maint" not in br.md_untrusted("ask @maint about it")
    assert br.md_url("https://evil.example/x") != "https://evil.example/x"
    assert br.md_url("https://github.com/a/b/blob/main/CONTRIBUTING.md") == "https://github.com/a/b/blob/main/CONTRIBUTING.md"


@pytest.mark.parametrize("files,expect", [
    ({"CONTRIBUTING.md": "Do not send unsolicited pull requests."}, "HOLD_POLICY_CHANNEL_NO_OUTREACH_DO_NOT_REQUEST_APPROVAL"),
    ({}, "HOLD_POLICY_CHANNEL_UNKNOWN_DO_NOT_REQUEST_APPROVAL"),
    ({"CONTRIBUTING.md": "Please open an issue first."}, "HOLD_POLICY_CHANNEL_ISSUE_FIRST_DO_NOT_REQUEST_APPROVAL"),
    (None, "REQUEST_HUMAN_APPROVAL"),
])
def test_a_clean_repo_is_only_offered_for_approval_when_its_channel_allows_it(registry, manifest, files, expect):
    e = scan(world(SINGLE, policy_files=files), manifest, registry)
    assert e["classification"] == "READY_TO_APPROVE" and e["recommended_action"] == expect


def test_a_prior_issue_holds_the_approval_request_too(registry, manifest):
    gh = world(SINGLE)
    prior(gh, [item(7)])
    comments(gh, 7, [])
    assert scan(gh, manifest, registry)["recommended_action"] == "HOLD_EXISTING_ISSUE_STAGE_DO_NOT_REQUEST_APPROVAL"


def test_recorded_history_is_overlaid_even_when_no_policy_scan_runs(registry, manifest, tmp_path):
    ledger = tmp_path / "l.jsonl"
    bp.append_event(ledger, SINGLE, "HISTORICAL_CLOSURE_RECORDED", "rec", {
        "pr_url": f"https://github.com/{SINGLE}/pull/10", "state": "CLOSED_UNMERGED", "closed_at": "2026-10-11T03:04:32Z",
        "kind": "ISSUE_FIRST_REDIRECT", "excerpt": "closed by the issue-first check"})
    gh = world(SINGLE)
    key, rec = br.find_record(manifest, SINGLE)
    e = br.reconcile_repo(client(gh), key, rec, registry, now=now,
                          policy=br.PolicyConfig(events=br.load_policy_events(ledger), scan=False))
    assert e["policy_channel"] == "UNKNOWN" and e["policy"]["partial_channel"] == "ISSUE_FIRST"
    assert e["policy"]["historical_closures"] and e["policy_cost"]["api_calls"] == 0
    assert not any("/contents" in c for c in gh.calls)  # offline overlay: no policy calls were made


@pytest.mark.parametrize("files,expect", [
    ({"CONTRIBUTING.md": "We do not accept external pull requests."}, "policy channel NO_OUTREACH is an internal hold (no PR, no issue)"),
    ({}, "policy channel UNKNOWN is an internal hold (no PR, no issue)"),
    ({"CONTRIBUTING.md": "Please open an issue first."},
     "policy channel ISSUE_FIRST needs a verified recorded maintainer approval (approval state MISSING)"),
])
def test_the_gate_refuses_every_non_pr_allowed_channel_on_policy_alone(registry, manifest, tmp_path, files, expect):
    """Campaign-approved, clean, complete evidence: the ONLY remaining reason to refuse is the channel."""
    approve(manifest, SINGLE)
    v = br.predispatch_gate(client(world(SINGLE, policy_files=files)), manifest, registry, SINGLE, "w",
                            directory=tmp_path, now=now, policy=cfg())
    assert not v["allowed"] and v["refusals"] == [expect]
    assert not list(tmp_path.glob("*.lock"))  # reservation released on refusal


def test_concurrent_appends_keep_one_unbroken_chain(tmp_path):
    import concurrent.futures
    ledger = tmp_path / "l.jsonl"

    def add(i):
        return bp.append_event(ledger, SINGLE, "PRIOR_REFUSAL_RECORDED", f"rec{i}", {"source_url": f"https://x/{i}", "excerpt": f"no {i}"})

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(add, range(24)))
    events = bp.read_events(ledger)
    assert [e["seq"] for e in events] == list(range(1, 25)) and bp.verify_chain(events) == []


def test_a_policy_search_pr_unknown_to_the_ledger_also_blocks_dispatch(registry, manifest, tmp_path):
    approve(manifest, SINGLE)
    gh = world(SINGLE)
    prior(gh, [item(12, pr=True, state="closed")])  # surfaced only by the cross-channel search
    comments(gh, 12, [])
    e = scan(gh, manifest, registry)
    assert e["policy"]["prior_prs"] and any("Gaia PR already exists" in r for r in br.evaluate_dispatch(manifest, SINGLE, e))
