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
