"""Read-side ports over committed Frontier case bundles (build time, fail closed per item).

Every docs build re-validates each ``evidence/frontier-challenges/<case>/`` bundle and
re-attempts admission through the production offline resolver, one case-bound resolver per
case (see ``challengeAdmission.CaseResolver``). Nothing recorded in a bundle (including
``events.jsonl``) is trusted as an admitted state:

* a case whose issuer receipt verifies AND binds the bundle becomes an admitted ``Challenge``
  and feeds the ``trustLifecycle`` channel through ``LifecyclePorts``;
* every other valid case becomes a ``gaia-challenge-review/v1`` record for the separate
  ``challengeReviews`` channel / ``reviews.json`` artifact (never labelled as a dispute);
* a bundle that fails re-validation, or collides with another case on challenge id or
  receipt id, is rejected: it appears nowhere public and the build log says why.

Determinism: with no bundle that claims an admission (an admission request plus a committed
``receipt/``), nothing here needs ``gh`` or full git history. When one does and the machine
cannot verify it, the build fails loudly (``BuildEnvironmentError``) instead of publishing
machine-dependent bytes. Any ``GAIA_RECEIPT_*`` trust-pin override disables publication.
"""
from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping

from . import challengeAdmission as admission
from .challengeAdmission import HoldReason
from .challengeDomain import Challenge
from .lifecycleProjection import LifecyclePorts
from .steward.challenge_receipts import CONFIG_ENV

REVIEWCONTRACT = "gaia-challenge-review/v1"
TRIAGESTATUS = "rejected-at-triage"
DEFERREDSTATUS = "deferred-at-triage"
DEFERREDDISCLOSURE = ("Review record only. This lead was deferred at triage, with no effect on standing: no experiment "
                      "was run and no admission was attempted, so this is not an admitted Gaia challenge and it "
                      "changes no Trust Magnitude, star, grade, Origin or ranking.")
TRIAGEDISCLOSURE = ("Review record only. This lead was rejected at triage: no experiment was run and no admission "
                    "was attempted, so this is not an admitted Gaia challenge and it changes no Trust Magnitude, "
                    "star, grade, Origin or ranking.")
HELDTEXT = {
    HoldReason.ISSUER_UNAVAILABLE: "The trusted receipt issuer produced no verifiable receipt for this review.",
    HoldReason.ISSUER_MISCONFIGURED: "The trusted receipt issuer configuration is not usable in this build.",
    HoldReason.RECEIPT_UNVERIFIABLE: "A receipt exists but could not be verified.",
    HoldReason.CHALLENGE_REJECTED: "The challenge domain rejected the admission request.",
    HoldReason.BUNDLE_NOT_BOUND: "The issued receipt does not bind this exact review bundle.",
    HoldReason.REQUEST_MISSING: "No admission was requested.",
    HoldReason.META_NOT_RECOMMENDED: "The independent assessment of this review does not recommend an admission review.",
    HoldReason.EVENT_LOG_BROKEN: "The review's event log failed its integrity check, so admission is held.",
}


NOEFFECT = "with no effect on Trust Magnitude, stars, grade, Origin or ranking"
DISCLOSURELEAD = "Review record only. This is not an admitted Gaia challenge, "


def heldDisclosure(reason: HoldReason) -> str:
    """Public text for a held review, keyed to what actually happened: an admission is described as
    requested only when a request exists. The build's automatic re-attempt is not a request."""
    if reason is HoldReason.REQUEST_MISSING:
        state = "No admission was requested."
    elif reason is HoldReason.META_NOT_RECOMMENDED:
        state = "The independent assessment does not recommend an admission review."
    else:
        state = f"An admission was requested and is held: {HELDTEXT[reason]}"
    return f"{DISCLOSURELEAD}{NOEFFECT}. {state}"


def overridesPresent() -> list[str]:
    return sorted(name for name in CONFIG_ENV.values() if os.environ.get(name))


def gitIsShallow(root: Path) -> bool:
    done = admission.scrubbedGit(["git", "-C", str(root), "rev-parse", "--is-shallow-repository"],
                                 capture_output=True, text=True, check=False)
    return done.returncode != 0 or done.stdout.strip() != "false"


@dataclass(frozen=True)
class Collected:
    ledgerPresent: bool
    admitted: Mapping[str, tuple[Challenge, ...]]
    genericRefs: Mapping[str, str]
    reviews: tuple[dict[str, Any], ...]
    rejected: tuple[dict[str, str], ...]
    resolver: Any = field(default=None, compare=False)
    disabled: str = ""

    @property
    def sourceStatus(self) -> str:
        """``verified`` only once a challenge was admitted through the production resolver.

        ``unavailable`` otherwise. ``verified-empty`` is reserved in the contract and never
        produced: a tooling probe is not proof that the set of challenges is empty.
        """
        return "verified" if self.admitted and not self.disabled else "unavailable"


def triageReviewOf(report: admission.BundleReport) -> dict[str, Any]:
    """Public, neutral record of a lead rejected at triage (no request, receipt or numbers)."""
    lead, meta = report.lead, report.meta
    target = lead["target"]
    deferred = meta.get("outcome") == "deferred_at_triage"
    if not deferred and meta.get("outcome") != "rejected_at_triage":
        raise ValueError("triage outcome must be rejected_at_triage or deferred_at_triage")
    return {
        "contract": REVIEWCONTRACT, "caseId": report.caseId, "status": DEFERREDSTATUS if deferred else TRIAGESTATUS,
        "subjectId": target["skillId"], "subjectKind": target["kind"],
        "genericSkillRef": target.get("genericSkillId") or target["skillId"],
        "leadId": lead["leadId"], "claimId": lead["claimId"], "claim": lead["capability"]["claim"],
        "challenger": {"name": lead["identity"]["name"], "version": lead["identity"]["version"],
                       "sourceUrl": lead["source"]["url"]},
        "comparator": lead["comparison"]["comparator"],
        "assessment": {"outcome": meta["outcome"], "suggestedAction": meta["recommend"]["action"],
                       "independence": meta["independence"]},
        "triage": {"explanation": ("The lead was deferred at triage, with no effect on standing; no experiment was run."
                                   if deferred else
                                   "The lead was rejected at triage, before any experiment was preregistered or run.")},
        "bundleDigest": report.digests["bundle"], "disclosure": DEFERREDDISCLOSURE if deferred else TRIAGEDISCLOSURE,
    }


def reviewOf(report: admission.BundleReport, outcome: admission.AdmissionOutcome) -> dict[str, Any]:
    """Public, neutral record of a held admission."""
    lead, request, receipt, meta = report.lead, report.request, report.receipt, report.meta
    target = lead["target"]
    reason = outcome.reason or HoldReason.ISSUER_UNAVAILABLE
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
        "held": {"reason": reason.value, "explanation": HELDTEXT[reason]},
        "bundleDigest": report.digests["bundle"], "disclosure": heldDisclosure(reason),
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
    folded: dict[str, list[str]] = {}
    for name in names:
        folded.setdefault(name.casefold(), []).append(name)
    clashing = {name for group in folded.values() if len(group) > 1 for name in group}
    for name in sorted(clashing):  # ids that differ only by case would alias on a case-insensitive checkout
        others = ", ".join(sorted(set(folded[name.casefold()]) - {name}))
        rejected.append({"caseId": name, "reason": f"case id differs only by letter case from {others}"})
    return [name for name in names if name not in clashing], rejected


def rejectCollisions(reports: dict[str, admission.BundleReport]) -> dict[str, str]:
    """Cases that share a challenge id or receipt id are ALL rejected (never first-wins).

    Called with the would-be-admitted cases only, so a held case cannot suppress a real admission."""
    owners: dict[tuple[str, str], list[str]] = {}
    for caseId, report in reports.items():
        for kind, value in (("challenge id", report.challengeId), ("receipt id", report.receiptId)):
            if value:
                owners.setdefault((kind, value.casefold()), []).append(caseId)
    reasons: dict[str, str] = {}
    for (kind, _), cases in owners.items():
        if len(cases) > 1:
            for caseId in cases:
                reasons[caseId] = f"shares a {kind} with " + ", ".join(sorted(set(cases) - {caseId}))
    return reasons


class RoutingResolver:
    """Routes a challenge id to the resolver bound to the case that admitted it."""

    def __init__(self, byChallenge: Mapping[str, Any]) -> None:
        self.byChallenge = dict(byChallenge)

    def for_challenge(self, challengeId: str):
        if challengeId not in self.byChallenge:
            raise KeyError("no admitted case for this challenge")
        return self.byChallenge[challengeId].for_challenge(challengeId)


def collect(root: str | Path, *, resolver: Any = None, which: Callable[[str], str | None] = shutil.which,
            shallow: Callable[[Path], bool] = gitIsShallow) -> Collected:
    """Load every committed bundle. ``resolver``/``which``/``shallow`` are test seams; builds pass none."""
    rootPath = Path(root).resolve()
    base = rootPath / admission.EVIDENCE
    if base.is_symlink() or not base.is_dir():
        return Collected(False, {}, {}, (), ())
    overrides = overridesPresent()
    if overrides:
        message = ("trust-pin overrides are set (" + ", ".join(overrides) + "); challenge publication is disabled")
        print(f"  warning: {message}", file=sys.stderr)
        return Collected(True, {}, {}, (), (), disabled=message)
    caseIds, rejected = listCases(base)
    reports: dict[str, admission.BundleReport] = {}
    for caseId in caseIds:
        try:
            report = admission.inspectBundle(rootPath, caseId)
        except Exception as exc:  # fail closed per item
            rejected.append({"caseId": caseId, "reason": admission.clean(f"{type(exc).__name__}: {exc}")})
            continue
        if report.ok:
            reports[caseId] = report
        else:
            rejected.append({"caseId": caseId, "reason": admission.clean(report.errors[0])})
    claims = [r.caseId for r in reports.values() if not r.triage and r.admission is not None and r.hasCommittedReceipt]
    if claims and resolver is None:
        if not which("gh"):
            raise admission.BuildEnvironmentError(
                f"case(s) {', '.join(claims)} claim an issuer receipt but the gh CLI is not installed; "
                "attestation verification cannot run, and publishing would be machine-dependent")
        if shallow(rootPath):
            raise admission.BuildEnvironmentError(
                f"case(s) {', '.join(claims)} claim an issuer receipt but git history is shallow or unreadable; "
                "check out with fetch-depth: 0 (attested commits must be reachable)")
    results: dict[str, admission.AdmissionOutcome] = {}
    reviews: list[dict[str, Any]] = []
    for caseId, report in sorted(reports.items()):
        if report.triage:  # never enters admission: a review entry only
            try:
                reviews.append(triageReviewOf(report))
            except Exception as exc:
                rejected.append({"caseId": caseId, "reason": admission.clean(f"{type(exc).__name__}: {exc}")})
            continue
        try:
            results[caseId] = admission.attemptAdmission(report, rootPath, resolver=resolver, online=False)
        except Exception as exc:
            rejected.append({"caseId": caseId, "reason": admission.clean(f"{type(exc).__name__}: {exc}")})
    # Collisions matter only between cases that would BOTH be admitted: a held case that shares
    # an id with an admitted one becomes a review and leaves the admitted case intact.
    winners = {caseId: reports[caseId] for caseId, out in results.items() if out.outcome is admission.Outcome.ADMITTED}
    collided = rejectCollisions(winners)
    admitted: dict[str, list[Challenge]] = {}
    refs: dict[str, str] = {}
    routes: dict[str, Any] = {}
    for caseId, outcome in sorted(results.items()):
        report = reports[caseId]
        if caseId in collided:
            rejected.append({"caseId": caseId, "reason": collided[caseId]})
        elif outcome.outcome is admission.Outcome.ADMITTED and outcome.challenge is not None:
            subject = outcome.challenge.subject_id
            if refs.setdefault(subject, outcome.genericRef or "") != outcome.genericRef:
                rejected.append({"caseId": caseId, "reason": "generic skill reference conflicts with another case"})
                continue
            admitted.setdefault(subject, []).append(outcome.challenge)
            routes[outcome.challenge.challenge_id] = outcome.resolver
        else:
            reviews.append(reviewOf(report, outcome))
            if outcome.reason is HoldReason.EVENT_LOG_BROKEN:
                print(f"  warning: challenge case {caseId} event log is broken: {outcome.detail}", file=sys.stderr)
            elif report.eventErrors:  # another hold reason took precedence; the log problem is still surfaced
                print(f"  warning: challenge case {admission.clean(caseId)} event log is broken: "
                      f"{admission.clean('; '.join(report.eventErrors))}", file=sys.stderr)
    return Collected(True, {key: tuple(value) for key, value in sorted(admitted.items())}, dict(sorted(refs.items())),
                     tuple(sorted(reviews, key=lambda item: item["caseId"])),
                     tuple(sorted(rejected, key=lambda item: item["caseId"])), RoutingResolver(routes))


class CommittedChallengeSource:
    """``ChallengeSource`` over admitted challenges; None (unavailable) for any other subject."""

    def __init__(self, admitted: Mapping[str, tuple[Challenge, ...]]) -> None:
        self.admitted = admitted

    def challenges_for(self, subject_id: str) -> tuple[Challenge, ...] | None:
        return self.admitted.get(subject_id)


def lifecyclePorts(collected: Collected) -> LifecyclePorts | None:
    """Ports for ``produce_lifecycle``; None when nothing is admitted (output stays byte-identical)."""
    if not collected.admitted or collected.resolver is None or collected.disabled:
        return None
    return LifecyclePorts(CommittedChallengeSource(collected.admitted), collected.resolver, None)


def reviewsBySubject(collected: Collected) -> dict[str, list[dict[str, Any]]]:
    """Valid reviews for the ``challengeReviews`` channel (same validator as reviews.json)."""
    from .challengeProjection import validateReview
    grouped: dict[str, list[dict[str, Any]]] = {}
    if collected.disabled:
        return grouped
    for review in collected.reviews:
        if not validateReview(review):
            grouped.setdefault(review["subjectId"], []).append(review)
    return grouped
