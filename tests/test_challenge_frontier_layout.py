"""The challenge projection reads the canonical Frontier bundle layout (regression for the four real C1-C4 cases)."""
import io
import json
import shutil
from contextlib import redirect_stderr
from pathlib import Path

import pytest

from challenge_case_support import CASE, makeCase
from gaia_cli import challengeAdmission as admission
from gaia_cli import challengeProjection as projection
from gaia_cli.committedChallenges import collect, lifecyclePorts, reviewsBySubject

TRIAGE = Path(__file__).resolve().parent / "fixtures" / "frontier-triage-case"


def relocate(directory):
    """Move receipt.json to the layout the landed Frontier receipt builder writes."""
    target = Path(directory) / admission.RECEIPTPATH
    target.parent.mkdir(exist_ok=True)
    (Path(directory) / "receipt.json").rename(target)
    return target


def triageRoot(tmp_path, caseId="c4-triage-fixture"):
    root = tmp_path / "triage-root"
    shutil.copytree(TRIAGE, root / admission.EVIDENCE / caseId)
    return root, root / admission.EVIDENCE / caseId


def test_canonical_receipt_path_is_read(tmp_path):
    root, directory = makeCase(tmp_path)
    relocate(directory)
    report = admission.inspectBundle(root, CASE)
    assert report.ok, report.errors
    found = collect(root)
    assert not found.rejected and [r["status"] for r in found.reviews] == ["admission-held"]
    assert found.admitted == {} and lifecyclePorts(found) is None


def test_legacy_receipt_path_is_still_accepted(tmp_path):
    root, _ = makeCase(tmp_path)
    assert admission.inspectBundle(root, CASE).ok


def test_both_receipt_locations_are_ambiguous_and_rejected(tmp_path):
    root, directory = makeCase(tmp_path)
    target = relocate(directory)
    (directory / "receipt.json").write_bytes(target.read_bytes())
    found = collect(root)
    assert found.reviews == () and "ambiguous receipt" in found.rejected[0]["reason"]


def test_uppercase_case_ids_are_accepted_but_traversal_is_not(tmp_path):
    for good in ("c3-git-log-L-vs-graft", "C3", "a" * 63):
        assert admission.CASEIDRE.fullmatch(good)
    for bad in ("", ".hidden", "..", "a/b", "a\\b", "a..b", "a.b", "-lead", "a b", "a" * 64, "a:b", "../x"):
        assert not admission.CASEIDRE.fullmatch(bad), bad
    root, directory = makeCase(tmp_path, "C3-Git-Log-L-Vs-Graft")
    relocate(directory)
    found = collect(root)
    assert not found.rejected and found.reviews[0]["caseId"] == "C3-Git-Log-L-Vs-Graft"


def test_dot_leading_and_separator_directories_are_listed_as_rejected(tmp_path):
    root, _ = makeCase(tmp_path)
    (root / admission.EVIDENCE / "bad.name").mkdir()
    found = collect(root)
    assert [r["caseId"] for r in found.rejected] == ["bad.name"] and len(found.reviews) == 1


def test_triage_case_projects_as_a_neutral_review_with_no_numbers(tmp_path):
    root, _ = triageRoot(tmp_path)
    found = collect(root)
    assert not found.rejected and found.admitted == {} and lifecyclePorts(found) is None
    [review] = found.reviews
    assert review["status"] == "rejected-at-triage" and "held" not in review and "experiment" not in review
    text = json.dumps(review)
    assert "contested" not in text.lower() and "request" not in review
    document = projection.buildReviews(root, collected=found)
    assert projection.validateReviews(document) == [] and document["reviews"] == [review]
    assert set(reviewsBySubject(found)) == {review["subjectId"]}
    assert projection.buildIndex(root, collected=found) == projection.emptyIndex()


def test_triage_case_can_never_be_admitted(tmp_path):
    root, _ = triageRoot(tmp_path)
    report = admission.inspectBundle(root, "c4-triage-fixture")
    assert report.ok and report.triage
    with pytest.raises(admission.AdmissionError):
        admission.attemptAdmission(report, root)


def test_tampered_triage_bundle_is_rejected(tmp_path):
    root, directory = triageRoot(tmp_path)
    (directory / "artifacts" / "match.json").write_text("{}\n", encoding="utf-8")
    found = collect(root)
    assert found.reviews == () and "match output binding mismatch" in found.rejected[0]["reason"]


def test_triage_case_with_an_issuer_receipt_directory_is_rejected(tmp_path):
    root, directory = triageRoot(tmp_path)
    (directory / "receipt").mkdir()
    assert collect(root).rejected


def test_triage_review_cannot_carry_held_or_contested_labels():
    base = {"contract": "gaia-challenge-review/v1", "status": "rejected-at-triage", "triage": {"explanation": "x"}}
    assert projection.validateReview(base) == []
    assert projection.validateReview({**base, "held": {"reason": "trusted-issuer-unavailable"}})
    assert projection.validateReview({**base, "triage": {"explanation": "contested"}})
    assert projection.validateReview({**base, "tm": 3})


def test_sync_surfaces_every_rejected_bundle_as_a_warning(tmp_path):
    root, _ = makeCase(tmp_path)
    (root / admission.EVIDENCE / "bad.name").mkdir()
    err = io.StringIO()
    with redirect_stderr(err):
        projection.sync(root, check=False)
    assert "warning: challenge bundle bad.name rejected:" in err.getvalue()


# --- event log reconciliation with frontier.validate_events -------------------------------

LEGACY = {"atUTC": "2026-10-28T18:22:57Z", "event": "lead-written", "leadId": "synthetic-lead-0001"}


def c1ShapedLog(directory, *, erratums=2):
    """One legacy unchained line followed by chained ``erratum`` lines written by the Frontier event tool."""
    from gaia_cli import frontier
    (Path(directory) / "events.jsonl").write_text(json.dumps(LEGACY) + "\n", encoding="utf-8")
    for number in range(erratums):
        frontier.append_event(directory, "erratum", f"synthetic correction {number}")
    return Path(directory) / "events.jsonl"


def test_legacy_lines_before_a_chain_are_tolerated_like_frontier_validate_events(tmp_path):
    from gaia_cli import frontier
    root, directory = makeCase(tmp_path)
    log = c1ShapedLog(directory)
    assert frontier.validate_events(log)[0] == []
    assert admission.readEvents(log)[1] == []
    assert admission.inspectBundle(root, CASE).eventErrors == []


def test_chained_log_that_breaks_or_gaps_is_still_broken(tmp_path):
    _, directory = makeCase(tmp_path)
    log = c1ShapedLog(directory, erratums=3)
    lines = log.read_bytes().splitlines(keepends=True)
    log.write_bytes(b"".join(lines[:2] + lines[3:]))  # delete a middle line: seq gap + hash break
    assert admission.readEvents(log)[1]
    log.write_bytes(b"".join(lines) + json.dumps(LEGACY).encode() + b"\n")  # unchained line after the chain started
    assert admission.readEvents(log)[1]
    edited = lines[:]
    edited[1] = edited[1].replace(b"synthetic correction 0", b"edited")
    log.write_bytes(b"".join(edited))
    assert admission.readEvents(log)[1]


def test_own_events_append_after_legacy_and_tool_chained_lines(tmp_path):
    _, directory = makeCase(tmp_path)
    log = c1ShapedLog(directory)
    event = admission.appendEvent(directory, "note", {})
    assert event["seq"] == 4 and admission.readEvents(log)[1] == []


def test_meta_not_recommended_is_the_hold_reason_and_is_neutral(tmp_path):
    root, directory = makeCase(tmp_path, positive=False)  # Meta record recommends "hold"
    c1ShapedLog(directory)
    found = collect(root)
    [review] = found.reviews
    assert not found.rejected and review["held"]["reason"] == "meta-not-recommended"
    assert "contested" not in json.dumps(review).lower()
    assert projection.validateReviews({"contract": "gaia-challenge-review/v1", "reviews": [review]}) == []


def test_meta_verdict_takes_precedence_over_a_broken_log_and_a_missing_request(tmp_path):
    root, directory = makeCase(tmp_path, positive=False)
    (directory / "events.jsonl").write_text("not json\n", encoding="utf-8")
    [review] = collect(root).reviews
    assert review["held"]["reason"] == "meta-not-recommended"


# --- independent review hardening ------------------------------------------------------------

def test_symlinked_receipts_directory_is_refused_before_any_read(tmp_path):
    root, directory = makeCase(tmp_path)
    target = relocate(directory)
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    shutil.move(str(target.parent), str(outside / "receipts"))
    (directory / "receipts").symlink_to(outside / "receipts", target_is_directory=True)
    report = admission.inspectBundle(root, CASE)
    assert not report.ok and any("symlink" in e for e in report.errors)
    found = collect(root)
    assert found.reviews == () and "symlink" in found.rejected[0]["reason"]


def test_symlinked_legacy_receipt_is_refused(tmp_path):
    root, directory = makeCase(tmp_path)
    real = tmp_path / "real-receipt.json"
    shutil.move(str(directory / "receipt.json"), str(real))
    (directory / "receipt.json").symlink_to(real)
    assert "symlink" in collect(root).rejected[0]["reason"]


def test_symlinked_receipts_cannot_make_a_case_look_triage_only(tmp_path):
    root, directory = triageRoot(tmp_path)
    (directory / "receipts").symlink_to(tmp_path)
    assert not admission.isTriageBundle(directory)


def triageWithOutcome(tmp_path, outcome):
    root, directory = triageRoot(tmp_path)
    path = directory / "meta-verification.json"
    record = json.loads(path.read_text())
    record["outcome"] = outcome
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return root


def test_triage_status_follows_the_meta_outcome(tmp_path):
    [rejected] = collect(triageWithOutcome(tmp_path / "a", "rejected_at_triage")).reviews
    assert rejected["status"] == "rejected-at-triage" and "rejected at triage" in rejected["triage"]["explanation"]
    found = collect(triageWithOutcome(tmp_path / "b", "deferred_at_triage"))
    [deferred] = found.reviews
    assert deferred["status"] == "deferred-at-triage" and "no effect on standing" in deferred["triage"]["explanation"]
    assert "no effect on standing" in deferred["disclosure"] and "rejected" not in json.dumps(deferred).lower()
    assert projection.validateReviews({"contract": "gaia-challenge-review/v1", "reviews": [deferred]}) == []


def test_list_cases_rejects_casefold_sets(tmp_path):
    from types import SimpleNamespace
    from gaia_cli.committedChallenges import listCases
    class Entry(SimpleNamespace):
        def __lt__(self, other):
            return self.name < other.name
    entries = [Entry(name=name, is_symlink=lambda: False, is_file=lambda: False, is_dir=lambda: True)
               for name in ("Case-A", "case-a", "other")]
    base = SimpleNamespace(iterdir=lambda: iter(entries))
    names, rejected = listCases(base)
    assert names == ["other"] and sorted(r["caseId"] for r in rejected) == ["Case-A", "case-a"]
    assert all("letter case" in r["reason"] for r in rejected)


def test_collisions_casefold_challenge_and_receipt_ids():
    from types import SimpleNamespace
    from gaia_cli.committedChallenges import rejectCollisions
    reports = {"x": SimpleNamespace(challengeId="Chal-1", receiptId="X-r1"),
               "y": SimpleNamespace(challengeId="chal-1", receiptId="y-r1")}
    assert set(rejectCollisions(reports)) == {"x", "y"}


def test_printed_rejection_reasons_are_cleaned(tmp_path):
    root, directory = makeCase(tmp_path)
    (directory / "lead.json").write_text('{"x": "::error::pwned\\u001b[31m"}\n', encoding="utf-8")
    err = io.StringIO()
    with redirect_stderr(err):
        projection.sync(root, check=False)
    text = err.getvalue()
    assert "::" not in text.replace(": :", "") and "\x1b" not in text


def test_masked_broken_event_log_is_still_warned(tmp_path):
    root, directory = makeCase(tmp_path, positive=False)
    (directory / "events.jsonl").write_text("not json\n", encoding="utf-8")
    err = io.StringIO()
    with redirect_stderr(err):
        [review] = collect(root).reviews
    assert review["held"]["reason"] == "meta-not-recommended" and "event log is broken" in err.getvalue()
