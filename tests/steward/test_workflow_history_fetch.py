"""workflowproof fetch: the one deterministic way to produce a job's history rows file.

Decision steward-workflow-timeout-history-fetch-2283. Covers key -> display-name
mapping, a renamed job, empty history, API failure, the outside-checkout rule, the
mechanical provenance check, and verifier recompute parity (pinned refetch is
byte-identical and the recomputed value matches).
"""

from __future__ import annotations

import json
import shlex
import subprocess
from pathlib import Path
from typing import Any, Sequence

import pytest

from gaia_cli.steward import workflowhistory as wh
from gaia_cli.steward.models import AuthorityClass, DispatchPacket, RoutingBudget
from gaia_cli.steward.policy import StewardPolicy
from gaia_cli.steward.prompt import render_tree_keeper_prompt, render_verifier_prompt
from gaia_cli.steward.verification import (
    PROOF_TRANSCRIPT_SCHEMA,
    evaluate,
    parse_proof_transcript,
    parse_unified_diff,
    workflow_history_check,
)
from gaia_cli.steward.workflowproof import _main as proof_main
from gaia_cli.steward.workflowproof import build_parser

REPO_ROOT = Path(__file__).resolve().parents[2]
RULE = "workflow-timeout-repair"
WF = ".github/workflows/backfill.yml"

WORKFLOW = """name: Backfill
on: workflow_dispatch
jobs:
  backfill:
    name: Create releases for all tags missing one
    runs-on: ubuntu-latest
    steps:
      - run: echo hi
  plain:
    runs-on: ubuntu-latest
    steps:
      - run: echo hi
"""


def _row(name: str, conclusion: str, start: str, end: str) -> dict[str, Any]:
    return {"name": name, "conclusion": conclusion, "started_at": start, "completed_at": end, "id": 9, "steps": []}


class FakeGh:
    """Answers exactly the two GETs fetch makes; records every call."""

    def __init__(self, runs: list[tuple[int, int]], jobs: dict[int, list[dict[str, Any]]], *, total: dict[int, int] | None = None):
        self.runs, self.jobs, self.total, self.calls = runs, jobs, total or {}, []

    def __call__(self, args: Sequence[str]) -> str:
        self.calls.append(list(args))
        if args[0] == "run":
            assert "--status" in args and "completed" in args and "--limit" in args and "50" in args
            return json.dumps([{"databaseId": r, "attempt": a} for r, a in self.runs])
        assert args[0] == "api"
        run_id = int(args[1].split("/runs/")[1].split("/")[0])
        listed = self.jobs.get(run_id, [])
        return json.dumps({"total_count": self.total.get(run_id, len(listed)), "jobs": listed})


CURRENT = "Create releases for all tags missing one"
OLD = "Create missing tags and releases"


def _renamed_gh() -> FakeGh:
    return FakeGh(
        [(30, 1), (20, 2), (10, 1)],
        {
            30: [_row(CURRENT, "success", "2026-11-01T00:00:00Z", "2026-11-01T00:00:40Z"),
                 _row("plain", "success", "2026-11-01T00:00:00Z", "2026-11-01T00:00:05Z")],
            20: [_row(CURRENT, "success", "2026-10-01T00:00:00Z", "2026-10-01T00:01:00Z")],
            10: [_row(OLD, "success", "2026-09-01T00:00:00Z", "2026-09-01T00:30:00Z")],
        },
    )


@pytest.fixture()
def checkout(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / WF).write_text(WORKFLOW, encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    return root


def _fetch(checkout: Path, out: Path, gh: FakeGh, *extra: str, job: str = "backfill") -> int:
    args = build_parser().parse_args(["fetch", "--workflow", WF, "--job", job, "--out", str(out), *extra])
    return wh.fetch_main(args, cwd=checkout, gh=gh)


def _lines(text: str) -> dict[str, str]:
    return dict(line.split(": ", 1) for line in text.splitlines() if ": " in line)


# --- key -> display-name mapping ------------------------------------------------------


def test_key_maps_to_its_name_and_a_nameless_job_to_its_key() -> None:
    assert wh.resolve_job(WORKFLOW, "backfill") == ("backfill", (CURRENT,))
    assert wh.resolve_job(WORKFLOW, "plain") == ("plain", ("plain",))


def test_a_display_name_resolves_to_its_key() -> None:
    assert wh.resolve_job(WORKFLOW, CURRENT) == ("backfill", (CURRENT,))


def test_matrix_names_expand_per_leg() -> None:
    text = """jobs:
  py:
    name: Python SDK (Python ${{ matrix.python-version }})
    strategy:
      matrix:
        python-version: ['3.10', '3.12']
  node:
    strategy:
      matrix:
        node: [18, 20]
        os: [linux]
"""
    assert wh.resolve_job(text, "py")[1] == ("Python SDK (Python 3.10)", "Python SDK (Python 3.12)")
    assert wh.resolve_job(text, "node")[1] == ("node (18, linux)", "node (20, linux)")


@pytest.mark.parametrize(
    "job, why",
    [
        ("    name: Build ${{ github.ref }}\n", "expression"),
        ("    strategy:\n      matrix:\n        v: [1]\n        include: [{v: 2}]\n", "include/exclude"),
        ("    strategy:\n      matrix:\n        v: [3.10]\n", "ambiguous"),
        ("    strategy:\n      matrix: ${{ fromJSON(inputs.m) }}\n", "literal mapping"),
        ("    uses: ./.github/workflows/x.yml\n", "reusable-workflow call"),
    ],
)
def test_unresolvable_display_names_are_refused(job: str, why: str) -> None:
    with pytest.raises(wh.HistoryRefused, match=why):
        wh.resolve_job("jobs:\n  a:\n" + job + "    runs-on: x\n", "a")


def test_two_jobs_sharing_a_display_name_are_refused() -> None:
    text = "jobs:\n  a:\n    name: Same\n  b:\n    name: Same\n"
    with pytest.raises(wh.HistoryRefused, match="shares display name"):
        wh.resolve_job(text, "a")
    with pytest.raises(wh.HistoryRefused, match="matches 2"):
        wh.resolve_job(text, "Same")


# --- fetch ----------------------------------------------------------------------------


def test_a_renamed_job_yields_rows_for_its_current_display_name_only(checkout: Path, tmp_path: Path, capsys) -> None:
    out = tmp_path / "hist" / "backfill.json"
    assert _fetch(checkout, out, _renamed_gh()) == 0
    document = json.loads(out.read_text(encoding="utf-8"))
    assert {row["name"] for row in document["jobs"]} == {CURRENT}
    assert [row["runId"] for row in document["jobs"]] == [20, 30]  # canonical order, not API order
    assert document["runsWithoutJob"] == [10]
    assert document["runs"] == [{"id": 10, "attempt": 1}, {"id": 20, "attempt": 2}, {"id": 30, "attempt": 1}]
    printed = _lines(capsys.readouterr().out)
    assert printed["job-key"] == "backfill"
    assert printed["run-ids"] == "10:1,20:2,30:1"
    # The old name's 30-minute run never reaches the rule: max(2 x 60 s, 1.5 x 60 s) -> 5.
    assert proof_main(["history", "--history", str(out)]) == 0
    assert capsys.readouterr().out.strip().splitlines()[-1] == "5"


def test_fetch_reads_the_attempt_the_run_list_reported(checkout: Path, tmp_path: Path) -> None:
    gh = _renamed_gh()
    _fetch(checkout, tmp_path / "h.json", gh)
    assert ["api", "repos/gaia-research/gaia-skill-tree/actions/runs/20/attempts/2/jobs?per_page=100"] in gh.calls


def test_empty_history_stops_and_writes_nothing(checkout: Path, tmp_path: Path, capsys) -> None:
    out = tmp_path / "h.json"
    assert _fetch(checkout, out, FakeGh([], {})) == 3
    assert "no completed runs" in capsys.readouterr().out
    assert not out.exists()


def test_no_row_for_the_job_stops(checkout: Path, tmp_path: Path, capsys) -> None:
    gh = FakeGh([(1, 1)], {1: [_row(OLD, "success", "2026-09-01T00:00:00Z", "2026-09-01T00:01:00Z")]})
    out = tmp_path / "h.json"
    assert _fetch(checkout, out, gh) == 3
    assert "history cannot be read" in capsys.readouterr().out
    assert not out.exists()


def test_an_api_failure_stops_and_writes_nothing(checkout: Path, tmp_path: Path, monkeypatch, capsys) -> None:
    def failing(*_a, **_k):
        return subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="HTTP 502")

    real = subprocess.run
    monkeypatch.setattr(wh.subprocess, "run", lambda cmd, **k: failing() if cmd[0] == "gh" else real(cmd, **k))
    out = tmp_path / "h.json"
    args = build_parser().parse_args(["fetch", "--workflow", WF, "--job", "backfill", "--out", str(out)])
    assert wh.fetch_main(args, cwd=checkout) == 3
    assert "history unreadable" in capsys.readouterr().out
    assert not out.exists()


def test_a_truncated_jobs_page_is_not_a_sample(checkout: Path, tmp_path: Path) -> None:
    gh = _renamed_gh()
    gh.total[30] = 150
    assert _fetch(checkout, tmp_path / "h.json", gh) == 3


_VALID = _row(CURRENT, "success", "2026-11-01T00:00:00Z", "2026-11-01T00:00:40Z")


@pytest.mark.parametrize("rows, total", [
    pytest.param([_VALID, None], None, id="null-row"),
    pytest.param([_VALID, "job"], None, id="string-row"),
    pytest.param([_VALID, {k: v for k, v in _VALID.items() if k != "name"}], None, id="nameless-row"),
    pytest.param([_VALID, {**_VALID, "name": "  "}], None, id="blank-name"),
    pytest.param([_VALID, {**_VALID, "name": 7}], None, id="non-string-name"),
    pytest.param([{k: v for k, v in _VALID.items() if k != "conclusion"}], None, id="missing-conclusion"),
    pytest.param([{**_VALID, "started_at": 1700000000}], None, id="numeric-timestamp"),
    pytest.param([_VALID], -1, id="negative-total"),
    pytest.param([_VALID], True, id="bool-total"),
    pytest.param([_VALID], False, id="bool-false-total"),
    pytest.param([_VALID, _VALID], 1, id="total-below-rows"),
    pytest.param([_VALID], "1", id="string-total"),
])
def test_malformed_jobs_response_stops_and_writes_nothing(
    checkout: Path, tmp_path: Path, capsys, rows: list[Any], total: Any
) -> None:
    """One valid matching row never makes a sample out of a response with an unusable part."""
    gh = FakeGh([(30, 1)], {30: rows})
    if total is not None:
        gh.total[30] = total
    out = tmp_path / "h.json"
    assert _fetch(checkout, out, gh) == 3
    assert "history unreadable" in capsys.readouterr().out
    assert not out.exists()


def test_non_json_api_output_stops(checkout: Path, tmp_path: Path) -> None:
    assert _fetch(checkout, tmp_path / "h.json", lambda args: "<html>") == 3


def test_out_inside_the_checkout_is_refused(checkout: Path) -> None:
    out = checkout / ".gaia" / "steward" / "h.json"
    assert _fetch(checkout, out, _renamed_gh()) == 2
    assert not out.exists()


@pytest.mark.parametrize("workflow", [".github/workflows/x.lock.yml", ".github/workflows/shared/x.yml", "ci.yml"])
def test_only_direct_child_hand_written_workflows_are_fetched(checkout: Path, tmp_path: Path, workflow: str) -> None:
    args = build_parser().parse_args(["fetch", "--workflow", workflow, "--job", "a", "--out", str(tmp_path / "h.json")])
    assert wh.fetch_main(args, cwd=checkout, gh=_renamed_gh()) == 2


# --- verifier recompute parity --------------------------------------------------------


def test_pinned_refetch_is_byte_identical_even_after_new_runs(checkout: Path, tmp_path: Path, capsys) -> None:
    built = tmp_path / "build" / "backfill.json"
    assert _fetch(checkout, built, _renamed_gh()) == 0
    printed = _lines(capsys.readouterr().out)
    later = _renamed_gh()
    later.runs.insert(0, (40, 1))  # a newer completed run lands between build and verify
    later.jobs[40] = [_row(CURRENT, "success", "2026-11-07T00:00:00Z", "2026-11-07T02:00:00Z")]
    verified = tmp_path / "verify" / "backfill.json"
    code = _fetch(checkout, verified, later, "--run-ids", printed["run-ids"], "--expect-sha256", printed["sha256"])
    assert code == 0, capsys.readouterr().out
    assert verified.read_bytes() == built.read_bytes()
    assert not any(call[0] == "run" for call in later.calls)  # pinned: no run sampling


def test_changed_rows_fail_the_recompute(checkout: Path, tmp_path: Path, capsys) -> None:
    assert _fetch(checkout, tmp_path / "b.json", _renamed_gh()) == 0
    printed = _lines(capsys.readouterr().out)
    tampered = _renamed_gh()
    tampered.jobs[30][0]["completed_at"] = "2026-11-01T03:00:00Z"
    code = _fetch(checkout, tmp_path / "v.json", tampered, "--run-ids", printed["run-ids"], "--expect-sha256", printed["sha256"])
    assert code == 4
    assert "MISMATCH" in capsys.readouterr().out


def _packet(*, with_fetch: bool = True) -> DispatchPacket:
    rule = StewardPolicy.load(REPO_ROOT).dispatch_rules[RULE]
    commands = tuple(c for c in rule.allowed_commands if with_fetch or "workflowproof fetch" not in c)
    return DispatchPacket.create(
        debt={"id": "debt:workflow_hygiene:x", "kind": "workflow_hygiene", "subject": {"type": "workflow", "id": WF}},
        evidence={"observedState": {"findings": [{"rule": "missing-timeout", "detail": "job backfill has no timeout-minutes"}]},
                  "subject": {"type": "workflow", "id": WF}},
        authority=AuthorityClass.B, rule=rule.id, routine=rule.routine, objective=rule.objective,
        allowed_paths=rule.allowed_paths, allowed_commands=commands, forbidden_paths=rule.forbidden_paths,
        stop_conditions=rule.stop_conditions, proof=rule.proof,
        budget=RoutingBudget(model_calls=0, max_tokens=0, max_minutes=0), capability=rule.capability,
    )


def _builder_transcript(checkout: Path, out: Path, capsys) -> str:
    fetch_cmd = f"python -m gaia_cli.steward.workflowproof fetch --workflow {WF} --job backfill --out {out}"
    assert _fetch(checkout, out, _renamed_gh()) == 0
    fetch_out = capsys.readouterr().out
    history_cmd = f"python -m gaia_cli.steward.workflowproof history --history {out}"
    assert proof_main(shlex.split(history_cmd)[3:]) == 0
    history_out = capsys.readouterr().out
    entries = [{"contractIndex": i, "command": f"proof item {i}", "exitCode": 0, "output": "ok"} for i in (1, 3, 4, 5)]
    entries += [
        {"contractIndex": 2, "command": fetch_cmd, "exitCode": 0, "output": fetch_out},
        {"contractIndex": 2, "command": history_cmd, "exitCode": 0, "output": history_out},
    ]
    return json.dumps({"schemaVersion": PROOF_TRANSCRIPT_SCHEMA, "entries": entries})


DIFF = (
    f"diff --git a/{WF} b/{WF}\n--- a/{WF}\n+++ b/{WF}\n@@ -6,2 +6,3 @@\n"
    "     runs-on: ubuntu-latest\n+    timeout-minutes: 5\n     steps:\n"
)


def _evaluate(packet: DispatchPacket, text: str):
    return evaluate(
        packet=packet,
        change_set=parse_unified_diff(DIFF),
        transcript=parse_proof_transcript(text, proof_contract_length=len(packet.proof)),
        debt_source="ci-workflow", sensor_sources=["ci-workflow"], baseline_open_debt=[], current_open_debt=[],
        authority_still_class_b=True,
        workflow_baseline={WF: WORKFLOW},
        history_check=workflow_history_check(packet, text),
    )


class _Pending:
    decided = False

    def __init__(self, recompute=()):
        self.recompute = tuple(recompute)


def test_verifier_recompute_reproduces_the_builders_bytes_and_value(checkout: Path, tmp_path: Path, capsys, monkeypatch) -> None:
    built = tmp_path / "build" / "backfill.json"
    text = _builder_transcript(checkout, built, capsys)
    builder_value = json.loads(text)["entries"][-1]["output"].strip().splitlines()[-1]
    packet = _packet()
    verdict = _evaluate(packet, text)
    assert verdict.verdict == "pending", verdict.reasons
    commands = list(verdict.recompute)
    assert len(commands) == 2
    assert "--run-ids 10:1,20:2,30:1" in commands[0] and "--expect-sha256 " in commands[0]
    assert f"/{packet.dispatch_id}/verify/backfill.json" in commands[0]
    assert commands[1].startswith("python -m gaia_cli.steward.workflowproof history --history ")
    assert verdict.to_dict()["recompute"] == commands  # recorded with the machine verdict
    # Run them as the verifier would, with the shell's TMPDIR expansion done here.
    monkeypatch.setenv("TMPDIR", str(tmp_path / "vt"))
    expanded = [c.replace("${TMPDIR:-/tmp}", str(tmp_path / "vt")) for c in commands]
    later = _renamed_gh()
    later.runs.insert(0, (99, 1))
    args = build_parser().parse_args(shlex.split(expanded[0])[3:])
    assert wh.fetch_main(args, cwd=checkout, gh=later) == 0
    assert "recompute: byte-identical" in capsys.readouterr().out
    verified = Path(args.out)
    assert verified.read_bytes() == built.read_bytes()
    assert proof_main(shlex.split(expanded[1])[3:]) == 0
    assert capsys.readouterr().out.strip().splitlines()[-1] == builder_value


def test_verifier_prompt_lists_the_recompute_from_the_verdict(checkout: Path, tmp_path: Path, capsys) -> None:
    text = _builder_transcript(checkout, tmp_path / "b.json", capsys)
    packet = _packet()
    verdict = _evaluate(packet, text)
    prompt = render_verifier_prompt(packet, verdict, prompt_guide="g", diff_text="", proof_outputs={})
    assert "## Recompute the inputs yourself (required)" in prompt
    assert verdict.recompute[0] in prompt


def test_the_prompt_refuses_a_fetch_era_verdict_without_recompute() -> None:
    with pytest.raises(ValueError, match="no recompute commands"):
        render_verifier_prompt(_packet(), _Pending(), prompt_guide="g", diff_text="", proof_outputs={})
    old = _packet(with_fetch=False)
    assert "Recompute the inputs" not in render_verifier_prompt(old, _Pending(), prompt_guide="g", diff_text="", proof_outputs={})


# --- mechanical provenance check ------------------------------------------------------


def test_a_fetched_history_satisfies_the_provenance_check(checkout: Path, tmp_path: Path, capsys) -> None:
    text = _builder_transcript(checkout, tmp_path / "b.json", capsys)
    problems, commands = workflow_history_check(_packet(), text)
    assert problems == [] and len(commands) == 2


def _mutated(text: str, change) -> str:
    data = json.loads(text)
    change(data["entries"])
    return json.dumps(data)


def _drop_line(prefix):
    def change(entries):
        entries[-2]["output"] = "\n".join(l for l in entries[-2]["output"].splitlines() if not l.startswith(prefix))
    return change


@pytest.mark.parametrize(
    "change, why",
    [
        (lambda e: e.pop(-2), "no successful workflowproof fetch entry"),
        (lambda e: e[-1].update(command=e[-1]["command"].replace("--history ", "--history /tmp/hand-made-")),
         "was not produced by a workflowproof fetch entry"),
        (lambda e: e.pop(-1), "no history or no-history entry reads"),
        (lambda e: e[-2].update(output="ok"), "lacks exactly one"),
        (lambda e: e[-2].update(command=e[-2]["command"].replace(WF, ".github/workflows/other.yml")), "not the command's"),
        # Review r2397 P1-a: every metadata field is required; none may be omitted.
        (_drop_line("workflow: "), "lacks exactly one workflow"),
        (_drop_line("job-key: "), "lacks exactly one job-key"),
        (_drop_line("sha256: "), "lacks exactly one sha256"),
        (_drop_line("run-ids: "), "lacks exactly one run-ids"),
        (lambda e: e[-2].update(output=e[-2]["output"] + "sha256: " + "b" * 64 + "\n"), "lacks exactly one sha256"),
        (lambda e: e.insert(-1, dict(e[-2])), "2 fetch entries; exactly one is allowed"),
        # Review r2397 note 3: labels are counted before values are validated.
        (lambda e: e[-2].update(output=e[-2]["output"] + "sha256: " + "B" * 64 + "\n"), "lacks exactly one sha256"),
        (lambda e: e[-2].update(output=e[-2]["output"] + "sha256: " + "b" * 63 + "\n"), "lacks exactly one sha256"),
        (lambda e: e[-2].update(output=e[-2]["output"] + "run-ids: invalid\n"), "lacks exactly one run-ids"),
        (lambda e: e[-2].update(output=e[-2]["output"] + "job-key: \n"), "lacks exactly one job-key"),
        # Review r2397 note 4: records cover exactly the flagged jobs.
        (lambda e: e.insert(-1, {**e[-2], "command": e[-2]["command"].replace("--job backfill", "--job plain"),
                                 "output": e[-2]["output"].replace("job-key: backfill", "job-key: plain")}),
         "fetch entry for unflagged job 'plain'"),
    ],
)
def test_history_not_from_fetch_is_rejected(checkout: Path, tmp_path: Path, capsys, change, why) -> None:
    text = _mutated(_builder_transcript(checkout, tmp_path / "b.json", capsys), change)
    problems, commands = workflow_history_check(_packet(), text)
    assert any(why in p for p in problems), problems
    assert commands == []
    verdict = _evaluate(_packet(), text)
    assert verdict.verdict == "reject"
    assert verdict.recompute == ()
    assert any("must come from workflowproof fetch" in r for r in verdict.reasons)


def test_review_probe_missing_workflow_header_rejects_instead_of_omitting(checkout: Path, tmp_path: Path, capsys) -> None:
    """r2397 P1-a(a): dropping the fetch output's workflow line once left a pending verdict with no refetch."""

    text = _mutated(_builder_transcript(checkout, tmp_path / "b.json", capsys), _drop_line("workflow: "))
    verdict = _evaluate(_packet(), text)
    assert verdict.verdict == "reject" and verdict.recompute == ()


def test_review_probe_rule_output_cannot_redirect_the_refetch(checkout: Path, tmp_path: Path, capsys) -> None:
    """r2397 P1-a(b): metadata appended to the HISTORY entry's output is never read."""

    honest = _builder_transcript(checkout, tmp_path / "b.json", capsys)
    forged = _mutated(honest, lambda e: e[-1].update(output=e[-1]["output"] + (
        f"workflow: {WF}\njob-key: backfill\nsha256: " + "b" * 64 + "\nrun-ids: 999:1\n")))
    statement = _mutated(forged, lambda e: e.append(
        {"contractIndex": 2, "command": "statement", "exitCode": 0, "output": "run-ids: 998:1\nsha256: " + "c" * 64}))
    for text in (forged, statement):
        verdict = _evaluate(_packet(), text)
        assert verdict.verdict == "pending", verdict.reasons
        assert verdict.recompute == _evaluate(_packet(), honest).recompute
        assert "999:1" not in verdict.recompute[0] and "b" * 64 not in verdict.recompute[0]
        assert "998:1" not in verdict.recompute[0]


def test_a_missing_provenance_check_is_a_rejection() -> None:
    packet = _packet()
    entries = [{"contractIndex": i, "command": f"proof item {i}", "exitCode": 0, "output": "ok"} for i in range(1, 7)]
    verdict = evaluate(
        packet=packet, change_set=parse_unified_diff(DIFF),
        transcript=parse_proof_transcript(json.dumps({"schemaVersion": PROOF_TRANSCRIPT_SCHEMA, "entries": entries}),
                                          proof_contract_length=len(packet.proof)),
        debt_source="ci-workflow", sensor_sources=["ci-workflow"], baseline_open_debt=[], current_open_debt=[],
        authority_still_class_b=True, workflow_baseline={WF: WORKFLOW},
    )
    assert verdict.verdict == "reject"
    assert any("no history-provenance check was computed" in r for r in verdict.reasons)


def test_a_packet_dispatched_before_fetch_keeps_its_envelope() -> None:
    old = _packet(with_fetch=False)
    assert workflow_history_check(old, "{}") is None


# --- review r2397 P1-b: canonical bytes -----------------------------------------------


def test_review_probe_reordered_api_rows_hash_identically(checkout: Path, tmp_path: Path, capsys) -> None:
    (checkout / WF).write_text("jobs:\n  backfill:\n    strategy:\n      matrix:\n        os: [linux, macos]\n", encoding="utf-8")
    rows = [_row("backfill (linux)", "success", "2026-11-01T00:00:00Z", "2026-11-01T00:00:40Z"),
            _row("backfill (macos)", "success", "2026-11-01T00:00:00Z", "2026-11-01T00:01:00Z")]
    assert _fetch(checkout, tmp_path / "a.json", FakeGh([(30, 1), (20, 1)], {30: rows, 20: rows})) == 0
    first = _lines(capsys.readouterr().out)
    reordered = FakeGh([(20, 1), (30, 1)], {30: list(reversed(rows)), 20: list(reversed(rows))})
    code = _fetch(checkout, tmp_path / "b.json", reordered, "--run-ids", "20:1,30:1", "--expect-sha256", first["sha256"])
    assert code == 0, capsys.readouterr().out
    assert (tmp_path / "a.json").read_bytes() == (tmp_path / "b.json").read_bytes()
    unpinned = FakeGh([(20, 1), (30, 1)], {30: list(reversed(rows)), 20: rows})
    assert _fetch(checkout, tmp_path / "c.json", unpinned) == 0
    assert _lines(capsys.readouterr().out)["sha256"] == first["sha256"]


# --- the packet itself ----------------------------------------------------------------


def test_a_freshly_rendered_packet_grants_fetch_and_names_the_location() -> None:
    packet = _packet()
    prompt = render_tree_keeper_prompt(packet, prompt_guide="founder/steward/routines/workflow-timeout.md")
    assert "python -m gaia_cli.steward.workflowproof fetch --workflow <workflow-file> --job <job-key> --out <history-dir>/<job-key>.json" in prompt
    assert "--history <history-dir>/<job-key>.json" in prompt
    assert "${TMPDIR:-/tmp}/gaia-steward-history/<dispatch-id>/build, outside the repository checkout" in prompt
    # The write envelope is unchanged: still exactly the direct-child workflow files.
    assert packet.allowed_paths == (".github/workflows/*.yml",)
    assert ".gaia/steward/**" in packet.forbidden_paths


def test_the_route_decision_stays_open_until_independent_acceptance() -> None:
    """r2397 P1-2: R4 is standing authority, not acceptance; the record must not close itself."""
    from gaia_cli.steward.desk import _check_record, _records_to_desk

    name = "steward-workflow-timeout-history-fetch-2283"
    record = json.loads((REPO_ROOT / "founder/steward/decisions" / f"{name}.json").read_text(encoding="utf-8"))
    record["_source"] = f"founder/steward/decisions/{name}.json"
    assert _check_record(record) is None
    assert record["status"] == "open" and "resolution" not in record
    awaiting: list[Any] = []
    pending, invalid = _records_to_desk([record], awaiting)
    assert [d.decision_id for d in pending] == [name] and awaiting == [] and invalid == []
