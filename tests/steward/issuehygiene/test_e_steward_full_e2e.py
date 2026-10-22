"""Lane E end-to-end: the ordinary ``gaia steward full run`` entrypoint, offline, on a fixture checkout.

What runs for real:
- ``gaia_cli.main.main`` with ``steward full run / record / run --resume`` (the /gaia-steward-full runner)
- the default sensor fleet, including the issue-hygiene sensor (routine 18)
- the census collector's writer (``scripts.steward_issue_census.writeAtomic``) and ``collectCensus``
- the closure script ``scripts/steward_issue_close.py``, performing each forge.close_issue action

What is fake: GitHub. ``FakeGitHub`` is seeded from the four-family census fixture and serves the
collector's REST shape; ``FakeForge`` performs the writes. Every socket and ``urlopen`` entry point
is refused, so any network use fails the test.

Two shapes are checked. With eligible closures at or under the per-run cap, the second run emits
nothing. With more eligible closures than the cap, the second run emits exactly the remainder and
the run after that emits nothing. Either way the closing comments and closes happen once per issue.
"""

from __future__ import annotations

import json
import socket
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pytest

import gaia_cli.steward.fullrun as fullrun
from gaia_cli.main import main as gaiaMain
from gaia_cli.steward.clock import utcNow
from gaia_cli.steward.controller import StewardController
from gaia_cli.steward.issuehygiene.identity import classify
from gaia_cli.steward.issuehygiene.registryindex import parseGithubUrl, splitId
from gaia_cli.steward.issuehygiene.sensor import CENSUS_INPUT, IssueHygieneSensor
from scripts.steward_issue_census import writeAtomic
from scripts.steward_issue_close import main as closeMain
from tests.steward.issuehygiene.e_fakes import FakeForge, FakeGitHub, REPO, loadFixture, makeCheckout, seedFromDocument

CLOSE = "forge.close_issue"
MARKER = "<!-- gaia-steward-closure:"


@pytest.fixture(autouse=True)
def refuseNetwork(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args, **kwargs):
        raise AssertionError("network use attempted by an offline steward test")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)
    monkeypatch.setattr(urllib.request, "urlopen", refuse)


def eligibleFromFixture(count: int) -> list[dict]:
    """Child intakes whose umbrella is open and whose suggested id and evidence URL parse cleanly."""

    document = loadFixture()
    openNumbers = {row["number"] for row in document["issues"] if row["state"] == "open"}
    picks: list[dict] = []
    seen: set[str] = set()
    for row in sorted(document["issues"], key=lambda item: item["number"]):
        if row.get("isPullRequest") or "upstream:child" not in row.get("labels", []):
            continue
        identity = classify(row)
        if identity.kind != "child" or identity.parent not in openNumbers:
            continue
        ref = parseGithubUrl(identity.evidenceUrl)
        if ref is None or splitId(identity.candidateId or "") is None or identity.candidateId in seen:
            continue
        seen.add(identity.candidateId)
        picks.append({"number": row["number"], "id": identity.candidateId, "url": ref.blobUrl()})
        if len(picks) == count:
            break
    return picks


def curatedRegistry(picks: list[dict]) -> dict[str, str]:
    named = {}
    for pick in picks:
        owner, slug = pick["id"].split("/")
        named[pick["id"]] = (
            f"---\nid: {pick['id']}\ncontributor: {owner}\nstatus: named\nlinks:\n  github: {pick['url']}\n---\n\n## Body\n"
        )
    return named


def safeName(text: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in text)


class Steward:
    """Stands in for the Claude driver: refreshes the census, runs the CLI, performs closures, records outcomes."""

    def __init__(self, root: Path, gh: FakeGitHub, forge: FakeForge, monkeypatch, capsys) -> None:
        self.root = root
        self.gh = gh
        self.forge = forge
        self.monkeypatch = monkeypatch
        self.capsys = capsys

    def census(self) -> None:
        writeAtomic(self.root / CENSUS_INPUT, self.gh.census(utcNow()))

    def gaia(self, *argv: str) -> tuple[int, dict | str]:
        self.monkeypatch.setattr(sys, "argv", ["gaia", "--registry", str(self.root), "steward", "full", *argv])
        code = 0
        try:
            gaiaMain()
        except SystemExit as exc:
            code = int(exc.code or 0)
        captured = self.capsys.readouterr()
        out = captured.out
        self.lastErr = captured.err
        try:
            return code, json.loads(out)
        except ValueError:
            return code, out

    def run(self) -> tuple[int, dict]:
        self.census()
        return self.gaia("run", "--ledger", "local", "--no-agents", "--json")

    def resume(self, runId: str) -> tuple[int, dict]:
        return self.gaia("run", "--resume", runId, "--ledger", "local", "--no-agents", "--json")

    def performClosures(self, view: dict) -> list[dict]:
        outcomes = []
        runId = view["runId"]
        for action in [a for a in view["actions"] if a["type"] == CLOSE]:
            stepId = action["stepId"]
            actionFile = self.root / ".gaia/steward/drive/closures" / f"{safeName(runId)}--{safeName(stepId)}.json"
            actionFile.parent.mkdir(parents=True, exist_ok=True)
            actionFile.write_text(json.dumps(action["params"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
            code = closeMain(["--root", str(self.root), "--action", str(actionFile), "--repo", REPO, "--run-id", runId],
                             forgeFactory=lambda repo, token: self.forge)
            outcome = json.loads(self.capsys.readouterr().out.strip().splitlines()[-1])
            assert code == 0 and outcome["outcome"] == "closed", outcome
            outcomeFile = self.root / ".gaia/steward/drive/outcomes" / f"{safeName(runId)}--{safeName(stepId)}.json"
            outcomeFile.parent.mkdir(parents=True, exist_ok=True)
            outcomeFile.write_text(json.dumps(outcome, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            recordCode, _ = self.gaia("record", runId, stepId, "--input", str(outcomeFile), "--ledger", "local", "--json")
            assert recordCode == 0, self.lastErr
            outcomes.append(outcome)
        return outcomes

    def receipts(self) -> list[dict]:
        found = []
        for path in sorted((self.root / ".gaia/steward/issue-hygiene/receipts").glob("*.jsonl")):
            found += [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return found


def closeActions(view: dict) -> list[dict]:
    return [action for action in view["actions"] if action["type"] == CLOSE]


def issueHygieneActions(view: dict) -> list[dict]:
    return [action for action in view["actions"]
            if action["type"] == CLOSE or str(action.get("debtId", "")).startswith("debt:issue_")]


def setUpSteward(tmp_path: Path, monkeypatch, capsys, eligibleCount: int) -> tuple[Steward, FakeGitHub, list[dict]]:
    """A fixture checkout, the census fixture as a fake GitHub, and only the issue-hygiene sensor.

    A bare fixture repository cannot satisfy the other sensors (about twenty report coverage unknown,
    which correctly blocks Class A), so the sensor set is narrowed through the same seam the CLI tests
    use. The CLI, the runner, the ledger, the closure script and ``record`` are all the real ones.
    """

    monkeypatch.setattr(fullrun, "StewardController", lambda: StewardController(sensors=(IssueHygieneSensor(),)))
    gh = FakeGitHub()
    seedFromDocument(gh, loadFixture())
    picks = eligibleFromFixture(eligibleCount)
    assert len(picks) == eligibleCount
    root = makeCheckout(tmp_path, named=curatedRegistry(picks))
    forge = FakeForge(gh)
    return Steward(root, gh, forge, monkeypatch, capsys), gh, picks


# The per-run cap is also an hourly budget (B7 L2): the remainder waits for the next UTC hour.
HOUR_ONE = "2026-10-21T19:30:00Z"
HOUR_TWO = "2026-10-21T20:30:00Z"


@pytest.mark.parametrize(("eligibleCount", "emissions", "instants"), [
    (10, [10, 0], [HOUR_ONE, HOUR_ONE]),    # everything fits under the cap: the second run emits nothing
    (12, [10, 0, 2, 0], [HOUR_ONE, HOUR_ONE, HOUR_TWO, HOUR_TWO]),  # cap 10 per hour: the remainder waits an hour
])
def test_ordinary_full_run_drains_issue_hygiene_offline_and_is_idempotent(
        tmp_path: Path, monkeypatch, capsys, eligibleCount: int, emissions: list[int], instants: list[str]) -> None:
    steward, gh, picks = setUpSteward(tmp_path, monkeypatch, capsys, eligibleCount)
    pickedNumbers = {pick["number"] for pick in picks}
    openBefore = sum(1 for number in pickedNumbers if gh.issues[number]["state"] == "open")
    assert openBefore == eligibleCount

    observed: list[int] = []
    for round_ in range(len(emissions)):
        monkeypatch.setenv("GAIA_STEWARD_NOW", instants[round_])
        writesBefore = len(forge_writes(steward))
        code, view = steward.run()
        assert code == 0, view
        closures = closeActions(view)
        observed.append(len(closures))
        assert len(closures) == emissions[round_], (round_, view.get("status"))
        assert issueHygieneActions(view) == closures  # nothing else from the issue sensor
        if closures:
            assert all(a["params"]["ruleId"] == "A1-child-curated" for a in closures)
            assert all(a["params"]["receiptPath"].endswith(f"{view['runId']}.jsonl") for a in closures)
            assert all("comment" not in a["params"] and "original" not in a["params"] for a in closures)  # compact (B7 D5)
            steward.performClosures(view)
            code, resumed = steward.resume(view["runId"])
            assert code == 0
            assert closeActions(resumed) == []  # the cap for that run is spent: nothing more from it
        else:
            assert len(forge_writes(steward)) == writesBefore  # zero comments, zero closes
    assert observed == emissions

    closedNumbers = sorted(pick["number"] for pick in picks)
    assert all(gh.issues[number]["state"] == "closed" for number in closedNumbers)
    assert all(len([c for c in gh.comments[number] if c["body"].startswith(MARKER)]) == 1 for number in closedNumbers)
    assert sorted(w[1] for w in forge_writes(steward) if w[0] == "close") == closedNumbers
    assert sum(1 for w in forge_writes(steward) if w[0] == "comment") == eligibleCount
    closedLines = [r for r in steward.receipts() if r["outcome"] == "closed"]
    assert sorted(r["issue"] for r in closedLines) == closedNumbers


def forge_writes(steward: Steward) -> list[tuple]:
    return steward.forge.writes


def test_the_first_run_emits_exactly_the_cap_and_the_rest_of_the_pending_work_is_not_lost(
        tmp_path: Path, monkeypatch, capsys) -> None:
    steward, gh, picks = setUpSteward(tmp_path, monkeypatch, capsys, 12)
    code, view = steward.run()
    assert code == 0 and view["status"] == "awaiting-action"
    assert len(closeActions(view)) == 10
    emitted = {a["params"]["issue"] for a in closeActions(view)}
    assert emitted <= {pick["number"] for pick in picks}
    steward.performClosures(view)
    code, resumed = steward.resume(view["runId"])
    assert len(closeActions(resumed)) == 0
    # The two deferred pairs are still eligible and are emitted once the hourly budget renews, not dropped.
    monkeypatch.setenv("GAIA_STEWARD_NOW", HOUR_TWO)
    code, nxt = steward.run()
    assert sorted(a["params"]["issue"] for a in closeActions(nxt)) == sorted(
        {pick["number"] for pick in picks} - emitted)


def test_a_driver_that_cannot_reach_the_forge_leaves_closures_pending_and_writes_nothing(
        tmp_path: Path, monkeypatch, capsys) -> None:
    steward, gh, picks = setUpSteward(tmp_path, monkeypatch, capsys, 3)
    code, view = steward.run()
    assert len(closeActions(view)) == 3
    assert steward.forge.writes == []
    assert all(gh.issues[pick["number"]]["state"] == "open" for pick in picks)
    code, again = steward.run()  # the pending run holds the lease; nothing is re-emitted
    assert again["status"] == "observing-existing"
    assert closeActions(again) == []
    assert steward.forge.writes == []


def test_with_the_full_default_fleet_closure_is_refused_and_nothing_is_written(tmp_path: Path, monkeypatch, capsys) -> None:
    """Without the narrowed sensor set, the other sensors cannot prove coverage on a bare fixture checkout.
    Another sensor's unknown coverage must block Class A closure at the CLI, not let it through."""

    gh = FakeGitHub()
    seedFromDocument(gh, loadFixture())
    picks = eligibleFromFixture(3)
    root = makeCheckout(tmp_path, named=curatedRegistry(picks))
    forge = FakeForge(gh)
    steward = Steward(root, gh, forge, monkeypatch, capsys)
    code, view = steward.run()
    assert code == 3 and view["status"] == "blocked"
    assert closeActions(view) == []
    assert view["coverageUnknown"]
    assert forge.writes == [] and all(gh.issues[pick["number"]]["state"] == "open" for pick in picks)
