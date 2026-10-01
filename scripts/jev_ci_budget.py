#!/usr/bin/env python3
"""
jev_ci_budget.py — GitHub Actions run-history budget gate for Jev advisory CI lane.

Enforces a conservative monthly run ceiling using GitHub Actions workflow run
history (NOT cache) as the spending ledger. Fails closed on API errors,
malformed payloads, missing current runs, created-month mismatches, or run attempts > 1.

Budget math:
  <=60 runs/month * <=20 calls/run * $0.003 reservation/call = $3.60/month CI ceiling.
  Local default envelope: $0.50/month.
  Unallocated buffer: $0.90 of the $5.00/month provider envelope.
  Per approved run: --monthly-limit-usd 0.06 --max-calls 20.

Limitations:
  - External shared account usage outside this workflow cannot be tracked by run history.
  - Deletion of GitHub Actions run history would bypass this count; require provider-side caps.
"""

from __future__ import annotations

import argparse
import calendar
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union

MAX_MONTHLY_RUNS = 60
MAX_CALLS_PER_RUN = 20
RESERVATION_USD_PER_CALL = 0.003
MONTHLY_CI_CAP_USD = 3.60
LOCAL_DEFAULT_CAP_USD = 0.50
UNUSED_BUFFER_USD = 0.90
PER_RUN_LIMIT_USD = 0.06
DEFAULT_WORKFLOW = "jev-advisory.yml"


def evaluate_ci_budget(
    runs_data: Optional[Dict[str, Any]],
    current_run_id: Union[int, str, None],
    run_attempt: Union[int, str, None] = 1,
    current_time: Optional[datetime] = None,
    max_monthly_runs: int = MAX_MONTHLY_RUNS,
) -> Dict[str, Any]:
    """
    Evaluate whether the current CI run is authorized to make paid Jev calls.
    Fails closed on any unexpected, missing, or mismatched data.
    """
    # 0. Validate cap: must be a positive integer, hard-capped at MAX_MONTHLY_RUNS (60)
    if max_monthly_runs is None or isinstance(max_monthly_runs, bool):
        return {
            "allowed": False,
            "reason": "invalid_cap",
            "message": f"Cap max_monthly_runs '{max_monthly_runs}' is missing or boolean.",
        }
    try:
        cap_int = int(max_monthly_runs)
    except (ValueError, TypeError):
        return {
            "allowed": False,
            "reason": "invalid_cap",
            "message": f"Cap max_monthly_runs '{max_monthly_runs}' is not an integer.",
        }
    if cap_int <= 0:
        return {
            "allowed": False,
            "reason": "invalid_cap",
            "message": f"Cap max_monthly_runs ({cap_int}) must be positive.",
        }
    # Enforce hard ceiling of MAX_MONTHLY_RUNS (60); never relax budget beyond 60
    effective_cap = min(cap_int, MAX_MONTHLY_RUNS)

    # 1. Parse run_attempt — fail closed if not first attempt (no paid reruns)
    if isinstance(run_attempt, bool):
        return {
            "allowed": False,
            "reason": "invalid_run_attempt",
            "message": f"Run attempt '{run_attempt}' is a boolean.",
        }
    try:
        attempt_int = int(run_attempt) if run_attempt is not None else 1
    except (ValueError, TypeError):
        return {
            "allowed": False,
            "reason": "invalid_run_attempt",
            "message": f"Run attempt '{run_attempt}' could not be parsed as an integer.",
        }

    if attempt_int != 1:
        return {
            "allowed": False,
            "reason": "rerun_not_permitted",
            "message": f"Run attempt {attempt_int} != 1. Reruns are blocked from making paid calls.",
        }

    # 2. Parse current_run_id
    if current_run_id is None or str(current_run_id).strip() == "":
        return {
            "allowed": False,
            "reason": "missing_run_id",
            "message": "Current run ID is required for CI budget validation.",
        }
    if isinstance(current_run_id, bool):
        return {
            "allowed": False,
            "reason": "invalid_run_id",
            "message": f"Run ID '{current_run_id}' is a boolean.",
        }
    try:
        run_id_int = int(current_run_id)
    except (ValueError, TypeError):
        return {
            "allowed": False,
            "reason": "invalid_run_id",
            "message": f"Run ID '{current_run_id}' is not a valid integer.",
        }

    # 3. Determine current UTC month
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    elif current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    current_month_str = current_time.strftime("%Y-%m")

    # 4. Validate runs_data shape
    if not isinstance(runs_data, dict):
        return {
            "allowed": False,
            "reason": "api_error",
            "message": "Workflow runs data is missing or not a dictionary.",
        }

    if "total_count" not in runs_data:
        return {
            "allowed": False,
            "reason": "malformed_payload",
            "message": "Runs payload is missing 'total_count'.",
        }

    raw_total = runs_data["total_count"]
    if isinstance(raw_total, bool) or not isinstance(raw_total, int):
        return {
            "allowed": False,
            "reason": "malformed_payload",
            "message": f"Runs payload total_count must be an integer, not boolean or other type: {type(raw_total).__name__}.",
        }

    total_count = raw_total
    if total_count < 0:
        return {
            "allowed": False,
            "reason": "malformed_payload",
            "message": f"Negative total_count in runs payload: {total_count}.",
        }

    if "workflow_runs" not in runs_data or not isinstance(runs_data["workflow_runs"], list):
        return {
            "allowed": False,
            "reason": "malformed_payload",
            "message": "Runs payload is missing valid list 'workflow_runs'.",
        }

    runs_list = runs_data["workflow_runs"]
    if not all(isinstance(run, dict) for run in runs_list):
        return {
            "allowed": False,
            "reason": "malformed_payload",
            "message": "Runs payload contains non-dict elements in workflow_runs.",
        }

    # Catch mismatched total_count and list length including 0
    if total_count == 0 and len(runs_list) != 0:
        return {
            "allowed": False,
            "reason": "malformed_payload",
            "message": f"Mismatched total_count (0) with non-empty workflow_runs ({len(runs_list)} items).",
        }
    if total_count > 0 and len(runs_list) == 0:
        return {
            "allowed": False,
            "reason": "malformed_payload",
            "message": f"Mismatched total_count ({total_count}) with empty workflow_runs list.",
        }
    if total_count < len(runs_list):
        return {
            "allowed": False,
            "reason": "malformed_payload",
            "message": f"total_count ({total_count}) is less than workflow_runs length ({len(runs_list)}).",
        }

    # 5. Locate current run in workflow_runs list
    current_run: Optional[Dict[str, Any]] = None
    for run in runs_list:
        if run.get("id") == run_id_int:
            current_run = run
            break

    if current_run is None:
        return {
            "allowed": False,
            "reason": "current_run_not_found",
            "message": f"Run ID {run_id_int} was not found in the workflow run history for this month.",
        }

    # 6. Check created_at of current run against current UTC month
    created_at_raw = current_run.get("created_at")
    if not created_at_raw or not isinstance(created_at_raw, str):
        return {
            "allowed": False,
            "reason": "missing_created_at",
            "message": f"Run ID {run_id_int} is missing 'created_at' timestamp.",
        }

    try:
        # Standard GitHub timestamp: '2026-10-01T08:00:00Z'
        clean_ts = created_at_raw.replace("Z", "+00:00")
        created_dt = datetime.fromisoformat(clean_ts)
        run_month_str = created_dt.strftime("%Y-%m")
    except Exception as exc:
        return {
            "allowed": False,
            "reason": "invalid_created_at",
            "message": f"Could not parse 'created_at' timestamp '{created_at_raw}': {exc}",
        }

    if run_month_str != current_month_str:
        return {
            "allowed": False,
            "reason": "created_month_mismatch",
            "message": (
                f"Current run created month ({run_month_str}) does not match "
                f"current UTC month ({current_month_str})."
            ),
        }

    # 7. Check run_attempt on the GitHub Actions record itself if present
    run_record_attempt = current_run.get("run_attempt")
    if run_record_attempt is not None:
        if isinstance(run_record_attempt, bool):
            return {
                "allowed": False,
                "reason": "malformed_payload",
                "message": f"Run record attempt is a boolean: {run_record_attempt}.",
            }
        try:
            record_attempt_int = int(run_record_attempt)
        except (ValueError, TypeError):
            return {
                "allowed": False,
                "reason": "malformed_payload",
                "message": f"Run record attempt '{run_record_attempt}' is not a valid integer.",
            }
        if record_attempt_int < 1:
            return {
                "allowed": False,
                "reason": "malformed_payload",
                "message": f"Run record attempt {record_attempt_int} < 1 is invalid.",
            }
        if record_attempt_int != 1:
            return {
                "allowed": False,
                "reason": "rerun_not_permitted",
                "message": f"Run record attempt {record_attempt_int} != 1 in GitHub Actions history.",
            }

    # 8. Check monthly run count against cap
    if total_count > effective_cap:
        return {
            "allowed": False,
            "reason": "monthly_run_limit_exceeded",
            "month": current_month_str,
            "monthly_runs_count": total_count,
            "max_monthly_runs": effective_cap,
            "message": (
                f"Monthly run count ({total_count}) exceeds conservative ceiling ({effective_cap})."
            ),
        }

    # 9. Approved
    estimated_spent = round(total_count * PER_RUN_LIMIT_USD, 4)
    return {
        "allowed": True,
        "reason": "budget_approved",
        "month": current_month_str,
        "current_run_id": run_id_int,
        "run_attempt": attempt_int,
        "monthly_runs_count": total_count,
        "max_monthly_runs": effective_cap,
        "per_run_limit_usd": PER_RUN_LIMIT_USD,
        "max_calls_per_run": MAX_CALLS_PER_RUN,
        "reservation_usd_per_call": RESERVATION_USD_PER_CALL,
        "monthly_ci_cap_usd": MONTHLY_CI_CAP_USD,
        "local_default_cap_usd": LOCAL_DEFAULT_CAP_USD,
        "unused_buffer_usd": UNUSED_BUFFER_USD,
        "estimated_spent_usd": estimated_spent,
        "limitations": [
            "Shared account usage outside this workflow is not tracked by run history",
            "Configure account spend caps if supported by provider rather than assuming dashboard enforcement",
            "Deletion of GitHub Actions run history would bypass this count; enforce administrative controls",
        ],
    }


def fetch_workflow_runs_gh(
    repo: str,
    workflow: str,
    created_filter: str,
) -> Optional[Dict[str, Any]]:
    """Fetch workflow runs using the authenticated `gh` CLI."""
    cmd = [
        "gh",
        "api",
        "--method",
        "GET",
        f"repos/{repo}/actions/workflows/{workflow}/runs",
        "-F",
        f"created={created_filter}",
        "-F",
        "per_page=100",
    ]
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=20,
        )
        if proc.returncode != 0:
            sys.stderr.write(f"gh api error: {proc.stderr}\n")
            return None
        return json.loads(proc.stdout)
    except Exception as exc:
        sys.stderr.write(f"Failed to fetch runs via gh CLI: {exc}\n")
        return None


def fetch_workflow_runs_http(
    repo: str,
    workflow: str,
    created_filter: str,
    token: str,
) -> Optional[Dict[str, Any]]:
    """Fetch workflow runs directly via GitHub REST API."""
    params = urllib.parse.urlencode({"created": created_filter, "per_page": 100})
    url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow}/runs?{params}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "gaia-jev-ci-budget-gate",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)
    except Exception as exc:
        sys.stderr.write(f"Failed to fetch runs via HTTP: {exc}\n")
        return None


def fetch_runs(
    repo: str,
    workflow: str,
    current_time: datetime,
    token: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Determine month date filter and fetch runs from GitHub API."""
    year = current_time.year
    month = current_time.month
    last_day = calendar.monthrange(year, month)[1]
    created_filter = f"{year:04d}-{month:02d}-01..{year:04d}-{month:02d}-{last_day:02d}"

    # Try gh CLI first if token not explicitly supplied or if in GH Actions
    data = fetch_workflow_runs_gh(repo, workflow, created_filter)
    if data is not None:
        return data

    if token:
        return fetch_workflow_runs_http(repo, workflow, created_filter, token)

    return None


def write_github_output(result: Dict[str, Any]) -> None:
    """Write outputs to $GITHUB_OUTPUT file if running inside GitHub Actions."""
    gh_output_path = os.environ.get("GITHUB_OUTPUT")
    if not gh_output_path:
        return
    try:
        with open(gh_output_path, "a", encoding="utf-8") as f:
            allowed_str = "true" if result.get("allowed") else "false"
            f.write(f"allowed={allowed_str}\n")
            f.write(f"reason={result.get('reason', 'unknown')}\n")
            f.write(f"month={result.get('month', '')}\n")
            f.write(f"monthly_runs={result.get('monthly_runs_count', 0)}\n")
            f.write(f"max_calls={result.get('max_calls_per_run', MAX_CALLS_PER_RUN)}\n")
            f.write(f"per_run_limit_usd={result.get('per_run_limit_usd', PER_RUN_LIMIT_USD)}\n")
    except Exception as exc:
        sys.stderr.write(f"Warning: could not write to GITHUB_OUTPUT: {exc}\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check GitHub Actions run history budget gate for Jev advisory lane."
    )
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", "gaia-research/gaia-skill-tree"))
    parser.add_argument("--workflow", default=DEFAULT_WORKFLOW)
    parser.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID"))
    parser.add_argument("--run-attempt", default=os.environ.get("GITHUB_RUN_ATTEMPT", "1"))
    parser.add_argument("--runs-json", help="Path to pre-fetched runs JSON (offline testable)")
    parser.add_argument("--current-time", help="ISO 8601 UTC timestamp for testing month alignment")
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN"))
    parser.add_argument("--max-monthly-runs", type=int, default=MAX_MONTHLY_RUNS)
    parser.add_argument("--strict", action="store_true", help="Exit 1 if budget check is blocked")
    parser.add_argument("--json", action="store_true", help="Emit raw JSON evaluation result")

    args = parser.parse_args()

    # Determine current timestamp
    if args.current_time:
        try:
            current_time = datetime.fromisoformat(args.current_time.replace("Z", "+00:00"))
        except Exception as exc:
            res = {
                "allowed": False,
                "reason": "invalid_current_time",
                "message": f"Failed to parse --current-time: {exc}",
            }
            write_github_output(res)
            print(json.dumps(res, indent=2))
            return 1 if args.strict else 0
    else:
        current_time = datetime.now(timezone.utc)

    # Load or fetch runs data
    runs_data: Optional[Dict[str, Any]] = None
    if args.runs_json:
        try:
            with open(args.runs_json, "r", encoding="utf-8") as f:
                runs_data = json.load(f)
        except Exception as exc:
            res = {
                "allowed": False,
                "reason": "file_read_error",
                "message": f"Failed to read runs JSON from '{args.runs_json}': {exc}",
            }
            write_github_output(res)
            print(json.dumps(res, indent=2))
            return 1 if args.strict else 0
    else:
        runs_data = fetch_runs(args.repo, args.workflow, current_time, args.token)

    # Enforce hard ceiling on max_monthly_runs; never relax budget beyond MAX_MONTHLY_RUNS (60)
    if args.max_monthly_runs is not None:
        if args.max_monthly_runs > MAX_MONTHLY_RUNS:
            sys.stderr.write(
                f"Warning: --max-monthly-runs ({args.max_monthly_runs}) exceeds hard ceiling "
                f"of {MAX_MONTHLY_RUNS}. Clamping to {MAX_MONTHLY_RUNS}.\n"
            )
            args.max_monthly_runs = MAX_MONTHLY_RUNS

    result = evaluate_ci_budget(
        runs_data=runs_data,
        current_run_id=args.run_id,
        run_attempt=args.run_attempt,
        current_time=current_time,
        max_monthly_runs=args.max_monthly_runs,
    )

    write_github_output(result)

    if args.json or not sys.stdout.isatty():
        print(json.dumps(result, indent=2))
    else:
        status_label = "ALLOWED" if result["allowed"] else "BLOCKED"
        print(f"Jev CI Budget Gate: {status_label}")
        print(f"Reason: {result['reason']}")
        if "message" in result:
            print(f"Details: {result['message']}")
        if result["allowed"]:
            print(f"Current UTC Month: {result['month']}")
            print(f"Monthly Runs Count: {result['monthly_runs_count']} / {result['max_monthly_runs']}")
            print(f"Per-Run Limit: ${result['per_run_limit_usd']:.2f} ({result['max_calls_per_run']} calls max)")
            print(f"Estimated Monthly CI Spent: ${result['estimated_spent_usd']:.4f} / ${result['monthly_ci_cap_usd']:.2f}")

    if args.strict and not result["allowed"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
