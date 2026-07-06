#!/usr/bin/env python3
"""HumanEval benchmark harness (v1.0) — reference implementation.

Produces a `.benchmark-result.json` matching the reproducibility fingerprint
contract in `scripts/benchmarks/README.md`. The output feeds directly into
`gaia push --benchmark humaneval --from-result-file <path>`.

Determinism is the load-bearing property: the same (dataset, prompt template,
harness config) triple MUST produce the same score. CI reproduction gates on
this by re-running the harness and comparing to the pending row.

Two run modes:

- **Stubbed** (default, no external state): a deterministic pseudo-random
  pass/fail is derived from `(datasetHash, taskId)`. This is what the CI
  workflow reproduces — it exercises the whole pipeline without a live model.
- **Model runner** (`HUMANEVAL_MODEL_RUNNER` env var): shells out to a
  subprocess for each problem, feeding the rendered prompt on stdin and
  reading the completion from stdout. The command must be deterministic;
  otherwise CI reproduction fails and the row stays `pending`.

The evaluator itself is a sandboxed `exec` of the (canonical or generated)
solution body against the fixture's `test` block. For the stubbed evaluator
we simply exec the canonical solution when the deterministic RNG says "pass"
so that scoring stays faithful to the "solution executes cleanly" semantics
without needing an actual model.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


HARNESS_CONFIG_VERSION = "humaneval@v1.0"
"""Frozen harness-config identifier. Bumping this deliberately invalidates
benchmarkInputHash for every prior run — reserve for schema-breaking changes
to the harness contract itself."""


def _readBytes(path: Path) -> bytes:
    """Read a file's raw bytes; raise a clean error if missing."""
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    return path.read_bytes()


def _sha256(data: bytes) -> str:
    """Return lowercase hex SHA-256 of the given bytes."""
    return hashlib.sha256(data).hexdigest()


def _computeInputHash(datasetBytes: bytes, promptBytes: bytes) -> str:
    """Combined fingerprint over (dataset, prompt template, harness config).

    Any change to any of the three produces a new fingerprint. The order and
    delimiter are frozen — do not reshuffle without bumping HARNESS_CONFIG_VERSION.
    """
    hasher = hashlib.sha256()
    hasher.update(b"gaia-benchmark-input:")
    hasher.update(HARNESS_CONFIG_VERSION.encode("utf-8"))
    hasher.update(b"\x00")
    hasher.update(datasetBytes)
    hasher.update(b"\x00")
    hasher.update(promptBytes)
    return hasher.hexdigest()


def _renderPrompt(template: str, problemPrompt: str) -> str:
    """Interpolate the problem into the prompt template.

    The template uses the single placeholder `{prompt}`. We deliberately do
    NOT use str.format(**kwargs) so that braces in the template body (e.g.
    for f-string examples) do not break rendering.
    """
    return template.replace("{prompt}", problemPrompt)


def _runSolution(problem: dict, renderedPrompt: str, datasetHash: str) -> bool:
    """Attempt the given problem; return True on pass, False on fail.

    Delegates to `_runViaModel` when HUMANEVAL_MODEL_RUNNER is set; otherwise
    runs the stubbed evaluator (deterministic pseudo-random pass/fail seeded
    by datasetHash + taskId, then exec-verifies the canonical solution when
    the coin lands on "pass").
    """
    runnerCmd = os.environ.get("HUMANEVAL_MODEL_RUNNER", "").strip()
    if runnerCmd:
        completion = _runViaModel(runnerCmd, renderedPrompt)
    else:
        completion = _runStubbed(problem, datasetHash)
    if completion is None:
        return False
    return _execAndCheck(problem, completion)


def _runViaModel(runnerCmd: str, renderedPrompt: str) -> str | None:
    """Invoke the external model runner and return the raw completion."""
    try:
        proc = subprocess.run(
            runnerCmd,
            input=renderedPrompt,
            capture_output=True,
            text=True,
            timeout=120,
            shell=True,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


def _runStubbed(problem: dict, datasetHash: str) -> str | None:
    """Deterministic pass/fail seeded by (datasetHash, taskId).

    Uses ~66% pass rate (one-third fail) so the stubbed pipeline produces
    a non-trivial score (e.g. 4/6 on the fixture) — enough to distinguish
    a real score column from an all-pass or all-fail sanity check.

    When the coin says "pass", we hand back the canonical_solution so the
    exec-and-check path runs the real tests against real code — the harness
    still measures "does this solution actually pass" rather than trusting
    the RNG blindly.
    """
    seed = hashlib.sha256(
        f"{datasetHash}:{problem.get('task_id', '')}".encode("utf-8")
    ).digest()
    coin = seed[0] % 3  # 0/3 fails, 1-2/3 passes
    if coin == 0:
        return None
    return problem.get("canonical_solution", "")


def _execAndCheck(problem: dict, completion: str) -> bool:
    """Assemble the full function from prompt + completion, exec, run tests.

    Returns True iff the `check(candidate)` block from `problem["test"]`
    completes without raising. Uses a fresh namespace per problem; any
    exception (compile, run, assertion) is caught and reported as a fail.
    """
    entryPoint = problem.get("entry_point")
    if not entryPoint:
        return False
    program = (problem.get("prompt", "") or "") + completion + "\n" + (problem.get("test", "") or "")
    namespace: dict[str, Any] = {}
    try:
        exec(compile(program, "<humaneval>", "exec"), namespace)  # noqa: S102 — sandboxed by fixture design
        candidate = namespace.get(entryPoint)
        checker = namespace.get("check")
        if candidate is None or checker is None:
            return False
        checker(candidate)
    except Exception:
        return False
    return True


def _loadDataset(path: Path) -> tuple[list[dict], bytes]:
    """Load a JSONL problem file, returning (rows, raw bytes for hashing)."""
    rawBytes = _readBytes(path)
    rows: list[dict] = []
    for lineno, line in enumerate(rawBytes.decode("utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            rows.append(json.loads(stripped))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Malformed JSONL at {path}:{lineno}: {exc}") from exc
    if not rows:
        raise ValueError(f"Dataset {path} is empty — nothing to evaluate.")
    return rows, rawBytes


def _harnessCommit() -> str:
    """Return the current HEAD sha for the harness permalink base."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        rev = proc.stdout.strip()
        if rev:
            return rev
    except (OSError, subprocess.SubprocessError):
        pass
    return "unknown"


def main(
    skillId: str,
    datasetPath: Path,
    promptTemplate: Path,
    outputFile: Path = Path(".benchmark-result.json"),
    dryRun: bool = False,
) -> dict:
    """Deterministic entry point. Returns the result dict; also writes it.

    Raises FileNotFoundError on missing dataset / prompt template — that is
    the cleanest error path for tests to assert on.
    """
    rows, datasetBytes = _loadDataset(datasetPath)
    promptBytes = _readBytes(promptTemplate)
    promptText = promptBytes.decode("utf-8")

    datasetHash = _sha256(datasetBytes)
    inputHash = _computeInputHash(datasetBytes, promptBytes)

    passed = 0
    if not dryRun:
        for problem in rows:
            rendered = _renderPrompt(promptText, problem.get("prompt", ""))
            if _runSolution(problem, rendered, datasetHash):
                passed += 1

    total = len(rows)
    score = (passed / total) if total else 0.0
    runAt = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    result = {
        "skillId": skillId,
        "benchmarkId": HARNESS_CONFIG_VERSION,
        "score": round(score, 6),
        "unit": "pass@1",
        "pass": passed,
        "total": total,
        "datasetHash": datasetHash,
        "benchmarkInputHash": inputHash,
        "runAt": runAt,
        "harnessCommit": _harnessCommit(),
        "dryRun": bool(dryRun),
    }

    outputFile.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def _cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="humaneval-run",
        description="Run the HumanEval benchmark harness and emit a Gaia benchmark-result JSON.",
    )
    parser.add_argument("--skill-id", required=True, dest="skillId",
                        help="Skill identifier the score is attributed to (contributor/slug).")
    parser.add_argument("--dataset", required=True, type=Path,
                        help="Path to the HumanEval JSONL dataset (or fixture).")
    parser.add_argument("--prompt-template", required=True, type=Path, dest="promptTemplate",
                        help="Path to the versioned prompt template.")
    parser.add_argument("--out", default=Path(".benchmark-result.json"), type=Path, dest="outputFile",
                        help="Where to write the benchmark result JSON (default: .benchmark-result.json).")
    parser.add_argument("--dry-run", action="store_true", dest="dryRun",
                        help="Compute hashes and fingerprints but skip the evaluation loop.")
    args = parser.parse_args(argv)

    try:
        result = main(
            skillId=args.skillId,
            datasetPath=args.dataset,
            promptTemplate=args.promptTemplate,
            outputFile=args.outputFile,
            dryRun=args.dryRun,
        )
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"\nWrote {args.outputFile}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
