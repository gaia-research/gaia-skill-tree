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
import sys
from pathlib import Path

# Ensure project root on sys.path for `scripts.*` imports when run directly
_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.lib.github_api import fetch_json, parse_owner_repo
from scripts.lib.named_iterator import iter_named_skills
from scripts.upstream_watcher.finder import compute_finding, detect_mode, iter_suite_skills
from scripts.upstream_watcher.issuer import create_issues
from scripts.upstream_watcher.liveness import check_component_liveness, fetch_component_diff

# ---------------------------------------------------------------------------
# Registry map builder
# ---------------------------------------------------------------------------


def _build_registry_map(root: Path | None = None) -> dict[str, dict]:
    """Return a dict mapping skill-id → frontmatter for all named skills."""
    return {fm["id"]: fm for _, fm in iter_named_skills(root=root) if fm.get("id")}


# ---------------------------------------------------------------------------
# Markdown report renderer (dry-run output)
# ---------------------------------------------------------------------------


def _render_report(full_findings: list[dict]) -> str:
    """Render full_findings as a markdown report for stdout."""
    if not full_findings:
        return "# Upstream Watcher — Dry-Run Report\n\n_No findings. All suites are up-to-date (or had no release data)._\n"

    lines = ["# Upstream Watcher — Dry-Run Report", ""]
    lines.append(f"**Total findings:** {len(full_findings)}")
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

            if adds:
                lines.append(f"- **Component adds:** {', '.join(f'`{s}`' for s in adds)}")
            if removes:
                lines.append(f"- **Component removes:** {', '.join(f'`{s}`' for s in removes)}")
            if liveness:
                lines.append(f"- **Broken links:** {len(liveness)}")
                for row in liveness:
                    lines.append(f"  - `{row['skillId']}` → `{row['url']}` ({row['status']})")
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

    # Only do component diff and liveness for update findings in components mode
    if finding["finding_type"] == "update" and mode == "components":
        adds, removes = fetch_component_diff(
            owner, repo, new_version, component_root, components
        )
        finding["componentAdds"] = adds
        finding["componentRemoves"] = removes

        liveness = check_component_liveness(components, registry_map)
        finding["linkLiveness"] = liveness
    else:
        finding["componentAdds"] = []
        finding["componentRemoves"] = []
        finding["linkLiveness"] = []

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
    args = parser.parse_args(argv)

    # --apply wins over --dry-run
    apply = args.apply
    verbose = args.verbose

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

    if not apply:
        # Dry-run: render markdown report to stdout
        report = _render_report(full_findings)
        print(report)
    else:
        summaries = create_issues(full_findings, apply=True, verbose=verbose)
        print(f"[watcher] Issue creation complete. {len(summaries)} finding(s) processed.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
