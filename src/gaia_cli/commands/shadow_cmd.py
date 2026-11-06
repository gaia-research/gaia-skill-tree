"""Report-only CLI module for Yggdrasil IV shadow evaluation and corpus census."""

from __future__ import annotations

import argparse
from gaia_cli.commands.base import Command


class ShadowCommand(Command):
    name = "shadow"
    help = "Yggdrasil IV Trust Magnitude shadow census and replay"
    description = (
        "Read-only complete registry census and shadow replay slice consuming "
        "evaluateShadow and evaluateShadowRegistry under explicit context."
    )

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--registry",
            default=".",
            help="Path to registry root (defaults to local checkout).",
        )
        parser.add_argument(
            "--at",
            "--evaluation-at",
            dest="evaluation_at",
            default="2026-10-25T00:00:00Z",
            help="Pinned evaluation datetime UTC (default: 2026-10-25T00:00:00Z).",
        )
        parser.add_argument(
            "--output-dir",
            default=None,
            help="Explicit external or ignored output directory (e.g. .gaia/shadow, generated-output/shadow).",
        )
        parser.add_argument(
            "--stdout",
            action="store_true",
            help="Print human-readable impact summary to stdout.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Print deterministic machine JSON report to stdout.",
        )
        parser.add_argument(
            "--fail-closed",
            dest="fail_closed",
            action="store_true",
            help="Fail closed and exit non-zero if parse failures or unresolvable records occur.",
        )
        parser.add_argument(
            "--filter-status",
            dest="filter_status",
            default=None,
            help="Filter evaluation to a specific status subset (e.g. 'named').",
        )

    def execute(self, args: argparse.Namespace) -> int | None:
        from gaia_cli.shadowCorpus import run_shadow_corpus_cli
        return run_shadow_corpus_cli(args)


COMMAND = ShadowCommand()
