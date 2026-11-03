"""State-machine scaffold and ledger inspector for `gaia curate`.

Migration Notice:
The 25 nominal workflow transition methods previously declared as
NotImplementedError stubs in this module were an orchestration scaffold, NOT
working automation. Outward-facing ecosystem intelligence and candidate
discovery are canonically owned by Gaia Frontier (`/gaia-frontier`) under the
Founder Frontier Ruling (2026-10-26). Manual, bounded L4-gated curation remains
fully supported through `/gaia-full-pipeline` and `/gaia-consult`.

This module retains the public CLI contracts:
- `CurationOrchestrator.print_status(run)`: status inspection for local ledgers
- `CurationOrchestrator.run_to_next_gate()`: ledger gating and blocker handling
- Ledger persistence and compatibility for historical runs in `.gaia/curation/runs/`
"""

from __future__ import annotations

from gaia_cli.curation.state import CurationRun
from gaia_cli.curationCheckpoint import compactCheckpoint


GATE_STATES = frozenset(
    {
        "AWAITING_L4_REVIEW",
        "AWAITING_EVIDENCE_APPROVAL",
        "AWAITING_CALIBRATION_APPROVAL",
    }
)
TERMINAL_STATES = frozenset({"DONE"})

# The curate command is a paused orchestration scaffold: only the run ledger
# and gates exist. Fresh runs pause at INITIALIZED.
SCAFFOLD_PAUSE_STATES = frozenset({"INITIALIZED"})


class CurationOrchestrator:
    """Drive or inspect a :class:`CurationRun` through the curate workflow."""

    def __init__(self, run: CurationRun, dry_run: bool = False):
        self.run = run
        self.dry_run = dry_run

    def run_to_next_gate(self) -> CurationRun:
        """Advance the run until a human gate or terminal state is reached."""
        if compactCheckpoint(self.run.checkpoint)["activeBlockers"]:
            return self.run
        pause_states = GATE_STATES | TERMINAL_STATES | SCAFFOLD_PAUSE_STATES
        if self.run.current_state not in pause_states:
            raise NotImplementedError(
                f"Transition from state {self.run.current_state!r} is not implemented. "
                "The 25 nominal workflow transitions were an orchestration scaffold, "
                "not working automation. Gaia Frontier (/gaia-frontier) owns outward "
                "discovery, and /gaia-full-pipeline provides manual L4-bounded curation."
            )
        return self.run

    @classmethod
    def print_status(cls, run: CurationRun) -> None:
        """Print a compact, human-readable status summary for *run*."""
        print(f"Run: {run.run_id}")
        print(f"State: {run.current_state}")
        print(f"URL: {run.input_url or '(none)'}")
        print(f"Dry run: {run.dry_run}")
        checkpoint = compactCheckpoint(run.checkpoint)
        print("Active blockers:")
        for blocker in checkpoint["activeBlockers"]:
            print(f"  {blocker.get('checkId', '(unnamed)')}: {blocker['currentStatus']}"
                  f" — {blocker.get('summary', '')}")
        if not checkpoint["activeBlockers"]:
            print("  (none)")
        print("Resolved blockers (with evidence):")
        for blocker in checkpoint["resolvedBlockers"]:
            print(f"  {blocker['checkId']}: {blocker['resolutionEvidence']}")
        print("Source revisions:")
        for source, revision in sorted(checkpoint["sourceRevisions"].items()):
            print(f"  {source}: {revision}")
