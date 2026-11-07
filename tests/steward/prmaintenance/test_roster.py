"""Environment roster profiles: capability-driven, environment-scoped, credential-free, and never a silent substitution."""

from __future__ import annotations

import copy
import json

import pytest

from gaia_cli.steward.policy import StewardPolicy
from gaia_cli.steward.prmaintenance import roster, state
from gaia_cli.steward.prmaintenance.sensor import PrMaintenanceSensor  # noqa: F401

from tests.steward.prmaintenance import helpers as h


def agent(agentId, caps, *, cost=3, efforts=("low", "medium", "high"), maxEffort="high", invocable="declared", binding=None):
    return {"agentId": agentId, "modelBinding": binding, "capabilities": dict(caps), "efforts": list(efforts), "defaultEffort": efforts[0],
            "maxEffort": maxEffort, "canDelegate": False, "invocable": invocable, "relativeCost": cost}


def profile(env="claude-code-remote", pid="p1", agents=None, **over):
    value = {"schemaVersion": roster.SCHEMA, "profileId": pid, "environmentId": env, "revision": 1,
             "provenance": {"source": "test"}, "dispatch": {"mechanism": "test dispatcher", "verified": False},
             "agents": agents or [agent("cheap", {"routine-maintenance": "declared"}, cost=1),
                                  agent("mid", {"independent-review": "declared", "routine-maintenance": "declared"}, cost=3),
                                  agent("strong", {"independent-review": "declared", "adversarial-verification": "declared"}, cost=7)],
             "limits": {"maxInFlight": 2, "maxDispatchesPerRun": 3}, "independence": {"verifierMustDifferFromBuilder": True}, "fallbacks": []}
    value.update(over)
    return value


ENV = {"CLAUDE_CODE_SESSION_ID": "s", "CCR_AGENT_PROXY_ENABLED": "1"}


def test_missing_active_profile_is_a_stop_not_a_guess(tmp_path):
    with pytest.raises(roster.RosterError) as caught:
        roster.preflight(tmp_path, "r1", env=ENV, write=False)
    assert caught.value.code == "no-active-profile"


def test_environment_is_discovered_from_signals_and_a_profile_for_another_environment_is_never_imported(tmp_path):
    assert roster.discoverEnvironment(ENV)["environmentId"] == "claude-code-remote"
    assert roster.discoverEnvironment({"GITHUB_ACTIONS": "true"})["environmentId"] == "github-actions"
    assert roster.discoverEnvironment({})["environmentId"] == "unknown-local"
    roster.saveProfile(tmp_path, profile(env="github-actions", pid="ci"), activate=True)
    with pytest.raises(roster.RosterError) as caught:
        roster.preflight(tmp_path, "r1", env=ENV, write=False)
    assert caught.value.code == "profile-for-other-environment"


def test_different_environments_hold_different_rosters_and_select_independently(tmp_path):
    local = profile(env="claude-code-remote", pid="a", agents=[agent("alpha", {"independent-review": "declared"}, cost=2)])
    ci = profile(env="github-actions", pid="b", agents=[agent("omega", {"independent-review": "declared"}, cost=9)])
    roster.saveProfile(tmp_path, local)
    roster.saveProfile(tmp_path, ci)
    assert roster.select(roster.loadProfile(tmp_path, "a"), "independent-review").agentId == "alpha"
    assert roster.select(roster.loadProfile(tmp_path, "b"), "independent-review").agentId == "omega"
    receipt = roster.preflight(tmp_path, "r1", explicit="a", env=ENV, write=True)
    assert receipt["profileId"] == "a" and receipt["usableAgents"] == ["alpha"]
    assert state.readRecords(tmp_path, "dispatches")[-1]["kind"] == "roster-preflight"


def test_selection_is_by_capability_cheapest_first_never_by_name():
    p = profile()
    assert roster.select(p, "independent-review").agentId == "mid"
    assert roster.select(p, "independent-review", exclude=["mid"]).agentId == "strong"  # the builder is excluded
    assert roster.select(p, "adversarial-verification").agentId == "strong"


def test_an_undeclared_or_uninvocable_agent_is_never_chosen_whatever_it_is_called():
    p = profile(agents=[agent("flagship-reviewer", {"independent-review": "undeclared"}, cost=1),
                        agent("ghost", {"independent-review": "declared"}, cost=2, invocable="unavailable"),
                        agent("unproven", {"independent-review": "declared"}, cost=2, invocable="unknown")])
    with pytest.raises(roster.RosterError) as caught:
        roster.select(p, "independent-review")
    assert caught.value.code == "capability-unavailable"


def test_unavailable_capability_is_recorded_and_not_silently_substituted():
    p = profile()
    with pytest.raises(roster.RosterError) as caught:
        roster.select(p, "cross-repo-analysis")
    assert caught.value.code == "capability-unavailable" and "no substitute" in caught.value.message


def test_only_an_explicitly_authorized_fallback_may_replace_a_missing_capability():
    base = profile(agents=[agent("primary", {"routine-maintenance": "declared"}, cost=1), agent("backup", {"independent-review": "declared"}, cost=2)])
    with pytest.raises(roster.RosterError):
        roster.select(base, "independent-review", exclude=["backup"])
    withFallback = copy.deepcopy(base)
    withFallback["fallbacks"] = [{"from": "primary", "to": "backup", "authorized": True}]
    assert roster.select(withFallback, "independent-review").agentId == "backup"
    unauthorized = copy.deepcopy(base)
    unauthorized["fallbacks"] = [{"from": "primary", "to": "backup", "authorized": False}]
    assert any("authorized: true" in problem for problem in roster.validateProfile(unauthorized))  # an unauthorized fallback is not loadable


def test_operator_choice_overrides_preference_only_inside_the_boundary():
    p = profile()
    assert roster.select(p, "independent-review", operatorChoice="strong").agentId == "strong"
    with pytest.raises(roster.RosterError) as caught:
        roster.select(p, "independent-review", operatorChoice="cheap")  # lacks the capability
    assert caught.value.code == "operator-choice-outside-boundary"
    with pytest.raises(roster.RosterError):
        roster.select(p, "independent-review", operatorChoice="not-in-profile")
    with pytest.raises(roster.RosterError):
        roster.select(p, "independent-review", operatorChoice="mid", exclude=["mid"])


def test_effort_must_be_explicit_and_inside_the_agents_ladder():
    p = profile()
    with pytest.raises(roster.RosterError) as caught:
        roster.select(p, "independent-review", effort="max")
    assert caught.value.code == "effort-outside-profile"
    bad = profile(agents=[agent("x", {"independent-review": "declared"}, efforts=("default", "high"))])
    assert any("explicit effort" in problem for problem in roster.validateProfile(bad))


def test_escalation_needs_a_stated_need_raises_effort_first_then_agent_and_stays_inside_the_profile():
    p = profile()
    first = roster.select(p, "independent-review")
    with pytest.raises(roster.RosterError) as caught:
        roster.escalate(p, first, "because")
    assert caught.value.code == "escalation-unjustified"
    need = "the verifier could not reproduce the rendered-html proof on two attempts"
    second = roster.escalate(p, first, need)
    assert (second.agentId, second.effort, second.escalation) == ("mid", "medium", need)
    top = roster.Selection("mid", None, "high", "independent-review", None, "p1", "claude-code-remote", 1)
    third = roster.escalate(p, top, need)
    assert third.agentId == "strong"
    exhausted = roster.Selection("strong", None, "high", "independent-review", None, "p1", "claude-code-remote", 1)
    with pytest.raises(roster.RosterError) as stop:
        roster.escalate(p, exhausted, need)
    assert stop.value.code == "escalation-exhausted"


def test_a_stronger_agent_never_gains_authority_the_policy_is_unchanged():
    policy = StewardPolicy.load(h.SOURCE)
    before = policy.pr_maintenance
    roster.select(profile(), "adversarial-verification")
    assert StewardPolicy.load(h.SOURCE).pr_maintenance == before
    assert before.mergeMethods == ("merge",) and before.maxMergesPerRun <= 5


def test_profiles_hold_no_credentials_and_are_rejected_when_they_try(tmp_path):
    for leak in ({"apiKey": "x"}, {"note": "ghp_" + "a" * 20}, {"access_token": "t"}):
        bad = profile()
        bad["provenance"] = {"source": "test", **leak}
        with pytest.raises(roster.RosterError) as caught:
            roster.saveProfile(tmp_path, bad)
        assert caught.value.code == "profile-invalid" and "credential-like" in caught.value.message
    assert roster.validateProfile(profile()) == []


def test_dispatch_limits_use_the_lower_of_profile_and_policy_and_exhaustion_defers(tmp_path):
    p = profile(limits={"maxInFlight": 5, "maxDispatchesPerRun": 5})
    picked = roster.select(p, "independent-review")
    envelope = {"paths": ["docs/reports/**"], "authority": "read-only verification"}
    roster.recordDispatch(tmp_path, p, picked, runId="r1", dispatchId="d1", envelope=envelope, role="verifier", laneMaxInFlight=2, laneMaxPerRun=1)
    with pytest.raises(roster.RosterError) as caught:
        roster.recordDispatch(tmp_path, p, picked, runId="r1", dispatchId="d2", envelope=envelope, role="verifier", laneMaxInFlight=2, laneMaxPerRun=1)
    assert caught.value.code == "class-b-budget-exhausted"  # per-run ceiling is the policy lane's 1, not the profile's 5
    roster.finishDispatch(tmp_path, "d1", "PASS", cost="not measurable")
    assert roster.inFlight(tmp_path) == 0
    roster.recordDispatch(tmp_path, p, picked, runId="r2", dispatchId="d3", envelope=envelope, role="verifier", laneMaxInFlight=2, laneMaxPerRun=1)
    roster.recordDispatch(tmp_path, p, roster.select(p, "independent-review", exclude=["mid"]), runId="r3", dispatchId="d4", envelope=envelope,
                          role="verifier", laneMaxInFlight=2, laneMaxPerRun=1)
    with pytest.raises(roster.RosterError):
        roster.recordDispatch(tmp_path, p, picked, runId="r4", dispatchId="d5", envelope=envelope, role="verifier", laneMaxInFlight=2, laneMaxPerRun=1)


def test_dispatch_record_carries_the_receipts_the_directive_requires(tmp_path):
    p = profile()
    picked = roster.escalate(p, roster.select(p, "independent-review"), "first pass could not reproduce the index rebuild proof")
    record = roster.recordDispatch(tmp_path, p, picked, runId="r1", dispatchId="d1", envelope={"authority": "verify only"}, role="verifier",
                                   laneMaxInFlight=2, laneMaxPerRun=2, builders=["cheap"])
    assert {"environmentId", "profileId", "profileRevision", "agentId", "effort", "capability", "escalationReason", "envelope", "builders"} <= set(record)
    assert json.loads((state.storeDir(tmp_path) / "dispatches.jsonl").read_text().splitlines()[-1])["escalationReason"]


def test_a_verifier_that_built_the_work_cannot_be_dispatched_as_its_verifier(tmp_path):
    p = profile()
    picked = roster.select(p, "independent-review")
    with pytest.raises(roster.RosterError) as caught:
        roster.recordDispatch(tmp_path, p, picked, runId="r1", dispatchId="d1", envelope={}, role="verifier", laneMaxInFlight=2, laneMaxPerRun=2,
                              builders=[picked.agentId])
    assert caught.value.code == "verifier-not-independent"
