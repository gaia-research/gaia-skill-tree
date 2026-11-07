"""Environment-scoped roster profiles: which agents this environment can actually run for Class B work.

Governance class and model identity are separate. Class B is a governed work category and is never defined here by
a model, provider or harness name. A *profile* says what one environment exposes: agent ids, opaque model bindings,
capability states, reasoning-effort ladders, dispatch permissions and budgets. Rules:

* a profile belongs to exactly one environment and is never imported into another (``profile-for-other-environment``);
* selection is by *capability*, never by name, and an agent whose capability is only ``undeclared`` is never chosen;
* escalation (higher effort, then a more capable agent) needs a stated, unresolved need and stays inside the profile;
* an unavailable capability is recorded as a limitation, and only an explicitly authorized fallback may replace it;
* the verifier is never a builder of the same work, and a stronger agent never widens authority;
* a profile persists configuration and validated capability states only. Credentials are rejected on load and save.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from gaia_cli.steward.prmaintenance import state

SCHEMA = "steward-roster-profile-v1"
ROSTER_DIR = Path(".gaia/steward/rosters")
ACTIVE_FILE = "ACTIVE"
PROFILE_ENV = "GAIA_STEWARD_ROSTER_PROFILE"
CAPABILITIES = (
    "deterministic-verification", "routine-maintenance", "multi-file-semantic", "independent-review",
    "cross-repo-analysis", "architectural-reconciliation", "adversarial-verification",
)
USABLE_CAPABILITY = ("declared", "probed")
USABLE_INVOCATION = ("declared", "probed")
SECRET_KEY = re.compile(r"(?i)(token|secret|passw|credential|api[-_]?key|bearer)")
SECRET_VALUE = re.compile(r"(?i)(ghp_|gho_|github_pat_|sk-[a-z0-9]|xox[abp]-|AKIA[0-9A-Z]{8})")
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,79}")


class RosterError(RuntimeError):
    """A roster precondition failed. ``code`` is stable; nothing was dispatched."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code, self.message = code, message


@dataclass(frozen=True)
class Selection:
    agentId: str
    modelBinding: str | None
    effort: str
    capability: str
    escalation: str | None
    profileId: str
    environmentId: str
    revision: int


def discoverEnvironment(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Which environment is this? From documented process signals only; an operator can name it explicitly."""

    env = os.environ if env is None else env
    explicit = env.get("GAIA_STEWARD_ENVIRONMENT", "").strip()
    signals = []
    if env.get("GITHUB_ACTIONS") == "true":
        harness = "github-actions"
        signals.append("GITHUB_ACTIONS")
    elif env.get("CLAUDE_CODE_SESSION_ID") or env.get("CLAUDE_CODE_CHILD_SESSION"):
        harness = "claude-code-remote" if env.get("CCR_AGENT_PROXY_ENABLED") else "claude-code"
        signals += [k for k in ("CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_CHILD_SESSION", "CCR_AGENT_PROXY_ENABLED") if env.get(k)]
    elif env.get("CODEX_HOME") or env.get("CODEX_SANDBOX"):
        harness = "codex"
        signals += [k for k in ("CODEX_HOME", "CODEX_SANDBOX") if env.get(k)]
    else:
        harness = "unknown-local"
    if explicit and not NAME.fullmatch(explicit):
        raise RosterError("environment-malformed", "GAIA_STEWARD_ENVIRONMENT must be a plain identifier")
    return {"environmentId": explicit or harness, "harness": harness, "signals": signals, "explicit": bool(explicit)}


def scanForSecrets(value: Any, path: str = "profile") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            if SECRET_KEY.search(str(key)):
                found.append(f"{path}.{key}")
            found += scanForSecrets(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            found += scanForSecrets(item, f"{path}[{index}]")
    elif isinstance(value, str) and SECRET_VALUE.search(value):
        found.append(path)
    return found


def validateProfile(profile: Any) -> list[str]:
    """Every problem with a profile; empty means usable. Never raises."""

    if not isinstance(profile, Mapping):
        return ["profile is not an object"]
    problems = []
    if profile.get("schemaVersion") != SCHEMA:
        problems.append(f"schemaVersion must be {SCHEMA}")
    for key in ("profileId", "environmentId"):
        if not isinstance(profile.get(key), str) or not NAME.fullmatch(profile[key]):
            problems.append(f"{key} must be a plain identifier")
    if not isinstance(profile.get("revision"), int) or isinstance(profile.get("revision"), bool) or profile["revision"] < 1:
        problems.append("revision must be a positive integer")
    if not isinstance(profile.get("provenance"), Mapping) or not profile["provenance"].get("source"):
        problems.append("provenance.source is required")
    problems += [f"credential-like content at {where}" for where in scanForSecrets(profile)]
    agents = profile.get("agents")
    if not isinstance(agents, list) or not agents:
        return problems + ["agents must be a non-empty list"]
    seen = set()
    for index, agent in enumerate(agents):
        where = f"agents[{index}]"
        if not isinstance(agent, Mapping) or not isinstance(agent.get("agentId"), str) or not NAME.fullmatch(agent["agentId"]):
            problems.append(f"{where}.agentId must be a plain identifier")
            continue
        if agent["agentId"] in seen:
            problems.append(f"{where}.agentId duplicates {agent['agentId']}")
        seen.add(agent["agentId"])
        efforts = agent.get("efforts")
        if not isinstance(efforts, list) or not efforts or not all(isinstance(e, str) and e and e not in state_BAD for e in efforts):
            problems.append(f"{where}.efforts must be an ordered list of explicit effort levels")
        else:
            for key in ("defaultEffort", "maxEffort"):
                if agent.get(key) not in efforts:
                    problems.append(f"{where}.{key} must be one of its efforts")
        capabilities = agent.get("capabilities")
        if not isinstance(capabilities, Mapping) or any(
                cap not in CAPABILITIES or st not in ("declared", "probed", "undeclared") for cap, st in capabilities.items()):
            problems.append(f"{where}.capabilities must map known capabilities to declared, probed or undeclared")
        if agent.get("invocable") not in ("declared", "probed", "unknown", "unavailable"):
            problems.append(f"{where}.invocable must be declared, probed, unknown or unavailable")
        if not isinstance(agent.get("relativeCost"), int) or isinstance(agent.get("relativeCost"), bool) or not 1 <= agent["relativeCost"] <= 10:
            problems.append(f"{where}.relativeCost must be an integer from 1 to 10")
    limits = profile.get("limits")
    if not isinstance(limits, Mapping) or not all(isinstance(limits.get(k), int) and limits[k] >= 0 for k in ("maxInFlight", "maxDispatchesPerRun")):
        problems.append("limits.maxInFlight and limits.maxDispatchesPerRun must be non-negative integers")
    independence = profile.get("independence")
    if not isinstance(independence, Mapping) or independence.get("verifierMustDifferFromBuilder") is not True:
        problems.append("independence.verifierMustDifferFromBuilder must be true")
    for index, fallback in enumerate(profile.get("fallbacks") or []):
        if not isinstance(fallback, Mapping) or fallback.get("from") not in seen or fallback.get("to") not in seen \
                or fallback.get("authorized") is not True:
            problems.append(f"fallbacks[{index}] must name two known agents and authorized: true")
    if not isinstance(profile.get("dispatch"), Mapping) or not profile["dispatch"].get("mechanism"):
        problems.append("dispatch.mechanism is required")
    return problems


state_BAD = frozenset({"", "default", "inherit"})


def rosterDir(root: Path) -> Path:
    directory = root / ROSTER_DIR
    if any(p.is_symlink() for p in (directory, *directory.parents) if str(p).startswith(str(root)) and p != root):
        raise RosterError("roster-store-unsafe", "the roster store is reached through a symlink")
    return directory


def saveProfile(root: Path, profile: Mapping[str, Any], activate: bool = False) -> Path:
    problems = validateProfile(profile)
    if problems:
        raise RosterError("profile-invalid", "; ".join(problems[:5]))
    directory = rosterDir(root)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{profile['profileId']}.json"
    target.write_text(json.dumps(profile, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if activate:
        (directory / ACTIVE_FILE).write_text(profile["profileId"] + "\n", encoding="utf-8")
    return target


def loadProfile(root: Path, profileId: str) -> dict[str, Any]:
    if not NAME.fullmatch(profileId or ""):
        raise RosterError("profile-invalid", "profile id must be a plain identifier")
    path = rosterDir(root) / f"{profileId}.json"
    try:
        profile = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RosterError("profile-missing", f"no readable profile {profileId!r} in {ROSTER_DIR}") from exc
    problems = validateProfile(profile)
    if problems:
        raise RosterError("profile-invalid", "; ".join(problems[:5]))
    return profile


def activeProfileId(root: Path, explicit: str | None = None, env: Mapping[str, str] | None = None) -> str:
    """Explicit choice, then the environment variable, then the ACTIVE pointer. Never a guess."""

    env = os.environ if env is None else env
    chosen = explicit or env.get(PROFILE_ENV, "").strip()
    if not chosen:
        pointer = rosterDir(root) / ACTIVE_FILE
        chosen = pointer.read_text(encoding="utf-8").strip() if pointer.is_file() else ""
    if not chosen:
        raise RosterError("no-active-profile", "no roster profile is selected: pass --profile, set "
                          f"{PROFILE_ENV}, or write {ROSTER_DIR}/{ACTIVE_FILE}; another environment's roster is never assumed")
    return chosen


def preflight(root: Path, runId: str, explicit: str | None = None, env: Mapping[str, str] | None = None,
              now: datetime | None = None, write: bool = True) -> dict[str, Any]:
    """Session-start roster preflight. Raises ``RosterError`` rather than guess; otherwise returns and records a receipt."""

    discovered = discoverEnvironment(env)
    profile = loadProfile(root, activeProfileId(root, explicit, env))
    if profile["environmentId"] != discovered["environmentId"]:
        raise RosterError("profile-for-other-environment",
                          f"profile {profile['profileId']!r} belongs to {profile['environmentId']!r}, this is {discovered['environmentId']!r}")
    usable = [a["agentId"] for a in profile["agents"] if a["invocable"] in USABLE_INVOCATION]
    unproven = [a["agentId"] for a in profile["agents"] if a["invocable"] not in USABLE_INVOCATION]
    receipt = {
        "kind": "roster-preflight", "at": state.stamp(now), "runId": runId, "environment": discovered,
        "profileId": profile["profileId"], "profileRevision": profile["revision"], "provenance": profile["provenance"],
        "dispatchMechanism": profile["dispatch"]["mechanism"], "limits": profile["limits"],
        "usableAgents": usable, "notInvocable": unproven,
        "capabilitiesByAgent": {a["agentId"]: {c: s for c, s in a["capabilities"].items() if s in USABLE_CAPABILITY} for a in profile["agents"]},
    }
    if write:
        with state.lock(root):
            state.appendRecord(root, "dispatches", receipt)
    return receipt


def effortIndex(agent: Mapping[str, Any], effort: str) -> int:
    return agent["efforts"].index(effort)


def candidates(profile: Mapping[str, Any], capability: str, exclude: Sequence[str]) -> list[Mapping[str, Any]]:
    if capability not in CAPABILITIES:
        raise RosterError("capability-unknown", f"{capability!r} is not a known capability")
    pool = [a for a in profile["agents"] if a["agentId"] not in exclude and a["invocable"] in USABLE_INVOCATION
            and a["capabilities"].get(capability) in USABLE_CAPABILITY]
    return sorted(pool, key=lambda a: (a["relativeCost"], a["agentId"]))


def select(profile: Mapping[str, Any], capability: str, *, exclude: Sequence[str] = (), operatorChoice: str | None = None,
           effort: str | None = None) -> Selection:
    """Capability-driven selection. The cheapest agent that *can* do the work, at its default effort unless told otherwise.

    An operator choice overrides the discovered preference only inside the boundary: the agent must be in this profile,
    invocable, hold the capability, and not be excluded. A missing capability is a stop, not a substitution.
    """

    pool = candidates(profile, capability, exclude)
    chosen = None
    if operatorChoice is not None:
        chosen = next((a for a in pool if a["agentId"] == operatorChoice), None)
        if chosen is None:
            raise RosterError("operator-choice-outside-boundary",
                              f"{operatorChoice!r} cannot be used for {capability}: not in this profile, not invocable, "
                              "lacks the capability, or is excluded")
    elif pool:
        chosen = pool[0]
    if chosen is None:
        for fallback in profile.get("fallbacks") or []:
            replacement = next((a for a in candidates(profile, capability, exclude) if a["agentId"] == fallback["to"]), None)
            if fallback.get("authorized") is True and replacement is not None:
                chosen = replacement
                break
    if chosen is None:
        raise RosterError("capability-unavailable", f"no agent in profile {profile['profileId']!r} holds {capability!r}; "
                          "recorded as a limitation, no substitute is chosen")
    level = effort or chosen["defaultEffort"]
    if level not in chosen["efforts"] or effortIndex(chosen, level) > effortIndex(chosen, chosen["maxEffort"]):
        raise RosterError("effort-outside-profile", f"{level!r} is not permitted for {chosen['agentId']!r}")
    return Selection(chosen["agentId"], chosen.get("modelBinding"), level, capability, None, profile["profileId"],
                     profile["environmentId"], profile["revision"])


def escalate(profile: Mapping[str, Any], current: Selection, need: str, *, exclude: Sequence[str] = ()) -> Selection:
    """Raise effort, then move to a more capable (costlier) agent, only for a stated unresolved need and inside the profile."""

    if len(need.strip()) < 12:
        raise RosterError("escalation-unjustified", "an escalation must state the unresolved need it answers")
    agent = next(a for a in profile["agents"] if a["agentId"] == current.agentId)
    index = effortIndex(agent, current.effort)
    if index < effortIndex(agent, agent["maxEffort"]):
        return Selection(agent["agentId"], agent.get("modelBinding"), agent["efforts"][index + 1], current.capability,
                         need.strip(), current.profileId, current.environmentId, current.revision)
    stronger = [a for a in candidates(profile, current.capability, [*exclude, current.agentId]) if a["relativeCost"] > agent["relativeCost"]]
    if not stronger:
        raise RosterError("escalation-exhausted", "this profile has no stronger authorized agent for that capability; "
                          "the work stays at its current authority and is reported, not widened")
    nxt = stronger[0]
    return Selection(nxt["agentId"], nxt.get("modelBinding"), nxt["defaultEffort"], current.capability, need.strip(),
                     current.profileId, current.environmentId, current.revision)


def inFlight(root: Path) -> int:
    started, finished = set(), set()
    for row in state.readRecords(root, "dispatches"):
        if row.get("kind") == "dispatch" and row.get("status") == "started":
            started.add(row["dispatchId"])
        elif row.get("kind") == "dispatch" and row.get("status") in ("finished", "abandoned"):
            finished.add(row["dispatchId"])
    return len(started - finished)


def dispatchesInRun(root: Path, runId: str) -> int:
    return len({r["dispatchId"] for r in state.readRecords(root, "dispatches")
                if r.get("kind") == "dispatch" and r.get("runId") == runId and r.get("status") == "started"})


def recordDispatch(root: Path, profile: Mapping[str, Any], selection: Selection, *, runId: str, dispatchId: str,
                   envelope: Mapping[str, Any], role: str, laneMaxInFlight: int, laneMaxPerRun: int,
                   builders: Sequence[str] = (), now: datetime | None = None) -> dict[str, Any]:
    """Record a dispatch, enforcing the *lower* of the profile's and the policy lane's limits. Starts the in-flight count."""

    if role == "verifier" and selection.agentId in builders:
        raise RosterError("verifier-not-independent", "the verifier would be a builder of the same work")
    with state.lock(root):
        cap = min(int(profile["limits"]["maxInFlight"]), laneMaxInFlight)
        perRun = min(int(profile["limits"]["maxDispatchesPerRun"]), laneMaxPerRun)
        if inFlight(root) >= cap:
            raise RosterError("class-b-budget-exhausted", f"{cap} dispatch(es) already in flight")
        if dispatchesInRun(root, runId) >= perRun:
            raise RosterError("class-b-budget-exhausted", f"run {runId} already used its {perRun} dispatch(es); resume next run")
        record = {"kind": "dispatch", "status": "started", "at": state.stamp(now), "runId": runId, "dispatchId": dispatchId,
                  "role": role, "environmentId": selection.environmentId, "profileId": selection.profileId,
                  "profileRevision": selection.revision, "agentId": selection.agentId, "modelBinding": selection.modelBinding,
                  "effort": selection.effort, "capability": selection.capability, "escalationReason": selection.escalation,
                  "envelope": dict(envelope), "builders": list(builders)}
        state.appendRecord(root, "dispatches", record)
    return record


def finishDispatch(root: Path, dispatchId: str, result: str, *, cost: str | None = None, receipts: Sequence[str] = (),
                   status: str = "finished", now: datetime | None = None) -> dict[str, Any]:
    record = {"kind": "dispatch", "status": status, "at": state.stamp(now), "dispatchId": dispatchId, "result": result[:400],
              "cost": cost, "receipts": list(receipts)}
    with state.lock(root):
        state.appendRecord(root, "dispatches", record)
    return record
