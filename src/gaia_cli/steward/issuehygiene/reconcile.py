"""Deterministic reconciliation of the GitHub census (contract sections 3.3 and 3.4, lane B).

``reconcile`` is a pure function of (census, registry index, policy, now, workflow probes).
It names every open issue, decides what each item is entitled to (authority A, B, C or
none), and assembles the manifest. It never writes and never reads the wall clock:
the manifest carries no timestamp except ``censusFetchedAt``.

Authority is downgraded, never upgraded. A closure rule applies only when its hard proof
holds, the rule is enabled in policy, the census is complete and the item has no
unknowns. Everything else is B (actionable batch) or C (one founder question per
distinct question).
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

import yaml

from gaia_cli.steward.issuehygiene.census import COMPLETE, Census, validateCensus
from gaia_cli.steward.issuehygiene.hygienepolicy import HygienePolicy
from gaia_cli.steward.issuehygiene.identity import Graph, Identity, buildGraph, classify, compareVersions, labelNames
from gaia_cli.steward.issuehygiene.registryindex import (
    GithubRef,
    NamedRecord,
    RegistryIndex,
    normalizeHandle,
    parseGithubUrl,
    refSplitTrusted,
    splitId,
)

SCHEMA_VERSION = "steward-issue-reconciliation-v1"
WORKFLOW_DIR = ".github/workflows"

RULE_A1 = "A1-child-curated"
RULE_A2 = "A2-umbrella-synced"
RULE_A3 = "A3-umbrella-superseded"
RULE_A4 = "A4-duplicate-child"
RULE_A5 = "A5-botreport-superseded"
RULE_STATE_REASON = {
    RULE_A1: "completed",
    RULE_A2: "completed",
    RULE_A3: "not_planned",
    RULE_A4: "duplicate",
    RULE_A5: "not_planned",
}

AUTH_A = "A"
AUTH_B = "B"
AUTH_C = "C"
AUTH_NONE = "none"

STATE_RESOLVED = "resolved"
STATE_SUPERSEDED = "superseded"
STATE_DUPLICATE = "duplicate"
STATE_ACTIONABLE = "actionable"
STATE_AMBIGUOUS = "ambiguous"
STATE_AWAITING = "awaiting-founder"
STATE_NOT_EVALUATED = "not-evaluated"
CLOSABLE_STATES = (STATE_RESOLVED, STATE_SUPERSEDED, STATE_DUPLICATE)
RULE_STATE = {RULE_A1: STATE_RESOLVED, RULE_A2: STATE_RESOLVED, RULE_A3: STATE_SUPERSEDED, RULE_A4: STATE_DUPLICATE, RULE_A5: STATE_RESOLVED}

ORPHAN_REASONS = frozenset({"no-parent-reference", "parent-closed", "parent-not-open", "parent-not-umbrella"})
SUITE_PREFIX = "upstream-suite:"
MISMATCH_PREFIX = "title-payload-suite-mismatch:"
PAYLOAD_LIST_RE = re.compile(r"(?:^|[\s`])\+\s*([A-Za-z][A-Za-z0-9._-]*)", re.MULTILINE)
WORKFLOW_REF_RE = re.compile(r"\.github/workflows/([A-Za-z0-9._-]+\.(?:md|ya?ml))")
SECURITY_RE = re.compile(r"\bsecurity\b|\bthreat\b|prompt injection|secret leak", re.IGNORECASE)
GH_AW_TRACKER = "detection runs"

QUESTION_GH_AW = (
    "The gh-aw bot reports are open while the workflows they report on are still enabled in the "
    "repository, so policy cannot close them. Disable or delete the gh-aw steward-build and "
    "steward-verify workflows, then close the reports?"
)
QUESTION_GH_AW_OPTIONS = ("disable-then-close", "keep-open", "defer")
GATE_OPTIONS = ("accept", "reject", "defer")
MISMATCH_OPTIONS = ("title-suite", "payload-suite", "defer")
ALIAS_OPTIONS = ("same-skill", "different-skill", "defer")


def sha256Text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def questionId(text: str) -> str:
    return "Q-" + sha256Text(text)[:8]


def manifestDigest(manifest: Mapping[str, Any]) -> str:
    body = {key: value for key, value in manifest.items() if key != "manifestSha256"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256Text(canonical)


def ev(kind: str, ref: str, sha: str | None, detail: str) -> dict:
    return {"type": kind, "ref": ref, "sha256": sha, "detail": detail}


def suiteRepo(suite: str | None) -> str | None:
    if suite is None:
        return None
    return suite[len(SUITE_PREFIX):] if suite.startswith(SUITE_PREFIX) else suite


def isConstantFalse(value: Any) -> bool:
    if value is False:
        return True
    return isinstance(value, str) and value.strip() in ("false", "${{ false }}", "${{false}}")


def probeWorkflow(root: Path, relPath: str) -> dict:
    """Read one workflow file from the checkout and decide whether it provably cannot run.

    Provable means every job carries a literal-false ``if:`` gate. Anything else, including
    a missing file, is unproven. Read-only.
    """
    result: dict[str, Any] = {"path": relPath, "sha256": None, "proven": False, "reasons": []}
    if "/" in relPath or not relPath.endswith((".yml", ".yaml")):
        result["reasons"].append("not-a-runnable-yaml-name")
        return result
    target = root / WORKFLOW_DIR / relPath
    if not target.is_file():
        result["reasons"].append("file-missing")
        return result
    raw = target.read_bytes()
    result["sha256"] = hashlib.sha256(raw).hexdigest()
    try:
        data = yaml.safe_load(raw.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError):
        result["reasons"].append("yaml-error")
        return result
    jobs = data.get("jobs") if isinstance(data, dict) else None
    if not isinstance(jobs, dict) or not jobs:
        result["reasons"].append("no-jobs")
        return result
    if all(isinstance(job, dict) and isConstantFalse(job.get("if")) for job in jobs.values()):
        result["proven"] = True
        result["reasons"].append("every-job-gated-false")
    else:
        result["reasons"].append("job-may-run")
    return result


def workflowProbesFor(root: Path, census: Census, policy: HygienePolicy) -> dict[str, dict]:
    """Probe every workflow that policy or an open gh-aw report names, keyed by bare file name."""
    names = {entry.rsplit("/", 1)[-1] for entry in policy.a5Disabled}
    for row in census.openIssues():
        if isinstance(row.get("title"), str) and row["title"].startswith("[aw]"):
            names.update(workflowRunnables(row.get("body") or ""))
    return {name: probeWorkflow(root, name) for name in sorted(names)}


def workflowRunnables(body: str) -> list[str]:
    """Runnable workflow files named by a report body. A gh-aw ``.md`` source maps to its ``.lock.yml``."""
    names = set()
    for name in WORKFLOW_REF_RE.findall(body or ""):
        names.add(name[:-3] + ".lock.yml" if name.endswith(".md") else name)
    return sorted(names)


class Draft:
    """Working state for one census item before it becomes a manifest entry."""

    def __init__(self, identity: Identity, row: dict):
        self.identity = identity
        self.number = identity.number
        self.kind = identity.kind
        self.key = identity.key
        self.suite = identity.suite
        self.parent = identity.parent if identity.kind == "child" else None
        self.row = row
        self.canonical: int | None = None
        self.state = STATE_ACTIONABLE
        self.authority = AUTH_NONE
        self.ruleId: str | None = None
        self.stateReason: str | None = None
        self.duplicateOf: int | None = None
        self.evidence: list[dict] = []
        self.unknowns: list[str] = []
        self.notProven: list[str] = []
        self.dependencies: list[int] = []
        self.confidence = "high"
        self.questions: list[str] = []
        self.proofRule: str | None = None
        self.forcedC = False
        self.a1Ok = False
        self.exact: NamedRecord | None = None


class Context:
    def __init__(self, census: Census, registry: RegistryIndex, policy: HygienePolicy, workflowDisabled: Mapping[str, dict] | None):
        self.census = census
        self.registry = registry
        self.policy = policy
        self.workflowDisabled = dict(workflowDisabled or {})
        self.drafts: dict[int, Draft] = {}
        self.questions: dict[str, dict] = {}
        self.graph: Graph | None = None
        self.closedSuite: dict[int, str] = {}
        self.mergedSyncs: list[dict] = []


def snapshot(row: dict) -> dict:
    return {
        "state": row.get("state"),
        "title": row.get("title"),
        "updatedAt": row.get("updatedAt"),
        "bodySha256": row.get("bodySha256"),
        "labels": sorted(labelNames(row)),
    }


def original(identity: Identity, row: dict) -> dict:
    candidate: dict[str, Any] = {}
    if identity.kind == "child":
        candidate = {"suggestedId": identity.candidateId, "evidenceUrl": identity.evidenceUrl, "umbrella": identity.parent}
    elif identity.kind in ("umbrella", "bootstrap"):
        candidate = {
            "skillId": suiteRepo(identity.suite),
            "newVersion": identity.version,
            "componentAdds": list((identity.payload or {}).get("componentAdds") or []),
        }
    elif identity.kind == "botreport":
        candidate = {"titleHash": identity.titleHash}
    return {"title": row.get("title"), "labels": sorted(labelNames(row)), "bodySha256": row.get("bodySha256"), "candidate": candidate}


def addQuestion(ctx: Context, draft: Draft, text: str, options: tuple[str, ...], recommendation: str | None = None, basis: str = "no basis for an opinion", kind: str = "generic", urlEqual: bool = False) -> None:
    meta = ctx.questions.setdefault(text, {"options": list(options), "affected": set(), "kind": kind, "allUrlEqual": True, "recommendation": recommendation, "basis": basis})
    meta["affected"].add(draft.number)
    meta["allUrlEqual"] = meta["allUrlEqual"] and urlEqual
    draft.questions.append(text)


# ----------------------------------------------------------------- children

def linkDifferences(record: NamedRecord, intake: GithubRef) -> list[str]:
    """Which parts of the registry claim differ from the intake evidence. The git ref is ignored.

    The repo the registry claims is ``upstream.repo`` when declared (a declared upstream must
    agree with the evidence, so a contradiction is never proof), otherwise the ``links.github``
    repo. The path always comes from ``links.github``. Repo and path are compared exactly once
    ``parseGithubUrl`` has folded ``tree/`` to ``blob/`` and dropped a trailing slash, query and
    fragment. An empty list means the same repo and path at any ref. It does not mean the same
    file: the ref/path split must also pass ``refSplitTrusted``, which the caller checks.
    """
    claimedRepo = record.upstreamRepo if record.upstreamRepo is not None else record.github.repo
    found: list[str] = []
    if claimedRepo != intake.repo:
        found.append("registry-repo-differs")
    if record.github.path != intake.path:
        found.append("registry-path-differs")
    return found


def linkProofDetail(record: NamedRecord, intake: GithubRef) -> str:
    """Evidence detail for a proven A1 link. Called only when the A1 proof holds (no differences, trusted ref split)."""
    if record.github.blobUrl() == intake.blobUrl():
        return "links.github equals the evidence URL"
    parts: list[str] = []
    if record.github.repo != intake.repo:
        parts.append("upstream repo and path match the evidence URL")
    if record.github.ref != intake.ref:
        parts.append(f"ref-differs: registry={record.github.ref} intake={intake.ref}")
    return "; ".join(parts)


def evaluateChild(ctx: Context, draft: Draft) -> None:
    """Rule A1 (``A1-child-curated``): the exact suggested-id record curates the same file as the intake.

    Proof needs a readable, non-draft record under the same contributor handle whose registry
    claim names the same repo and the same path as the intake evidence URL. The git ref is not
    part of the match, so a pinned tag or commit against ``main`` still proves A1 and is recorded
    as ``ref-differs``. That ref-free match is sound only when both ref/path splits are trusted
    (``refSplitTrusted``): a slash-containing branch ref on either side leaves ``ref-split-ambiguous``
    and the child falls to B. Any other difference, a draft or missing status, or an unreadable
    record keeps the child out of A (B, or C for an alias candidate).
    """
    identity = draft.identity
    unknownReasons = [reason for reason in identity.reasons if reason not in ORPHAN_REASONS]
    orphanReasons = [reason for reason in identity.reasons if reason in ORPHAN_REASONS]
    draft.unknowns.extend(sorted(unknownReasons))
    draft.notProven.extend(f"orphan:{reason}" for reason in orphanReasons)
    candidate = identity.candidateId
    parts = splitId(candidate) if candidate else None
    if parts is None:
        draft.unknowns.append("candidate-id-malformed")
        draft.state = STATE_AMBIGUOUS
        return
    if ctx.registry.unreadableNear(candidate):
        draft.state = STATE_NOT_EVALUATED
        draft.unknowns.append("registry-unreadable:" + candidate)
        return

    owner, slug = parts
    record = ctx.registry.byId(candidate)
    draft.exact = record
    evidenceRef = parseGithubUrl(identity.evidenceUrl)
    failures: list[str] = []
    if identity.evidenceUrl is None:
        failures.append("evidence-url-missing")
    elif evidenceRef is None:
        failures.append("evidence-url-not-github-file")
    if record is None:
        failures.append("no-exact-registry-record")
    else:
        draft.evidence.append(ev("registry", record.path, record.sha256, "exact suggested-id record"))
        if record.status is None:
            failures.append("registry-status-missing")
        elif record.status == "draft":
            failures.append("registry-draft")
        if record.contributor != owner:
            failures.append("contributor-handle-differs")
        if record.github is None:
            failures.append("registry-link-missing")
        elif evidenceRef is not None:
            differences = linkDifferences(record, evidenceRef)
            if differences:
                failures.append("registry-link-differs")
                failures.extend(differences)
            if not refSplitTrusted(record.github, evidenceRef):
                failures.append("ref-split-ambiguous")
                draft.evidence.append(ev("registry", record.github.blobUrl(), None, f"ref split ambiguous against evidence {identity.evidenceUrl}"))
                draft.evidence.append(ev("issue", f"#{draft.number}", None, f"evidence {identity.evidenceUrl}"))
    if draft.unknowns:
        failures.append("unknown-facts")
    if orphanReasons:
        failures.append("orphan-child")

    if record is not None and not failures:
        draft.a1Ok = True
        draft.proofRule = RULE_A1
        for entry in draft.evidence:
            if entry["type"] == "registry" and entry["ref"] == record.path:
                entry["detail"] = linkProofDetail(record, evidenceRef)
        if record.github.blobUrl() != evidenceRef.blobUrl():
            draft.evidence.append(ev("registry", record.github.blobUrl(), None, f"links.github of {record.path}"))
        if identity.evidenceUrl:
            draft.evidence.append(ev("issue", f"#{draft.number}", None, f"evidence {identity.evidenceUrl}"))
        return
    draft.notProven.extend(failures)
    if record is not None:
        draft.state = STATE_AMBIGUOUS
        draft.confidence = "medium"
        return
    aliases = ctx.registry.aliasCandidates(candidate)
    if aliases:
        draft.state = STATE_AWAITING
        draft.authority = AUTH_C
        draft.confidence = "medium"
        for alias in aliases:
            draft.evidence.append(ev("registry", alias.path, alias.sha256, "alias candidate: same slug under another handle"))
            sameHandle = normalizeHandle(alias.contributor) == normalizeHandle(owner)
            aliasRef = alias.github
            urlMatch = bool(aliasRef and evidenceRef and aliasRef.blobUrl() == evidenceRef.blobUrl())
            if sameHandle:
                text = (
                    f'Do child intakes under the contributor handle "{owner}" name the same skills as the registry '
                    f'records under the handle "{alias.contributor}"? Rule on this handle pair.'
                )
                addQuestion(ctx, draft, text, ALIAS_OPTIONS, kind="alias", urlEqual=urlMatch)
            else:
                text = f"Is the registry record {alias.id} the same skill as the child intake candidate {candidate}?"
                addQuestion(ctx, draft, text, ALIAS_OPTIONS, kind="alias", urlEqual=urlMatch)
        return
    draft.state = STATE_ACTIONABLE


def resolveDuplicates(ctx: Context) -> None:
    for key, numbers in sorted(ctx.graph.duplicates.items()):
        members = [ctx.drafts[number] for number in numbers if number in ctx.drafts and ctx.drafts[number].kind == "child"]
        if len(members) < 2:
            continue
        canonical = members[0]
        canonicalClosable = canonical.a1Ok and ctx.policy.ruleEnabled(RULE_A1)
        for member in members[1:]:
            orphan = any(item.startswith("orphan") for item in member.notProven)
            if member.a1Ok or member.unknowns or orphan:
                continue
            if canonical.unknowns or canonicalClosable:
                member.notProven.append("canonical-not-stable")
                continue
            evidenceMember = parseGithubUrl(member.identity.evidenceUrl)
            evidenceCanon = parseGithubUrl(canonical.identity.evidenceUrl)
            if evidenceMember is None or evidenceCanon is None or evidenceMember.blobUrl() != evidenceCanon.blobUrl():
                member.notProven.append("evidence-url-differs-from-canonical")
                continue
            member.state = STATE_DUPLICATE
            member.proofRule = RULE_A4
            member.canonical = canonical.number
            member.duplicateOf = canonical.number
            member.evidence.append(ev("issue", f"#{canonical.number}", None, "lower-numbered open child with the same key and evidence URL stays canonical"))
            member.confidence = "proven"


# ----------------------------------------------------------------- umbrellas and bootstrap

def mergedSyncFor(ctx: Context, repoId: str, version: str) -> dict | None:
    for row in ctx.mergedSyncs:
        title = row.get("title") if isinstance(row.get("title"), str) else ""
        if title.startswith("[upstream sync]") and repoId in title and version in title:
            return row
    return None


def evaluateUmbrella(ctx: Context, draft: Draft) -> None:
    identity = draft.identity
    draft.dependencies = sorted(ctx.graph.children.get(draft.number, ()))
    draft.unknowns.extend(sorted(identity.reasons))
    for reason in identity.reasons:
        if reason.startswith(MISMATCH_PREFIX):
            titled, payloaded = reason[len(MISMATCH_PREFIX):].split("!=", 1)
            text = (
                f'The umbrella title names suite "{titled}" but its payload names suite "{payloaded}". '
                "Which suite key is canonical for this umbrella?"
            )
            addQuestion(ctx, draft, text, MISMATCH_OPTIONS)
            draft.forcedC = True
    labels = labelNames(draft.row)
    if "skip-child-gate" in labels and draft.dependencies:
        repo = suiteRepo(identity.suite) or "unknown"
        text = (
            f'An umbrella for suite "{repo}" was approved with skip-child-gate while child intakes remain open. '
            "Accept that approval as recorded, reject it, or defer?"
        )
        addQuestion(ctx, draft, text, GATE_OPTIONS)
        draft.forcedC = True
    if draft.forcedC:
        draft.state = STATE_AWAITING
        draft.authority = AUTH_C
        draft.confidence = "medium"
        return

    umbrellas = ctx.graph.suites.get(identity.suite or "", ())
    newest = umbrellas[-1] if umbrellas else None
    repoId = suiteRepo(identity.suite)
    failures: list[str] = []
    if draft.unknowns:
        failures.append("unknown-facts")
    if draft.dependencies:
        failures.append(f"open-children:{len(draft.dependencies)}")
    if newest != draft.number:
        failures.append("newer-umbrella-open")
    if identity.version is None or repoId is None:
        failures.append("version-or-suite-unknown")

    suiteRecords = [entry for entry in ctx.registry.unreadable if entry.pathId == repoId]
    if repoId and suiteRecords:
        draft.state = STATE_NOT_EVALUATED
        draft.unknowns.append("registry-unreadable:" + repoId)
        return
    record = ctx.registry.byId(repoId) if repoId else None
    if record is None:
        failures.append("suite-record-missing")
    else:
        draft.evidence.append(ev("registry", record.path, record.sha256, "suite record"))
        if record.installable is False:
            failures.append("suite-frozen")
        versionMatch = record.upstreamVersion is not None and record.upstreamVersion == identity.version
        sync = mergedSyncFor(ctx, repoId, identity.version) if repoId and identity.version else None
        if sync is not None:
            draft.evidence.append(ev("pr", f"#{sync['number']}", sync.get("bodySha256"), "merged upstream sync PR for this version"))
        if not (versionMatch or sync is not None):
            failures.append("registry-version-differs")

    if not failures:
        draft.proofRule = RULE_A2
        draft.confidence = "proven"
        return
    draft.notProven.extend(failures)

    if newest is not None and newest != draft.number and a3Ok(ctx, draft, umbrellas):
        draft.proofRule = RULE_A3
        draft.canonical = newest
        draft.confidence = "proven"
        draft.evidence.append(ev("issue", f"#{newest}", ctx.drafts[newest].row.get("bodySha256"), "newer open umbrella of the same suite lists every open child"))
        return
    draft.state = STATE_AMBIGUOUS if draft.unknowns else STATE_ACTIONABLE
    draft.confidence = "medium" if draft.unknowns else "high"


def a3Ok(ctx: Context, draft: Draft, umbrellas: tuple[int, ...]) -> bool:
    newestNumber = umbrellas[-1]
    newer = ctx.drafts[newestNumber]
    reasons: list[str] = []
    if newer.unknowns:
        reasons.append("superseder-unknown-facts")
    if draft.identity.version is None or newer.identity.version is None:
        reasons.append("version-unknown")
    elif compareVersions(newer.identity.version, draft.identity.version) <= 0:
        reasons.append("superseder-not-newer")
    adds = list((draft.identity.payload or {}).get("componentAdds") or []) if draft.identity.payload else None
    newerAdds = set((newer.identity.payload or {}).get("componentAdds") or []) if newer.identity.payload else None
    if adds is None or newerAdds is None:
        reasons.append("component-adds-unknown")
    children = [ctx.drafts[number] for number in ctx.graph.children.get(draft.number, ())]
    resolvedSlugs = {child.identity.slug for child in children if child.a1Ok}
    if adds is not None and newerAdds is not None:
        unresolved = [slug for slug in adds if slug not in resolvedSlugs]
        missing = sorted(set(unresolved) - newerAdds)
        if missing:
            reasons.append("superseder-lacks-adds:" + ",".join(missing))
    listed = set(PAYLOAD_LIST_RE.findall(newer.row.get("body") or ""))
    refs = set(newer.identity.childRefs)
    for child in children:
        if child.a1Ok:
            continue
        if child.identity.slug not in listed and child.number not in refs:
            reasons.append(f"not-listed-in-superseder:{child.number}")
    if reasons:
        draft.notProven.extend(reasons)
        return False
    draft.evidence.append(ev("policy", "founder/steward/POLICY.yaml", None, "issueHygiene.enabledRules"))
    return True


def evaluateBootstrap(ctx: Context, draft: Draft) -> None:
    draft.unknowns.extend(sorted(draft.identity.reasons))
    draft.state = STATE_AMBIGUOUS if draft.unknowns else STATE_ACTIONABLE
    draft.authority = AUTH_NONE
    draft.confidence = "medium" if draft.unknowns else "high"


# ----------------------------------------------------------------- bot reports

def evaluateBot(ctx: Context, draft: Draft) -> None:
    row = draft.row
    title = row.get("title") if isinstance(row.get("title"), str) else ""
    body = row.get("body") if isinstance(row.get("body"), str) else ""
    labels = labelNames(row)
    normal = re.sub(r"^\[aw\]\s*", "", title, flags=re.IGNORECASE).strip().lower()
    failures: list[str] = []
    if normal == GH_AW_TRACKER:
        failures.append("detection-runs-tracker")
    if any("security" in label.lower() for label in labels) or "security" in title.lower():
        failures.append("security-label-or-title")
    if SECURITY_RE.search(body):
        failures.append("security-finding-markers")
    runnables = workflowRunnables(body)
    if not runnables:
        failures.append("no-workflow-reference")
    for runnable in runnables:
        if f"{WORKFLOW_DIR}/{runnable}" not in ctx.policy.a5Disabled:
            failures.append(f"workflow-not-listed:{runnable}")
        probe = ctx.workflowDisabled.get(runnable)
        if probe is None or not probe.get("proven"):
            failures.append(f"workflow-not-proven-disabled:{runnable}")
        else:
            draft.evidence.append(ev("workflow", f"{WORKFLOW_DIR}/{runnable}", probe.get("sha256"), ",".join(probe.get("reasons", []))))
    if draft.unknowns:
        failures.append("unknown-facts")
    if not failures:
        draft.proofRule = RULE_A5
        draft.confidence = "proven"
        return
    draft.notProven.extend(failures)
    draft.forcedC = True
    draft.state = STATE_AWAITING
    draft.authority = AUTH_C
    draft.confidence = "medium"
    addQuestion(ctx, draft, QUESTION_GH_AW, QUESTION_GH_AW_OPTIONS)


# ----------------------------------------------------------------- finalize

def finalize(ctx: Context, draft: Draft) -> None:
    if draft.state == STATE_NOT_EVALUATED:
        draft.authority = AUTH_NONE
        return
    if draft.forcedC:
        return
    if draft.proofRule is not None and not draft.unknowns:
        rule = draft.proofRule
        draft.ruleId = rule
        draft.state = RULE_STATE[rule]
        if ctx.policy.ruleEnabled(rule):
            draft.authority = AUTH_A
            draft.confidence = "proven"
        else:
            draft.authority = AUTH_B
            draft.ruleId = None
            draft.notProven.append(f"rule-disabled:{rule}")
            draft.confidence = "high"
        if rule == RULE_A4:
            draft.duplicateOf = draft.canonical
        return
    if draft.kind == "child" and draft.authority == AUTH_NONE:
        draft.authority = AUTH_B
    elif draft.kind == "umbrella" and draft.authority == AUTH_NONE:
        draft.authority = AUTH_B


# ----------------------------------------------------------------- batches and questions

def batches(ctx: Context) -> list[dict]:
    bySuite: dict[str, list[str]] = {}
    unbatched: list[str] = []
    for number in sorted(ctx.drafts):
        draft = ctx.drafts[number]
        if draft.kind == "child" and draft.authority == AUTH_B:
            suite = draft.suite or ctx.closedSuite.get(draft.parent)
            if suite is None:
                unbatched.append(draft.key)
            else:
                bySuite.setdefault(suite, []).append(draft.key)
        elif draft.kind == "umbrella" and draft.authority == AUTH_B and draft.suite:
            bySuite.setdefault(draft.suite, [])
    batches = []
    for suite in sorted(bySuite):
        umbrellas = ctx.graph.suites.get(suite, ())
        classB = sorted(bySuite[suite])
        batches.append({"suite": suiteRepo(suite), "umbrella": umbrellas[-1] if umbrellas else None, "classB": classB, "size": len(classB)})
    if unbatched:
        classB = sorted(unbatched)
        batches.append({"suite": None, "umbrella": None, "classB": classB, "size": len(classB)})
    return batches


def questionList(ctx: Context) -> list[dict]:
    out = []
    for text, meta in ctx.questions.items():
        recommendation = meta["recommendation"]
        basis = meta["basis"]
        if meta["kind"] == "alias" and meta["allUrlEqual"] and meta["affected"]:
            recommendation = "same-skill"
            basis = "registry links.github equals each child evidence URL; only the contributor handle differs"
        out.append({
            "id": questionId(text),
            "question": text,
            "affected": sorted(meta["affected"]),
            "options": meta["options"],
            "recommendation": recommendation,
            "basis": basis,
        })
    return sorted(out, key=lambda item: (item["id"], item["question"]))


def itemOut(ctx: Context, draft: Draft) -> dict:
    closable = draft.state in CLOSABLE_STATES and draft.proofRule is not None
    stateReason = RULE_STATE_REASON[draft.proofRule] if closable else None
    action = "close" if closable else "keep"
    evidence = sorted(draft.evidence, key=lambda item: (item["type"], item["ref"], item["detail"]))
    return {
        "key": draft.key,
        "issue": draft.number,
        "kind": draft.kind,
        "state": draft.state,
        "parent": draft.parent,
        "canonical": draft.canonical if draft.proofRule in (RULE_A3, RULE_A4) else None,
        "authority": draft.authority,
        "ruleId": draft.ruleId,
        "evidence": evidence,
        "proposedTransition": {
            "action": action,
            "stateReason": stateReason if action == "close" else None,
            "duplicateOf": draft.duplicateOf if action == "close" and draft.proofRule == RULE_A4 else None,
        },
        "confidence": draft.confidence,
        "unknowns": sorted(set(draft.unknowns)),
        "notProven": sorted(set(draft.notProven)),
        "dependencies": sorted(draft.dependencies) if draft.kind == "umbrella" else ([draft.parent] if draft.parent is not None else []),
        "suite": suiteRepo(draft.suite),
        "questions": sorted(questionId(text) for text in set(draft.questions)),
        "snapshot": snapshot(draft.row),
        "original": original(draft.identity, draft.row),
    }


def unevaluatedDraft(identity: Identity, row: dict, reasons: list[str]) -> Draft:
    draft = Draft(identity, row)
    draft.state = STATE_NOT_EVALUATED
    draft.authority = AUTH_NONE
    draft.unknowns.extend(reasons)
    draft.confidence = "low"
    return draft


def reconcile(
    census: Census,
    registryIndex: RegistryIndex,
    policy: HygienePolicy,
    now: Any,
    workflowDisabled: Mapping[str, dict] | None = None,
) -> dict:
    """Build the reconciliation manifest. Deterministic: same inputs give the same bytes."""
    document = census.document if isinstance(census.document, dict) else None
    if document is not None:
        status = validateCensus(document, now, policy.maxCensusAgeSeconds)
    else:
        status = census.status
    fetchedAt = document.get("fetchedAt") if document is not None else None
    complete = status.status == COMPLETE

    rowsOpen = [row for row in census.openIssues() if isinstance(row.get("number"), int)] if document is not None else []
    rowsClosed = census.rows("recentlyClosed") if document is not None else []
    ctx = Context(census, registryIndex, policy, workflowDisabled)
    ctx.graph = buildGraph(rowsOpen, rowsClosed)
    ctx.mergedSyncs = [row for row in census.mergedPulls() if isinstance(row.get("number"), int)] if document is not None else []
    for row in rowsClosed:
        if isinstance(row.get("number"), int) and not row.get("isPullRequest"):
            closed = classify(row)
            if closed.kind == "umbrella" and closed.suite and closed.suite != SUITE_PREFIX + "unknown":
                ctx.closedSuite[closed.number] = closed.suite

    rowByNumber = {row["number"]: row for row in rowsOpen}
    if not complete:
        reasons = [f"census:{status.status}"] + list(status.reasons)
        ctx.drafts = {
            number: unevaluatedDraft(identity, rowByNumber.get(number, {}), reasons)
            for number, identity in ctx.graph.items.items()
        }
    else:
        ctx.drafts = {number: Draft(identity, rowByNumber.get(number, {})) for number, identity in ctx.graph.items.items()}
        for number in sorted(ctx.drafts):
            draft = ctx.drafts[number]
            if draft.kind == "child":
                evaluateChild(ctx, draft)
            elif draft.kind == "bootstrap":
                evaluateBootstrap(ctx, draft)
            elif draft.kind == "botreport":
                evaluateBot(ctx, draft)
        resolveDuplicates(ctx)
        for number in sorted(ctx.drafts):
            draft = ctx.drafts[number]
            if draft.kind == "umbrella":
                evaluateUmbrella(ctx, draft)
        for number in sorted(ctx.drafts):
            finalize(ctx, ctx.drafts[number])

    items = [itemOut(ctx, ctx.drafts[number]) for number in sorted(ctx.drafts)]
    unknownCoverage = [f"census:{status.status}"] + list(status.reasons) if not complete else []
    unknownCoverage += [f"registry-unreadable:{entry.path}:{entry.reason}" for entry in registryIndex.unreadable]
    counts = {"A": 0, "B": 0, "C": 0}
    for item in items:
        if item["authority"] in counts:
            counts[item["authority"]] += 1
    kinds = [item["kind"] for item in items]
    stats = {
        "openIssues": len(rowsOpen),
        "botOpen": kinds.count("botreport"),
        "upstreamChildOpen": kinds.count("child"),
        "umbrellaOpen": kinds.count("umbrella"),
        "bootstrapOpen": kinds.count("bootstrap"),
        "classA": counts["A"],
        "classB": counts["B"],
        "classC": counts["C"],
        "untracked": kinds.count("untracked"),
        "notEvaluated": sum(1 for item in items if item["state"] == STATE_NOT_EVALUATED),
    }
    manifest: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "censusFetchedAt": fetchedAt,
        "censusStatus": status.status,
        "coverage": {
            "known": ["botreport", "bootstrap", "child", "umbrella", "untracked"] if complete else [],
            "unknown": sorted(set(unknownCoverage)),
            "notEvaluated": sorted(item["issue"] for item in items if item["state"] == STATE_NOT_EVALUATED),
        },
        "policy": {
            "enabledRules": list(policy.enabledRules),
            "writesEnabled": policy.writesEnabled,
            "maxClosuresPerRun": policy.maxClosuresPerRun,
            "a5Disabled": list(policy.a5Disabled),
        },
        "stats": stats,
        "items": items,
        "batches": batches(ctx) if complete else [],
        "founderQuestions": questionList(ctx) if complete else [],
    }
    manifest["manifestSha256"] = manifestDigest(manifest)
    return manifest


__all__ = [
    "AUTH_A",
    "AUTH_B",
    "AUTH_C",
    "CLOSABLE_STATES",
    "RULE_A1",
    "RULE_A2",
    "RULE_A3",
    "RULE_A4",
    "RULE_A5",
    "SCHEMA_VERSION",
    "WORKFLOW_DIR",
    "manifestDigest",
    "probeWorkflow",
    "questionId",
    "reconcile",
    "workflowProbesFor",
    "workflowRunnables",
]
