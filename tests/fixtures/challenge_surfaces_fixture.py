"""Visibly SYNTHETIC challenge-surface documents for tests and local visual evidence.

Not published anywhere: nothing under ``docs/`` may carry these (see
``test_no_synthetic_data_under_docs``). The admitted subjects are the real
``produce_lifecycle`` output from ``lifecycle_dto_test_ports`` (disposable
in-process ports); the held reviews follow ``committedChallenges.reviewOf``.

    python3 tests/fixtures/challenge_surfaces_fixture.py [subjectId ...]

prints ``{"index": gaia-challenge-projection/v1, "reviews": gaia-challenge-review/v1}``.
The first three subject ids stand for a material challenge, a scoped challenge and a
resolved challenge (default: placeholders). Rewriting ``subjectId`` leaves each
challenge id unchanged, which the browser module does not re-derive.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lifecycle_dto_test_ports import make  # noqa: E402

DEFAULT = ("skill/material-example", "skill/scoped-example", "skill/resolved-example")


def retarget(dto, subject):
    old = dto["subjectId"]
    dto = json.loads(json.dumps(dto))
    dto["subjectId"] = subject
    for challenge in dto["challenges"]:
        if challenge["subjectId"] == old:
            challenge["subjectId"] = subject
    return dto


def subjects(ids=DEFAULT):
    built = [make(True, kind="approved-decision"),
             make(False, kind="current-baseline"),
             make(True, True, "approved-decision", True)]
    out = []
    for entry, subject in zip(built, ids):
        dto = retarget(entry["trustLifecycle"], subject)
        # Distinct challenge ids per subject (the three fixtures share one synthetic context).
        for challenge in dto["challenges"]:
            challenge["challengeId"] = f"{subject.replace('/', '-')}-{challenge['challengeId'][:12]}"
            for event in challenge["history"]:
                event["challenge_id"] = challenge["challengeId"]
        out.append({"subjectId": dto["subjectId"], "genericSkillRef": dto["genericSkillRef"],
                    "materialOriginContested": dto["materialOriginContested"],
                    "consequence": dto["consequence"], "challenges": dto["challenges"]})
    return out


def index(ids=DEFAULT, status="verified"):
    return {"contract": "gaia-challenge-projection/v1", "sourceStatus": status,
            "subjects": subjects(ids) if status == "verified" else []}


def review(caseId="synthetic-review-0001", subject="skill/held-example", reason="trusted-issuer-unavailable",
           outcome="substantiated", action="request-admission-review"):
    return {
        "contract": "gaia-challenge-review/v1", "caseId": caseId, "status": "admission-held",
        "subjectId": subject, "subjectKind": "named", "genericSkillRef": "synthetic-bucket",
        "leadId": "synthetic-lead-0001", "claimId": "synthetic-claim-0001",
        "claim": "Challenger tool finds callers of five pinned functions with higher recall than the incumbent.",
        "challenger": {"name": "Synthetic Challenger", "version": "0.0.1", "sourceUrl": "https://example.org/synthetic-challenger"},
        "comparator": "Incumbent skill at its pinned commit",
        "protocolDigest": "sha256:" + "0" * 64, "requestId": "synthetic-request-0001",
        "experiment": {"result": "supported", "documentedVersion": "0.0.1", "executedVersion": "0.0.1"},
        "assessment": {"outcome": outcome, "suggestedAction": action, "independence": "declared-unauthenticated"},
        "held": {"reason": reason, "explanation": "The trusted receipt issuer produced no verifiable receipt for this review."},
        "bundleDigest": "sha256:" + "1" * 64,
        "disclosure": ("Review record only. An admission was attempted and held, so this is not an admitted Gaia challenge "
                       "and it changes no Trust Magnitude, star, grade, Origin or ranking."),
    }


def triageReview(caseId="synthetic-review-0003", subject="skill/triage-example", status="rejected-at-triage"):
    """A lead that never reached admission: a triage note, no held reason, no experiment."""
    record = review(caseId, subject, outcome="rejected_at_triage", action="no-action")
    for key in ("held", "experiment", "protocolDigest", "requestId"):
        del record[key]
    deferred = status == "deferred-at-triage"
    record["status"] = status
    record["assessment"]["outcome"] = "deferred_at_triage" if deferred else "rejected_at_triage"
    record["triage"] = {"explanation": ("The lead was deferred at triage, with no effect on standing; no experiment was run." if deferred
                                        else "The lead was rejected at triage, before any experiment was preregistered or run.")}
    record["disclosure"] = ("Review record only. This lead was " + ("deferred" if deferred else "rejected") +
                            " at triage: no experiment was run and no admission was attempted, so this is not an admitted Gaia challenge "
                            "and it changes no Trust Magnitude, star, grade, Origin or ranking.")
    return record


def reviews(records=None):
    held2 = review("synthetic-review-0002", "skill/other-held-example", "meta-not-recommended", "contradicted", "no-action")
    held2["held"]["explanation"] = "The independent assessment of this review does not recommend an admission review."
    return {"contract": "gaia-challenge-review/v1",
            "reviews": records if records is not None else [review(), held2, triageReview(),
                                                            triageReview("synthetic-review-0004", "skill/deferred-example", "deferred-at-triage")]}


if __name__ == "__main__":
    given = tuple(sys.argv[1:4])
    ids = given + DEFAULT[len(given):]
    print(json.dumps({"index": index(ids), "reviews": reviews()}))
