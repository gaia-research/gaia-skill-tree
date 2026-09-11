"""Regression tests for the PR #1792 sandbox review findings on
.github/workflows/intake-approval.yml:

- the maintainer-authorization gate must run before `actions/checkout`
  checks out an issue-body-controlled ref, in both jobs.
- `inputs.base_ref` (a free-form workflow_dispatch string) must be read
  through `env:` rather than interpolated directly into the shell script.
- the failure-comment path must not rely on the exit status of a bare
  `( ... ) 2> >(tee ...)` compound under Actions' default `bash -e {0}`
  shell, which aborts the step before `rc=$?` runs.
- `gh pr create --base` must have a fallback when the resolved base branch
  no longer exists (deleted `dev/*` integration branch).
"""

import pathlib

import yaml

WORKFLOW_PATH = (
    pathlib.Path(__file__).resolve().parents[1] / ".github" / "workflows" / "intake-approval.yml"
)


def _load():
    with open(WORKFLOW_PATH, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _step_names(steps):
    return [step.get("name") or step.get("uses") for step in steps]


def test_workflow_is_valid_yaml():
    doc = _load()
    assert "jobs" in doc
    assert set(doc["jobs"]) == {"topology-approved", "evidence-approved"}


def test_maintainer_check_precedes_checkout_in_both_jobs():
    doc = _load()
    for job_name in ("topology-approved", "evidence-approved"):
        names = _step_names(doc["jobs"][job_name]["steps"])
        maintainer_idx = next(i for i, n in enumerate(names) if n == "Require a repository maintainer")
        checkout_idx = next(i for i, n in enumerate(names) if n == "actions/checkout@v4")
        assert maintainer_idx < checkout_idx, (
            f"{job_name}: maintainer gate (index {maintainer_idx}) must run before "
            f"checkout (index {checkout_idx})"
        )


def test_topology_approved_job_has_a_maintainer_gate():
    """The sandbox review found topology-approved had no gate at all ahead
    of the mutating assemble_gaia.py/validate_intake.py run under
    contents: write. Confirm the gate step exists (in addition to running
    before checkout, asserted above)."""
    doc = _load()
    names = _step_names(doc["jobs"]["topology-approved"]["steps"])
    assert "Require a repository maintainer" in names


def test_base_ref_input_is_read_through_env_not_interpolated():
    """`${{ inputs.base_ref }}` must not be interpolated directly into a
    run: script body (shell-injection vector) -- it must flow through an
    `env:` var and be referenced as a shell variable instead."""
    doc = _load()
    for job_name in ("topology-approved", "evidence-approved"):
        for step in doc["jobs"][job_name]["steps"]:
            run = step.get("run", "")
            code_lines = "\n".join(
                line for line in run.splitlines() if not line.strip().startswith("#")
            )
            assert "${{ inputs.base_ref }}" not in code_lines, (
                f"{job_name}: found direct interpolation of inputs.base_ref in a run: script"
            )
        # The resolve step must instead pull it in via env.
        resolve_step = next(
            s for s in doc["jobs"][job_name]["steps"]
            if (s.get("name") or "").startswith("Resolve")
        )
        assert resolve_step.get("env", {}).get("BASE_REF_INPUT") == "${{ inputs.base_ref }}"
        assert "BASE_REF_INPUT" in resolve_step["run"]


def test_ref_is_validated_against_an_allowlist_before_checkout():
    doc = _load()
    for job_name in ("topology-approved", "evidence-approved"):
        resolve_step = next(
            s for s in doc["jobs"][job_name]["steps"]
            if (s.get("name") or "").startswith("Resolve")
        )
        run = resolve_step["run"]
        assert "main|review/meta/*|dev/*" in run
        assert "gh api" in run and "branches" in run


def test_failure_comment_path_does_not_rely_on_bare_process_substitution():
    """No `2> >(tee ...)` process substitution whose exit status the script
    then reads via a bare `rc=$?` -- that construct is not errexit-exempt
    under Actions' default `bash -e {0}` and made the failure-comment
    branch dead code."""
    doc = _load()
    for job_name in ("topology-approved", "evidence-approved"):
        for step in doc["jobs"][job_name]["steps"]:
            run = step.get("run", "")
            if "rc=$?" not in run:
                continue
            code_lines = "\n".join(
                line for line in run.splitlines() if not line.strip().startswith("#")
            )
            assert "2> >(tee" not in code_lines, (
                f"{job_name}/{step.get('name')}: still uses process-substitution tee as a command"
            )
            assert "set +e" in code_lines, (
                f"{job_name}/{step.get('name')}: rc=$? capture must be wrapped in set +e/set -e"
            )


def test_gh_calls_before_checkout_know_the_repository():
    """Issue #1799: `gh issue view` runs before `actions/checkout`, where there
    is no .git for gh to infer the repo from. Every job must set GH_REPO."""
    doc = _load()
    for job_name in ("topology-approved", "evidence-approved"):
        env = doc["jobs"][job_name].get("env", {})
        assert env.get("GH_REPO") == "${{ github.repository }}", (
            f"{job_name}: GH_REPO must be set at job level for pre-checkout gh calls"
        )


def test_pr_create_base_has_a_fallback_for_deleted_branches():
    doc = _load()
    step = next(
        s for s in doc["jobs"]["evidence-approved"]["steps"]
        if (s.get("name") or "") == "Create or reuse the batch promotion PR"
    )
    run = step["run"]
    assert "pr_base" in run
    assert "git ls-remote" in run
    assert '--base "$pr_base"' in run
