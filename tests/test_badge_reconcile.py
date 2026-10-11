"""Deterministic fixture tests for upstream badge reconciliation (Issue #2069, Campaign #1817).

No network: a FakeGitHub transport serves canned REST responses (pagination, 403/404/429,
incomplete search results, redirects).
"""

from __future__ import annotations

import base64
import concurrent.futures
import copy
import json
import subprocess
import sys
import urllib.parse
from argparse import Namespace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from scripts import badge_reconcile as br
from scripts import plan_badge_provisioning as pbp

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXED_NOW = datetime(2026, 10, 11, 12, 0, 0, tzinfo=timezone.utc)


def now() -> datetime:
    return FIXED_NOW


# ---------------------------------------------------------------------------
# Fake GitHub
# ---------------------------------------------------------------------------


class FakeGitHub:
    """Route table keyed on (path, query-subset, q-substring); most specific route wins."""

    def __init__(self) -> None:
        self.routes: list[dict] = []
        self.calls: list[str] = []
        self.unrouted: list[str] = []

    def add(self, path, body=None, status=200, headers=None, q=None, query=None, seq=None):
        self.routes.append({"path": path, "body": body, "status": status, "headers": headers or {},
                            "q": q, "query": query or {}, "seq": list(seq) if seq else None})
        return self

    def get(self, url: str) -> br.Response:
        parsed = urllib.parse.urlparse(url)
        path = urllib.parse.unquote(parsed.path)
        query = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
        self.calls.append(path + ("?" + parsed.query if parsed.query else ""))
        best, best_score = None, (-1, -1)
        for i, r in enumerate(self.routes):
            if r["path"] != path:
                continue
            if any(query.get(k) != v for k, v in r["query"].items()):
                continue
            if r["q"] is not None and r["q"] not in query.get("q", ""):
                continue
            score = (len(r["query"]) + (1 if r["q"] else 0), i)
            if score > best_score:
                best, best_score = r, score
        if best is None:
            self.unrouted.append(url)
            return br.Response(404, {}, {"message": "unrouted in fake"})
        if best["seq"]:
            status, headers, body = best["seq"].pop(0) if len(best["seq"]) > 1 else best["seq"][0]
            return br.Response(status, headers, body)
        return br.Response(best["status"], best["headers"], copy.deepcopy(best["body"]))


def b64(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


def badge_md(handle: str, stem: str, repo: str = "o/r", seal: bool = False, honesty: bool = True) -> str:
    fname = f"{stem}-seal.svg" if seal else f"{stem}.svg"
    mid = "_assets/" if honesty else ""
    return (f"[![Gaia Skill: {stem}](https://gaiaskilltree.com/badges/{mid}{handle}/{fname}"
            f"?repo={urllib.parse.quote(repo, safe='')})](https://gaiaskilltree.com/named/#explorer/{handle}/{stem})")


def pr_payload(number, state="open", merged=False, user="mbtiongson1", head="gaia/badge-x", title="docs: add Gaia Skill Tree recognition badge"):
    return {
        "number": number, "state": state, "merged": merged,
        "merged_at": "2026-10-10T00:00:00Z" if merged else None,
        "html_url": f"https://github.com/o/r/pull/{number}", "title": title, "body": "",
        "user": {"login": user}, "head": {"ref": head, "sha": "h" * 40, "repo": {"full_name": "fork/r"}},
        "base": {"ref": "main", "sha": "b" * 40},
    }


def patch_for(*badges: str) -> list[dict]:
    patch = "@@ -1,1 +1,{n} @@\n # Title\n".format(n=1 + len(badges)) + "".join(f"+{b}\n" for b in badges)
    return [{"filename": "README.md", "status": "modified", "changes": len(badges), "patch": patch}]


def world(repo="o/r", requested=None, canonical=None, readme="# Title\n", open_pulls=None,
          prs=None, search_prs=None, branch_sha="c" * 40, other_files=None, archived=False) -> FakeGitHub:
    """prs: {number: (pr_payload, files)}. search_prs: numbers surfaced only by search."""
    canonical = canonical or repo
    gh = FakeGitHub()
    gh.add(f"/repos/{requested or repo}", {"id": 4242, "full_name": canonical, "default_branch": "main", "archived": archived})
    if requested and requested != canonical:
        gh.add(f"/repos/{canonical}", {"id": 4242, "full_name": canonical, "default_branch": "main", "archived": archived})
    gh.add(f"/repos/{canonical}/pulls", open_pulls or [], query={"state": "open"})
    gh.add("/search/issues", {"total_count": 0, "incomplete_results": False, "items": []})
    if search_prs:
        gh.add("/search/issues", {"total_count": len(search_prs), "incomplete_results": False,
                                  "items": [{"number": n} for n in search_prs]}, q="gaiaskilltree.com")
    gh.add("/search/code", {"total_count": len(other_files or []), "incomplete_results": False,
                            "items": [{"path": p} for p in (other_files or [])]})
    gh.add(f"/repos/{canonical}/branches/main", {"commit": {"sha": branch_sha}})
    if readme is None:
        gh.add(f"/repos/{canonical}/readme", {"message": "Not Found"}, status=404)
    else:
        gh.add(f"/repos/{canonical}/readme", {"encoding": "base64", "content": b64(readme), "sha": "blob1",
                                               "path": "README.md", "html_url": f"https://github.com/{canonical}/blob/main/README.md"})
    for n, (payload, files) in (prs or {}).items():
        gh.add(f"/repos/{canonical}/pulls/{n}", payload)
        gh.add(f"/repos/{canonical}/pulls/{n}/files", files)
    return gh


def client(gh: FakeGitHub) -> br.GitHubClient:
    return br.GitHubClient(gh, retries=1, sleep=lambda s: None, search_intervals={})


# ---------------------------------------------------------------------------
# Fixtures: registry + manifest
# ---------------------------------------------------------------------------


def make_registry() -> dict:
    def skill(handle, slug, rank, branch="standard"):
        return {"id": f"{handle}/{slug}", "name": slug.title(), "rank": rank, "branch": branch,
                "file": f"{slug}.svg", "fileSeal": f"{slug}-seal.svg"}

    return {"generatedAt": "2026-10-11", "contributors": {
        "alice": {"repos": ["Alice/Multi"], "topSkill": "alice/main", "namedSkills": [
            skill("alice", "main", 4), skill("alice", "extra", 2)],
            "skillsByRepo": {"Alice/Multi": ["alice/main", "alice/extra"]}},
        "bob": {"repos": ["bob/single"], "topSkill": "bob/solo", "namedSkills": [skill("bob", "solo", 3)],
                "skillsByRepo": {"bob/single": ["bob/solo"]}},
    }}


@pytest.fixture
def registry() -> dict:
    return make_registry()


@pytest.fixture
def manifest(registry) -> dict:
    return pbp.plan_campaign(registry, {}, check_assets=False)


def approve(manifest: dict, repo: str) -> dict:
    return pbp.record_outcome(manifest, repo, "APPROVED", approved_by="@founder", notes="ok")


def run(gh, manifest, registry, repo):
    key, rec = br.find_record(manifest, repo)
    return br.reconcile_repo(client(gh), key, rec, registry, now=now)


MULTI = "Alice/Multi"
SINGLE = "bob/single"


# ---------------------------------------------------------------------------
# Badge normalization
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("raw,handle,stem,style", [
    ("https://gaiaskilltree.com/badges/_assets/Alice/Main.svg?repo=o%2Fr", "alice", "main", "wordmark"),
    ("https://GaiaSkillTree.com/badges/alice/main-seal.svg", "alice", "main", "seal"),
    ("https://www.gaiaskilltree.com/badges/_assets/alice/main.svg?repo=o/r&amp;x=1", "alice", "main", "wordmark"),
    ("https://gaiaskilltree.com/badges/_assets/alice/ma%69n-seal.svg?repo=O%2FR", "alice", "main", "seal"),
])
def test_parse_badge_url_variants(raw, handle, stem, style):
    ref = br.parse_badge_url(raw)
    assert (ref.handle, ref.stem, ref.style) == (handle, stem, style)
    assert "?" not in ref.url


def test_parse_badge_url_repo_param_normalized_and_rejects_foreign_paths():
    assert br.parse_badge_url("https://gaiaskilltree.com/badges/_assets/a/b.svg?repo=Owner%2FRepo").repo_param == "owner/repo"
    assert br.parse_badge_url("https://gaiaskilltree.com/badges/index.html") is None
    assert br.parse_badge_url("https://gaiaskilltree.com/named/x") is None


def test_extract_markdown_and_html_forms_and_dedup():
    text = (
        badge_md("alice", "main") + "\n"
        '<p align="center"><a href="https://gaiaskilltree.com/named/#explorer/alice/extra">'
        '<img src="https://gaiaskilltree.com/badges/_assets/alice/extra-seal.svg?repo=o%2Fr&amp;v=1" height="20"></a></p>\n'
        + badge_md("alice", "main", honesty=False)  # worker path variant of same badge
    )
    refs, links = br.extract_badges(text)
    assert {(r.handle, r.stem, r.style) for r in refs} == {("alice", "main", "wordmark"), ("alice", "extra", "seal")}
    assert "https://gaiaskilltree.com/named/#explorer/alice/extra" in links


def test_coverage_seal_wordmark_partial_and_contributor_level(registry):
    expected = br.expected_skills_for_repo(registry, "alice/multi")  # case-insensitive lookup
    assert [s["id"] for s in expected] == ["alice/main", "alice/extra"]  # ordered by rank desc
    seal_only, _ = br.extract_badges(badge_md("alice", "main", seal=True))
    cov = br.compute_coverage(expected, seal_only)
    assert cov["level"] == "partial" and cov["covered_skill_ids"] == ["alice/main"]
    assert cov["details"][0]["styles"] == ["seal"] and cov["missing_skill_ids"] == ["alice/extra"]
    both, _ = br.extract_badges(badge_md("alice", "main") + badge_md("alice", "extra", seal=True))
    assert br.compute_coverage(expected, both)["level"] == "full"
    contrib, _ = br.extract_badges(badge_md("alice", "rank") + badge_md("alice", "skills", seal=True))
    cov = br.compute_coverage(expected, contrib)
    assert cov["level"] == "none" and len(cov["contributor_level_badges"]) == 2
    wrong_handle, _ = br.extract_badges(badge_md("mallory", "main"))
    cov = br.compute_coverage(expected, wrong_handle)
    assert cov["level"] == "none" and cov["unmapped_badges"]


# ---------------------------------------------------------------------------
# Classification scenarios
# ---------------------------------------------------------------------------


def test_clean_repo_ready_to_approve(registry, manifest):
    e = run(world("bob/single"), manifest, registry, SINGLE)
    assert e["classification"] == "READY_TO_APPROVE" and e["recommended_action"] == "REQUEST_HUMAN_APPROVAL"
    assert e["github_id"] == 4242 and e["default_branch"] == "main"
    assert e["evidence"]["complete"] and e["evidence"]["readme_commit_sha"] == "c" * 40
    assert e["expected_skills"] == [{"id": "bob/solo", "name": "Solo", "rank": 3}]


def test_existing_open_pr_recorded_in_ledger(registry, manifest):
    approve(manifest, SINGLE)
    pbp.record_outcome(manifest, SINGLE, "PR_OPEN", pr_url="https://github.com/bob/single/pull/10")
    files = patch_for(badge_md("bob", "solo", "bob/single"))
    gh = world("bob/single", open_pulls=[pr_payload(10)], prs={10: (pr_payload(10), files)})
    e = run(gh, manifest, registry, SINGLE)
    assert e["classification"] == "PR_OPEN"
    pr = e["pull_requests"][0]
    assert (pr["number"], pr["state"], pr["ledgered"], pr["has_gaia_badge"]) == (10, "open", True, True)
    assert pr["head"]["ref"] == "gaia/badge-x" and pr["base"]["ref"] == "main"
    assert e["ledger"]["approved_by"] == "@founder" and len(e["ledger"]["history"]) == 2
    assert not any(a["code"] == "unledgered_pr" for a in e["anomalies"])


def test_unledgered_open_pr_is_found_by_content_and_blocks(registry, manifest):
    """A third-party PR (not by the campaign account, not on a gaia/ branch) is found via
    its title marker and then confirmed by inspecting the diff, not the title."""
    p = pr_payload(7, user="someone", head="feature", title="Add badge")
    gh = world("bob/single", open_pulls=[p], prs={7: (p, patch_for(badge_md("bob", "solo", "bob/single")))})
    e = run(gh, manifest, registry, SINGLE)
    assert e["classification"] == "PR_OPEN"
    assert e["pull_requests"][0]["matched_by"] == ["open_list"]
    assert any(a["code"] == "unledgered_pr" for a in e["anomalies"])


def test_unrelated_open_pr_is_ignored(registry, manifest):
    p = pr_payload(8, user="someone", head="fix-typo", title="Fix typo")
    clean = [{"filename": "src/a.py", "status": "modified", "changes": 3, "patch": "@@ -1 +1 @@\n+x = 1\n"}]
    gh = world("bob/single", open_pulls=[p], prs={8: (p, clean)})
    e = run(gh, manifest, registry, SINGLE)
    assert e["classification"] == "READY_TO_APPROVE" and e["pull_requests"] == []
    assert e["ignored_pr_numbers"] == [8]
    assert e["evidence"]["open_pr_scan"]["complete"] is True


def test_unmarked_open_pr_with_gaia_badge_is_found_and_blocks_dispatch(registry, manifest, tmp_path):
    """Review check 1: odd title/branch/author must not hide a Gaia badge PR."""
    approve(manifest, SINGLE)
    p = pr_payload(21, user="a-maintainer", head="patch-1", title="Update readme")
    gh = world("bob/single", open_pulls=[p], prs={21: (p, patch_for(badge_md("bob", "solo", "bob/single")))})
    e = run(gh, manifest, registry, SINGLE)
    assert e["classification"] == "PR_OPEN"
    assert e["pull_requests"][0]["matched_by"] == ["open_scan"]
    assert any(a["code"] == "unledgered_pr" for a in e["anomalies"])
    verdict = br.predispatch_gate(client(gh), manifest, registry, SINGLE, "w", directory=tmp_path / "res", now=now)
    assert verdict["allowed"] is False
    assert not list((tmp_path / "res").glob("*.lock"))  # reservation released on refusal


def test_open_pr_scan_over_limit_fails_closed_never_ready(registry, manifest, tmp_path):
    approve(manifest, SINGLE)
    ps = [pr_payload(30 + i, user="u", head=f"b{i}", title=f"t{i}") for i in range(3)]
    clean = [{"filename": "a.md", "status": "modified", "changes": 1, "patch": "@@ -1 +1 @@\n+hi\n"}]
    gh = world("bob/single", open_pulls=ps, prs={p["number"]: (p, clean) for p in ps})
    key, rec = br.find_record(manifest, SINGLE)
    e = br.reconcile_repo(client(gh), key, rec, registry, now=now, open_scan_limit=2)
    assert e["classification"] == "UNKNOWN"
    assert e["evidence"]["open_pr_scan"] == {"complete": False, "open_total": 3, "unmarked_total": 3,
                                             "unmarked_inspected": 2, "limit": 2}
    assert any(a["code"] == "open_pr_scan_incomplete" for a in e["anomalies"])
    assert br.evaluate_dispatch(manifest, key, e)
    assert br.reconcile_repo(client(gh), key, rec, registry, now=now, open_scan_limit=3)["classification"] == "READY_TO_APPROVE"


def test_unmarked_pr_with_unreadable_readme_diff_makes_scan_incomplete(registry, manifest):
    p = pr_payload(40, user="u", head="b", title="t")
    big = [{"filename": "README.md", "status": "modified", "changes": 5000}]
    e = run(world("bob/single", open_pulls=[p], prs={40: (p, big)}), manifest, registry, SINGLE)
    assert e["classification"] == "UNKNOWN" and e["pull_requests"] == []


def test_reservation_voided_when_ledger_authorization_changes(tmp_path, registry, manifest):
    """Review check 2: a token cannot outlive the authorization it was issued under."""
    approve(manifest, SINGLE)
    res = tmp_path / "res"
    v = br.predispatch_gate(client(world("bob/single")), manifest, registry, SINGLE, "w", directory=res, now=now)
    assert v["allowed"]
    token = v["reservation"]["token"]
    _, rec = br.find_record(manifest, SINGLE)
    br.verify_reservation(SINGLE, token, res, now=now, current_snapshot=br.ledger_snapshot(rec))
    for status in ("DECLINED", "OPTED_OUT"):
        changed = json.loads(json.dumps(manifest))
        pbp.record_outcome(changed, SINGLE, status, notes="maintainer said no")
        _, crec = br.find_record(changed, SINGLE)
        with pytest.raises(br.ReservationError, match="changed since predispatch"):
            br.verify_reservation(SINGLE, token, res, now=now, current_snapshot=br.ledger_snapshot(crec))


def test_unrelated_badge_pr_with_clean_diff_is_ignored_but_unreadable_one_is_not(registry, manifest):
    p = pr_payload(9, user="someone", head="chore/pepy-badge", title="docs: swap download badge")
    clean = [{"filename": "README.md", "status": "modified", "changes": 1, "patch": "@@ -1 +1 @@\n+![pepy](https://pepy.tech/b.svg)\n"}]
    e = run(world("bob/single", open_pulls=[p], prs={9: (p, clean)}), manifest, registry, SINGLE)
    assert e["classification"] == "READY_TO_APPROVE" and e["pull_requests"] == [] and e["ignored_pr_numbers"] == [9]
    unreadable = [{"filename": "README.md", "status": "modified", "changes": 900}]
    e = run(world("bob/single", open_pulls=[p], prs={9: (p, unreadable)}), manifest, registry, SINGLE)
    assert e["classification"] == "NEEDS_REVIEW"


def test_merged_pr_with_visible_badge_is_adopted(registry, manifest):
    pbp.record_outcome(manifest, SINGLE, "APPROVED", approved_by="@f")
    pbp.record_outcome(manifest, SINGLE, "PR_OPEN", pr_url="https://github.com/bob/single/pull/3")
    p = pr_payload(3, state="closed", merged=True)
    gh = world("bob/single", readme="# T\n" + badge_md("bob", "solo", "bob/single"),
               prs={3: (p, patch_for(badge_md("bob", "solo", "bob/single")))})
    e = run(gh, manifest, registry, SINGLE)
    assert e["classification"] == "ADOPTED" and e["coverage"]["level"] == "full"
    assert e["coverage"]["covered_skill_ids"] == ["bob/solo"]
    assert e["ledger"]["status"] == "PR_OPEN"  # ledger lifecycle untouched by observation


def test_independently_installed_badge_is_already_adopted(registry, manifest):
    gh = world("bob/single", readme="<img src='https://gaiaskilltree.com/badges/_assets/bob/solo-seal.svg?repo=bob/single'>")
    e = run(gh, manifest, registry, SINGLE)
    assert e["classification"] == "ALREADY_ADOPTED"
    assert e["coverage"]["details"][0]["styles"] == ["seal"]


def test_merged_pr_with_missing_badge_is_not_adoption(registry, manifest):
    pbp.record_outcome(manifest, SINGLE, "APPROVED", approved_by="@f")
    pbp.record_outcome(manifest, SINGLE, "PR_OPEN", pr_url="https://github.com/bob/single/pull/3")
    p = pr_payload(3, state="closed", merged=True)
    gh = world("bob/single", readme="# T\nbadge removed later\n", prs={3: (p, patch_for(badge_md("bob", "solo", "bob/single")))})
    e = run(gh, manifest, registry, SINGLE)
    assert e["classification"] == "NEEDS_REVIEW"
    assert any(a["code"] == "merged_without_badge" for a in e["anomalies"])


def test_closed_unmerged_pr(registry, manifest):
    p = pr_payload(4, state="closed", merged=False)
    gh = world("bob/single", search_prs=[4], prs={4: (p, patch_for(badge_md("bob", "solo", "bob/single")))})
    e = run(gh, manifest, registry, SINGLE)
    assert e["classification"] == "CLOSED_UNMERGED" and e["recommended_action"].startswith("EXPLICIT_REVIEW")
    assert e["pull_requests"][0]["matched_by"] == ["search"]


@pytest.mark.parametrize("status", ["DECLINED", "OPTED_OUT", "NO_RESPONSE"])
def test_terminal_restrictions_preserved(registry, manifest, status):
    key, rec = br.find_record(manifest, SINGLE)
    rec["status"] = status
    rec["provisioning"]["outcome"] = status
    e = run(world("bob/single"), manifest, registry, SINGLE)
    assert e["terminal_restriction"] == status
    assert e["recommended_action"] == "NO_OUTREACH_TERMINAL_RESTRICTION"
    # Observation is independent of lifecycle: ledger says contacted, upstream shows no trace.
    assert e["classification"] == "NEEDS_REVIEW"
    assert any(a["code"] == "ledger_contacted_but_no_upstream_trace" for a in e["anomalies"])
    assert br.evaluate_dispatch(manifest, key, e)  # always refused


def test_multiple_named_skills_in_one_pr_and_full_coverage(registry, manifest):
    pbp.record_outcome(manifest, MULTI, "APPROVED", approved_by="@f")
    pbp.record_outcome(manifest, MULTI, "PR_OPEN", pr_url="https://github.com/Alice/Multi/pull/9")
    files = patch_for(badge_md("alice", "main", "alice/multi"), badge_md("alice", "extra", "alice/multi", seal=True))
    p = pr_payload(9)
    gh = world("Alice/Multi", open_pulls=[p], prs={9: (p, files)})
    e = run(gh, manifest, registry, MULTI)
    assert e["classification"] == "PR_OPEN"
    assert {b["stem"] for b in e["pull_requests"][0]["badges"]} == {"main", "extra"}
    readme = "# T\n" + badge_md("alice", "main") + badge_md("alice", "extra", seal=True)
    e2 = run(world("Alice/Multi", readme=readme, open_pulls=[], prs={9: (pr_payload(9, "closed", True), files)}),
             manifest, registry, MULTI)
    assert e2["classification"] == "ADOPTED" and e2["coverage"]["level"] == "full"


def test_partial_skill_coverage(registry, manifest):
    gh = world("Alice/Multi", readme=badge_md("alice", "main"))
    e = run(gh, manifest, registry, MULTI)
    assert e["classification"] == "PARTIAL_COVERAGE"
    assert e["coverage"]["covered_skill_ids"] == ["alice/main"] and e["coverage"]["missing_skill_ids"] == ["alice/extra"]


def test_contributor_level_badge_never_proves_skill_coverage(registry, manifest):
    gh = world("bob/single", readme=badge_md("bob", "rank") + badge_md("bob", "handle", seal=True))
    e = run(gh, manifest, registry, SINGLE)
    assert e["coverage"]["level"] == "none" and e["classification"] == "NEEDS_REVIEW"
    assert any(a["code"] == "contributor_level_badge_only" for a in e["anomalies"])


def test_badge_in_other_file_reported_separately(registry, manifest):
    e = run(world("bob/single", other_files=["docs/index.md"]), manifest, registry, SINGLE)
    assert e["classification"] == "NEEDS_REVIEW" and e["other_files"] == ["docs/index.md"]
    assert e["coverage"]["level"] == "none"


def test_ambiguous_marker_pr_without_badge_content(registry, manifest):
    p = pr_payload(5)
    gh = world("bob/single", open_pulls=[p], prs={5: (p, [{"filename": "README.md", "status": "modified", "changes": 1,
                                                          "patch": "@@ -1 +1 @@\n+hello\n"}])})
    e = run(gh, manifest, registry, SINGLE)
    assert e["classification"] == "NEEDS_REVIEW"
    assert e["pull_requests"][0]["marker_only"] is True


def test_uninspectable_patch_is_ambiguous(registry, manifest):
    p = pr_payload(5)
    gh = world("bob/single", open_pulls=[p], prs={5: (p, [{"filename": "README.md", "status": "modified", "changes": 900}])})
    e = run(gh, manifest, registry, SINGLE)
    assert e["classification"] == "NEEDS_REVIEW"
    assert any(a["code"] == "patch_unavailable" for a in e["anomalies"])


def test_no_readme_needs_review(registry, manifest):
    e = run(world("bob/single", readme=None), manifest, registry, SINGLE)
    assert e["classification"] == "NEEDS_REVIEW" and e["readme"]["present"] is False


def test_ledger_contacted_but_nothing_upstream(registry, manifest):
    pbp.record_outcome(manifest, SINGLE, "APPROVED", approved_by="@f")
    pbp.record_outcome(manifest, SINGLE, "PR_OPEN", pr_url="https://github.com/bob/single/pull/3")
    p = pr_payload(3, state="closed", merged=False)
    gh = world("bob/single", prs={3: (p, patch_for(badge_md("bob", "solo", "bob/single")))})
    e = run(gh, manifest, registry, SINGLE)
    assert e["classification"] == "CLOSED_UNMERGED"
    assert any(a["code"] == "ledger_pr_open_but_not_open_upstream" for a in e["anomalies"])


def test_graphify_hold_is_never_recommended_for_approval(registry, manifest):
    reg = copy.deepcopy(registry)
    reg["contributors"]["safishamsi"] = {"repos": ["safishamsi/graphify"], "topSkill": "safishamsi/graphify", "namedSkills": [
        {"id": "safishamsi/graphify", "name": "Graphify", "rank": 5, "branch": "unique", "file": "graphify.svg"}],
        "skillsByRepo": {"safishamsi/graphify": ["safishamsi/graphify"]}}
    m = pbp.plan_campaign(reg, {}, check_assets=False)
    gh = world("safishamsi/graphify", canonical="Graphify-Labs/graphify")
    gh.add("/repos/safishamsi/graphify", {"id": 4242, "full_name": "Graphify-Labs/graphify", "default_branch": "main"})
    e = run(gh, m, reg, "safishamsi/graphify")
    assert e["classification"] == "READY_TO_APPROVE" and e["hold"] == "#2067"
    assert e["recommended_action"] == "HELD_UNDER_2067_DO_NOT_REQUEST_APPROVAL"
    assert e["aliases"] == ["safishamsi/graphify"] and e["repository"] == "Graphify-Labs/graphify"
    approve(m, "safishamsi/graphify")
    key, rec = br.find_record(m, "safishamsi/graphify")
    assert any("hold" in r for r in br.evaluate_dispatch(m, key, run(gh, m, reg, "safishamsi/graphify")))


# ---------------------------------------------------------------------------
# Identity: redirects and case
# ---------------------------------------------------------------------------


def test_repo_rename_redirect_records_alias_and_uses_canonical(registry, manifest):
    gh = world("bob/single", requested="bob/single", canonical="Bob-Org/Single-Renamed")
    e = run(gh, manifest, registry, SINGLE)
    assert e["repository"] == "Bob-Org/Single-Renamed" and e["aliases"] == ["bob/single"]
    assert e["identity"]["renamed"] is True
    assert any(a["code"] == "repo_renamed" for a in e["anomalies"])
    assert not gh.unrouted
    assert all("/repos/bob/single/" not in c for c in gh.calls)  # later calls hit the canonical name


def test_case_normalization(registry, manifest):
    gh = world("Alice/Multi", requested="Alice/Multi", canonical="alice/multi")
    e = run(gh, manifest, registry, MULTI)
    assert e["identity"]["case_normalized"] is True and e["identity"]["renamed"] is False
    assert any(a["code"] == "repo_case_normalized" for a in e["anomalies"])


# ---------------------------------------------------------------------------
# Fail-closed API behaviour
# ---------------------------------------------------------------------------


def _assert_unknown(e, code):
    assert e["classification"] == "UNKNOWN", e["reasons"]
    assert e["classification"] != "READY_TO_APPROVE"
    assert e["evidence"]["complete"] is False
    assert any(x["code"] == code for x in e["evidence"]["errors"])
    assert e["recommended_action"] in ("RETRY_RECONCILE_NO_DISPATCH", "NO_OUTREACH_TERMINAL_RESTRICTION")


def test_repo_404_unresolved_identity(registry, manifest):
    gh = FakeGitHub().add("/repos/bob/single", {"message": "Not Found"}, status=404)
    _assert_unknown(run(gh, manifest, registry, SINGLE), "NOT_FOUND")


def test_permission_denied_403_on_readme(registry, manifest):
    gh = world("bob/single")
    gh.add("/repos/bob/single/readme", {"message": "Resource not accessible"}, status=403)
    _assert_unknown(run(gh, manifest, registry, SINGLE), "PERMISSION_DENIED")


def test_rate_limit_403_header_and_429(registry, manifest):
    gh = world("bob/single")
    gh.add("/repos/bob/single/pulls", {"message": "API rate limit exceeded"}, status=403,
           headers={"x-ratelimit-remaining": "0"}, query={"state": "open"})
    _assert_unknown(run(gh, manifest, registry, SINGLE), "RATE_LIMITED")
    gh = world("bob/single")
    gh.add("/search/issues", {"message": "slow down"}, status=429, headers={"retry-after": "30"})
    _assert_unknown(run(gh, manifest, registry, SINGLE), "RATE_LIMITED")


def test_search_incomplete_results_flag(registry, manifest):
    gh = world("bob/single")
    gh.add("/search/issues", {"total_count": 0, "incomplete_results": True, "items": []}, q="gaiaskilltree.com")
    _assert_unknown(run(gh, manifest, registry, SINGLE), "INCOMPLETE")


def test_search_truncated_total_exceeds_items(registry, manifest):
    gh = world("bob/single")
    gh.add("/search/issues", {"total_count": 1200, "incomplete_results": False, "items": []}, q="gaiaskilltree.com")
    _assert_unknown(run(gh, manifest, registry, SINGLE), "INCOMPLETE")


def test_code_search_failure_blocks_ready(registry, manifest):
    gh = world("bob/single")
    gh.add("/search/code", {"message": "rate"}, status=429)
    _assert_unknown(run(gh, manifest, registry, SINGLE), "RATE_LIMITED")


def test_readme_too_large_is_incomplete(registry, manifest):
    gh = world("bob/single")
    gh.add("/repos/bob/single/readme", {"encoding": "none", "content": "", "path": "README.md", "sha": "x"})
    _assert_unknown(run(gh, manifest, registry, SINGLE), "INCOMPLETE")


def test_ledger_pr_404_fails_closed(registry, manifest):
    pbp.record_outcome(manifest, SINGLE, "APPROVED", approved_by="@f")
    pbp.record_outcome(manifest, SINGLE, "PR_OPEN", pr_url="https://github.com/bob/single/pull/99")
    gh = world("bob/single")  # PR 99 unrouted -> 404
    _assert_unknown(run(gh, manifest, registry, SINGLE), "NOT_FOUND")


def test_transient_5xx_is_retried_then_succeeds(registry, manifest):
    gh = world("bob/single")
    gh.add("/repos/bob/single/branches/main", seq=[(502, {}, {"message": "bad gateway"}),
                                                    (200, {}, {"commit": {"sha": "d" * 40}})])
    e = run(gh, manifest, registry, SINGLE)
    assert e["classification"] == "READY_TO_APPROVE" and e["evidence"]["readme_commit_sha"] == "d" * 40


def test_persistent_5xx_fails_closed(registry, manifest):
    gh = world("bob/single")
    gh.add("/repos/bob/single/branches/main", {"message": "boom"}, status=503)
    _assert_unknown(run(gh, manifest, registry, SINGLE), "SERVER_ERROR")


def test_network_error_fails_closed(registry, manifest):
    class Down:
        def get(self, url):
            raise br.TransportError("connection reset")
    key, rec = br.find_record(manifest, SINGLE)
    e = br.reconcile_repo(br.GitHubClient(Down(), retries=1, sleep=lambda s: None), key, rec, registry, now=now)
    _assert_unknown(e, "NETWORK_ERROR")


def test_pagination_merges_pages_and_follows_link():
    gh = FakeGitHub()
    gh.add("/x", [1, 2], headers={"link": '<https://api.github.com/x?per_page=100&page=2>; rel="next"'})
    gh.add("/x", [3], query={"page": "2"})
    items, complete, meta = client(gh).paginate("/x")
    assert items == [1, 2, 3] and complete and meta["pages"] == 2


def test_pagination_page_cap_marks_incomplete():
    gh = FakeGitHub().add("/x", [1], headers={"link": '<https://api.github.com/x?page=2>; rel="next"'})
    items, complete, meta = client(gh).paginate("/x", max_pages=3)
    assert not complete and meta["truncated"] and len(items) == 3


def test_pagination_in_search_collects_all_pages(registry, manifest):
    gh = world("bob/single")
    gh.add("/search/issues", {"total_count": 2, "incomplete_results": False, "items": [{"number": 21}]},
           q="gaiaskilltree.com", headers={"link": '<https://api.github.com/search/issues?q=repo%3Abob%2Fsingle+is%3Apr+gaiaskilltree.com&per_page=100&page=2>; rel="next"'})
    gh.add("/search/issues", {"total_count": 2, "incomplete_results": False, "items": [{"number": 22}]},
           q="gaiaskilltree.com", query={"page": "2"})
    for n in (21, 22):
        gh.add(f"/repos/bob/single/pulls/{n}", pr_payload(n, "closed", False))
        gh.add(f"/repos/bob/single/pulls/{n}/files", patch_for(badge_md("bob", "solo", "bob/single")))
    e = run(gh, manifest, registry, SINGLE)
    assert e["evidence"]["complete"] and sorted(p["number"] for p in e["pull_requests"]) == [21, 22]
    assert e["classification"] == "CLOSED_UNMERGED"


# ---------------------------------------------------------------------------
# Receipts, idempotency, read-only guarantees
# ---------------------------------------------------------------------------


def test_campaign_receipt_is_read_only_idempotent_and_complete(registry, manifest, tmp_path):
    before = json.dumps(manifest, sort_keys=True)
    gh = world("bob/single")
    gh.add("/repos/Alice/Multi", {"id": 1, "full_name": "Alice/Multi", "default_branch": "main"})
    gh.add("/repos/Alice/Multi/pulls", [], query={"state": "open"})
    gh.add("/repos/Alice/Multi/branches/main", {"commit": {"sha": "e" * 40}})
    gh.add("/repos/Alice/Multi/readme", {"encoding": "base64", "content": b64(badge_md("alice", "main")), "sha": "b", "path": "README.md"})
    c = client(gh)
    r1 = br.reconcile_campaign(c, manifest, registry, now=now, max_workers=3)
    r2 = br.reconcile_campaign(c, manifest, registry, now=now, max_workers=1)
    assert r1 == r2  # repeat-run idempotency (deterministic given fixed clock)
    assert json.dumps(manifest, sort_keys=True) == before
    assert r1["mode"] == "read-only" and r1["summary"]["repositories"] == 2
    assert r1["summary"]["by_classification"] == {"READY_TO_APPROVE": 1, "PARTIAL_COVERAGE": 1}
    assert r1["manifest_sha256"] == br.manifest_digest(manifest)
    jp, mp = br.write_receipt(r1, tmp_path / "out")
    assert json.loads(jp.read_text()) == json.loads(json.dumps(r1, default=str))
    md = mp.read_text()
    assert "## Summary" in md and "## Anomalies" in md and "PARTIAL_COVERAGE" in md and "Alice/Multi" in md
    # GET-only: the fake would 404 anything unexpected, and no mutating verbs exist on the transport
    assert not gh.unrouted
    assert not hasattr(br.UrllibTransport, "post") and not hasattr(br.UrllibTransport, "put")


def test_reconcile_subset_unknown_repo_raises(registry, manifest):
    with pytest.raises(KeyError):
        br.reconcile_campaign(client(FakeGitHub()), manifest, registry, repos=["nope/nope"])


def test_full_ledger_preserved_when_github_unavailable():
    """All 43 real campaign records are carried through; total outage => all UNKNOWN."""
    manifest = pbp.load_existing_manifest(pbp.DEFAULT_MANIFEST)
    registry = pbp.load_registry(pbp.DEFAULT_REGISTRY)
    before = pbp.DEFAULT_MANIFEST.read_bytes()
    receipt = br.reconcile_campaign(client(FakeGitHub()), manifest, registry, now=now)
    assert receipt["summary"]["repositories"] == 43
    assert receipt["summary"]["by_classification"] == {"UNKNOWN": 43}
    assert pbp.DEFAULT_MANIFEST.read_bytes() == before
    for name in ("pbakaus/impeccable", "trailhq/Graft"):
        assert receipt["repositories"][name]["ledger"]["status"] == "PR_OPEN"
        assert receipt["repositories"][name]["ledger"]["history"]


@pytest.mark.parametrize("repo,number,slug,handle,skill_stem", [
    ("pbakaus/impeccable", 1010, "pbakaus/impeccable", "pbakaus", "impeccable"),
    ("trailhq/Graft", 581, "trailhq/Graft", "trailhq", "graft"),
])
def test_pilot_repos_protected_while_pr_open(repo, number, slug, handle, skill_stem, tmp_path):
    manifest = pbp.load_existing_manifest(pbp.DEFAULT_MANIFEST)
    registry = pbp.load_registry(pbp.DEFAULT_REGISTRY)
    p = pr_payload(number)
    p["html_url"] = f"https://github.com/{repo}/pull/{number}"
    gh = world(repo, open_pulls=[p], prs={number: (p, patch_for(badge_md(handle, skill_stem, repo)))})
    e = run(gh, manifest, registry, repo)
    assert e["classification"] == "PR_OPEN" and e["recommended_action"] == "DO_NOT_DISPATCH_WAIT_FOR_MAINTAINER"
    verdict = br.predispatch_gate(client(gh), manifest, registry, repo, "w1", directory=tmp_path / "res", now=now)
    assert verdict["allowed"] is False
    assert any("PR_OPEN" in r or "upstream already has" in r or "PR URL" in r for r in verdict["refusals"])
    assert not list((tmp_path / "res").glob("*.lock"))  # reservation released on refusal


# ---------------------------------------------------------------------------
# Pre-dispatch gate + reservations + concurrency
# ---------------------------------------------------------------------------


def test_predispatch_requires_human_approval(registry, manifest, tmp_path):
    v = br.predispatch_gate(client(world("bob/single")), manifest, registry, SINGLE, "w", directory=tmp_path, now=now)
    assert not v["allowed"] and any("human approval" in r for r in v["refusals"])


def test_predispatch_allows_clean_approved_repo_and_reserves(registry, manifest, tmp_path):
    approve(manifest, SINGLE)
    v = br.predispatch_gate(client(world("bob/single")), manifest, registry, SINGLE, "w1", directory=tmp_path, now=now)
    assert v["allowed"], v["refusals"]
    assert br.verify_reservation(SINGLE, v["reservation"]["token"], tmp_path, now=now)["worker"] == "w1"
    v2 = br.predispatch_gate(client(world("bob/single")), manifest, registry, SINGLE, "w2", directory=tmp_path, now=now)
    assert not v2["allowed"] and "already reserved" in v2["refusals"][0]
    assert br.release_reservation(SINGLE, v["reservation"]["token"], directory=tmp_path)
    v3 = br.predispatch_gate(client(world("bob/single")), manifest, registry, SINGLE, "w3", directory=tmp_path, now=now)
    assert v3["allowed"]


def test_predispatch_refuses_stale_ledger_when_upstream_pr_appeared(registry, manifest, tmp_path):
    approve(manifest, SINGLE)  # ledger says nothing was sent...
    p = pr_payload(31)         # ...but a PR now exists upstream (second worker / manual)
    gh = world("bob/single", open_pulls=[p], prs={31: (p, patch_for(badge_md("bob", "solo", "bob/single")))})
    v = br.predispatch_gate(client(gh), manifest, registry, SINGLE, "w", directory=tmp_path, now=now)
    assert not v["allowed"] and v["entry"]["classification"] == "PR_OPEN"


def test_predispatch_refuses_when_upstream_visibility_incomplete(registry, manifest, tmp_path):
    approve(manifest, SINGLE)
    gh = world("bob/single")
    gh.add("/search/issues", {"message": "limit"}, status=429)
    v = br.predispatch_gate(client(gh), manifest, registry, SINGLE, "w", directory=tmp_path, now=now)
    assert not v["allowed"] and any("incomplete" in r for r in v["refusals"])


def test_predispatch_gate_internal_error_fails_closed(registry, manifest, tmp_path):
    approve(manifest, SINGLE)

    class Boom:
        def get(self, url):
            raise RuntimeError("kaboom")
    v = br.predispatch_gate(br.GitHubClient(Boom(), retries=0), manifest, registry, SINGLE, "w", directory=tmp_path, now=now)
    assert not v["allowed"] and "gate error" in v["refusals"][0]
    assert not list(tmp_path.glob("*.lock"))


def test_concurrent_predispatch_exactly_one_winner(registry, manifest, tmp_path):
    approve(manifest, SINGLE)

    def attempt(i):
        return br.predispatch_gate(client(world("bob/single")), manifest, registry, SINGLE, f"w{i}", directory=tmp_path, now=now)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        verdicts = list(pool.map(attempt, range(8)))
    assert sum(v["allowed"] for v in verdicts) == 1
    assert all("already reserved" in v["refusals"][0] for v in verdicts if not v["allowed"])


def test_reservation_expiry_and_token_checks(tmp_path):
    res = br.acquire_reservation("a/b", "w", ttl_minutes=5, directory=tmp_path, now=now)
    with pytest.raises(br.ReservationError, match="token mismatch"):
        br.verify_reservation("a/b", "wrong", tmp_path, now=now)
    with pytest.raises(br.ReservationError, match="expired"):
        br.verify_reservation("a/b", res["token"], tmp_path, now=lambda: FIXED_NOW + timedelta(minutes=6))
    # An expired reservation is not silently stolen
    with pytest.raises(br.ReservationError, match="already reserved"):
        br.acquire_reservation("A/B", "other", directory=tmp_path, now=lambda: FIXED_NOW + timedelta(hours=1))
    with pytest.raises(br.ReservationError):
        br.release_reservation("a/b", "wrong", directory=tmp_path)
    assert br.release_reservation("a/b", force=True, directory=tmp_path)
    assert not br.release_reservation("a/b", force=True, directory=tmp_path)


# ---------------------------------------------------------------------------
# CLI: corrupt manifest, record-outcome gating, concurrent manifest writes
# ---------------------------------------------------------------------------


def _write_manifest(path: Path, manifest: dict) -> None:
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def _cli(*argv: str, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "scripts/plan_badge_provisioning.py", *argv], cwd=cwd,
                          capture_output=True, text=True, timeout=60)


@pytest.mark.integration
def test_corrupt_manifest_preserved_and_fail_closed(tmp_path, registry):
    mpath = tmp_path / "manifest.json"
    mpath.write_text("{not json", encoding="utf-8")
    reg = tmp_path / "registry.json"
    reg.write_text(json.dumps(registry), encoding="utf-8")
    args = Namespace(manifest=mpath, registry=reg, campaign_author=None, repo=["bob/single"], all=False,
                     out_dir=tmp_path / "out", max_workers=1, open_scan_limit=100)
    with pytest.raises(ValueError, match="Corrupt manifest"):
        pbp._cmd_reconcile(args, client(FakeGitHub()))
    pargs = Namespace(manifest=mpath, registry=reg, campaign_author=None, repo="bob/single", worker="w",
                      ttl_minutes=5, out_dir=None, reservation_dir=tmp_path / "res", open_scan_limit=100)
    with pytest.raises(ValueError, match="Corrupt manifest"):
        pbp._cmd_predispatch(pargs, client(FakeGitHub()))
    assert mpath.read_text() == "{not json"
    assert not (tmp_path / "out").exists()
    r = _cli("record-outcome", "--manifest", str(mpath), "--repo", "bob/single", "--status", "APPROVED", "--approved-by", "@f")
    assert r.returncode != 0 and "Corrupt manifest" in r.stderr
    assert mpath.read_text() == "{not json"


def test_cli_reconcile_end_to_end_writes_only_receipts(tmp_path, registry, manifest):
    mpath, reg = tmp_path / "manifest.json", tmp_path / "registry.json"
    _write_manifest(mpath, manifest)
    reg.write_text(json.dumps(registry), encoding="utf-8")
    before = mpath.read_bytes()
    args = Namespace(manifest=mpath, registry=reg, campaign_author=None, repo=None, all=True,
                     out_dir=tmp_path / "out", max_workers=2, open_scan_limit=100)
    gh = world("bob/single")
    gh.add("/repos/Alice/Multi", {"message": "Not Found"}, status=404)
    assert pbp._cmd_reconcile(args, client(gh)) == 0
    assert mpath.read_bytes() == before
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == ["receipt.json", "receipt.md"]
    data = json.loads((tmp_path / "out" / "receipt.json").read_text())
    assert data["summary"]["by_classification"] == {"READY_TO_APPROVE": 1, "UNKNOWN": 1}
    assert pbp._cmd_reconcile(Namespace(**{**vars(args), "all": False, "repo": None}), client(gh)) == 64


@pytest.mark.integration
def test_cli_predispatch_exit_codes_and_pr_open_requires_token(tmp_path, registry, manifest):
    mpath, reg, res = tmp_path / "manifest.json", tmp_path / "registry.json", tmp_path / "res"
    approve(manifest, SINGLE)
    _write_manifest(mpath, manifest)
    reg.write_text(json.dumps(registry), encoding="utf-8")
    pargs = Namespace(manifest=mpath, registry=reg, campaign_author=None, repo=SINGLE, worker="w",
                      ttl_minutes=10, out_dir=tmp_path / "gate", reservation_dir=res, open_scan_limit=100)
    assert pbp._cmd_predispatch(pargs, client(world("bob/single"))) == 0
    token = json.loads(next(res.glob("*.lock")).read_text())["token"]
    assert pbp._cmd_predispatch(pargs, client(world("bob/single"))) == 2  # already reserved
    assert (tmp_path / "gate" / "predispatch.json").exists()

    url = "https://github.com/bob/single/pull/1"
    base = ["record-outcome", "--manifest", str(mpath), "--repo", SINGLE, "--status", "PR_OPEN",
            "--pr-url", url, "--reservation-dir", str(res)]
    r = _cli(*base)
    assert r.returncode != 0 and "reservation-token" in r.stderr
    r = _cli(*base, "--reservation-token", "bogus")
    assert r.returncode != 0 and "reservation invalid" in r.stderr
    assert json.loads(mpath.read_text())["repositories"][SINGLE]["status"] == "APPROVED"

    # Two concurrent processes race with the same valid token: exactly one records the PR.
    procs = [subprocess.Popen([sys.executable, "scripts/plan_badge_provisioning.py", *base, "--reservation-token", token],
                              cwd=REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(2)]
    codes = sorted(p.wait(timeout=60) for p in procs)
    for p in procs:
        p.stdout.close()
        p.stderr.close()
    assert codes[0] == 0 and codes[1] != 0
    rec = json.loads(mpath.read_text())["repositories"][SINGLE]
    assert rec["status"] == "PR_OPEN" and rec["provisioning"]["attempts"] == 1
    assert not list(res.glob("*.lock"))  # reservation consumed
    # History preserved append-only
    assert [h["to_status"] for h in rec["provisioning"]["history"]] == ["APPROVED", "PR_OPEN"]


@pytest.mark.integration
def test_cli_old_token_cannot_record_pr_after_decline(tmp_path, registry, manifest):
    mpath, reg, res = tmp_path / "manifest.json", tmp_path / "registry.json", tmp_path / "res"
    approve(manifest, SINGLE)
    _write_manifest(mpath, manifest)
    reg.write_text(json.dumps(registry), encoding="utf-8")
    pargs = Namespace(manifest=mpath, registry=reg, campaign_author=None, repo=SINGLE, worker="w",
                      ttl_minutes=10, out_dir=None, reservation_dir=res, open_scan_limit=100)
    assert pbp._cmd_predispatch(pargs, client(world("bob/single"))) == 0
    token = json.loads(next(res.glob("*.lock")).read_text())["token"]

    r = _cli("record-outcome", "--manifest", str(mpath), "--repo", SINGLE, "--status", "DECLINED",
             "--notes", "maintainer declined", "--reservation-dir", str(res))
    assert r.returncode == 0, r.stderr
    assert not list(res.glob("*.lock"))  # any other ledger change voids the outstanding reservation

    r = _cli("record-outcome", "--manifest", str(mpath), "--repo", SINGLE, "--status", "PR_OPEN",
             "--pr-url", "https://github.com/bob/single/pull/1", "--reservation-token", token,
             "--reservation-dir", str(res))
    assert r.returncode != 0
    rec = json.loads(mpath.read_text())["repositories"][SINGLE]
    assert rec["status"] == "DECLINED" and not rec["provisioning"].get("pr_url")


def test_atomic_manifest_write_leaves_no_temp_files(tmp_path, manifest):
    p = tmp_path / "m.json"
    pbp.write_manifest_atomic(p, manifest)
    assert json.loads(p.read_text()) == manifest
    assert [x.name for x in tmp_path.iterdir()] == ["m.json"]


def test_search_calls_are_spaced_across_threads_but_other_calls_are_not():
    slept: list[float] = []
    t = [100.0]
    gh = world("bob/single")
    c = br.GitHubClient(gh, sleep=slept.append, clock=lambda: t[0], search_intervals={"issues": 2.0, "code": 6.0})
    c.get("/search/issues?q=a")
    c.get("/search/issues?q=b")      # same instant: must wait one interval
    c.get("/search/code?q=c")        # separate bucket: no wait
    c.get("/repos/bob/single")       # non-search: never throttled
    assert slept == [2.0]


def test_known_migrations_mirror_planner():
    assert br.KNOWN_MIGRATIONS == {k.lower(): v.lower() for k, v in pbp.REPO_MIGRATIONS.items()}


def test_rate_limit_trips_circuit_breaker_and_stops_spending_calls(registry, manifest):
    gh = world("bob/single")
    gh.add("/repos/bob/single", {"message": "API rate limit exceeded"}, status=403, headers={"x-ratelimit-remaining": "0"})
    c = client(gh)
    key, rec = br.find_record(manifest, SINGLE)
    e = br.reconcile_repo(c, key, rec, registry, now=now)
    assert e["classification"] == "UNKNOWN"
    n = len(gh.calls)
    e2 = br.reconcile_repo(c, key, rec, registry, now=now)
    assert e2["classification"] == "UNKNOWN" and len(gh.calls) == n  # no further API calls
