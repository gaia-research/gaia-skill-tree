"""Sequential, checkpointed discovery with shared candidate accounting and L4 stop."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from gaia_cli.curation.state import CurationRun, STATE_NAMES
from gaia_cli.curationCheckpoint import compactCheckpoint

GATE_STATES = frozenset({"AWAITING_L4_REVIEW", "AWAITING_EVIDENCE_APPROVAL", "AWAITING_CALIBRATION_APPROVAL"})
TERMINAL_STATES = frozenset({"DONE"})
MAX_CANDIDATES = 5
MAX_ATTEMPTS = 3
MAX_PROCESSING_ATTEMPTS = 10


class CurationOrchestrator:
    """Use existing prefill/assessment primitives; never submit or promote.

    ``processor`` is an internal unit-test/integration hook, not a CLI bypass.
    Semantic mapping remains model-neutral. Default prefill produces advisory
    deferred packets for human review; it never invents an approved mapping.
    """

    def __init__(self, run: CurationRun, dry_run=False, *, registry_path=".",
                 save_path=None, processor: Callable | None = None):
        self.run, self.dry_run, self.registry_path = run, dry_run, registry_path
        self.save_path = Path(save_path) if save_path else run.run_dir / "state.json"
        self.processor = processor

    def _save(self):
        self.run.save(self.save_path)

    def _single_candidate(self):
        cid = self.run.candidate_id or _candidate_id_from_url(self.run.input_url)
        return {"candidateId": cid, "namedIdentity": self.run.named_identity,
                "sourceUrl": self.run.input_url, "name": self.run.candidate_name}

    def _prepare_inventory(self):
        if self.processor and self.run.inventory:
            return self.run.inventory
        from gaia_cli.curation.reconciliation import freezeInventory, reconcileInventory
        from gaia_cli.prefill import buildGenericSnapshot, fetchCandidateSource, parseFrontmatter
        checkpoint = self.run.checkpoint
        if checkpoint.get("inventoryEnvelope"):
            envelope = checkpoint["inventoryEnvelope"]
            reconcileInventory(envelope, [])  # Verify the persisted envelope digest.
            if self.run.inventory != envelope["candidates"]:
                raise ValueError("durable inventory differs from its frozen envelope")
            self._validate_frozen_inventory(envelope["candidates"])
            return self.run.inventory
        declared = checkpoint.setdefault("declaredInventory", copy.deepcopy(self.run.inventory or [self._single_candidate()]))
        if not 1 <= len(declared) <= MAX_CANDIDATES:
            raise ValueError("curate supports 1–5 declared candidates")
        snapshot = checkpoint.get("genericSnapshot") or buildGenericSnapshot(self.registry_path)
        if not snapshot:
            raise ValueError("canonical generic snapshot unavailable; prepare the registry before discovery")
        checkpoint["genericSnapshot"] = snapshot
        prepared = checkpoint.setdefault("preparedSources", {})
        frozen = []
        for original in declared:
            cid = original.get("candidateId")
            url = original.get("sourceUrl") or original.get("skillFileUrl") or original.get("canonicalUrl")
            if not isinstance(cid, str) or not isinstance(url, str):
                raise ValueError("each candidate requires candidateId and exact sourceUrl")
            _candidate_id_from_url(url)  # Validate exact source URL before fetching.
            if cid not in prepared:
                prep_attempts = checkpoint.setdefault("preparationAttempts", {})
                attempts = int(prep_attempts.get(cid, 0))
                if attempts >= MAX_ATTEMPTS or sum(prep_attempts.values()) >= MAX_PROCESSING_ATTEMPTS:
                    checkpoint["budgetExhausted"] = True
                    self._save()
                    raise ValueError(f"source preparation retry budget exhausted for {cid}")
                prep_attempts[cid] = attempts + 1
                self._save()  # Charge preparation before fetching, including failed attempts.
                _, _, content, digest = fetchCandidateSource(url)
                if content is None or digest is None:
                    checkpoint["lastError"] = {"candidateId": cid, "stage": "fetch-source", "attempt": attempts + 1, "message": "source fetch unavailable"}
                    # The declared inventory is durable even when a fetch fails.
                    self._save()
                    raise ValueError(f"source fetch unavailable for {cid}; resume retries this source only")
                expected = original.get("sourceDigest") or original.get("sourceSha256")
                if expected and expected != digest:
                    raise ValueError(f"frozen source changed for {cid}")
                meta = parseFrontmatter(content)
                identity = original.get("namedIdentity") or meta.get("id")
                if not identity and isinstance(meta.get("name"), str) and re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", meta["name"]):
                    identity = f"{urlparse(url).path.split('/')[1]}/{meta['name']}"
                if not identity:
                    raise ValueError(f"exact named identity required for {cid}; provide --named-identity or inventory namedIdentity")
                name, description = meta.get("name"), meta.get("description")
                if not isinstance(name, str) or not name.strip() or not isinstance(description, str) or not description.strip():
                    raise ValueError(f"source SKILL.md for {cid} requires name and description frontmatter")
                revision = _revision_from_url(url)
                claimed = original.get("sourceRevision")
                if claimed and claimed != revision:
                    raise ValueError(f"source revision cannot be independently bound for {cid}")
                prepared[cid] = {"candidateId": cid, "namedIdentity": identity, "sourceRevision": revision,
                    "freshnessRequired": revision is None, "sourceDigest": digest, "canonicalUrl": url,
                    "citedOrigin": original.get("citedOrigin"), "packetInput": {
                        "candidateId": cid, "namedIdentity": identity, "name": name, "description": description,
                        "sourceUrl": url, "sourceContent": content, "packet": {"genericSnapshot": snapshot}}}
                checkpoint.pop("lastError", None)
                self._save()
            frozen.append(prepared[cid])
        envelope = freezeInventory(frozen)
        checkpoint["inventoryEnvelope"] = envelope
        self.run.inventory = copy.deepcopy(envelope["candidates"])
        self._save()
        return self.run.inventory

    def _validate_frozen_inventory(self, candidates):
        from gaia_cli.curation.freshness import sameGenericSnapshot
        from gaia_cli.prefill import buildGenericSnapshot, fetchCandidateSource, parseFrontmatter
        live_snapshot = buildGenericSnapshot(self.registry_path)
        if not live_snapshot:
            raise ValueError("canonical generic snapshot unavailable; prepared inventory cannot resume")
        expected_snapshot = self.run.checkpoint.get("genericSnapshot")
        if not sameGenericSnapshot(expected_snapshot, live_snapshot):
            raise ValueError("live generic catalog differs from frozen source preparation")
        for candidate in candidates:
            packet_input = candidate.get("packetInput")
            content = packet_input.get("sourceContent") if isinstance(packet_input, dict) else None
            if not isinstance(content, str):
                raise ValueError(f"frozen source bytes missing for {candidate.get('candidateId')}")
            digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
            if digest != candidate.get("sourceDigest"):
                raise ValueError(f"frozen source bytes changed for {candidate.get('candidateId')}")
            _, _, live_content, live_digest = fetchCandidateSource(candidate["canonicalUrl"])
            if live_content is None or live_digest != digest:
                raise ValueError(f"live source differs from frozen source for {candidate.get('candidateId')}")
            metadata = parseFrontmatter(content)
            if metadata.get("name") != packet_input.get("name") or metadata.get("description") != packet_input.get("description"):
                raise ValueError(f"frozen packet metadata differs from source bytes for {candidate.get('candidateId')}")

    def run_to_next_gate(self):
        if self.dry_run or self.run.dry_run:
            return self.run
        if compactCheckpoint(self.run.checkpoint)["activeBlockers"] or self.run.current_state in GATE_STATES | TERMINAL_STATES:
            return self.run
        if self.run.current_state == "INITIALIZED":
            self.run.current_state = "RESOLVING_URL"
            self._save()
        candidates = self._prepare_inventory()
        while self.run.current_state != "AWAITING_L4_REVIEW":
            index = int(self.run.checkpoint.get("inventoryIndex", 0))
            attempts = self.run.checkpoint.setdefault("attempts", {})
            if index >= len(candidates):
                return self._pause_l4()
            candidate = candidates[index]
            used = int(attempts.get(str(index), 0))
            if used >= MAX_ATTEMPTS or sum(attempts.values()) >= MAX_PROCESSING_ATTEMPTS:
                self.run.checkpoint["budgetExhausted"] = True
                return self._pause_l4()
            self.run.current_state = "PREFILLING_MAPPING"
            attempts[str(index)] = used + 1
            self._save()  # Charge the attempt before executing external work.
            try:
                result = self._process(candidate)
                result["attempt"] = used + 1
                if result.get("receipt"):
                    result["receipt"]["attempt"] = used + 1
            except Exception as exc:
                self.run.checkpoint["lastError"] = {"candidateId": candidate["candidateId"],
                    "stage": "packet-preparation", "attempt": used + 1, "message": str(exc)}
                self._save()
                raise
            self.run.checkpoint.pop("lastError", None)
            self.run.checkpoint["inventoryIndex"] = index + 1
            self.run.checkpoint.setdefault("results", []).append(result)
            self.run.ledger.append({"state": "BUILDING_DISCOVERY_PACKET", "candidateId": candidate["candidateId"], "packetSha256": result.get("packetSha256")})
            self.run.current_state = "BUILDING_DISCOVERY_PACKET"
            self._save()
        return self.run

    def retry_candidate(self):
        if not self.run.checkpoint.get("lastError"):
            raise ValueError("There is no failed candidate stage to retry")
        index = int(self.run.checkpoint.get("inventoryIndex", 0))
        if self.run.checkpoint.get("attempts", {}).get(str(index), 0) >= MAX_ATTEMPTS:
            raise RuntimeError("candidate retry budget exhausted")
        self.run.current_state = "FETCHING_SOURCE"
        self._save()
        return self.run_to_next_gate()

    def _process(self, candidate):
        if self.processor:
            return self.processor(candidate, self.registry_path)
        from gaia_cli.prefill import prefillCommand, safeCandidateSlug, writePacket
        from gaia_cli.curation.assessment import buildAssessment
        from gaia_cli.prefill import writeAssessmentReceipt
        frozen = candidate["packetInput"]
        # Use only the already fetched bytes, and only for that exact source URL.
        def frozen_fetcher(raw_url):
            return frozen["sourceContent"].encode("utf-8")
        args = type("PrefillArgs", (), {})()
        args.candidate_id, args.name, args.description, args.url = candidate["candidateId"], frozen["name"], frozen["description"], candidate["canonicalUrl"]
        args.source_lane, args.registry, args.fetcher = "source-repository", self.registry_path, frozen_fetcher
        args.allow_stale = args.json = args.stdout = False
        args.vector = args.suite_role = args.suite_id = args.component_ids = None
        if prefillCommand(args) != 0:
            raise RuntimeError(f"Gaia prefill failed for {args.candidate_id}")
        slug = safeCandidateSlug(args.candidate_id)
        packet_path = Path(self.registry_path) / "registry-for-review/discovery-packets" / f"{slug}.json"
        packet = json.loads(packet_path.read_bytes())
        packet["namedIdentity"] = candidate["namedIdentity"]
        packet_path = Path(writePacket(packet, self.registry_path))
        assessment = buildAssessment(packet, self.registry_path)
        assessment_path = Path(writeAssessmentReceipt(packet, assessment, self.registry_path))
        assessment_bytes = assessment_path.read_bytes()
        assessment_hash = hashlib.sha256(assessment_bytes).hexdigest()
        assessment_relative = assessment_path.resolve().relative_to(Path(self.registry_path).resolve()).as_posix()
        decision = packet["decision"]
        proposal = {"decision": decision["value"]}
        if decision["value"] == "MAP":
            proposal["genericId"] = decision["genericId"]
        elif decision["value"] == "NEW_GENERIC":
            proposal["proposal"] = decision["proposal"]
        outcome = {"DEFER": "deferred", "NOT_A_SKILL": "rejected", "DUPLICATE": "proven-duplicate"}.get(decision["value"], "review-ready")
        packet_hash = hashlib.sha256(packet_path.read_bytes()).hexdigest()
        receipt = {"candidateId": candidate["candidateId"], "taskId": candidate["taskId"],
            "attempt": 1, "inputDigest": candidate["inputDigest"], "outputDigest": packet_hash,
            "packetHash": packet_hash, "packetPath": str(packet_path.relative_to(Path(self.registry_path).resolve())),
            "assessmentPath": assessment_relative, "assessmentSha256": assessment_hash,
            "proposedGeneric": proposal, "outcome": outcome, "reason": decision.get("reasonCode")}
        if outcome == "proven-duplicate":
            dedupe = packet["exactDedupe"]
            receipt["duplicateProof"] = {"targetNamedIdentity": dedupe.get("namedIdentity"), "source": {
                "canonicalUrl": dedupe.get("canonicalUrl"), "contentSha256": dedupe.get("contentSha256")}}
        return {"candidateId": candidate["candidateId"], "namedIdentity": candidate["namedIdentity"],
            "sourceUrl": candidate["canonicalUrl"], "sourceSha256": candidate["sourceDigest"],
            "sourceRevision": candidate["sourceRevision"], "packetPath": str(packet_path), "packetSha256": packet_hash,
            "assessmentPath": str(assessment_path), "assessmentSha256": hashlib.sha256(assessment_path.read_bytes()).hexdigest(),
            "genericProposal": proposal, "receipt": receipt}

    def _reconcile(self):
        from gaia_cli.curation.reconciliation import reconcileInventory
        envelope = self.run.checkpoint.get("inventoryEnvelope")
        if not envelope:
            return {"humanApproved": False, "accounted": False, "decisions": []}
        report = reconcileInventory(envelope, [row["receipt"] for row in self.run.checkpoint.get("results", []) if row.get("receipt")], packetRoot=self.registry_path)
        if self.run.checkpoint.get("budgetExhausted"):
            for row in report["decisions"]:
                if row["outcome"] == "deferred" and row["reason"] == "missing worker receipt":
                    row["reason"] = "processing budget exhausted; explicit deferred candidate"
        return report

    def _pause_l4(self):
        self.run.current_state = "AWAITING_L4_REVIEW"
        self.run.checkpoint["reconciliation"] = self._reconcile()
        refs = self.run.external_refs
        self.run.checkpoint["handoff"] = {"status": "AWAITING_L4_REVIEW", "batchId": refs.get("batch_id"),
            "intakeIssueNumber": refs.get("intake_issue_number"), "intakeIssueUrl": refs.get("intake_issue_url"),
            "downstream": "existing intake only" if refs.get("intake_issue_number") else "human review; no submission"}
        self._save()
        return self.run

    @classmethod
    def print_status(cls, run):
        print(f"Run: {run.run_id}\nState: {run.current_state}\nURL: {run.input_url or '(none)'}\nDry run: {run.dry_run}")
        checkpoint = compactCheckpoint(run.checkpoint)
        print("Active blockers:")
        for blocker in checkpoint["activeBlockers"]:
            print(f"  {blocker.get('checkId', '(unnamed)')}: {blocker['currentStatus']} — {blocker.get('summary', '')}")
        if not checkpoint["activeBlockers"]:
            print("  (none)")
        print("Resolved blockers (with evidence):")
        for blocker in checkpoint["resolvedBlockers"]:
            print(f"  {blocker['checkId']}: {blocker['resolutionEvidence']}")
        print("Source revisions:")
        for source, revision in sorted(checkpoint["sourceRevisions"].items()):
            print(f"  {source}: {revision}")
        for row in run.checkpoint.get("reconciliation", {}).get("decisions", []):
            print(f"  {row['candidateId']} [{row['namedIdentity']}]: {row['outcome']} — {row.get('reason', '')}")

    def _blocked(self, state):
        raise RuntimeError(f"{state} is outside the discovery-only curation boundary")


def _candidate_id_from_url(url):
    parsed = urlparse(url)
    path = parsed.path.strip("/").split("/")
    if parsed.scheme != "https" or parsed.netloc not in {"github.com", "www.github.com"} or len(path) < 5 or path[2] != "blob" or path[-1] != "SKILL.md" or any(part in {"", ".", ".."} for part in path):
        raise ValueError("source must be an exact GitHub SKILL.md blob URL; repository-wide discovery requires a declared inventory")
    return "/".join(path[:2] + path[4:])


def _revision_from_url(url):
    _candidate_id_from_url(url)
    revision = urlparse(url).path.strip("/").split("/")[3]
    return revision if re.fullmatch(r"[0-9a-f]{40}", revision) else None


# Preserve the old transition API without implementing downstream governance.
def _discovery_transition(self):
    return self.run_to_next_gate()


for _state in STATE_NAMES:
    if _state in {"INITIALIZED", "RESOLVING_URL", "FINDING_SKILL_FILES", "FETCHING_SOURCE", "SNAPSHOTTING_GENERIC", "PREFILLING_MAPPING", "BUILDING_DISCOVERY_PACKET"}:
        setattr(CurationOrchestrator, f"transition_{_state.lower()}", _discovery_transition)
    elif _state in {"AWAITING_L4_REVIEW", "DONE"}:
        setattr(CurationOrchestrator, f"transition_{_state.lower()}", lambda self: self.run)
    else:
        setattr(CurationOrchestrator, f"transition_{_state.lower()}", lambda self, state=_state: self._blocked(state))
