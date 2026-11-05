"""Release provenance guards for distinct suite identities (founder lock #2283 C1)."""
from __future__ import annotations

import json
import re

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


def validateUmbrellaIdentity(finding: dict, issue: dict, *, generated: bool = False) -> None:
    """A source URL selects a repo umbrella; it does not authorize changing its skillId.

    Historical headless payloads keep the existing repair path, but newly generated
    bodies (including the run cache) must have a valid matching owner/skill identity.
    A readable historical payload naming a different suite is conflicting evidence.
    """
    validateReleaseSource(finding)
    body = issue.get("body")
    match = PAYLOAD_RE.search(body if isinstance(body, str) else "")
    payload = None
    if match:
        try:
            payload = json.loads(match.group(1))
        except (ValueError, TypeError):
            pass
    prior = payload.get("skillId") if isinstance(payload, dict) else None
    incoming = finding.get("skillId")
    if generated and not all(
        isinstance(identifier, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*", identifier)
        for identifier in (prior, incoming)
    ):
        raise GhError(f"generated umbrella payload identity missing or malformed for {incoming!r}; no overwrite authorized")
    if isinstance(prior, str) and isinstance(incoming, str) and prior.lower() != incoming.lower():
        raise GhError(f"umbrella #{issue['number']} payload identity conflicts with incoming suite; technical reconciliation required before any overwrite")
