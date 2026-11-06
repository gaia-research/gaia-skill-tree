"""Pure evaluation of one census pull request against its registered producer.

Every function here is deterministic. A gate is ``pass``, ``fail`` or ``unknown``; ``unknown`` is
never promoted to ``pass`` (a check that never ran, an object that is not local, a verifier that has
not answered). The disposition is the *first* rule that applies, so a founder hold always outranks a
technical failure, and a technical failure always outranks "ready".
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from gaia_cli.steward.models import stable_json
from gaia_cli.steward.prmaintenance import proofs
from gaia_cli.steward.prmaintenance.producers import Match, Producer, Registry, matchProducer

PASS, FAIL, UNKNOWN = proofs.PASS, proofs.FAIL, proofs.UNKNOWN

KIND_MERGE = "routine_pr_merge_ready"
KIND_BLOCKED = "routine_pr_blocked"
KIND_SUPERSEDED = "routine_pr_superseded"
KIND_CONFLICT = "routine_pr_conflict"
KIND_VERIFY = "routine_pr_verification_failed"
KIND_PROVENANCE = "routine_pr_provenance_unknown"
KIND_CLOSURE = "routine_pr_closure_ready"
KIND_FOUNDER = "routine_pr_founder_decision"
KINDS = (KIND_MERGE, KIND_BLOCKED, KIND_SUPERSEDED, KIND_CONFLICT, KIND_VERIFY, KIND_PROVENANCE, KIND_CLOSURE, KIND_FOUNDER)
CLASS_C_KINDS = (KIND_FOUNDER,)

CHECKAPP = "github-actions"
FAILED = {"failure", "cancelled", "timed_out", "action_required", "startup_failure", "stale"}
HOLDWORD = re.compile(r"(?i)\bsteward[: -]hold\b")
TRUSTED = {"OWNER", "MEMBER", "COLLABORATOR"}
# What each reconciler can regenerate. A failing gate outside this set is not reconcilable by it.
RECONCILERS = {
    "content-engine-cachebust": {
        "repairs": ("cache-bust-current", "base-currency", "ci:Schema + DAG + Integrity Checks", "index-rebuild", "mergeable",
                    "ci:Verify branch scope matches changed files"),
        "requires": ("report-json", "rendered-html", "provenance", "scope", "holds"),
    },
}


@dataclass(frozen=True)
class Gate:
    name: str
    state: str
    detail: str

    def asDict(self) -> dict[str, str]:
        return {"name": self.name, "state": self.state, "detail": self.detail[:400]}


@dataclass(frozen=True)
class Evaluation:
    repo: str
    number: int
    title: str
    headSha: str
    baseSha: str
    baseRef: str
    producerId: str | None
    match: str
    label: str | None
    kind: str
    authority: str
    gates: tuple[Gate, ...]
    reasons: tuple[str, ...]
    reconcile: str | None = None
    closureReason: str | None = None
    replacement: int | None = None
    evidence: Mapping[str, Any] = field(default_factory=dict)

    @property
    def subjectId(self) -> str:
        return f"{self.repo}#{self.number}"

    def gate(self, name: str) -> Gate | None:
        return next((g for g in self.gates if g.name == name), None)

    def asState(self) -> dict[str, Any]:
        return {
            "repo": self.repo, "number": self.number, "title": self.title[:160], "headSha": self.headSha,
            "baseSha": self.baseSha, "baseRef": self.baseRef, "producerId": self.producerId, "match": self.match,
            "label": self.label, "disposition": self.kind, "authority": self.authority,
            "gates": [g.asDict() for g in self.gates], "reasons": list(self.reasons), "reconcile": self.reconcile,
            "closureReason": self.closureReason, "replacement": self.replacement, "evidence": dict(self.evidence),
        }

    def digest(self) -> str:
        return hashlib.sha256(stable_json(self.asState()).encode("utf-8")).hexdigest()


def gateOf(name: str, state: str, detail: str) -> Gate:
    return Gate(name, state, detail)


def latestReviews(row: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    """The latest review state per reviewer. A review is evidence only for the commit it was made on."""

    latest: dict[str, Mapping[str, Any]] = {}
    for review in sorted((r for r in row.get("reviews") or [] if isinstance(r, dict)), key=lambda r: str(r.get("submittedAt"))):
        if review.get("state") in {"APPROVED", "CHANGES_REQUESTED", "DISMISSED"}:
            latest[str(review.get("user"))] = review
    return latest


def checkGates(row: Mapping[str, Any], producer: Producer, protection: Mapping[str, Any]) -> list[Gate]:
    """Required checks must have run, at the head SHA, and passed. A check that never ran is unknown."""

    required = sorted({*producer.requiredChecks, *[str(c) for c in protection.get("requiredChecks") or []]})
    gates = []
    # Only the app a ruleset names (GitHub Actions) can satisfy a required context; a same-named check from another app is ignored.
    runs = [r for r in row.get("checkRuns") or [] if isinstance(r, dict) and r.get("app") == CHECKAPP]
    for name in required:
        mine = [r for r in runs if r.get("name") == name]
        if not mine:
            gates.append(gateOf(f"ci:{name}", UNKNOWN, "required check has not run at this head"))
        elif any(r.get("status") != "completed" for r in mine):
            gates.append(gateOf(f"ci:{name}", UNKNOWN, "required check is still running"))
        elif any(r.get("conclusion") in FAILED for r in mine):
            gates.append(gateOf(f"ci:{name}", FAIL, "required check failed at this head"))
        elif any(r.get("conclusion") == "success" for r in mine):
            gates.append(gateOf(f"ci:{name}", PASS, "required check succeeded at this head"))
        else:
            gates.append(gateOf(f"ci:{name}", UNKNOWN, "required check ended without success"))
    return gates


def provenanceGate(match: Match, row: Mapping[str, Any]) -> list[Gate]:
    """Identity, branch, labels, same-repository head, and EVERY commit. No commit evidence is a failure, never a pass."""

    producer = match.producer
    if not match.verified or producer is None:
        return [gateOf("provenance", FAIL, "; ".join(match.reasons) or match.status)]
    commits = [c for c in row.get("commits") or [] if isinstance(c, dict)]
    if not commits:
        return [gateOf("provenance", FAIL, "no commit evidence is available for this pull request")]
    foreign = []
    for commit in commits:
        short = str(commit.get("sha"))[:9]
        if int(commit.get("parents") or 1) > 1:
            # A merge commit is either made through GitHub's web flow (committer login web-flow AND a verified GitHub signature)
            # or by one of the producer's own verified identities. A free-text committer name proves nothing.
            webFlow = commit.get("committerLogin") in producer.allowedMergeCommitters and commit.get("verified") is True
            ownMerge = commit.get("committerLogin") in {who.login for who in producer.commitAuthors}
            if not (webFlow or ownMerge):
                foreign.append(f"merge {short} committed by {commit.get('committerLogin')!r} (verified={commit.get('verified')})")
        elif not any(commit.get("authorLogin") == who.login and commit.get("authorType") == who.accountType
                     and (who.accountId is None or commit.get("authorId") == who.accountId) for who in producer.commitAuthors):
            foreign.append(f"commit {short} authored by {commit.get('authorLogin')!r} ({commit.get('authorType')!r})")
    if foreign:
        return [gateOf("provenance", FAIL, "commits not made by the producer or by GitHub: " + "; ".join(foreign[:4]))]
    if producer.commitMarker and not any(producer.commitMarker in str(c.get("message") or "") for c in commits
                                         if int(c.get("parents") or 1) == 1):
        return [gateOf("provenance", FAIL, f"no producer commit names its workflow ({producer.commitMarker})")]
    return [gateOf("provenance", PASS, f"identity, branch convention, label, same-repository head and {len(commits)} commit(s) verified")]


def scopeGate(row: Mapping[str, Any], producer: Producer, label: str | None) -> Gate:
    bad, removed = [], []
    for item in row.get("files") or []:
        path = str(item.get("path"))
        if item.get("status") in {"removed", "renamed"}:
            removed.append(path)
        elif producer.pathProtected(path) or not producer.pathAllowed(path, label):
            bad.append(path)
    if removed:
        return gateOf("scope", FAIL, f"a historical file is removed or renamed: {', '.join(removed[:3])}")
    if bad:
        return gateOf("scope", FAIL, f"files outside the producer scope: {', '.join(bad[:4])}")
    if not row.get("files"):
        return gateOf("scope", FAIL, "the pull request changes no files")
    return gateOf("scope", PASS, f"{len(row['files'])} file(s), all inside the producer's allowed paths")


def holdGates(row: Mapping[str, Any], producer: Producer) -> list[Gate]:
    labels = {str(item).strip().lower() for item in row.get("labels") or []}
    gates = []
    held = sorted(labels & {item.lower() for item in producer.holdLabels})
    gates.append(gateOf("holds", FAIL if held else PASS, f"hold label(s): {', '.join(held)}" if held else "no hold labels"))
    reviews = latestReviews(row)
    changes = [u for u, r in reviews.items() if r.get("state") == "CHANGES_REQUESTED"]
    if changes:
        gates.append(gateOf("reviews", FAIL, f"changes requested by {', '.join(changes)}"))
    else:
        gates.append(gateOf("reviews", PASS, "no outstanding change request"))
    voices = [str(c.get("body") or "") for c in row.get("comments") or [] if c.get("authorAssociation") in TRUSTED]
    voices += [str(r.get("body") or "") for r in row.get("reviews") or [] if isinstance(r, dict) and r.get("authorAssociation") in TRUSTED]
    gates.append(gateOf("hold-comment", FAIL if HOLDWORD.search("\n".join(voices)) else PASS,
                        "a maintainer comment or review declares a Steward hold" if HOLDWORD.search("\n".join(voices)) else "no maintainer hold"))
    threads = row.get("reviewThreadsUnresolved")
    if isinstance(threads, bool) or not isinstance(threads, int):
        gates.append(gateOf("review-threads", UNKNOWN, "unresolved review threads could not be read; unknown is never zero"))
    else:
        gates.append(gateOf("review-threads", FAIL if threads > 0 else PASS,
                            f"{threads} unresolved review thread(s)" if threads > 0 else "no unresolved review threads"))
    approvals = [u for u, r in reviews.items()
                 if r.get("state") == "APPROVED" and r.get("commitId") == row.get("headSha") and r.get("authorAssociation") in TRUSTED]
    if producer.requiredApprovals:
        met = len(approvals) >= producer.requiredApprovals
        gates.append(gateOf("approvals", PASS if met else FAIL,
                            f"{len(approvals)}/{producer.requiredApprovals} trusted approval(s) at this head"))
    else:
        gates.append(gateOf("approvals", PASS, f"none required ({producer.reviewRequestPolicy}); {len(approvals)} approval(s) at this head recorded"))
    return gates


REPLACES = re.compile(r"gaia-steward:replaces repo=(?P<repo>[A-Za-z0-9._/-]{1,100}) pr=(?P<pr>[0-9]{1,9}) head=(?P<head>[0-9a-f]{12})")


def replacementGates(root: Path, registry: Registry, repo: str, producer: Producer, row: Mapping[str, Any], label: str | None,
                     siblings: Sequence[Mapping[str, Any]]) -> list[Gate]:
    """A tracked replacement is routine only when it provably carries the original producer's payload, byte for byte."""

    branch = str(row.get("headRef") or "")
    found = producer.branchPattern.match(branch)
    originalNumber = int(found.group("original")) if found and "original" in found.groupdict() else None
    marker = REPLACES.search(str(row.get("body") or ""))
    if marker is None or originalNumber is None or int(marker.group("pr")) != originalNumber or marker.group("repo") != repo:
        return [gateOf("replacement-link", FAIL, "the body carries no replacement marker naming the original pull request on this branch"),
                gateOf("payload-preserved", UNKNOWN, "the original is not identified")]
    original = next((s for s in siblings if s.get("number") == originalNumber and s.get("headSha")), None)
    if original is None or original.get("state", "open") != "open":
        return [gateOf("replacement-link", UNKNOWN, f"the original #{originalNumber} is not an open pull request in the census"),
                gateOf("payload-preserved", UNKNOWN, "the original's head is not available")]
    originalMatch = matchProducer(registry, repo, original)
    if not originalMatch.verified or originalMatch.producer is None or originalMatch.producer.validator != "content-engine-report":
        return [gateOf("replacement-link", FAIL, f"the original #{originalNumber} is not a proven content-engine pull request: "
                                                  + "; ".join(originalMatch.reasons or (originalMatch.status,))),
                gateOf("payload-preserved", UNKNOWN, "the original's provenance is not proven")]
    originalProvenance = provenanceGate(originalMatch, original)[0]
    if originalProvenance.state != PASS:
        return [gateOf("replacement-link", FAIL, f"the original #{originalNumber} fails provenance: {originalProvenance.detail}"),
                gateOf("payload-preserved", UNKNOWN, "the original's provenance is not proven")]
    # A hold, draft, change request or unresolved thread on the ORIGINAL binds the replacement too, including one placed after it was built.
    unready = [g for g in holdGates(original, originalMatch.producer) if g.name != "approvals" and g.state != PASS]
    if original.get("draft") or unready:
        why = "draft" if original.get("draft") else "; ".join(f"{g.name}: {g.detail}" for g in unready[:3])
        return [gateOf("replacement-link", FAIL, f"the original #{originalNumber} is held or not ready ({why})"),
                gateOf("payload-preserved", UNKNOWN, "the original is held")]
    if not str(original["headSha"]).startswith(marker.group("head")):
        return [gateOf("replacement-link", FAIL, "the original's head moved after this replacement was built; rebuild it"),
                gateOf("payload-preserved", UNKNOWN, "the original's head changed")]
    path = f"docs/api/v1/reports/{label}.json"
    mine, theirs = proofs.blob(root, str(row["headSha"]), path), proofs.blob(root, str(original["headSha"]), path)
    if mine is None or theirs is None:
        return [gateOf("replacement-link", PASS, f"marker names original #{originalNumber} at {marker.group('head')}"),
                gateOf("payload-preserved", UNKNOWN, "the payload objects are not available locally")]
    return [gateOf("replacement-link", PASS, f"marker names original #{originalNumber} at {marker.group('head')}; original provenance verified"),
            gateOf("payload-preserved", PASS if mine == theirs else FAIL,
                   "canonical JSON is byte-identical to the original producer's" if mine == theirs
                   else "canonical JSON differs from the original producer's payload")]


def validatorGates(root: Path, producer: Producer, row: Mapping[str, Any], baseSha: str, label: str | None,
                   registry: Registry | None = None, repo: str = "", siblings: Sequence[Mapping[str, Any]] = ()) -> list[Gate]:
    headSha = str(row["headSha"])
    files = [str(f.get("path")) for f in row.get("files") or []]
    if producer.validator == "content-engine-replacement" and label and registry is not None:
        found = [proofs.reportJsonProof(root, headSha, label), proofs.stampProof(root, baseSha, headSha, files)]
        found += proofs.contentEngineProofs(root, baseSha, headSha, label)
        gates = [gateOf(p.name, p.state, p.detail) for p in found] + replacementGates(root, registry, repo, producer, row, label, siblings)
        rendered = next((g for g in gates if g.name == "rendered-html"), None)
        gates.append(gateOf("rendered-surface", rendered.state if rendered else UNKNOWN,
                            "template chrome is the base template's own render (not a design change)" if rendered and rendered.state == PASS
                            else "rendered surface is not proven to be an instance of the base template"))
        return gates
    if producer.validator == "content-engine-report" and label:
        found = [proofs.reportJsonProof(root, headSha, label), proofs.stampProof(root, baseSha, headSha, files)]
        found += proofs.contentEngineProofs(root, baseSha, headSha, label)
        gates = [gateOf(p.name, p.state, p.detail) for p in found]
        rendered = next((g for g in gates if g.name == "rendered-html"), None)
        gates.append(gateOf("rendered-surface", rendered.state if rendered else UNKNOWN,
                            "template chrome is the base template's own render (not a design change)" if rendered and rendered.state == PASS
                            else "rendered surface is not proven to be an instance of the base template"))
        return gates
    if producer.validator == "docs-routine":
        return [gateOf("docs-accuracy", UNKNOWN, "documentation accuracy against CLI behaviour needs an independent verifier receipt"),
                gateOf("rendered-surface", UNKNOWN, "docs edits change visible copy; founder review applies")]
    return [gateOf("validator", UNKNOWN, f"validator {producer.validator!r} is not implemented")]


def supersession(root: Path, repo: str, producer: Producer, row: Mapping[str, Any], label: str | None, baseSha: str,
                 siblings: Sequence[Mapping[str, Any]], closed: Sequence[Mapping[str, Any]]) -> tuple[str | None, int | None, bool, str]:
    """``(reason, replacement, payloadPreserved, detail)`` when the PR is superseded; reason ``None`` otherwise.

    Closure needs three proofs together: the label is already published on the base, a merged PR carrying this
    PR's replacement marker exists, and the original canonical JSON is byte-identical to the published one.
    """

    if not label:
        return None, None, False, "no label"
    exact = re.compile(rf"gaia-steward:replaces repo={re.escape(repo)} pr={int(row['number'])}(?![0-9])")
    merged = next((c for c in closed if c.get("mergedAt") and exact.search(str(c.get("body") or ""))), None)
    if producer.validator == "content-engine-report":
        published = proofs.blob(root, baseSha, f"docs/api/v1/reports/{label}.json")
        mine = proofs.blob(root, str(row["headSha"]), f"docs/api/v1/reports/{label}.json")
        if published is not None:
            same = mine is not None and published == mine
            return ("label-already-published", int(merged["number"]) if merged else None, same,
                    f"report {label} is already published on the base; the original payload is "
                    f"{'byte-identical to' if same else 'different from'} the published one"
                    + (f"; replacement #{merged['number']} merged" if merged else "; no merged replacement is linked"))
    twin = next((s for s in siblings if s.get("number") != row.get("number") and producer.labelOf(str(s.get("headRef"))) == label), None)
    if twin is not None and int(twin["number"]) < int(row["number"]):
        return "duplicate-of-open-sibling", int(twin["number"]), False, f"PR #{twin['number']} already proposes report {label}"
    return None, None, False, "not superseded"


def evaluate(root: Path, registry: Registry, repo: str, row: Mapping[str, Any], tips: Mapping[str, str],
             protection: Mapping[str, Any], siblings: Sequence[Mapping[str, Any]], closed: Sequence[Mapping[str, Any]]) -> Evaluation | None:
    """One pull request -> one disposition, or ``None`` when it is not routine work for any registered producer."""

    match = matchProducer(registry, repo, row)
    base = dict(repo=repo, number=int(row["number"]), title=str(row.get("title") or ""), headSha=str(row["headSha"]),
                baseSha=str(row["baseSha"]), baseRef=str(row["baseRef"]))
    if match.status in {"deferred", "not-enabled"}:
        return None
    author = row.get("author") if isinstance(row.get("author"), Mapping) else {}
    if match.status == "unknown-producer":
        if author.get("type") != "Bot":
            return None  # a human feature PR is not routine work and is not Steward's to classify
        gates = (gateOf("provenance", FAIL, "an automation account opened this PR but no registered producer owns it"),)
        return Evaluation(**base, producerId=None, match=match.status, label=None, kind=KIND_PROVENANCE, authority="B",
                          gates=gates, reasons=("unregistered automation producer",))
    producer, label = match.producer, match.label
    gates: list[Gate] = provenanceGate(match, row)
    if not match.verified or producer is None:
        return Evaluation(**base, producerId=producer.id if producer else None, match=match.status, label=label,
                          kind=KIND_PROVENANCE, authority="B", gates=tuple(gates), reasons=tuple(match.reasons))
    if gates[0].state != PASS:
        return Evaluation(**base, producerId=producer.id, match=match.status, label=label, kind=KIND_PROVENANCE, authority="B",
                          gates=tuple(gates), reasons=(gates[0].detail,))
    if row.get("state") != "open":
        gates.append(gateOf("state", FAIL, f"pull request is {row.get('state')}"))
    draft = bool(row.get("draft"))
    gates.append(gateOf("draft", FAIL if draft else PASS, "draft pull request" if draft else "ready for review"))
    gates += holdGates(row, producer)
    gates.append(scopeGate(row, producer, label))
    gates += checkGates(row, producer, protection)
    tip = tips.get(str(row["baseRef"]))
    gates.append(gateOf("base-currency", PASS if tip == row["baseSha"] else FAIL,
                        "up to date with the destination tip" if tip == row["baseSha"]
                        else f"base {str(row['baseSha'])[:9]} is behind destination tip {str(tip)[:9]}"))
    conflict = row.get("mergeable") is False or row.get("mergeableState") == "dirty"
    gates.append(gateOf("mergeable", FAIL if conflict else (PASS if row.get("mergeable") is True else UNKNOWN),
                        "merge conflicts with the destination" if conflict else
                        ("GitHub reports a clean merge" if row.get("mergeable") is True else "mergeability not yet computed")))
    gates += validatorGates(root, producer, row, str(tip or row["baseSha"]), label, registry, repo, siblings)
    reason, replacement, preserved, detail = supersession(root, repo, producer, row, label, str(tip or row["baseSha"]), siblings, closed)
    reasons: list[str] = []
    by = {g.name: g for g in gates}
    heldOriginal = by.get("replacement-link") is not None and by["replacement-link"].state == FAIL and "is held or not ready" in by["replacement-link"].detail
    held = heldOriginal or (draft and producer.draftPolicy == "hold") or by["holds"].state == FAIL or by["reviews"].state == FAIL \
        or by.get("hold-comment", Gate("", PASS, "")).state == FAIL or by["approvals"].state == FAIL \
        or by.get("review-threads", Gate("", PASS, "")).state == FAIL \
        or (by.get("rendered-surface") and by["rendered-surface"].state == FAIL)
    evidence = {"producerRevision": registry.revision, "registrySha256": registry.sha256, "supersession": detail}
    if held:
        why = [g.detail for g in gates if g.state == FAIL and g.name in {"draft", "holds", "reviews", "hold-comment", "review-threads", "approvals", "rendered-surface", "replacement-link"}]
        if draft and producer.draftPolicy == "hold":
            why.insert(0, "draft state is a founder hold and is never read as consent")
        return Evaluation(**base, producerId=producer.id, match=match.status, label=label, kind=KIND_FOUNDER, authority="C",
                          gates=tuple(gates), reasons=tuple(dict.fromkeys(why)) or ("founder decision required",), evidence=evidence)
    if reason:
        # Superseded is always reported. Closure additionally needs the reason to be registered as eligible AND proven:
        # the label is published, a merged marker-linked replacement exists, and the payload is byte-identical.
        eligible = reason in producer.closureEligibility
        # A hold, a draft, an unresolved thread or a change request is never overridden by supersession: those go to the founder above.
        clean = all(by[name].state == PASS for name in ("draft", "holds", "reviews", "hold-comment", "review-threads") if name in by)
        provable = eligible and clean and bool(replacement) and preserved and reason == "label-already-published"
        gates.append(gateOf("supersession", PASS if provable else UNKNOWN, detail))
        return Evaluation(**base, producerId=producer.id, match=match.status, label=label,
                          kind=KIND_CLOSURE if provable else KIND_SUPERSEDED, authority="B", gates=tuple(gates),
                          reasons=(detail,), closureReason=reason, replacement=replacement, evidence=evidence)
    failing = [g for g in gates if g.state == FAIL]
    unknown = [g for g in gates if g.state == UNKNOWN]
    reconciler = producer.reconciler
    spec = RECONCILERS.get(reconciler or "")
    reconcile = None
    if spec and (failing or unknown):
        problems = {g.name for g in failing + unknown}
        if problems <= set(spec["repairs"]) and all(by.get(n) and by[n].state == PASS for n in spec["requires"]):
            reconcile = reconciler
    if by["mergeable"].state == FAIL:
        return Evaluation(**base, producerId=producer.id, match=match.status, label=label, kind=KIND_CONFLICT, authority="B",
                          gates=tuple(gates), reasons=(by["mergeable"].detail,), reconcile=reconcile, evidence=evidence)
    if failing:
        return Evaluation(**base, producerId=producer.id, match=match.status, label=label, kind=KIND_VERIFY, authority="B",
                          gates=tuple(gates), reasons=tuple(f"{g.name}: {g.detail}" for g in failing[:6]), reconcile=reconcile, evidence=evidence)
    if unknown:
        return Evaluation(**base, producerId=producer.id, match=match.status, label=label, kind=KIND_BLOCKED, authority="B",
                          gates=tuple(gates), reasons=tuple(f"{g.name}: {g.detail}" for g in unknown[:6]), reconcile=reconcile, evidence=evidence)
    return Evaluation(**base, producerId=producer.id, match=match.status, label=label, kind=KIND_MERGE, authority="B",
                      gates=tuple(gates), reasons=("every registered gate passed; independent verification is still required before any merge",),
                      evidence=evidence)


def evaluateCensus(root: Path, registry: Registry, document: Mapping[str, Any]) -> list[Evaluation]:
    repo = str(document["repo"])
    rows = [r for r in document.get("pulls") or [] if isinstance(r, dict)]
    tips = document.get("baseTips") or {}
    protection = document.get("protection") or {}
    closed = [r for r in document.get("recentlyClosed") or [] if isinstance(r, dict)]
    found = []
    for row in sorted(rows, key=lambda r: r["number"]):
        evaluation = evaluate(root, registry, repo, row, tips, protection, rows, closed)
        if evaluation is not None:
            found.append(evaluation)
    return found
