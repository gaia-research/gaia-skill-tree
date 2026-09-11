"""
scripts.upstream_watcher.issuer — GitHub issue creation for the watcher.

Responsible for:
- Rendering issue bodies (umbrella, bootstrap, child intake).
- Idempotency checks (skip if matching open issue already exists).
- ``gh issue create`` invocations.
- Post-creation umbrella body edit to add child-intake cross-references.

Public API
----------
render_umbrella_body(finding, mode)
    Return the full markdown body for an umbrella ``[upstream:release]`` issue.

render_bootstrap_body(finding)
    Return the full markdown body for a ``[upstream:bootstrap]`` issue.

render_child_body(slug, contributor, umbrella_number, suite_gh_url)
    Return the markdown body for a child ``[intake]`` issue.

create_issues(findings, apply, verbose)
    Main entry point: for each finding, check idempotency, create issues
    (if --apply), and return a summary dict.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Label vocab table (embedded in issue bodies, per design §5)
# ---------------------------------------------------------------------------

_LABEL_VOCAB = """
| Label | Meaning |
|---|---|
| `upstream:approved` | Approve — watcher will open a draft sync PR |
| `upstream:rejected` | Reject — skip this release; child intakes auto-closed |
| `upstream:needs-info` | Hold — waiting for more information |
| `skip-child-gate` | Bypass child-intake resolution check (use with `upstream:approved`) |
""".strip()

_REVIEWER_ACTIONS = """
| Action | How |
|---|---|
| Approve sync | Apply `upstream:approved` label |
| Reject | Apply `upstream:rejected` label |
| Hold | Apply `upstream:needs-info` label |
| Force-approve (skip child gate) | Apply `skip-child-gate` + `upstream:approved` |
""".strip()

_BOOTSTRAP_REVIEWER_ACTIONS = """
| Action | How |
|---|---|
| Reject | Apply `upstream:rejected` label |
| Hold | Apply `upstream:needs-info` label |
""".strip()


# ---------------------------------------------------------------------------
# Body renderers
# ---------------------------------------------------------------------------


def _payload_block(payload: dict) -> str:
    """Wrap a dict as a machine-readable payload block in the issue body."""
    json_str = json.dumps(payload, indent=2)
    return (
        "<!-- gaia-upstream-payload\n"
        f"{json_str}\n"
        "-->"
    )


def render_umbrella_body(
    finding: dict,
    mode: str,
    component_adds: list[str],
    component_removes: list[str],
    link_liveness: list[dict],
    name_drift: list[dict] | None = None,
) -> str:
    """Render the full body for an umbrella ``[upstream:release]`` issue."""
    skill_id = finding["skillId"]
    prev_version = finding.get("currentVersion", "none")
    new_version = finding["newVersion"]
    released_at = finding.get("releasedAt", "")
    source_url = finding.get("sourceUrl", "")
    name_drift = name_drift or []

    # Machine-readable payload
    payload = {
        "skillId": skill_id,
        "previousVersion": prev_version,
        "newVersion": new_version,
        "releasedAt": released_at,
        "sourceUrl": source_url,
        "mode": mode,
        "componentAdds": component_adds,
        "componentRemoves": component_removes,
        "linkLiveness": link_liveness,
        "nameDrift": name_drift,
    }

    # Human-readable sections
    adds_section = ""
    if component_adds:
        lines = [f"- `+ {slug}` (child intake: _pending_)" for slug in component_adds]
        adds_section = "\n".join(lines)
    else:
        adds_section = "_No new components detected._"

    removes_section = ""
    if component_removes:
        lines = [f"- `- {slug}` (will be **frozen** on approval)" for slug in component_removes]
        removes_section = "\n".join(lines)
    else:
        removes_section = "_No removed components detected._"

    liveness_section = ""
    if link_liveness:
        rows = [f"| `{r['skillId']}` | `{r['url']}` | `{r['status']}` |"
                for r in link_liveness]
        liveness_section = (
            "| Skill | URL | Status |\n"
            "|---|---|---|\n"
            + "\n".join(rows)
        )
    else:
        liveness_section = "_All component links are healthy._"

    drift_section = ""
    if name_drift:
        rows = [
            f"| `{r['skillId']}` | `{r['registrySlug']}` | `{r['sanitizedName']}` | `{r['fixCommand']}` |"
            for r in name_drift
        ]
        drift_section = (
            "| Skill | Registry slug | Upstream name (sanitized) | Fix |\n"
            "|---|---|---|---|\n"
            + "\n".join(rows)
        )
    else:
        drift_section = "_No slug/name drift detected._"

    mode_note = (
        "**Mode:** `components` — component diff and link-liveness checks were performed."
        if mode == "components"
        else "**Mode:** `version-only` — component layout not detected in upstream repo; only version bump tracked."
    )

    return f"""## Upstream release detected

> Auto-generated by the Gaia upstream watcher. See [upstream-watcher.md](https://github.com/gaia-research/gaia-skill-tree/blob/main/docs/agents/upstream-watcher.md) for the full design spec.

{_payload_block(payload)}

---

### Version

**`{skill_id}`** was at `{prev_version}` → upstream is now **`{new_version}`**
Released: `{released_at}`
Source: {source_url}

{mode_note}

---

### Component changes

**Added upstream:**

{adds_section}

**Removed upstream:**

{removes_section}

---

### Link liveness

{liveness_section}

---

### Name drift (registry slug vs upstream `SKILL.md` name)

> Per [issue #1446](https://github.com/gaia-research/gaia-skill-tree/issues/1446) (Option A), the registry slug is authoritative. A row below means the sanitized upstream frontmatter `name` no longer matches it — apply the listed fix command to realign before this shows up as `DIRNAME_MISMATCH` in an `install_parity.py` sweep.

{drift_section}

---

### Label vocab

{_LABEL_VOCAB}

---

### Reviewer actions

{_REVIEWER_ACTIONS}
"""


def render_bootstrap_body(finding: dict) -> str:
    """Render body for a ``[upstream:bootstrap]`` issue."""
    skill_id = finding["skillId"]
    new_version = finding["newVersion"]
    released_at = finding.get("releasedAt", "")
    source_url = finding.get("sourceUrl", "")

    payload = {
        "skillId": skill_id,
        "previousVersion": None,
        "newVersion": new_version,
        "releasedAt": released_at,
        "sourceUrl": source_url,
        "mode": "bootstrap",
        "componentAdds": [],
        "componentRemoves": [],
        "linkLiveness": [],
    }

    return f"""## Upstream watcher — first-time baseline

> The Gaia upstream watcher has encountered **`{skill_id}`** for the first time.
> No `upstream:` block exists in its frontmatter yet.
>
> This baseline proposal is **automatically approved** (`upstream:approved`) to baseline
> at the current upstream release `{new_version}`. The sync workflow opens a draft PR
> to write the initial `upstream:` block.

{_payload_block(payload)}

---

### Proposed baseline

- **Skill:** `{skill_id}`
- **Baseline version:** `{new_version}`
- **Released:** `{released_at}`
- **Source:** {source_url}

---

### Label vocab

{_LABEL_VOCAB}

---

### Reviewer actions

{_BOOTSTRAP_REVIEWER_ACTIONS}
"""


def render_child_body(
    slug: str,
    contributor: str,
    umbrella_number: int | str,
    suite_gh_url: str,
) -> str:
    """Render body for a child ``[intake]`` issue."""
    # Derive a best-guess skill ID and GitHub link
    # component paths like "skills/foo-bar" → contributor/foo-bar
    owner_repo = None
    from scripts.lib.github_api import parse_owner_repo
    parsed = parse_owner_repo(suite_gh_url)
    if parsed:
        owner_repo = f"{parsed[0]}/{parsed[1]}"

    suggested_id = f"{contributor}/{slug}"
    skill_md_url = ""
    if owner_repo:
        skill_md_url = f"https://github.com/{owner_repo}/blob/main/skills/{slug}/SKILL.md"

    return f"""> Auto-populated by upstream watcher. Umbrella: #{umbrella_number}.

---

## New skill intake proposal

**Suggested ID:** `{suggested_id}`
**Name:** _{slug}_ (update with canonical title from SKILL.md)
**Contributor:** `{contributor}`

### Attribution

- **type:** `attributed`
- **upstream_author:** `{contributor}`

### Evidence

- **type:** `repo`
- **url:** {skill_md_url if skill_md_url else '_unknown — check upstream repo_'}

---

### Description

_Auto-detected from upstream release. Review SKILL.md for the canonical description._

---

### Checklist

- [ ] Confirm skill ID matches upstream directory name
- [ ] Copy description from upstream SKILL.md
- [ ] Verify `links.github` blob URL resolves
- [ ] Assign `genericSkillRef` from the registry
- [ ] Set star level per META.md §2

---

> This issue was auto-created by the Gaia upstream watcher.
> Umbrella: #{umbrella_number}
"""


# ---------------------------------------------------------------------------
# Idempotency check
# ---------------------------------------------------------------------------


def _find_existing_suite_issue(
    prefix: str,
    label: str,
    run_cache: dict[tuple[str, str], Any] | None = None,
) -> tuple[int, str] | None:
    """Return (issue_number, current_title) of an open issue matching *prefix* under *label*, or None.

    Consults *run_cache* first, then queries GitHub for open issues carrying *label*.
    """
    if run_cache is not None:
        cached = run_cache.get((label, prefix))
        if cached is not None:
            if isinstance(cached, tuple):
                return cached
            return (cached, f"{prefix}...")
    try:
        result = subprocess.run(
            [
                "gh", "issue", "list",
                "--label", label,
                "--state", "open",
                "--limit", "100",
                "--json", "number,title",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return None
        issues = json.loads(result.stdout or "[]")
        for issue in issues:
            title = issue.get("title", "")
            if prefix in title:
                return issue["number"], title
    except Exception as exc:  # noqa: BLE001
        print(f"  [warn] suite issue lookup failed: {exc}", file=sys.stderr)
    return None


def _update_issue(
    issue_number: int,
    new_title: str,
    new_body: str,
    comment: str | None = None,
    dry_run: bool = False,
    verbose: bool = False,
) -> bool:
    """Update an existing issue's title, body, and optionally post an update comment."""
    if dry_run:
        if verbose:
            print(f"  [dry-run] Would update issue #{issue_number}: {new_title!r}", file=sys.stderr)
        return True

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as f:
        f.write(new_body)
        body_file = f.name

    try:
        cmd = [
            "gh", "issue", "edit", str(issue_number),
            "--title", new_title,
            "--body-file", body_file,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if res.returncode != 0:
            print(f"  [error] gh issue edit failed for #{issue_number}: {res.stderr}", file=sys.stderr)
            return False
        if comment:
            subprocess.run(
                ["gh", "issue", "comment", str(issue_number), "--body", comment],
                capture_output=True, text=True, timeout=30
            )
        print(f"  Updated existing issue #{issue_number}: {new_title}", file=sys.stderr)
        return True
    finally:
        Path(body_file).unlink(missing_ok=True)


def _dispatch_upstream_approve(
    issue_number: int,
    dry_run: bool = False,
    verbose: bool = False,
) -> bool:
    """Dispatch the upstream-approve workflow for an auto-approved bootstrap issue."""
    if dry_run:
        if verbose:
            print(f"  [dry-run] Would dispatch upstream-approve for #{issue_number}", file=sys.stderr)
        return True

    try:
        cmd = [
            "gh", "workflow", "run", "upstream-approve.yml",
            "-f", f"issue_number={issue_number}",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if res.returncode == 0:
            if verbose:
                print(f"  [auto-bootstrap] Dispatched upstream-approve for #{issue_number}", file=sys.stderr)
            return True
        if verbose:
            print(f"  [auto-bootstrap] Note: gh workflow run returned {res.returncode}: {res.stderr.strip()}", file=sys.stderr)
        return False
    except Exception as exc:  # noqa: BLE001
        if verbose:
            print(f"  [auto-bootstrap] Could not dispatch upstream-approve for #{issue_number}: {exc}", file=sys.stderr)
        return False


def _find_existing_issue(
    search_str: str,
    label: str,
    run_cache: dict[tuple[str, str], int] | None = None,
) -> int | None:
    """Return the number of an open issue matching *search_str* and *label*, or None.

    GitHub's issue search index is eventually consistent: an issue created
    seconds ago is not yet findable by ``gh issue list --search``.  A single
    watcher run routinely emits several findings that collapse onto the same
    umbrella (one per skill in a multi-skill upstream repo), so relying on the
    index alone let identical issues through in the same run.  *run_cache*
    remembers what this process already created and is consulted first.
    """
    if run_cache is not None:
        cached = run_cache.get((label, search_str))
        if cached is not None:
            return cached
    try:
        result = subprocess.run(
            [
                "gh", "issue", "list",
                "--label", label,
                "--state", "open",
                "--search", search_str,
                "--json", "number,title",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return None
        issues = json.loads(result.stdout or "[]")
        for issue in issues:
            if search_str in issue.get("title", ""):
                return issue["number"]
    except Exception as exc:  # noqa: BLE001
        print(f"  [warn] idempotency check failed: {exc}", file=sys.stderr)
    return None


# ---------------------------------------------------------------------------
# Issue creation
# ---------------------------------------------------------------------------


def _create_issue(
    title: str,
    labels: list[str],
    body: str,
    dry_run: bool,
    verbose: bool = False,
) -> int | None:
    """Create a GitHub issue.  Returns the new issue number or None."""
    if dry_run:
        if verbose:
            print(f"  [dry-run] Would create issue: {title!r}", file=sys.stderr)
        return None

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as f:
        f.write(body)
        body_file = f.name

    try:
        cmd = [
            "gh", "issue", "create",
            "--title", title,
            "--label", ",".join(labels),
            "--body-file", body_file,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            print(
                f"  [error] gh issue create failed: {result.stderr}",
                file=sys.stderr,
            )
            return None
        # Output is the issue URL; extract number
        url = result.stdout.strip()
        m = re.search(r"/issues/(\d+)", url)
        if m:
            num = int(m.group(1))
            print(f"  Created issue #{num}: {title}", file=sys.stderr)
            return num
        return None
    finally:
        Path(body_file).unlink(missing_ok=True)


def _edit_umbrella_body(
    umbrella_number: int,
    child_numbers: list[int],
    dry_run: bool,
) -> None:
    """Append child-intake cross-references to the umbrella issue body."""
    if dry_run or not child_numbers:
        return
    refs = ", ".join(f"#{n}" for n in child_numbers)
    comment_body = f"Child intakes: {refs}"
    try:
        subprocess.run(
            [
                "gh", "issue", "comment",
                str(umbrella_number),
                "--body", comment_body,
            ],
            check=True,
            capture_output=True,
            timeout=30,
        )
    except Exception as exc:  # noqa: BLE001
        print(
            f"  [warn] Could not comment child refs on #{umbrella_number}: {exc}",
            file=sys.stderr,
        )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def create_issues(
    full_findings: list[dict],
    apply: bool,
    verbose: bool = False,
) -> list[dict]:
    """Process all findings and create issues.

    Parameters
    ----------
    full_findings:
        Each dict has keys: finding_type, skillId, mode, currentVersion,
        newVersion, releasedAt, sourceUrl, componentAdds, componentRemoves,
        linkLiveness.
    apply:
        If False, dry-run mode — print but don't create.
    verbose:
        Extra logging.

    Returns
    -------
    list[dict]
        Summary records per finding.
    """
    summaries: list[dict] = []
    # Issues created by *this* run, keyed (label, title-fragment).  GitHub's
    # search index lags creation by seconds, so this is the only reliable
    # dedup for findings that collapse onto one issue within a single run.
    run_cache: dict[tuple[str, str], int] = {}

    for finding in full_findings:
        skill_id = finding["skillId"]
        finding_type = finding["finding_type"]
        new_version = finding["newVersion"]
        contributor = skill_id.split("/")[0] if "/" in skill_id else skill_id

        # ── Bootstrap ──────────────────────────────────────────────────────
        if finding_type == "bootstrap":
            title = f"[upstream:bootstrap] {skill_id} → baseline at {new_version}"
            suite_prefix = f"[upstream:bootstrap] {skill_id} → baseline at "
            existing_suite = _find_existing_suite_issue(
                suite_prefix, "upstream:bootstrap", run_cache
            )
            if existing_suite:
                existing_num, existing_title = existing_suite
                if existing_title == title:
                    print(
                        f"  Bootstrap for {skill_id}@{new_version} already exists as #{existing_num}; skipping.",
                        file=sys.stderr,
                    )
                    summaries.append(
                        {"type": "bootstrap", "skillId": skill_id, "skipped": True, "issue": existing_num}
                    )
                    run_cache[("upstream:bootstrap", suite_prefix)] = (existing_num, title)
                    continue

                # Existing issue was for an older version -> update it in place!
                body = render_bootstrap_body(finding)
                prev_v = existing_title.removeprefix(suite_prefix)
                comment = f"Updated baseline version to: **`{new_version}`** (previously `{prev_v}`)."
                _update_issue(
                    existing_num,
                    title,
                    body,
                    comment=comment,
                    dry_run=not apply,
                    verbose=verbose,
                )
                run_cache[("upstream:bootstrap", suite_prefix)] = (existing_num, title)
                if apply:
                    _dispatch_upstream_approve(existing_num, dry_run=False, verbose=verbose)
                summaries.append(
                    {"type": "bootstrap", "skillId": skill_id, "skipped": False, "updated": True, "issue": existing_num}
                )
                continue

            body = render_bootstrap_body(finding)
            issue_num = _create_issue(
                title,
                ["upstream:bootstrap", "upstream:approved"],
                body,
                dry_run=not apply,
                verbose=verbose,
            )
            if issue_num:
                run_cache[("upstream:bootstrap", suite_prefix)] = (issue_num, title)
                if apply:
                    _dispatch_upstream_approve(issue_num, dry_run=False, verbose=verbose)
            summaries.append(
                {"type": "bootstrap", "skillId": skill_id, "skipped": False, "issue": issue_num}
            )
            continue

        # ── Update umbrella ────────────────────────────────────────────────
        owner_repo_str = skill_id  # fallback
        source_url = finding.get("sourceUrl", "")
        from scripts.lib.github_api import parse_owner_repo as _parse
        parsed = _parse(source_url) if source_url else None
        if parsed:
            owner_repo_str = f"{parsed[0]}/{parsed[1]}"

        umbrella_title = f"[upstream] {owner_repo_str} → {new_version}"
        suite_prefix = f"[upstream] {owner_repo_str} → "
        existing_suite = _find_existing_suite_issue(
            suite_prefix, "upstream:release", run_cache
        )

        component_adds = finding.get("componentAdds", [])
        component_removes = finding.get("componentRemoves", [])
        link_liveness = finding.get("linkLiveness", [])
        name_drift = finding.get("nameDrift", [])
        mode = finding.get("mode", "version-only")

        if existing_suite:
            existing_num, existing_title = existing_suite
            if existing_title == umbrella_title:
                print(
                    f"  Umbrella for {owner_repo_str}@{new_version} already exists as #{existing_num}; skipping.",
                    file=sys.stderr,
                )
                summaries.append(
                    {
                        "type": "update",
                        "skillId": skill_id,
                        "skipped": True,
                        "issue": existing_num,
                    }
                )
                run_cache[("upstream:release", suite_prefix)] = (existing_num, umbrella_title)
                continue

            # Older release umbrella exists for the same suite -> update in place!
            umbrella_body = render_umbrella_body(
                finding, mode, component_adds, component_removes, link_liveness, name_drift
            )
            prev_v = existing_title.removeprefix(suite_prefix)
            comment = (
                f"Updated umbrella for new upstream release: **`{new_version}`** (previously `{prev_v}`). "
                "Payload, component diff, and link-liveness refreshed."
            )
            _update_issue(
                existing_num,
                umbrella_title,
                umbrella_body,
                comment=comment,
                dry_run=not apply,
                verbose=verbose,
            )
            umbrella_num = existing_num
            run_cache[("upstream:release", suite_prefix)] = (existing_num, umbrella_title)
            is_update = True
        else:
            umbrella_body = render_umbrella_body(
                finding, mode, component_adds, component_removes, link_liveness, name_drift
            )
            umbrella_num = _create_issue(
                umbrella_title,
                ["upstream:release", "needs-triage"],
                umbrella_body,
                dry_run=not apply,
                verbose=verbose,
            )
            if umbrella_num:
                run_cache[("upstream:release", suite_prefix)] = (umbrella_num, umbrella_title)
            is_update = False

        # ── Child intakes for added components ────────────────────────────
        child_numbers: list[int] = []
        suite_gh = finding.get("sourceUrl", "")

        for slug in component_adds:
            child_title = f"[intake] {contributor}/{slug}"
            child_key = f"[intake] {contributor}/{slug}"
            existing_child = _find_existing_issue(child_key, "intake", run_cache)
            if existing_child:
                print(
                    f"  Child intake for {contributor}/{slug} already exists as #{existing_child}; skipping.",
                    file=sys.stderr,
                )
                child_numbers.append(existing_child)
                continue

            child_body = render_child_body(
                slug=slug,
                contributor=contributor,
                umbrella_number=umbrella_num or "?",
                suite_gh_url=suite_gh,
            )
            child_num = _create_issue(
                child_title,
                ["intake", "needs-triage", "upstream:child"],
                child_body,
                dry_run=not apply,
                verbose=verbose,
            )
            if child_num:
                run_cache[("intake", child_key)] = child_num
                child_numbers.append(child_num)

        # Edit umbrella to list child refs
        if umbrella_num:
            _edit_umbrella_body(umbrella_num, child_numbers, dry_run=not apply)

        summaries.append(
            {
                "type": "update",
                "skillId": skill_id,
                "umbrella": umbrella_num,
                "children": child_numbers,
                "skipped": False,
                "updated": is_update,
            }
        )

    return summaries
