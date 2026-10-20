"""Sequential discovery-to-packet curation workflow; always stops at L4."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from gaia_cli.curation.state import CurationRun, STATE_NAMES
from gaia_cli.curationCheckpoint import compactCheckpoint

GATE_STATES = frozenset({"AWAITING_L4_REVIEW", "AWAITING_EVIDENCE_APPROVAL", "AWAITING_CALIBRATION_APPROVAL"})
TERMINAL_STATES = frozenset({"DONE"})
MAX_CANDIDATES = 5
MAX_ATTEMPTS = 3
MAX_PROCESSING_ATTEMPTS = 10


class CurationOrchestrator:
    """Prepare deterministic, source-frozen packets and stop for human L4."""

    def __init__(self, run: CurationRun, dry_run: bool = False, *, registry_path: str = ".",
                 save_path: str | Path | None = None,
                 processor: Callable[[dict[str, Any], str], dict[str, Any]] | None = None):
        self.run, self.dry_run, self.registry_path = run, dry_run, registry_path
        self.save_path = Path(save_path) if save_path else run.run_dir / "state.json"
        self.processor = processor

    def _save(self): self.run.save(self.save_path)

    def _prepare_inventory(self):
        """Fetch bounded sources first, then freeze immutable input before processing."""
        # The explicit processor hook is retained for narrow orchestration unit tests;
        # production always follows the frozen source + real prefill path below.
        if self.processor and self.run.inventory:
            return self.run.inventory
        from gaia_cli.curation.reconciliation import freezeInventory
        from gaia_cli.prefill import fetchCandidateSource, parseFrontmatter
        candidates = self.run.inventory or [self._single_candidate()]
        if not 1 <= len(candidates) <= MAX_CANDIDATES:
            raise ValueError("curate supports 1–5 frozen candidates")
        if candidates and candidates[0].get("contractVersion") == "curation-inventory-v1":
            return candidates
        frozen_inputs, source_info = [], {}
        for row in candidates:
            url = row.get("sourceUrl") or row.get("skillFileUrl") or row.get("canonicalUrl")
            cid = row.get("candidateId")
            if not isinstance(url, str) or not cid:
                raise ValueError("each candidate requires candidateId and exact GitHub blob sourceUrl")
            _, raw_url, content, digest = fetchCandidateSource(url)
            if content is None:
                raise ValueError(f"Unable to fetch exact GitHub SKILL.md source: {url}")
            expected = row.get("sourceDigest") or row.get("sourceSha256")
            if expected and expected != digest:
                raise ValueError(f"Frozen source digest changed for {cid}")
            meta = parseFrontmatter(content)
            name = meta.get("name") or row.get("name") or cid.rsplit("/", 1)[-1]
            desc = meta.get("description") or row.get("description")
            if not isinstance(desc, str) or len(desc.strip()) < 10:
                raise ValueError(f"source SKILL.md for {cid} must provide a description of at least 10 characters")
            identity = row.get("namedIdentity") or meta.get("id") or f"named:{cid}"
            revision = row.get("sourceRevision") or _revision_from_url(url)
            packet_input = {"candidateId": cid, "namedIdentity": identity, "name": name,
                            "description": desc, "sourceUrl": url, "sourceSha256": digest,
                            "sourceContent": content}
            frozen_inputs.append({"candidateId": cid, "namedIdentity": identity,
                                  "sourceRevision": revision, "sourceDigest": digest,
                                  "canonicalUrl": url, "citedOrigin": row.get("citedOrigin"),
                                  "packetInput": packet_input})
            source_info[cid] = {"url": url, "rawUrl": raw_url, "content": content, "digest": digest}
        envelope = freezeInventory(frozen_inputs)
        self.run.inventory = envelope["candidates"]
        self.run.checkpoint["inventoryEnvelope"] = envelope
        self.run.checkpoint["sourceInfo"] = source_info
        self.run.checkpoint["inventoryIndex"] = int(self.run.checkpoint.get("inventoryIndex", 0))
        self._save()
        return self.run.inventory

    def run_to_next_gate(self):
        if compactCheckpoint(self.run.checkpoint)["activeBlockers"] or self.run.current_state in GATE_STATES | TERMINAL_STATES:
            return self.run
        if self.run.current_state == "INITIALIZED":
            self.run.current_state = "RESOLVING_URL"
            self._record("resolved input", {"inputUrl": self.run.input_url})
        candidates = self._prepare_inventory()
        while self.run.current_state != "AWAITING_L4_REVIEW":
            index = int(self.run.checkpoint.get("inventoryIndex", 0))
            if index >= len(candidates):
                self.run.current_state = "AWAITING_L4_REVIEW"
                self.run.checkpoint["handoff"] = self._handoff()
                self.run.checkpoint["reconciliation"] = self._reconcile()
                self._record("discovery complete; awaiting human L4 review", self.run.checkpoint["handoff"])
                break
            candidate = candidates[index]
            attempts = self.run.checkpoint.setdefault("attempts", {})
            key = str(index)
            used = int(attempts.get(key, 0))
            total = sum(int(value) for value in attempts.values())
            if used >= MAX_ATTEMPTS or total >= MAX_PROCESSING_ATTEMPTS:
                raise RuntimeError(f"retry budget exhausted for candidate {candidate['candidateId']} (attempts {used}/{MAX_ATTEMPTS}; total {total}/{MAX_PROCESSING_ATTEMPTS})")
            self.run.current_state = "FETCHING_SOURCE"
            self._save()
            attempts[key] = used + 1
            try:
                result = self._process(candidate)
                result["attempt"] = used + 1
            except Exception as exc:
                self.run.checkpoint["lastError"] = {"candidateId": candidate.get("candidateId"), "stage": "packet-preparation", "attempt": used + 1, "message": str(exc)}
                self._save()
                raise
            self.run.checkpoint.pop("lastError", None)
            self.run.checkpoint["inventoryIndex"] = index + 1
            self.run.checkpoint.setdefault("results", []).append(result)
            self._record("candidate packet created", result)
            self.run.current_state = "BUILDING_DISCOVERY_PACKET"
            self._save()
        return self.run

    def retry_candidate(self):
        error = self.run.checkpoint.get("lastError")
        if not error: raise ValueError("There is no failed candidate stage to retry")
        index = int(self.run.checkpoint.get("inventoryIndex", 0))
        if int(self.run.checkpoint.get("attempts", {}).get(str(index), 0)) >= MAX_ATTEMPTS:
            raise RuntimeError("candidate retry budget exhausted")
        self.run.checkpoint.pop("lastError", None)
        self.run.current_state = "FETCHING_SOURCE"
        self._save()
        return self.run_to_next_gate()

    def _single_candidate(self):
        source_url = self.run.input_url
        candidate_id = self.run.candidate_id or _candidate_id_from_url(source_url)
        return {"candidateId": candidate_id, "namedIdentity": f"named:{candidate_id}",
                "sourceUrl": source_url, "name": self.run.candidate_name}

    def _process(self, candidate):
        if self.processor:
            return self.processor(candidate, self.registry_path)
        from gaia_cli.prefill import prefillCommand, safeCandidateSlug
        packet_input = candidate["packetInput"]
        source_url = packet_input["sourceUrl"]
        content = packet_input["sourceContent"]
        def frozen_fetcher(_raw_url): return content.encode("utf-8")
        args = type("PrefillArgs", (), {})()
        args.candidate_id = candidate["candidateId"]
        args.name, args.description, args.url = packet_input["name"], packet_input["description"], source_url
        args.source_lane, args.registry = "source-repository", self.registry_path
        args.allow_stale, args.json, args.stdout = False, False, False
        args.vector = args.suite_role = args.suite_id = args.component_ids = None
        args.fetcher = frozen_fetcher
        if prefillCommand(args) != 0: raise RuntimeError(f"Gaia prefill failed for {args.candidate_id}")
        slug = safeCandidateSlug(args.candidate_id)
        packet_path = Path(self.registry_path) / "registry-for-review" / "discovery-packets" / f"{slug}.json"
        assessment_path = Path(self.registry_path) / "generated-output" / "curation" / f"{slug}.assessment.json"
        packet_bytes = packet_path.read_bytes()
        packet = json.loads(packet_bytes)
        if not assessment_path.is_file(): raise RuntimeError(f"Assessment receipt was not created for {args.candidate_id}")
        packet_hash = hashlib.sha256(packet_bytes).hexdigest()
        assessment_hash = hashlib.sha256(assessment_path.read_bytes()).hexdigest()
        return {"candidateId": args.candidate_id, "namedIdentity": candidate["namedIdentity"],
                "sourceUrl": source_url, "sourceSha256": candidate["sourceDigest"],
                "sourceRevision": candidate["sourceRevision"], "packetPath": str(packet_path),
                "packetSha256": packet_hash, "assessmentPath": str(assessment_path),
                "assessmentSha256": assessment_hash, "genericProposal": packet.get("proposedDisposition"),
                "receipt": {"candidateId": candidate["candidateId"], "taskId": candidate["taskId"],
                            "attempt": 1, "inputDigest": candidate["inputDigest"],
                            "outputDigest": packet_hash, "packetHash": packet_hash,
                            "packetPath": str(packet_path.relative_to(Path(self.registry_path))),
                            "proposedGeneric": packet.get("proposedDisposition"), "outcome": "review-ready"}}

    def _reconcile(self):
        from gaia_cli.curation.reconciliation import reconcileInventory
        envelope = self.run.checkpoint.get("inventoryEnvelope")
        if not envelope:
            return {"humanApproved": False, "accounted": False, "decisions": []}
        return reconcileInventory(envelope,
                                  [row["receipt"] for row in self.run.checkpoint.get("results", []) if row.get("receipt")],
                                  packetRoot=self.registry_path)

    def _handoff(self):
        return {"status": "AWAITING_L4_REVIEW", "batchId": self.run.external_refs.get("batch_id"),
                "intakeIssueNumber": self.run.external_refs.get("intake_issue_number"),
                "intakeIssueUrl": self.run.external_refs.get("intake_issue_url"),
                "downstream": "existing intake only" if self.run.external_refs.get("intake_issue_number") else "human review; no submission"}

    def _record(self, message, details):
        self.run.ledger.append({"state": self.run.current_state, "message": message, "details": details})
        self._save()

    @classmethod
    def print_status(cls, run):
        print(f"Run: {run.run_id}\nState: {run.current_state}\nURL: {run.input_url or '(none)'}\nDry run: {run.dry_run}")
        checkpoint = compactCheckpoint(run.checkpoint)
        print("Active blockers:")
        for blocker in checkpoint["activeBlockers"]: print(f"  {blocker.get('checkId', '(unnamed)')}: {blocker['currentStatus']} — {blocker.get('summary', '')}")
        if not checkpoint["activeBlockers"]: print("  (none)")
        print("Resolved blockers (with evidence):")
        for blocker in checkpoint["resolvedBlockers"]: print(f"  {blocker['checkId']}: {blocker['resolutionEvidence']}")
        print("Source revisions:")
        for source, revision in sorted(checkpoint["sourceRevisions"].items()): print(f"  {source}: {revision}")

    def transition_initialized(self): return self.run_to_next_gate()
    def transition_resolving_url(self): return self.run_to_next_gate()
    def transition_finding_skill_files(self): return self.run_to_next_gate()
    def transition_fetching_source(self): return self.run_to_next_gate()
    def transition_snapshotting_generic(self): return self.run_to_next_gate()
    def transition_prefilling_mapping(self): return self.run_to_next_gate()
    def transition_building_discovery_packet(self): return self.run_to_next_gate()
    def transition_awaiting_l4_review(self): return self.run
    def _blocked(self, state): raise RuntimeError(f"{state} is outside the discovery-only curation boundary")
    def transition_applying_l4_resolution(self): return self._blocked("APPLYING_L4_RESOLUTION")
    def transition_discovering_evidence(self): return self._blocked("DISCOVERING_EVIDENCE")
    def transition_compiling_evidence_lake(self): return self._blocked("COMPILING_EVIDENCE_LAKE")
    def transition_verifying_stars(self): return self._blocked("VERIFYING_STARS")
    def transition_verifying_benchmarks(self): return self._blocked("VERIFYING_BENCHMARKS")
    def transition_auditing_evidence(self): return self._blocked("AUDITING_EVIDENCE")
    def transition_validating_links(self): return self._blocked("VALIDATING_LINKS")
    def transition_building_ingest_plan(self): return self._blocked("BUILDING_INGEST_PLAN")
    def transition_awaiting_evidence_approval(self): return self._blocked("AWAITING_EVIDENCE_APPROVAL")
    def transition_opening_review_branch(self): return self._blocked("OPENING_REVIEW_BRANCH")
    def transition_ingesting_evidence(self): return self._blocked("INGESTING_EVIDENCE")
    def transition_appraising_trust(self): return self._blocked("APPRAISING_TRUST")
    def transition_proposing_calibration(self): return self._blocked("PROPOSING_CALIBRATION")
    def transition_awaiting_calibration_approval(self): return self._blocked("AWAITING_CALIBRATION_APPROVAL")
    def transition_applying_calibration(self): return self._blocked("APPLYING_CALIBRATION")
    def transition_validating_registry(self): return self._blocked("VALIDATING_REGISTRY")
    def transition_done(self): return self.run


def _revision_from_url(url):
    from urllib.parse import urlparse
    parts = [part for part in urlparse(url).path.split("/") if part]
    if len(parts) < 5 or parts[2] != "blob": raise ValueError("source must be an exact GitHub blob URL; repository-wide discovery is not yet supported")
    return parts[3]


def _candidate_id_from_url(url):
    from urllib.parse import urlparse
    path = [part for part in urlparse(url).path.split("/") if part]
    if len(path) < 5 or path[2] != "blob": raise ValueError("source URL must identify an exact GitHub blob file; repo-wide discovery is unsupported; provide --inventory of exact SKILL.md URLs")
    if Path(path[-1]).name.lower() != "skill.md": raise ValueError("source URL must point to SKILL.md")
    return f"{path[0]}/{path[1]}/{Path(path[-2]).name if len(path) > 5 else Path(path[-1]).stem}"


_missing = [state for state in STATE_NAMES if not hasattr(CurationOrchestrator, f"transition_{state.lower()}")]
if _missing: raise RuntimeError(f"Missing curation transition methods: {_missing}")
