"""Release provenance guards for distinct suite identities (founder lock #2283 C1)."""
from __future__ import annotations

import json

from scripts.lib.github_api import parse_owner_repo
from scripts.upstream_watcher.live import GhError
from scripts.upstream_watcher.markers import PAYLOAD_RE

# These are distinct repositories, not aliases. suiteRef remains topology, never
# permission to substitute the parent's release for the nested suite's release.
LOCKED_SOURCES = {"ruvnet/ruflo": "ruvnet/ruflo", "ruvnet/agentdb": "ruvnet/agentdb"}


def validateReleaseSource(finding: dict) -> None:
    identifier = str(finding.get("skillId", "")).lower()
    expected = LOCKED_SOURCES.get(identifier)
    parsed = parse_owner_repo(finding.get("sourceUrl", ""))
    actual = "/".join(parsed).lower() if parsed else None
    if expected is not None and actual != expected:
        raise GhError(f"release source for {identifier} must be {expected}; reconcile registry source/version metadata via canonical CLI before polling (unknown evidence)")


def validateUmbrellaIdentity(finding: dict, issue: dict) -> None:
    """A source URL selects a repo umbrella; it does not authorize changing its skillId.

    A headless payload keeps the existing repair path. A readable payload naming
    a different suite is affirmative conflicting evidence, not a headless issue.
    """
    validateReleaseSource(finding)
    match = PAYLOAD_RE.search(issue.get("body") or "")
    if not match:
        return
    try:
        payload = json.loads(match.group(1))
    except (ValueError, TypeError):
        return
    prior = payload.get("skillId") if isinstance(payload, dict) else None
    incoming = finding.get("skillId")
    if isinstance(prior, str) and isinstance(incoming, str) and prior.lower() != incoming.lower():
        raise GhError(f"umbrella #{issue['number']} payload identity conflicts with incoming suite; technical reconciliation required before any overwrite")
