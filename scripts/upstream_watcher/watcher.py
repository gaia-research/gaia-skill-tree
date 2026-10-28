"""
scripts.upstream_watcher.watcher — main entry point for the Gaia upstream watcher.

Usage
-----
    python scripts/upstream_watcher/watcher.py [--dry-run] [--apply] [--skill <id>]
        [--child-mode batch|fanout] [--escalate <candidate-id>] [--report FILE] [--verbose]

Flags
-----
--dry-run         (default) Print findings as a markdown report; do NOT create issues.
--apply           Create GitHub issues (requires gh CLI + GH_TOKEN).
--skill <id>      Scope to a single suite skill-id (e.g. mattpocock/skills).
--child-mode M    fanout (default): preserve the deployed emission contract.
                  batch: opt-in payloadVersion 2 record, no per-candidate children.
--escalate ID     Create (or adopt) ONE intake child for the batch row ``ID``
                  (for example ``garrytan/gbrain:foo``) and exit.
--report FILE     Write the JSON run report (issuesCreated, issuesUpdated,
                  suppressedDuplicates, retainedCandidates, unknownEvidence, suites).
--verbose         Extra logging to stderr.

Exit codes
----------
0  Success (even when some suites are skipped or have no findings).
1  Hard failure (import error, unrecoverable exception).
2  Escalation target not found in any open umbrella.
3  Unknown evidence (registry unreadable or a GitHub list/get failed). Zero
   issue writes were made; the report still lists unknownEvidence.

A suite that is permanently refused, or whose truncated tree cannot be walked within budget, is skipped for the
run and listed under ``unavailable`` (its ``reason`` is ``permanent`` or ``tree-truncated``). It never blocks the
other suites and never produces a finding.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure project root on sys.path for `scripts.*` imports when run directly
_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.lib.github_api import (
    GitHubFetchError,
    GitHubNotFound,
    fetch_json,
    is_permanent_unavailable,
    parse_owner_repo,
)
from scripts.lib.named_iterator import iter_named_skills
from scripts.upstream_watcher.finder import compute_finding, detect_mode, iter_suite_skills
from scripts.upstream_watcher.batch import batch_stopped, escalate_candidate, new_report, run_batch
from scripts.upstream_watcher.issuer import IdempotencyLookupError, UmbrellaWriteError, create_issues
from scripts.upstream_watcher.live import (
    LiveGh,
    SuiteUnavailable,
    UnknownEvidenceError,
    retry_transient,
    unknown_read_detail,
)
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


def _status_of(exc: Exception) -> int | None:
    return getattr(exc.__cause__, "status", None)


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

    # Fail closed (M1). Only a definitive HTTP 404 means "no releases tagged" and is
    # skipped. Any other failure (403, 5xx, network, unparseable body) is unknown
    # evidence, so the run writes nothing and exits 3.
    release_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    try:
        # C9 (H-B): a transient failure gets three attempts before it is unknown evidence.
        release_data = retry_transient(lambda: fetch_json(release_url, strict=True))
    except GitHubNotFound:
        print(
            f"  [skip] {skill_id} — {owner}/{repo} has no releases tagged (HTTP 404).",
            file=sys.stderr,
        )
        return None
    except GitHubFetchError as exc:
        # H2: a permanent refusal (451, 410, or a 403 without a rate-limit signal) skips this suite only.
        if is_permanent_unavailable(exc):
            raise SuiteUnavailable(
                f"releases/latest for {owner}/{repo} is unavailable (HTTP {exc.status}): {exc}"
            ) from exc
        raise UnknownEvidenceError(
            f"releases/latest for {owner}/{repo} could not be read: {exc}{unknown_read_detail(exc)}"
        ) from exc
    if not isinstance(release_data, dict) or not release_data.get("tag_name"):
        raise UnknownEvidenceError(f"releases/latest for {owner}/{repo} returned no tag")

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
        # L2: a transient network error is not a broken link. It stays out of the
        # hashed linkLiveness; the planner carries the previous state for it.
        finding["linkLiveness"] = [row for row in liveness if row["status"] != "network_error"]
        finding["linkLivenessUnknown"] = sorted(
            row["skillId"] for row in liveness if row["status"] == "network_error"
        )

        # Issue #1457: compare each tracked component's registry slug against
        # its sanitized upstream SKILL.md frontmatter `name` — catches
        # DIRNAME_MISMATCH drift at release time, before a periodic
        # install_parity.py sweep would surface it.
        finding["nameDrift"] = check_name_drift(components, registry_map)
    else:
        finding["componentAdds"] = []
        finding["componentRemoves"] = []
        finding["linkLiveness"] = []
        finding["linkLivenessUnknown"] = []
        finding["nameDrift"] = []

    return finding


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


def _write_report(report: dict, path: str | None) -> None:
    if not path:
        return
    Path(path).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Return exit code. 0 on success; 1 on hard failure; 2 escalation target missing; 3 unknown evidence."""
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
        "--child-mode",
        choices=("batch", "fanout"),
        default="fanout",
        help="fanout (default): deployed children. batch: opt-in umbrella batch record.",
    )
    parser.add_argument(
        "--escalate",
        metavar="CANDIDATE_ID",
        default=None,
        help="Create or adopt one intake child for batch row CANDIDATE_ID, then exit.",
    )
    parser.add_argument(
        "--report",
        metavar="FILE",
        default=None,
        help="Write the JSON run report to FILE (also in dry-run).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Extra logging to stderr.",
    )
    parser.add_argument(
        "--reset-records",
        metavar="SUITE",
        default=None,
        help="Rebuild SUITE's record state from the fresh poll (M4). Requires --apply --child-mode batch. Per-row status and child "
        "links stored only in the lost record comments are not recovered.",
    )
    args = parser.parse_args(argv)

    # --apply wins over --dry-run
    apply = args.apply
    verbose = args.verbose

    if args.reset_records and not apply:
        print("[watcher] --reset-records requires --apply: a reset rewrites the umbrella's record comments.",
              file=sys.stderr)
        return 1

    if args.reset_records and args.child_mode != "batch":
        print("[watcher] --reset-records requires --child-mode batch; fanout cannot reset records.", file=sys.stderr)
        return 1

    if args.escalate:
        result, code = escalate_candidate(args.escalate, LiveGh(), apply=apply)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return code

    batch_mode = args.child_mode == "batch"
    try:
        registry_map = _build_registry_map()
    except Exception as exc:  # noqa: BLE001
        print(f"[error] Failed to build registry map: {exc}", file=sys.stderr)
        if not batch_mode:
            return 1
        # Fail closed: registry unreadable => zero writes, unknown evidence, exit 3.
        report = new_report()
        report["dryRun"] = not apply
        report["unknownEvidence"].append({"source": "registry", "detail": str(exc)})
        _write_report(report, args.report)
        return 3

    full_findings: list[dict] = []
    unknown: list[dict] = []
    unavailable: list[dict] = []
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
        except SuiteUnavailable as exc:
            # H2 and C9 (H-B): skipped, listed, and never blocking. The suite has no finding, so it cannot change anything.
            if exc.reason == "tree-truncated":
                print(f"::notice::{skill_id} skipped: unavailable: tree-truncated ({exc})", file=sys.stderr)
            else:
                print(f"::notice::{skill_id} skipped: upstream is permanently unavailable ({exc})", file=sys.stderr)
            unavailable.append(
                {"suite": skill_id, "detail": str(exc), "status": _status_of(exc), "reason": exc.reason}
            )
            continue
        except UnknownEvidenceError as exc:
            print(f"  [unknown] {skill_id} — {exc}", file=sys.stderr)
            unknown.append({"source": "github-poll", "suite": skill_id, "detail": str(exc)})
            continue
        except Exception as exc:  # noqa: BLE001 — fail closed: an unexpected failure is unknown evidence, never "skipped"
            print(f"  [unknown] {skill_id} — unexpected error while polling: {exc}", file=sys.stderr)
            unknown.append({"source": "github-poll", "suite": skill_id, "detail": f"unexpected error: {exc}"})
            continue

        if finding is None:
            up_to_date += 1
        else:
            full_findings.append(finding)

    print(
        f"\n[watcher] Polled suites: {len(full_findings) + up_to_date + len(unknown)} total, "
        f"{len(full_findings)} finding(s), {up_to_date} up-to-date, {len(unknown)} unknown.",
        file=sys.stderr,
    )

    if unknown:
        # M1: one unreadable poll makes the whole run unknown. Nothing is written, not
        # even for suites that polled cleanly, so the next run starts from the same state.
        report = new_report()
        report["childMode"] = args.child_mode
        report["dryRun"] = not apply
        report["unknownEvidence"] = unknown
        report["unavailable"] = unavailable
        _write_report(report, args.report)
        print(
            f"[watcher] Unknown evidence on {len(unknown)} suite(s); zero issues written this run.",
            file=sys.stderr,
        )
        return 3

    if not apply:
        # Dry-run: render markdown report to stdout
        print(_render_report(full_findings))

    if not batch_mode:
        report = new_report()
        report["childMode"] = "fanout"
        report["dryRun"] = not apply
        report["unavailable"] = unavailable
        summaries: list[dict] = []
        if apply:
            try:
                summaries = create_issues(full_findings, apply=True, verbose=verbose)
            except IdempotencyLookupError as exc:
                # Fail closed: every duplicate check ran before the first write, so nothing was created.
                report["unknownEvidence"].append({"source": "github-list", "detail": str(exc)})
                _write_report(report, args.report)
                print(f"[watcher] Unknown evidence, no issues written: {exc}", file=sys.stderr)
                return 3
            except UmbrellaWriteError as exc:
                # M10: an umbrella write failed. Its children were not written, and later suites stop.
                report["unknownEvidence"].append({"source": "github-write", "detail": str(exc)})
                _write_report(report, args.report)
                print(f"[watcher] Umbrella write failed, run stopped: {exc}", file=sys.stderr)
                return 3
        report["issuesCreated"] = sum(1 for row in summaries if row.get("umbrella") and not row.get("updated"))
        report["issuesUpdated"] = sum(1 for row in summaries if row.get("updated"))
        _write_report(report, args.report)
        if apply:
            print(f"[watcher] Issue creation complete. {len(summaries)} finding(s) processed.")
        return 0

    report, code = run_batch(full_findings, LiveGh(), apply=apply, reset_records=args.reset_records)
    report["unavailable"] = unavailable
    # The bootstrap pass runs unless a GitHub read or write stopped the batch. A record-level failure on one
    # suite does not stop it (H2), and the exit code is still 3 at the end.
    if not batch_stopped(report):
        bootstrap = [finding for finding in full_findings if finding["finding_type"] == "bootstrap"]
        if bootstrap:
            try:
                create_issues(bootstrap, apply=apply, verbose=verbose)
            except IdempotencyLookupError as exc:
                report["unknownEvidence"].append({"source": "github-list", "detail": str(exc), "stopped": True})
                code = 3
            except UmbrellaWriteError as exc:
                # L4: a bootstrap write GitHub refused is unknown evidence, not an uncaught crash.
                report["unknownEvidence"].append({"source": "github-write", "detail": str(exc), "stopped": True})
                code = 3
    _write_report(report, args.report)
    print(json.dumps({k: report[k] for k in ("issuesCreated", "issuesUpdated", "suppressedDuplicates",
                                             "retainedCandidates", "unknownEvidence")},
                     ensure_ascii=False), file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
