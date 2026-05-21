#!/usr/bin/env bash
set -euo pipefail

# Triage/update Gaia GitHub issues without changing repo code.
#
# Default mode is a dry run that prints the comments/actions.
# Run with --apply to post comments with GitHub CLI.
# Run with --apply --close-resolved to close issues that appear resolved/outdated.
#
# Requirements for --apply:
#   gh auth login
#   gh auth status
#
# Optional:
#   REPO=owner/name scripts/triage_outdated_issues.sh --apply

REPO="${REPO:-mbtiongson1/gaia-skill-tree}"
APPLY=0
CLOSE_RESOLVED=0

usage() {
  cat <<USAGE
Usage: $0 [--apply] [--close-resolved]

Posts triage comments for likely outdated/stale Gaia issues.

Options:
  --apply            Actually post comments using gh. Without this, prints a dry run.
  --close-resolved   With --apply, close issues that appear resolved/outdated (#65, #134, #182).
  -h, --help         Show this help.

Environment:
  REPO               GitHub repo, default: ${REPO}
USAGE
}

for arg in "$@"; do
  case "$arg" in
    --apply)
      APPLY=1
      ;;
    --close-resolved)
      CLOSE_RESOLVED=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "$APPLY" -eq 1 ]]; then
  if ! command -v gh >/dev/null 2>&1; then
    echo "error: gh is required for --apply. Install GitHub CLI and run gh auth login." >&2
    exit 1
  fi
  gh auth status >/dev/null
fi

comment_issue() {
  local issue="$1"
  local body
  body="$(cat)"

  if [[ "$APPLY" -eq 1 ]]; then
    echo "Commenting on #${issue}..."
    gh issue comment "$issue" --repo "$REPO" --body "$body"
  else
    echo "--- DRY RUN: would comment on #${issue} in ${REPO} ---"
    printf '%s\n' "$body"
    echo
  fi
}

close_issue() {
  local issue="$1"
  local reason="$2"

  if [[ "$CLOSE_RESOLVED" -ne 1 ]]; then
    return 0
  fi

  if [[ "$APPLY" -eq 1 ]]; then
    echo "Closing #${issue}..."
    gh issue close "$issue" --repo "$REPO" --reason completed --comment "$reason"
  else
    echo "--- DRY RUN: would close #${issue} in ${REPO} ---"
    printf '%s\n\n' "$reason"
  fi
}

comment_issue 65 <<'BODY'
Triage update: this appears implemented in the current checkout.

Evidence:
- `src/gaia_cli/commands/stats.py` contains the stats collection/rendering command.
- `README.md` documents `gaia stats`.
- `tests/test_stats.py` covers collection, rendering, and CLI output.

Recommendation: close this issue after maintainer review, or retitle it to any remaining stats polish that is not already covered by the current command.
BODY
close_issue 65 'Closing as implemented by the current gaia stats command and tests. Please reopen or file a narrower follow-up if specific stats polish remains.'

comment_issue 182 <<'BODY'
Triage update: I could not reproduce current docs drift.

Verification command:

```bash
python scripts/build_docs.py --check
```

Current result: documentation is up to date.

Recommendation: close this issue if it only tracks the already-fixed drift. If the real ask is release-process enforcement, retitle this as a release automation hardening issue, e.g. "Ensure docs build runs with every version bump".
BODY
close_issue 182 'Closing because python scripts/build_docs.py --check reports the generated docs are currently up to date. Please reopen or retitle if release-process enforcement is still needed.'

comment_issue 134 <<'BODY'
Triage update: this appears outdated or already addressed in the current CLI/package tests.

Evidence:
- `gaia docs build` resolves the registry path before calling `scripts/build_docs.py`.
- `tests/test_packaging.py` includes coverage that `python -m gaia_cli docs build --check` can run from a registry clone without passing `--registry` explicitly.

Recommendation: close if no current reproduction remains. If this still fails in a specific install mode, please update the issue with the exact command, working directory, and install method.
BODY
close_issue 134 "Closing as outdated based on current docs-build behavior and packaging coverage. Please reopen with a current reproduction if this still fails."

comment_issue 181 <<'BODY'
Triage update: this still looks valid, but the acceptance criteria should be narrowed.

Current root cause still appears to be that packaging tests call `python -m build`, while `build` is in the `dev` extra, not the `embeddings` extra.

Recommended resolution options:
1. Docs-only: document `pip install -e ".[embeddings,dev]"` for running the full test suite.
2. Test behavior: skip packaging-only tests when `build` is unavailable, with a message telling contributors to install `.[dev]`.
3. Dependency policy: move `build` to a broader contributor extra if packaging tests are expected in the default local suite.

Recommendation: keep open, but choose one of the options above and update the issue title/body accordingly.
BODY

comment_issue 180 <<'BODY'
Triage update: this still looks like a valid CLI bug and should stay open until fixed.

Current expected fix scope:
- Normalize display-style named skill IDs such as `/huggingface/hf-cli` before `skills info` matching.
- Normalize the same input before named-skill install resolution.
- Add regression tests for both `gaia skills info /contributor/name` and `gaia skills install /contributor/name`.

Recommendation: keep open and mark as ready for implementation.
BODY

comment_issue 71 <<'BODY'
Triage update: this issue is partially stale because the proposed command shape references `gaia lookup`, while the current CLI exposes named-skill discovery through `gaia skills list/search/info/install/uninstall`.

Recommendation: keep the feature request if bucket variants are still desired, but retitle/reframe around one of these paths:
- extend `gaia skills info <skill>` to show all bucket variants, or
- add a new `gaia lookup <skill>` command explicitly as part of this issue.

This should stay blocked on the bucket/origin/variant data model being finalized.
BODY

comment_issue 64 <<'BODY'
Triage update: this still looks valid as an enhancement, but it should be treated as deferred rather than stale.

Current state:
- There is no registered `gaia browse` subcommand.
- Adding a TUI likely needs an explicit optional dependency policy and fallback UX decision.

Recommendation: keep open, mark as enhancement/deferred, and split dependency-policy discussion from implementation if needed.
BODY

comment_issue 118 <<'BODY'
Triage update: this needs a fresh reproduction before implementation.

The promotion UI and rank/effective-level behavior have changed enough that the original screenshot may no longer describe the current output exactly.

Recommendation: keep open, but ask for current output from:

```bash
gaia scan
gaia appraise <affected-skill>
```

Then narrow this issue to the specific card rendering/title problems still present.
BODY

comment_issue 119 <<'BODY'
Triage update: this needs a current duplicate inventory before implementation.

Recommendation: keep open, but update the issue with:
- exact duplicate skill IDs/names observed in the latest `registry/gaia.json`,
- whether the duplication is canonical skills, named implementations, or display buckets,
- expected consolidation behavior.

This likely overlaps with bucket/origin/variant work, so it may need to be linked to the named-skill duplicate/bucket issues.
BODY

cat <<DONE
Done.
Mode: $([[ "$APPLY" -eq 1 ]] && echo apply || echo dry-run)
Repo: ${REPO}
Close resolved: $([[ "$CLOSE_RESOLVED" -eq 1 ]] && echo yes || echo no)
DONE
