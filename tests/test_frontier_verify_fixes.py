"""Regression tests for the Frontier tooling defects found by the independent Meta verifier (EPIC #2189)."""
import copy
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from gaia_cli import frontier
from gaia_cli.frontier import (append_event, build_experiment_receipt, check_timestamps, receipt_digest, validate_events, validate_experiment_receipt,
                               validate_lead_timestamps, validate_meta_verification, validate_triage_record)
from test_frontier_meta_verification import ART, REPO, VERIFIER_RUN, case, check, rerunTrace, run_cli, sha, verifierNative  # noqa: F401  (case is a fixture)
from test_frontier_protocol import committedBundle


# ---- 1. rerun provenance replaces the byte-identical copy check -------------------------------

def identicalTarget(root, art):
    raw = (root / art / "target.txt").read_bytes()
    (root / art / "verifier-target.txt").write_bytes(raw)
    return {"label": "target", "contentDigest": sha(raw), "path": f"{art}/verifier-target.txt", "trace": rerunTrace(root, art, "verifier-target.stdout", raw)}


def identicalNative(root, art, **trace):
    """A byte-identical native artifact; its trace commits the receipt output text as the raw stdout stream."""
    raw = (root / art / "native.json").read_bytes()
    (root / art / "verifier-native.json").write_bytes(raw)
    stdout = json.loads(raw)["output"].encode()
    return {"label": "native", "contentDigest": sha(raw), "path": f"{art}/verifier-native.json", "trace": rerunTrace(root, art, "verifier-native.stdout", stdout, **trace)}


@pytest.fixture
def noNormalization(monkeypatch):
    """A deterministic protocol: the pinned declaration declares no run-varying content to normalize."""
    real = frontier.pinned_declaration
    monkeypatch.setattr(frontier, "pinned_declaration", lambda *a, **k: {**real(*a, **k), "outputNormalization": []})


def test_byte_identical_rerun_with_a_backed_trace_is_accepted_for_a_deterministic_protocol(case, noNormalization):
    root, _, _, rec = case
    rec = copy.deepcopy(rec)
    rec["reexecution"]["artifacts"][0] = identicalNative(root, ART)
    rec["reexecution"]["artifacts"][1] = identicalTarget(root, ART)
    assert check(case, rec) == []


def test_byte_identical_rerun_is_refused_even_with_a_trace_when_the_protocol_normalizes_run_varying_content(case):
    root, _, _, rec = case
    rec = copy.deepcopy(rec)
    rec["reexecution"]["artifacts"][0] = identicalNative(root, ART)
    assert any("byte-identical" in e for e in check(case, rec))


def test_dummy_trace_on_a_byte_copy_cannot_record_a_positive(case, noNormalization):
    """P1 regression: a copied native.json plus a made-up trace (argv ['true']) used to validate as substantiated."""
    root, _, _, rec = case
    rec = copy.deepcopy(rec)
    raw = (root / ART / "native.json").read_bytes()
    (root / ART / "verifier-native.json").write_bytes(raw)
    rec["reexecution"]["artifacts"][0] = {"label": "native", "contentDigest": sha(raw), "path": f"{ART}/verifier-native.json", "trace": rerunTrace(argv=["true"])}
    assert any("requires stdoutPath" in e for e in check(case, rec))
    # ... and the same copy with a stdout file that merely hashes correctly but is not the receipt output
    rec["reexecution"]["artifacts"][0]["trace"] = rerunTrace(root, ART, "fake.stdout", b"made up", argv=["true"])
    assert any("stdout for native differs from the receipt's native output" in e for e in check(case, rec))


def test_non_positive_outcome_remains_possible_for_an_unbacked_identical_rerun(case, noNormalization):
    root, _, _, rec = case
    rec = copy.deepcopy(rec)
    rec["reexecution"]["artifacts"][0] = identicalNative(root, ART)
    del rec["reexecution"]["artifacts"][0]["trace"]["stdoutPath"]
    rec.update(outcome="inconclusive", recommend={"action": "hold", "rationale": "Identical rerun without committed stdout evidence."})
    assert check(case, rec) == []


@pytest.mark.parametrize("mutate,needle", [
    (lambda t, root: t.update(stdoutDigest=sha(b"other")), "does not match the sha256"),
    (lambda t, root: t.update(stdoutPath="registry/nodes/x.stdout"), "stdout artifact"),
    (lambda t, root: t.update(stdoutPath=t["stdoutPath"] + ".missing"), "not found"),
    (lambda t, root: t.update(toolVersions={"git": "9.9.9"}), "differs from the receipt's executed version"),
    (lambda t, root: t.update(toolVersions={"other-tool": "2.56.0"}), "no toolVersions entry"),
])
def test_positive_trace_must_be_backed_by_stdout_evidence_and_the_executed_version(case, mutate, needle):
    root, _, _, rec = case
    rec = copy.deepcopy(rec)
    mutate(rec["reexecution"]["artifacts"][0]["trace"], root)
    assert any(needle in e for e in check(case, rec))


def test_trace_stdout_artifact_cannot_reuse_a_receipt_output(case):
    root, _, receipt, rec = case
    rec = copy.deepcopy(rec)
    rec["reexecution"]["artifacts"][1]["trace"].update(stdoutPath=receipt["outputs"][1]["path"], stdoutDigest=receipt["outputs"][1]["contentDigest"])
    assert any("reuses a receipt output path" in e for e in check(case, rec))

def test_byte_identical_artifact_without_a_trace_is_still_indistinguishable_from_a_copy(case):
    root, _, _, rec = case
    rec = copy.deepcopy(rec)
    rec["reexecution"]["artifacts"][0] = identicalNative(root, ART)
    del rec["reexecution"]["artifacts"][0]["trace"]
    errors = check(case, rec)
    assert any("byte-identical" in e for e in errors) and any("requires a rerun trace" in e for e in errors)


def test_reformatted_copy_without_a_trace_no_longer_passes(case):
    root, _, _, rec = case
    rec = copy.deepcopy(rec)
    native = json.loads((root / ART / "native.json").read_text())
    raw = (json.dumps(native, indent=4) + "\n").encode()  # same content, new bytes
    (root / ART / "verifier-native.json").write_bytes(raw)
    rec["reexecution"]["artifacts"][0] = {"label": "native", "contentDigest": sha(raw), "path": f"{ART}/verifier-native.json"}
    assert any("requires a rerun trace" in e for e in check(case, rec))


def test_identical_bytes_are_only_explained_for_the_matching_label(case, noNormalization):
    root, _, _, rec = case
    rec = copy.deepcopy(rec)
    raw = (root / ART / "target.txt").read_bytes()
    rec["reexecution"]["artifacts"][0] = identicalNative(root, ART)
    rec["reexecution"]["artifacts"][1] = identicalTarget(root, ART)
    assert check(case, rec) == []
    # a native artifact that is byte-identical to the receipt's *target* output is a copy, trace or not
    (root / ART / "verifier-native.json").write_bytes(raw)
    rec["reexecution"]["artifacts"][0] = {"label": "native", "contentDigest": sha(raw), "path": f"{ART}/verifier-native.json", "trace": rerunTrace(root, ART, "n.stdout", raw)}
    assert any("byte-identical" in e for e in check(case, rec))

def test_traced_rerun_output_must_equal_the_receipt_output_after_normalization(case):
    root, _, _, rec = case
    rec = copy.deepcopy(rec)
    (root / ART / "verifier-target.txt").write_bytes(b"a different target output\n")
    rec["reexecution"]["artifacts"][1]["contentDigest"] = sha(b"a different target output\n")
    assert any("target output differs from the receipt's target output" in e for e in check(case, rec))


@pytest.mark.parametrize("patch,needle", [
    ({"finishedAtUTC": "2026-10-28T01:29:00Z"}, "finishes before it starts"),
    ({"startedAtUTC": "2026-10-28T00:00:00Z", "finishedAtUTC": "2026-10-28T00:00:05Z"}, "starts before the receipt"),
    ({"startedAtUTC": "2026-10-28T05:00:00Z", "finishedAtUTC": "2026-10-28T05:00:05Z"}, "finishes after the verification record"),
])
def test_trace_times_must_be_plausible(case, patch, needle):
    rec = copy.deepcopy(case[3])
    rec["reexecution"]["artifacts"][0]["trace"].update(patch)
    assert any(needle in e for e in check(case, rec))


@pytest.mark.parametrize("drop", ["argv", "toolVersions", "startedAtUTC", "finishedAtUTC", "stdoutDigest", "stderrDigest"])
def test_trace_schema_requires_every_provenance_field(case, drop):
    rec = copy.deepcopy(case[3])
    del rec["reexecution"]["artifacts"][0]["trace"][drop]
    assert any(drop in e for e in check(case, rec))


def test_trace_digests_must_be_sha256_and_argv_non_empty(case):
    rec = copy.deepcopy(case[3])
    rec["reexecution"]["artifacts"][0]["trace"].update(stdoutDigest="md5:abc", argv=[])
    assert len(check(case, rec)) >= 2


def test_positive_outcome_without_traces_is_refused(case):
    rec = copy.deepcopy(case[3])
    for item in rec["reexecution"]["artifacts"]:
        del item["trace"]
    assert sum("requires a rerun trace" in e for e in check(case)) == 0  # fixture itself is traced
    assert sum("requires a rerun trace" in e for e in check(case, rec)) == 2


def test_schema_states_the_trace_is_declared_not_authenticated():
    schema = json.loads(frontier.META_VERIFICATION_SCHEMA.read_text())
    Draft202012Validator.check_schema(schema)
    trace = schema["properties"]["reexecution"]["properties"]["artifacts"]["items"]["properties"]["trace"]
    assert "DECLARED, NOT AUTHENTICATED" in trace["description"] and "never authentication" in trace["description"]
    assert "never authenticate" in " ".join(frontier.validate_meta_verification.__doc__.split())


def test_legacy_record_without_traces_still_validates_when_not_positive(case):
    """Backward compatibility: pre-trace records keep validating unless they claim a positive outcome."""
    rec = copy.deepcopy(case[3])
    rec.update(outcome="contradicted", recommend={"action": "hold", "rationale": "Legacy record written before rerun traces."})
    (case[0] / ART / "verifier-target.txt").write_bytes(b"legacy verifier output that differs\n")
    rec["reexecution"]["artifacts"][1]["contentDigest"] = sha(b"legacy verifier output that differs\n")
    for item in rec["reexecution"]["artifacts"]:
        del item["trace"]
    assert check(case, rec) == []


# ---- 2. receipts bind raw-stream trace artifacts -----------------------------------------------

def traceReceipt(tmp_path, **kwargs):
    root, request, art = committedBundle(tmp_path)
    (root / art / "native-trace.json").write_text(json.dumps({"argv": ["x"], "stdoutDigest": sha(b"o")}))
    receipt = build_experiment_receipt(root=root, request=request, protocol=request["protocol"]["path"], execution_path=f"{art}/native.json",
                                       target_path=f"{art}/target.txt", result="supported", artifact_root=art,
                                       trace_paths=[("native-trace", f"{art}/native-trace.json")], **kwargs)
    return root, request, art, receipt


def test_receipt_binds_the_trace_digest_and_revalidates(tmp_path):
    root, request, art, receipt = traceReceipt(tmp_path)
    assert receipt["traces"] == [{"label": "native-trace", "contentDigest": sha((root / art / "native-trace.json").read_bytes()), "path": f"{art}/native-trace.json"}]
    assert validate_experiment_receipt(receipt, request, repo_root=root, artifact_root=art) == []
    assert "traces" in json.loads(frontier.EXPERIMENT_SCHEMA_V11.read_text())["properties"]
    (root / art / "native-trace.json").write_text("{}")
    assert any("trace artifact digest mismatch" in e for e in validate_experiment_receipt(receipt, request, repo_root=root, artifact_root=art))
    assert any("trace artifacts require local integrity" in e for e in validate_experiment_receipt(receipt, request))


def test_receipt_without_traces_is_unchanged(tmp_path):
    root, request, art = committedBundle(tmp_path)
    receipt = build_experiment_receipt(root=root, request=request, protocol=request["protocol"]["path"], execution_path=f"{art}/native.json", result="inconclusive", artifact_root=art)
    assert "traces" not in receipt


def test_trace_must_be_confined_non_empty_and_not_an_alias(tmp_path):
    root, request, art = committedBundle(tmp_path)
    (root / art / "empty").write_text("  ")
    common = dict(root=root, request=request, protocol=request["protocol"]["path"], execution_path=f"{art}/native.json", result="inconclusive", artifact_root=art)
    with pytest.raises(ValueError, match="empty"):
        build_experiment_receipt(**common, trace_paths=[("t", f"{art}/empty")])
    with pytest.raises(ValueError):
        build_experiment_receipt(**common, trace_paths=[("t", "registry/nodes/x.json")])
    with pytest.raises(ValueError, match="aliases another artifact"):
        build_experiment_receipt(**common, trace_paths=[("t", f"{art}/native.json")])  # aliases the native output


# ---- 3. timestamp sanity -----------------------------------------------------------------------

def gitRepo(tmp_path, committed_at):
    repo = tmp_path / "repo"
    repo.mkdir()
    env = {**os.environ, "GIT_AUTHOR_DATE": committed_at, "GIT_COMMITTER_DATE": committed_at, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}
    run = lambda *a: subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.org", "-c", "commit.gpgsign=false", *a], check=True, env=env, capture_output=True)
    run("init", "-q")
    (repo / "record.json").write_text("{}")
    run("add", "record.json")
    run("commit", "-q", "-m", "x")
    return repo


def test_future_timestamps_are_rejected_without_git():
    now = datetime(2026, 10, 29, 12, 0, tzinfo=timezone.utc)
    errors = check_timestamps({"a": "2026-10-29T12:01:00Z", "b": "2026-10-29T20:00:00Z"}, now=now)
    assert errors == ["timestamp is in the future: b 2026-10-29T20:00:00Z"]  # within 120s skew passes


def test_local_time_mislabelled_z_is_caught_against_the_committing_commit(tmp_path):
    repo = gitRepo(tmp_path, "2026-10-28T10:00:00+00:00")
    later = datetime(2026, 11, 30, tzinfo=timezone.utc)
    ok = check_timestamps({"t": "2026-10-28T09:59:00Z"}, repo_root=repo, committed_path=repo / "record.json", now=later)
    assert ok == []
    bad = check_timestamps({"t": "2026-10-28T18:00:00Z"}, repo_root=repo, committed_path=repo / "record.json", now=later)  # 18:00 local +08 labelled Z
    assert len(bad) == 1 and "later than the committing commit" in bad[0]


def test_no_git_or_uncommitted_file_is_warn_only(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / "record.json").write_text("{}")
    warnings: list[str] = []
    assert check_timestamps({"t": "2026-10-28T18:00:00Z"}, repo_root=plain, committed_path=plain / "record.json", warnings=warnings) == []
    assert any("no git checkout" in w for w in warnings)
    repo = gitRepo(tmp_path, "2026-10-28T10:00:00+00:00")
    (repo / "record.json").write_text('{"edited": true}')
    warnings = []
    assert check_timestamps({"t": "2026-10-28T18:00:00Z"}, repo_root=repo, committed_path=repo / "record.json", warnings=warnings) == []
    assert any("uncommitted" in w for w in warnings)


def test_lead_timestamps_are_checked_in_a_git_context(tmp_path):
    repo = gitRepo(tmp_path, "2026-10-28T10:00:00+00:00")
    lead = {"source": {"observedAtUTC": "2026-10-28T18:20:00Z"}, "dedupe": {"checkedAtUTC": "2026-10-28T09:00:00Z"}}
    errors = validate_lead_timestamps(lead, repo_root=repo, lead_path=repo / "record.json")
    assert len(errors) == 1 and "source.observedAtUTC" in errors[0]
    future = {"source": {"observedAtUTC": "2999-01-01T00:00:00Z"}}
    assert any("in the future" in e for e in validate_lead_timestamps(future))
    assert validate_lead_timestamps("not a lead") == []


def test_meta_validate_rejects_a_future_record_timestamp(case):
    rec = copy.deepcopy(case[3])
    rec["recordedAtUTC"] = "2999-01-01T00:00:00Z"
    assert any("timestamp is in the future: recordedAtUTC" in e for e in check(case, rec))


def test_cli_lead_validate_and_meta_validate_report_warnings(case, tmp_path, capsys):
    code, out = run_cli(["--registry", str(REPO), "dev", "frontier", "lead-validate", "--lead", str(REPO / "examples/frontier/git-log-L-graft.challenger-lead-v1.json"), "--repo-root", str(REPO)], capsys)
    result = json.loads(out.out)
    assert code in (0, None) and result["valid"] is True
    lead = json.loads((REPO / "examples/frontier/git-log-L-graft.challenger-lead-v1.json").read_text())
    lead["source"]["observedAtUTC"] = "2999-01-01T00:00:00Z"
    path = tmp_path / "lead.json"
    path.write_text(json.dumps(lead))
    code, out = run_cli(["--registry", str(REPO), "dev", "frontier", "lead-validate", "--lead", str(path), "--repo-root", str(REPO)], capsys)
    assert code == 1 and any("in the future" in e for e in json.loads(out.out)["errors"])
    root, req, receipt, rec = case
    files = {}
    for name, value in (("record", rec), ("receipt", receipt), ("request", req)):
        files[name] = tmp_path / f"{name}.json"
        files[name].write_text(json.dumps(value))
    code, out = run_cli(["--registry", str(root / "registry"), "dev", "frontier", "meta-validate", "--record", str(files["record"]), "--receipt", str(files["receipt"]),
                         "--request", str(files["request"]), "--repo-root", str(root), "--artifact-root", ART], capsys)
    result = json.loads(out.out)
    assert code in (0, None) and result["structurallyValid"] is True and any("not checked against a committing commit" in w for w in result["warnings"])


# ---- 4. events helper --------------------------------------------------------------------------

def test_append_event_chains_entries_and_validates(tmp_path):
    t0 = datetime(2026, 10, 29, 1, 0, 0, tzinfo=timezone.utc)
    first = append_event(tmp_path, "lead-written", "lead committed", now=t0)
    second = append_event(tmp_path, "runner-started", "runner started", extra={"artifact": "artifacts/native.json"}, now=t0 + timedelta(minutes=3))
    assert first["seq"] == 1 and first["prevHash"] is None and second["seq"] == 2 and second["artifact"] == "artifacts/native.json"
    lines = (tmp_path / "events.jsonl").read_bytes().splitlines(keepends=True)
    assert second["prevHash"] == "sha256:" + hashlib.sha256(lines[0].rstrip(b"\n")).hexdigest()
    errors, warnings = validate_events(tmp_path / "events.jsonl", now=t0 + timedelta(hours=1))
    assert errors == [] and warnings == []


def test_event_chain_detects_edits_deletions_and_reordering(tmp_path):
    t0 = datetime(2026, 10, 29, 1, 0, 0, tzinfo=timezone.utc)
    for i in range(3):
        append_event(tmp_path, "step", f"step {i}", now=t0 + timedelta(minutes=i))
    path = tmp_path / "events.jsonl"
    original = path.read_bytes().splitlines(keepends=True)
    now = t0 + timedelta(hours=1)
    path.write_bytes(original[0].replace(b"step 0", b"STEP 0") + b"".join(original[1:]))
    assert any("prevHash" in e for e in validate_events(path, now=now)[0])
    path.write_bytes(original[0] + original[2])
    assert any("seq" in e or "prevHash" in e for e in validate_events(path, now=now)[0])
    path.write_bytes(original[0] + original[2] + original[1])
    assert validate_events(path, now=now)[0]


def test_append_event_extends_a_legacy_unchained_log(tmp_path):
    legacy = tmp_path / "events.jsonl"
    legacy.write_text(json.dumps({"atUTC": "2026-10-28T18:22:57Z", "event": "lead-written"}) + "\n")
    entry = append_event(tmp_path, "results", "later", now=datetime(2026, 10, 29, tzinfo=timezone.utc))
    assert entry["seq"] == 2 and entry["prevHash"].startswith("sha256:")
    assert validate_events(legacy, now=datetime(2026, 10, 30, tzinfo=timezone.utc)) == ([], [])  # chained tail, so no unchained warning


def test_append_event_refuses_symlinks_and_damaged_logs(tmp_path):
    target = tmp_path / "elsewhere.jsonl"
    target.write_text("")
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    (case_dir / "events.jsonl").symlink_to(target)
    with pytest.raises(ValueError, match="symlink"):
        append_event(case_dir, "step", "should not write")
    assert target.read_text() == ""
    alias = tmp_path / "alias"
    alias.symlink_to(case_dir, target_is_directory=True)
    with pytest.raises(ValueError, match="symlinks are refused"):
        append_event(alias, "step", "x")
    damaged = tmp_path / "damaged"
    damaged.mkdir()
    (damaged / "events.jsonl").write_text('{"event": "a", "atUTC": "2026-10-28T00:00:00Z"}')  # no trailing newline
    with pytest.raises(ValueError, match="newline"):
        append_event(damaged, "step", "x")


@pytest.mark.parametrize("kind,note,extra", [("Bad Type", "x", None), ("a", "x", None), ("ok-type", "  ", None), ("ok-type", "x", {"seq": 9}), ("ok-type", "x", {"k": [1]}), ("ok-type", "x", {"bad key": "v"})])
def test_append_event_validates_inputs(tmp_path, kind, note, extra):
    with pytest.raises(ValueError):
        append_event(tmp_path, kind, note, extra=extra)
    assert not (tmp_path / "events.jsonl").exists() or (tmp_path / "events.jsonl").read_text() == ""


def test_batch_written_log_with_one_timestamp_warns(tmp_path):
    stamp = "2026-10-28T18:22:57Z"
    path = tmp_path / "events.jsonl"
    path.write_text("".join(json.dumps({"atUTC": stamp, "event": name}) + "\n" for name in ("lead-written", "frontier-match", "frontier-dedupe")))
    errors, warnings = validate_events(path, now=datetime(2026, 10, 30, tzinfo=timezone.utc))
    assert errors == [] and any("share one timestamp" in w for w in warnings)
    path.write_text(json.dumps({"atUTC": stamp, "event": "only"}) + "\n")
    assert not any("share one timestamp" in w for w in validate_events(path, now=datetime(2026, 10, 30, tzinfo=timezone.utc))[1])


def test_events_validation_flags_backwards_and_future_times(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_text(json.dumps({"atUTC": "2026-10-28T10:00:00Z", "event": "a"}) + "\n" + json.dumps({"atUTC": "2026-10-28T09:00:00Z", "event": "b"}) + "\n" + json.dumps({"atUTC": "2999-01-01T00:00:00Z", "event": "c"}) + "\n")
    errors, _ = validate_events(path)
    assert any("backwards" in e for e in errors) and any("future" in e for e in errors)


def test_cli_event_appends_and_events_validate_reports(tmp_path, capsys):
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    code, out = run_cli(["dev", "frontier", "event", str(case_dir), "--type", "runner-started", "--note", "started", "--field", "artifact=artifacts/native.json"], capsys)
    assert code in (0, None) and json.loads(out.out)["seq"] == 1
    run_cli(["dev", "frontier", "event", str(case_dir), "--type", "runner-finished", "--note", "done"], capsys)
    code, out = run_cli(["dev", "frontier", "events-validate", str(case_dir)], capsys)
    result = json.loads(out.out)
    assert code in (0, None) and result["valid"] is True
    code, out = run_cli(["dev", "frontier", "event", str(case_dir), "--type", "x", "--note", "y"], capsys)
    assert code == 1 and "refused" in out.err


# ---- 5. triage-stage review of a lead rejected before any receipt ------------------------------

LEAD = REPO / "examples/frontier/git-log-L-graft.challenger-lead-v1.json"


@pytest.fixture
def triage(tmp_path):
    lead = json.loads(LEAD.read_text())
    match, dedupe = b'{"candidates": []}\n', b'{"isDuplicate": true}\n'
    record = {
        "schemaVersion": "frontier-meta-verification-v1.1", "stage": "triage", "verificationId": "meta-triage-c4-2026-10-29",
        "campaignId": "yggiv-challenger-cases-2026-10", "verifierRunId": "meta-run-" + "2" * 32,
        "leadDigest": frontier._sha(frontier._canonical(lead)), "matchDigest": sha(match), "dedupeDigest": sha(dedupe),
        "outcome": "rejected_at_triage",
        "recommend": {"action": "reject-lead", "rationale": "Synthetic: duplicate of a committed lead, no request was ever built."},
        "counterevidence": {"searched": "Synthetic: re-ran match and dedupe against the ledger.", "items": []},
        "independence": "declared-unauthenticated", "limitations": ["Synthetic triage record; nothing was executed."],
        "recordedAtUTC": "2026-10-28T02:00:00Z",
    }
    return record, lead, match, dedupe


def test_triage_record_without_receipt_validates(triage):
    record, lead, match, dedupe = triage
    Draft202012Validator.check_schema(json.loads(frontier.META_VERIFICATION_SCHEMA.read_text()))
    assert validate_triage_record(record, lead, match, dedupe) == []


@pytest.mark.parametrize("drop", ["leadDigest", "matchDigest", "dedupeDigest"])
def test_triage_record_requires_its_three_digests(triage, drop):
    record, lead, match, dedupe = triage
    del record[drop]
    assert any(drop in e for e in validate_triage_record(record, lead, match, dedupe))


def test_triage_record_is_bound_to_the_exact_lead_and_outputs(triage):
    record, lead, match, dedupe = triage
    changed = copy.deepcopy(lead)
    changed["capability"]["task"] += " edited"
    assert "lead binding mismatch: leadDigest" in validate_triage_record(record, changed, match, dedupe)
    assert "match output binding mismatch: matchDigest" in validate_triage_record(record, lead, match + b" ", dedupe)
    assert "dedupe output binding mismatch: dedupeDigest" in validate_triage_record(record, lead, match, dedupe + b" ")


def test_triage_record_cannot_carry_receipt_fields_or_positive_outcomes(triage):
    record, lead, match, dedupe = triage
    for extra in ({"requestId": "sha256:" + "a" * 64}, {"receiptDigest": "sha256:" + "a" * 64}, {"receiptRunId": "run-12345678"}, {"reexecution": {"performed": False, "artifacts": []}}):
        assert validate_triage_record({**record, **extra}, lead, match, dedupe)
    for outcome in ("substantiated", "narrowed", "contradicted"):
        assert validate_triage_record({**record, "outcome": outcome}, lead, match, dedupe)
    admission = copy.deepcopy(record)
    admission["recommend"]["action"] = "request-admission-review"
    assert validate_triage_record(admission, lead, match, dedupe)
    assert validate_triage_record({**record, "approved": True}, lead, match, dedupe)


def test_verification_stage_cannot_use_triage_outcomes_or_fields(case):
    rec = copy.deepcopy(case[3])
    assert check(case, {**rec, "outcome": "rejected_at_triage", "recommend": {"action": "hold", "rationale": "Synthetic hold rationale."}})
    assert check(case, {**rec, "leadDigest": "sha256:" + "a" * 64})


def test_triage_record_is_refused_by_the_receipt_validator(case, triage):
    record = triage[0]
    assert any("triage-stage record has no receipt" in e for e in validate_meta_verification(record, case[2], case[1]))


def test_cli_meta_validate_handles_triage_records(triage, tmp_path, capsys):
    record, lead, match, dedupe = triage
    paths = {}
    for name, value in (("record", json.dumps(record).encode()), ("lead", json.dumps(lead).encode()), ("match", match), ("dedupe", dedupe)):
        paths[name] = tmp_path / f"{name}.json"
        paths[name].write_bytes(value)
    base = ["--registry", str(REPO), "dev", "frontier", "meta-validate", "--record", str(paths["record"]), "--repo-root", str(REPO)]
    code, out = run_cli([*base, "--lead", str(paths["lead"]), "--match", str(paths["match"]), "--dedupe", str(paths["dedupe"])], capsys)
    assert code in (0, None) and json.loads(out.out)["structurallyValid"] is True
    code, out = run_cli(base, capsys)  # missing --lead/--match/--dedupe
    assert code == 1 and "--lead" in out.err


def test_skill_documents_rerun_traces_events_and_triage_and_mirrors_match():
    claude = (REPO / ".claude/skills/gaia-frontier/SKILL.md").read_bytes()
    assert claude == (REPO / ".agents/skills/gaia-frontier/SKILL.md").read_bytes()
    text = claude.decode().casefold()
    for needle in ("rerun trace", "gaia dev frontier event", "stage", "triage", "declared, not authenticated", "events-validate"):
        assert needle in text


# ---- review hold repairs ------------------------------------------------------------------------

@pytest.mark.parametrize("bad", ["2026-10-28T10:00:00", "2026-10-28T10:00:00z", "2026-10-28T18:00:00+08:00", "yesterday", "2026-10-28", 12345])
def test_malformed_timestamps_are_errors_not_silent_skips(bad):
    assert any("malformed UTC timestamp" in e for e in check_timestamps({"t": bad}))
    assert any("malformed UTC timestamp" in e for e in validate_lead_timestamps({"source": {"observedAtUTC": bad}, "dedupe": {"checkedAtUTC": "2026-10-28T10:00:00Z"}}))


@pytest.mark.parametrize("good", ["2026-10-28T10:00:00Z", "2026-10-28T10:00:00+00:00", "2026-10-28T10:00:00.250Z"])
def test_strict_utc_forms_are_accepted(good):
    assert check_timestamps({"t": good}, now=datetime(2026, 11, 1, tzinfo=timezone.utc)) == []


def test_malformed_record_and_trace_timestamps_are_errors(case):
    rec = copy.deepcopy(case[3])
    rec["recordedAtUTC"] = "2026-10-28T02:00:00z"
    rec["reexecution"]["artifacts"][0]["trace"]["startedAtUTC"] = "2026-10-28T01:30:00"
    errors = check(case, rec)
    assert sum("malformed UTC timestamp" in e for e in errors) >= 2


def test_append_event_does_not_need_pread_or_forget_binary_mode(tmp_path, monkeypatch):
    import inspect
    monkeypatch.delattr(os, "pread", raising=False)  # Windows has no os.pread
    append_event(tmp_path, "step", "one")
    assert append_event(tmp_path, "step", "two")["seq"] == 2
    assert "O_BINARY" in inspect.getsource(append_event)


def test_events_without_any_chained_entry_warn(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_text(json.dumps({"atUTC": "2026-10-28T10:00:00Z", "event": "a"}) + "\n" + json.dumps({"atUTC": "2026-10-28T11:00:00Z", "event": "b"}) + "\n")
    errors, warnings = validate_events(path, now=datetime(2026, 11, 1, tzinfo=timezone.utc))
    assert errors == [] and any("no chained entries" in w for w in warnings)
    doc = " ".join((append_event.__doc__ + validate_events.__doc__).split())
    assert "truncating the tail" in doc and "Git history is the anchor" in doc


def test_shallow_clone_makes_the_commit_time_check_inconclusive(tmp_path):
    repo = gitRepo(tmp_path, "2026-10-28T10:00:00+00:00")
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", "-q", "--depth", "1", f"file://{repo}", str(clone)], check=True, capture_output=True)
    warnings: list[str] = []
    errors = check_timestamps({"t": "2026-10-28T09:00:00Z"}, repo_root=clone, committed_path=clone / "record.json", now=datetime(2026, 11, 1, tzinfo=timezone.utc), warnings=warnings)
    assert errors == [] and any("shallow" in w and "inconclusive" in w for w in warnings)
    assert "shallow" in frontier.committer_time.__doc__ and "lenient" in " ".join(frontier.check_timestamps.__doc__.split())


def test_duplicate_trace_labels_on_a_receipt_are_rejected(tmp_path):
    root, request, art = committedBundle(tmp_path)
    (root / art / "t1.json").write_text("{}")
    (root / art / "t2.json").write_text('{"a": 1}')
    with pytest.raises(ValueError, match="duplicate trace label"):
        build_experiment_receipt(root=root, request=request, protocol=request["protocol"]["path"], execution_path=f"{art}/native.json", result="inconclusive",
                                 artifact_root=art, trace_paths=[("same", f"{art}/t1.json"), ("same", f"{art}/t2.json")])


def test_append_event_rejects_non_finite_floats(tmp_path):
    for value in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError, match="invalid extra event field"):
            append_event(tmp_path, "step", "x", extra={"score": value})
    assert append_event(tmp_path, "step", "x", extra={"score": 0.5})["score"] == 0.5


def test_missing_or_directory_trace_path_is_a_clean_value_error(tmp_path, capsys):
    root, request, art = committedBundle(tmp_path)
    (root / art / "adir").mkdir()
    common = dict(root=root, request=request, protocol=request["protocol"]["path"], execution_path=f"{art}/native.json", result="inconclusive", artifact_root=art)
    for path in (f"{art}/missing.json", f"{art}/adir"):
        with pytest.raises(ValueError, match="missing or not a readable file"):
            build_experiment_receipt(**common, trace_paths=[("t", path)])
    sys.path.insert(0, str(REPO / "examples/frontier"))
    import record_experiment
    with pytest.raises(ValueError, match="LABEL=PATH"):
        record_experiment.parse_traces(["no-equals"])
    assert record_experiment.parse_traces(["a=b/c"]) == [("a", "b/c")]


def test_schema_version_gates_the_new_shape(case):
    Draft202012Validator.check_schema(json.loads(frontier.META_VERIFICATION_SCHEMA.read_text()))
    old = copy.deepcopy(case[3])
    old["schemaVersion"] = "frontier-meta-verification-v1"
    assert any("require schemaVersion frontier-meta-verification-v1.1" in e for e in check(case, old))  # positive + traces
    old.update(outcome="inconclusive", recommend={"action": "hold", "rationale": "Legacy-shaped record."}, reexecution={"performed": False, "artifacts": []})
    assert check(case, old) == []  # the original v1 shape still validates
    assert check(case, {**old, "schemaVersion": "frontier-meta-verification-v2"})


def test_triage_record_must_declare_v11(triage):
    record, lead, match, dedupe = triage
    assert validate_triage_record({**record, "schemaVersion": "frontier-meta-verification-v1"}, lead, match, dedupe)
