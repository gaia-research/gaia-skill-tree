"""State-machine scaffold for `gaia curate`."""

from __future__ import annotations

from gaia_cli.curation.state import CurationRun, STATE_NAMES


GATE_STATES = frozenset(
    {
        "AWAITING_L4_REVIEW",
        "AWAITING_EVIDENCE_APPROVAL",
        "AWAITING_CALIBRATION_APPROVAL",
    }
)
TERMINAL_STATES = frozenset({"DONE"})

# The curate command is currently an orchestration scaffold: only the run ledger
# and gates exist, while workflow transitions are deliberately stubbed.  Pause
# fresh runs here so `gaia curate <url>` persists state and reports scaffold
# status instead of invoking the unimplemented INITIALIZED transition.
SCAFFOLD_PAUSE_STATES = frozenset({"INITIALIZED"})


class CurationOrchestrator:
    """Drive a :class:`CurationRun` through the curate workflow."""

    def __init__(self, run: CurationRun, dry_run: bool = False):
        self.run = run
        self.dry_run = dry_run

    def run_to_next_gate(self):
        """Advance the run until a human gate or terminal state is reached."""
        pause_states = GATE_STATES | TERMINAL_STATES | SCAFFOLD_PAUSE_STATES
        while self.run.current_state not in pause_states:
            method = getattr(self, f"transition_{self.run.current_state.lower()}", None)
            if method is None:
                raise NotImplementedError(
                    f"No transition stub for state {self.run.current_state!r}."
                )
            method()
        return self.run

    @classmethod
    def print_status(cls, run: CurationRun) -> None:
        """Print a compact, human-readable status summary for *run*."""
        print(f"Run: {run.run_id}")
        print(f"State: {run.current_state}")
        print(f"URL: {run.input_url or '(none)'}")
        print(f"Dry run: {run.dry_run}")

    def transition_initialized(self):
        """Move INITIALIZED runs into URL resolution after validating inputs."""
        raise NotImplementedError("INITIALIZED transition is not implemented yet.")

    def transition_resolving_url(self):
        """Resolve the input URL into a canonical GitHub repository or blob URL."""
        raise NotImplementedError("RESOLVING_URL transition is not implemented yet.")

    def transition_finding_skill_files(self):
        """Find candidate SKILL.md files when the input URL names a repository."""
        raise NotImplementedError("FINDING_SKILL_FILES transition is not implemented yet.")

    def transition_fetching_source(self):
        """Fetch the selected source skill file and record immutable provenance."""
        raise NotImplementedError("FETCHING_SOURCE transition is not implemented yet.")

    def transition_snapshotting_generic(self):
        """Snapshot the suggested or matched generic registry node for L4 review."""
        raise NotImplementedError("SNAPSHOTTING_GENERIC transition is not implemented yet.")

    def transition_prefilling_mapping(self):
        """Run deterministic prefill to rank candidate generic mappings."""
        raise NotImplementedError("PREFILLING_MAPPING transition is not implemented yet.")

    def transition_building_discovery_packet(self):
        """Build and persist the discovery packet that human L4 reviews."""
        raise NotImplementedError("BUILDING_DISCOVERY_PACKET transition is not implemented yet.")

    def transition_awaiting_l4_review(self):
        """Resume from the L4 mapping/topology gate once a decision is present."""
        raise NotImplementedError("AWAITING_L4_REVIEW transition is not implemented yet.")

    def transition_applying_l4_resolution(self):
        """Apply the approved L4 resolution without ingesting evidence yet."""
        raise NotImplementedError("APPLYING_L4_RESOLUTION transition is not implemented yet.")

    def transition_discovering_evidence(self):
        """Optionally discover higher-quality evidence for the candidate."""
        raise NotImplementedError("DISCOVERING_EVIDENCE transition is not implemented yet.")

    def transition_compiling_evidence_lake(self):
        """Compile known evidence rows into the evidence data lake artifact."""
        raise NotImplementedError("COMPILING_EVIDENCE_LAKE transition is not implemented yet.")

    def transition_verifying_stars(self):
        """Verify live GitHub stargazer evidence before audit."""
        raise NotImplementedError("VERIFYING_STARS transition is not implemented yet.")

    def transition_verifying_benchmarks(self):
        """Verify benchmark-result rows against registered benchmark sources."""
        raise NotImplementedError("VERIFYING_BENCHMARKS transition is not implemented yet.")

    def transition_auditing_evidence(self):
        """Run adversarial evidence quality checks over the lake."""
        raise NotImplementedError("AUDITING_EVIDENCE transition is not implemented yet.")

    def transition_validating_links(self):
        """Validate source URL liveness for all evidence rows."""
        raise NotImplementedError("VALIDATING_LINKS transition is not implemented yet.")

    def transition_building_ingest_plan(self):
        """Create the proposed evidence ingest plan for human approval."""
        raise NotImplementedError("BUILDING_INGEST_PLAN transition is not implemented yet.")

    def transition_awaiting_evidence_approval(self):
        """Resume from the evidence approval gate once approval is recorded."""
        raise NotImplementedError("AWAITING_EVIDENCE_APPROVAL transition is not implemented yet.")

    def transition_opening_review_branch(self):
        """Create or switch to the review branch for registry mutations."""
        raise NotImplementedError("OPENING_REVIEW_BRANCH transition is not implemented yet.")

    def transition_ingesting_evidence(self):
        """Ingest approved evidence rows through the Gaia CLI mutation path."""
        raise NotImplementedError("INGESTING_EVIDENCE transition is not implemented yet.")

    def transition_appraising_trust(self):
        """Run Trust Magnitude appraisal for affected named skills."""
        raise NotImplementedError("APPRAISING_TRUST transition is not implemented yet.")

    def transition_proposing_calibration(self):
        """Propose star calibration based on Trust Magnitude output."""
        raise NotImplementedError("PROPOSING_CALIBRATION transition is not implemented yet.")

    def transition_awaiting_calibration_approval(self):
        """Resume from calibration approval once an explicit decision exists."""
        raise NotImplementedError("AWAITING_CALIBRATION_APPROVAL transition is not implemented yet.")

    def transition_applying_calibration(self):
        """Apply the approved calibration to registry metadata."""
        raise NotImplementedError("APPLYING_CALIBRATION transition is not implemented yet.")

    def transition_validating_registry(self):
        """Run registry validation and generated-artifact checks."""
        raise NotImplementedError("VALIDATING_REGISTRY transition is not implemented yet.")

    def transition_done(self):
        """No-op terminal transition for completed curation runs."""
        return self.run


_missing = [
    state for state in STATE_NAMES if not hasattr(CurationOrchestrator, f"transition_{state.lower()}")
]
if _missing:
    raise RuntimeError(f"Missing curation transition stubs: {_missing}")
