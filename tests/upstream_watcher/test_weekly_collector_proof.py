"""Offline collector provenance proof tests (P2 Slice 3).

Exercises the real watcher/liveness/repository_batch/weekly_reducer seams with
strictly fake transports (network trap installed) and zero GitHub writes.
"""

from __future__ import annotations

import copy
import urllib.request
from typing import Any
from urllib.parse import quote

import pytest
from upstream_fakes import FakeGh, index_from_entries

from scripts.lib.github_api import GitHubFetchError
from scripts.upstream_watcher import (
    batch,
    envelope,
    liveness,
    name_drift,
    repository_batch,
    watcher,
    weekly_collector,
    weekly_reducer,
)
from scripts.upstream_watcher.live import SuiteUnavailable, UnknownEvidenceError
from scripts.upstream_watcher.weekly_reducer import (
    DECISION_HELD_SCOPE,
    DECISION_UNAVAILABLE,
    PRESENCE_PRESENT_CANDIDATE,
    PRESENCE_PRESENT_TRACKED,
    PRESENCE_UNKNOWN,
    PRESENCE_VANISHED,
    ReducerConfig,
    empty_state,
    reduce_poll,
)

# ---------------------------------------------------------------------------
# Offline fake GitHub upstream transport + network trap
# ---------------------------------------------------------------------------


def _fake_policy() -> dict[str, Any]:
    return {
        "direction": {
            "shared_source_model": "repo_envelope",
            "legacy_transition": "preserve_plan",
            "decisions": {
                "shared_source_model": "repo_envelope",
                "legacy_transition": "preserve_plan",
            },
        },
        "referencePolicy": {
            "planPolicyVersion": 1,
            "planOnly": True,
            "historicalAuthorityCommit": "0" * 40,
            "directionRecord": "founder/reports/upstream-backlog-2026-11/direction.json",
        },
        "shared_source_model": "repo_envelope",
        "legacy_transition": "preserve_plan",
    }


def _tree_payload(
    *,
    root: str = "skills",
    slug_paths: list[str] | None = None,
    extra_entries: list[dict[str, Any]] | None = None,
    include_root: bool = True,
    truncated: Any = False,
    sha: str | None = "a" * 40,
) -> dict[str, Any]:
    """Build a GitHub recursive git/trees response dict."""
    entries: list[dict[str, Any]] = []
    if include_root and root:
        parts = root.strip("/").split("/")
        built = ""
        for part in parts:
            built = f"{built}/{part}" if built else part
            entries.append({"path": built, "type": "tree", "sha": "b" * 40})
    for rel_skill_path in slug_paths or []:
        entries.append({"path": rel_skill_path, "type": "blob", "sha": "c" * 40})
    if extra_entries:
        entries.extend(extra_entries)
    payload: dict[str, Any] = {"tree": entries}
    if sha is not None:
        payload["sha"] = sha
    if truncated is not None:
        payload["truncated"] = truncated
    return payload


class FakeUpstreamTransport:
    """In-memory fake for GitHub releases, git trees, HEAD liveness, and raw SKILL.md."""

    def __init__(self) -> None:
        self.releases: dict[str, dict[str, Any] | Exception] = {}
        self.trees: dict[str, dict[str, Any] | Exception] = {}
        self.subtrees: dict[str, dict[str, Any] | Exception] = {}
        self.head_statuses: dict[str, int | None] = {}
        self.raw_texts: dict[str, str | None] = {}
        self.json_calls: list[str] = []
        self.head_calls: list[str] = []
        self.text_calls: list[str] = []

    def set_release(
        self,
        owner: str,
        repo: str,
        tag: str,
        *,
        published_at: str = "2026-11-18T12:00:00Z",
        html_url: str | None = None,
    ) -> None:
        key = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
        self.releases[key] = {
            "tag_name": tag,
            "published_at": published_at,
            "html_url": html_url
            if html_url is not None
            else f"https://github.com/{owner}/{repo}/releases/tag/{quote(tag, safe='')}",
        }

    def set_tree(self, owner: str, repo: str, tag: str, payload: dict[str, Any] | Exception) -> None:
        url = f"{liveness.tree_base_url(owner, repo)}/{quote(tag, safe='')}?recursive=1"
        self.trees[url] = payload

    def set_subtree(self, owner: str, repo: str, ref: str, payload: dict[str, Any] | Exception) -> None:
        url = f"{liveness.tree_base_url(owner, repo)}/{quote(ref, safe='')}"
        self.subtrees[url] = payload

    def tree_call_count(self, owner: str, repo: str, tag: str) -> int:
        url = f"{liveness.tree_base_url(owner, repo)}/{quote(tag, safe='')}?recursive=1"
        return sum(1 for call in self.json_calls if call == url)

    def fetch_json(self, url: str, token: str | None = None, timeout: int = 10, *, strict: bool = False) -> Any:
        self.json_calls.append(url)
        if url in self.releases:
            val = self.releases[url]
            if isinstance(val, Exception):
                raise val
            return copy.deepcopy(val)
        if url in self.trees:
            val = self.trees[url]
            if isinstance(val, Exception):
                raise val
            return copy.deepcopy(val)
        if url in self.subtrees:
            val = self.subtrees[url]
            if isinstance(val, Exception):
                raise val
            return copy.deepcopy(val)
        raise GitHubFetchError(f"unexpected fake GitHub URL: {url}", status=404)

    def head_check(self, url: str, timeout: int = 10) -> int | None:
        self.head_calls.append(url)
        return self.head_statuses.get(url, 200)

    def fetch_text(self, url: str, timeout: int = 10) -> str | None:
        self.text_calls.append(url)
        return self.raw_texts.get(url, "---\nname: base\n---\n")


@pytest.fixture()
def fake_transport(monkeypatch: pytest.MonkeyPatch) -> FakeUpstreamTransport:
    """Install a strict network trap + fake GitHub upstream transport."""
    transport = FakeUpstreamTransport()

    def _forbid_network(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError(f"Accidental real network call attempted: args={args!r}")

    monkeypatch.setattr(urllib.request, "urlopen", _forbid_network)
    monkeypatch.setattr(watcher, "fetch_json", transport.fetch_json)
    monkeypatch.setattr(liveness, "fetch_json", transport.fetch_json)
    monkeypatch.setattr(liveness, "head_check", transport.head_check)
    monkeypatch.setattr(name_drift, "fetch_text", transport.fetch_text)
    return transport


def _make_suite_authority(
    *,
    suite_id: str = "alice/widgets",
    owner: str = "acme",
    repo: str = "widgets",
    version: str | None = "v1.0.0",
    components: list[str] | None = None,
    component_root: str | None = None,
    extra_component_repo: dict[str, str] | None = None,
) -> dict[str, dict[str, Any]]:
    comp_ids = list(components) if components is not None else ["alice/base"]
    root = component_root if component_root is not None else "skills"
    suite_fm: dict[str, Any] = {
        "id": suite_id,
        "level": "3★",
        "links": {"github": f"https://github.com/{owner}/{repo}"},
        "suiteComponents": comp_ids,
    }
    if version is not None:
        suite_fm["upstream"] = {"repo": f"{owner}/{repo}", "version": version}
    if component_root is not None:
        suite_fm["upstreamComponentRoot"] = component_root

    authority: dict[str, dict[str, Any]] = {suite_id: suite_fm}
    for comp_id in comp_ids:
        slug = comp_id.rsplit("/", 1)[-1]
        comp_repo = (extra_component_repo or {}).get(comp_id, f"{owner}/{repo}")
        authority[comp_id] = {
            "id": comp_id,
            "level": "2★",
            "links": {"github": f"https://github.com/{comp_repo}/blob/main/{root}/{slug}/SKILL.md"},
        }
    return authority


def _run_offline_cycle(
    suites: list[dict[str, Any]],
    authority: dict[str, dict[str, Any]],
    *,
    poll_id: str,
    observed_at: str,
    gh: FakeGh,
    state: weekly_reducer.ReducerState,
    config: ReducerConfig | None = None,
    historical_map: dict[str, dict[str, Any]] | None = None,
    override_collected: weekly_collector.CollectedPoll | None = None,
    use_collected: bool = True,
) -> tuple[
    weekly_collector.CollectedPoll,
    dict[str, Any],
    int,
    weekly_reducer.PollInput,
    weekly_reducer.PollReductionResult,
]:
    collected = weekly_collector.collect_suites(suites, authority, poll_id=poll_id)
    entries = [
        {"id": sid, "github": (meta.get("links") or {}).get("github", "")}
        for sid, meta in authority.items()
    ]
    report, code = repository_batch.run_repository_batch(
        list(collected.observed_findings),
        gh,
        apply=False,
        authority=authority,
        index_loader=lambda: index_from_entries(entries),
        policy=_fake_policy(),
        historical_loader=lambda sid: {sid: historical_map[sid]} if historical_map and sid in historical_map else {},
        plan_only=True,
    )
    passed_collected = (
        override_collected if override_collected is not None else (collected if use_collected else None)
    )
    poll_input = weekly_collector.build_poll_input(
        poll_id,
        observed_at,
        report,
        passed_collected,
        authority,
    )
    reduced = reduce_poll(state, poll_input, authority, config=config)
    return collected, report, code, poll_input, reduced


# ---------------------------------------------------------------------------
# 1. End-to-end lifecycle: untracked -> adopted (empty delta) -> proved absent + replay
# ---------------------------------------------------------------------------


def test_end_to_end_untracked_adopted_vanished_and_replay(fake_transport: FakeUpstreamTransport):
    gh = FakeGh()
    state = empty_state()

    # Poll 1: alpha is untracked upstream -> present-candidate with FirstSeenPin
    auth1 = _make_suite_authority(version="v1.0.0", components=["alice/base"])
    fake_transport.set_release("acme", "widgets", "v1.1.0", published_at="2026-11-17T10:00:00Z")
    fake_transport.set_tree(
        "acme",
        "widgets",
        "v1.1.0",
        _tree_payload(slug_paths=["skills/base/SKILL.md", "skills/alpha/SKILL.md"]),
    )
    c1, r1, code1, p1, res1 = _run_offline_cycle(
        [auth1["alice/widgets"]],
        auth1,
        poll_id="poll-1",
        observed_at="2026-11-17T12:00:00Z",
        gh=gh,
        state=state,
    )
    assert code1 == 0
    assert gh.write_count() == 0
    assert fake_transport.tree_call_count("acme", "widgets", "v1.1.0") == 1
    assert c1.results[0].proof_reason is None
    assert c1.results[0].complete_inventory is not None
    assert r1["observedFindings"][0]["componentAdds"] == ["alpha"]
    assert r1["observedFindings"][0]["componentRemoves"] == []
    assert res1.status == "applied"
    assert res1.write_authorized is False
    bucket1 = res1.state.get_bucket("acme/widgets", "alice/widgets")
    assert bucket1 is not None
    assert bucket1.rows["acme/widgets:alpha"].presence == PRESENCE_PRESENT_CANDIDATE
    pin1 = bucket1.rows["acme/widgets:alpha"].first_seen_pin
    assert pin1.first_seen_version == "v1.1.0"
    assert pin1.first_seen_poll_id == "poll-1"

    # Poll 2: alpha adopted into suiteComponents and still upstream -> empty delta, present-tracked
    auth2 = _make_suite_authority(version="v1.1.0", components=["alice/base", "alice/alpha"])
    fake_transport.set_release("acme", "widgets", "v1.2.0", published_at="2026-11-18T10:00:00Z")
    fake_transport.set_tree(
        "acme",
        "widgets",
        "v1.2.0",
        _tree_payload(slug_paths=["skills/base/SKILL.md", "skills/alpha/SKILL.md"]),
    )
    c2, r2, code2, p2, res2 = _run_offline_cycle(
        [auth2["alice/widgets"]],
        auth2,
        poll_id="poll-2",
        observed_at="2026-11-18T12:00:00Z",
        gh=gh,
        state=res1.state,
    )
    assert code2 == 0
    assert gh.write_count() == 0
    assert fake_transport.tree_call_count("acme", "widgets", "v1.2.0") == 1
    assert r2["observedFindings"][0]["componentAdds"] == []
    assert r2["observedFindings"][0]["componentRemoves"] == []
    assert c2.results[0].complete_inventory is not None
    assert c2.results[0].complete_inventory.present_slugs == frozenset({"base", "alpha"})
    assert res2.status == "applied"
    bucket2 = res2.state.get_bucket("acme/widgets", "alice/widgets")
    assert bucket2 is not None
    assert bucket2.rows["acme/widgets:alpha"].presence == PRESENCE_PRESENT_TRACKED
    assert bucket2.rows["acme/widgets:alpha"].first_seen_pin == pin1
    assert bucket2.rows["acme/widgets:alpha"].vanished_at is None

    # Poll 3: alpha removed upstream -> raw short diff ["alpha"] + canonical full ID ["alice/alpha"] + vanished
    auth3 = _make_suite_authority(version="v1.2.0", components=["alice/base", "alice/alpha"])
    fake_transport.set_release("acme", "widgets", "v1.3.0", published_at="2026-11-19T10:00:00Z")
    fake_transport.set_tree(
        "acme",
        "widgets",
        "v1.3.0",
        _tree_payload(slug_paths=["skills/base/SKILL.md"]),
    )
    c3, r3, code3, p3, res3 = _run_offline_cycle(
        [auth3["alice/widgets"]],
        auth3,
        poll_id="poll-3",
        observed_at="2026-11-19T12:00:00Z",
        gh=gh,
        state=res2.state,
    )
    assert code3 == 0
    assert gh.write_count() == 0
    assert fake_transport.tree_call_count("acme", "widgets", "v1.3.0") == 1
    # Raw finding keeps exact short slug; canonical planned finding resolves full named ID.
    assert r3["observedFindings"][0]["componentAdds"] == []
    assert r3["observedFindings"][0]["componentRemoves"] == ["alpha"]
    planned_finding = r3["repositories"][0]["payload"]["findings"][0]
    assert planned_finding["componentRemoves"] == ["alice/alpha"]
    assert res3.status == "applied"
    assert res3.write_authorized is False
    bucket3 = res3.state.get_bucket("acme/widgets", "alice/widgets")
    assert bucket3 is not None
    assert bucket3.rows["acme/widgets:alpha"].presence == PRESENCE_VANISHED
    assert bucket3.rows["acme/widgets:alpha"].vanished_at == "2026-11-19T12:00:00Z"
    assert bucket3.rows["acme/widgets:alpha"].vanished_poll_id == "poll-3"
    assert bucket3.rows["acme/widgets:alpha"].first_seen_pin == pin1

    # Exact current poll replay is idempotent with zero mutations.
    replay = reduce_poll(res3.state, p3, auth3)
    assert replay.status == "replayed"
    assert replay.replayed is True
    assert replay.eligible == ()
    assert replay.state == res3.state
    assert gh.write_count() == 0


# ---------------------------------------------------------------------------
# 2. Same repo, same release, same slug, two roots — zero cross-sibling proof
# ---------------------------------------------------------------------------


def test_same_repo_same_release_same_slug_two_roots_isolated(fake_transport: FakeUpstreamTransport):
    gh = FakeGh()

    def _two_root_auth(version: str, adopted: bool) -> dict[str, dict[str, Any]]:
        comps_a = ["alice/base-a", "alice/shared"] if adopted else ["alice/base-a"]
        comps_b = ["bob/base-b", "bob/shared"] if adopted else ["bob/base-b"]
        a = _make_suite_authority(
            suite_id="alice/suite-a",
            owner="acme",
            repo="monorepo",
            version=version,
            components=comps_a,
            component_root="skills-a",
        )
        b = _make_suite_authority(
            suite_id="bob/suite-b",
            owner="acme",
            repo="monorepo",
            version=version,
            components=comps_b,
            component_root="skills-b",
        )
        return {**a, **b}

    # Poll 1: both roots contain slug "shared" as untracked candidate
    auth1 = _two_root_auth("v1.0.0", adopted=False)
    fake_transport.set_release("acme", "monorepo", "v2.0.0")
    fake_transport.set_tree(
        "acme",
        "monorepo",
        "v2.0.0",
        {
            "sha": "d" * 40,
            "truncated": False,
            "tree": [
                {"path": "skills-a", "type": "tree", "sha": "1" * 40},
                {"path": "skills-a/base-a/SKILL.md", "type": "blob", "sha": "2" * 40},
                {"path": "skills-a/shared/SKILL.md", "type": "blob", "sha": "3" * 40},
                {"path": "skills-b", "type": "tree", "sha": "4" * 40},
                {"path": "skills-b/base-b/SKILL.md", "type": "blob", "sha": "5" * 40},
                {"path": "skills-b/shared/SKILL.md", "type": "blob", "sha": "6" * 40},
            ],
        },
    )
    _, _, code1, _, res1 = _run_offline_cycle(
        [auth1["alice/suite-a"], auth1["bob/suite-b"]],
        auth1,
        poll_id="mono-1",
        observed_at="2026-11-17T12:00:00Z",
        gh=gh,
        state=empty_state(),
    )
    assert code1 == 0
    assert res1.state.get_bucket("acme/monorepo", "alice/suite-a").rows["acme/monorepo:shared"].presence == PRESENCE_PRESENT_CANDIDATE
    assert res1.state.get_bucket("acme/monorepo", "bob/suite-b").rows["acme/monorepo:shared"].presence == PRESENCE_PRESENT_CANDIDATE

    # Poll 2: skills-a removes "shared", skills-b keeps "shared" -> independent proofs
    auth2 = _two_root_auth("v2.0.0", adopted=True)
    fake_transport.set_release("acme", "monorepo", "v2.1.0")
    fake_transport.set_tree(
        "acme",
        "monorepo",
        "v2.1.0",
        {
            "sha": "e" * 40,
            "truncated": False,
            "tree": [
                {"path": "skills-a", "type": "tree", "sha": "1" * 40},
                {"path": "skills-a/base-a/SKILL.md", "type": "blob", "sha": "2" * 40},
                {"path": "skills-b", "type": "tree", "sha": "4" * 40},
                {"path": "skills-b/base-b/SKILL.md", "type": "blob", "sha": "5" * 40},
                {"path": "skills-b/shared/SKILL.md", "type": "blob", "sha": "6" * 40},
            ],
        },
    )
    _, _, code2, _, res2 = _run_offline_cycle(
        [auth2["alice/suite-a"], auth2["bob/suite-b"]],
        auth2,
        poll_id="mono-2",
        observed_at="2026-11-18T12:00:00Z",
        gh=gh,
        state=res1.state,
    )
    assert code2 == 0
    assert res2.state.get_bucket("acme/monorepo", "alice/suite-a").rows["acme/monorepo:shared"].presence == PRESENCE_VANISHED
    assert res2.state.get_bucket("acme/monorepo", "bob/suite-b").rows["acme/monorepo:shared"].presence == PRESENCE_PRESENT_TRACKED

    # Poll 3: skills-a verified, skills-b missing root -> skills-b stays UNKNOWN (no cross-sibling proof)
    auth3 = _two_root_auth("v2.1.0", adopted=True)
    fake_transport.set_release("acme", "monorepo", "v2.2.0")
    fake_transport.set_tree(
        "acme",
        "monorepo",
        "v2.2.0",
        {
            "sha": "f" * 40,
            "truncated": False,
            "tree": [
                {"path": "skills-a", "type": "tree", "sha": "1" * 40},
                {"path": "skills-a/base-a/SKILL.md", "type": "blob", "sha": "2" * 40},
            ],
        },
    )
    c3, _, code3, _, res3 = _run_offline_cycle(
        [auth3["alice/suite-a"], auth3["bob/suite-b"]],
        auth3,
        poll_id="mono-3",
        observed_at="2026-11-19T12:00:00Z",
        gh=gh,
        state=res2.state,
    )
    assert code3 == 0
    by_id = {r.named_id: r for r in c3.results}
    assert by_id["alice/suite-a"].complete_inventory is not None
    assert by_id["bob/suite-b"].complete_inventory is None
    assert by_id["bob/suite-b"].proof_reason == "missing-component-root"
    assert res3.state.get_bucket("acme/monorepo", "bob/suite-b").rows["acme/monorepo:shared"].presence == PRESENCE_UNKNOWN
    assert gh.write_count() == 0


# ---------------------------------------------------------------------------
# 3. Conservative unknown cases: none may infer vanished
# ---------------------------------------------------------------------------


def _seed_candidate_state(
    fake_transport: FakeUpstreamTransport,
    gh: FakeGh,
) -> tuple[weekly_reducer.ReducerState, dict[str, dict[str, Any]]]:
    auth = _make_suite_authority(version="v1.0.0", components=["alice/base"])
    fake_transport.set_release("acme", "widgets", "v1.1.0")
    fake_transport.set_tree(
        "acme",
        "widgets",
        "v1.1.0",
        _tree_payload(slug_paths=["skills/base/SKILL.md", "skills/alpha/SKILL.md"]),
    )
    _, _, code, _, res = _run_offline_cycle(
        [auth["alice/widgets"]],
        auth,
        poll_id="seed-1",
        observed_at="2026-11-17T12:00:00Z",
        gh=gh,
        state=empty_state(),
    )
    assert code == 0
    assert res.state.get_bucket("acme/widgets", "alice/widgets").rows["acme/widgets:alpha"].presence == PRESENCE_PRESENT_CANDIDATE
    return res.state, auth


@pytest.mark.parametrize(
    "case_name,tree_payload,expected_reason",
    [
        (
            "missing-root",
            _tree_payload(include_root=False, slug_paths=[]),
            "missing-component-root",
        ),
        (
            "truncation-flag-omitted",
            _tree_payload(slug_paths=["skills/base/SKILL.md"], truncated=None),
            "truncation-flag-not-false",
        ),
        (
            "missing-tree-sha",
            _tree_payload(slug_paths=["skills/base/SKILL.md"], sha=None),
            "missing-tree-sha",
        ),
        (
            "submodule-under-root",
            _tree_payload(
                slug_paths=["skills/base/SKILL.md"],
                extra_entries=[{"path": "skills/submod", "type": "commit", "sha": "9" * 40}],
            ),
            "submodule-under-root",
        ),
        (
            "malformed-tree-entry",
            _tree_payload(
                slug_paths=["skills/base/SKILL.md"],
                extra_entries=[{"path": "skills/weird", "type": "unknown-type"}],
            ),
            "malformed-tree-entry",
        ),
        (
            "duplicate-tree-path",
            _tree_payload(
                slug_paths=["skills/base/SKILL.md", "skills/base/SKILL.md"],
            ),
            "duplicate-tree-path",
        ),
        (
            "ambiguous-slug-path",
            _tree_payload(
                slug_paths=[
                    "skills/base/SKILL.md",
                    "skills/cat-a/dup/SKILL.md",
                    "skills/cat-b/dup/SKILL.md",
                ],
            ),
            "ambiguous-slug-path",
        ),
    ],
)
def test_unqualified_trees_stay_conservative_unknown(
    fake_transport: FakeUpstreamTransport,
    case_name: str,
    tree_payload: dict[str, Any],
    expected_reason: str,
):
    gh = FakeGh()
    seeded_state, _ = _seed_candidate_state(fake_transport, gh)

    # Next release omits alpha, but the tree fails complete-inventory proof -> must remain UNKNOWN
    auth2 = _make_suite_authority(version="v1.1.0", components=["alice/base"])
    fake_transport.set_release("acme", "widgets", "v1.2.0")
    fake_transport.set_tree("acme", "widgets", "v1.2.0", tree_payload)
    c2, _, code2, _, res2 = _run_offline_cycle(
        [auth2["alice/widgets"]],
        auth2,
        poll_id=f"poll-{case_name}",
        observed_at="2026-11-18T12:00:00Z",
        gh=gh,
        state=seeded_state,
    )
    assert code2 == 0
    assert c2.results[0].complete_inventory is None
    assert c2.results[0].proof_reason == expected_reason
    bucket = res2.state.get_bucket("acme/widgets", "alice/widgets")
    assert bucket is not None
    assert bucket.rows["acme/widgets:alpha"].presence == PRESENCE_UNKNOWN
    assert bucket.rows["acme/widgets:alpha"].vanished_at is None
    assert gh.write_count() == 0


def test_invalid_slug_in_tree_fails_closed_without_vanished(fake_transport: FakeUpstreamTransport):
    gh = FakeGh()
    seeded_state, _ = _seed_candidate_state(fake_transport, gh)

    auth2 = _make_suite_authority(version="v1.1.0", components=["alice/base"])
    fake_transport.set_release("acme", "widgets", "v1.2.0")
    fake_transport.set_tree(
        "acme",
        "widgets",
        "v1.2.0",
        _tree_payload(slug_paths=["skills/base/SKILL.md", "skills/.hidden/SKILL.md"]),
    )
    c2, r2, code2, p2, res2 = _run_offline_cycle(
        [auth2["alice/widgets"]],
        auth2,
        poll_id="poll-invalid-slug",
        observed_at="2026-11-18T12:00:00Z",
        gh=gh,
        state=seeded_state,
    )
    assert c2.results[0].complete_inventory is None
    assert c2.results[0].proof_reason == "invalid-slug"
    assert code2 == 3
    assert r2["unknownEvidence"]
    assert p2.complete is False
    assert res2.status == "rejected"
    assert res2.state == seeded_state
    assert gh.write_count() == 0


def test_truncated_tree_walk_never_claims_complete_inventory(fake_transport: FakeUpstreamTransport):
    """Even when walk_truncated_tree succeeds for raw diff, Slice 3 keeps presence UNKNOWN."""
    gh = FakeGh()
    seeded_state, _ = _seed_candidate_state(fake_transport, gh)

    auth2 = _make_suite_authority(version="v1.1.0", components=["alice/base"])
    fake_transport.set_release("acme", "widgets", "v1.2.0")
    fake_transport.set_tree(
        "acme",
        "widgets",
        "v1.2.0",
        _tree_payload(slug_paths=["skills/base/SKILL.md"], truncated=True),
    )
    # Provide valid non-recursive subtrees so walk_truncated_tree succeeds for the raw diff
    fake_transport.set_subtree(
        "acme", "widgets", "v1.2.0", {"tree": [{"path": "skills", "type": "tree", "sha": "rootsha"}]}
    )
    fake_transport.set_subtree(
        "acme", "widgets", "rootsha", {"tree": [{"path": "base", "type": "tree", "sha": "basesha"}]}
    )
    fake_transport.set_subtree(
        "acme", "widgets", "basesha", {"tree": [{"path": "SKILL.md", "type": "blob", "sha": "blobsha"}]}
    )

    c2, _, code2, _, res2 = _run_offline_cycle(
        [auth2["alice/widgets"]],
        auth2,
        poll_id="poll-truncated-walk",
        observed_at="2026-11-18T12:00:00Z",
        gh=gh,
        state=seeded_state,
    )
    assert code2 == 0
    assert c2.results[0].complete_inventory is None
    assert c2.results[0].proof_reason == "tree-truncated"
    assert c2.results[0].enumeration is not None
    assert c2.results[0].enumeration.truncated is True
    assert c2.results[0].enumeration.complete is False
    bucket = res2.state.get_bucket("acme/widgets", "alice/widgets")
    assert bucket is not None
    assert bucket.rows["acme/widgets:alpha"].presence == PRESENCE_UNKNOWN
    assert gh.write_count() == 0


def test_version_only_and_bootstrap_cannot_infer_vanished(fake_transport: FakeUpstreamTransport):
    gh = FakeGh()
    seeded_state, _ = _seed_candidate_state(fake_transport, gh)

    # Version-only: component points to external repo so detect_mode -> "version-only"
    auth_vo = _make_suite_authority(
        version="v1.1.0",
        components=["alice/base"],
        extra_component_repo={"alice/base": "other/external"},
    )
    fake_transport.set_release("acme", "widgets", "v1.2.0")
    c_vo, _, code_vo, _, res_vo = _run_offline_cycle(
        [auth_vo["alice/widgets"]],
        auth_vo,
        poll_id="poll-vo",
        observed_at="2026-11-18T12:00:00Z",
        gh=gh,
        state=seeded_state,
    )
    assert code_vo == 0
    assert c_vo.results[0].complete_inventory is None
    assert c_vo.results[0].proof_reason == "non-component-mode"
    assert res_vo.state.get_bucket("acme/widgets", "alice/widgets").rows["acme/widgets:alpha"].presence == PRESENCE_UNKNOWN

    # Bootstrap: no stored upstream version
    auth_boot = _make_suite_authority(version=None, components=["alice/base"])
    fake_transport.set_release("acme", "widgets", "v1.3.0")
    c_boot, _, code_boot, _, res_boot = _run_offline_cycle(
        [auth_boot["alice/widgets"]],
        auth_boot,
        poll_id="poll-boot",
        observed_at="2026-11-19T12:00:00Z",
        gh=gh,
        state=seeded_state,
    )
    assert code_boot == 0
    assert c_boot.results[0].complete_inventory is None
    assert c_boot.results[0].proof_reason == "bootstrap-finding"
    assert res_boot.state.get_bucket("acme/widgets", "alice/widgets").rows["acme/widgets:alpha"].presence == PRESENCE_UNKNOWN


def test_stale_raw_p1_report_and_copied_poll_cannot_promote(fake_transport: FakeUpstreamTransport):
    gh = FakeGh()
    seeded_state, _ = _seed_candidate_state(fake_transport, gh)

    auth2 = _make_suite_authority(version="v1.1.0", components=["alice/base"])
    fake_transport.set_release("acme", "widgets", "v1.2.0")
    fake_transport.set_tree(
        "acme", "widgets", "v1.2.0", _tree_payload(slug_paths=["skills/base/SKILL.md"])
    )

    # Stale raw P1 report (collected=None) leaves omitted row UNKNOWN
    _, _, code_raw, p_raw, res_raw = _run_offline_cycle(
        [auth2["alice/widgets"]],
        auth2,
        poll_id="poll-raw-p1",
        observed_at="2026-11-18T12:00:00Z",
        gh=gh,
        state=seeded_state,
        use_collected=False,
    )
    assert code_raw == 0
    assert p_raw.complete_inventories == ()
    assert res_raw.state.get_bucket("acme/widgets", "alice/widgets").rows["acme/widgets:alpha"].presence == PRESENCE_UNKNOWN

    # Copied CollectedPoll from an older poll_id cannot be promoted under a new poll_id
    old_collected = weekly_collector.collect_suites(
        [auth2["alice/widgets"]], auth2, poll_id="poll-old"
    )
    assert len(old_collected.complete_inventories) == 1
    _, _, code_copy, p_copy, res_copy = _run_offline_cycle(
        [auth2["alice/widgets"]],
        auth2,
        poll_id="poll-new",
        observed_at="2026-11-19T12:00:00Z",
        gh=gh,
        state=seeded_state,
        override_collected=old_collected,
    )
    assert code_copy == 0
    assert p_copy.complete_inventories == ()
    assert res_copy.state.get_bucket("acme/widgets", "alice/widgets").rows["acme/widgets:alpha"].presence == PRESENCE_UNKNOWN


# ---------------------------------------------------------------------------
# 4. Forged repo / tag / source / root / diff & case-sensitive authority
# ---------------------------------------------------------------------------


def test_forged_release_source_locked_source_root_and_diff_fail_closed(
    fake_transport: FakeUpstreamTransport,
):
    gh = FakeGh()
    seeded_state, _ = _seed_candidate_state(fake_transport, gh)

    # Forged release html_url pointing to wrong repo/tag
    auth = _make_suite_authority(version="v1.1.0", components=["alice/base"])
    fake_transport.set_release(
        "acme",
        "widgets",
        "v1.2.0",
        html_url="https://github.com/evil/widgets/releases/tag/v1.2.0",
    )
    fake_transport.set_tree(
        "acme", "widgets", "v1.2.0", _tree_payload(slug_paths=["skills/base/SKILL.md"])
    )
    res_forged_url = weekly_collector.collect_suite_observation(
        auth["alice/widgets"], auth, poll_id="poll-forged-url"
    )
    assert res_forged_url.complete_inventory is None
    assert res_forged_url.proof_reason is not None

    # Locked source violation (ruvnet/agentdb pointing to ruvnet/ruflo) -> unknown
    bad_locked = {
        "ruvnet/agentdb": {
            "id": "ruvnet/agentdb",
            "level": "3★",
            "links": {"github": "https://github.com/ruvnet/ruflo"},
            "upstream": {"repo": "ruvnet/ruflo", "version": "v1.0.0"},
            "suiteComponents": ["ruvnet/sub"],
        },
        "ruvnet/sub": {
            "id": "ruvnet/sub",
            "level": "2★",
            "links": {"github": "https://github.com/ruvnet/ruflo/blob/main/skills/sub/SKILL.md"},
        },
    }
    res_locked = weekly_collector.collect_suite_observation(
        bad_locked["ruvnet/agentdb"], bad_locked, poll_id="poll-locked"
    )
    assert res_locked.status == "unknown"
    assert res_locked.complete_inventory is None

    # Case-mismatched named_id not matching exact case-sensitive authority -> unknown
    wrong_case_fm = {**auth["alice/widgets"], "id": "Alice/Widgets"}
    res_case = weekly_collector.collect_suite_observation(
        wrong_case_fm, auth, poll_id="poll-case"
    )
    assert res_case.status == "unknown"
    assert res_case.complete_inventory is None

    # Malformed upstreamComponentRoot in authority -> never proves absence
    bad_root_auth = _make_suite_authority(
        version="v1.1.0", components=["alice/base"], component_root="../evil"
    )
    fake_transport.set_release("acme", "widgets", "v1.2.0")
    fake_transport.set_tree(
        "acme", "widgets", "v1.2.0", _tree_payload(root="../evil", slug_paths=[])
    )
    res_bad_root = weekly_collector.collect_suite_observation(
        bad_root_auth["alice/widgets"], bad_root_auth, poll_id="poll-bad-root"
    )
    assert res_bad_root.complete_inventory is None
    assert res_bad_root.proof_reason is not None

    # Forged diff in report["observedFindings"] after collection -> inventory dropped, never vanishes
    fake_transport.set_release("acme", "widgets", "v1.2.0")
    fake_transport.set_tree(
        "acme", "widgets", "v1.2.0", _tree_payload(slug_paths=["skills/base/SKILL.md"])
    )
    collected = weekly_collector.collect_suites([auth["alice/widgets"]], auth, poll_id="poll-tamper")
    assert len(collected.complete_inventories) == 1
    entries = [{"id": sid, "github": (m.get("links") or {}).get("github", "")} for sid, m in auth.items()]
    report, code = repository_batch.run_repository_batch(
        list(collected.observed_findings),
        gh,
        apply=False,
        authority=auth,
        index_loader=lambda: index_from_entries(entries),
        policy=_fake_policy(),
        plan_only=True,
    )
    assert code == 0
    tampered_report = copy.deepcopy(report)
    tampered_report["observedFindings"][0]["componentRemoves"] = ["forged-slug"]
    poll_tampered = weekly_collector.build_poll_input(
        "poll-tamper", "2026-11-18T12:00:00Z", tampered_report, collected, auth
    )
    assert poll_tampered.complete_inventories == ()
    reduced_tampered = reduce_poll(seeded_state, poll_tampered, auth)
    assert reduced_tampered.state.get_bucket("acme/widgets", "alice/widgets").rows["acme/widgets:alpha"].presence == PRESENCE_UNKNOWN


# ---------------------------------------------------------------------------
# 5. Unaffected scope retains use; #1833 / legacy holds preserved; zero writes
# ---------------------------------------------------------------------------


def test_unaffected_scope_retains_use_with_unavailable_and_1833_hold(
    fake_transport: FakeUpstreamTransport,
    monkeypatch: pytest.MonkeyPatch,
):
    # Lower budget so truncated tree exhaustion triggers SuiteUnavailable cleanly
    monkeypatch.setattr(liveness, "TREE_REQUEST_BUDGET", 1)

    auth_good = _make_suite_authority(
        suite_id="alice/widgets",
        owner="acme",
        repo="widgets",
        version="v1.0.0",
        components=["alice/base"],
    )
    auth_trunc = _make_suite_authority(
        suite_id="carol/huge",
        owner="acme",
        repo="huge",
        version="v1.0.0",
        components=["carol/item"],
    )
    auth_ruflo = _make_suite_authority(
        suite_id="ruvnet/ruflo",
        owner="ruvnet",
        repo="ruflo",
        version="v3.63.0",
        components=["ruvnet/core"],
    )
    authority = {**auth_good, **auth_trunc, **auth_ruflo}

    # Seed #1833-style legacy umbrella on ruvnet/ruflo with payload skillId ruvnet/agentdb
    legacy_payload = {
        "payloadVersion": 2,
        "skillId": "ruvnet/agentdb",
        "newVersion": "v3.63.8",
        "releasedAt": "2026-11-04T20:00:00Z",
        "sourceUrl": "https://github.com/ruvnet/ruflo/releases/tag/v3.63.8",
        "mode": "version-only",
        "componentAdds": [],
        "componentRemoves": [],
        "linkLiveness": [],
        "nameDrift": [],
        "candidates": [],
    }
    legacy_payload = envelope.seal(legacy_payload)
    gh = FakeGh(
        issues=[
            {
                "number": 1833,
                "title": "[upstream] ruvnet/ruflo → v3.63.8",
                "state": "open",
                "labels": ["upstream:release", "upstream:needs-info", "P2"],
                "body": batch.payload_block(legacy_payload),
            }
        ]
    )
    historical_map = {
        "ruvnet/agentdb": {
            "id": "ruvnet/agentdb",
            "level": "3★",
            "links": {"github": "https://github.com/ruvnet/ruflo"},
            "suiteComponents": [],
        }
    }

    # Seed a prior bucket for carol/huge on poll-mixed-0 so poll-mixed-1 proves
    # its prior state is preserved untouched with DECISION_UNAVAILABLE.
    fake_transport.set_release("acme", "huge", "v1.0.5")
    fake_transport.set_tree(
        "acme",
        "huge",
        "v1.0.5",
        _tree_payload(slug_paths=["skills/item/SKILL.md", "skills/pending-huge/SKILL.md"]),
    )
    _, _, seed_code, _, seeded = _run_offline_cycle(
        [authority["carol/huge"]],
        authority,
        poll_id="poll-mixed-0",
        observed_at="2026-11-17T12:00:00Z",
        gh=gh,
        state=empty_state(),
        historical_map=historical_map,
    )
    assert seed_code == 0
    assert seeded.state.get_bucket("acme/huge", "carol/huge") is not None

    # Good suite has verified release + tree
    fake_transport.set_release("acme", "widgets", "v1.1.0")
    fake_transport.set_tree(
        "acme",
        "widgets",
        "v1.1.0",
        _tree_payload(slug_paths=["skills/base/SKILL.md", "skills/newbie/SKILL.md"]),
    )
    # Huge suite has truncated tree whose walk exceeds budget=1 -> SuiteUnavailable(tree-truncated)
    fake_transport.set_release("acme", "huge", "v1.1.0")
    fake_transport.set_tree(
        "acme",
        "huge",
        "v1.1.0",
        _tree_payload(slug_paths=["skills/item/SKILL.md"], truncated=True),
    )
    fake_transport.set_subtree(
        "acme", "huge", "v1.1.0", {"tree": [{"path": "skills", "type": "tree", "sha": "s1"}]}
    )
    # Ruflo suite has a new release on the #1833-held repo
    fake_transport.set_release("ruvnet", "ruflo", "v3.64.0")
    fake_transport.set_tree(
        "ruvnet",
        "ruflo",
        "v3.64.0",
        _tree_payload(slug_paths=["skills/core/SKILL.md"]),
    )

    collected, report, code, poll_input, reduced = _run_offline_cycle(
        [authority["alice/widgets"], authority["carol/huge"], authority["ruvnet/ruflo"]],
        authority,
        poll_id="poll-mixed-1",
        observed_at="2026-11-18T12:00:00Z",
        gh=gh,
        state=seeded.state,
        historical_map=historical_map,
    )

    assert code == 0
    assert gh.write_count() == 0
    assert "carol/huge" in collected.unavailable_named_ids
    assert "ruvnet/ruflo" in poll_input.held_repos
    assert any(h["issue"] == 1833 for h in report["knownLegacyHolds"])
    assert reduced.status == "applied"
    assert reduced.write_authorized is False
    assert reduced.decisions[("ruvnet/ruflo", "ruvnet/ruflo")].decision == DECISION_HELD_SCOPE
    assert reduced.decisions[("acme/huge", "carol/huge")].decision == DECISION_UNAVAILABLE
    # Unaffected good repo retains full use and verified complete inventory
    good_bucket = reduced.state.get_bucket("acme/widgets", "alice/widgets")
    assert good_bucket is not None
    assert good_bucket.rows["acme/widgets:newbie"].presence == PRESENCE_PRESENT_CANDIDATE
    assert any(inv.named_id == "alice/widgets" for inv in poll_input.complete_inventories)


# ---------------------------------------------------------------------------
# 6. Backward compatibility of shared P1 helpers
# ---------------------------------------------------------------------------


def test_p1_shared_helpers_preserve_exact_legacy_behavior(
    fake_transport: FakeUpstreamTransport,
    monkeypatch: pytest.MonkeyPatch,
):
    # fetch_component_diff still returns (list, list) and preserves missing-root ([], [])
    fake_transport.set_tree(
        "acme",
        "widgets",
        "v1.1.0",
        _tree_payload(slug_paths=["skills/base/SKILL.md", "skills/nested/extra/SKILL.md"]),
    )
    adds, removes = liveness.fetch_component_diff(
        "acme", "widgets", "v1.1.0", "skills", ["alice/base", "alice/gone"]
    )
    assert isinstance(adds, list) and isinstance(removes, list)
    assert adds == ["extra"]
    assert removes == ["gone"]

    fake_transport.set_tree(
        "acme", "widgets", "v1.2.0", _tree_payload(include_root=False, slug_paths=[])
    )
    assert liveness.fetch_component_diff("acme", "widgets", "v1.2.0", "skills", ["alice/base"]) == ([], [])

    # Permanent 410 -> SuiteUnavailable; empty dict -> UnknownEvidenceError
    fake_transport.set_tree("acme", "widgets", "v1.3.0", GitHubFetchError("gone", status=410))
    with pytest.raises(SuiteUnavailable):
        liveness.fetch_component_diff("acme", "widgets", "v1.3.0", "skills", ["alice/base"])

    fake_transport.set_tree("acme", "widgets", "v1.4.0", {})
    with pytest.raises(UnknownEvidenceError):
        liveness.fetch_component_diff("acme", "widgets", "v1.4.0", "skills", ["alice/base"])

    # Ordinary watcher._poll_suite still uses watcher.fetch_component_diff and does NOT leak upstreamComponentRoot
    auth = _make_suite_authority(version="v1.0.0", components=["alice/base"])
    fake_transport.set_release("acme", "widgets", "v1.1.0")
    diff_calls: list[tuple[str, str, str, str, list[str]]] = []

    def _spy_diff(owner: str, repo: str, tag: str, root: str, comps: list[str]) -> tuple[list[str], list[str]]:
        diff_calls.append((owner, repo, tag, root, list(comps)))
        return (["extra"], [])

    monkeypatch.setattr(watcher, "fetch_component_diff", _spy_diff)
    p1_finding = watcher._poll_suite(auth["alice/widgets"], auth, verbose=False)
    assert p1_finding is not None
    assert len(diff_calls) == 1
    assert p1_finding["componentAdds"] == ["extra"]
    assert p1_finding["componentRemoves"] == []
    assert "upstreamComponentRoot" not in p1_finding
