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


class CurationOrchestrator:
    """Drive the executable discovery portion of a curation run.

    ``processor`` is an optional test/integration hook accepting a candidate and
    registry path, returning packet/assessment paths and hashes. The normal CLI
    uses Gaia's actual prefill and assessment primitives.
    """

    def __init__(self, run: CurationRun, dry_run: bool = False, *, registry_path: str = ".",
                 save_path: str | Path | None = None,
                 processor: Callable[[dict[str, Any], str], dict[str, Any]] | None = None):
        self.run = run
        self.dry_run = dry_run
        self.registry_path = registry_path
        self.save_path = Path(save_path) if save_path else run.run_dir / "state.json"
        self.processor = processor

    def _save(self):
        self.run.save(self.save_path)

    def run_to_next_gate(self):
        """Advance sequentially through discovery and stop at the human L4 gate."""
        if compactCheckpoint(self.run.checkpoint)["activeBlockers"]:
            return self.run
        if self.run.current_state in GATE_STATES | TERMINAL_STATES:
            return self.run
        if self.run.current_state == "INITIALIZED":
            self.run.current_state = "RESOLVING_URL"
            self._record("resolved input", {"inputUrl": self.run.input_url})
        candidates = self.run.inventory or [self._single_candidate()]
        while self.run.current_state != "AWAITING_L4_REVIEW":
            index = int(self.run.checkpoint.get("inventoryIndex", 0))
            if index >= len(candidates):
                self.run.current_state = "AWAITING_L4_REVIEW"
                self.run.checkpoint["handoff"] = self._handoff()
                self._record("discovery complete; awaiting human L4 review", self.run.checkpoint["handoff"])
                self._save()
                break
            candidate = candidates[index]
            self.run.current_state = "FETCHING_SOURCE"
            self._save()
            try:
                result = self._process(candidate)
            except Exception as exc:
                attempts = self.run.checkpoint.setdefault("attempts", {}).setdefault(str(index), 0) + 1
                self.run.checkpoint["attempts"][str(index)] = attempts
                self.run.checkpoint["lastError"] = {"candidateId": candidate.get("candidateId"), "message": str(exc)}
                self._save()
                raise
            self.run.checkpoint.pop("lastError", None)
            self.run.checkpoint["inventoryIndex"] = index + 1
            self.run.checkpoint.setdefault("results", []).append(result)
            self._record("candidate packet created", result)
            # Atomic checkpoint after each candidate: restart never reprocesses completed rows.
            self.run.current_state = "BUILDING_DISCOVERY_PACKET"
            self._save()
        return self.run

    def retry_candidate(self):
        """Retry only the failed inventory item; completed candidates remain frozen."""
        if not self.run.checkpoint.get("lastError"):
            raise ValueError("There is no failed candidate stage to retry")
        self.run.checkpoint.pop("lastError", None)
        self.run.current_state = "FETCHING_SOURCE"
        self._save()
        return self.run_to_next_gate()

    def _single_candidate(self):
        source_url = self.run.input_url
        candidate_id = self.run.candidate_id or _candidate_id_from_url(source_url)
        return {"candidateId": candidate_id, "namedIdentity": candidate_id,
                "sourceUrl": source_url, "name": self.run.candidate_name or candidate_id.rsplit("/", 1)[-1],
                "description": self.run.candidate_description or f"Candidate discovered from {source_url}"}

    def _process(self, candidate):
        if self.processor:
            return self.processor(candidate, self.registry_path)
        from gaia_cli.prefill import fetchCandidateSource, parseFrontmatter, prefillCommand
        source_url = candidate.get("sourceUrl") or candidate.get("skillFileUrl")
        if not source_url:
            raise ValueError("candidate is missing sourceUrl")
        _, _, content, source_digest = fetchCandidateSource(source_url)
        if content is None:
            raise ValueError(f"Unable to fetch source skill file: {source_url}")
        expected_digest = candidate.get("sourceSha256") or candidate.get("sourceDigest")
        if expected_digest and expected_digest != source_digest:
            raise ValueError(f"Frozen source digest changed for {candidate.get('candidateId')}")
        meta = parseFrontmatter(content)
        name = candidate.get("name") or meta.get("name") or candidate.get("candidateId")
        description = candidate.get("description") or meta.get("description")
        if not isinstance(description, str) or len(description.strip()) < 10:
            raise ValueError("source SKILL.md must provide a description of at least 10 characters")
        args = type("PrefillArgs", (), {})()
        args.candidate_id = candidate.get("candidateId")
        args.name, args.description, args.url = name, description, source_url
        args.source_lane, args.registry = "curate", self.registry_path
        args.allow_stale, args.json, args.stdout = False, False, False
        args.vector = args.suite_role = args.suite_id = args.component_ids = args.fetcher = None
        if prefillCommand(args) != 0:
            raise RuntimeError(f"Gaia prefill failed for {args.candidate_id}")
        slug = args.candidate_id.replace("/", "-")
        packet_path = Path(self.registry_path) / "registry-for-review" / "discovery-packets" / f"{slug}.json"
        packet_bytes = packet_path.read_bytes()
        packet = json.loads(packet_bytes)
        assessment_path = Path(self.registry_path) / "generated-output" / "curation" / f"{slug}.assessment.json"
        if not assessment_path.exists():
            raise RuntimeError(f"Assessment receipt was not created for {args.candidate_id}")
        return {"candidateId": args.candidate_id, "namedIdentity": candidate.get("namedIdentity", args.candidate_id),
                "sourceUrl": source_url, "sourceSha256": source_digest,
                "packetPath": str(packet_path), "packetSha256": hashlib.sha256(packet_bytes).hexdigest(),
                "assessmentPath": str(assessment_path),
                "assessmentSha256": hashlib.sha256(assessment_path.read_bytes()).hexdigest(),
                "genericProposal": packet.get("proposedDisposition")}

    def _handoff(self):
        return {"status": "AWAITING_L4_REVIEW", "batchId": self.run.external_refs.get("batch_id"),
                "intakeIssueNumber": self.run.external_refs.get("intake_issue_number"),
                "intakeIssueUrl": self.run.external_refs.get("intake_issue_url"),
                "downstream": "existing intake only" if self.run.external_refs.get("intake_issue_number") else "human review; no submission"}

    def _record(self, message, details):
        self.run.ledger.append({"state": self.run.current_state, "message": message, "details": details})
        self._save()

    @classmethod
    def print_status(cls, run: CurationRun) -> None:
        print(f"Run: {run.run_id}\nState: {run.current_state}\nURL: {run.input_url or '(none)'}\nDry run: {run.dry_run}")
        checkpoint = compactCheckpoint(run.checkpoint)
        print("Active blockers:")
        for blocker in checkpoint["activeBlockers"]:
            print(f"  {blocker.get('checkId', '(unnamed)')}: {blocker['currentStatus']} — {blocker.get('summary', '')}")
        if not checkpoint["activeBlockers"]: print("  (none)")
        print("Resolved blockers (with evidence):")
        for blocker in checkpoint["resolvedBlockers"]: print(f"  {blocker['checkId']}: {blocker['resolutionEvidence']}")
        print("Source revisions:")
        for source, revision in sorted(checkpoint["sourceRevisions"].items()): print(f"  {source}: {revision}")

    # Preserve the old public transition methods. Only INITIALIZED/discovery are
    # executable; all post-L4 operations remain deliberately unavailable.
    def transition_initialized(self): return self.run_to_next_gate()
    def transition_resolving_url(self): return self.run_to_next_gate()
    def transition_finding_skill_files(self): return self.run_to_next_gate()
    def transition_fetching_source(self): return self.run_to_next_gate()
    def transition_snapshotting_generic(self): return self.run_to_next_gate()
    def transition_prefilling_mapping(self): return self.run_to_next_gate()
    def transition_building_discovery_packet(self): return self.run_to_next_gate()
    def transition_awaiting_l4_review(self): return self.run

    def _blocked(self, state):
        raise RuntimeError(f"{state} is outside the discovery-only curation boundary")

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


def _candidate_id_from_url(url):
    from urllib.parse import urlparse
    path = [part for part in urlparse(url).path.split("/") if part]
    if len(path) < 5 or path[2] != "blob":
        raise ValueError("source URL must identify a GitHub blob file; use --inventory for a frozen batch")
    return f"{path[0]}/{path[1]}/{Path(path[-1]).stem}"


_missing = [state for state in STATE_NAMES if not hasattr(CurationOrchestrator, f"transition_{state.lower()}")]
if _missing: raise RuntimeError(f"Missing curation transition methods: {_missing}")
