"""`gaia curate`: discovery-only packet preparation with an L4 hard stop."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from gaia_cli.commands.base import Command
from gaia_cli.curation.orchestrator import CurationOrchestrator
from gaia_cli.curation.state import CurationRun


class CurateCommand(Command):
    name = "curate"
    help = "Discover candidates and prepare packets for human L4 review"
    description = "Run sequential source discovery and packet prefill; always stop at AWAITING_L4_REVIEW."

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("url", nargs="?", help="GitHub blob URL for one SKILL.md source")
        parser.add_argument("--generic", "-g", dest="generic", help="Suggested generic ID (advisory only)")
        parser.add_argument("--discover", action="store_true", help="Record optional downstream evidence-discovery intent")
        parser.add_argument("--resume", metavar="RUN_ID", help="Resume an existing local run")
        parser.add_argument("--status", action="store_true", help="Print run status without advancing it")
        parser.add_argument("--dry-run", action="store_true", help="Persist run state without packet writes")
        parser.add_argument("--inventory", help="Frozen JSON candidate array/envelope (maximum five candidates)")
        parser.add_argument("--candidate-id", help="Explicit candidate identity for a single source URL")
        parser.add_argument("--name", help="Candidate display name")
        parser.add_argument("--description", help="Candidate description")
        parser.add_argument("--batch-id", help="Existing intake batch reference; never submits a new batch")
        parser.add_argument("--intake-issue-number", type=int, help="Existing intake issue number")
        parser.add_argument("--intake-issue-url", help="Existing intake issue URL")
        parser.add_argument("--registry", default=".", help=argparse.SUPPRESS)

    @staticmethod
    def _inventory(path: str) -> list[dict[str, Any]]:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        # C owns canonical freeze/reconcile. If integrated, normalize raw candidate
        # lists through its shared freezeInventory contract; otherwise consume an
        # already-frozen envelope without inventing another reconciliation format.
        if isinstance(data, list):
            from gaia_cli.curation.reconciliation import freezeInventory
            data = freezeInventory(data)
        rows = data.get("candidates") if isinstance(data, dict) else None
        if not isinstance(rows, list) or not 1 <= len(rows) <= 5:
            raise ValueError("frozen inventory must contain 1–5 candidates")
        normalized = []
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("inventory candidates must be objects")
            candidate_id = row.get("candidateId")
            source_url = row.get("sourceUrl") or row.get("skillFileUrl")
            if not isinstance(candidate_id, str) or not candidate_id.strip() or not isinstance(source_url, str):
                raise ValueError("each candidate requires candidateId and sourceUrl")
            normalized.append({**row, "candidateId": candidate_id, "sourceUrl": source_url})
        return normalized

    @staticmethod
    def _freshness(run: CurationRun, registry: str) -> list[str]:
        results = run.checkpoint.get("results", [])
        if not results:
            return []
        try:
            from gaia_cli.curation.freshness import verifyPacketFreshness
        except ImportError:
            return ["packet freshness verifier is unavailable; resume is fail-closed"]
        errors: list[str] = []
        for result in results:
            packet_path = result.get("packetPath")
            if not packet_path:
                continue
            try:
                packet = json.loads(Path(packet_path).read_text(encoding="utf-8"))
                errors.extend(verifyPacketFreshness(packet, registryPath=registry))
            except Exception as exc:
                errors.append(f"{packet_path}: freshness check failed: {exc}")
        return errors

    def execute(self, args: argparse.Namespace) -> int | None:
        if args.resume:
            run = CurationRun.load(CurationRun(run_id=args.resume).run_dir)
            # Resume arguments cannot replace durable external references/inventory.
            freshness_errors = self._freshness(run, args.registry)
            if freshness_errors:
                blockers = {item.get("checkId"): item for item in run.checkpoint.get("blockers", [])}
                for i, error in enumerate(freshness_errors):
                    blockers[f"packet-freshness-{i}"] = {
                        "checkId": f"packet-freshness-{i}", "status": "open", "summary": error
                    }
                run.checkpoint["blockers"] = list(blockers.values())
                run.save(run.run_dir)
        else:
            if not args.url and not args.inventory:
                print("gaia curate: a source URL or --inventory is required")
                return 2
            try:
                inventory = self._inventory(args.inventory) if args.inventory else []
            except Exception as exc:
                print(f"gaia curate: invalid frozen inventory: {exc}")
                return 2
            run = CurationRun(input_url=args.url or "", suggested_generic_id=args.generic,
                              candidate_id=args.candidate_id, candidate_name=args.name,
                              candidate_description=args.description, inventory=inventory,
                              discover=args.discover, dry_run=args.dry_run)
            run.external_refs.update(batch_id=args.batch_id, intake_issue_number=args.intake_issue_number,
                                     intake_issue_url=args.intake_issue_url)
            run.save(run.run_dir)

        if args.status:
            CurationOrchestrator.print_status(run)
            return 0
        if args.dry_run or run.dry_run:
            CurationOrchestrator.print_status(run)
            return 0
        orchestrator = CurationOrchestrator(run, registry_path=args.registry, save_path=run.run_dir / "state.json")
        try:
            orchestrator.run_to_next_gate()
        except Exception as exc:
            print(f"gaia curate: discovery paused for targeted retry: {exc}")
            CurationOrchestrator.print_status(run)
            return 1
        CurationOrchestrator.print_status(run)
        return 0


COMMAND = CurateCommand()
