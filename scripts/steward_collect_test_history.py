#!/usr/bin/env python3
"""Fold pytest JUnit XML into the Steward test-history sensor's driver input.

The Steward sensors never touch the network. A driver (the scheduled workflow,
or an operator) runs pytest with ``--junitxml`` and hands the result over as
``.gaia/steward/inputs/test-history.json`` (``steward-test-history-v1``). This
script is that hand-over: a pure transform with no network access of its own.

    python -m pytest tests -q --junitxml=junit-abc123.xml
    python scripts/steward_collect_test_history.py \
      --run 25001 3f2c9d1 junit-abc123.xml --repository gaia-research/gaia-skill-tree

Run pytest from the repository root so node ids come out repository-relative
(pytest derives them from its rootdir), and keep the runId stable across
re-runs of the same CI run.

Each ``--run RUNID SHA JUNIT`` contributes one run. The run is merged into the
existing history: a run with the same runId replaces the old entry, the history
keeps the newest runs, and the output is written atomically. The caps mirror
the sensor's own (run count, result count, file size), so a history this script
writes is one the sensor will read.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "steward-test-history-v1"
OUTPUT = Path(".gaia/steward/inputs/test-history.json")
RUNCAP = 5000
RESULTCAP = 500_000
BYTECAP = 8 * 1024 * 1024
STATUSES = ("passed", "failed", "error", "skipped")
# When one JUnit file reports a node twice, the more severe outcome wins.
RANK = {"passed": 0, "skipped": 1, "failed": 2, "error": 3}
ENCODING = {"sort_keys": True, "separators": (",", ":")}


class InputError(ValueError):
    """The JUnit file, the existing history or the requested runs cannot be recorded."""


def encode(value: Any) -> str:
    return json.dumps(value, **ENCODING)


def caseId(classname: str, name: str) -> str:
    """Rebuild a pytest node id from a JUnit testcase.

    pytest's JUnit output carries the module as a dotted classname
    (``tests.steward.test_x.TestClass``) and no file attribute, so the module is
    the first dotted part that looks like a test module (``test_*`` or ``*_test``).
    """

    parts = classname.split(".") if classname else []
    index = next(
        (position for position, part in enumerate(parts) if part.startswith("test_") or part.endswith("_test")),
        None,
    )
    if index is None and not classname:
        # A module pytest skipped at collection (``pytest.importorskip``, a
        # missing optional dependency) is reported with an empty classname and
        # the dotted module path as the testcase name. It is a module-level
        # record, not a malformed one: keep it as the module's own node id.
        module_parts = name.split(".")
        if any(part.startswith("test_") or part.endswith("_test") for part in module_parts) and all(
            part.isidentifier() for part in module_parts
        ):
            return "/".join(module_parts) + ".py"
    if index is None:
        raise InputError(f"cannot locate the test module for testcase {name!r}")
    module = "/".join(parts[: index + 1]) + ".py"
    return "::".join([module, *parts[index + 1 :], name])


def caseStatus(case: ET.Element) -> str:
    # A rerunFailure child (pytest-rerunfailures) is a failed attempt that was
    # rerun, not the outcome, so it is deliberately not counted here.
    tags = {child.tag for child in case}
    if "error" in tags:
        return "error"
    if "failure" in tags:
        return "failed"
    if "skipped" in tags:
        return "skipped"
    return "passed"


def readJunit(path: Path) -> dict[str, str]:
    try:
        tree = ET.parse(path)
    except (OSError, ET.ParseError) as exc:
        raise InputError(f"{path} is not readable JUnit XML: {exc}") from exc
    results: dict[str, str] = {}
    for case in tree.getroot().iter("testcase"):
        key = caseId(case.get("classname", ""), case.get("name", ""))
        value = caseStatus(case)
        if key in results and RANK[results[key]] >= RANK[value]:
            continue
        results[key] = value
    return results


def checkRun(run: Any) -> None:
    """Refuse anything the sensor would refuse, before it reaches the file."""

    if not isinstance(run, dict):
        raise InputError("a run must be an object")
    runid, sha, results = run.get("runId"), run.get("sha"), run.get("results")
    if not isinstance(runid, str) or not runid or not isinstance(sha, str) or not sha:
        raise InputError("a run needs a non-empty string runId and sha")
    if not isinstance(results, dict):
        raise InputError(f"run {runid!r} results must be an object")
    for nodeid, status in results.items():
        if not isinstance(nodeid, str) or status not in STATUSES:
            raise InputError(f"run {runid!r} has an invalid result entry")


def readHistory(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InputError(f"existing history {path} is unreadable: {exc}") from exc
    if not isinstance(document, dict) or document.get("schemaVersion") != SCHEMA:
        raise InputError(f"existing history {path} is not a {SCHEMA} document; refusing to overwrite it")
    if not isinstance(document.get("runs"), list):
        raise InputError(f"existing history {path} has no runs list; refusing to overwrite it")
    return document


def trim(runs: list[dict[str, Any]], header: dict[str, Any]) -> list[dict[str, Any]]:
    """Keep the newest runs that fit the sensor's caps, dropping the oldest first."""

    budget = len(encode({**header, "runs": []}).encode("utf-8"))
    kept: list[dict[str, Any]] = []
    results = 0
    for run in reversed(runs):
        cost = len(encode(run).encode("utf-8")) + 1
        count = len(run["results"])
        if len(kept) == RUNCAP or results + count > RESULTCAP or budget + cost > BYTECAP:
            break
        kept.append(run)
        results += count
        budget += cost
    if runs and not kept:
        raise InputError("the newest run alone exceeds the sensor's result or size caps")
    return list(reversed(kept))


def build(
    history: dict[str, Any] | None,
    incoming: list[dict[str, Any]],
    *,
    repository: str | None,
    collected: str,
) -> dict[str, Any]:
    """Merge incoming runs into the history. Pure: no file access."""

    ids = [run.get("runId") for run in incoming]
    if len(set(ids)) != len(ids):
        raise InputError("two --run arguments share a runId")
    for run in incoming:
        checkRun(run)
    existing = history.get("runs", []) if history else []
    for run in existing:
        checkRun(run)
    # Re-inserting moves a run to the end, so a replaced runId takes its newest position.
    ordered: dict[str, dict[str, Any]] = {}
    for run in existing + incoming:
        ordered.pop(run["runId"], None)
        ordered[run["runId"]] = run
    header: dict[str, Any] = {"schemaVersion": SCHEMA, "collectedAt": collected}
    chosen = repository or (history or {}).get("repository")
    if chosen:
        header["repository"] = chosen
    return {**header, "runs": trim(list(ordered.values()), header)}


def render(document: dict[str, Any]) -> str:
    text = encode(document) + "\n"
    if len(text.encode("utf-8")) > BYTECAP:
        raise InputError("rendered history exceeds the sensor's size cap")
    return text


def write(path: Path, text: str) -> None:
    """Replace ``path`` atomically: a reader sees the old file or the new one, never a partial."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--run",
        nargs=3,
        action="append",
        required=True,
        metavar=("RUNID", "SHA", "JUNIT"),
        help="one pytest JUnit XML file and the CI run and commit it came from (repeatable)",
    )
    parser.add_argument("--repository", help="owner/name the runs belong to (kept from the history when omitted)")
    parser.add_argument("--history", type=Path, default=OUTPUT, help="existing history to merge into")
    parser.add_argument("--output", type=Path, help="where to write (defaults to --history)")
    args = parser.parse_args(argv)
    target = args.output or args.history
    try:
        history = readHistory(args.history)
        incoming = [
            {"runId": runid, "sha": sha, "results": readJunit(Path(path))}
            for runid, sha, path in args.run
        ]
        document = build(history, incoming, repository=args.repository, collected=now())
        write(target, render(document))
    except (OSError, InputError) as exc:
        print(f"steward_collect_test_history: {exc}", file=sys.stderr)
        return 1
    total = sum(len(run["results"]) for run in document["runs"])
    print(f"wrote {len(document['runs'])} runs ({total} results) to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
