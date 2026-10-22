#!/usr/bin/env python3
"""Unattended driver for `gaia steward full run`.

The runner makes zero model calls: whatever needs a model or a forge comes back
as a pending action. This driver performs exactly the loop in
.claude/skills/gaia-steward-full/SKILL.md: run, hand each pending action to its
single owner, record the outcome, resume, repeat.

Owners
  agent.build      a fresh builder agent (STEWARD_AGENT_CMD); model family from
                   params.allowedModels, Haiku by default
  agent.verify     a fresh verifier agent, Sonnet only, never a forbidden id
  forge.open_pr    gh: draft PR into a dev/* integration branch (idempotent)
  lead.integrate   gh: merge commit into a dev/* integration branch, never main
  forge.close_issue  scripts/steward_issue_close.py: one proven closure (#2130)

Before the first run the driver refreshes the GitHub issue census that the
issue-hygiene sensor reads (scripts/steward_issue_census.py, REST, fail closed).
A census that cannot be trusted is removed, so the sensor reports its input
missing rather than reconciling against stale rows. `--no-census` skips this.

Anything else is reported and not executed. Nothing is faked: an agent that
produces no usable outcome is not recorded.

Without agent credentials or an agent command the run is started with
--no-agents, so no Class B work can be dispatched and left stranded in
`building`. Class A landing and forge handling still run. Exit 5 is returned
only when pending agent actions exist that the driver could not perform.

Exit codes
  0  completed, or stopped with nothing outstanding
  1  stopped: a step refused twice, a stall, a driver refusal, or an unknown state
  2  refused input or configuration
  3  blocked (runner)
  4  observing-existing (runner: another run holds the lease)
  5  NOT RUN: pending agent actions could not be performed (no agent credentials)
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from gaia_cli.steward.fullrun import BADEFFORTS, agentIdentity
from gaia_cli.steward.issuehygiene.sensor import CENSUS_INPUT

EXITCOMPLETED = 0
EXITSTOPPED = 1
EXITREFUSEDINPUT = 2
WRITESOFFREASON = "issueHygiene.writesEnabled is false"
EXITBLOCKED = 3
EXITOBSERVING = 4
EXITNOTRUN = 5

AGENTTYPES = ("agent.build", "agent.verify")
CLOSETYPE = "forge.close_issue"
KNOWNTYPES = AGENTTYPES + ("forge.open_pr", "lead.integrate", CLOSETYPE)
CLOSEOUTCOMES = ("closed", "already-closed", "stale-skip", "failed", "blocked", "blocked-identity")
CLOSEREFUSED = 2
VERDICTS = ("accept", "reject", "escalate")
BUILDFAMILIES = ("haiku", "sonnet")
ENGINES = ("copilot", "claude", "codex", "pi")
ADAPTER = "scripts/steward_agent_dispatch.py"
CLOSESCRIPT = "scripts/steward_issue_close.py"
CENSUSSCRIPT = "scripts/steward_issue_census.py"
CENSUSPATH = CENSUS_INPUT.as_posix()
CLOSUREDIR = ".gaia/steward/drive/closures"
DEFAULTREPO = "gaia-research/gaia-skill-tree"
DEFAULTREPORT = ".gaia/steward/drive-report.json"
DEFAULTOUTCOMEDIR = ".gaia/steward/drive/outcomes"
DEFAULTAGENTCMD = (
    'claude -p --model {model} --effort {effort} '
    '"Read the file {prompt_path} and follow it exactly. '
    'Print only the outcome JSON object as your final output."'
)
DEFAULTBUILDEFFORT = "medium"
DEFAULTVERIFYEFFORT = "high"
DEFAULTHAIKUID = "claude-haiku-5-5"
DEFAULTAGENTTIMEOUT = 3600.0
BRANCHPATTERN = re.compile(r"^dev/[A-Za-z0-9._/-]+$")
PROTECTEDBASES = ("main", "master")
DRIVERACTOR = "steward-drive"
MAXFAILURESPERSTEP = 2
CENSUSTIMEOUT = 900.0
CLOSETIMEOUT = 300.0


class DriverRefusal(Exception):
    """The driver declines an action on its own authority. The run stops; nothing is retried."""


class DriverConfigError(Exception):
    """Configuration the driver cannot run under."""


@dataclass
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""
    timedOut: bool = False


Runner = Callable[..., CommandResult]


def textOf(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def runCommand(argv: Sequence[str], *, cwd: Path, timeout: float | None = None,
               env: Mapping[str, str] | None = None) -> CommandResult:
    """Run argv directly. Never a shell."""

    try:
        proc = subprocess.run(
            list(argv), cwd=str(cwd), env=None if env is None else dict(env),
            capture_output=True, text=True, timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return CommandResult(124, textOf(exc.stdout), textOf(exc.stderr), timedOut=True)
    except OSError as exc:
        return CommandResult(127, "", str(exc))
    return CommandResult(proc.returncode, proc.stdout or "", proc.stderr or "")


def lastJsonObject(text: str) -> dict[str, Any] | None:
    """The whole text as a JSON object, or failing that its last line that is one."""

    stripped = text.strip()
    if not stripped:
        return None
    try:
        value = json.loads(stripped)
        if isinstance(value, dict):
            return value
    except ValueError:
        pass
    for line in reversed(stripped.splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict):
            return value
    return None


def safeName(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9.-]+", "-", text).strip("-") or "step"


def baseRefusal(base: Any, integrationBranch: str | None) -> str | None:
    """Why a base branch may not receive a landing or a merge, or None when it may."""

    if not isinstance(base, str) or not base.strip():
        return "action names no base branch"
    if base in PROTECTEDBASES:
        return f"base {base!r} is protected; only the integration branch is a target"
    if ".." in base or not BRANCHPATTERN.match(base):
        return f"base {base!r} is not a dev/* integration branch"
    if integrationBranch and base != integrationBranch:
        return f"base {base!r} is not the run's integration branch {integrationBranch!r}"
    return None


def agentReadiness(env: Mapping[str, str], which: Callable[[str], str | None]) -> tuple[bool, str]:
    """Whether agent outcomes can honestly be produced in this environment."""

    engine = (env.get("STEWARD_AGENT") or "").strip().lower()
    if engine:
        if engine not in ENGINES:
            return False, f"STEWARD_AGENT {engine!r} is not one of {', '.join(ENGINES)}"
        if which("gh") is None:
            return False, "gh is not on PATH (needed to dispatch the agent workflow)"
        if not (env.get("GH_TOKEN") or env.get("GITHUB_TOKEN")):
            return False, "no GH_TOKEN or GITHUB_TOKEN (needed to dispatch the agent workflow)"
        return True, ""
    if not (env.get("STEWARD_SONNET_MODEL_ID") or "").strip():
        return False, "no agent credentials (STEWARD_SONNET_MODEL_ID unset: the verifier must be Sonnet)"
    if (env.get("STEWARD_AGENT_CMD") or "").strip():
        return True, ""
    if which("claude") is None:
        return False, "no agent credentials (STEWARD_AGENT_CMD unset and claude is not on PATH)"
    if not (env.get("ANTHROPIC_API_KEY") or env.get("CLAUDE_CODE_OAUTH_TOKEN")):
        return False, "no agent credentials (ANTHROPIC_API_KEY and CLAUDE_CODE_OAUTH_TOKEN unset)"
    return True, ""


def scanPendingAgentActions(node: Any, found: list[dict[str, Any]]) -> None:
    if isinstance(node, dict):
        if node.get("type") in AGENTTYPES and node.get("status") == "pending":
            found.append(node)
        for value in node.values():
            scanPendingAgentActions(value, found)
    elif isinstance(node, list):
        for value in node:
            scanPendingAgentActions(value, found)


@dataclass
class DriveOptions:
    root: Path
    integrationBranch: str | None = None
    ledger: str = "git"
    push: bool = True
    trigger: str = "scheduled"
    afk: bool = False
    reportPath: Path = Path(DEFAULTREPORT)
    python: str = sys.executable
    agentTimeout: float = DEFAULTAGENTTIMEOUT
    census: bool = False
    repo: str = DEFAULTREPO


@dataclass
class Handled:
    outcome: dict[str, Any] | None = None
    reason: str = ""
    skip: bool = False
    halt: bool = False


@dataclass
class PassResult:
    progressed: bool = False
    failed: bool = False


@dataclass
class Driver:
    options: DriveOptions
    runner: Runner = runCommand
    env: dict[str, str] = field(default_factory=lambda: dict(os.environ))
    which: Callable[[str], str | None] = shutil.which
    newId: Callable[[str], str] = field(default=lambda prefix: f"{prefix}-{uuid.uuid4()}")
    clock: Callable[[], str] = field(
        default=lambda: dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"))

    def __post_init__(self) -> None:
        self.buildEffort = self.effortFrom("STEWARD_BUILD_EFFORT", DEFAULTBUILDEFFORT)
        self.verifyEffort = self.effortFrom("STEWARD_VERIFY_EFFORT", DEFAULTVERIFYEFFORT)
        self.builderFamily = (self.env.get("STEWARD_BUILDER_MODEL") or "haiku").strip().lower()
        self.engine = (self.env.get("STEWARD_AGENT") or "").strip().lower() or None
        self.verifierEngine = (self.env.get("STEWARD_VERIFIER_AGENT") or "").strip().lower() or self.engine
        for name, value in (("STEWARD_AGENT", self.engine), ("STEWARD_VERIFIER_AGENT", self.verifierEngine)):
            if value is not None and value not in ENGINES:
                raise DriverConfigError(f"{name} must be one of {', '.join(ENGINES)}, not {value!r}")
        if self.engine is not None and self.engine != "claude":
            self.builderFamily = self.engine
        if self.builderFamily not in BUILDFAMILIES and self.builderFamily not in ENGINES:
            raise DriverConfigError(f"STEWARD_BUILDER_MODEL must be haiku or sonnet, not {self.builderFamily!r}")
        self.haikuId = (self.env.get("STEWARD_HAIKU_MODEL_ID") or DEFAULTHAIKUID).strip()
        self.sonnetId = (self.env.get("STEWARD_SONNET_MODEL_ID") or "").strip() or None
        if self.builderFamily == "sonnet" and self.sonnetId is None and self.engine is None:
            raise DriverConfigError("STEWARD_BUILDER_MODEL=sonnet needs STEWARD_SONNET_MODEL_ID")
        self.ready, self.notReadyReason = agentReadiness(self.env, self.which)
        self.failures: dict[str, int] = {}
        self.handled: list[dict[str, Any]] = []
        self.refused: list[dict[str, Any]] = []
        self.skipped: list[dict[str, Any]] = []
        self.unknown: list[dict[str, Any]] = []
        self.unperformed: list[dict[str, Any]] = []
        self.runIds: list[str] = []
        self.builderIds: set[str] = set()
        self.tokensIn = 0
        self.tokensOut = 0
        self.stopReason: str | None = None
        self.lastStatus: str | None = None
        self.censusReport: dict[str, Any] | None = None
        self.startedAt = self.clock()

    # -- configuration -----------------------------------------------

    def effortFrom(self, name: str, default: str) -> str:
        value = self.env.get(name)
        value = default if value is None else value.strip()
        if not value or value.lower() in BADEFFORTS:
            raise DriverConfigError(f"{name} must be an explicit thinking effort, not {value!r}")
        return value

    def verifierFamily(self) -> str:
        """Claude verifies as Sonnet; every other agent is recorded under its engine name."""

        if self.verifierEngine is None or self.verifierEngine == "claude":
            return "sonnet"
        return self.verifierEngine

    def builderModelId(self) -> str:
        return self.haikuId if self.builderFamily == "haiku" else str(self.sonnetId)

    # -- runner plumbing ---------------------------------------------

    def gaia(self, tail: Sequence[str]) -> tuple[int, dict[str, Any] | None, str]:
        argv = [self.options.python, "-m", "gaia_cli.main", "steward", "full", *tail]
        result = self.runner(argv, cwd=self.options.root, env=self.env)
        return result.returncode, lastJsonObject(result.stdout), result.stderr

    def runTail(self, runId: str | None = None, noAgents: bool = False) -> list[str]:
        o = self.options
        tail = ["run"]
        if runId:
            tail += ["--resume", runId]
        else:
            tail += ["--trigger", o.trigger]
        if o.afk:
            tail.append("--afk")
        if noAgents:
            tail.append("--no-agents")
        tail += ["--ledger", o.ledger]
        if o.integrationBranch:
            tail += ["--integration-branch", o.integrationBranch]
        if o.push:
            tail.append("--push")
        tail.append("--json")
        return tail

    def resolveFile(self, value: Any) -> Path | None:
        if not isinstance(value, str) or not value.strip():
            return None
        path = Path(value)
        candidate = path if path.is_absolute() else self.options.root / path
        return candidate if candidate.is_file() else None

    def runGh(self, args: Sequence[str]) -> CommandResult:
        return self.runner(["gh", *args], cwd=self.options.root, env=self.env)

    def spawnEngine(self, role: str, engine: str, promptPath: Path,
                    params: Mapping[str, Any]) -> tuple[CommandResult, dict[str, Any] | None]:
        """Run one agent through the engine-agnostic adapter (a gh-aw workflow run)."""

        argv = [self.options.python, str(self.options.root / ADAPTER), "--role", role, "--engine", engine,
                "--prompt-path", str(promptPath), "--dispatch-id", str(params.get("dispatchId") or self.newId(role)),
                "--timeout", str(int(self.options.agentTimeout))]
        if role == "build":
            argv += ["--base", str(params.get("base") or ""), "--branch", str(params.get("branch") or "")]
        result = self.runner(argv, cwd=self.options.root, timeout=self.options.agentTimeout + 120, env=self.env)
        if result.timedOut or result.returncode != 0:
            return result, None
        return result, lastJsonObject(result.stdout)

    def spawn(self, modelId: str, effort: str, promptPath: Path) -> tuple[CommandResult, dict[str, Any] | None]:
        template = shlex.split(self.env.get("STEWARD_AGENT_CMD") or DEFAULTAGENTCMD)
        values = {"model": modelId, "effort": effort, "prompt_path": str(promptPath)}
        argv = []
        for token in template:
            for key, value in values.items():
                token = token.replace("{" + key + "}", value)
            argv.append(token)
        if not argv:
            return CommandResult(127, "", "empty agent command"), None
        result = self.runner(argv, cwd=self.options.root, timeout=self.options.agentTimeout, env=self.env)
        if result.timedOut or result.returncode != 0:
            return result, None
        return result, lastJsonObject(result.stdout)

    @staticmethod
    def failureText(role: str, result: CommandResult) -> str:
        if result.timedOut:
            return f"{role} agent timed out"
        if result.returncode != 0:
            tail = (result.stderr or "").strip().splitlines()[-1:] or [""]
            return f"{role} agent exited {result.returncode}" + (f": {tail[0][:300]}" if tail[0] else "")
        return f"{role} agent printed no JSON outcome"

    def numberOrNone(self, value: Any) -> float | int | None:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            return None
        return value

    def addTokens(self, outcome: Mapping[str, Any]) -> None:
        self.tokensIn += int(outcome.get("tokensIn") or 0)
        self.tokensOut += int(outcome.get("tokensOut") or 0)

    # -- owners -------------------------------------------------------

    def handleBuild(self, action: Mapping[str, Any]) -> Handled:
        params = action.get("params") or {}
        allowed = params.get("allowedModels") or []
        if self.builderFamily in BUILDFAMILIES and self.builderFamily not in allowed:
            return Handled(reason=f"builder family {self.builderFamily!r} not in allowedModels {allowed}")
        promptPath = self.resolveFile(params.get("promptPath"))
        if promptPath is None:
            return Handled(reason="promptPath is missing or not a file")
        agentId = self.newId("builder")
        self.builderIds.add(agentId)
        if self.engine is not None:
            result, out = self.spawnEngine("build", self.engine, promptPath, params)
        else:
            result, out = self.spawn(self.builderModelId(), self.buildEffort, promptPath)
        if out is None:
            return Handled(reason=self.failureText("builder", result))
        noChange = out.get("noChange")
        summary = out.get("summary")
        if not isinstance(noChange, bool):
            return Handled(reason="builder output needs a boolean noChange")
        if not isinstance(summary, str) or not summary.strip():
            return Handled(reason="builder output needs a non-empty summary")
        outcome: dict[str, Any] = {
            "agentId": agentId, "model": self.builderFamily, "effort": self.buildEffort,
            "noChange": noChange, "summary": summary.strip(),
            "tokensIn": self.numberOrNone(out.get("tokensIn")),
            "tokensOut": self.numberOrNone(out.get("tokensOut")),
        }
        if not noChange:
            outputs = params.get("outputs") or {}
            diffRel = outputs.get("diffPath")
            proofRel = outputs.get("proofPath")
            if not diffRel or not proofRel:
                return Handled(reason="build params name no diffPath or proofPath")
            diffAbs = self.options.root / diffRel
            proofAbs = self.options.root / proofRel
            if self.engine is not None and not proofAbs.is_file() and isinstance(out.get("proof"), dict):
                proofAbs.parent.mkdir(parents=True, exist_ok=True)
                proofAbs.write_text(json.dumps(out["proof"], indent=2, sort_keys=True), encoding="utf-8")
            if not diffAbs.is_file():
                base, branch = params.get("base"), params.get("branch")
                if base and branch and self.engine is not None:
                    self.runner(["git", "fetch", "origin", str(base), str(branch)],
                                cwd=self.options.root, env=self.env)
                    base, branch = f"origin/{base}", f"origin/{branch}"
                if base and branch:
                    captured = self.runner(["git", "diff", f"{base}...{branch}"],
                                           cwd=self.options.root, env=self.env)
                    if captured.returncode == 0 and captured.stdout.strip():
                        diffAbs.parent.mkdir(parents=True, exist_ok=True)
                        diffAbs.write_text(captured.stdout, encoding="utf-8")
            if not diffAbs.is_file() or not diffAbs.read_text(encoding="utf-8").strip():
                return Handled(reason="builder claimed a change but produced no diff")
            if not (self.options.root / proofRel).is_file():
                return Handled(reason="builder produced no proof transcript")
            outcome["diffPath"] = diffRel
            outcome["proofPath"] = proofRel
        return Handled(outcome=outcome)

    def handleVerify(self, action: Mapping[str, Any]) -> Handled:
        params = action.get("params") or {}
        forbidden = {agentIdentity(v) for v in params.get("forbiddenAgentIds") or []}
        promptPath = self.resolveFile(params.get("verifierPromptPath"))
        if promptPath is None:
            return Handled(reason="verifierPromptPath is missing or not a file")
        if self.verifierEngine is None and self.sonnetId is None:
            return Handled(reason="no Sonnet model is configured for the verifier")
        agentId = self.newId("verifier")
        if agentIdentity(agentId) in forbidden or agentIdentity(agentId) in {agentIdentity(b) for b in self.builderIds}:
            return Handled(reason=f"verifier id {agentId!r} belongs to a builder; refusing to spawn it")
        if self.verifierEngine is not None:
            result, out = self.spawnEngine("verify", self.verifierEngine, promptPath, params)
        else:
            result, out = self.spawn(str(self.sonnetId), self.verifyEffort, promptPath)
        if out is None:
            return Handled(reason=self.failureText("verifier", result))
        verdict = out.get("verdict")
        rationale = out.get("rationale")
        if verdict not in VERDICTS:
            return Handled(reason=f"verifier verdict {verdict!r} is not accept, reject or escalate")
        if not isinstance(rationale, str) or not rationale.strip():
            return Handled(reason="verifier output needs a non-empty rationale")
        return Handled(outcome={
            "agentId": agentId, "model": self.verifierFamily(), "effort": self.verifyEffort,
            "verdict": verdict, "rationale": rationale.strip(),
            "tokensIn": self.numberOrNone(out.get("tokensIn")),
            "tokensOut": self.numberOrNone(out.get("tokensOut")),
        })

    def listPullRequests(self, head: str, base: str, state: str, fields: str) -> list[dict[str, Any]] | None:
        result = self.runGh(["pr", "list", "--head", head, "--base", base, "--state", state, "--json", fields])
        if result.returncode != 0:
            return None
        try:
            value = json.loads(result.stdout or "[]")
        except ValueError:
            return None
        if not isinstance(value, list):
            return None
        return [e for e in value if isinstance(e, dict)
                and e.get("headRefName", head) == head and e.get("baseRefName", base) == base]

    def handleForge(self, action: Mapping[str, Any]) -> Handled:
        params = action.get("params") or {}
        base = params.get("base")
        refusal = baseRefusal(base, self.options.integrationBranch)
        if refusal:
            raise DriverRefusal(refusal)
        head = params.get("head") or params.get("branch")
        if not isinstance(head, str) or not head.strip():
            raise DriverRefusal("forge.open_pr names no head branch")
        bodyPath = self.resolveFile(params.get("bodyPath"))
        if bodyPath is None:
            return Handled(reason="PR body file is missing or not a file")
        existing = self.listPullRequests(head, str(base), "all",
                                         "number,url,state,baseRefName,headRefName")
        if existing is None:
            return Handled(reason="gh pr list failed")
        if existing:
            existing.sort(key=lambda e: e.get("state") != "OPEN")
            pr = existing[0]
            merged = pr.get("state") == "MERGED"
            outcome: dict[str, Any] = {
                "pullRequest": {"number": pr.get("number"), "url": pr.get("url")}, "merged": merged,
            }
            if merged:
                view = self.runGh(["pr", "view", str(pr.get("number")), "--json", "mergeCommit",
                                   "--jq", ".mergeCommit.oid"])
                sha = view.stdout.strip()
                if view.returncode != 0 or not sha:
                    return Handled(reason="existing PR is merged but its merge commit is unknown")
                outcome["mergedSha"] = sha
            return Handled(outcome=outcome)
        title = params.get("title") or f"chore(steward): repair {head}"
        created = self.runGh(["pr", "create", "--draft", "--base", str(base), "--head", head,
                              "--title", title, "--body-file", str(bodyPath)])
        if created.returncode != 0:
            return Handled(reason=f"gh pr create failed: {created.stderr.strip()[:200]}")
        url = next((line.strip() for line in reversed(created.stdout.splitlines())
                    if line.strip().startswith("http")), "")
        try:
            number = int(url.rstrip("/").rsplit("/", 1)[-1])
        except ValueError:
            return Handled(reason="gh pr create printed no pull request URL")
        return Handled(outcome={"pullRequest": {"number": number, "url": url}, "merged": False})

    def handleIntegrate(self, action: Mapping[str, Any]) -> Handled:
        params = action.get("params") or {}
        base = params.get("base")
        refusal = baseRefusal(base, self.options.integrationBranch)
        if refusal:
            raise DriverRefusal(refusal)
        branch = params.get("branch")
        if not isinstance(branch, str) or not branch.strip():
            return Handled(skip=True, reason="work item names no branch; nothing to integrate")
        matches = self.listPullRequests(branch, str(base), "open",
                                        "number,url,isDraft,headRefOid,headRefName,baseRefName")
        if matches is None:
            return Handled(reason="gh pr list failed")
        if len(matches) != 1:
            return Handled(skip=True, reason=f"ambiguous: {len(matches)} open pull requests for {branch}; recorded nothing")
        pr = matches[0]
        if pr.get("isDraft"):
            return Handled(skip=True, reason="pull request is a draft; not integrated")
        sha = pr.get("headRefOid")
        number = str(pr.get("number"))
        if not isinstance(sha, str) or not sha:
            return Handled(skip=True, reason="pull request head commit is unknown; recorded nothing")
        merged = self.runGh(["pr", "merge", number, "--merge", "--match-head-commit", sha])
        if merged.returncode != 0:
            return Handled(reason=f"gh pr merge failed: {merged.stderr.strip()[:200]}")
        view = self.runGh(["pr", "view", number, "--json", "mergeCommit", "--jq", ".mergeCommit.oid"])
        mergeSha = view.stdout.strip()
        if view.returncode != 0 or not mergeSha:
            return Handled(reason="merged, but the merge commit could not be read")
        return Handled(outcome={
            "decision": "integrate", "by": DRIVERACTOR,
            "pullRequest": {"number": pr.get("number"), "url": pr.get("url")}, "mergedSha": mergeSha,
        })

    def closuresEnabled(self) -> bool:
        """Re-read at every closure: flipping writesEnabled off stops pending closures on the next pass."""
        from gaia_cli.steward.policy import PolicyError, StewardPolicy

        try:
            return StewardPolicy.load(self.options.root).issue_hygiene.writesEnabled is True
        except PolicyError:
            return False

    def forgeToken(self) -> str | None:
        return (self.env.get("GH_TOKEN") or self.env.get("GITHUB_TOKEN") or "").strip() or None

    def refreshCensus(self) -> dict[str, Any]:
        """Collect the issue census the sensor reads. Fail closed: an untrusted file is removed."""

        o = self.options
        target = o.root / CENSUSPATH
        argv = [o.python, str(o.root / CENSUSSCRIPT), "--repo", o.repo, "--out", str(target)]
        result = self.runner(argv, cwd=o.root, timeout=CENSUSTIMEOUT, env=self.env)
        if result.returncode == 0:
            return {"state": "complete", "detail": f"{o.repo} census collected"}
        if result.returncode == 3:
            # The collector writes the file with its completeness flags false, so the sensor reports it not evaluated.
            return {"state": "incomplete", "detail": "a page failed or was short; issue hygiene is not evaluated"}
        if target.is_file():
            target.unlink()
        return {"state": "failed", "detail": f"census collector exited {result.returncode}; input removed"}

    def handleClose(self, action: Mapping[str, Any], runId: str) -> Handled:
        """One proven closure, performed by scripts/steward_issue_close.py. Its stdout is the outcome."""

        params = action.get("params") or {}
        stepId = str(action.get("stepId"))
        # The action is compact (B7 D5): identifiers, digests and the receipt path. The executor rebuilds the comments.
        if not isinstance(params.get("issue"), int) or not isinstance(params.get("key"), str) \
                or not isinstance(params.get("receiptPath"), str):
            return Handled(reason="closure action names no issue, key or receipt")
        directory = self.options.root / CLOSUREDIR
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{safeName(runId)}--{safeName(stepId)}.json"
        path.write_text(json.dumps(dict(params), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        o = self.options
        argv = [o.python, str(o.root / CLOSESCRIPT), "--root", str(o.root), "--action", str(path),
                "--repo", o.repo, "--run-id", runId]
        result = self.runner(argv, cwd=o.root, timeout=CLOSETIMEOUT, env=self.env)
        if result.returncode == CLOSEREFUSED:
            # The executor's gate refused: writes off, rule off, cap reached, or the checkout no longer proves
            # the action. That is a fact about the action, not a failure to retry, so the runner skips it.
            detail = (result.stderr or "").strip().splitlines()
            return Handled(skip=True, reason=f"closure refused by the executor gate: {(detail[-1] if detail else 'no reason')[:200]}")
        outcome = lastJsonObject(result.stdout)
        if outcome is None or outcome.get("outcome") not in CLOSEOUTCOMES:
            return Handled(reason=f"closure script printed no outcome (exit {result.returncode})")
        reason = str(outcome.get("failure") or outcome["outcome"])
        return Handled(outcome=outcome, reason=reason, halt=outcome["outcome"] == "blocked")

    def recordOutcome(self, runId: str, stepId: str, outcome: Mapping[str, Any]) -> tuple[bool, str]:
        directory = self.options.root / DEFAULTOUTCOMEDIR
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{safeName(runId)}--{safeName(stepId)}.json"
        path.write_text(json.dumps(dict(outcome), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        code, view, err = self.gaia(["record", runId, stepId, "--input", str(path),
                                     "--ledger", self.options.ledger, "--json"])
        if view is None or code == EXITREFUSEDINPUT:
            return False, (err.strip() or f"record exited {code} with no JSON").splitlines()[-1][:300]
        return True, str(view.get("status"))

    # -- the pass -----------------------------------------------------

    def performPending(self, runId: str, actions: Sequence[Mapping[str, Any]]) -> PassResult:
        result = PassResult()
        for action in actions:
            stepId = str(action.get("stepId"))
            kind = action.get("type")
            if kind not in KNOWNTYPES:
                self.unknown.append({"stepId": stepId, "type": kind, "reason": "unknown action type; not executed"})
                continue
            if kind in AGENTTYPES and not self.ready:
                self.unperformed.append({"stepId": stepId, "type": kind, "reason": self.notReadyReason})
                continue
            if kind == CLOSETYPE and not self.closuresEnabled():
                self.skipped.append({"stepId": stepId, "type": kind, "reason": WRITESOFFREASON + "; closure not performed"})
                continue
            if kind == CLOSETYPE and not self.forgeToken():
                self.unperformed.append({"stepId": stepId, "type": kind,
                                         "reason": "no GH_TOKEN or GITHUB_TOKEN (needed to close issues)"})
                continue
            try:
                if kind == "agent.build":
                    handled = self.handleBuild(action)
                elif kind == "agent.verify":
                    handled = self.handleVerify(action)
                elif kind == "forge.open_pr":
                    handled = self.handleForge(action)
                elif kind == CLOSETYPE:
                    handled = self.handleClose(action, runId)
                else:
                    handled = self.handleIntegrate(action)
            except DriverRefusal as exc:
                self.refused.append({"stepId": stepId, "type": kind, "reason": str(exc)})
                self.stopReason = f"driver refused {stepId}: {exc}"
                return result
            if handled.skip:
                self.skipped.append({"stepId": stepId, "type": kind, "reason": handled.reason})
                continue
            if handled.outcome is None:
                result.failed = True
                if self.registerFailure(stepId, kind, handled.reason):
                    return result
                continue
            ok, detail = self.recordOutcome(runId, stepId, handled.outcome)
            if not ok:
                result.failed = True
                self.refused.append({"stepId": stepId, "type": kind, "reason": f"record refused: {detail}"})
                if self.registerFailure(stepId, kind, f"record refused: {detail}"):
                    return result
                continue
            result.progressed = True
            self.addTokens(handled.outcome)
            self.handled.append(self.handledEntry(stepId, kind, handled.outcome, detail))
            if handled.halt:
                # Auth, rate or transport failure: the forge is not trustworthy for the rest of this run.
                self.stopReason = f"{kind} blocked at {stepId}: {handled.reason}"
                return result
        return result

    def registerFailure(self, stepId: str, kind: str, reason: str) -> bool:
        """Count a failed attempt. True when this step has now failed twice and the run must stop."""

        self.failures[stepId] = self.failures.get(stepId, 0) + 1
        if self.failures[stepId] >= MAXFAILURESPERSTEP:
            self.stopReason = f"step {stepId} ({kind}) failed twice; last reason: {reason}"
            return True
        return False

    @staticmethod
    def handledEntry(stepId: str, kind: str, outcome: Mapping[str, Any], status: str) -> dict[str, Any]:
        entry: dict[str, Any] = {"stepId": stepId, "type": kind, "recordedStatus": status}
        for key in ("agentId", "model", "effort", "verdict", "decision", "noChange", "tokensIn", "tokensOut",
                    "outcome", "issue"):
            if key in outcome:
                entry[key] = outcome[key]
        if isinstance(outcome.get("pullRequest"), dict):
            entry["pullRequest"] = outcome["pullRequest"]
        return entry

    # -- the loop -----------------------------------------------------

    def checkEarlierAgentActions(self) -> None:
        """With no agent path, report agent actions left pending by earlier runs."""

        _, payload, _ = self.gaia(["status", "--json"])
        if payload is None:
            return
        found: list[dict[str, Any]] = []
        scanPendingAgentActions(payload, found)
        known = {u["stepId"] for u in self.unperformed}
        for action in found:
            stepId = str(action.get("stepId"))
            if stepId not in known:
                self.unperformed.append({"stepId": stepId, "type": action.get("type"),
                                         "reason": f"earlier run; {self.notReadyReason}"})

    def drive(self) -> int:
        if not self.ready:
            self.checkEarlierAgentActions()
        if self.options.census:
            self.censusReport = self.refreshCensus()
        code, view, err = self.gaia(self.runTail(noAgents=not self.ready))
        while True:
            if view is None:
                return self.stop(EXITSTOPPED, f"runner output was not JSON (exit {code}): {err.strip()[-300:]}")
            runId = view.get("runId")
            if isinstance(runId, str) and runId not in self.runIds:
                self.runIds.append(runId)
            status = view.get("status")
            self.lastStatus = status
            if code == EXITREFUSEDINPUT:
                return self.stop(EXITREFUSEDINPUT, f"runner refused input: {err.strip()[-300:]}")
            if code == EXITBLOCKED or status == "blocked":
                return self.stop(EXITBLOCKED, "run blocked by the runner; reported, not retried")
            if code == EXITOBSERVING:
                return self.stop(EXITOBSERVING, "another run holds the lease; reported, not retried")
            if code == EXITCOMPLETED and status == "completed":
                return self.settle(EXITCOMPLETED)
            if code != EXITCOMPLETED or status != "awaiting-action" or not isinstance(runId, str):
                return self.stop(EXITSTOPPED, f"run ended with status {status!r} (exit {code})")
            actions = list(view.get("actions") or [])
            if not actions:
                return self.stop(EXITSTOPPED, "awaiting-action with no pending actions")
            passResult = self.performPending(runId, actions)
            if self.stopReason:
                return self.settle(EXITSTOPPED)
            if not (passResult.progressed or passResult.failed):
                if any(str(entry.get("reason", "")).startswith(WRITESOFFREASON) for entry in self.skipped):
                    # Writes are off, so the runner cancels the pending closures (B7 D3). Ask it to, then report it.
                    self.gaia(self.runTail(runId=runId, noAgents=not self.ready))
                    return self.stop(EXITSTOPPED, "writes disabled: pending closures were cancelled by the runner; nothing was written")
                return self.stop(EXITSTOPPED, "stalled: the remaining pending actions are not ones this driver performs")
            code, view, err = self.gaia(self.runTail(runId=runId, noAgents=not self.ready))

    def stop(self, code: int, reason: str) -> int:
        self.stopReason = reason
        return self.settle(code)

    def settle(self, code: int) -> int:
        if self.unperformed:
            code = EXITNOTRUN
            if not self.stopReason:
                self.stopReason = "pending agent actions could not be performed"
        report = self.buildReport(code)
        self.writeReport(report)
        markdown = renderMarkdown(report)
        print(markdown)
        summaryPath = self.env.get("GITHUB_STEP_SUMMARY")
        if summaryPath:
            with open(summaryPath, "a", encoding="utf-8") as handle:
                handle.write(markdown + "\n")
        return code

    def buildReport(self, code: int) -> dict[str, Any]:
        return {
            "schemaVersion": "steward-drive-report-v1",
            "startedAt": self.startedAt,
            "finishedAt": self.clock(),
            "exitCode": code,
            "status": self.lastStatus,
            "stopReason": self.stopReason,
            "runIds": self.runIds,
            "agents": {
                "state": "ready" if self.ready else "NOT RUN",
                "reason": None if self.ready else self.notReadyReason,
                "builderFamily": self.builderFamily,
                "buildEffort": self.buildEffort,
                "verifyEffort": self.verifyEffort,
            },
            "census": self.censusReport or {"state": "skipped", "detail": "census refresh disabled for this run"},
            "options": {"integrationBranch": self.options.integrationBranch,
                        "ledger": self.options.ledger, "push": self.options.push},
            "handled": self.handled,
            "refused": self.refused,
            "skipped": self.skipped,
            "unknownActions": self.unknown,
            "unperformed": self.unperformed,
            "tokens": {"in": self.tokensIn, "out": self.tokensOut},
        }

    def writeReport(self, report: dict[str, Any]) -> None:
        path = self.options.reportPath
        if not path.is_absolute():
            path = self.options.root / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def renderMarkdown(report: Mapping[str, Any]) -> str:
    agents = report["agents"]
    if agents["state"] == "ready":
        agentLine = "agents: ready"
    else:
        agentLine = f"agents: NOT RUN: {agents['reason']}"
    lines = [
        "## Steward drive", "",
        f"- Exit code: {report['exitCode']}",
        f"- Final run status: {report['status'] or 'none'}",
        f"- Runs: {', '.join(report['runIds']) or 'none'}",
        f"- {agentLine}",
        f"- Issue census: {report['census']['state']} ({report['census']['detail']})",
    ]
    if report["stopReason"]:
        lines.append(f"- Stopped: {report['stopReason']}")
    lines += ["", "### Handled", ""]
    if report["handled"]:
        lines += ["| Step | Type | Outcome | Agent | Model | Effort |", "| --- | --- | --- | --- | --- | --- |"]
        for entry in report["handled"]:
            lines.append(f"| {entry['stepId']} | {entry['type']} | {entry.get('recordedStatus')} | "
                         f"{entry.get('agentId', '-')} | {entry.get('model', '-')} | {entry.get('effort', '-')} |")
    else:
        lines.append("None.")
    for title, key in (("Refused", "refused"), ("Skipped", "skipped"),
                       ("Unknown action types (not executed)", "unknownActions"),
                       ("Unperformed agent actions", "unperformed")):
        if report[key]:
            lines += ["", f"### {title}", ""]
            lines += [f"- {entry['stepId']} ({entry['type']}): {entry['reason']}" for entry in report[key]]
    lines += ["", f"Tokens: in {report['tokens']['in']}, out {report['tokens']['out']}", ""]
    return "\n".join(lines)


def buildParser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="steward_drive.py",
        description="Drive `gaia steward full run` to completion, performing each pending action through its owner.",
    )
    parser.add_argument("--root", default=".", help="Repository checkout to drive (default: current directory)")
    parser.add_argument("--integration-branch", default=os.environ.get("GAIA_STEWARD_INTEGRATION_BRANCH"),
                        metavar="B", help="dev/* integration branch (default: $GAIA_STEWARD_INTEGRATION_BRANCH)")
    parser.add_argument("--ledger", choices=("auto", "git", "local"), default="git")
    parser.add_argument("--no-push", action="store_true", help="Do not push Class A landing branches")
    parser.add_argument("--trigger", choices=("manual", "scheduled"), default="scheduled")
    parser.add_argument("--afk", action="store_true", help="Queue founder decisions instead of prompting")
    parser.add_argument("--report", default=DEFAULTREPORT, metavar="PATH",
                        help=f"Machine-readable summary (default: {DEFAULTREPORT})")
    parser.add_argument("--no-census", action="store_true",
                        help="Do not refresh the GitHub issue census before the run (issue hygiene then reports not evaluated)")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY") or DEFAULTREPO, metavar="OWNER/NAME",
                        help="repository whose issue census is collected (default: $GITHUB_REPOSITORY)")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = buildParser().parse_args(argv)
    root = Path(args.root).resolve()
    options = DriveOptions(
        root=root, integrationBranch=args.integration_branch, ledger=args.ledger,
        push=not args.no_push, trigger=args.trigger, afk=args.afk, reportPath=Path(args.report),
        census=not args.no_census, repo=args.repo,
    )
    if options.integrationBranch:
        refusal = baseRefusal(options.integrationBranch, None)
        if refusal:
            print(f"steward drive refused: {refusal}", file=sys.stderr)
            return EXITREFUSEDINPUT
    try:
        driver = Driver(options)
    except DriverConfigError as exc:
        print(f"steward drive refused: {exc}", file=sys.stderr)
        return EXITREFUSEDINPUT
    return driver.drive()


if __name__ == "__main__":
    raise SystemExit(main())
