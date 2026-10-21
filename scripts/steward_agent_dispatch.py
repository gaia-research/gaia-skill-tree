#!/usr/bin/env python3
"""Engine-agnostic dispatch adapter for Gaia Steward agents.

Steward needs a fresh coding agent for one task: a builder (role ``build``) or
an independent verifier (role ``verify``). Each agent is a GitHub Agentic
Workflow compiled to ``.github/workflows/steward-<role>-<engine>.lock.yml``
and ends by uploading an artifact named ``steward-outcome`` holding one
``outcome.json`` object.

This adapter dispatches that workflow, waits for the run to finish, downloads
the outcome and prints it as ONE line of JSON on stdout. All human diagnostics
go to stderr, so a caller can parse the last JSON object on stdout.

The adapter never fabricates an outcome. Every failure exits non-zero.

Exit codes
  0  success: the outcome line is on stdout
  1  the run concluded unsuccessfully, or its outcome is missing or invalid
  2  refused input or configuration (bad flags, prompt too long, no repo)
  3  blocked: the agent could not be started (dispatch refused, gh failure)
  4  timeout: no new run appeared, or the run did not complete in time
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

EXITOK = 0
EXITFAILED = 1
EXITREFUSEDINPUT = 2
EXITBLOCKED = 3
EXITTIMEOUT = 4

ROLES = ("build", "verify")
ENGINES = ("copilot", "claude", "codex", "pi")
ARTIFACTNAME = "steward-outcome"
OUTCOMEFILE = "outcome.json"
PROMPTLIMIT = 60000
RESERVEDKEYS = ("engine", "runId", "runUrl")
SNAPSHOTFIELDS = "databaseId"
DISCOVERYFIELDS = "databaseId,createdAt"
REFENVVAR = "STEWARD_AGENT_REF"
REPOENVVAR = "GITHUB_REPOSITORY"
DEFAULTTIMEOUT = 2700
DEFAULTPOLL = 20

Runner = Callable[[Sequence[str]], subprocess.CompletedProcess]
Sleeper = Callable[[float], Any]
Clock = Callable[[], float]


class DispatchFailure(Exception):
    """A stop with a known exit code and a human-readable reason."""

    def __init__(self, exitCode: int, message: str):
        super().__init__(message)
        self.exitCode = exitCode
        self.message = message


@dataclass(frozen=True)
class Options:
    role: str
    engine: str
    promptPath: str
    dispatchId: str
    base: str | None = None
    branch: str | None = None
    ref: str | None = None
    repo: str | None = None
    timeout: int = DEFAULTTIMEOUT
    poll: int = DEFAULTPOLL


def note(message: str) -> None:
    print(f"steward-agent-dispatch: {message}", file=sys.stderr)


def defaultRunner(argv: Sequence[str]) -> subprocess.CompletedProcess:
    return subprocess.run(list(argv), capture_output=True, text=True, check=False)


def workflowFileName(role: str, engine: str) -> str:
    if role not in ROLES:
        raise DispatchFailure(EXITREFUSEDINPUT, f"unknown role {role!r}; expected one of {ROLES}")
    if engine not in ENGINES:
        raise DispatchFailure(EXITREFUSEDINPUT, f"unknown engine {engine!r}; expected one of {ENGINES}")
    return f"steward-{role}-{engine}.lock.yml"


def checkOptions(options: Options) -> None:
    workflowFileName(options.role, options.engine)
    if not options.dispatchId.strip():
        raise DispatchFailure(EXITREFUSEDINPUT, "--dispatch-id must not be empty")
    if options.role == "build":
        if not options.base or not options.branch:
            raise DispatchFailure(EXITREFUSEDINPUT, "--base and --branch are required for --role build")
    elif options.base or options.branch:
        raise DispatchFailure(EXITREFUSEDINPUT, "--base and --branch apply only to --role build")
    if options.timeout <= 0 or options.poll <= 0:
        raise DispatchFailure(EXITREFUSEDINPUT, "--timeout and --poll must be positive")


def resolveRepo(options: Options, env: Mapping[str, str]) -> str:
    repo = options.repo or env.get(REPOENVVAR, "")
    parts = repo.split("/")
    if len(parts) != 2 or not all(parts):
        raise DispatchFailure(
            EXITREFUSEDINPUT,
            f"repository must be OWNER/NAME; pass --repo or set {REPOENVVAR} (got {repo!r})",
        )
    return repo


def resolveRef(options: Options, repo: str, runner: Runner, env: Mapping[str, str]) -> str:
    if options.ref:
        return options.ref
    if env.get(REFENVVAR):
        return env[REFENVVAR]
    result = runner(["gh", "repo", "view", repo, "--json", "defaultBranchRef"])
    if result.returncode != 0:
        raise DispatchFailure(
            EXITBLOCKED,
            f"cannot resolve default branch of {repo}: gh exited {result.returncode}\n{result.stderr.rstrip()}",
        )
    view = parseJsonObject(result.stdout, "gh repo view output")
    branch = (view.get("defaultBranchRef") or {}).get("name")
    if not branch:
        raise DispatchFailure(EXITBLOCKED, f"gh repo view returned no default branch for {repo}")
    return branch


def readPrompt(path: str) -> str:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise DispatchFailure(EXITREFUSEDINPUT, f"cannot read prompt file {path}: {error}")
    if len(text) > PROMPTLIMIT:
        raise DispatchFailure(
            EXITREFUSEDINPUT,
            f"prompt is {len(text)} characters; the limit is {PROMPTLIMIT} "
            "(workflow dispatch inputs total 65535 characters)",
        )
    return text


def dispatchArgv(options: Options, repo: str, ref: str, prompt: str) -> list[str]:
    workflow = workflowFileName(options.role, options.engine)
    pairs = [f"dispatch-id={options.dispatchId}", f"prompt={prompt}"]
    if options.role == "build":
        pairs += [f"base={options.base}", f"branch={options.branch}"]
    argv = ["gh", "workflow", "run", workflow, "--repo", repo, "--ref", ref]
    for pair in pairs:
        argv += ["-f", pair]
    return argv


def listArgv(workflow: str, repo: str, fields: str) -> list[str]:
    return [
        "gh", "run", "list", "--workflow", workflow, "--repo", repo,
        "--event", "workflow_dispatch", "--limit", "30", "--json", fields,
    ]


def parseJsonText(text: str, what: str) -> Any:
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError) as error:
        raise DispatchFailure(EXITFAILED, f"{what} is not valid JSON: {error}")


def parseJsonObject(text: str, what: str) -> dict[str, Any]:
    value = parseJsonText(text, what)
    if not isinstance(value, dict):
        raise DispatchFailure(EXITFAILED, f"{what} is not a JSON object")
    return value


def parseRunList(text: str) -> list[dict[str, Any]]:
    value = parseJsonText(text, "gh run list output")
    if not isinstance(value, list):
        raise DispatchFailure(EXITFAILED, "gh run list output is not a JSON array")
    runs = []
    for entry in value:
        if not isinstance(entry, dict) or not isinstance(entry.get("databaseId"), int):
            raise DispatchFailure(EXITFAILED, f"gh run list entry has no integer databaseId: {entry!r}")
        runs.append(entry)
    return runs


def startedKey(run: Mapping[str, Any]) -> tuple[dt.datetime, int]:
    sentinel = dt.datetime.max.replace(tzinfo=dt.timezone.utc)
    value = run.get("createdAt")
    started = sentinel
    if isinstance(value, str):
        try:
            started = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
            if started.tzinfo is None:
                started = started.replace(tzinfo=dt.timezone.utc)
        except ValueError:
            started = sentinel
    return (started, run["databaseId"])


def snapshotRunIds(runner: Runner, options: Options, repo: str, workflow: str) -> set[int]:
    result = runner(listArgv(workflow, repo, SNAPSHOTFIELDS))
    if result.returncode != 0:
        raise DispatchFailure(
            EXITBLOCKED,
            f"cannot list existing runs of {workflow}: gh exited {result.returncode}\n{result.stderr.rstrip()}",
        )
    return {run["databaseId"] for run in parseRunList(result.stdout)}


def waitForNewRun(
    runner: Runner,
    options: Options,
    repo: str,
    workflow: str,
    snapshot: set[int],
    sleep: Sleeper,
    clock: Clock,
) -> dict[str, Any]:
    deadline = clock() + options.timeout
    while True:
        result = runner(listArgv(workflow, repo, DISCOVERYFIELDS))
        if result.returncode != 0:
            note(f"gh run list failed (exit {result.returncode}); retrying: {result.stderr.rstrip()}")
        else:
            fresh = [run for run in parseRunList(result.stdout) if run["databaseId"] not in snapshot]
            if fresh:
                ordered = sorted(fresh, key=startedKey)
                if len(ordered) > 1:
                    note(
                        f"{len(ordered)} new runs of {workflow} appeared; "
                        f"choosing the earliest, run {ordered[0]['databaseId']}"
                    )
                return ordered[0]
        if clock() >= deadline:
            raise DispatchFailure(
                EXITTIMEOUT,
                f"no new run of {workflow} appeared within {options.timeout}s after dispatch",
            )
        sleep(options.poll)


def waitForCompletion(
    runner: Runner,
    options: Options,
    repo: str,
    runId: int,
    sleep: Sleeper,
    clock: Clock,
) -> dict[str, Any]:
    deadline = clock() + options.timeout
    runArg = str(runId)
    while True:
        result = runner(["gh", "run", "view", runArg, "--repo", repo, "--json", "status,conclusion,url"])
        if result.returncode != 0:
            note(f"gh run view failed (exit {result.returncode}); retrying: {result.stderr.rstrip()}")
        else:
            view = parseJsonObject(result.stdout, "gh run view output")
            if view.get("status") == "completed":
                return view
        if clock() >= deadline:
            cancel = runner(["gh", "run", "cancel", runArg, "--repo", repo])
            if cancel.returncode != 0:
                note(f"gh run cancel {runArg} failed (exit {cancel.returncode}): {cancel.stderr.rstrip()}")
            raise DispatchFailure(
                EXITTIMEOUT,
                f"run {runId} did not complete within {options.timeout}s; cancellation requested",
            )
        sleep(options.poll)


def readOutcome(directory: Path) -> dict[str, Any]:
    candidates = sorted(directory.rglob(OUTCOMEFILE), key=lambda path: (len(path.parts), str(path)))
    if not candidates:
        raise DispatchFailure(EXITFAILED, f"artifact {ARTIFACTNAME} contains no {OUTCOMEFILE}")
    try:
        text = candidates[0].read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise DispatchFailure(EXITFAILED, f"cannot read {OUTCOMEFILE}: {error}")
    try:
        value = json.loads(text)
    except json.JSONDecodeError as error:
        raise DispatchFailure(EXITFAILED, f"{OUTCOMEFILE} is not valid JSON: {error}")
    if not isinstance(value, dict):
        raise DispatchFailure(EXITFAILED, f"{OUTCOMEFILE} must hold a JSON object, not {type(value).__name__}")
    return value


def fetchOutcome(runner: Runner, repo: str, runId: int, directory: Path) -> dict[str, Any]:
    result = runner([
        "gh", "run", "download", str(runId), "--repo", repo,
        "-n", ARTIFACTNAME, "-D", str(directory),
    ])
    if result.returncode != 0:
        raise DispatchFailure(
            EXITFAILED,
            f"cannot download artifact {ARTIFACTNAME} from run {runId}: gh exited {result.returncode}\n"
            f"{result.stderr.rstrip()}",
        )
    return readOutcome(directory)


def mergeOutcome(outcome: Mapping[str, Any], engine: str, runId: int, runUrl: str) -> dict[str, Any]:
    overlapping = [key for key in RESERVEDKEYS if key in outcome]
    if overlapping:
        note(f"outcome supplied reserved keys {overlapping}; the adapter values are kept")
    merged = {key: value for key, value in outcome.items() if key not in RESERVEDKEYS}
    merged.update({"engine": engine, "runId": runId, "runUrl": runUrl})
    return merged


def runDispatch(
    options: Options,
    *,
    runner: Runner,
    sleep: Sleeper,
    clock: Clock,
    env: Mapping[str, str],
) -> dict[str, Any]:
    checkOptions(options)
    repo = resolveRepo(options, env)
    prompt = readPrompt(options.promptPath)
    ref = resolveRef(options, repo, runner, env)
    workflow = workflowFileName(options.role, options.engine)

    snapshot = snapshotRunIds(runner, options, repo, workflow)

    started = runner(dispatchArgv(options, repo, ref, prompt))
    if started.returncode != 0:
        raise DispatchFailure(
            EXITBLOCKED,
            f"cannot start agent {workflow} on ref {ref}: gh exited {started.returncode}\n"
            f"{started.stderr.rstrip()}",
        )

    run = waitForNewRun(runner, options, repo, workflow, snapshot, sleep, clock)
    runId = run["databaseId"]
    view = waitForCompletion(runner, options, repo, runId, sleep, clock)
    runUrl = view.get("url") or ""
    conclusion = view.get("conclusion") or ""
    if conclusion != "success":
        raise DispatchFailure(
            EXITFAILED,
            f"run {runId} concluded {conclusion or 'without a conclusion'}; {runUrl}",
        )

    with tempfile.TemporaryDirectory(prefix="steward-agent-") as scratch:
        outcome = fetchOutcome(runner, repo, runId, Path(scratch))
    return mergeOutcome(outcome, options.engine, runId, runUrl)


def buildParser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dispatch a Gaia Steward agent and print its outcome.")
    parser.add_argument("--role", required=True, choices=ROLES)
    parser.add_argument("--engine", required=True, choices=ENGINES)
    parser.add_argument("--prompt-path", required=True)
    parser.add_argument("--dispatch-id", required=True)
    parser.add_argument("--base")
    parser.add_argument("--branch")
    parser.add_argument("--ref")
    parser.add_argument("--repo")
    parser.add_argument("--timeout", type=int, default=DEFAULTTIMEOUT)
    parser.add_argument("--poll", type=int, default=DEFAULTPOLL)
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    runner: Runner | None = None,
    sleep: Sleeper | None = None,
    clock: Clock | None = None,
    env: Mapping[str, str] | None = None,
) -> int:
    args = buildParser().parse_args(argv)
    options = Options(
        role=args.role,
        engine=args.engine,
        promptPath=args.prompt_path,
        dispatchId=args.dispatch_id,
        base=args.base,
        branch=args.branch,
        ref=args.ref,
        repo=args.repo,
        timeout=args.timeout,
        poll=args.poll,
    )
    try:
        outcome = runDispatch(
            options,
            runner=runner or defaultRunner,
            sleep=sleep or time.sleep,
            clock=clock or time.monotonic,
            env=os.environ if env is None else env,
        )
    except DispatchFailure as failure:
        note(failure.message)
        return failure.exitCode
    print(json.dumps(outcome, ensure_ascii=False))
    return EXITOK


if __name__ == "__main__":
    sys.exit(main())
