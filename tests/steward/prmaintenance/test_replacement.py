"""A tracked replacement is routine work only when it provably carries the original producer's payload."""

from __future__ import annotations

import pytest

from gaia_cli.steward.prmaintenance import evaluate as ev
from gaia_cli.steward.prmaintenance import reconcile
from gaia_cli.steward.prmaintenance.sensor import PrMaintenanceSensor

from tests.steward.prmaintenance import helpers as h

NOW = "2026-11-04T18:30:00Z"
FOUNDER = {"login": "mbtiongson1", "id": 153011150, "type": "User"}
CLAUDE = {"sha": "", "authorLogin": "claude", "authorId": 81847, "authorType": "User", "committerLogin": "claude", "committerName": "Claude",
          "parents": 1, "message": "replacement"}


@pytest.fixture()
def world(tmp_path):
    fx = h.makeRepo(tmp_path / "w")
    original = fx.head("2026-44", version="8.26.10", dropIndexRow="2026-43")
    made = reconcile.buildReplacement(fx.root, h.REPO, 2157, original, "2026-44", fx.base, tmp_path / "wt")
    return fx, original, made


def rows(fx, original, made, *, body=None, author=None, headRef=None, originalOver=None, replacementOver=None):
    first = h.row(fx, original, "2026-44", number=2157, **(originalOver or {}))
    kw = dict(number=2290, author=author or dict(FOUNDER), labels=[], headRef=headRef or made.branch,
              body=body if body is not None else made.body, commits=[{**CLAUDE, "sha": made.commit}])
    kw.update(replacementOver or {})
    second = h.row(fx, made.commit, "2026-44", **kw)
    return [first, second]


def observe(fx, rowsList, **over):
    h.writeCensus(fx, h.census(rowsList, fx.base, **over))
    return {o.observed_state["number"]: o for o in PrMaintenanceSensor().scan_detailed(fx.root, NOW).observations}


def gates(seen):
    return {g["name"]: g["state"] for g in seen.observed_state["gates"]}


def test_a_proven_replacement_is_merge_ready_and_its_original_stays_reconcilable_not_closable(world):
    fx, original, made = world
    seen = observe(fx, rows(fx, original, made))
    assert seen[2290].kind == ev.KIND_MERGE and seen[2290].observed_state["producerId"] == "content-engine-replacement"
    assert gates(seen[2290])["replacement-link"] == "pass" and gates(seen[2290])["payload-preserved"] == "pass"
    assert seen[2157].kind == ev.KIND_VERIFY and seen[2157].observed_state["reconcile"] == "content-engine-cachebust"


def test_without_the_marker_or_with_the_wrong_one_it_is_not_ready(world):
    fx, original, made = world
    plain = observe(fx, rows(fx, original, made, body="no marker here"))[2290]
    assert plain.kind != ev.KIND_MERGE and gates(plain)["replacement-link"] == "fail"
    wrong = made.body.replace("pr=2157", "pr=9999")
    assert observe(fx, rows(fx, original, made, body=wrong))[2290].kind != ev.KIND_MERGE


def test_a_replacement_for_an_original_that_moved_or_vanished_is_not_ready(world):
    fx, original, made = world
    moved = made.body.replace(f"head={original[:12]}", "head=000000000000")
    assert observe(fx, rows(fx, original, made, body=moved))[2290].kind != ev.KIND_MERGE
    only = [rows(fx, original, made)[1]]
    seen = observe(fx, only)[2290]
    assert seen.kind != ev.KIND_MERGE and gates(seen)["replacement-link"] in ("fail", "unknown")


def test_a_payload_that_differs_from_the_originals_is_never_accepted(world):
    fx, original, made = world
    fx.detach(made.commit)  # the replacement's branch is checked out in the worktree that built it; build on its commit
    path = fx.root / "docs/api/v1/reports/2026-44.json"
    path.write_text(path.read_text().replace("2026-10-", "2026-09-"))
    forged = fx.commit("forged payload")
    seen = observe(fx, rows(fx, original, made, replacementOver={"headSha": forged, "commits": [{**CLAUDE, "sha": forged}],
                                                                   "files": h.filesOf(fx, forged)}))[2290]
    assert seen.kind != ev.KIND_MERGE and gates(seen)["payload-preserved"] == "fail"


def test_an_unproven_original_cannot_launder_a_replacement(world):
    fx, original, made = world
    forgedOriginal = {"author": {"login": "github-actions", "id": 1, "type": "User"}}
    seen = observe(fx, rows(fx, original, made, originalOver=forgedOriginal))[2290]
    assert seen.kind != ev.KIND_MERGE and gates(seen)["replacement-link"] == "fail"


def test_only_the_registered_identity_and_branch_convention_make_a_replacement(world):
    fx, original, made = world
    stranger = observe(fx, rows(fx, original, made, author={"login": "rando", "id": 5, "type": "User"}))
    assert stranger[2290].kind == ev.KIND_PROVENANCE  # an impostor using the branch convention is reported, never merged
    other = observe(fx, rows(fx, original, made, headRef="steward/b/anything"))
    assert 2290 not in other  # off-convention human work is not routine and is ignored
