"""One deterministic, read-only way to produce a job's raw history rows (workflow-timeout route).

The history and no-history rules in ``workflowproof`` recompute a timeout from one
job's raw rows. Before this module, nothing allowed in the packet produced that
rows file: the ``gh api ... --jq`` command emits one JSON line per job per run, the
jobs API keys jobs by display name rather than YAML key, and the route may not
write inside the repository. ``fetch`` closes that gap:

* it resolves the YAML job key to the display name(s) GitHub reports, from the
  workflow file itself (``name:``, matrix legs), and refuses anything it cannot
  resolve exactly (an expression other than ``${{ matrix.<key> }}``, ``include`` /
  ``exclude``, a float or boolean matrix value, an ambiguous name);
* it samples the same runs the route always sampled (the latest 50 completed runs
  of the workflow) and reads each run's jobs for the attempt that run list reported,
  so a later re-run never changes the bytes;
* it keeps only rows whose name is a current display name of this job: a job that
  was renamed contributes rows for its current name only;
* it writes one canonical JSON document (sorted keys, no timestamps of its own) to
  an ``--out`` path that must lie outside the repository checkout, and prints its
  sha256 and the pinned ``--run-ids``;
* ``--run-ids`` plus ``--expect-sha256`` let the independent verifier refetch the
  same runs and prove byte-identical input before recomputing the value.

It fails closed: an API failure, a truncated jobs page, no completed runs, or no
row for the job is "history cannot be read" (exit 3, nothing written), exactly the
existing stop condition. The rows file is accepted unchanged by
``workflowproof history|no-history --history`` (its ``jobs`` list).
"""

from __future__ import annotations

import hashlib
import itertools
import json
import re
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping, Sequence

import yaml

SCHEMA = "steward-workflow-job-history-v1"
DEFAULT_REPOSITORY = "gaia-research/gaia-skill-tree"
RUN_SAMPLE = 50
JOBS_PAGE = 100
HISTORY_DIR_HINT = "${TMPDIR:-/tmp}/gaia-steward-history"
_MATRIX_EXPRESSION = re.compile(r"\$\{\{\s*matrix\.([A-Za-z0-9_-]+)\s*\}\}")
_FLAGGED = re.compile(r"^job (?P<job>.+) has no timeout-minutes$")
_SHA = re.compile(r"^sha256: ([0-9a-f]{64})$", re.MULTILINE)
_RUN_IDS = re.compile(r"^run-ids: ([0-9]+:[0-9]+(?:,[0-9]+:[0-9]+)*)$", re.MULTILINE)
_JOB_KEY = re.compile(r"^job-key: (.+)$", re.MULTILINE)
_WORKFLOW_LINE = re.compile(r"^workflow: (.+)$", re.MULTILINE)
_SAFE_KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_-]{0,99}")
_SAFE_PATH = re.compile(r"\.github/workflows/[A-Za-z0-9._-]+\.yml")
_SHELL_BREAKS = {"&&", "||", ";", "|", ">", ">>", "2>&1", "<"}

Gh = Callable[[Sequence[str]], str]


class HistoryRefused(ValueError):
    """The request itself is invalid or unresolvable (exit 2)."""


class HistoryUnavailable(RuntimeError):
    """History cannot be read for this job: the route stops (exit 3)."""


# --------------------------------------------------------------------------
# YAML job key -> display names
# --------------------------------------------------------------------------


def _matrix_value(value: Any, where: str) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise HistoryRefused(
            f"{where}: matrix value {value!r} is not a string or integer; its display form is ambiguous"
        )
    return str(value)


def _job_display_names(key: str, job: Mapping[str, Any]) -> tuple[str, ...]:
    """Every display name GitHub reports for one job (one per matrix leg)."""

    name = job.get("name", key)
    if not isinstance(name, str) or not name:
        raise HistoryRefused(f"job {key!r}: name is not a non-empty string")
    strategy = job.get("strategy")
    matrix = strategy.get("matrix") if isinstance(strategy, dict) else None
    if matrix is None:
        if "${{" in name:
            raise HistoryRefused(f"job {key!r}: display name {name!r} contains an expression")
        return (name,)
    if not isinstance(matrix, dict) or not matrix:
        raise HistoryRefused(f"job {key!r}: matrix is not a literal mapping")
    if "include" in matrix or "exclude" in matrix:
        raise HistoryRefused(f"job {key!r}: matrix include/exclude is not resolved; stop")
    dims: list[tuple[str, list[str]]] = []
    for dim, values in matrix.items():
        if not isinstance(values, list) or not values:
            raise HistoryRefused(f"job {key!r}: matrix {dim!r} is not a literal non-empty list")
        dims.append((str(dim), [_matrix_value(v, f"job {key!r} matrix {dim!r}") for v in values]))
    names: list[str] = []
    for combo in itertools.product(*(values for _, values in dims)):
        bound = dict(zip((dim for dim, _ in dims), combo, strict=True))
        if _MATRIX_EXPRESSION.search(name):
            missing = [m for m in _MATRIX_EXPRESSION.findall(name) if m not in bound]
            if missing:
                raise HistoryRefused(f"job {key!r}: name refers to unknown matrix key(s) {missing}")
            rendered = _MATRIX_EXPRESSION.sub(lambda m, values=bound: values[m.group(1)], name)
        else:
            rendered = f"{name} ({', '.join(combo)})"
        if "${{" in rendered:
            raise HistoryRefused(f"job {key!r}: display name {name!r} contains an unresolvable expression")
        names.append(rendered)
    return tuple(names)


def resolve_job(workflow_text: str, job: str) -> tuple[str, tuple[str, ...]]:
    """``(yaml key, display names)`` for ``job``, given as a YAML key or a display name."""

    try:
        document = yaml.safe_load(workflow_text)
    except yaml.YAMLError as exc:
        raise HistoryRefused(f"workflow does not parse ({type(exc).__name__})") from exc
    jobs = document.get("jobs") if isinstance(document, dict) else None
    if not isinstance(jobs, dict) or not jobs:
        raise HistoryRefused("workflow has no jobs mapping")
    if job in jobs and isinstance(jobs[job], dict):
        key = job
    else:
        matches = []
        for candidate, body in jobs.items():
            if not isinstance(body, dict):
                continue
            try:
                if job in _job_display_names(str(candidate), body):
                    matches.append(str(candidate))
            except HistoryRefused:
                continue
        if len(matches) != 1:
            raise HistoryRefused(
                f"{job!r} is not a job key and matches {len(matches)} job display names; give the YAML job key"
            )
        key = matches[0]
    body = jobs[key]
    if "uses" in body:
        raise HistoryRefused(f"job {key!r} is a reusable-workflow call; it cannot take timeout-minutes")
    names = _job_display_names(key, body)
    for other, other_body in jobs.items():
        if str(other) == key or not isinstance(other_body, dict):
            continue
        try:
            clash = set(names) & set(_job_display_names(str(other), other_body))
        except HistoryRefused:
            continue
        if clash:
            raise HistoryRefused(
                f"job {key!r} shares display name(s) {sorted(clash)} with job {other!r}; rows cannot be attributed"
            )
    return key, names


# --------------------------------------------------------------------------
# The two GETs
# --------------------------------------------------------------------------


def run_gh(args: Sequence[str]) -> str:
    """Run ``gh`` read-only; any failure is unreadable history."""

    try:
        done = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=120, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HistoryUnavailable(f"gh could not run: {exc}") from exc
    if done.returncode != 0:
        raise HistoryUnavailable(f"gh {' '.join(args[:2])} failed (exit {done.returncode}): {done.stderr.strip()[:200]}")
    return done.stdout


def _json(text: str, what: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise HistoryUnavailable(f"{what} is not JSON: {exc}") from exc


def parse_run_ids(value: str) -> list[tuple[int, int]]:
    pins: list[tuple[int, int]] = []
    for part in value.split(","):
        match = re.fullmatch(r"([1-9][0-9]*):([1-9][0-9]*)", part.strip())
        if not match:
            raise HistoryRefused(f"--run-ids entry {part!r} is not <run-id>:<attempt>")
        pins.append((int(match.group(1)), int(match.group(2))))
    if not pins or len(set(pins)) != len(pins):
        raise HistoryRefused("--run-ids must list distinct <run-id>:<attempt> pairs")
    return pins


def sample_runs(workflow: str, repository: str, gh: Gh) -> list[tuple[int, int]]:
    """The latest completed runs of the workflow, as (run id, attempt), in API order."""

    raw = _json(
        gh([
            "run", "list", "--repo", repository, "--workflow", PurePosixPath(workflow).name,
            "--status", "completed", "--limit", str(RUN_SAMPLE), "--json", "databaseId,attempt",
        ]),
        "gh run list output",
    )
    if not isinstance(raw, list):
        raise HistoryUnavailable("gh run list did not return a list")
    pins: list[tuple[int, int]] = []
    for item in raw:
        run_id = item.get("databaseId") if isinstance(item, dict) else None
        attempt = item.get("attempt") if isinstance(item, dict) else None
        if isinstance(run_id, bool) or not isinstance(run_id, int) or isinstance(attempt, bool) or not isinstance(attempt, int):
            raise HistoryUnavailable(f"gh run list returned an unusable row: {item!r}"[:200])
        pins.append((run_id, attempt))
    return pins


def run_jobs(run_id: int, attempt: int, repository: str, gh: Gh) -> list[dict[str, Any]]:
    data = _json(
        gh(["api", f"repos/{repository}/actions/runs/{run_id}/attempts/{attempt}/jobs?per_page={JOBS_PAGE}"]),
        f"jobs of run {run_id}",
    )
    jobs = data.get("jobs") if isinstance(data, dict) else None
    total = data.get("total_count") if isinstance(data, dict) else None
    if not isinstance(jobs, list) or not isinstance(total, int):
        raise HistoryUnavailable(f"jobs of run {run_id} have no jobs list / total_count")
    if total > len(jobs):
        raise HistoryUnavailable(f"run {run_id} has {total} jobs but one page returned {len(jobs)}; refusing a partial sample")
    return [job for job in jobs if isinstance(job, dict)]


# --------------------------------------------------------------------------
# fetch
# --------------------------------------------------------------------------


def build_document(
    workflow: str,
    workflow_text: str,
    job: str,
    *,
    repository: str = DEFAULT_REPOSITORY,
    pins: Sequence[tuple[int, int]] | None = None,
    gh: Gh = run_gh,
) -> dict[str, Any]:
    """The canonical rows document for one job, or raise."""

    key, names = resolve_job(workflow_text, job)
    sampled = list(pins) if pins is not None else sample_runs(workflow, repository, gh)
    if not sampled:
        raise HistoryUnavailable("the workflow has no completed runs; history cannot be read")
    rows: list[dict[str, Any]] = []
    without: list[int] = []
    wanted = set(names)
    for run_id, attempt in sampled:
        found = False
        for item in run_jobs(run_id, attempt, repository, gh):
            if item.get("name") in wanted:
                found = True
                rows.append({
                    "runId": run_id,
                    "attempt": attempt,
                    "name": item.get("name"),
                    "conclusion": item.get("conclusion"),
                    "started_at": item.get("started_at"),
                    "completed_at": item.get("completed_at"),
                })
        if not found:
            without.append(run_id)
    if not rows:
        raise HistoryUnavailable(
            f"none of the {len(sampled)} sampled runs has a job named {sorted(names)}; history cannot be read"
        )
    # Canonical order, so the bytes never depend on the order the API listed runs or jobs.
    rows.sort(key=_row_key)
    return {
        "schemaVersion": SCHEMA,
        "repository": repository,
        "workflow": workflow,
        "job": {"key": key, "displayNames": sorted(names)},
        "runs": [{"id": run_id, "attempt": attempt} for run_id, attempt in sorted(set(sampled))],
        "runsWithoutJob": sorted(set(without)),
        "jobs": rows,
    }


def _row_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    """A complete sort key: every field of a row, so equal keys mean identical rows."""

    return (
        row["runId"],
        row["attempt"],
        *(json.dumps(row.get(field), sort_keys=True) for field in ("name", "started_at", "completed_at", "conclusion")),
    )


def render(document: Mapping[str, Any]) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("ascii")


def _checkout_root(cwd: Path) -> Path | None:
    done = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], cwd=cwd, capture_output=True, text=True, check=False
    )
    return Path(done.stdout.strip()).resolve() if done.returncode == 0 and done.stdout.strip() else None


def check_out_path(out: Path, checkout: Path | None) -> Path:
    """``out`` resolved; refused when it lies inside the repository checkout."""

    resolved = out.expanduser().resolve()
    if checkout is not None and (resolved == checkout or checkout in resolved.parents):
        raise HistoryRefused(
            f"--out {out} is inside the repository checkout; the rows file must live outside it "
            f"(for example {HISTORY_DIR_HINT}/<dispatch-id>/build/<job-key>.json)"
        )
    return resolved


def fetch_main(args: Any, *, cwd: Path | None = None, gh: Gh = run_gh) -> int:
    """CLI body for ``workflowproof fetch``; returns the exit code."""

    cwd = (cwd or Path.cwd()).resolve()
    checkout = _checkout_root(cwd)
    base = checkout or cwd
    try:
        workflow = str(PurePosixPath(args.workflow))
        if PurePosixPath(workflow).parent != PurePosixPath(".github/workflows") or not workflow.endswith(".yml"):
            raise HistoryRefused(f"--workflow {args.workflow!r} is not a direct-child .github/workflows/*.yml path")
        if workflow.endswith(".lock.yml"):
            raise HistoryRefused("--workflow is a gh-aw lock file; that route is founder-gated")
        path = base / workflow
        if not path.is_file():
            raise HistoryRefused(f"{workflow} does not exist in this checkout")
        out = check_out_path(Path(args.out), checkout)
        pins = parse_run_ids(args.run_ids) if args.run_ids else None
        document = build_document(
            workflow, path.read_text(encoding="utf-8"), args.job, repository=args.repo, pins=pins, gh=gh
        )
    except HistoryRefused as exc:
        print(f"refused: {exc}")
        return 2
    except HistoryUnavailable as exc:
        print(f"history unreadable: {exc}; stop")
        return 3
    payload = render(document)
    digest = hashlib.sha256(payload).hexdigest()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(payload)
    run_ids = ",".join(f"{run['id']}:{run['attempt']}" for run in document["runs"])
    print(f"workflow: {document['workflow']}")
    print(f"job-key: {document['job']['key']}")
    print(f"display-names: {json.dumps(document['job']['displayNames'])}")
    print(f"runs: {len(document['runs'])} ({'pinned' if pins else f'latest {RUN_SAMPLE} completed'}); "
          f"rows: {len(document['jobs'])}; runs without this job: {len(document['runsWithoutJob'])}")
    print(f"out: {out}")
    print(f"sha256: {digest}")
    print(f"run-ids: {run_ids}")
    if args.expect_sha256 and args.expect_sha256 != digest:
        print(f"MISMATCH: expected sha256 {args.expect_sha256}; the recomputed rows differ; stop")
        return 4
    if args.expect_sha256:
        print("recompute: byte-identical")
    return 0


# --------------------------------------------------------------------------
# Provenance check (mechanical) and verifier recompute (rendered)
# --------------------------------------------------------------------------


def uses_fetch(allowed_commands: Sequence[str]) -> bool:
    """Whether a packet was commissioned under the envelope that includes ``fetch``."""

    return any("gaia_cli.steward.workflowproof fetch" in command for command in allowed_commands)


def _proof_command(command: str) -> tuple[str, Any] | None:
    """``(subcommand, parsed args)`` for a ``workflowproof`` invocation, else None."""

    from gaia_cli.steward.workflowproof import build_parser

    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    for index in range(len(tokens) - 1):
        if tokens[index] == "-m" and tokens[index + 1] == "gaia_cli.steward.workflowproof":
            rest: list[str] = []
            for token in tokens[index + 2:]:
                if token in _SHELL_BREAKS:
                    break
                rest.append(token)
            try:
                parsed = build_parser().parse_args(rest)
            except SystemExit:
                return None
            return parsed.rule, parsed
    return None


def _entries(transcript_text: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(transcript_text)
    except json.JSONDecodeError:
        return []
    entries = data.get("entries") if isinstance(data, dict) else None
    return [e for e in entries if isinstance(e, dict)] if isinstance(entries, list) else []


def flagged_jobs(evidence: Mapping[str, Any]) -> list[str]:
    state = evidence.get("observedState", evidence)
    findings = state.get("findings") if isinstance(state, Mapping) else None
    jobs: list[str] = []
    for item in findings or []:
        if isinstance(item, Mapping) and item.get("rule") == "missing-timeout":
            match = _FLAGGED.match(str(item.get("detail", "")))
            if match:
                jobs.append(match.group("job"))
    return sorted(set(jobs))


@dataclass(frozen=True)
class FetchRecord:
    """One successful ``fetch`` proof entry, with every metadata field present exactly once."""

    workflow: str
    job: str
    out: str
    sha256: str
    run_ids: str


def _single(pattern: re.Pattern[str], output: str) -> str | None:
    found = pattern.findall(output)
    return found[0].strip() if len(found) == 1 else None


def parse_provenance(transcript_text: str) -> tuple[list[FetchRecord], list[tuple[str, Any]], list[str]]:
    """Parse item-2 proof entries once: ``(fetch records, rule entries, problems)``.

    Metadata is read only from the captured output of a successful ``fetch`` entry,
    never from a history/no-history entry or a statement. A fetch entry whose output
    lacks, repeats or contradicts any field (``workflow``, ``job-key``, ``sha256``,
    ``run-ids``) is a problem, not a skipped record.
    """

    records: list[FetchRecord] = []
    rules: list[tuple[str, Any]] = []
    problems: list[str] = []
    for entry in _entries(transcript_text):
        if entry.get("contractIndex") != 2 or entry.get("exitCode") != 0:
            continue
        parsed = _proof_command(str(entry.get("command", "")))
        if parsed is None:
            continue
        rule, args = parsed
        if rule != "fetch":
            rules.append((rule, args))
            continue
        output = str(entry.get("output", ""))
        fields = {
            "workflow": _single(_WORKFLOW_LINE, output),
            "job-key": _single(_JOB_KEY, output),
            "sha256": _single(_SHA, output),
            "run-ids": _single(_RUN_IDS, output),
        }
        missing = sorted(name for name, value in fields.items() if value is None)
        if missing:
            problems.append(
                f"fetch entry for {str(args.job)[:60]!r} lacks exactly one {', '.join(missing)} line in its output"
            )
            continue
        if fields["workflow"] != args.workflow or fields["job-key"] != args.job:
            problems.append(
                f"fetch entry for {str(args.job)[:60]!r}: its output names {fields['workflow']!r} / "
                f"{fields['job-key']!r}, not the command's --workflow / --job"
            )
            continue
        records.append(FetchRecord(args.workflow, args.job, args.out, fields["sha256"], fields["run-ids"]))
    return records, rules, problems


def history_provenance(
    *, evidence: Mapping[str, Any], subject: str | None, transcript_text: str, dispatch_id: str
) -> tuple[list[str], list[str]]:
    """``(violations, verifier recompute commands)`` from one parse of the transcript.

    Every flagged job needs exactly one complete fetch record for the subject
    workflow, and a history/no-history entry reading exactly that record's ``--out``.
    The recompute commands are rendered only from those records, with the subject
    and job names taken from the packet; any violation yields no commands, and the
    violations reject the build, so provenance is never silently omitted.
    """

    records, rules, problems = parse_provenance(transcript_text)
    flagged = flagged_jobs(evidence)
    if subject is None or _SAFE_PATH.fullmatch(subject) is None:
        problems.append(f"the packet subject {subject!r} is not a direct-child workflow path")
    by_job: dict[str, list[FetchRecord]] = {}
    for record in records:
        by_job.setdefault(record.job, []).append(record)
    outs = {record.out for record in records}
    consumed = {args.history for _, args in rules if args.history in outs}
    for rule, args in rules:
        if args.history not in outs:
            problems.append(f"{rule} --history {args.history} was not produced by a workflowproof fetch entry")
    chosen: dict[str, FetchRecord] = {}
    for job in flagged:
        found = by_job.get(job, [])
        if not _SAFE_KEY.fullmatch(job):
            problems.append(f"job {job[:60]!r} is not a plain YAML job key")
        elif not found:
            problems.append(f"job {job!r}: no successful workflowproof fetch entry under proof item 2")
        elif len(found) > 1:
            problems.append(f"job {job!r}: {len(found)} fetch entries; exactly one is allowed")
        elif found[0].workflow != subject:
            problems.append(f"job {job!r}: fetched {found[0].workflow}, not the subject {subject}")
        elif found[0].out not in consumed:
            problems.append(f"job {job!r}: no history or no-history entry reads its fetched rows file")
        else:
            chosen[job] = found[0]
    if problems or not flagged:
        return problems or ["the packet names no flagged job"], []
    commands: list[str] = []
    for job in flagged:
        record = chosen[job]
        rows = f"{HISTORY_DIR_HINT}/{dispatch_id}/verify/{job}.json"
        commands.append(
            f"python -m gaia_cli.steward.workflowproof fetch --workflow {subject} --job {job} "
            f"--run-ids {record.run_ids} --expect-sha256 {record.sha256} --out {rows}"
        )
        commands.append(f"python -m gaia_cli.steward.workflowproof history --history {rows}")
    return [], commands
