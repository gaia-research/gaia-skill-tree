"""Repository-level orchestration around the existing per-named batch planner.

Virtual issue projections isolate each named finding's carry-forward/processed
history. They are never sent to GitHub. Only the complete repository envelope is
written; legacy issues are immutable migration holds, never projected as another
named finding. No policy record can enable execution of a legacy migration.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess

from scripts.upstream_watcher import batch, envelope, prechecks, records
from scripts.upstream_watcher.approval import PayloadError, extract_payload
from scripts.upstream_watcher.live import GhError, canonical_umbrellas, read_live, umbrella_suite

ROOT = Path(__file__).resolve().parents[2]
PLAN_POLICY_PATH = Path(__file__).with_name("legacy_plan_policy.json")


def plan_policy():
    config = json.loads(PLAN_POLICY_PATH.read_text(encoding="utf-8"))
    import re
    if (not isinstance(config, dict) or config.get("planPolicyVersion") != 1 or config.get("planOnly") is not True
            or not isinstance(config.get("historicalAuthorityCommit"), str)
            or not re.fullmatch(r"[0-9a-f]{40}", config["historicalAuthorityCommit"])):
        raise PayloadError("legacy reference policy must be plan-only and commit-pinned")
    path = config.get("directionRecord")
    if not isinstance(path, str) or not (ROOT / path).resolve().is_relative_to(ROOT):
        raise PayloadError("legacy direction record is outside this checkout")
    return config


def historical_authority(identifier):
    """Bounded local immutable blob read, no issue/network access or mutation."""
    from gaia_cli.frontmatter import split_frontmatter, load_yaml_simple
    if not isinstance(identifier, str) or not envelope.IDENTIFIER.fullmatch(identifier):
        return {}
    commit = plan_policy()["historicalAuthorityCommit"]
    result = subprocess.run(["git", "show", f"{commit}:registry/named/{identifier}.md"],
                            capture_output=True, text=True, timeout=10, cwd=ROOT)
    if result.returncode:
        probe = subprocess.run(["git", "cat-file", "-e", f"{commit}^{{commit}}"],
                               capture_output=True, text=True, timeout=10, cwd=ROOT)
        if probe.returncode:
            raise PayloadError(f"pinned historical authority commit {commit} is unavailable in local checkout")
        return {}
    try:
        _, front, _ = split_frontmatter(result.stdout)
        meta = load_yaml_simple(front)
    except Exception:
        return {}
    return {identifier: meta}


def policy_record():
    config = plan_policy()
    policy = json.loads((ROOT / config["directionRecord"]).read_text(encoding="utf-8"))
    if (policy.get("shared_source_model") != "repo_envelope" or policy.get("legacy_transition") != "preserve_plan"
            or policy.get("decisions") != {"shared_source_model": "repo_envelope", "legacy_transition": "preserve_plan"}):
        raise PayloadError("repository-envelope policy record is missing or inconsistent")
    # Include the historical-authority pin in the plan reference, never change
    # the founder's verbatim record or turn it into an execution receipt.
    return {"direction": policy, "referencePolicy": config,
            "shared_source_model": policy["shared_source_model"], "legacy_transition": policy["legacy_transition"]}


def group_findings(findings, authority):
    groups = {}
    unique = {}
    for finding in findings:
        identifier = finding.get("skillId")
        repo = envelope.release_repository(finding.get("sourceUrl"), finding.get("newVersion"))
        if envelope.authority_repository(identifier, authority) != repo:
            raise PayloadError("incoming finding conflicts with registry release authority")
        key = (repo, identifier)
        if key in unique:
            if unique[key] != finding:
                raise PayloadError("conflicting duplicate incoming named finding")
            continue  # byte-equivalent logical finding; no data is lost
        unique[key] = copy.deepcopy(finding)
        groups.setdefault(repo, []).append(copy.deepcopy(finding))
    return {repo: sorted(rows, key=lambda row: row["skillId"]) for repo, rows in sorted(groups.items())}


def read_repository_live(gh):
    live = read_live(gh)
    # Legacy bootstrap history must not disappear at the recent-window boundary
    # or allow a parallel repository umbrella. Keep the existing strict port.
    bootstrap = gh.list_issues("closed", labels="upstream:bootstrap")
    known = {i["number"] for i in live["issues"]}
    live["issues"].extend(i for i in bootstrap if not i.get("pull_request") and i["number"] not in known)
    return live


def inspect_history(repo, live, gh, authority, policy, historical_loader):
    """Validate every claimed OPEN target and closed repository history before writes."""
    found = canonical_umbrellas(live["issues"], repo)
    if found.ambiguous:
        raise PayloadError("malformed claimed repository umbrella title")
    matching = {i["number"]: i for i in live["issues"] + live["closedUmbrellas"]
                if "upstream:release" in batch.label_names(i) and umbrella_suite(i.get("title", "")) == repo}
    for issue in live["issues"] + live["closedUmbrellas"]:
        labels = batch.label_names(issue)
        if "upstream:release" in labels:
            candidate = batch.parse_payload(issue.get("body"))
            identities = []
            if isinstance(candidate, dict):
                if envelope.is_envelope(candidate) and isinstance(candidate.get("findings"), list):
                    identities = [f.get("skillId") for f in candidate["findings"] if isinstance(f, dict)]
                else:
                    identities = [candidate.get("skillId")]
            # A historical named scope follows its own migration hold even when
            # the current release source is now a DIFFERENT repository. This
            # blocks a new parallel umbrella for the old named identity too.
            if any(isinstance(identifier, str) and identifier in authority
                   and envelope.authority_repository(identifier, authority) == repo for identifier in identities):
                matching[issue["number"]] = issue
            continue
        if "upstream:bootstrap" not in labels:
            continue
        from scripts.upstream_watcher.evidence import title_suite_and_version
        parsed_title = title_suite_and_version(issue.get("title", ""), "bootstrap")
        claimed = False
        if parsed_title:
            # A title can claim a target but cannot prove its payload. Unknown or
            # malformed claimed payloads below remain unknown, not benign holds.
            for identifier in authority:
                if identifier.lower() == parsed_title[0] and envelope.authority_repository(identifier, authority) == repo:
                    claimed = True
        payload = batch.parse_payload(issue.get("body"))
        if isinstance(payload, dict):
            try:
                claimed = claimed or envelope.release_repository(payload.get("sourceUrl"), payload.get("newVersion")) == repo
            except PayloadError:
                pass
        if claimed:
            matching[issue["number"]] = issue
    holds, envelopes = [], {}
    for number, issue in sorted(matching.items()):
        payload, _ = extract_payload(issue.get("body"))
        if envelope.is_envelope(payload):
            comments = gh.list_comments(number) if "candidateRecords" in payload else None
            envelopes[number] = envelope.read(issue.get("body"), authority,
                                               title_text=issue.get("title"), comments=comments)
        else:
            try:
                plan = envelope.migration_plan(issue, payload, authority, {}, policy)
            except PayloadError:
                plan = envelope.migration_plan(issue, payload, authority,
                                               historical_loader(payload.get("skillId")), policy)
            if "candidateRecords" in payload:
                original_rows = records.read_rows(gh.list_comments(number), payload["candidateRecords"])
                plan = envelope.seal({**plan, "originalRecordRows": original_rows})
            holds.append(plan)
    return found, holds, envelopes


def projection(live, repo, identifier, envelopes):
    """Only this named member enters the old planner's processed/carry-forward keys.

    A repo-level ``upstream:rejected`` label on a closed envelope is not a per-named
    disposition, so strip it from projected envelope issues before ``carry_forward``
    to prevent sibling childless rows from silently settling as rejected.
    """
    def project(issue):
        if umbrella_suite(issue.get("title", "")) != repo or "upstream:release" not in batch.label_names(issue):
            return copy.deepcopy(issue)
        payload = envelopes.get(issue["number"])
        if payload is None:  # legacy is retained by reference in the hold, not reassigned
            return None
        finding = next((f for f in payload["findings"] if f["skillId"] == identifier), None)
        if finding is None:
            return None
        labels = [
            label for label in issue.get("labels", [])
            if (label.get("name") if isinstance(label, dict) else label) != "upstream:rejected"
        ]
        return {**issue, "labels": labels, "title": batch.umbrella_title(repo, finding["newVersion"]),
                "body": batch.payload_block(finding)}
    return {**live, **{key: [p for issue in live[key] if (p := project(issue)) is not None]
                     for key in ("issues", "closedUmbrellas")}}


def plan_repository(repo, findings, gh, index, live, authority, policy, historical_loader=historical_authority):
    found, holds, stored = inspect_history(repo, live, gh, authority, policy, historical_loader)
    members = {}
    if found.canonical is not None and found.canonical["number"] in stored:
        members = {f["skillId"]: copy.deepcopy(f) for f in stored[found.canonical["number"]]["findings"]}
    plans = []
    for finding in findings:
        identifier = finding["skillId"]
        view = projection(live, repo, identifier, stored)
        plan = batch.plan_suite(finding, view, index, probe=gh.child_state, gh=gh)
        if plan["action"] == "blocked-identity":
            raise PayloadError("named closed history is ambiguous")
        plans.append({"skillId": identifier, "sourceUrl": finding["sourceUrl"],
                      "newVersion": finding["newVersion"], "action": plan["action"],
                      "covering": plan["covering"], "carried": plan["carried"],
                      "newRows": plan["newRows"], "suppressed": plan["suppressed"],
                      "totalRows": plan["totalRows"]})
        if plan["action"] != "suppressed-processed":
            # Hydrate the old planner's logical rows before repository-level
            # layout. Its per-named record generation is never executed.
            full = {k: v for k, v in plan["payload"].items() if k != "candidateRecords"}
            if plan["records"] is not None:
                full["candidates"] = plan["records"]
            # New candidate evidence is pinned to the release at first sight,
            # never to unapproved mutable main. Carried facts keep their exact pin.
            from urllib.parse import quote
            for row in full["candidates"]:
                if row["id"] in plan["newRows"]:
                    row["evidenceUrl"] = row["evidenceUrl"].replace(
                        "/blob/main/", f"/blob/{quote(row['firstSeenVersion'], safe='')}/", 1)
            if finding.get("finding_type") == "bootstrap":
                full["findingType"] = "bootstrap"
            members[identifier] = envelope.seal(full)
    if found.canonical is None and any(p["action"] != "suppressed-processed" for p in plans):
        # A new repository batch also carries unresolved siblings which had no
        # new release finding today. Never turn their rows into the incoming
        # member's identity, nor recreate a wholly processed closed batch.
        newest = {}
        for closed in sorted(live["closedUmbrellas"], key=lambda i: i["number"], reverse=True):
            for prior in stored.get(closed["number"], {}).get("findings", []):
                newest.setdefault(prior["skillId"], prior)
        for identifier, prior in newest.items():
            if identifier in members:
                continue
            view = projection(live, repo, identifier, stored)
            carried = batch.carry_forward(view, repo, batch.child_state_lookup(live, gh.child_state), gh)
            if carried:
                members[identifier] = envelope.seal({**prior, "candidates": carried})
    payload = envelope.build(repo, list(members.values()), authority) if members else None
    wire_payload, body, record_rows = envelope.layout(payload) if payload else (None, None, None)
    canonical = found.canonical
    record_plan = None
    had_records = canonical and "candidateRecords" in (batch.parse_payload(canonical.get("body")) or {})
    if record_rows is not None or had_records:
        comments = gh.list_comments(canonical["number"]) if canonical else []
        record_plan = records.plan_generation(comments, record_rows)
    record_pending = record_plan is not None and (record_plan.prewrites or record_plan.cleanup)
    if payload is None:
        action = "suppressed-processed"
    elif canonical is None:
        action = "create"
    elif (stored.get(canonical["number"]) == payload and canonical["title"] == envelope.title(payload)
          and not record_pending):
        action = "noop"
    else:
        action = "update"
    return {"repository": repo, "umbrella": canonical["number"] if canonical else None,
            "action": action, "payload": payload, "body": body, "wirePayload": wire_payload,
            "records": record_rows, "recordPlan": record_plan,
            "snapshot": batch.snapshot_of(canonical) if canonical else None,
            "findings": plans, "knownLegacyHolds": holds, "writeReadiness": not holds,
            "duplicates": [{"number": i["number"], "title": i.get("title", "")} for i in found.duplicates]}


def write_repository(plan, gh):
    """Only native envelopes, never legacy migrations. Guard each update mutation."""
    if not plan["writeReadiness"] or plan["knownLegacyHolds"]:
        raise GhError("legacy migration hold cannot be executed")
    if plan["action"] == "create":
        plan["umbrella"] = gh.create_issue(envelope.title(plan["payload"]),
            ["upstream:release", "needs-triage"], batch.PLACEHOLDER_BODY if plan["records"] is not None else plan["body"])
        if plan["records"] is not None:
            batch._switch_records(batch.ClosureGuard(gh, plan["umbrella"]), plan["umbrella"],
                                  envelope.title(plan["payload"]), plan["body"], plan["recordPlan"])
        return "created"
    number = plan["umbrella"]
    current = gh.get_issue(number)
    existing, _ = extract_payload(current.get("body"))
    if not envelope.is_envelope(existing):
        raise GhError("legacy migration hold appeared before write")
    if current.get("state") != "open":
        raise batch.UmbrellaClosed(number)
    if batch.snapshot_of(current) != plan["snapshot"]:
        raise RepositoryRaced("repository target changed before write")
    guarded = batch.ClosureGuard(gh, number)
    # A repo label is never per-named authority. Reset it before any body change;
    # exact named approval comments bind immutable individual finding digests.
    if "upstream:approved" in batch.label_names(current):
        guarded.edit_labels(number, add=["upstream:needs-info"], remove=["upstream:approved"])
    batch._switch_records(guarded, number, envelope.title(plan["payload"]), plan["body"], plan["recordPlan"])
    return "updated"


class RepositoryRaced(RuntimeError):
    """A changed snapshot cannot be overwritten by a stale plan."""


def execute_repository(plan, findings, gh, index, authority, policy, historical_loader):
    for _ in range(2):
        # Complete revalidation at adoption/update, including newly introduced
        # legacy holds. A second race is read-only until the next normal poll.
        fresh = read_repository_live(gh)
        replanned = plan_repository(plan["repository"], findings, gh, index, fresh,
                                     authority, policy, historical_loader)
        if not replanned["writeReadiness"]:
            return replanned, "held"
        if replanned["action"] in {"noop", "suppressed-processed"}:
            return replanned, replanned["action"]
        if replanned["umbrella"] is not None:
            current = gh.get_issue(replanned["umbrella"])
            if current.get("state") != "open" or batch.snapshot_of(current) != replanned["snapshot"]:
                continue
        try:
            return replanned, write_repository(replanned, gh)
        except (batch.UmbrellaClosed, RepositoryRaced):
            continue
    return plan, "raced-skip"


def run_repository_batch(findings, gh, apply, authority, *, index_loader=prechecks.load_registry_index,
                         policy=None, historical_loader=historical_authority, mode="batch", staging=None,
                         reset_records=None, plan_only=False):
    """Complete read-only planning precedes the first mutation for ALL repositories.

    Fanout/staged execution is explicitly held, not silently sent through old
    single-ID writers or ambiguous repo-only journals. When ``plan_only=True``,
    even native unstaged batch ``--apply`` is held fail-closed (exit 4) with zero
    GitHub writes; direct callers (``plan_only=False``) keep the native writer
    testable offline.
    """
    legacy_hold = bool(reset_records) or mode != "batch" or (staging is not None and staging.active)
    plan_hold = bool(plan_only and apply)
    operational_hold = legacy_hold or plan_hold
    if legacy_hold:
        hold_reason = "fanout-records-reset-or-legacy-repository-journal-requires-scoped-upgrade"
    elif plan_hold:
        hold_reason = "watcher-plan-only-guard-blocks-envelope-apply"
    else:
        hold_reason = None
    report = batch.new_report()
    report.update(childMode=mode, dryRun=not apply, protocol="repository-envelope-v2",
                  repositories=[], knownLegacyHolds=[], writeReadiness=not operational_hold,
                  executionHold=hold_reason, actualIssuesCreated=0, actualIssuesUpdated=0,
                  observedFindings=copy.deepcopy(findings))
    if staging is not None and staging.active:
        from scripts.upstream_watcher.staging import Journal
        journal = Journal.load(staging.journalPath, staging.bootstrap, staging.initialized)
        report["staging"] = {"journal": {"status": journal.status, "detail": journal.detail},
                             "executionHold": "legacy repo-only journal cannot be assigned to a named finding",
                             "unassignedPendingState": True, "writeReadiness": False}
        if staging.journalPath and Path(staging.journalPath).is_file():
            import hashlib
            try:
                report["staging"]["journal"]["rawSha256"] = hashlib.sha256(Path(staging.journalPath).read_bytes()).hexdigest()
            except OSError as exc:
                report["unknownEvidence"].append({"source": "staging-journal", "detail": str(exc), "stopped": True})
                return report, 3
        report["staging"]["journal"]["pendingRepositories"] = sorted(journal.data.get("repos", {}))
        if journal.blocked:
            report["unknownEvidence"].append({"source": "staging-journal", "detail": journal.detail, "stopped": True})
            return report, 3
    updates = [f for f in findings if f.get("finding_type") in {"update", "bootstrap"}]
    try:
        policy = policy_record() if policy is None else policy
        groups = group_findings(updates, authority)
        index = index_loader()
        live = read_repository_live(gh)
        plans = [plan_repository(repo, rows, gh, index, live, authority, policy, historical_loader)
                 for repo, rows in groups.items()]
    except (PayloadError, GhError, prechecks.RegistryUnreadable, OSError, ValueError, TypeError, KeyError,
            subprocess.SubprocessError) as exc:
        report["unknownEvidence"].append({"source": "repository-plan", "detail": str(exc), "stopped": True})
        report["writeReadiness"] = False
        return report, 3
    for plan in plans:
        outcome = "planned"
        if operational_hold:
            plan["writeReadiness"] = False
            plan["executionHold"] = hold_reason
        if not plan["writeReadiness"]:
            outcome = "held"
        elif plan["action"] in {"noop", "suppressed-processed"}:
            outcome = plan["action"]
        elif apply:
            try:
                plan, outcome = execute_repository(plan, groups[plan["repository"]], gh, index,
                                                   authority, policy, historical_loader)
            except (PayloadError, GhError, OSError, ValueError, TypeError, KeyError) as exc:
                report["unknownEvidence"].append({"source": "repository-write", "repository": plan["repository"],
                                                  "detail": str(exc), "stopped": True})
                report["writeReadiness"] = False
                return report, 3
        report["writeReadiness"] = report["writeReadiness"] and plan["writeReadiness"]
        seen_holds = {hold["payloadSha256"] for hold in report["knownLegacyHolds"]}
        report["knownLegacyHolds"].extend(
            hold for hold in plan["knownLegacyHolds"] if hold["payloadSha256"] not in seen_holds)
        public = {k: v for k, v in plan.items() if k not in {"snapshot", "body", "recordPlan", "records"}}
        public["outcome"] = outcome
        report["repositories"].append(public)
        if plan["duplicates"]:
            report["duplicateOpenUmbrellas"].append({"suite": plan["repository"],
                "canonical": plan["umbrella"], "duplicates": plan["duplicates"]})
        # Logical planned counters vs actual physical mutator counters.
        if plan["action"] == "create" and outcome in {"planned", "held", "created"}:
            report["issuesCreated"] += 1
        if plan["action"] == "update" and outcome in {"planned", "held", "updated"}:
            report["issuesUpdated"] += 1
        if outcome == "created":
            report["actualIssuesCreated"] += 1
        if outcome == "updated":
            report["actualIssuesUpdated"] += 1
        logical_members = (plan["payload"] or {}).get("findings", [])
        report["retainedCandidates"] += sum(len(f.get("candidates", [])) for f in logical_members)
        report["suppressedDuplicates"] += sum(
            r.get("status") in prechecks.SUPPRESSED_STATUSES for f in logical_members for r in f.get("candidates", []))
        for finding in plan["findings"]:
            report["suites"].append({"suite": plan["repository"], "skillId": finding["skillId"],
                "umbrella": plan["umbrella"], "totalRows": finding["totalRows"],
                "newRows": len(finding["newRows"]), "carriedForward": len(finding["carried"]), "outcome": outcome,
                "sourceUrl": finding["sourceUrl"], "newVersion": finding["newVersion"]})
    if apply and operational_hold:
        return report, 4
    return report, 0
