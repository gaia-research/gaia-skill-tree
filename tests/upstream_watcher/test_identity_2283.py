"""Ruflo releases never become AgentDB versions, nor the reverse."""
import copy
import json
from unittest.mock import patch

import pytest

from scripts.upstream_watcher import issuer
from scripts.upstream_watcher.batch import plan_suite
from scripts.upstream_watcher.finder import compute_finding
from scripts.upstream_watcher.live import GhError, UnknownEvidenceError, read_live
from scripts.upstream_watcher.watcher import _poll_suite
from upstream_fakes import FakeGh, index_from_entries


def finding(skill, source=None):
    return {"finding_type": "update", "skillId": skill, "currentVersion": "v1", "newVersion": "v2",
            "sourceUrl": f"https://github.com/{source or skill}/releases/tag/v2", "releasedAt": "2026-11-04T00:00:00Z",
            "mode": "version-only", "componentAdds": [], "componentRemoves": [], "linkLiveness": [], "nameDrift": []}


def umbrella(skill, source=None):
    payload = finding(skill, source)
    return {"number": 1833, "title": f"[upstream] {source or skill} → v1", "state": "open", "labels": ["upstream:release"],
            "body": "<!-- gaia-upstream-payload\n" + json.dumps(payload) + "\n-->"}


@pytest.mark.parametrize("skill,source", [("ruvnet/agentdb", "ruvnet/ruflo"), ("ruvnet/ruflo", "ruvnet/agentdb")])
def test_wrong_repository_release_is_unknown_even_when_tag_matches_stored_version(skill, source):
    fm = {"id": skill, "suiteRef": "ruvnet/ruflo", "upstream": {"version": "v2"}}
    with pytest.raises(UnknownEvidenceError, match="release source"):
        compute_finding(fm, {"tag_name": "v2", "html_url": f"https://github.com/{source}/releases/tag/v2"})


@pytest.mark.parametrize("skill", ["ruvnet/agentdb", "ruvnet/ruflo"])
def test_own_repository_release_preserves_suite_identity_and_version(skill):
    fm = {"id": skill, "suiteRef": "ruvnet/ruflo", "upstream": {"version": "v1"}}
    before = copy.deepcopy(fm)
    result = compute_finding(fm, {"tag_name": "v2", "html_url": f"https://github.com/{skill}/releases/tag/v2"})
    assert result["skillId"] == skill and result["currentVersion"] == "v1"
    assert fm == before


def test_current_agentdb_registry_source_is_refused_before_poll_not_silently_rebased():
    fm = {"id": "ruvnet/agentdb", "suiteRef": "ruvnet/ruflo", "links": {"github": "https://github.com/ruvnet/ruflo"},
          "upstream": {"repo": "ruvnet/ruflo", "version": "v3.67.0"}}
    with patch("scripts.upstream_watcher.watcher.fetch_json") as fetch:
        with pytest.raises(UnknownEvidenceError, match="canonical CLI"):
            _poll_suite(fm, {}, False)
        fetch.assert_not_called()


def test_relink_alone_cannot_reuse_the_parent_repository_version():
    fm = {"id": "ruvnet/agentdb", "links": {"github": "https://github.com/ruvnet/agentdb"},
          "upstream": {"repo": "ruvnet/ruflo", "version": "v3.67.0"}}
    with pytest.raises(UnknownEvidenceError, match="contradicts upstream.repo"):
        _poll_suite(fm, {}, False)


def test_batch_will_not_overwrite_conflicting_live_1833_payload():
    gh = FakeGh([umbrella("ruvnet/agentdb", "ruvnet/ruflo")])
    before = copy.deepcopy(gh.issues)
    with pytest.raises(GhError, match="payload identity conflicts"):
        plan_suite(finding("ruvnet/ruflo"), read_live(gh), index_from_entries([]), gh=gh)
    assert gh.issues == before and gh.writes == []


def test_fanout_refuses_conflicting_umbrella_before_same_version_noop_or_write():
    row = umbrella("ruvnet/agentdb", "ruvnet/ruflo")
    row["title"] = "[upstream] ruvnet/ruflo → v2"
    with patch.object(issuer, "_open_snapshot", return_value={"upstream:release": [row]}), \
            patch.object(issuer, "_update_issue") as update, patch.object(issuer, "_create_issue") as create:
        with pytest.raises(issuer.IdempotencyLookupError, match="payload identity conflicts"):
            issuer.create_issues([finding("ruvnet/ruflo")], apply=True)
        update.assert_not_called()
        create.assert_not_called()


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_same_run_shared_source_conflict_is_preflighted_before_any_write(version):
    first = finding("ruvnet/ruflo")
    first["newVersion"] = "v1"
    second = finding("ruvnet/flow-nexus", "ruvnet/ruflo")
    second["newVersion"] = version
    with patch.object(issuer, "_open_snapshot", return_value={"upstream:release": []}), \
            patch.object(issuer, "_create_issue", return_value=123) as create, \
            patch.object(issuer, "_update_issue", return_value=True) as update, \
            patch.object(issuer, "_edit_umbrella_body") as edit:
        with pytest.raises(issuer.IdempotencyLookupError, match="identity conflicts"):
            issuer.create_issues([first, second], apply=True)
        create.assert_not_called()
        update.assert_not_called()
        edit.assert_not_called()


def test_same_identity_same_run_is_idempotent():
    first = finding("ruvnet/ruflo")
    with patch.object(issuer, "_open_snapshot", return_value={"upstream:release": []}), \
            patch.object(issuer, "_create_issue", return_value=123) as create, \
            patch.object(issuer, "_update_issue") as update, \
            patch.object(issuer, "_edit_umbrella_body"):
        result = issuer.create_issues([first, copy.deepcopy(first)], apply=True)
    assert create.call_count == 1
    update.assert_not_called()
    assert result[1]["skipped"] is True


@pytest.mark.parametrize("existing", [False, True], ids=["created-cache", "updated-cache"])
@pytest.mark.parametrize("nextVersion", ["v2", "v3"], ids=["skip", "update"])
def test_generated_cache_is_strictly_validated_before_each_skip_or_update(existing, nextVersion):
    from scripts.upstream_watcher import releaseidentity

    first = finding("ruvnet/ruflo")
    second = copy.deepcopy(first)
    second["newVersion"] = nextVersion
    snapshot = {"upstream:release": [umbrella("ruvnet/ruflo")] if existing else []}
    with patch.object(issuer, "_open_snapshot", return_value=snapshot), \
            patch.object(issuer, "_create_issue", return_value=123) as create, \
            patch.object(issuer, "_update_issue", return_value=True) as update, \
            patch.object(issuer, "_fanout_approval_reset"), \
            patch.object(issuer, "_edit_umbrella_body"), \
            patch.object(releaseidentity, "validateUmbrellaIdentity", wraps=releaseidentity.validateUmbrellaIdentity) as validate:
        result = issuer.create_issues([first, second, copy.deepcopy(second)], apply=True)
    assert create.call_count == (0 if existing else 1)
    assert update.call_count == int(existing) + int(nextVersion == "v3")
    assert result[1]["skipped"] is (nextVersion == "v2")
    assert result[2]["skipped"] is True
    # A historical snapshot read alone may use recovery; every generated body read is strict.
    assert [call.kwargs["generated"] for call in validate.call_args_list] == (
        ([False] if existing else []) + [True] * (4 if nextVersion == "v3" else 3)
    )


def test_generated_identity_matching_remains_case_insensitive():
    from scripts.upstream_watcher.releaseidentity import validateUmbrellaIdentity

    validateUmbrellaIdentity(finding("RuvNet/Ruflo"), umbrella("ruvnet/ruflo"), generated=True)


def test_cached_payload_is_checked_even_after_preflight():
    first = finding("ruvnet/ruflo")
    original = issuer.render_umbrella_body
    def conflicting_body(*args):
        text = original(*args)
        return text.replace('"skillId": "ruvnet/ruflo"', '"skillId": "ruvnet/flow-nexus"')
    with patch.object(issuer, "_open_snapshot", return_value={"upstream:release": []}), \
            patch.object(issuer, "render_umbrella_body", side_effect=conflicting_body), \
            patch.object(issuer, "_create_issue", return_value=123), \
            patch.object(issuer, "_edit_umbrella_body"), \
            patch.object(issuer, "_update_issue") as update:
        with pytest.raises(issuer.IdempotencyLookupError, match="payload identity conflicts"):
            issuer.create_issues([first, copy.deepcopy(first)], apply=True)
        update.assert_not_called()


GENERATED_BAD_BODIES = [
    "no payload",
    "<!-- gaia-upstream-payload\n{broken\n-->",
    *["<!-- gaia-upstream-payload\n" + json.dumps(payload) + "\n-->" for payload in (
        None, True, [], {}, {"skillId": None}, {"skillId": True}, {"skillId": 123},
        {"skillId": []}, {"skillId": {}}, {"skillId": ""}, {"skillId": "ruvnet"},
        {"skillId": "ruvnet/ruflo/extra"}, {"skillId": " ruvnet/ruflo"},
        {"skillId": "ruvnet/ruflo\n"}, {"skillId": "ruvnet/flow-nexus"},
    )],
]


@pytest.mark.parametrize("body", GENERATED_BAD_BODIES)
@pytest.mark.parametrize("existing", [False, True], ids=["create", "update"])
def test_generated_invalid_identity_refuses_before_any_write(body, existing):
    first = finding("ruvnet/ruflo")
    snapshot = {"upstream:release": [umbrella("ruvnet/ruflo")] if existing else []}
    with patch.object(issuer, "_open_snapshot", return_value=snapshot), \
            patch.object(issuer, "render_umbrella_body", return_value=body), \
            patch.object(issuer, "_create_issue", return_value=123) as create, \
            patch.object(issuer, "_update_issue", return_value=True) as update, \
            patch.object(issuer, "_fanout_approval_reset") as reset, \
            patch.object(issuer, "_edit_umbrella_body") as edit:
        with pytest.raises(issuer.IdempotencyLookupError, match="payload identity"):
            issuer.create_issues([first, copy.deepcopy(first)], apply=True)
        create.assert_not_called()
        update.assert_not_called()
        reset.assert_not_called()
        edit.assert_not_called()


@pytest.mark.parametrize("body", GENERATED_BAD_BODIES[:11])
def test_historical_headless_or_unidentified_payload_can_still_be_repaired(body):
    row = {**umbrella("ruvnet/ruflo"), "body": body}
    with patch.object(issuer, "_open_snapshot", return_value={"upstream:release": [row]}), \
            patch.object(issuer, "_create_issue") as create, \
            patch.object(issuer, "_update_issue", return_value=True) as update, \
            patch.object(issuer, "_fanout_approval_reset"), \
            patch.object(issuer, "_edit_umbrella_body"):
        result = issuer.create_issues([finding("ruvnet/ruflo")], apply=True)
        assert result[0]["updated"] is True
        update.assert_called_once()
        create.assert_not_called()


def test_two_distinct_correct_repository_sources_do_not_claim_each_others_umbrellas():
    gh = FakeGh([umbrella("ruvnet/ruflo"), {**umbrella("ruvnet/agentdb"), "number": 1834}])
    for identifier, expected in [("ruvnet/ruflo", 1833), ("ruvnet/agentdb", 1834)]:
        plan = plan_suite(finding(identifier), read_live(gh), index_from_entries([]), gh=gh)
        assert plan["umbrella"] == expected
    assert gh.writes == []
