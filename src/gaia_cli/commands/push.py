import argparse
from gaia_cli.commands.base import Command

class PushCommand(Command):
    name = "push"
    help = "Prepare detected skills for review and file a GitHub issue"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print the skill batch without writing it",
        )
        # Sprint D W2b (#905) — benchmark-evidence divert. Present flags trigger
        # push_benchmark_command in execute() BEFORE the skill-proposal flow runs.
        # All fingerprint validation is delegated to _preflight_benchmark_row via
        # the meta_evidence_command SSOT — DO NOT reimplement it here.
        parser.add_argument(
            "--benchmark",
            metavar="NAME",
            help="Divert to benchmark-evidence flow. Short name (e.g. 'humaneval') maps to a versioned benchmarkId. Writes a provenance:pending row for CI/Verifier promotion.",
        )
        parser.add_argument(
            "--from-result-file",
            dest="fromResultFile",
            metavar="PATH",
            help="Populate every benchmark field from a harness result JSON (typically .benchmark-result.json).",
        )
        parser.add_argument(
            "--skill-id",
            dest="skillId",
            metavar="ID",
            help="Skill the score is attributed to (contributor/slug). Only used with --benchmark.",
        )
        parser.add_argument(
            "--score",
            type=float,
            metavar="NUMBER",
            help="Benchmark score in the units named by --unit. Only used with --benchmark.",
        )
        parser.add_argument(
            "--unit",
            default=None,
            choices=["pct", "pass@1", "pass@10", "bleu", "f1", "accuracy", "elo", "raw"],
            help="Benchmark score unit (frozen enum). Only used with --benchmark; defaults to pass@1 for humaneval via --from-result-file.",
        )
        parser.add_argument(
            "--dataset-hash",
            dest="datasetHash",
            metavar="SHA256",
            help="SHA-256 of the raw dataset. Only used with --benchmark; typically comes from --from-result-file.",
        )
        parser.add_argument(
            "--benchmark-input-hash",
            dest="benchmarkInputHash",
            metavar="SHA256",
            help="SHA-256 of (dataset + prompt + harness config). Only used with --benchmark.",
        )
        parser.add_argument(
            "--run-at",
            dest="runAt",
            metavar="ISO8601",
            help="ISO 8601 timestamp when the harness executed. Only used with --benchmark.",
        )
        parser.add_argument(
            "--attestor",
            metavar="HANDLE",
            help="Override the auto-detected GitHub handle stamped as attestor of a pending row.",
        )
        parser.add_argument(
            "--harness-url",
            dest="harnessUrl",
            metavar="URL",
            help="Permalink into the pinned-commit harness code that produced the result.",
        )
        parser.add_argument(
            "--percentile",
            type=int,
            metavar="N",
            help="Optional 0..100 leaderboard percentile; feeds the benchmark-result magnitude formula.",
        )
        parser.add_argument(
            "--no-build",
            dest="no_build",
            action="store_true",
            help="Skip regenerating docs/graph after a benchmark evidence append (fastest path).",
        )
        parser.add_argument(
            "--no-issue",
            action="store_true",
            dest="no_issue",
            help="Write intake record without creating a GitHub issue",
        )
        parser.add_argument(
            "--no-pr", action="store_true", dest="no_issue", help=argparse.SUPPRESS
        )
        parser.add_argument(
            "--yes", "-y", "--y", action="store_true", dest="yes", help="Skip confirmation prompts"
        )
        parser.add_argument(
            "--allow-unsafe",
            action="store_true",
            dest="allowUnsafe",
            help="Override the security scanner block on high-severity findings (requires --reason)",
        )
        parser.add_argument(
            "--reason",
            type=str,
            default="",
            dest="overrideReason",
            help="Document an --allow-unsafe override for the audit trail",
        )

    def execute(self, args: argparse.Namespace) -> int | None:
        # Sprint D W2b (#905) — divert to the benchmark-evidence flow when
        # --benchmark is set. The standard skill-proposal path is untouched.
        if getattr(args, "benchmark", None):
            from gaia_cli.commands.pushBenchmark import push_benchmark_command
            return push_benchmark_command(args)
        from gaia_cli.main import push_command
        push_command(args)
        return 0

class ProposeCommand(Command):
    name = "propose"
    help = "Propose a single canonical skill as a named PR"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "skillId", help="Canonical skill ID (accepts /skill-id form)"
        )
        parser.add_argument(
            "--target", help="Named skill target in contributor/skill-name format"
        )
        parser.add_argument(
            "--ultimate",
            action="store_true",
            help="Require that the selected skill is ultimate",
        )
        parser.add_argument(
            "--yes", "-y", "--y", action="store_true", help="Use defaults without interactive prompts"
        )
        parser.add_argument(
            "--no-pr",
            action="store_true",
            help="Write intake proposal without opening a PR",
        )

    def execute(self, args: argparse.Namespace) -> int | None:
        from gaia_cli.main import propose_command
        propose_command(args)
        return 0

COMMANDS = [PushCommand(), ProposeCommand()]
