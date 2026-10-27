"""Domain plans for the guarded P3 CLI, not an approval or scoring authority.

No CLI option/environment variable loads a provider. Tests replace resolver functions
in their own interpreter; the installed command has no fixture-issuer switch.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

from jsonschema import Draft7Validator, FormatChecker

from gaia_cli import canonicalTransaction as tx
from gaia_cli.commands.dev.helpers import _parse_md, serializeMarkdown
from gaia_cli.evidenceLifecycle import (
    canonical_json_bytes, compute_payload_digest, rehearse_legacy_migration,
    prepare_assertion_transition, prepare_metric_refresh,
)
from gaia_cli.timeline import get_utc_now_iso

FORMAT = "gaia-canonical-plan-v1"
OPERATIONS = {"migrate-evidence", "assertion-transition", "metric-refresh", "reconcile-owner"}


def digest(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def revision(root):
    result = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                            capture_output=True, text=True, timeout=10, check=False)
    if result.returncode:
        raise tx.TransactionError("canonical preparation requires a repository with a committed HEAD")
    return result.stdout.strip()


def schemaPolicy(root):
    """Current schemas only. Adoption of a proposed schema is NOT inferred."""
    return {name: json.loads((root / "registry/schema" / name).read_bytes())
            for name in ("namedSkill.schema.json", "skillTree.schema.json")}


def resolveApproval(root, plan, operation):
    """Trusted deployment seam. No configured genuine issuer exists yet.

    A future reviewed adapter must resolve the actual decision out-of-band, validate
    quorum/revocation/scope, and verify tx.ApprovalRequest against this entire plan.
    Inline approvedBy, operator identity and digests never authenticate a decision.
    """
    return tx.UnavailableApprovalProvider()


def inputContext(root):
    # Actual policy/schema/catalog bytes, not merely caller-supplied version labels.
    paths = [p for p in (root / "registry/schema").rglob("*.json")]
    paths += [root / p for p in ("META.md", "GOVERNANCE.md",
              "founder/YGGDRASIL_IV_RATIFICATION_2026-10-25.md",
              "registry/benchmark-sources.json") if (root / p).exists()]
    paths += list((root / "registry/nodes").rglob("*.json"))
    if sum(p.stat().st_size for p in paths) > 16_777_216:
        raise tx.TransactionError("input snapshot exceeds bounded preparation budget")
    files = {p.relative_to(root).as_posix(): tx._hash(p.read_bytes()) for p in sorted(paths)}
    code = {name: tx._hash((Path(__file__).parent / name).read_bytes()) for name in
            ("canonicalWorkflow.py", "canonicalTransaction.py", "evidenceLifecycle.py", "trustMagnitude.py")}
    return {"repositoryRevision": revision(root), "files": files, "implementation": code}


def checkRequest(request):
    required = {"operation", "skillId", "decisionRef", "evaluationAtUTC", "policyRevision"}
    optional = {"evidenceId", "targetState", "metrics", "observationProvenance"}
    if not isinstance(request, dict) or not required <= request.keys() or request.keys() - required - optional:
        raise tx.TransactionError("request requires operation, skillId, decisionRef, evaluationAtUTC, policyRevision; unknown fields refused")
    if request["operation"] not in OPERATIONS:
        raise tx.TransactionError("unsupported canonical operation")
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9-]*/[a-z0-9][a-z0-9_-]*", request["skillId"]):
        raise tx.TransactionError("canonical workflow requires an exact named skill ID")
    for key in ("decisionRef", "policyRevision"):
        if not isinstance(request[key], str) or not request[key].strip():
            raise tx.TransactionError(f"{key} must be an explicit nonblank reference, not approval")
    when = request["evaluationAtUTC"]
    if not isinstance(when, str) or not when.endswith("Z") or not FormatChecker().conforms(when, "date-time"):
        raise tx.TransactionError("evaluationAtUTC must be an explicit UTC date-time")
    allowed = {"migrate-evidence": set(), "reconcile-owner": set(),
               "assertion-transition": {"evidenceId", "targetState"},
               "metric-refresh": {"evidenceId", "metrics", "observationProvenance"}}[request["operation"]]
    if request.keys() - required != allowed:
        raise tx.TransactionError("operation-specific request fields are missing or extraneous")


def buildPlan(root, request, *, preparedAt=None):
    root = tx._root(root)
    preparedAt = preparedAt or get_utc_now_iso()
    tx.assertNoPendingTransaction(root)
    checkRequest(request)
    context = inputContext(root)
    skillId = request["skillId"]
    owner = skillId.split("/")[0]
    namedRel = f"registry/named/{skillId}.md"
    treeRel = f"skill-trees/{owner}/skill-tree.json"
    namedPath, treePath = tx._target(root, namedRel), tx._target(root, treeRel)
    beforeBytes = {namedRel: namedPath.read_bytes(), treeRel: treePath.read_bytes()}
    named, body = _parse_md(namedPath)
    tree = json.loads(beforeBytes[treeRel])
    if named.get("id") != skillId or named.get("contributor") != owner:
        raise tx.TransactionError("named identity/contributor does not match exact target path")
    if tree.get("userId") != owner:
        raise tx.TransactionError("owner tree identity does not match named contributor")
    matches = [u for u in tree.get("unlockedSkills", []) if u.get("skillId") == skillId]
    if len(matches) != 1 or named.get("level") not in {f"{n}★" for n in range(7)}:
        raise tx.TransactionError("one existing owner unlock and a known canonical level are required; no historical invention")
    # Resolve exact generic context for the reused read-only legacy comparison.
    generic = {}
    for rel in context["files"]:
        if rel.startswith("registry/nodes/"):
            node = json.loads((root / rel).read_bytes())
            if node.get("id") in generic:
                raise tx.TransactionError("duplicate generic identity in input snapshot")
            generic[node.get("id")] = node
    if named.get("genericSkillRef") and named["genericSkillRef"] not in generic:
        raise tx.TransactionError("generic context unresolved; not an authoritative zero")
    after = copy.deepcopy(named)
    nextTree = copy.deepcopy(tree)
    operation = request["operation"]
    summary = {"scoreAuthority": "none; legacy migration comparison is informational, not a pinned published assessment"}
    if operation == "migrate-evidence":
        result = rehearse_legacy_migration(named, request["decisionRef"], generic)
        if not result.score_neutral:
            raise tx.TransactionError("legacy migration comparison was not score-neutral")
        after = result.after_payload
        from gaia_cli.trustMagnitude import computeTrustMagnitude
        catalogPath = root / "registry/benchmark-sources.json"
        catalog = json.loads(catalogPath.read_bytes()) if catalogPath.exists() else {}
        evaluationAt = datetime.fromisoformat(request["evaluationAtUTC"].replace("Z", "+00:00"))
        oldScore = computeTrustMagnitude(named, generic, evaluationAtUTC=evaluationAt, benchmarkCatalog=catalog)
        newScore = computeTrustMagnitude(after, generic, evaluationAtUTC=evaluationAt, benchmarkCatalog=catalog)
        if oldScore != newScore:
            raise tx.TransactionError("pinned migration comparison was not score-neutral")
        summary.update(migratedRows=result.migrated_row_count, legacyBeforeTM=oldScore,
                       legacyAfterTM=newScore, evaluationAtUTC=request["evaluationAtUTC"],
                       scoreAuthority="none; pinned legacy comparison is informational, not a published assessment")
    elif operation == "assertion-transition":
        after = prepare_assertion_transition(named, request["evidenceId"], request["targetState"], request["decisionRef"]).after_payload
        # Proposal core records wall time; make the transaction's proposal provenance replayable.
        for row in after.get("evidence", []):
            if row not in named.get("evidence", []):
                row["decisionHistory"][-1]["proposedAt"] = preparedAt
    elif operation == "metric-refresh":
        after = prepare_metric_refresh(named, request["evidenceId"], request["metrics"],
                    request["decisionRef"], request["observationProvenance"]).after_payload
    else:
        # Current reconciliation, NOT a backfilled award or a new canonical rank.
        nextTree["unlockedSkills"][tree["unlockedSkills"].index(matches[0])]["level"] = named["level"]
    changed = after != named or nextTree != tree
    preparedAt = preparedAt or get_utc_now_iso()
    eventId = digest({"request": request, "context": context, "before": {p: tx._hash(b) for p, b in beforeBytes.items()}})
    if changed:
        event = {"timestamp": preparedAt, "action": operation.replace("-", "_"),
                 "decisionRef": request["decisionRef"], "eventId": eventId,
                 "details": "Prepared canonical decision; no historical approval or award inferred.",
                 "previousValue": compute_payload_digest(named.get("evidence", [])),
                 "newValue": compute_payload_digest(after.get("evidence", []))}
        if operation == "reconcile-owner":
            event.update(previousValue=named["level"], newValue=named["level"])
        after.setdefault("timeline", []).append(copy.deepcopy(event))
        treeEvent = dict(event, skillId=skillId)
        if operation == "reconcile-owner":
            treeEvent["previousValue"] = matches[0].get("level")
        nextTree.setdefault("timeline", []).append(treeEvent)
    changes = []
    if changed:
        changes = [tx.Change(namedRel, serializeMarkdown(after, body).encode("utf-8")),
                   tx.Change(treeRel, (json.dumps(nextTree, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))]
    identity = digest({"request": request, "context": context, "preparedAtUTC": preparedAt})
    plan = tx.prepare(root, operation, identity, changes) if changes else None
    if plan and any(t.before != beforeBytes[t.path] for t in plan.targets):
        raise tx.TransactionError("CAS conflict during preparation")
    if inputContext(root) != context:
        raise tx.TransactionError("input snapshot changed during preparation")
    document = {"format": FORMAT, "root": str(root), "request": copy.deepcopy(request),
                "preparedAtUTC": preparedAt, "context": context, "summary": summary,
                "noChange": not changed, "transactionDigest": plan.digest if plan else None,
                "identity": identity, "targets": [{"path": t.path,
                    "before": base64.b64encode(t.before).decode("ascii"),
                    "after": base64.b64encode(t.after).decode("ascii"),
                    "beforeSha256": tx._hash(t.before), "afterSha256": tx._hash(t.after)} for t in plan.targets] if plan else []}
    document["planDigest"] = digest(document)
    return document


def transactionPlan(document):
    targets = tuple(tx.Target(t["path"], base64.b64decode(t["before"], validate=True),
                              base64.b64decode(t["after"], validate=True)) for t in document["targets"])
    return tx.Plan(document["root"], document["request"]["operation"], document["identity"],
                   targets, document["transactionDigest"])


def validatePlan(root, document):
    root = tx._root(root)
    if document.get("format") != FORMAT or document.get("root") != str(root):
        raise tx.TransactionError("plan format/root mismatch")
    if buildPlan(root, document["request"], preparedAt=document["preparedAtUTC"]) != document:
        raise tx.TransactionError("plan/context/targets changed or are stale; prepare and review a new plan")
    schemas = schemaPolicy(root)
    errors = []
    for item in document["targets"]:
        data = base64.b64decode(item["after"], validate=True).decode("utf-8")
        if item["path"].endswith(".md"):
            import yaml
            instance = yaml.safe_load(data.split("---", 2)[1])
            name = "namedSkill.schema.json"
        else:
            instance, name = json.loads(data), "skillTree.schema.json"
        validator = Draft7Validator(schemas[name], format_checker=FormatChecker())
        for error in validator.iter_errors(instance):
            # Do not dump raw canonical evidence into command errors.
            errors.append(f"{item['path']}: {error.validator} at /{'/'.join(map(str, error.absolute_path))}")
    if errors:
        raise tx.TransactionError("schema adoption held or invalid staged output: " + "; ".join(errors[:12]))
    return document


class BoundApproval:
    def __init__(self, provider, plan):
        self.provider, self.plan = provider, plan

    def verify(self, request):
        # Adapter sees the complete context (not only a caller hash). The tx request
        # also binds exact bytes, root, operation and identity through its digest.
        expected = transactionPlan(self.plan)
        if (request.root != expected.root or request.plan_digest != expected.digest
                or request.context_digest != tx._context(expected, request.operation)):
            return False
        return self.provider.verify(request)


def applyPlan(root, document):
    with tx.canonicalTransactionLock(root):
        validatePlan(root, document)
        if document["noChange"]:
            return {"status": "no-change", "journal": None}
        provider = resolveApproval(Path(root).resolve(), document, "apply")
        journal = tx.apply(transactionPlan(document), BoundApproval(provider, document))
        return {"status": "committed", "journal": journal}


def status(root):
    root = tx._root(root)
    state = root / tx.STATE_DIR
    if (root / ".gaia").is_symlink() or state.is_symlink():
        raise tx.TransactionError("transaction metadata paths cannot be symlinks")
    receipts = []
    if state.exists():
        for path in sorted(state.glob("*.json")):
            if path.is_symlink():
                raise tx.TransactionError("journal cannot be a symlink")
            doc, plan = tx._read_journal(path, root)
            states = {}
            for target in plan.targets:
                p = tx._target(root, target.path)
                current = p.read_bytes() if p.exists() else None
                states[target.path] = "before" if current == target.before else "after" if current == target.after else "outside-edit"
            receipts.append({"journal": str(path), "status": doc["status"], "targets": states,
                             "recovery": "rollback only; requires separately resolved approval" if path.name.endswith(".pending.json") else None})
    return {"receipts": receipts, "pending": any(r["journal"].endswith(".pending.json") for r in receipts)}


def rollbackPlan(root, document, journal):
    with tx._lock(tx._root(root)):
        return _rollbackPlan(root, document, journal)


def _rollbackPlan(root, document, journal):
    # Do NOT re-run forward CAS/validators against a partially applied tree. The
    # exact original plan and current input revisions are separately bound below.
    root = tx._root(root)
    if document.get("format") != FORMAT or document.get("root") != str(root):
        raise tx.TransactionError("rollback plan format/root mismatch")
    body = {k: v for k, v in document.items() if k != "planDigest"}
    if digest(body) != document.get("planDigest") or inputContext(root) != document["context"]:
        raise tx.TransactionError("rollback plan integrity/input revision mismatch")
    path = Path(journal).absolute()
    if path.parent != root / tx.STATE_DIR or path.is_symlink():
        raise tx.TransactionError("rollback journal must be in selected transaction state")
    _, saved = tx._read_journal(path, root)
    if saved != transactionPlan(document):
        raise tx.TransactionError("rollback journal does not bind the supplied plan")
    provider = resolveApproval(root, document, "rollback")
    tx.rollback(root, path, BoundApproval(provider, document))
    return {"status": "rolled-back"}
