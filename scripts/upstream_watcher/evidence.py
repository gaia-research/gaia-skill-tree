"""Historical evidence for the closed-issue loop guard (PR #2133, hardening pass).

A finding is identified by its evidence, never by an issue number and never by a title alone:

- the suite: owner/repo for an umbrella, the skill id for a bootstrap, lower-cased (GitHub names are case-insensitive);
- the version it proposes;
- the candidate ids it adds, ``owner/repo:slug`` (lower-cased). A bootstrap adds none.

A closed issue is evidence of the finding its payload records. A title only selects which closed issues to read.

``classify`` returns one of three states:

- ``processed``: a closed issue of the same suite records the same version and every candidate id the finding adds.
  Nothing is created. The finding was already handled.
- ``new``: no closed issue covers the finding. A new open issue may be created.
- ``ambiguous``: a closed issue names this suite and version but its payload is missing, unreadable, tampered or
  contradicts its own title. The caller must create nothing and fail closed rather than recreate the backlog.

``ambiguous`` takes precedence over ``processed``.
"""

from __future__ import annotations

import json
import re
from typing import NamedTuple

from scripts.lib.github_api import parse_owner_repo
from scripts.upstream_watcher.approval import payload_tampered
from scripts.upstream_watcher.live import umbrella_suite
from scripts.upstream_watcher.markers import PAYLOAD_RE

UMBRELLA_VERSION = re.compile(r" → (?P<version>\S+)$")
BOOTSTRAP_TITLE = re.compile(r"^\[upstream:bootstrap\] (?P<skill>\S+) → baseline at (?P<version>\S+)$")


class Verdict(NamedTuple):
    state: str
    covering: tuple[int, ...] = ()
    ambiguous: tuple[int, ...] = ()


def read_payload(body: str | None) -> dict | None:
    match = PAYLOAD_RE.search(body or "")
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def suite_of(record: dict, kind: str) -> str:
    """The lower-cased suite a finding or payload belongs to. Release findings use owner/repo, bootstraps the skill."""
    if kind == "bootstrap":
        return str(record["skillId"]).strip().lower()
    parsed = parse_owner_repo(record["sourceUrl"]) if record.get("sourceUrl") else None
    owner_repo = f"{parsed[0]}/{parsed[1]}" if parsed else str(record["skillId"])
    return owner_repo.strip().lower()


def candidate_ids(record: dict, kind: str) -> frozenset[str]:
    """The candidate ids a finding adds, in the same ``owner/repo:slug`` form the umbrella rows use."""
    if kind == "bootstrap":
        return frozenset()
    suite = suite_of(record, kind)
    return frozenset(f"{suite}:{slug}".lower() for slug in record.get("componentAdds", []))


def title_suite_and_version(title: str, kind: str) -> tuple[str, str] | None:
    """Which suite and version a closed issue's title names. Only selects candidates; it never proves a finding."""
    if kind == "bootstrap":
        match = BOOTSTRAP_TITLE.match(title)
        return (match.group("skill").lower(), match.group("version")) if match else None
    suite = umbrella_suite(title)
    version = UMBRELLA_VERSION.search(title)
    return (suite, version.group("version")) if suite and version else None


def usable_payload(payload: dict, kind: str) -> bool:
    if not isinstance(payload.get("skillId"), str) or not isinstance(payload.get("newVersion"), str):
        return False
    if kind == "bootstrap":
        return True
    return isinstance(payload.get("componentAdds", []), list)


def classify(finding: dict, kind: str, closed_issues: list[dict]) -> Verdict:
    """Decide whether *finding* is new, already processed, or ambiguous against the closed history.

    *kind* is ``release`` (an umbrella finding) or ``bootstrap``. *closed_issues* is the full closed history of that
    label, read without a window. Open and pull-request rows are ignored.
    """
    suite = suite_of(finding, kind)
    version = finding["newVersion"]
    ids = candidate_ids(finding, kind)
    covering: list[int] = []
    ambiguous: list[int] = []
    for issue in closed_issues:
        if issue.get("state") != "closed" or issue.get("pull_request"):
            continue
        titled = title_suite_and_version(issue.get("title") or "", kind)
        if titled is None or titled != (suite, version):
            continue
        number = issue["number"]
        payload = read_payload(issue.get("body"))
        if payload is None or payload_tampered(payload) or not usable_payload(payload, kind):
            ambiguous.append(number)
            continue
        if suite_of(payload, kind) != suite or payload["newVersion"] != version:
            ambiguous.append(number)
            continue
        if ids <= candidate_ids(payload, kind):
            covering.append(number)
    if ambiguous:
        return Verdict("ambiguous", tuple(sorted(covering)), tuple(sorted(ambiguous)))
    if covering:
        return Verdict("processed", tuple(sorted(covering)))
    return Verdict("new")


__all__ = ["Verdict", "candidate_ids", "classify", "read_payload", "suite_of", "title_suite_and_version"]
