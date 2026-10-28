"""Read-side ports over committed Frontier case bundles (build time, fail closed per item).

Every docs build re-validates each ``evidence/frontier-challenges/<case>/`` bundle and
re-attempts admission through the production offline resolver
(``CommittedAttestedReceiptSource``). Nothing recorded in a bundle (including
``events.jsonl``) is trusted as an admitted state:

* a case whose issuer receipt verifies becomes an admitted ``Challenge`` and feeds the
  ``trustLifecycle`` channel through ``LifecyclePorts``;
* every other valid case becomes a ``gaia-challenge-review/v1`` record for the separate
  ``challengeReviews`` channel (a held review is never labelled as contested);
* a bundle that fails re-validation is rejected: it appears nowhere public.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping

from . import challengeAdmission as admission
from .challengeDomain import Challenge
from .lifecycleProjection import LifecyclePorts

REVIEWCONTRACT = "gaia-challenge-review/v1"
DISCLOSURE = ("Review record only. An admission was attempted and held, so this is not an admitted Gaia challenge "
              "and it changes no Trust Magnitude, star, grade, Origin or ranking.")
HELDTEXT = {
    "trusted-issuer-unavailable": "The trusted receipt issuer produced no verifiable receipt for this review.",
    "trusted-issuer-misconfigured": "The trusted receipt issuer configuration is not usable in this build.",
    "receipt-unverifiable": "A receipt exists but could not be verified.",
    "challenge-rejected": "The challenge domain rejected the admission request.",
    "admission-request-missing": "No admission request has been prepared for this review.",
    "not-recommended-for-admission": "The independent assessment does not recommend an admission review.",
}
VERIFIABLE = ("offline-only", "available")


def defaultProbe(root: Path) -> dict[str, Any]:
    from .steward.challenge_receipts import probe_trusted_receipt_source
    return probe_trusted_receipt_source(repoRoot=root)


@dataclass(frozen=True)
class Collected:
    ledgerPresent: bool
    issuerVerifiable: bool
    issuerStatus: str
    admitted: Mapping[str, tuple[Challenge, ...]]
    genericRefs: Mapping[str, str]
    reviews: tuple[dict[str, Any], ...]
    rejected: tuple[dict[str, str], ...]
    resolver: Any = field(default=None, compare=False)

    @property
    def sourceStatus(self) -> str:
        """unavailable | verified-empty | verified (a pure function of committed bytes and pins)."""
        if not self.ledgerPresent or not self.issuerVerifiable:
            return "unavailable"
        return "verified" if self.admitted else "verified-empty"


def reviewOf(report: admission.BundleReport, outcome: admission.AdmissionOutcome) -> dict[str, Any]:
    """Public, neutral record of a held admission. Never uses the word for a live dispute."""
    lead, request, receipt, meta = report.lead, report.request, report.receipt, report.meta
    target = lead["target"]
    return {
        "contract": REVIEWCONTRACT, "caseId": report.caseId, "status": "admission-held",
        "subjectId": target["skillId"], "subjectKind": target["kind"],
        "genericSkillRef": target.get("genericSkillId") or target["skillId"],
        "leadId": lead["leadId"], "claimId": lead["claimId"], "claim": lead["capability"]["claim"],
        "challenger": {"name": lead["identity"]["name"], "version": lead["identity"]["version"],
                       "sourceUrl": lead["source"]["url"]},
        "comparator": lead["comparison"]["comparator"],
        "protocolDigest": request["protocol"]["contentDigest"], "requestId": request["requestId"],
        "experiment": {"result": receipt.get("result"), "documentedVersion": receipt.get("documentedVersion"),
                       "executedVersion": receipt.get("executedVersion")},
        "assessment": {"outcome": meta["outcome"], "suggestedAction": meta["recommend"]["action"],
                       "independence": meta["independence"]},
        "held": {"reason": outcome.reason, "explanation": HELDTEXT.get(outcome.reason, "Admission was held.")},
        "bundleDigest": report.digests["bundle"], "disclosure": DISCLOSURE,
    }


def listCases(base: Path) -> tuple[list[str], list[dict[str, str]]]:
    names, rejected = [], []
    for entry in sorted(base.iterdir()):
        if entry.name.startswith(".") or (entry.is_file() and not entry.is_symlink()):
            continue
        if entry.is_symlink() or not entry.is_dir() or not admission.CASEIDRE.fullmatch(entry.name):
            rejected.append({"caseId": entry.name, "reason": "not a regular case directory with a valid id"})
        else:
            names.append(entry.name)
    return names, rejected


def collect(root: str | Path, *, resolver: Any = None,
            probe: Callable[[Path], Mapping[str, Any]] | None = None) -> Collected:
    """Load every committed bundle. ``resolver``/``probe`` are test seams; builds pass neither."""
    rootPath = Path(root).resolve()
    base = rootPath / admission.EVIDENCE
    if base.is_symlink() or not base.is_dir():
        return Collected(False, False, "ledger-absent", {}, {}, (), ())
    caseIds, rejected = listCases(base)
    admitted: dict[str, list[Challenge]] = {}
    refs: dict[str, str] = {}
    reviews: list[dict[str, Any]] = []
    for caseId in caseIds:
        try:
            report = admission.inspectBundle(rootPath, caseId)
            if not report.ok:
                rejected.append({"caseId": caseId, "reason": report.errors[0][:200]})
                continue
            outcome = admission.attemptAdmission(report, rootPath, resolver=resolver, online=False)
        except Exception as exc:  # fail closed per item
            rejected.append({"caseId": caseId, "reason": f"{type(exc).__name__}: {exc}"[:200]})
            continue
        if outcome.challenge is not None:
            subject = outcome.challenge.subject_id
            admitted.setdefault(subject, []).append(outcome.challenge)
            refs[subject] = report.lead["target"].get("genericSkillId") or report.lead["target"]["skillId"]
        else:
            reviews.append(reviewOf(report, outcome))
    try:
        issuer = dict((probe or defaultProbe)(rootPath))
    except Exception as exc:
        issuer = {"status": "misconfigured", "reason": str(exc)}
    status = str(issuer.get("status", "misconfigured"))
    active = resolver
    if admitted and active is None:
        active = admission.productionResolver(rootPath, online=False)
    return Collected(True, status in VERIFIABLE, status,
                     {key: tuple(value) for key, value in sorted(admitted.items())}, dict(sorted(refs.items())),
                     tuple(sorted(reviews, key=lambda item: item["caseId"])),
                     tuple(sorted(rejected, key=lambda item: item["caseId"])), active)


class CommittedChallengeSource:
    """``ChallengeSource`` over admitted challenges; None (unavailable) for any other subject."""

    def __init__(self, admitted: Mapping[str, tuple[Challenge, ...]]) -> None:
        self.admitted = admitted

    def challenges_for(self, subject_id: str) -> tuple[Challenge, ...] | None:
        return self.admitted.get(subject_id)


def lifecyclePorts(collected: Collected) -> LifecyclePorts | None:
    """Ports for ``produce_lifecycle``; None when nothing is admitted (output stays byte-identical)."""
    if not collected.admitted or collected.resolver is None or not collected.issuerVerifiable:
        return None
    return LifecyclePorts(CommittedChallengeSource(collected.admitted), collected.resolver, None)


def reviewsBySubject(collected: Collected) -> dict[str, list[dict[str, Any]]]:
    """Reviews for the ``challengeReviews`` channel, only when the issuer path is verifiable."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    if collected.sourceStatus == "unavailable":
        return grouped
    for review in collected.reviews:
        grouped.setdefault(review["subjectId"], []).append(review)
    return grouped
