"""Hosted read-only P2 weekly census CLI entrypoint.

Enforces ``state_mode="ephemeral-empty"``, validates ``census_scope.json``,
module digests (when pinned), local registry authority, and the pinned
historical authority commit before any network I/O. Writes only a bounded
redacted receipt JSON with zero raw issue/comment bodies, headers, or tokens.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from scripts.lib.named_iterator import iter_named_skills
from scripts.upstream_watcher import envelope, prechecks, repository_batch, weekly_census, weekly_collector
from scripts.upstream_watcher.approval import PayloadError
from scripts.upstream_watcher.live import GhError, SuiteUnavailable, UnknownEvidenceError
from scripts.upstream_watcher.readonly_issue_port import HostedUpstreamClient, ReadOnlyIssuePort

EXPECTED_REPOSITORY = "gaia-research/gaia-skill-tree"
EXPECTED_QUARANTINE_REF = "refs/heads/census/p2-hosted-readonly-2026-11"
EXPECTED_HISTORICAL_COMMIT = "9b4d9b98043140188f00b14d0ac8fa6bc02491b7"
EXPECTED_BASELINE_COUNT = 81
EXPECTED_BASELINE_SHA256 = "c369ea43b3733aeb2c915ee3f185ea7451d9c38808a37a26e22431b3440db28b"
BASELINE_RECORDS_REL = Path("founder/reports/upstream-backlog-2026-11/BASELINE_UPSTREAM_RECORDS.json")
BASELINE_METADATA_REL = Path("founder/reports/upstream-backlog-2026-11/BASELINE_UPSTREAM_METADATA.json")
EXPECTED_BASELINE_FILES_SHA256: dict[Path, str] = {
    BASELINE_RECORDS_REL: "9d135a5fd84bf9bda2473b4dca4eabd5f28c599e6b6e52456a663326a1b69b48",
    BASELINE_METADATA_REL: "c14a5301b111ca2f0713e282a8478e23c7d8866072f22939fb354e4b2f723a51",
}
EXPECTED_SCOPE_COUNT = 14
DEFAULT_SCOPE_PATH = Path(__file__).with_name("census_scope.json")
EXPECTED_WORKFLOW_REF = (
    f"{EXPECTED_REPOSITORY}/.github/workflows/upstream-watcher.yml@{EXPECTED_QUARANTINE_REF}"
)

_HEX40_RE = re.compile(r"[0-9a-f]{40}")
_RUN_ID_RE = re.compile(r"[0-9]{1,20}")
_SAFE_PROV_RE = re.compile(r"[A-Za-z0-9._/@:-]{1,256}")
MAX_EVENT_BYTES = 256 * 1024

_ALLOWED_DISPATCH_KEYS = frozenset({
    "apply",
    "child_mode",
    "staging",
    "skill_id",
    "staging_bootstrap",
    "challenge_watch",
    "challenge_shadow",
    "permission_ab",
    "metadata_probe",
    "escalate_candidate",
    "challenge_input",
})
_OMISSIBLE_FALSE_SWITCHES = frozenset({
    "staging_bootstrap",
    "challenge_watch",
    "challenge_shadow",
    "permission_ab",
    "metadata_probe",
})
_OMISSIBLE_BLANK_INPUTS = frozenset({"skill_id", "escalate_candidate", "challenge_input"})


def validate_workflow_dispatch_payload(payload_inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Validate wire dispatch inputs without requiring branch-only seed inputs.

    Allows omission (treated as default false/blank) only for explicitly
    understood default-valued switches; rejects truthy switches and extra keys.
    """
    if not isinstance(payload_inputs, Mapping):
        raise HostedCensusRefusal("invalid-dispatch-inputs-shape")
    extra = set(payload_inputs.keys()) - _ALLOWED_DISPATCH_KEYS
    if extra:
        raise HostedCensusRefusal("unexpected-dispatch-input-keys")
    if payload_inputs.get("apply") is not False:
        raise HostedCensusRefusal("dispatch-apply-must-be-false")
    if payload_inputs.get("child_mode") != "batch":
        raise HostedCensusRefusal("dispatch-child-mode-must-be-batch")
    if payload_inputs.get("staging") != "off":
        raise HostedCensusRefusal("dispatch-staging-must-be-off")
    for key in _OMISSIBLE_FALSE_SWITCHES:
        if key in payload_inputs and payload_inputs[key] is not False:
            raise HostedCensusRefusal(f"dispatch-switch-not-false:{key}")
    for key in _OMISSIBLE_BLANK_INPUTS:
        if key in payload_inputs and payload_inputs[key] != "":
            raise HostedCensusRefusal(f"dispatch-text-input-not-empty:{key}")
    return {
        "apply": False,
        "child_mode": "batch",
        "staging": "off",
        "skill_id": "",
        "staging_bootstrap": False,
        "challenge_watch": False,
        "challenge_shadow": False,
        "permission_ab": False,
        "metadata_probe": False,
        "escalate_candidate": "",
        "challenge_input": "",
    }


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate-json-key")
        result[key] = value
    return result


def _reject_json_constant(token: str) -> Any:
    raise ValueError(f"disallowed-json-constant:{token}")


def _loads_strict_json(raw_text: str) -> Any:
    return json.loads(
        raw_text,
        object_pairs_hook=_no_duplicate_keys,
        parse_constant=_reject_json_constant,
    )


def _is_raw_false_value(value: Any, *, allow_blank: bool = False) -> bool:
    if value is False:
        return True
    if type(value) is str:
        if value == "false":
            return True
        if allow_blank and value == "":
            return True
    return False


def validate_raw_event_payload(event_path: Path) -> None:
    """Validate bounded raw ``GITHUB_EVENT_PATH`` JSON before any network I/O.

    Never logs or returns raw event field values; only raises bounded refusal codes.
    """
    try:
        if not event_path.is_file():
            raise HostedCensusRefusal("missing-raw-event-file")
        with event_path.open("rb") as handle:
            raw_bytes = handle.read(MAX_EVENT_BYTES + 1)
    except HostedCensusRefusal:
        raise
    except OSError:
        raise HostedCensusRefusal("unreadable-raw-event-file") from None
    if len(raw_bytes) > MAX_EVENT_BYTES:
        raise HostedCensusRefusal("raw-event-too-large")
    try:
        event = _loads_strict_json(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise HostedCensusRefusal("invalid-raw-event-json") from None
    if not isinstance(event, dict):
        raise HostedCensusRefusal("invalid-raw-event-shape")

    if "ref" in event and event["ref"] != EXPECTED_QUARANTINE_REF:
        raise HostedCensusRefusal("raw-event-ref-mismatch")
    if "repository" in event:
        repo_obj = event["repository"]
        if not isinstance(repo_obj, dict):
            raise HostedCensusRefusal("invalid-raw-event-repository")
        if "full_name" in repo_obj and repo_obj["full_name"] != EXPECTED_REPOSITORY:
            raise HostedCensusRefusal("raw-event-repository-mismatch")
        default_branch = repo_obj.get("default_branch")
        if default_branch is not None:
            if not isinstance(default_branch, str) or not default_branch:
                raise HostedCensusRefusal("invalid-raw-event-default-branch")
            if EXPECTED_QUARANTINE_REF == f"refs/heads/{default_branch}":
                raise HostedCensusRefusal("raw-event-ref-is-default-branch")

    raw_inputs = event.get("inputs")
    if not isinstance(raw_inputs, dict):
        raise HostedCensusRefusal("invalid-raw-event-inputs-shape")
    extra = set(raw_inputs.keys()) - _ALLOWED_DISPATCH_KEYS
    if extra:
        raise HostedCensusRefusal("unexpected-raw-event-input-keys")
    if not _is_raw_false_value(raw_inputs.get("apply"), allow_blank=False):
        raise HostedCensusRefusal("raw-event-apply-must-be-false")
    if type(raw_inputs.get("child_mode")) is not str or raw_inputs.get("child_mode") != "batch":
        raise HostedCensusRefusal("raw-event-child-mode-must-be-batch")
    if type(raw_inputs.get("staging")) is not str or raw_inputs.get("staging") != "off":
        raise HostedCensusRefusal("raw-event-staging-must-be-off")
    for key in _OMISSIBLE_FALSE_SWITCHES:
        if key in raw_inputs and raw_inputs[key] is not None and not _is_raw_false_value(raw_inputs[key], allow_blank=True):
            raise HostedCensusRefusal(f"raw-event-switch-not-false:{key}")
    for key in _OMISSIBLE_BLANK_INPUTS:
        if key in raw_inputs and raw_inputs[key] is not None and (type(raw_inputs[key]) is not str or raw_inputs[key] != ""):
            raise HostedCensusRefusal(f"raw-event-text-input-not-empty:{key}")


def _validate_hosted_runtime_env(env: Mapping[str, str]) -> None:
    """Validate hosted Actions context & raw dispatch payload before any network I/O."""
    in_actions = env.get("GITHUB_ACTIONS") == "true"
    raw_inputs = env.get("DISPATCH_INPUTS_JSON")
    event_path_str = env.get("GITHUB_EVENT_PATH")
    if not in_actions and raw_inputs is None and not event_path_str:
        return
    if in_actions or raw_inputs is not None:
        if not raw_inputs:
            raise HostedCensusRefusal("missing-dispatch-inputs-json")
        try:
            parsed_inputs = _loads_strict_json(raw_inputs)
        except ValueError as exc:
            raise HostedCensusRefusal("invalid-dispatch-inputs-json") from exc
        validate_workflow_dispatch_payload(parsed_inputs)

    if in_actions:
        if env.get("GITHUB_EVENT_NAME") != "workflow_dispatch":
            raise HostedCensusRefusal("runtime-event-name-mismatch")
        if env.get("GITHUB_REPOSITORY") != EXPECTED_REPOSITORY:
            raise HostedCensusRefusal("runtime-repository-mismatch")
        if env.get("GITHUB_REF") != EXPECTED_QUARANTINE_REF:
            raise HostedCensusRefusal("runtime-quarantine-ref-mismatch")
        if env.get("GITHUB_WORKFLOW_REF") != EXPECTED_WORKFLOW_REF:
            raise HostedCensusRefusal("runtime-workflow-ref-mismatch")
        if env.get("GITHUB_RUN_ATTEMPT") != "1":
            raise HostedCensusRefusal("runtime-attempt-not-1")
        if not _RUN_ID_RE.fullmatch(env.get("GITHUB_RUN_ID", "")):
            raise HostedCensusRefusal("runtime-invalid-run-id")
        if not _HEX40_RE.fullmatch(env.get("GITHUB_SHA", "")):
            raise HostedCensusRefusal("runtime-invalid-sha")
        actor = env.get("GITHUB_ACTOR", "")
        if not actor or not _SAFE_PROV_RE.fullmatch(actor):
            raise HostedCensusRefusal("runtime-invalid-actor")
        if not event_path_str:
            raise HostedCensusRefusal("missing-raw-event-path")
        validate_raw_event_payload(Path(event_path_str))
    elif event_path_str:
        validate_raw_event_payload(Path(event_path_str))


class HostedCensusRefusal(RuntimeError):
    """Typed local refusal with a bounded code and no untrusted remote text."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_committed_baseline_files(repo_root: Path) -> None:
    """Verify exact SHA-256 and structural invariants of both committed baseline files.

    Never emits or logs baseline rows.
    """
    resolved_root = repo_root.resolve()
    parsed_docs: dict[Path, Any] = {}
    for rel_path, expected_hex in EXPECTED_BASELINE_FILES_SHA256.items():
        candidate = (resolved_root / rel_path).resolve()
        if not candidate.is_relative_to(resolved_root) or not candidate.is_file():
            raise HostedCensusRefusal("missing-baseline-file")
        try:
            raw_bytes = candidate.read_bytes()
        except OSError:
            raise HostedCensusRefusal("unreadable-baseline-file") from None
        if hashlib.sha256(raw_bytes).hexdigest() != expected_hex:
            raise HostedCensusRefusal("baseline-file-sha256-mismatch")
        try:
            doc = _loads_strict_json(raw_bytes.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise HostedCensusRefusal("invalid-baseline-json") from None
        if not isinstance(doc, dict):
            raise HostedCensusRefusal("invalid-baseline-shape")
        parsed_docs[rel_path] = doc

    records_doc = parsed_docs[BASELINE_RECORDS_REL]
    if records_doc.get("schemaVersion") != "upstream-backlog-baseline-records-v1":
        raise HostedCensusRefusal("invalid-baseline-records-schema")
    if records_doc.get("recordsDigestSha256") != EXPECTED_BASELINE_SHA256:
        raise HostedCensusRefusal("baseline-records-digest-mismatch")
    counts = records_doc.get("counts")
    if (
        not isinstance(counts, dict)
        or type(counts.get("requested")) is not int
        or counts.get("requested") != EXPECTED_BASELINE_COUNT
        or type(counts.get("found")) is not int
        or counts.get("found") != EXPECTED_BASELINE_COUNT
        or type(counts.get("missing")) is not int
        or counts.get("missing") != 0
    ):
        raise HostedCensusRefusal("baseline-records-count-mismatch")
    if records_doc.get("missingIDs") != []:
        raise HostedCensusRefusal("baseline-records-missing-ids")
    records = records_doc.get("records")
    if not isinstance(records, list) or len(records) != EXPECTED_BASELINE_COUNT:
        raise HostedCensusRefusal("baseline-records-length-mismatch")

    meta_doc = parsed_docs[BASELINE_METADATA_REL]
    if meta_doc.get("schemaVersion") != "upstream-backlog-baseline-metadata-v1":
        raise HostedCensusRefusal("invalid-baseline-metadata-schema")
    if meta_doc.get("sourceSHA") != EXPECTED_HISTORICAL_COMMIT:
        raise HostedCensusRefusal("baseline-metadata-source-sha-mismatch")


def load_and_validate_scope(
    scope_path: Path,
    *,
    repo_root: Path = _REPO_ROOT,
) -> tuple[dict[str, Any], str]:
    """Load and strictly validate ``census_scope.json``, committed baselines, and optional ``moduleDigests``."""
    try:
        raw_bytes = scope_path.read_bytes()
        scope_sha256 = hashlib.sha256(raw_bytes).hexdigest()
        data = _loads_strict_json(raw_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise HostedCensusRefusal("invalid-scope-file") from exc

    if not isinstance(data, dict) or type(data.get("schemaVersion")) is not int or data.get("schemaVersion") != 1:
        raise HostedCensusRefusal("invalid-scope-schema")
    if data.get("repository") != EXPECTED_REPOSITORY:
        raise HostedCensusRefusal("scope-repository-mismatch")
    if data.get("quarantineRef") != EXPECTED_QUARANTINE_REF:
        raise HostedCensusRefusal("scope-quarantine-ref-mismatch")
    if data.get("historicalAuthorityCommit") != EXPECTED_HISTORICAL_COMMIT:
        raise HostedCensusRefusal("scope-historical-commit-mismatch")
    if type(data.get("baselineCount")) is not int or data.get("baselineCount") != EXPECTED_BASELINE_COUNT:
        raise HostedCensusRefusal("scope-baseline-count-mismatch")
    if data.get("baselineSha256") != EXPECTED_BASELINE_SHA256:
        raise HostedCensusRefusal("scope-baseline-sha256-mismatch")

    entries = data.get("scope")
    if not isinstance(entries, list) or len(entries) != EXPECTED_SCOPE_COUNT:
        raise HostedCensusRefusal("scope-entry-count-mismatch")
    seen_ids: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise HostedCensusRefusal("invalid-scope-entry")
        named_id = entry.get("namedId")
        release_repo = entry.get("releaseRepo")
        if (
            not isinstance(named_id, str)
            or not envelope.IDENTIFIER.fullmatch(named_id)
            or named_id in seen_ids
            or not isinstance(release_repo, str)
        ):
            raise HostedCensusRefusal("invalid-scope-entry-identity")
        try:
            if envelope.repository(release_repo) != release_repo:
                raise HostedCensusRefusal("invalid-scope-release-repo")
        except PayloadError as exc:
            raise HostedCensusRefusal("invalid-scope-release-repo") from exc
        seen_ids.add(named_id)

    digests = data.get("moduleDigests")
    if digests is not None:
        if not isinstance(digests, dict):
            raise HostedCensusRefusal("invalid-module-digests")
        resolved_root = repo_root.resolve()
        for rel_path, expected_hex in digests.items():
            if not isinstance(rel_path, str) or not isinstance(expected_hex, str) or not envelope.SHA.fullmatch(expected_hex):
                raise HostedCensusRefusal("invalid-module-digest-entry")
            candidate = (resolved_root / rel_path).resolve()
            if not candidate.is_relative_to(resolved_root) or not candidate.is_file():
                raise HostedCensusRefusal("missing-digested-module")
            if _sha256_file(candidate) != expected_hex:
                raise HostedCensusRefusal("module-digest-mismatch")

    _verify_committed_baseline_files(repo_root)

    return data, scope_sha256


def _load_authority_and_suites(
    scope_data: Mapping[str, Any],
    *,
    registry_root: Path | None = None,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Load local registry frontmatter, reject duplicates, and pin exact 14 scoped suites."""
    authority: dict[str, dict[str, Any]] = {}
    for _path, fm in iter_named_skills(root=registry_root):
        identifier = fm.get("id")
        if not isinstance(identifier, str) or not identifier:
            raise HostedCensusRefusal("malformed-registry-named-id")
        if identifier in authority:
            raise HostedCensusRefusal("duplicate-registry-named-id")
        authority[identifier] = fm

    scoped_suites: list[dict[str, Any]] = []
    for entry in scope_data["scope"]:
        named_id = entry["namedId"]
        expected_repo = entry["releaseRepo"]
        fm = authority.get(named_id)
        if not isinstance(fm, dict) or fm.get("id") != named_id:
            raise HostedCensusRefusal("scoped-suite-missing-from-authority")
        try:
            actual_repo = envelope.authority_repository(named_id, authority)
        except PayloadError as exc:
            raise HostedCensusRefusal("scoped-suite-invalid-authority-repo") from exc
        if actual_repo != expected_repo:
            raise HostedCensusRefusal("scoped-suite-release-repo-drift")
        scoped_suites.append(fm)

    return authority, scoped_suites


def _verify_local_historical_commit(repo_root: Path = _REPO_ROOT) -> None:
    try:
        policy = repository_batch.plan_policy()
    except PayloadError as exc:
        raise HostedCensusRefusal("invalid-legacy-plan-policy") from exc
    if policy.get("historicalAuthorityCommit") != EXPECTED_HISTORICAL_COMMIT:
        raise HostedCensusRefusal("legacy-plan-policy-commit-mismatch")
    res = subprocess.run(
        ["git", "cat-file", "-e", f"{EXPECTED_HISTORICAL_COMMIT}^{{commit}}"],
        capture_output=True,
        text=True,
        timeout=10,
        cwd=repo_root,
    )
    if res.returncode != 0:
        raise HostedCensusRefusal("missing-historical-authority-commit")


def _safe_prov(value: str | None) -> str:
    if not isinstance(value, str) or not _SAFE_PROV_RE.fullmatch(value):
        return ""
    return value


def _build_redacted_receipt(
    census: weekly_census.WeeklyCensus,
    *,
    observed_at_iso: str,
    scope_sha256: str,
    provenance_env: Mapping[str, str],
) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "mode": "hosted-readonly-observation-only",
        "pollId": census.poll_id,
        "observedAt": observed_at_iso,
        "runProvenance": {
            "repository": _safe_prov(provenance_env.get("GITHUB_REPOSITORY")) or EXPECTED_REPOSITORY,
            "ref": _safe_prov(provenance_env.get("GITHUB_REF")),
            "sha": _safe_prov(provenance_env.get("GITHUB_SHA")),
            "workflowRef": _safe_prov(provenance_env.get("GITHUB_WORKFLOW_REF")),
            "actor": _safe_prov(provenance_env.get("GITHUB_ACTOR")),
            "runId": _safe_prov(provenance_env.get("GITHUB_RUN_ID")),
            "runAttempt": _safe_prov(provenance_env.get("GITHUB_RUN_ATTEMPT")),
            "scopeFileSha256": scope_sha256,
            "historicalAuthorityCommit": EXPECTED_HISTORICAL_COMMIT,
            "baselineCount": EXPECTED_BASELINE_COUNT,
            "baselineSha256": EXPECTED_BASELINE_SHA256,
        },
        "status": census.status,
        "bindingStatus": census.binding_status,
        "refusal": census.refusal,
        "logicalCandidateCount": census.logical_candidate_count,
        "actualCreates": census.actual_creates,
        "actualUpdates": census.actual_updates,
        "writeAuthorized": census.write_authorized,
        "writeReadiness": census.write_readiness,
        "persisted": census.persisted,
        "stateMode": census.state_mode,
        "knownLegacyHolds": [
            {
                "repository": h.repository,
                "issue": h.issue,
                "legacyNamedId": h.legacy_named_id,
                "currentReleaseRepository": h.current_release_repository,
                "hold": h.hold,
            }
            for h in census.known_legacy_holds
        ],
        "repositoryStatuses": [list(item) for item in census.repository_statuses],
        "scopes": [
            {
                "namedId": s.named_id,
                "repository": s.repository,
                "collectionStatus": s.collection_status,
                "proofStatus": s.proof_status,
                "decision": s.decision,
                "currentVersion": s.current_version,
                "releaseVersion": s.release_version,
                "releaseSource": s.release_source,
                "releaseTime": s.release_time,
                "inventoryStatus": s.inventory_status,
                "versionStatus": s.version_status,
                "deltaStatus": s.delta_status,
                "holdReason": s.hold_reason,
                "componentAddCount": sum(len(vals) for key, vals in s.structural_delta if key == "componentAdds"),
                "componentRemoveCount": sum(len(vals) for key, vals in s.structural_delta if key == "componentRemoves"),
                "canonicalRemovalCount": len(s.canonical_removals),
                "livenessCount": len(s.liveness),
                "nameDriftStatus": s.name_drift_status,
                "nameDriftCount": None if s.name_drift_status == "unknown" else len(s.name_drift_ids),
                "nameDriftVerifiedUnchangedCount": len(s.name_drift_unchanged_ids),
                "nameDriftVerifiedDriftCount": len(s.name_drift_ids),
                "nameDriftUnknownCount": len(s.name_drift_unknown),
                "nameDriftUnknown": [
                    {"namedId": nid, "reason": code} for nid, code in s.name_drift_unknown
                ],
            }
            for s in census.scopes
        ],
        "constraints": [
            "observation-only-no-writes",
            "non-atomic-live-snapshot-same-count-churn-possible",
            "concurrency-does-not-prevent-separate-future-dispatch",
            "tag-ref-recheck-not-atomic-or-immutable",
        ],
    }


def run_hosted_census(
    *,
    scope_path: Path = DEFAULT_SCOPE_PATH,
    issue_port: ReadOnlyIssuePort | None = None,
    upstream_client: HostedUpstreamClient | None = None,
    token: str | None = None,
    registry_root: Path | None = None,
    repo_root: Path = _REPO_ROOT,
    index_loader=prechecks.load_registry_index,
    historical_loader=repository_batch.historical_authority,
    verify_historical_commit: bool = True,
    now: dt.datetime | None = None,
    provenance_env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Execute the complete hosted read-only census and return a bounded redacted receipt."""
    env = dict(os.environ if provenance_env is None else provenance_env)
    _validate_hosted_runtime_env(env)
    scope_data, scope_sha256 = load_and_validate_scope(scope_path, repo_root=repo_root)
    authority, scoped_suites = _load_authority_and_suites(scope_data, registry_root=registry_root)
    if verify_historical_commit:
        _verify_local_historical_commit(repo_root=repo_root)

    effective_token = token if token is not None else env.get("CENSUS_READONLY_TOKEN", "")
    if issue_port is None:
        issue_port = ReadOnlyIssuePort(EXPECTED_REPOSITORY, effective_token)
    elif type(issue_port) is not ReadOnlyIssuePort:
        raise HostedCensusRefusal("invalid-issue-port-type")
    if upstream_client is None:
        upstream_client = HostedUpstreamClient()
    elif type(upstream_client) is not HostedUpstreamClient:
        raise HostedCensusRefusal("invalid-upstream-client-type")

    now_dt = (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc).replace(microsecond=0)
    observed_at_iso = now_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    run_id = _safe_prov(env.get("GITHUB_RUN_ID")) or "local"
    poll_id = f"hosted-readonly-{now_dt.strftime('%Y%m%dT%H%M%SZ')}-{run_id}"

    collected = weekly_collector.collect_suites(
        scoped_suites,
        authority,
        poll_id=poll_id,
        upstream_client=upstream_client,
    )
    policy = repository_batch.policy_record()
    census = weekly_census.run_hosted_weekly_census(
        scoped_suites,
        authority,
        issue_port,
        collected,
        poll_id=poll_id,
        observed_at=observed_at_iso,
        state_mode="ephemeral-empty",
        config_repo=EXPECTED_REPOSITORY,
        index_loader=index_loader,
        policy=policy,
        historical_loader=historical_loader,
    )
    return _build_redacted_receipt(
        census,
        observed_at_iso=observed_at_iso,
        scope_sha256=scope_sha256,
        provenance_env=env,
    )


def _write_receipt(output_path: Path | None, payload: Mapping[str, Any]) -> None:
    if output_path is None:
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hosted read-only P2 weekly census entrypoint.")
    parser.add_argument("--scope-file", type=Path, default=DEFAULT_SCOPE_PATH)
    parser.add_argument("--output", type=Path, default=Path("generated-output/weekly-census-readonly-receipt.json"))
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        receipt = run_hosted_census(scope_path=args.scope_file)
    except HostedCensusRefusal as exc:
        _write_receipt(
            args.output,
            {
                "schemaVersion": 1,
                "mode": "hosted-readonly-observation-only",
                "status": "refused",
                "errorCode": exc.code,
                "actualCreates": 0,
                "actualUpdates": 0,
                "writeAuthorized": False,
                "writeReadiness": False,
                "persisted": False,
                "stateMode": "ephemeral-empty",
            },
        )
        print(f"hosted_census refused: {exc.code}", file=sys.stderr)
        return 2
    except (PayloadError, GhError, SuiteUnavailable, UnknownEvidenceError) as exc:
        _write_receipt(
            args.output,
            {
                "schemaVersion": 1,
                "mode": "hosted-readonly-observation-only",
                "status": "unknown-incomplete",
                "errorCode": type(exc).__name__,
                "actualCreates": 0,
                "actualUpdates": 0,
                "writeAuthorized": False,
                "writeReadiness": False,
                "persisted": False,
                "stateMode": "ephemeral-empty",
            },
        )
        print(f"hosted_census incomplete: {type(exc).__name__}", file=sys.stderr)
        return 3
    except Exception as exc:  # noqa: BLE001 — never emit traceback or remote body
        _write_receipt(
            args.output,
            {
                "schemaVersion": 1,
                "mode": "hosted-readonly-observation-only",
                "status": "refused",
                "errorCode": type(exc).__name__,
                "actualCreates": 0,
                "actualUpdates": 0,
                "writeAuthorized": False,
                "writeReadiness": False,
                "persisted": False,
                "stateMode": "ephemeral-empty",
            },
        )
        print(f"hosted_census failed: {type(exc).__name__}", file=sys.stderr)
        return 1

    _write_receipt(args.output, receipt)
    return 3 if receipt.get("status") == "unknown-incomplete" else 0


if __name__ == "__main__":
    raise SystemExit(main())
