"""
scripts.upstream_watcher.watcher — main entry point for the Gaia upstream watcher.

Usage
-----
    python scripts/upstream_watcher/watcher.py [--dry-run] [--apply] [--skill <id>] [--verbose]

Flags
-----
--dry-run     (default) Print findings as a markdown report; do NOT create issues.
--apply       Create GitHub issues (requires gh CLI + GH_TOKEN).
--skill <id>  Scope to a single suite skill-id (e.g. mattpocock/skills).
--verbose     Extra logging to stderr.

Exit codes
----------
0  Success (even when some suites are skipped or have no findings).
1  Hard failure (import error, unrecoverable exception).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Ensure project root on sys.path for `scripts.*` imports when run directly
_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.lib.github_api import fetch_json, parse_owner_repo
from scripts.lib.named_iterator import iter_named_skills
from scripts.upstream_watcher.challenge_watch import (
    ChallengeWatchResult,
    WatchBudget,
    run_challenge_watch,
)
from scripts.upstream_watcher.finder import compute_finding, detect_mode, iter_suite_skills
from scripts.upstream_watcher.issuer import create_issues
from scripts.upstream_watcher.liveness import check_component_liveness, fetch_component_diff
from scripts.upstream_watcher.name_drift import check_name_drift

# ---------------------------------------------------------------------------
# Registry map builder
# ---------------------------------------------------------------------------


def _build_registry_map(root: Path | None = None) -> dict[str, dict]:
    """Return a dict mapping skill-id → frontmatter for all named skills."""
    return {fm["id"]: fm for _, fm in iter_named_skills(root=root) if fm.get("id")}


# ---------------------------------------------------------------------------
# Markdown report renderer (dry-run output)
# ---------------------------------------------------------------------------


def _render_report(
    full_findings: list[dict],
    challenge_result: ChallengeWatchResult | None = None,
) -> str:
    """Render full_findings and optional challenge_result as a markdown report for stdout."""
    if not full_findings and not (challenge_result and challenge_result.packets):
        base = "# Upstream Watcher — Dry-Run Report\n\n_No findings. All suites are up-to-date (or had no release data)._\n"
        if challenge_result and challenge_result.summaries:
            base += (
                f"\n## Challenge Watch Summary\n"
                f"- **Active monitored challenges:** {challenge_result.active_count}\n"
                f"- **Resolved (returned to routine):** {challenge_result.resolved_count}\n"
                f"- **Unverified inputs rejected:** {challenge_result.rejected_unverified_count}\n"
                f"- **Trusted receipt resolver unavailable:** {challenge_result.unavailable_count}\n"
                f"- **New verification packets emitted:** {len(challenge_result.packets)}\n"
            )
        return base

    lines = ["# Upstream Watcher — Dry-Run Report", ""]
    lines.append(f"**Total findings:** {len(full_findings)}")
    lines.append("")

    if challenge_result:
        lines.append(f"## Two-Sided Challenge Watch")
        lines.append(f"- **Active challenges:** {challenge_result.active_count}")
        lines.append(f"- **Resolved challenges (returned to routine):** {challenge_result.resolved_count}")
        lines.append(f"- **Unverified inputs rejected:** {challenge_result.rejected_unverified_count}")
        lines.append(f"- **Trusted receipt resolver unavailable:** {challenge_result.unavailable_count}")
        lines.append(f"- **Verification packets emitted:** {len(challenge_result.packets)}")
        lines.append("")
        if challenge_result.packets:
            lines.append("### Emitted Verification Packets")
            for pkt in challenge_result.packets:
                lines.append(f"- **`{pkt.packet_id[:12]}`** — `{pkt.subject_id}` vs `{pkt.comparator_id or 'none'}`")
                lines.append(f"  - **Trigger:** `{pkt.trigger_side}` ({pkt.trigger_type})")
                lines.append(f"  - **Notes:** {pkt.notes}")
            lines.append("")

    bootstrap_findings = [f for f in full_findings if f["finding_type"] == "bootstrap"]
    update_findings = [f for f in full_findings if f["finding_type"] == "update"]

    if bootstrap_findings:
        lines.append(f"## Bootstrap findings ({len(bootstrap_findings)})")
        lines.append("")
        lines.append("These suites have no `upstream:` block yet. Approval will baseline them.")
        lines.append("")
        for f in bootstrap_findings:
            lines.append(f"### `{f['skillId']}`")
            lines.append(f"- **Proposed baseline:** `{f['newVersion']}`")
            lines.append(f"- **Released:** `{f.get('releasedAt', 'unknown')}`")
            lines.append(f"- **Source:** {f.get('sourceUrl', '')}")
            lines.append("")

    if update_findings:
        lines.append(f"## Update findings ({len(update_findings)})")
        lines.append("")
        for f in update_findings:
            lines.append(f"### `{f['skillId']}`")
            lines.append(f"- **Previous version:** `{f['currentVersion']}`")
            lines.append(f"- **New version:** `{f['newVersion']}`")
            lines.append(f"- **Released:** `{f.get('releasedAt', 'unknown')}`")
            lines.append(f"- **Mode:** `{f.get('mode', 'version-only')}`")
            lines.append(f"- **Source:** {f.get('sourceUrl', '')}")

            adds = f.get("componentAdds", [])
            removes = f.get("componentRemoves", [])
            liveness = f.get("linkLiveness", [])
            name_drift = f.get("nameDrift", [])

            if adds:
                lines.append(f"- **Component adds:** {', '.join(f'`{s}`' for s in adds)}")
            if removes:
                lines.append(f"- **Component removes:** {', '.join(f'`{s}`' for s in removes)}")
            if liveness:
                lines.append(f"- **Broken links:** {len(liveness)}")
                for row in liveness:
                    lines.append(f"  - `{row['skillId']}` → `{row['url']}` ({row['status']})")
            if name_drift:
                lines.append(f"- **Name drift:** {len(name_drift)}")
                for row in name_drift:
                    lines.append(
                        f"  - `{row['skillId']}` registry:`{row['registrySlug']}` "
                        f"upstream:`{row['sanitizedName']}` — fix: `{row['fixCommand']}`"
                    )
            lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Core poll loop
# ---------------------------------------------------------------------------


def _poll_suite(
    fm: dict,
    registry_map: dict[str, dict],
    verbose: bool,
) -> dict | None:
    """Poll a single suite and return a full finding dict or None."""
    skill_id = fm.get("id", "?")
    gh_url = (fm.get("links") or {}).get("github", "")

    parsed = parse_owner_repo(gh_url)
    if not parsed:
        print(
            f"  [warn] {skill_id} — cannot derive owner/repo from links.github={gh_url!r}; skipping.",
            file=sys.stderr,
        )
        return None

    owner, repo = parsed

    if verbose:
        print(f"  Polling {owner}/{repo} for {skill_id} ...", file=sys.stderr)

    release_data = fetch_json(
        f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    )

    if not release_data:
        print(
            f"  [skip] {skill_id} — no release data from {owner}/{repo} (no releases tagged or API error).",
            file=sys.stderr,
        )
        return None

    finding = compute_finding(fm, release_data)
    if finding is None:
        if verbose:
            print(f"  [ok] {skill_id} — up-to-date at {fm.get('upstream', {}).get('version', '?')}.", file=sys.stderr)
        return None

    # Auto-detect mode
    mode = detect_mode(fm, registry_map)
    finding["mode"] = mode

    new_version = finding["newVersion"]
    components = fm.get("suiteComponents") or []
    component_root = fm.get("upstreamComponentRoot") or "skills"

    # Only do component diff, liveness, and name-drift for update findings
    # in components mode.
    if finding["finding_type"] == "update" and mode == "components":
        adds, removes = fetch_component_diff(
            owner, repo, new_version, component_root, components
        )
        finding["componentAdds"] = adds
        finding["componentRemoves"] = removes

        liveness = check_component_liveness(components, registry_map)
        finding["linkLiveness"] = liveness

        # Issue #1457: compare each tracked component's registry slug against
        # its sanitized upstream SKILL.md frontmatter `name` — catches
        # DIRNAME_MISMATCH drift at release time, before a periodic
        # install_parity.py sweep would surface it.
        finding["nameDrift"] = check_name_drift(components, registry_map)
    else:
        finding["componentAdds"] = []
        finding["componentRemoves"] = []
        finding["linkLiveness"] = []
        finding["nameDrift"] = []

    return finding


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Return exit code. 0 on success; 1 on hard failure."""
    parser = argparse.ArgumentParser(
        description="Gaia upstream watcher — poll suite skill repos for new releases."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Print findings as a markdown report; do NOT create issues (default).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Actually create GitHub issues (requires gh CLI + GH_TOKEN).",
    )
    parser.add_argument(
        "--skill",
        metavar="SKILL_ID",
        default=None,
        help="Scope to a single suite skill-id (e.g. mattpocock/skills).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Extra logging to stderr.",
    )
    # Challenge Watch (Yggdrasil IV P2)
    parser.add_argument(
        "--challenge-watch",
        action="store_true",
        default=False,
        help="Enable bounded two-sided challenge watch.",
    )
    parser.add_argument(
        "--challenge-input",
        metavar="PATH",
        default=None,
        help="Optional path to active challenges input JSON file.",
    )
    parser.add_argument(
        "--challenge-ledger",
        metavar="PATH",
        default=None,
        help="Optional path to durable challenge watch ledger file.",
    )
    parser.add_argument(
        "--challenge-output",
        metavar="DIR",
        default=None,
        help="Optional directory to write emitted verification packets.",
    )
    parser.add_argument(
        "--challenge-shadow",
        action="store_true",
        default=False,
        help="Admit unverified challenges in shadow mode without public authority.",
    )
    parser.add_argument(
        "--challenge-budget-requests",
        type=int,
        default=20,
        help="Maximum HTTP requests allocated for challenge watch (default: 20).",
    )
    parser.add_argument(
        "--challenge-budget-subjects",
        type=int,
        default=10,
        help="Maximum subjects evaluated in challenge watch (default: 10).",
    )
    args = parser.parse_args(argv)

    # --apply wins over --dry-run
    apply = args.apply
    verbose = args.verbose
    challenge_watch_enabled = args.challenge_watch or (
        os.environ.get("GAIA_CHALLENGE_WATCH_ENABLED", "").lower() in {"1", "true", "yes"}
    )

    try:
        registry_map = _build_registry_map()
    except Exception as exc:  # noqa: BLE001
        print(f"[error] Failed to build registry map: {exc}", file=sys.stderr)
        return 1

    full_findings: list[dict] = []
    skipped = 0
    up_to_date = 0

    suite_iter = (
        (p, fm)
        for p, fm in iter_suite_skills()
        if (args.skill is None or fm.get("id") == args.skill)
    )

    # ── Routine Suite Watch ────────────────────────────────────────────────
    for _path, fm in suite_iter:
        skill_id = fm.get("id", "?")
        try:
            finding = _poll_suite(fm, registry_map, verbose)
        except Exception as exc:  # noqa: BLE001
            print(f"  [error] Unexpected error polling {skill_id}: {exc}", file=sys.stderr)
            skipped += 1
            continue

        if finding is None:
            up_to_date += 1
        else:
            full_findings.append(finding)

    print(
        f"\n[watcher] Polled suites: {len(full_findings) + up_to_date + skipped} total, "
        f"{len(full_findings)} finding(s), {up_to_date} up-to-date, {skipped} skipped.",
        file=sys.stderr,
    )

    # ── Optional Two-Sided Challenge Watch (Opt-In / Configured) ────────────
    challenge_result: ChallengeWatchResult | None = None
    if challenge_watch_enabled:
        if verbose:
            print("[watcher] Executing two-sided challenge watch seam ...", file=sys.stderr)
        c_budget = WatchBudget(
            max_requests=args.challenge_budget_requests,
            max_subjects=args.challenge_budget_subjects,
        )
        shared_store = None
        if args.challenge_ledger is None:
            from gaia_cli.steward.ledger import GitRefLedgerStore
            shared_store = GitRefLedgerStore(Path.cwd(), "origin")
        challenge_result = run_challenge_watch(
            challenges=args.challenge_input,
            registry_map=registry_map,
            budget=c_budget,
            ledger_path=args.challenge_ledger,
            packets_dir=args.challenge_output,
            shared_store=shared_store,
            allow_shadow=args.challenge_shadow,
            verbose=verbose,
        )

    if not apply:
        # Dry-run: render markdown report to stdout
        report = _render_report(full_findings, challenge_result)
        print(report)
    else:
        summaries = create_issues(full_findings, apply=True, verbose=verbose)
        print(f"[watcher] Issue creation complete. {len(summaries)} finding(s) processed.")
        if challenge_result:
            print(
                f"[watcher] Challenge watch: {len(challenge_result.packets)} verification packet(s) written, "
                f"{challenge_result.active_count} active challenge(s) monitored."
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
