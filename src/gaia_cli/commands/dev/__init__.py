import sys
import argparse
from gaia_cli.commands.base import Command

from gaia_cli.commands.dev.helpers import (
    _run_docs_build,
    _confirm_destructive,
    _replace_section,
    _GENERATED_PREFIXES,
    _GENERATED_SUFFIXES,
    _GENERATED_EXACT,
    _VERSION_FILES,
    _get_contributor,
    _is_verifier,
    _parse_md,
    _write_md,
    _find_named_file,
    _update_named_skill_ref,
    _is_generated,
    _parse_named_frontmatter,
)
from gaia_cli.commands.dev.list import meta_list_command
from gaia_cli.commands.dev.verify import (
    meta_verify_command,
    _loadSkillForVerification,
    meta_verify_tier_command,
)
from gaia_cli.commands.dev.merge import (
    meta_merge_command,
    meta_split_command,
)
from gaia_cli.commands.dev.rename import meta_rename_command
from gaia_cli.commands.dev.calibrate import (
    meta_calibrate_command,
    calibrate_evidence_grades_command,
)
from gaia_cli.commands.dev.audit import (
    meta_audit_command,
    meta_diff_command,
)
from gaia_cli.commands.dev.timeline import meta_timeline_command
from gaia_cli.commands.dev.named import meta_update_named_command
from gaia_cli.commands.dev.evidence import (
    meta_evidence_command,
    meta_rm_evidence_command,
)
from gaia_cli.commands.dev.build import (
    meta_build_command,
    meta_add_command,
    meta_remove_command,
    meta_link_command,
    meta_reclassify_command,
)


DEV_USAGE = """\
Registry development commands (requires Verifier authorization):

  gaia dev list [--generic] [--named] [--description] [--json]
  gaia dev audit <skill_id>
  gaia dev diff [ref] [--base <ref>]
  gaia dev add <name> [--type <type>] [--description <desc>] [--named]
  gaia dev merge <target> <source1> [source2...] [--named] [--yes]
  gaia dev split <source> <target1> <target2>... [--yes]
  gaia dev rename <old_id> <new_id>
  gaia dev calibrate <skill_id> <level>
  gaia dev rm <skill_id> [--yes]
  gaia dev link <target> <prereqs> [--reset]
  gaia dev reclassify <skill_id> <new_type>
  gaia dev update-named <skill_id> [--status <status>] [--generic-ref <ref>]
  gaia dev evidence <skillId> <source> [--class A|B|C] [--evaluator <user>]
  gaia dev rm-evidence <skill_id> (--index N | --source URL) [--yes]
  gaia dev timeline <skill_id> --action <action> --notes <notes> [--user <username>]
  gaia dev build
  gaia dev verify <skill_id>

Read-only (no Verifier required):
  gaia dev list
  gaia dev audit <skill_id>
  gaia dev diff [ref]
  gaia validate [--intake] [--meta-sync]
  gaia test <suite>
"""

class DevCommand(Command):
    name = "dev"
    help = "Registry development and maintenance (requires writable registry)"
    epilog = DEV_USAGE
    formatter_class = argparse.RawDescriptionHelpFormatter

    def configure(self, parser: argparse.ArgumentParser) -> None:
        dev_sub = parser.add_subparsers(dest="dev_command")

        dev_list = dev_sub.add_parser(
            "list", help="List skills in the registry with filtering"
        )
        dev_list.add_argument(
            "--generic", action="store_true", help="Include generic (canonical) skills"
        )
        dev_list.add_argument("--named", action="store_true", help="Include named skills")
        dev_list.add_argument(
            "--description", action="store_true", help="Include skill descriptions"
        )
        dev_list.add_argument("--level", action="store_true", help="Include skill level")
        dev_list.add_argument(
            "--evidence", action="store_true", help="Include evidence count (generic only)"
        )
        dev_list.add_argument(
            "--contributor",
            action="store_true",
            help="Include contributor name (named only)",
        )
        dev_list.add_argument("--json", action="store_true", help="Output in JSON format")
        dev_list.add_argument(
            "--extra", action="append", help="Include extra schema fields in output"
        )

        dev_merge = dev_sub.add_parser(
            "merge", help="Merge one or more skills into a target skill"
        )
        dev_merge.add_argument("target", help="Target skill ID to merge into")
        dev_merge.add_argument("sources", nargs="+", help="Source skill IDs to merge from")
        dev_merge.add_argument(
            "--named",
            action="store_true",
            help="Also merge named implementation references",
        )
        dev_merge.add_argument(
            "--yes", "-y", "--y", action="store_true", help="Skip confirmation prompt"
        )

        dev_split = dev_sub.add_parser(
            "split", help="Split a skill into multiple new skills"
        )
        dev_split.add_argument("source", help="Source skill ID to split")
        dev_split.add_argument("targets", nargs="+", help="Target skill IDs to create")
        dev_split.add_argument(
            "--yes", "-y", "--y", action="store_true", help="Skip confirmation prompt"
        )

        dev_rename = dev_sub.add_parser(
            "rename", help="Rename a skill and update all references"
        )
        dev_rename.add_argument("old_id", help="Original skill ID")
        dev_rename.add_argument("new_id", help="New skill ID")

        dev_verify = dev_sub.add_parser(
            "verify", help="Verify or dispute a skill's evidence"
        )
        dev_verify.add_argument("skill_id", help="Skill ID to verify")
        dev_verify.add_argument(
            "--index", type=int, required=True, help="Index of the evidence entry to verify"
        )
        dev_verify.add_argument(
            "--dispute",
            action="store_true",
            help="Mark evidence as disputed instead of verified",
        )
        dev_verify.add_argument(
            "--notes", help="Optional notes about the verification/dispute"
        )
        dev_verify.add_argument("--source", help="URL to the verification discussion or PR")
        dev_verify.add_argument(
            "--no-build",
            action="store_true",
            help="Skip rebuilding docs and graph assets after verification",
        )

        dev_verify_tier = dev_sub.add_parser(
            "verify-tier",
            help="Recompute and persist a skill's verification tier (community/benchmark/security/enterprise)",
        )
        dev_verify_tier.add_argument(
            "skill_id", help="Skill ID (generic ref or contributor/named) to evaluate"
        )

        dev_calibrate = dev_sub.add_parser("calibrate", help="Update the level of a skill")
        dev_calibrate.add_argument("skill_id", help="Skill ID to calibrate")
        dev_calibrate.add_argument("level", help="New level (e.g. 3★)")
        dev_calibrate.add_argument(
            "--no-build",
            action="store_true",
            help="Skip rebuilding docs and graph assets after calibrating",
        )

        dev_calibrate_ev = dev_sub.add_parser(
            "calibrate-evidence-grades",
            help="Backfill per-row evidence grade fields from per-type artifact_score thresholds (Issue #761)",
        )
        dev_calibrate_ev.add_argument(
            "--dry-run", action="store_true", help="Show what would change without writing"
        )
        dev_calibrate_ev.add_argument(
            "--skill", help="Only process this skill ID (generic ref or contributor/name)"
        )
        dev_calibrate_ev.add_argument(
            "--scope",
            choices=("all", "generic", "named"),
            default="all",
            help="Limit scope to generic nodes, named .md files, or both (default: all)",
        )
        dev_calibrate_ev.add_argument(
            "--no-build", action="store_true", help="Skip rebuilding docs after backfill"
        )
        dev_calibrate_ev.add_argument(
            "--yes", "-y", action="store_true", help="Skip confirmation prompt"
        )

        dev_add = dev_sub.add_parser("add", help="Add a new skill to the registry")
        dev_add.add_argument("name", help="Human-readable name of the skill")
        dev_add.add_argument(
            "--id", help="Explicit ID for the skill (defaults to slugified name)"
        )
        dev_add.add_argument(
            "--type",
            choices=("basic", "extra", "ultimate", "unique"),
            default="basic",
            help="Skill type (default: basic)",
        )
        dev_add.add_argument("--description", help="Skill description")
        dev_add.add_argument(
            "--named", action="store_true", help="Add as a named skill instead of generic"
        )
        dev_add.add_argument(
            "--contributor", help="Contributor name for named skill (default: gaiabot)"
        )
        dev_add.add_argument(
            "--generic-ref", help="Generic skill reference for named skill"
        )
        dev_add.add_argument(
            "--status",
            help="Initial status (default: named for named skills, provisional for generic)",
        )
        dev_add.add_argument("--title", help="Display title (lore title) for named skills")
        dev_add.add_argument(
            "--level", help="Initial level (default: 2★ for named, 1★ for generic)"
        )
        dev_add.add_argument(
            "--extra-fields", help="JSON string of additional schema fields"
        )
        dev_add.add_argument(
            "--no-build",
            action="store_true",
            help="Skip rebuilding docs and graph assets after adding",
        )

        dev_rm = dev_sub.add_parser("rm", help="Remove a skill from the registry")
        dev_rm.add_argument("skill_id", help="Skill ID to remove")
        dev_rm.add_argument(
            "--no-build",
            action="store_true",
            help="Skip rebuilding docs and graph assets after removing",
        )
        dev_rm.add_argument(
            "--yes", "-y", "--y", action="store_true", help="Skip confirmation prompt"
        )

        dev_link = dev_sub.add_parser("link", help="Link skills by adding prerequisites")
        dev_link.add_argument(
            "target", help="Target skill ID that receives the prerequisites"
        )
        dev_link.add_argument(
            "prereqs", help="Comma-separated list of prerequisite skill IDs"
        )
        dev_link.add_argument(
            "--reset",
            action="store_true",
            help="Overwrite existing prerequisites instead of appending",
        )
        dev_link.add_argument(
            "--no-build",
            action="store_true",
            help="Skip rebuilding docs and graph assets after linking",
        )

        dev_reclassify = dev_sub.add_parser(
            "reclassify", help="Change the type of a generic skill"
        )
        dev_reclassify.add_argument("skill_id", help="Generic skill ID to reclassify")
        dev_reclassify.add_argument(
            "new_type",
            choices=("basic", "extra", "ultimate", "unique"),
            help="New skill type",
        )
        dev_reclassify.add_argument(
            "--no-build",
            action="store_true",
            help="Skip rebuilding docs and graph assets after reclassifying",
        )

        dev_update_named = dev_sub.add_parser(
            "update-named", help="Update frontmatter properties of a named skill"
        )
        dev_update_named.add_argument("skill_id", help="Named skill ID (e.g. author/skill)")
        dev_update_named.add_argument("--status", help="New status (e.g. awakened, named)")
        dev_update_named.add_argument(
            "--title",
            help="Display title (lore title) for the named skill — required by schema when status=named",
        )
        dev_update_named.add_argument(
            "--catalog-ref",
            help="Catalog reference slug — alternative to --title for satisfying the named-skill identity requirement",
        )
        dev_update_named.add_argument("--generic-ref", help="New generic skill reference")
        dev_update_named.add_argument(
            "--suite-components", help="Comma-separated list of suite components"
        )
        dev_update_named.add_argument(
            "--suite-ref",
            help="Suite capstone ID this skill belongs to. Sets suiteRef in frontmatter.",
        )
        dev_update_named.add_argument(
            "--installation-file",
            metavar="PATH",
            help="Path to a markdown file whose content replaces the '## Installation' section in the capstone skill.",
        )
        dev_update_named.add_argument(
            "--origin",
            choices=["true", "false"],
            help="Set the origin flag to true or false",
        )
        dev_update_named.add_argument(
            "--github-link",
            help="New GitHub URL link for the named skill (must be a blob link for 3★+)",
        )
        dev_update_named.add_argument(
            "--installable",
            choices=["true", "false"],
            help="Set the installable flag to true or false",
        )
        dev_update_named.add_argument(
            "--no-build",
            action="store_true",
            help="Skip rebuilding docs and graph assets after updating",
        )

        dev_timeline = dev_sub.add_parser(
            "timeline",
            help="Append a standalone event to a skill's or user tree's timeline",
        )
        dev_timeline.add_argument(
            "skill_id",
            help="Skill ID to append the event to (generic, named, or user-tree)",
        )
        dev_timeline.add_argument(
            "--action",
            required=True,
            choices=(
                "propose",
                "rank_up",
                "demote",
                "verified",
                "disputed",
                "type_change",
                "suite_ref_set",
                "note",
                "apex_pr_signed",
            ),
            help="The type of event action",
        )
        dev_timeline.add_argument("--notes", required=True, help="Description of the event")
        dev_timeline.add_argument(
            "--user",
            help="Write to skill-trees/<user>/skill-tree.json instead of the registry node",
        )
        dev_timeline.add_argument(
            "--timestamp",
            help="ISO 8601 timestamp for the event; defaults to now. Use for historical backfills.",
        )
        dev_timeline.add_argument(
            "--no-build",
            action="store_true",
            help="Skip rebuilding docs and graph assets after appending event",
        )

        dev_evidence = dev_sub.add_parser("evidence", help="Add evidence to a skill")
        dev_evidence.add_argument("skill_id", help="Skill ID to add evidence to")
        dev_evidence.add_argument("source", help="URL to the evidence source")
        dev_evidence.add_argument(
            "--index",
            type=int,
            metavar="N",
            help=(
                "Re-grade the existing evidence entry at this index in place "
                "(0-based) instead of appending a new one. Sets --type/--trust/"
                "--notes on that entry while preserving its other fields (e.g. "
                "the deprecated class). Used by the class→grade backfill."
            ),
        )
        dev_evidence.add_argument(
            "--type",
            dest="evidence_type",
            metavar="TYPE",
            help="Evidence type. Validated against meta.json evidence.types.",
        )
        dev_evidence.add_argument(
            "--trust",
            type=float,
            metavar="NUMBER",
            help="Trust Magnitude value. Grade is auto-derived: S≥250, A≥100, B≥50, C≥20; <20=ungraded.",
        )
        dev_evidence.add_argument(
            "--class",
            dest="evidence_class",
            choices=("A", "B", "C"),
            default=None,
            help="[DEPRECATED] Use --trust instead. Evidence class (A/B/C).",
        )
        dev_evidence.add_argument("--evaluator", help="GitHub username of the evaluator")
        dev_evidence.add_argument("--date", help="Date of evaluation (ISO 8601)")
        dev_evidence.add_argument("--notes", help="Optional notes about the evaluation")
        dev_evidence.add_argument(
            "--stars",
            type=int,
            metavar="N",
            help="GitHub star count",
        )
        dev_evidence.add_argument(
            "--views",
            type=int,
            metavar="N",
            help="View count",
        )
        dev_evidence.add_argument(
            "--citations",
            type=int,
            metavar="N",
            help="Citation count",
        )
        dev_evidence.add_argument(
            "--reviewers",
            type=int,
            metavar="N",
            help="Number of peer reviewers",
        )
        dev_evidence.add_argument(
            "--commits",
            type=int,
            metavar="N",
            help="Commit count",
        )
        dev_evidence.add_argument(
            "--contributors",
            type=int,
            metavar="N",
            help="Contributor count",
        )
        dev_evidence.add_argument(
            "--skill-count-in-repo",
            dest="skill_count_in_repo",
            type=int,
            metavar="N",
            help="Number of skills in the repo",
        )
        dev_evidence.add_argument(
            "--source-started-at",
            dest="source_started_at",
            metavar="YYYY-MM-DD",
            help="ISO date the source content first existed",
        )
        dev_evidence.add_argument(
            "--no-build",
            action="store_true",
            help="Skip rebuilding docs and graph assets after adding evidence",
        )

        dev_rm_evidence = dev_sub.add_parser(
            "rm-evidence",
            help="Remove an evidence entry (by --index or --source) from a skill"
        )
        dev_rm_evidence.add_argument(
            "skill_id",
            help="Skill ID to remove evidence from",
        )
        dev_rm_evidence.add_argument(
            "--index", type=int, help="Index of the evidence entry to remove"
        )
        dev_rm_evidence.add_argument(
            "--source",
            help="Remove all evidence entries whose source URL matches this exactly",
        )
        dev_rm_evidence.add_argument(
            "--no-build",
            action="store_true",
            help="Skip rebuilding docs and graph assets after removing evidence",
        )
        dev_rm_evidence.add_argument(
            "--yes", "-y", "--y", action="store_true", help="Skip confirmation prompt"
        )

        dev_build = dev_sub.add_parser(
            "build", help="Regenerate registry and documentation site"
        )

        dev_audit = dev_sub.add_parser("audit", help="Run registry maintenance linter")
        dev_audit.add_argument("--level", type=int, help="Filter audit by level threshold")

        dev_diff = dev_sub.add_parser(
            "diff",
            help="Show substantive registry additions in a branch vs main (strips generated noise)",
        )
        dev_diff.add_argument(
            "ref",
            nargs="?",
            help="Branch or ref to compare. Short names are auto-prefixed with origin/.",
        )
        dev_diff.add_argument(
            "--base",
            default="origin/main",
            help="Base ref to compare against",
        )

        dev_validate = dev_sub.add_parser(
            "validate", help="Validate the Gaia registry"
        )
        dev_validate.add_argument(
            "--intake",
            action="store_true",
            help="Validate intake batches instead of canonical graph",
        )
        dev_validate.add_argument(
            "--meta-sync",
            action="store_true",
            help="Verify meta.json is in sync with gaia.json",
        )

        dev_release = dev_sub.add_parser(
            "release", help="Bump version, commit, tag, and push to trigger GitHub Release"
        )
        dev_release.add_argument("release_type", choices=("patch", "minor", "major"))
        dev_release.add_argument(
            "--sync",
            action="store_true",
            help="Force sync versions if they disagree before bump",
        )
        dev_release.add_argument(
            "--no-push",
            action="store_true",
            help="Skip git push",
        )

        dev_test = dev_sub.add_parser(
            "test", help="Run self-verification tests"
        )
        dev_test.add_argument("suite", choices=("meta", "all"), help="Test suite to run")

        dev_docs = dev_sub.add_parser(
            "docs", help="Regenerate generated documentation regions"
        )
        dev_docs.add_argument(
            "--check", action="store_true", help="Fail if docs are stale without writing"
        )

        dev_mcp = dev_sub.add_parser(
            "mcp", help="Manage or run the bundled Gaia MCP server"
        )
        dev_mcp_sub = dev_mcp.add_subparsers(dest="mcp_command")
        dev_mcp_sub.add_parser("start", help="Start the MCP daemon")
        dev_mcp_sub.add_parser("stop", help="Stop the MCP daemon")
        dev_mcp_sub.add_parser("status", help="Get MCP daemon status")

        dev_hook = dev_sub.add_parser(
            "hook", help="Internal command invoked by Claude Code hook"
        )
        dev_hook.add_argument("--event", default="file_edit", help="Hook event type")

    def execute(self, args: argparse.Namespace) -> int | None:
        dev_cmd = getattr(args, "dev_command", None)
        MUTATING_DEV_COMMANDS = {
            "add",
            "merge",
            "split",
            "rename",
            "calibrate",
            "calibrate-evidence-grades",
            "evidence",
            "rm-evidence",
            "link",
            "reclassify",
            "update-named",
            "timeline",
            "rm",
            "verify",
            "verify-tier",
            "build",
            "release",
        }
        if dev_cmd in MUTATING_DEV_COMMANDS:
            from gaia_cli.authz import require_operator
            require_operator(f"dev {dev_cmd}", args.registry)

        if dev_cmd == "list":
            from gaia_cli.commands.dev.list import meta_list_command
            meta_list_command(args)
        elif dev_cmd == "merge":
            from gaia_cli.commands.dev.merge import meta_merge_command
            meta_merge_command(args)
        elif dev_cmd == "split":
            from gaia_cli.commands.dev.merge import meta_split_command
            meta_split_command(args)
        elif dev_cmd == "rename":
            from gaia_cli.commands.dev.rename import meta_rename_command
            meta_rename_command(args)
        elif dev_cmd == "verify":
            from gaia_cli.commands.dev.verify import meta_verify_command
            meta_verify_command(args)
        elif dev_cmd == "verify-tier":
            from gaia_cli.commands.dev.verify import meta_verify_tier_command
            meta_verify_tier_command(args)
        elif dev_cmd == "calibrate":
            from gaia_cli.commands.dev.calibrate import meta_calibrate_command
            meta_calibrate_command(args)
        elif dev_cmd == "calibrate-evidence-grades":
            from gaia_cli.commands.dev.calibrate import calibrate_evidence_grades_command
            calibrate_evidence_grades_command(args)
        elif dev_cmd == "add":
            from gaia_cli.commands.dev.build import meta_add_command
            meta_add_command(args)
        elif dev_cmd == "rm":
            from gaia_cli.commands.dev.build import meta_remove_command
            meta_remove_command(args)
        elif dev_cmd == "link":
            from gaia_cli.commands.dev.build import meta_link_command
            meta_link_command(args)
        elif dev_cmd == "reclassify":
            from gaia_cli.commands.dev.build import meta_reclassify_command
            meta_reclassify_command(args)
        elif dev_cmd == "update-named":
            from gaia_cli.commands.dev.named import meta_update_named_command
            meta_update_named_command(args)
        elif dev_cmd == "timeline":
            from gaia_cli.commands.dev.timeline import meta_timeline_command
            meta_timeline_command(args)
        elif dev_cmd == "evidence":
            from gaia_cli.commands.dev.evidence import meta_evidence_command
            meta_evidence_command(args)
        elif dev_cmd == "rm-evidence":
            from gaia_cli.commands.dev.evidence import meta_rm_evidence_command
            meta_rm_evidence_command(args)
        elif dev_cmd == "build":
            from gaia_cli.commands.dev.build import meta_build_command
            meta_build_command(args)
        elif dev_cmd == "audit":
            from gaia_cli.commands.dev.audit import meta_audit_command
            meta_audit_command(args)
        elif dev_cmd == "diff":
            from gaia_cli.commands.dev.audit import meta_diff_command
            meta_diff_command(args)
        elif dev_cmd == "validate":
            from gaia_cli.impl import validate_command
            validate_command(args)
        elif dev_cmd == "release":
            from gaia_cli.impl import release_command
            release_command(args)
        elif dev_cmd == "test":
            from gaia_cli.impl import test_command
            test_command(args)
        elif dev_cmd == "docs":
            from gaia_cli.impl import docs_command
            docs_command(args)
        elif dev_cmd == "mcp":
            from gaia_cli.commands.mcp_cmd import execute_dev_mcp
            execute_dev_mcp(args)
        elif dev_cmd == "hook":
            from gaia_cli.impl import hook_command
            hook_command(args)
        else:
            from gaia_cli.main import get_parser
            parser, subparsers = get_parser()
            if subparsers and "dev" in subparsers.choices:
                subparsers.choices["dev"].print_help()
            else:
                parser.print_help()
            return 1
        return 0

COMMAND = DevCommand()
