#!/usr/bin/env python3
"""Contribution-channel policy classification (Issue #2074, Campaign #1817).

Pure logic (no network, no GitHub client): text-signal extraction, issue-channel
analysis, the channel decision, the append-only policy ledger, approval provenance
verification and the local-only proposal draft. Evidence *gathering* lives in
``scripts/badge_reconcile.py`` and feeds this module raw material.

Every target repository is classified into exactly one channel:

* ``PR_ALLOWED``   explicit permission from authoritative guidance for an outside PR.
* ``ISSUE_FIRST``  the repo requires an approved issue before an outside PR.
* ``NO_OUTREACH``  the repo forbids/refused this kind of contact. Internal hold.
* ``UNKNOWN``      anything else, including incomplete evidence. Internal hold.

Design rules
------------
* Fail closed. ``UNKNOWN`` is a hold, never a default permission.
* Explicit permission is not the same thing as absence of prohibition. Permission needs
  an authoritative source (contribution guidance, README, maintainer comment). A restriction
  is honoured from *any* source because a false positive only holds outreach.
* An issue and a PR are two stages of ONE outreach attempt, not two quotas.
* Never manufacture an issue to bypass a PR rejection: an issue proposal is only possible
  when the repo itself says issue-first and nothing refused us.
* ``ISSUE_FIRST`` permits exactly one concise proposal issue; this tooling only ever drafts
  it locally. The README PR needs a recorded, upstream-verified maintainer approval.
* Channel and approval changes are append-only, hash-chained ledger events; historical
  closures and refusals are never erased.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

SCHEMA_VERSION = 1

CHANNELS = ("PR_ALLOWED", "ISSUE_FIRST", "NO_OUTREACH", "UNKNOWN")

# Channel-specific next actions (machine codes). Holds never mention PR/issue creation.
ACTION_PR_PATH = "PR_PATH_RUN_PREDISPATCH_AFTER_CAMPAIGN_APPROVAL"
ACTION_PR_AFTER_APPROVAL = "PR_PATH_RUN_PREDISPATCH_AFTER_RECORDED_MAINTAINER_APPROVAL"
ACTION_DRAFT_ISSUE = "HOLD_INTERNAL_DRAFT_ONE_PROPOSAL_ISSUE_AWAITING_FRESH_HUMAN_APPROVAL"
ACTION_WAIT_ISSUE = "HOLD_WAIT_FOR_MAINTAINER_ON_EXISTING_ISSUE_NO_NEW_OUTREACH"
ACTION_ISSUE_CLOSED = "HOLD_EXISTING_ISSUE_CLOSED_NO_SECOND_ISSUE_EXPLICIT_REVIEW"
ACTION_APPROVAL_UNVERIFIED = "HOLD_RECORDED_APPROVAL_UNVERIFIED_REVIEW_PROVENANCE"
ACTION_NO_OUTREACH = "INTERNAL_HOLD_NO_PR_NO_ISSUE"
ACTION_UNKNOWN = "INTERNAL_HOLD_RESOLVE_POLICY_EVIDENCE_NO_PR_NO_ISSUE"
ACTION_INCOMPLETE = "INTERNAL_HOLD_RETRY_POLICY_SCAN_LATER_NO_PR_NO_ISSUE"
ACTION_NOT_SCANNED = "INTERNAL_HOLD_RUN_SCOPED_POLICY_SCAN_NO_PR_NO_ISSUE"
ACTION_EXISTING_OUTREACH = "INTERNAL_HOLD_EXISTING_OUTREACH_STAGE_NO_NEW_PR_OR_ISSUE"

# Who may grant (or evidence) a permission / approval. GitHub author_association values.
AUTHORITY_ASSOCIATIONS = ("OWNER", "MEMBER", "COLLABORATOR")
AUTOMATED_ACTORS = {"claude", "claude-bot", "codex", "gemini", "gemini-bot", "jules", "bot", "agent", "ai"}

SOURCE_KINDS = (
    "readme", "contributing", "agents", "pr_template", "issue_template", "issue_config",
    "code_of_conduct", "security", "workflow", "comment", "ledger", "repo_settings",
)
# Only these kinds may *grant* permission (restrictions are honoured from any kind).
PERMISSION_KINDS = ("contributing", "readme", "comment")

EVENT_TYPES = (
    "CHANNEL_CLASSIFIED",
    "HISTORICAL_CLOSURE_RECORDED",
    "PRIOR_REFUSAL_RECORDED",
    "ISSUE_PROPOSAL_DRAFTED",
    "ISSUE_PROPOSAL_SENT",
    "MAINTAINER_APPROVAL_RECORDED",
    "APPROVAL_REVOKED",
)
CLOSURE_KINDS = ("ISSUE_FIRST_REDIRECT", "REFUSAL", "UNEXPLAINED")
GENESIS_HASH = "0" * 64


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def normalize_repo_name(name: str) -> str:
    return urllib.parse.unquote(name).strip().strip("/").lower()


def repo_keys(names: list[str], migrations: dict[str, str] | None = None) -> set[str]:
    """Normalized names for one repo, closed over known renames in both directions."""
    migrations = {normalize_repo_name(k): normalize_repo_name(v) for k, v in (migrations or {}).items()}
    keys = {normalize_repo_name(n) for n in names if n}
    changed = True
    while changed:
        changed = False
        for old, new in migrations.items():
            if (old in keys) != (new in keys):
                keys |= {old, new}
                changed = True
    return keys


# ---------------------------------------------------------------------------
# Text signals
# ---------------------------------------------------------------------------

_FLAGS = re.IGNORECASE
_BEFORE_PR = r"before\s+(?:opening|submitting|sending|creating|making|raising)\s+(?:an?\s+)?(?:pull requests?|prs?)"

ISSUE_FIRST_PATTERNS = [re.compile(p, _FLAGS) for p in (
    r"issue[- ]first",
    r"(?:open|create|file|raise|start with)\s+(?:an?\s+)?(?:issue|discussion)\s+(?:first|before)",
    r"(?:open|create|file|raise|submit)\s+(?:an?\s+)?(?:issue|discussion)\b[^.\n]{0,60}\b" + _BEFORE_PR,
    r"(?:discuss|propose|raise)\b[^.\n]{0,80}\b" + _BEFORE_PR,
    r"(?:pull requests?|prs?)\b[^.\n]{0,80}\b(?:requires?|must (?:be linked|reference|link|have)|needs?)\b[^.\n]{0,60}\b(?:an?\s+)?(?:approved|accepted|linked|existing|associated)?\s*issue",
    r"(?:pull requests?|prs?)\b[^.\n]{0,60}\b(?:without|not linked to|that do(?:es)? not (?:reference|link|have))\b[^.\n]{0,40}\bissues?\b[^.\n]{0,60}\b(?:will|may|can|are|is)\b[^.\n]{0,20}\b(?:closed|rejected|declined)",
    r"\bissue\b[^.\n]{0,60}\bapproved by\b",
    r"(?:outside|external|first[- ]time)\s+(?:contributors?|contributions?)\b[^.\n]{0,80}\bissue\b",
)]

# Hard "do not contact us this way" statements (any source kind).
NO_OUTREACH_PATTERNS = [re.compile(p, _FLAGS) for p in (
    r"(?:we|i|this (?:project|repo(?:sitory)?)|the maintainers?)\s+(?:do(?:es)?\s+not|don't|doesn't|cannot|can't|won't|will not|are not|aren't|is not|isn't)\s+(?:currently\s+|presently\s+)?(?:accept(?:ing)?|take|taking|review(?:ing)?|welcom(?:e|ing)|open to)\s+(?:any\s+)?(?:external\s+|outside\s+|third[- ]party\s+|unsolicited\s+|drive[- ]by\s+|community\s+)?(?:contributions?|pull requests?|prs?)",
    r"\bnot\s+(?:currently\s+)?(?:accepting|open to|taking)\s+(?:any\s+)?(?:external\s+|outside\s+|unsolicited\s+)?(?:contributions?|pull requests?|prs?)",
    r"(?:external|outside)\s+(?:contributions?|pull requests?|prs?)\s+(?:are\s+)?(?:disabled|closed|not\s+(?:accepted|allowed|welcome))",
    r"(?:contributions?|pull requests?|prs?)\s+(?:are\s+)?(?:disabled|closed|not\s+accepted|not\s+allowed|not\s+welcome)",
    r"read[- ]only\s+(?:mirror|repository)",
    r"(?:promotional|advertis\w+|self[- ]promotion|marketing|spam)\b[^.\n]{0,60}\b(?:not\s+(?:accepted|allowed|welcome|permitted)|will be closed|prohibited|forbidden)",
    r"(?:do not|don't|please do not|never)\s+(?:submit|open|send|create)\s+(?:any\s+)?(?:unsolicited|promotional|badge|advertis\w+)",
    r"(?:\bai|\bllm|\bbot|\bagent|automated|machine)[- ](?:generated|authored|written|assisted)?\s*(?:pull requests?|prs?|contributions?|submissions?)\b[^.\n]{0,60}\b(?:not\s+(?:accepted|allowed|welcome|permitted)|will be closed|prohibited|forbidden)",
)]

# "Only maintainers ..." is a PR restriction in contribution docs but only an issue-channel
# restriction inside issue forms. Applied per source kind.
MAINTAINER_ONLY_PATTERNS = [re.compile(p, _FLAGS) for p in (
    r"(?:maintainers?|core team|team members?)[- ]only\b",
    r"\bonly\s+(?:the\s+)?(?:maintainers?|core team|team members?)\s+(?:may|can|should|are allowed to)\b",
    r"\breserved for\s+(?:the\s+)?(?:maintainers?|core team|team members?)\b",
)]

# Refusal phrasing, only meaningful inside comments (closure replies, issue replies).
REFUSAL_PATTERNS = [re.compile(p, _FLAGS) for p in (
    r"not interested",
    r"\bno,? thanks?\b|\bno thank you\b",
    r"we(?:'ll| will)? (?:pass|decline)",
    r"(?:won't|will not|do not|don't)\s+(?:merge|accept)\s+(?:this|these|such|badge|promotional)",
    r"closing (?:this )?as (?:not planned|wontfix|won't fix)",
    r"\bnot a fit\b",
    r"please\s+(?:do not|don't)\s+(?:open|send|submit)\s+(?:any\s+)?(?:more|further|another|these)",
)]

PERMISSION_PATTERNS = [re.compile(p, _FLAGS) for p in (
    r"(?:pull requests?|prs?|contributions?)(?:\s+and\s+(?:issues?|bug reports?))?\s+(?:are\s+|is\s+)?(?:always\s+|very\s+|warmly\s+|gladly\s+|greatly\s+)?(?:welcome|appreciated|encouraged)",
    r"\b(?:we|i)\s+(?:welcome|accept|appreciate|love|encourage|gladly accept)\s+(?:all\s+|any\s+|your\s+)?(?:pull requests?|prs?|contributions?)",
    r"feel free to\s+(?:open|submit|send|create|make|raise)\s+(?:an?\s+|your\s+)?(?:pull request|pr)\b",
    r"\bprs?[-_ ]welcome\b",
    r"(?:go ahead|please)\b[^.\n]{0,30}\b(?:and\s+)?(?:open|send|submit)\s+(?:a\s+)?(?:pull request|pr)\b",
)]
# How-to instructions only count as permission in contribution guidance itself.
GUIDANCE_PERMISSION_PATTERNS = [re.compile(p, _FLAGS) for p in (
    r"(?:fork|clone)\b[^.\n]{0,80}\b(?:open|submit|send|create)\s+(?:a\s+)?(?:pull request|pr)\b",
    r"(?:open|submit|send|create)\s+(?:a\s+)?(?:pull request|pr)\s+(?:with|against|to)\b",
)]

ISSUE_CLOSED_PATTERNS = [re.compile(p, _FLAGS) for p in (
    r"issues?\s+(?:are\s+)?(?:disabled|closed)",
    r"(?:do not|don't|please do not)\s+(?:open|create|file)\s+(?:an?\s+)?(?:issues?|feature requests?|proposals?)\b",
)]
BUG_ONLY_TEXT = [re.compile(p, _FLAGS) for p in (
    r"\b(?:only|solely|exclusively)\s+(?:for\s+)?(?:reporting\s+)?bugs?\b",
    r"\bbug\s+reports?\s+only\b",
    r"\bnot\s+for\s+(?:feature requests?|questions?|proposals?|general)\b",
)]
APPROVAL_PATTERNS = [re.compile(p, _FLAGS) for p in (
    r"\b(?:go ahead|sounds good|happy to (?:accept|merge|take)|feel free to (?:open|send|submit)|please (?:open|send|submit)|we(?:'d| would) (?:welcome|accept|love)|approved|lgtm|yes,? (?:please|that works))\b",
)]
WITHDRAWAL_PATTERNS = [re.compile(p, _FLAGS) for p in (
    r"\b(?:please\s+)?(?:don't|do not)\s+(?:open|send|submit|proceed)\b",
    r"\bhold off\b|\bnever ?mind\b|\bactually,?\s+no\b|\bwithdraw\w*\b|\bchanged my mind\b|\bplease stop\b",
)]
_NEGATION = re.compile(r"(?:\bnot\b|n't\b|\bnever\b|\bno\b|\bwithout\b)\s*(?:\w+\s+){0,2}$", _FLAGS)
_MENTION = re.compile(r"@([A-Za-z0-9][A-Za-z0-9-]{0,38})")
_WS = re.compile(r"\s+")


_NEGATION_WITHIN = re.compile(r"\b(?:not|never|no|without)\b|n't\b", _FLAGS)


def _negated(text: str, start: int, end: int | None = None) -> bool:
    """Negation just before the match, or anywhere inside it ('please do not send a pull request')."""
    return bool(_NEGATION.search(text[max(0, start - 40):start])) or (
        end is not None and bool(_NEGATION_WITHIN.search(text[start:end])))


def collapse(text: str) -> str:
    return _WS.sub(" ", text).strip()


def excerpt_around(text: str, start: int, end: int, limit: int = 240) -> str:
    """The sentence/line containing the match, whitespace-collapsed and bounded."""
    left = max(text.rfind(".", 0, start), text.rfind("\n", 0, start), text.rfind("!", 0, start), text.rfind("?", 0, start))
    cands = [i for i in (text.find(".", end), text.find("\n", end), text.find("!", end), text.find("?", end)) if i != -1]
    right = min(cands) + 1 if cands else len(text)
    out = collapse(text[left + 1:right])
    if len(out) > limit:
        mid = start - (left + 1)
        out = collapse(text[left + 1:right])[max(0, mid - limit // 2): max(0, mid - limit // 2) + limit]
    return out


def _signal(kind: str, effect: str, strength: str, source_url: str | None, path: str | None,
            excerpt: str, authority: str, observed_at: str, **extra: Any) -> dict[str, Any]:
    sig = {
        "kind": kind, "effect": effect, "strength": strength, "authority": authority,
        "source_url": source_url, "path": path, "excerpt": excerpt, "observed_at": observed_at,
    }
    sig.update(extra)
    sig["id"] = hashlib.sha256(
        json.dumps([kind, effect, source_url, path, excerpt], sort_keys=True).encode()).hexdigest()[:12]
    return sig


def extract_signals(kind: str, text: str, source_url: str | None, path: str | None, observed_at: str,
                    authority: str = "repository_file", comment_author_ok: bool | None = None) -> list[dict[str, Any]]:
    """Policy signals found in one document. ``kind`` selects which pattern families apply.

    Effects: ``ISSUE_FIRST``, ``NO_OUTREACH``, ``PERMITS_PR``, ``ISSUES_CLOSED``, ``BUG_ONLY``.
    ``comment_author_ok`` (comments only) says the author is a maintainer: only then may a
    comment grant permission.
    """
    signals: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def add(effect: str, m: re.Match[str], strength: str = "explicit", **extra: Any) -> None:
        ex = excerpt_around(text, m.start(), m.end())
        if (effect, ex) in seen:
            return
        seen.add((effect, ex))
        named = sorted({h.lower() for h in _MENTION.findall(ex)}) if effect == "ISSUE_FIRST" else []
        signals.append(_signal(kind, effect, strength, source_url, path, ex, authority, observed_at,
                               named_approvers=named, **extra))

    for p in ISSUE_FIRST_PATTERNS:
        for m in p.finditer(text):
            add("ISSUE_FIRST", m)
    for p in NO_OUTREACH_PATTERNS:
        for m in p.finditer(text):
            add("NO_OUTREACH", m)
    if kind == "comment":
        for p in REFUSAL_PATTERNS:
            for m in p.finditer(text):
                add("NO_OUTREACH", m, refusal=True)
    for p in MAINTAINER_ONLY_PATTERNS:
        for m in p.finditer(text):
            add("ISSUES_CLOSED" if kind in ("issue_template", "issue_config") else "NO_OUTREACH", m)
    if kind in ("issue_template", "issue_config"):
        for p in ISSUE_CLOSED_PATTERNS:
            for m in p.finditer(text):
                add("ISSUES_CLOSED", m)
        for p in BUG_ONLY_TEXT:
            for m in p.finditer(text):
                add("BUG_ONLY", m)

    may_permit = kind in PERMISSION_KINDS and (kind != "comment" or bool(comment_author_ok))
    if may_permit:
        pats = list(PERMISSION_PATTERNS) + (list(GUIDANCE_PERMISSION_PATTERNS) if kind == "contributing" else [])
        for p in pats:
            for m in p.finditer(text):
                if _negated(text, m.start(), m.end()):
                    continue
                add("PERMITS_PR", m)
    return signals


# ---------------------------------------------------------------------------
# Issue channel analysis (templates / forms / config / repo settings)
# ---------------------------------------------------------------------------

_BUG_WORDS = re.compile(r"\b(bug|defect|crash|error|regression|broken|problem|failure)\b", _FLAGS)
_PROPOSAL_WORDS = re.compile(
    r"\b(feature|enhancement|proposal|idea|request|suggestion|question|discussion|general|other|docs?|"
    r"documentation|rfc|improvement|support|task|blank)\b", _FLAGS)
_YAML_NAME = re.compile(r"^\s*(?:name|title|labels?)\s*:\s*(.+)$", re.MULTILINE)


def analyze_issue_channel(issues_enabled: bool | None, config_text: str | None,
                          templates: list[tuple[str, str]], discussions_enabled: bool | None = None,
                          closed_text_signals: bool = False, bug_only_text: bool = False) -> dict[str, Any]:
    """Can a (non-bug) proposal issue be filed at all?

    ``proposal_possible`` is True/False/None (None = could not be determined).
    """
    blank: bool | None = None
    contact_links = 0
    if config_text is not None:
        m = re.search(r"^\s*blank_issues_enabled\s*:\s*(true|false)\b", config_text, _FLAGS | re.MULTILINE)
        blank = (m.group(1).lower() == "true") if m else True
        contact_links = len(re.findall(r"^\s*-\s*name\s*:", config_text, re.MULTILINE))
    else:
        blank = True  # GitHub default when no config
    names: list[str] = []
    bug_templates = 0
    proposal_templates = 0
    for path, text in templates:
        meta = " ".join(_YAML_NAME.findall(text[:2000])) + " " + Path(path).stem.replace("_", " ").replace("-", " ")
        names.append(Path(path).name)
        is_proposal = bool(_PROPOSAL_WORDS.search(meta))
        is_bug = bool(_BUG_WORDS.search(meta))
        if is_proposal:
            proposal_templates += 1
        elif is_bug:
            bug_templates += 1
    forms_bug_only = bool(templates) and proposal_templates == 0 and bug_templates == len(templates) and blank is False
    restricted = forms_bug_only or bug_only_text
    if issues_enabled is False:
        possible: bool | None = False
        reason = "issues_disabled"
    elif closed_text_signals:
        possible, reason = False, "issues_maintainer_only_or_closed_by_template_text"
    elif restricted:
        possible, reason = False, "issue_forms_restricted_to_bugs"
    elif issues_enabled is None:
        possible, reason = None, "issues_setting_unknown"
    else:
        possible, reason = True, "issues_open_for_proposals"
    return {
        "issues_enabled": issues_enabled,
        "blank_issues_enabled": blank,
        "discussions_enabled": discussions_enabled,
        "templates": sorted(names),
        "bug_templates": bug_templates,
        "proposal_templates": proposal_templates,
        "contact_links": contact_links,
        "bug_only": restricted,
        "proposal_possible": possible,
        "reason": reason,
    }


# ---------------------------------------------------------------------------
# Append-only policy ledger
# ---------------------------------------------------------------------------

ISSUE_URL_RE = re.compile(r"^https?://github\.com/([^/\s]+)/([^/\s#]+)/issues/(\d+)/?$", re.IGNORECASE)
PR_URL_RE = re.compile(r"^https?://github\.com/([^/\s]+)/([^/\s#]+)/pull/(\d+)/?$", re.IGNORECASE)
COMMENT_URL_RE = re.compile(r"^https?://github\.com/([^/\s]+)/([^/\s#]+)/(?:issues|pull)/(\d+)#issuecomment-(\d+)$", re.IGNORECASE)


class LedgerError(Exception):
    pass


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def event_hash(event: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json({k: v for k, v in event.items() if k != "hash"}).encode()).hexdigest()


def read_events(path: Path) -> list[dict[str, Any]]:
    """All events, fail-closed: a corrupt line aborts instead of silently dropping history."""
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
        except ValueError as e:
            raise LedgerError(f"corrupt policy ledger line {n}: {e}") from e
        if not isinstance(ev, dict):
            raise LedgerError(f"corrupt policy ledger line {n}: not an object")
        events.append(ev)
    return events


def verify_chain(events: list[dict[str, Any]]) -> list[str]:
    """Problems in the hash chain (empty = intact). Detects edits, deletions and reordering."""
    problems: list[str] = []
    prev = GENESIS_HASH
    for i, ev in enumerate(events, 1):
        if ev.get("seq") != i:
            problems.append(f"event {i}: seq {ev.get('seq')} out of order")
        if ev.get("prev_hash") != prev:
            problems.append(f"event {i}: prev_hash does not match previous event (history altered)")
        if ev.get("hash") != event_hash(ev):
            problems.append(f"event {i}: hash mismatch (event altered)")
        prev = ev.get("hash", "")
    return problems


def _require(data: dict[str, Any], *keys: str) -> None:
    missing = [k for k in keys if not data.get(k)]
    if missing:
        raise LedgerError(f"missing required field(s): {', '.join(missing)}")


def _check_human(actor: str | None, what: str) -> str:
    a = (actor or "").strip()
    if not a:
        raise LedgerError(f"{what} requires a named human actor (--recorded-by)")
    low = a.lower()
    if low.endswith("[bot]") or low in AUTOMATED_ACTORS or low.startswith("claude"):
        raise LedgerError(f"{what} must be recorded by a human, not '{a}'")
    return a


def validate_event(event_type: str, repository: str, actor: str | None, data: dict[str, Any]) -> None:
    if event_type not in EVENT_TYPES:
        raise LedgerError(f"unknown event type {event_type!r}; expected one of {EVENT_TYPES}")
    if not repository or "/" not in repository:
        raise LedgerError("repository must be owner/name")
    if not (actor or "").strip():
        raise LedgerError("actor is required")
    if event_type == "CHANNEL_CLASSIFIED":
        _require(data, "channel", "observed_at")
        if data["channel"] not in CHANNELS:
            raise LedgerError(f"channel must be one of {CHANNELS}")
    elif event_type == "HISTORICAL_CLOSURE_RECORDED":
        _require(data, "pr_url", "closed_at", "kind", "excerpt", "state")
        if data["kind"] not in CLOSURE_KINDS:
            raise LedgerError(f"closure kind must be one of {CLOSURE_KINDS}")
        if not PR_URL_RE.match(data["pr_url"]):
            raise LedgerError("pr_url must be a GitHub pull request URL")
    elif event_type == "PRIOR_REFUSAL_RECORDED":
        _require(data, "source_url", "excerpt")
    elif event_type == "ISSUE_PROPOSAL_DRAFTED":
        _require(data, "draft_path", "draft_sha256")
        if data.get("sent") is not False:
            raise LedgerError("a draft event must carry sent=false; sending is a separate human act")
    elif event_type == "ISSUE_PROPOSAL_SENT":
        _check_human(actor, "recording a sent proposal")
        _require(data, "issue_url")
        if not ISSUE_URL_RE.match(data["issue_url"]):
            raise LedgerError("issue_url must be a GitHub issue URL (not a pull request)")
    elif event_type == "MAINTAINER_APPROVAL_RECORDED":
        _check_human(actor, "recording a maintainer approval")
        _require(data, "issue_url", "approver", "authority", "evidence_url", "evidence_excerpt")
        if data["authority"] not in AUTHORITY_ASSOCIATIONS:
            raise LedgerError(f"approval authority must be one of {AUTHORITY_ASSOCIATIONS}")
        m_issue, m_ev = ISSUE_URL_RE.match(data["issue_url"]), COMMENT_URL_RE.match(data["evidence_url"])
        if not m_issue:
            raise LedgerError("issue_url must be a GitHub issue URL")
        if not m_ev:
            raise LedgerError("evidence_url must be a GitHub comment URL (…#issuecomment-<id>)")
        if (m_issue.group(1).lower(), m_issue.group(2).lower(), m_issue.group(3)) != (
                m_ev.group(1).lower(), m_ev.group(2).lower(), m_ev.group(3)):
            raise LedgerError("evidence comment must belong to the approved proposal issue")
        if data["approver"].strip().lower().endswith("[bot]"):
            raise LedgerError("a bot cannot grant maintainer approval")
    elif event_type == "APPROVAL_REVOKED":
        _check_human(actor, "revoking an approval")
        _require(data, "target_hash", "reason")


def append_event(path: Path, repository: str, event_type: str, actor: str, data: dict[str, Any],
                 now: Callable[[], datetime] = utcnow) -> dict[str, Any]:
    """Append one hash-chained event under an exclusive lock. History is never rewritten."""
    validate_event(event_type, repository, actor, data)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.parent / (path.name + ".lock")
    with open(lock_path, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            events = read_events(path)
            problems = verify_chain(events)
            if problems:
                raise LedgerError("refusing to append to a tampered ledger: " + "; ".join(problems))
            if event_type == "APPROVAL_REVOKED" and not any(e["hash"] == data["target_hash"] for e in events):
                raise LedgerError("revocation target_hash matches no ledger event")
            ev = {
                "seq": len(events) + 1,
                "timestamp": now().isoformat(),
                "repository": repository,
                "event_type": event_type,
                "actor": actor.strip(),
                "data": data,
                "prev_hash": events[-1]["hash"] if events else GENESIS_HASH,
            }
            ev["hash"] = event_hash(ev)
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(canonical_json(ev) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
    return ev


def ledger_state(events: list[dict[str, Any]], names: list[str], migrations: dict[str, str] | None = None) -> dict[str, Any]:
    """Reduce the ledger for one repository (all aliases / migrated names).

    Closures and refusals accumulate forever; a later channel or approval event never removes them.
    """
    keys = repo_keys(names, migrations)
    mine = [e for e in events if normalize_repo_name(e.get("repository", "")) in keys
            or any(normalize_repo_name(a) in keys for a in (e.get("data") or {}).get("aliases", []))]
    revoked = {e["data"]["target_hash"] for e in mine if e["event_type"] == "APPROVAL_REVOKED"}
    approvals = [{"event": e, "active": e["hash"] not in revoked}
                 for e in mine if e["event_type"] == "MAINTAINER_APPROVAL_RECORDED"]
    channel_events = [e for e in mine if e["event_type"] == "CHANNEL_CLASSIFIED"]
    return {
        "events": mine,
        "historical_closures": [e for e in mine if e["event_type"] == "HISTORICAL_CLOSURE_RECORDED"],
        "refusals": [e for e in mine if e["event_type"] == "PRIOR_REFUSAL_RECORDED"]
        + [e for e in mine if e["event_type"] == "HISTORICAL_CLOSURE_RECORDED" and e["data"]["kind"] == "REFUSAL"],
        "drafts": [e for e in mine if e["event_type"] == "ISSUE_PROPOSAL_DRAFTED"],
        "proposals_sent": [e for e in mine if e["event_type"] == "ISSUE_PROPOSAL_SENT"],
        "approvals": approvals,
        "active_approvals": [a["event"] for a in approvals if a["active"]],
        "channel_events": channel_events,
        "last_channel": channel_events[-1]["data"]["channel"] if channel_events else None,
        "revoked_hashes": sorted(revoked),
    }


def ledger_signals(state: dict[str, Any], observed_at: str) -> list[dict[str, Any]]:
    """Signals contributed by recorded history (never expires, never erased)."""
    out: list[dict[str, Any]] = []
    for e in state["historical_closures"]:
        d = e["data"]
        effect = {"ISSUE_FIRST_REDIRECT": "ISSUE_FIRST", "REFUSAL": "NO_OUTREACH"}.get(d["kind"])
        if effect is None:  # UNEXPLAINED closure: not evidence of any channel, but never permission
            out.append(_signal("ledger", "UNEXPLAINED_CLOSURE", "explicit", d.get("comment_url") or d["pr_url"],
                               None, d["excerpt"], "policy_ledger", observed_at, closure_pr=d["pr_url"]))
            continue
        out.append(_signal("ledger", effect, "explicit", d.get("comment_url") or d["pr_url"], None, d["excerpt"],
                           "policy_ledger", observed_at, closure_pr=d["pr_url"], recorded_at=e["timestamp"],
                           named_approvers=sorted({h.lower() for h in _MENTION.findall(d["excerpt"])})
                           if effect == "ISSUE_FIRST" else []))
    for e in state["events"]:
        if e["event_type"] == "PRIOR_REFUSAL_RECORDED":
            d = e["data"]
            out.append(_signal("ledger", "NO_OUTREACH", "explicit", d["source_url"], None, d["excerpt"],
                               "policy_ledger", observed_at, refusal=True, recorded_at=e["timestamp"]))
    return out


# ---------------------------------------------------------------------------
# Approval provenance
# ---------------------------------------------------------------------------


def _norm_url(url: str | None) -> str:
    return (url or "").strip().rstrip("/").lower()


def evaluate_approval(state: dict[str, Any], prior_issues: list[dict[str, Any]],
                      comments_by_issue: dict[str, list[dict[str, Any]] | None],
                      named_approvers: list[str]) -> dict[str, Any]:
    """Verify the newest active recorded approval against upstream comments.

    States: ``MISSING`` (none recorded), ``VERIFIED``, ``UNVERIFIED`` (evidence does not match
    upstream), ``WITHDRAWN``, ``INCOMPLETE`` (upstream comments unreadable). Only ``VERIFIED``
    opens the README PR path; everything else holds.
    """
    active = state["active_approvals"]
    result: dict[str, Any] = {"state": "MISSING", "record": None, "failed_checks": [], "checks": []}
    if not active:
        return result
    rec = active[-1]
    d = rec["data"]
    result["record"] = {"hash": rec["hash"], "recorded_at": rec["timestamp"], "recorded_by": rec["actor"], **d}
    failed: list[str] = []
    issue = next((i for i in prior_issues if _norm_url(i["url"]) == _norm_url(d["issue_url"])), None)
    comments = comments_by_issue.get(_norm_url(d["issue_url"]))
    if issue is None or issue.get("state") == "recorded_sent_not_seen_upstream":
        # A human-recorded send that search has not surfaced cannot have its authorship verified: retry later.
        failed.append("approval_issue_not_found_among_upstream_issues")
    elif not issue.get("gaia_authored"):
        failed.append("approval_issue_not_authored_by_campaign")
    if comments is None:
        result.update(state="INCOMPLETE", failed_checks=failed + ["issue_comments_unreadable"])
        return result
    cid = COMMENT_URL_RE.match(d["evidence_url"]).group(4)  # validated at record time
    hit = next((c for c in comments if str(c.get("id")) == cid), None)
    if hit is None:
        failed.append("evidence_comment_not_found_on_issue")
    else:
        user = hit.get("user") or {}
        login = (user.get("login") or "").lower()
        if login != d["approver"].strip().lstrip("@").lower():
            failed.append("evidence_comment_author_differs_from_recorded_approver")
        if user.get("type") == "Bot" or login.endswith("[bot]"):
            failed.append("evidence_comment_authored_by_bot")
        if hit.get("author_association") not in AUTHORITY_ASSOCIATIONS:
            failed.append(f"commenter_lacks_authority_association:{hit.get('author_association')}")
        if collapse(d["evidence_excerpt"]).lower() not in collapse(hit.get("body") or "").lower():
            failed.append("recorded_excerpt_not_in_upstream_comment")
        named = [n.lower().lstrip("@") for n in named_approvers]
        if named and login not in named and hit.get("author_association") != "OWNER":
            failed.append("approver_not_named_by_repo_policy")
        later = [c for c in comments
                 if (c.get("created_at") or "") > (hit.get("created_at") or "")
                 and (c.get("user") or {}).get("login", "").lower() == login
                 and any(p.search(c.get("body") or "") for p in WITHDRAWAL_PATTERNS)]
        if later:
            result.update(state="WITHDRAWN", failed_checks=failed + ["approver_withdrew_after_approving"])
            return result
    result["checks"] = ["issue_found", "campaign_authored", "comment_found", "author_matches",
                        "authority_association", "excerpt_present", "not_withdrawn"] if not failed else []
    result["failed_checks"] = failed
    result["state"] = "UNVERIFIED" if failed else "VERIFIED"
    return result


def approval_candidates(prior_issues: list[dict[str, Any]],
                        comments_by_issue: dict[str, list[dict[str, Any]] | None]) -> list[dict[str, Any]]:
    """Maintainer comments that *look like* approval. Surfaced for a human; never applied."""
    out: list[dict[str, Any]] = []
    for issue in prior_issues:
        for c in comments_by_issue.get(_norm_url(issue["url"])) or []:
            body = c.get("body") or ""
            user = c.get("user") or {}
            if user.get("type") == "Bot" or c.get("author_association") not in AUTHORITY_ASSOCIATIONS:
                continue
            for p in APPROVAL_PATTERNS:
                m = p.search(body)
                if m and not _negated(body, m.start()):
                    out.append({"issue_url": issue["url"], "comment_url": c.get("html_url"), "comment_id": c.get("id"),
                                "author": user.get("login"), "association": c.get("author_association"),
                                "excerpt": excerpt_around(body, m.start(), m.end()), "created_at": c.get("created_at"),
                                "applied": False})
                    break
    return out


# ---------------------------------------------------------------------------
# Channel decision
# ---------------------------------------------------------------------------


def decide_channel(signals: list[dict[str, Any]], issue_channel: dict[str, Any] | None,
                   repo_flags: dict[str, Any], complete: bool, incomplete_reasons: list[str],
                   terminal_restriction: str | None) -> dict[str, Any]:
    """Pure channel decision. Restrictions win over permissions; incompleteness wins over all.

    ``partial_channel`` records what the evidence seen so far indicates when the scan was
    incomplete, so a reviewer can see *why* it holds, while ``channel`` stays ``UNKNOWN``.
    """
    reasons: list[str] = []
    conflicts: list[str] = []
    by_effect: dict[str, list[dict[str, Any]]] = {}
    for s in signals:
        by_effect.setdefault(s["effect"], []).append(s)
    explicit = lambda e: [s for s in by_effect.get(e, []) if s["strength"] == "explicit"]  # noqa: E731
    no_out, issue_first, permits = explicit("NO_OUTREACH"), explicit("ISSUE_FIRST"), explicit("PERMITS_PR")
    if repo_flags.get("archived") or repo_flags.get("disabled"):
        no_out = no_out + [_signal("repo_settings", "NO_OUTREACH", "explicit", repo_flags.get("html_url"), None,
                                   "Repository is archived or disabled and cannot receive contributions.",
                                   "repo_settings", repo_flags.get("observed_at", ""))]
    if terminal_restriction:
        no_out = no_out + [_signal("ledger", "NO_OUTREACH", "explicit", None, None,
                                   f"Campaign ledger records terminal restriction {terminal_restriction}.",
                                   "policy_ledger", repo_flags.get("observed_at", ""))]
    if no_out and (issue_first or permits):
        conflicts.append("restriction_overrides_other_signals")

    def finish(channel: str, why: list[str], decisive: list[dict[str, Any]], partial: str | None = None) -> dict[str, Any]:
        return {"channel": channel, "partial_channel": partial, "reasons": why,
                "decisive_signal_ids": [s["id"] for s in decisive], "conflicts": conflicts,
                "extra_signals": [s for s in decisive if s["id"] not in {x["id"] for x in signals}]}

    # What the evidence says so far, regardless of completeness.
    if no_out:
        partial, why, dec = "NO_OUTREACH", ["explicit_restriction_or_refusal"], no_out
    elif issue_first:
        if issue_channel and issue_channel.get("proposal_possible") is False:
            partial, why, dec = "NO_OUTREACH", [
                "issue_first_required_but_issue_channel_unavailable:" + str(issue_channel.get("reason"))], issue_first
        else:
            partial, why, dec = "ISSUE_FIRST", ["repo_requires_issue_before_outside_pr"], issue_first
            if permits:
                conflicts.append("issue_first_overrides_general_pr_welcome")
    elif permits:
        partial, why, dec = "PR_ALLOWED", ["explicit_permission_from_authoritative_source"], permits
    else:
        partial, why, dec = None, ["no_explicit_permission_found:absence_of_prohibition_is_not_permission"], []
        if by_effect.get("UNEXPLAINED_CLOSURE"):
            why.append("prior_pr_closed_without_explanation")
    if not complete:
        return finish("UNKNOWN", ["evidence_incomplete_failing_closed", *incomplete_reasons], dec, partial)
    if partial is None:
        return finish("UNKNOWN", why, [])
    return finish(partial, why, dec)


# ---------------------------------------------------------------------------
# Outreach attempt (issue + PR are stages of ONE attempt)
# ---------------------------------------------------------------------------


def summarize_attempt(prior_issues: list[dict[str, Any]], prior_prs: list[dict[str, Any]],
                      state: dict[str, Any], approval: dict[str, Any]) -> dict[str, Any]:
    stages: list[dict[str, Any]] = []
    for p in prior_prs:
        stages.append({"stage": "PR", "url": p["url"], "state": p["state"]})
    for i in prior_issues:
        stages.append({"stage": "ISSUE", "url": i["url"], "state": i["state"]})
    for e in state["proposals_sent"]:
        if not any(_norm_url(s["url"]) == _norm_url(e["data"]["issue_url"]) for s in stages):
            stages.append({"stage": "ISSUE", "url": e["data"]["issue_url"], "state": "recorded_sent_not_seen_upstream"})
    open_issue = any(s["stage"] == "ISSUE" and s["state"] in ("open", "recorded_sent_not_seen_upstream") for s in stages)
    any_issue = any(s["stage"] == "ISSUE" for s in stages)
    return {
        "stages": stages,
        "one_attempt_two_stages": True,
        "issue_stage": ("APPROVED" if approval["state"] == "VERIFIED" else "OPEN" if open_issue
                        else "CLOSED_WITHOUT_VERIFIED_APPROVAL" if any_issue else "NONE"),
        "has_prior_outreach": bool(stages),
    }


def next_action(channel: str, complete: bool, issue_channel: dict[str, Any] | None, attempt: dict[str, Any],
                approval: dict[str, Any], any_prior_issue: bool, has_ledger_prs: bool) -> tuple[str, str]:
    """Channel-specific next action: (code, human sentence). Holds never suggest PR or issue creation."""
    if channel == "NO_OUTREACH":
        return ACTION_NO_OUTREACH, "Internal hold. The repository forbids or refused this contact; open no PR and no issue."
    if channel == "UNKNOWN":
        if not complete:
            return ACTION_INCOMPLETE, "Evidence was incomplete (rate limit, truncation or budget). Retry the scoped scan later; open no PR and no issue."
        return ACTION_UNKNOWN, ("No explicit permission found. Absence of a prohibition is not permission. "
                                "A human resolves the policy evidence; open no PR and no issue.")
    if channel == "ISSUE_FIRST":
        st = approval["state"]
        if st == "VERIFIED":
            return ACTION_PR_AFTER_APPROVAL, ("Recorded maintainer approval verified upstream. One README PR may proceed, "
                                              "but only through `predispatch` and the campaign approval gate.")
        if st in ("UNVERIFIED", "WITHDRAWN", "INCOMPLETE"):
            return ACTION_APPROVAL_UNVERIFIED, "A maintainer approval is recorded but not verified upstream; hold and review its provenance."
        if any_prior_issue or attempt["issue_stage"] != "NONE":
            if attempt["issue_stage"] == "OPEN":
                return ACTION_WAIT_ISSUE, "A proposal issue already exists. Wait for the maintainer; do not follow up, reopen, or file a second issue or PR."
            return ACTION_ISSUE_CLOSED, "A Gaia issue exists but is closed without a verified approval. No second issue; a human reviews."
        if issue_channel and issue_channel.get("proposal_possible") is False:
            return ACTION_NO_OUTREACH, "Issue-first repo whose issue channel is unavailable; internal hold."
        return ACTION_DRAFT_ISSUE, ("Keep a local draft of ONE concise proposal issue (never sent by tooling). "
                                    "Contacting upstream needs fresh human approval; the README PR waits for a recorded maintainer approval.")
    # PR_ALLOWED
    if attempt["has_prior_outreach"] or has_ledger_prs:
        return ACTION_EXISTING_OUTREACH, "Guidance allows PRs, but this attempt already has a PR or issue stage. No new PR or issue."
    return ACTION_PR_PATH, "Guidance explicitly allows outside PRs. Needs campaign human approval, then `predispatch` immediately before the single README PR."


# ---------------------------------------------------------------------------
# Local-only proposal draft (never sent)
# ---------------------------------------------------------------------------

DRAFT_BANNER = (
    "<!-- DRAFT ONLY. LOCAL FILE. NEVER SENT. This tooling has no path that posts to GitHub.\n"
    "     Contacting upstream needs fresh human approval and a human to do it. -->"
)


def render_draft_proposal(repo: str, skill_name: str, deep_link: str, badge_url: str) -> str:
    """One concise *proposal* (a question, not a claim to be approved)."""
    body = (
        f"{DRAFT_BANNER}\n\n"
        f"Title: Would a Gaia Skill Tree recognition badge in the README be welcome?\n\n"
        f"Hello! {skill_name} is recognized in the [Gaia Skill Tree]({deep_link}), an open registry of agent skills.\n\n"
        f"Would you like an optional badge linking to that page in your README? It would be a single "
        f"README-only change, e.g. `![Gaia Skill]({badge_url})`.\n\n"
        f"If this isn't something you want, no problem at all, and we will not follow up. "
        f"We will only open a PR if you tell us it is welcome.\n\nThank you for building {repo.split('/')[-1]}.\n"
    )
    return body


def draft_word_count(text: str) -> int:
    return len(re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL).split())


# ---------------------------------------------------------------------------
# File selection (which policy documents are worth fetching)
# ---------------------------------------------------------------------------

_NAME_RES = {
    "contributing": re.compile(r"^contributing(\.\w+)?$", _FLAGS),
    "agents": re.compile(r"^(agents|claude)\.md$", _FLAGS),
    "code_of_conduct": re.compile(r"^code[_-]of[_-]conduct(\.\w+)?$", _FLAGS),
    "security": re.compile(r"^security(\.\w+)?$", _FLAGS),
    "pr_template": re.compile(r"^pull_request_template(\.\w+)?$", _FLAGS),
    "issue_template": re.compile(r"^issue_template(\.\w+)?$", _FLAGS),
}
_WORKFLOW_NAME = re.compile(
    r"issue[-_ ]?first|require[-_ ]?issue|linked?[-_ ]?issue|check[-_ ]?issue|contributor|polic|external|"
    r"first[-_ ]?time|no[-_ ]?pr|close[-_ ]?pr|pr[-_ ]?check|ai[-_ ]?(?:use|policy|disclos)", _FLAGS)
_DOC_EXT = (".md", ".markdown", ".txt", ".rst", ".yml", ".yaml", "")
_PRIORITY = ("contributing", "agents", "issue_config", "pr_template", "issue_template", "code_of_conduct",
             "security", "workflow")


def select_policy_files(root: list[dict[str, Any]], github: list[dict[str, Any]],
                        issue_dir: tuple[str, list[dict[str, Any]]] | None,
                        pr_dir: tuple[str, list[dict[str, Any]]] | None,
                        workflows: tuple[str, list[dict[str, Any]]] | None) -> tuple[list[dict[str, str]], list[str]]:
    """Pure: choose policy documents from directory listings, in priority order.

    Returns (candidates, absent) where absent lists the standard policy paths the listings prove do
    not exist (a definitive negative: a listing is a successful read, not a missing-evidence guess).
    """
    cands: list[dict[str, str]] = []

    def files(entries: list[dict[str, Any]], prefix: str) -> list[tuple[str, str]]:
        return [(e["name"], f"{prefix}{e['name']}") for e in entries if e.get("type") == "file"]

    for entries, prefix in ((root, ""), (github, ".github/")):
        for name, path in files(entries, prefix):
            for kind, rx in _NAME_RES.items():
                if rx.match(name) and not (kind == "agents" and prefix):
                    cands.append({"kind": kind, "path": path})
    if issue_dir:
        base, entries = issue_dir
        for name, path in files(entries, base + "/"):
            if name.lower() in ("config.yml", "config.yaml"):
                cands.append({"kind": "issue_config", "path": path})
            elif name.lower().endswith((".md", ".yml", ".yaml")):
                cands.append({"kind": "issue_template", "path": path})
    if pr_dir:
        base, entries = pr_dir
        for name, path in files(entries, base + "/"):
            if name.lower().endswith(".md"):
                cands.append({"kind": "pr_template", "path": path})
    if workflows:
        base, entries = workflows
        for name, path in files(entries, base + "/"):
            if name.lower().endswith((".yml", ".yaml")) and _WORKFLOW_NAME.search(name):
                cands.append({"kind": "workflow", "path": path})
    cands.sort(key=lambda c: (_PRIORITY.index(c["kind"]), c["path"]))
    have_kinds = {c["kind"] for c in cands}
    absent = []
    if "contributing" not in have_kinds:
        absent += ["CONTRIBUTING.md", ".github/CONTRIBUTING.md"]
    for kind, label in (("agents", "AGENTS.md / CLAUDE.md"), ("code_of_conduct", "CODE_OF_CONDUCT.md"),
                        ("security", "SECURITY.md"), ("pr_template", "pull request template")):
        if kind not in have_kinds:
            absent.append(label)
    if issue_dir is None:
        absent.append("ISSUE_TEMPLATE/")
    return cands, absent


def unexplained_closure_signal(pr_url: str, closed_at: str | None, observed_at: str) -> dict[str, Any]:
    """A Gaia PR closed unmerged with no recognisable maintainer/bot explanation: never a permission."""
    return _signal("comment", "UNEXPLAINED_CLOSURE", "explicit", pr_url, None,
                   f"Gaia PR closed without merge and without a recognisable explanation (closed_at={closed_at}).",
                   "upstream_state", observed_at, closure_pr=pr_url)


def issue_not_planned_signal(issue_url: str, closed_at: str | None, observed_at: str) -> dict[str, Any]:
    """A Gaia issue closed as 'not planned' is a refusal."""
    return _signal("comment", "NO_OUTREACH", "explicit", issue_url, None,
                   f"Gaia issue closed as not planned (closed_at={closed_at}).", "upstream_state", observed_at,
                   refusal=True)


def workflow_name_only_signal(path: str, url: str | None, observed_at: str) -> dict[str, Any]:
    """A policy-looking workflow file name is only a weak hint; content must confirm it."""
    return _signal("workflow", "ISSUE_FIRST", "weak", url, path,
                   f"Workflow file name suggests a contribution policy check: {path}", "policy_workflow", observed_at)


# ---------------------------------------------------------------------------
# Assembly: raw evidence + ledger -> the policy block carried in receipts
# ---------------------------------------------------------------------------

MAX_SOURCES = 40


def parse_pr_key(url: str | None, keys: set[str]) -> tuple[str, int] | None:
    m = PR_URL_RE.match((url or "").strip())
    if not m:
        return None
    full = normalize_repo_name(f"{m.group(1)}/{m.group(2)}")
    return ("family" if full in keys else full, int(m.group(3)))


def _item_state(item: dict[str, Any]) -> str:
    if "pull_request" in item:
        if item.get("state") == "open":
            return "open"
        return "merged" if (item.get("pull_request") or {}).get("merged_at") else "closed_unmerged"
    return item.get("state", "open")


def mentionsGaiaSite(text: str) -> bool:
    """Recognize real site links, including bare domains, without trusting URL substrings.

    Keep each URL token intact: a matching name in userinfo, a path, query or an
    attacker-controlled hostname is not a reference to the Gaia site.
    """
    for token in re.findall(r'''[^\s<>()"'`]+''', text):
        token = token.rstrip(".,;!?")
        # Bare domains are often emphasized or displayed as Markdown link text.
        # Strip balanced outer markup only; never split a URL's authority/path.
        wrapped = True
        while wrapped:
            wrapped = False
            for left, right in (("**", "**"), ("__", "__"), ("~~", "~~"), ("*", "*"), ("_", "_"), ("[", "]")):
                if len(token) > len(left) + len(right) and token.startswith(left) and token.endswith(right):
                    token = token[len(left):-len(right)]
                    wrapped = True
                    break
        candidate = token if "://" in token or token.startswith("//") else "//" + token
        try:
            parsed = urllib.parse.urlsplit(candidate)
            if parsed.scheme not in ("", "http", "https") or parsed.username is not None or parsed.password is not None:
                continue
            # Accessing port validates malformed and out-of-range authority values.
            if parsed.port is not None and not 0 < parsed.port <= 65535:
                continue
            if (parsed.hostname or "").removesuffix(".") in {"gaiaskilltree.com", "www.gaiaskilltree.com"}:
                return True
        except ValueError:
            continue
    return False


def normalize_prior_items(items: list[dict[str, Any]], authors: tuple[str, ...], keys: set[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Search hits -> (issues, prs), deduplicated across aliases/renames by number."""
    issues: dict[int, dict[str, Any]] = {}
    prs: dict[int, dict[str, Any]] = {}
    low_authors = {a.lower() for a in authors}
    for it in items:
        n = it.get("number")
        url = it.get("html_url")
        if not isinstance(n, int) or not url:
            continue
        text = f"{it.get('title') or ''} {it.get('body') or ''}".lower()
        user = (it.get("user") or {}).get("login") or ""
        rec = {
            "url": url, "number": n, "state": _item_state(it), "state_reason": it.get("state_reason"),
            "title": it.get("title"), "author": user, "author_association": it.get("author_association"),
            "closed_at": it.get("closed_at"), "created_at": it.get("created_at"),
            "gaia_authored": user.lower() in low_authors or "gaia skill tree" in text or mentionsGaiaSite(text),
        }
        (prs if "pull_request" in it else issues).setdefault(n, rec)
    return ([issues[k] for k in sorted(issues)], [prs[k] for k in sorted(prs)])


def assemble_policy(raw: dict[str, Any], *, record: dict[str, Any], state: dict[str, Any], observed_at: str,
                    authors: tuple[str, ...], flags: dict[str, Any], terminal_restriction: str | None,
                    upstream_prs: list[dict[str, Any]], ledger_pr_urls: list[str],
                    names: list[str], migrations: dict[str, str] | None = None,
                    upstream_complete: bool = True) -> dict[str, Any]:
    """Build the full policy block (pure). ``raw`` is what the scan observed (see badge_reconcile)."""
    keys = repo_keys(names, migrations)
    sigs = list(raw.get("signals", [])) + ledger_signals(state, observed_at)
    ic_in = raw.get("issue_channel_inputs")
    issue_channel = None
    if ic_in is not None:
        issue_channel = analyze_issue_channel(
            ic_in.get("issues_enabled"), ic_in.get("config_text"), ic_in.get("templates", []),
            ic_in.get("discussions_enabled"),
            closed_text_signals=any(s["effect"] == "ISSUES_CLOSED" for s in sigs),
            bug_only_text=any(s["effect"] == "BUG_ONLY" for s in sigs))
    reasons_incomplete = list(raw.get("incomplete_reasons", []))
    if not upstream_complete:
        reasons_incomplete.append("upstream_pr_or_readme_evidence_incomplete")
    if not raw.get("scanned", True):
        reasons_incomplete.append("policy_not_scanned")
    complete = not reasons_incomplete

    prior_issues, search_prs = normalize_prior_items(raw.get("prior_items", []), authors, keys)
    for e in state["proposals_sent"]:  # human-recorded sends that search has not (yet) surfaced
        if not any(_norm_url(i["url"]) == _norm_url(e["data"]["issue_url"]) for i in prior_issues):
            prior_issues.append({"url": e["data"]["issue_url"], "number": int(ISSUE_URL_RE.match(e["data"]["issue_url"]).group(3)),
                                 "state": "recorded_sent_not_seen_upstream", "state_reason": None, "title": None,
                                 "author": e["actor"], "author_association": None, "closed_at": None,
                                 "created_at": e["timestamp"], "gaia_authored": True})
    prior_prs: list[dict[str, Any]] = []
    seen_pr: set[tuple[str, int]] = set()
    for p in [*({"url": u, "state": x["state"]} for x in upstream_prs for u in [x["url"]]), *search_prs,
              *({"url": u, "state": "ledger_recorded"} for u in ledger_pr_urls)]:
        k = parse_pr_key(p["url"], keys) or (p["url"].lower(), 0)
        if k not in seen_pr:
            seen_pr.add(k)
            prior_prs.append({"url": p["url"], "state": p["state"]})

    comments = {k: v for k, v in raw.get("comments", {}).items()}
    named = sorted({n for s in sigs if s["effect"] == "ISSUE_FIRST" and s["strength"] == "explicit"
                    for n in s.get("named_approvers", [])})
    approval = evaluate_approval(state, prior_issues, comments, named)
    decision = decide_channel(sigs, issue_channel, flags, complete, reasons_incomplete, terminal_restriction)
    channel = decision["channel"]
    attempt = summarize_attempt(prior_issues, prior_prs, state, approval)
    code, sentence = next_action(channel, complete, issue_channel, attempt, approval,
                                 bool(prior_issues), bool(ledger_pr_urls))
    if not raw.get("scanned", True):
        code, sentence = ACTION_NOT_SCANNED, ("Policy was not scanned for this repo (scope guard). Run a scoped "
                                              "`reconcile --repo` before any outreach; open no PR and no issue.")
    elif channel == "UNKNOWN" and complete and attempt["has_prior_outreach"]:
        code, sentence = ACTION_EXISTING_OUTREACH, "Prior outreach exists and no permission is established; no new PR or issue."

    # A PR closed under the repo's own issue-first policy must not block the one approved README PR.
    redirect_keys = {parse_pr_key(e["data"]["pr_url"], keys) for e in state["historical_closures"]
                     if e["data"]["kind"] == "ISSUE_FIRST_REDIRECT"}
    prior_keys = {parse_pr_key(p["url"], keys) for p in prior_prs}
    waived = bool(channel == "ISSUE_FIRST" and approval["state"] == "VERIFIED" and prior_keys and None not in prior_keys
                  and prior_keys <= redirect_keys
                  and all(p["state"] in ("closed_unmerged", "ledger_recorded") for p in prior_prs))

    sources = list({s["id"]: s for s in [*sigs, *decision["extra_signals"]]}.values())
    decisive = set(decision["decisive_signal_ids"])
    for s in sources:
        s["decisive"] = s["id"] in decisive
    sources.sort(key=lambda s: (not s["decisive"], s["kind"], s["path"] or "", s["id"]))
    needs_maint = channel == "ISSUE_FIRST"
    approval_required = {
        "campaign_human_approval": channel in ("PR_ALLOWED", "ISSUE_FIRST"),
        "maintainer_approval": needs_maint,
        "maintainer_approval_state": approval["state"] if needs_maint else "NOT_APPLICABLE",
        "named_approvers": named,
        "satisfied": (channel == "PR_ALLOWED") or (needs_maint and approval["state"] == "VERIFIED"),
    }
    cost = dict(raw.get("cost", {}))
    return {
        "scanned": bool(raw.get("scanned", True)),
        "schema_version": SCHEMA_VERSION,
        "observed_at": observed_at,
        "channel": channel,
        "partial_channel": decision["partial_channel"],
        "channel_reasons": decision["reasons"],
        "conflicts": decision["conflicts"],
        "decisive_signal_ids": decision["decisive_signal_ids"],
        "sources": sources[:MAX_SOURCES],
        "sources_truncated": len(sources) > MAX_SOURCES,
        "files": raw.get("files", {}),
        "issue_channel": issue_channel,
        "prior_issues": prior_issues,
        "prior_issue_urls": sorted({i["url"] for i in prior_issues}),
        "prior_prs": prior_prs,
        "attempt": attempt,
        "approval": approval,
        "approval_candidates": approval_candidates(prior_issues, comments),
        "approval_required": approval_required,
        "historical_closures": [{"event_hash": e["hash"], "recorded_at": e["timestamp"], **e["data"]}
                                for e in state["historical_closures"]],
        "recorded_refusals": [{"event_hash": e["hash"], "recorded_at": e["timestamp"], **e["data"]} for e in state["refusals"]
                              if e["event_type"] == "PRIOR_REFUSAL_RECORDED"],
        "local_drafts": [{"event_hash": e["hash"], **e["data"]} for e in state["drafts"]],
        "pr_history_waived": waived,
        "recommended_next_action": code,
        "next_action_detail": sentence,
        "completeness": {"complete": complete, "incomplete_reasons": reasons_incomplete,
                         "searches_complete": not any(r.startswith("prior_search") for r in reasons_incomplete)},
        "cost": cost,
    }


def unscanned_policy(observed_at: str, state: dict[str, Any], names: list[str]) -> dict[str, Any]:
    """Policy block for a repo whose policy scan was not run (scope guard) or could not start."""
    return assemble_policy({"scanned": False, "incomplete_reasons": [], "cost": {"api_calls": 0, "budget": 0,
                                                                                  "budget_exhausted": False}},
                           record={}, state=state, observed_at=observed_at, authors=(), flags={},
                           terminal_restriction=None, upstream_prs=[], ledger_pr_urls=[], names=names)
