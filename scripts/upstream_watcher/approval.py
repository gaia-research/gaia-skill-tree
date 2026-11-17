"""scripts.upstream_watcher.approval — the digest, approval and Verifier checks (#2131 round 3, D1-D3).

One copy of each rule, used by the watcher (batch.py, issuer.py) and by the workflows
(upstream-approve.yml, upstream-reject.yml, upstream-close-children.yml). The workflows run it from a
checkout of main, with the repository root on sys.path.

Digest. ``payloadSha256`` is the SHA-256 of the canonical JSON of the payload without that field. The
watcher recomputes it on every read (D1a): a stored digest that does not match its own payload is a
tampered payload. A legacy payload carries no digest and is compared by content instead.

Approval marker. When an authorized ``upstream:approved`` event lands, the approve workflow records the
digest it approved as a bot-authored comment (``<!-- gaia-upstream-approval payload=<sha> -->``). A
later run (a re-fire, or a manual dispatch) syncs only when the payload it extracted still hashes to
that digest (D1b, D6). Only comments from the watcher's own login with the Bot user type count (I3).

Verifier. ``verifier_status`` is the labeler check the workflows run against the freshly built index. There is
no bootstrap grant (M1): an index with no authorised Verifier denies everyone. The allowlist (``allowlisted``)
is the lockout escape hatch, and it needs the sender's user type (M2). Handles match case-insensitively (L9).

Skip. ``skip_label_authorized`` decides whether an applied ``skip-child-gate`` label is honoured (L5).
"""

from __future__ import annotations

import hashlib
import json
import os
import re

from scripts.upstream_watcher import records
# L3: the one definition of the payload block regex. Every reader imports it from here.
from scripts.upstream_watcher.markers import PAYLOAD_RE  # noqa: F401  (re-exported)

APPROVAL_RE = re.compile(r"<!-- gaia-upstream-approval payload=([0-9a-f]{64}) -->")
APPROVAL_RESET_MARKER = "gaia-upstream-approval-reset"
LEGACY_KEYS = frozenset({
    "skillId", "previousVersion", "newVersion", "releasedAt", "sourceUrl", "mode",
    "componentAdds", "componentRemoves", "linkLiveness", "nameDrift",
})
LEGACY_DEFAULTS = {"componentAdds": [], "componentRemoves": [], "linkLiveness": [], "nameDrift": []}


class PayloadError(ValueError):
    """The umbrella body does not hold a payload that can be trusted."""


def canonical_hash(payload: dict) -> str:
    """SHA-256 over the canonical JSON of *payload*, excluding its own digest field."""
    data = {key: value for key, value in payload.items() if key != "payloadSha256"}
    encoded = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def payload_tampered(payload: dict | None) -> bool:
    """D1a: True when the stored digest of *payload* does not match its own content.

    A payload without a stored digest is a legacy payload. It cannot be checked this way, so it is
    compared by content (see changed_fields and representation_only in batch.py).
    """
    if payload is None or "payloadSha256" not in payload:
        return False
    return payload["payloadSha256"] != canonical_hash(payload)


def extract_payload(body: str | None) -> tuple[dict, str]:
    """Return ``(payload, digest)`` for an umbrella body, or raise PayloadError.

    The digest is recomputed from the extracted payload. A stored digest that differs fails closed.
    """
    if body is not None and (not isinstance(body, str) or len(body) > 65_536):
        raise PayloadError("upstream body is not bounded text")
    matches = list(PAYLOAD_RE.finditer(body or ""))
    if len(matches) != 1:
        raise PayloadError("exactly one gaia-upstream-payload block is required in the umbrella body")
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise PayloadError("duplicate JSON field in upstream payload")
            result[key] = value
        return result
    def invalid_constant(value):
        raise PayloadError("non-finite JSON number in upstream payload")
    try:
        data = json.loads(matches[0].group(1), object_pairs_hook=unique_object, parse_constant=invalid_constant)
    except json.JSONDecodeError as exc:
        raise PayloadError(f"the payload JSON does not parse: {exc}") from exc
    if not isinstance(data, dict):
        raise PayloadError("the payload is not a JSON object")
    digest = canonical_hash(data)
    stored = data.get("payloadSha256")
    if stored is not None and stored != digest:
        raise PayloadError(
            f"the stored payloadSha256 does not match the payload (stored {stored}, computed {digest}); "
            "the umbrella body was edited after its digest was written"
        )
    return data, digest


def named_authority() -> dict:
    """Read canonical source metadata; no generated evidence/trust schema changes."""
    from scripts.lib.named_iterator import iter_named_skills
    rows = {}
    try:
        for _path, meta in iter_named_skills():
            identifier = meta.get("id")
            if identifier in rows:
                raise PayloadError("duplicate canonical named identity")
            if identifier:
                rows[identifier] = meta
    except PayloadError:
        raise
    except Exception as exc:
        raise PayloadError("cannot read canonical named authority") from exc
    if not rows:
        raise PayloadError("canonical named authority is empty")
    return rows


def envelope_comments(payload: dict, issue_number=None):
    """Read a required record generation through the existing authenticated gh port."""
    if "candidateRecords" not in payload:
        return None
    from scripts.upstream_watcher.live import LiveGh, GhError
    number = str(issue_number or os.environ.get("ISSUE_NUMBER") or "")
    if not number.isdigit() or int(number) < 1:
        raise PayloadError("records-mode envelope requires an exact issue number")
    try:
        return LiveGh(repo=os.environ.get("REPO") or None).list_comments(int(number))
    except GhError as exc:
        raise PayloadError("repository record generation could not be read") from exc


def workflow_payload(body: str | None, *, title: str | None = None) -> tuple[dict, str]:
    """Select ONE finding after the existing workflow actor guard authenticates.

    Inputs are selectors, not authority. The label event cannot select anything
    in a repo envelope. An explicit authenticated workflow_dispatch binds all
    three identity-bearing inputs; automatic refires cannot invent a selection.
    Legacy issues remain read-only until separately approved migration.
    """
    from scripts.upstream_watcher import envelope
    payload, _digest = extract_payload(body)
    if not envelope.is_envelope(payload):
        raise PayloadError("legacy upstream payload is held for separately approved migration")
    if os.environ.get("EVENT_NAME") != "workflow_dispatch" or os.environ.get("INPUT_REFIRE") == "true":
        raise PayloadError("repository labels/refires do not approve named findings; use explicit dispatch selectors")
    return envelope.select(body, named_authority(),
        identifier=os.environ.get("NAMED_SKILL_ID"), digest=os.environ.get("FINDING_SHA256"),
        source=os.environ.get("APPROVED_SOURCE_URL"), title_text=title,
        comments=envelope_comments(payload))


def verify_repository_target(issue: dict, *, require_selection: bool = True, require_approved: bool = True) -> bool:
    """Read-only freshness/cardinality/legacy gate, NOT actor authorization.

    Approval cannot target a later duplicate or a parallel current-source issue
    for a named scope whose historical repository still carries a migration hold.
    Both the initial workflow preflight and final re-verification call this.
    """
    from scripts.upstream_watcher import envelope
    from scripts.upstream_watcher.live import LiveGh, GhError
    from scripts.upstream_watcher.repository_batch import read_repository_live, inspect_history, policy_record, historical_authority
    number = str(issue.get("number") or os.environ.get("ISSUE_NUMBER") or "")
    if not number.isdigit() or int(number) < 1:
        raise PayloadError("approval requires an exact canonical issue number")
    authority = named_authority()
    raw, _ = extract_payload(issue.get("body"))
    if not envelope.is_envelope(raw):
        raise PayloadError("legacy payload is held for separately approved migration")
    current = envelope.read(issue.get("body"), authority, title_text=issue.get("title"),
                            comments=envelope_comments(raw, number))
    gh = LiveGh(repo=os.environ.get("REPO") or None)
    try:
        live = read_repository_live(gh)
        found, holds, stored = inspect_history(current["repository"], live, gh, authority,
                                               policy_record(), historical_authority)
    except (GhError, OSError, ValueError, TypeError, KeyError) as exc:
        raise PayloadError(f"canonical repository approval evidence unavailable: {exc}") from exc
    if holds:
        raise PayloadError("repository or historical named scope has an unresolved migration hold")
    if found.canonical is None or found.canonical["number"] != int(number):
        raise PayloadError("approval target is not the lowest canonical OPEN repository umbrella")
    if require_approved and "upstream:approved" not in {
            v.get("name") if isinstance(v, dict) else v for v in found.canonical.get("labels", [])}:
        raise PayloadError("canonical umbrella no longer carries upstream:approved")
    if require_selection:
        selected = [f for f in stored[int(number)]["findings"] if f["skillId"] == os.environ.get("NAMED_SKILL_ID")]
        if (len(selected) != 1 or selected[0]["payloadSha256"] != os.environ.get("FINDING_SHA256")
                or selected[0]["sourceUrl"] != os.environ.get("APPROVED_SOURCE_URL")):
            raise PayloadError("canonical named finding changed after selection")
    return True


def owned_upstream_issue(issue: dict, *, allow_envelope: bool = False) -> bool:
    """Prove upstream umbrella/bootstrap ownership before any label-guard write."""
    from scripts.upstream_watcher.evidence import title_suite_and_version, suite_of

    if not isinstance(issue, dict):
        return False
    labels = {label.get("name") if isinstance(label, dict) else label for label in issue.get("labels", [])}
    kind = "bootstrap" if "upstream:bootstrap" in labels else "release" if "upstream:release" in labels else None
    if kind is None:
        return False
    try:
        payload, _ = extract_payload(issue.get("body"))
        from scripts.upstream_watcher import envelope
        if envelope.is_envelope(payload):
            if kind != "release" or not allow_envelope:
                return False
            envelope.read(issue.get("body"), named_authority(), title_text=issue.get("title", ""),
                          comments=envelope_comments(payload, issue.get("number")))
            return True
        # Ownership is historical identification, NOT migration/write authority.
        # Workflow compatibility holds run before any legacy write consumer.
        title = title_suite_and_version(issue.get("title", ""), kind)
        return bool(title and title == (suite_of(payload, kind), payload.get("newVersion")))
    except (PayloadError, KeyError, TypeError, ValueError):
        return False


def approval_marker(payload_hash: str) -> str:
    return f"<!-- gaia-upstream-approval payload={payload_hash} -->"


def reset_marker(payload_hash: str) -> str:
    """The hidden marker of one approval-reset note (L3). It names the payload hash the reset moved to."""
    return f"<!-- {APPROVAL_RESET_MARKER} payload={payload_hash} -->"


def latest_approval_sha(comments: list[dict]) -> str | None:
    """The digest of the most recent approval marker written by the watcher's own login and type (I3)."""
    latest = None
    for comment in comments:
        if not records.is_watcher_comment(comment):
            continue
        match = APPROVAL_RE.search(comment.get("body") or "")
        if match:
            latest = match.group(1)
    return latest


def decode_pages(text: str) -> list:
    """Items from ``gh api --paginate`` output, which prints one JSON array per page back to back."""
    decoder = json.JSONDecoder()
    items: list = []
    pos = 0
    while True:
        while pos < len(text) and text[pos].isspace():
            pos += 1
        if pos >= len(text):
            return items
        page, pos = decoder.raw_decode(text, pos)
        if not isinstance(page, list):
            raise ValueError("a page is not a JSON array")
        items.extend(page)


SKIP_LABEL = "skip-child-gate"
# M2: bot-named accounts. These exact logins are trusted only for a Bot sender.
BOT_NAMES = frozenset({"github-actions", "codex", "jules", "claude-bot", "gemini-bot"})
# C9 (M-1): the explicit set of trusted bot logins. A login is NOT trusted because it ends in '[bot]': any GitHub App
# can have that suffix (dependabot[bot], renovate[bot], an arbitrary app). Only these names count, and only for a Bot.
TRUSTED_BOT_LOGINS = frozenset({"github-actions[bot]"} | BOT_NAMES)
# M2: the human escape hatch. The handle is trusted only for the User account with this id.
HUMAN_ALLOWLIST_LOGIN = "mbtiongson1"
HUMAN_ALLOWLIST_ID = 153011150


def latest_labeler_actor(events: list[dict], label: str = "upstream:approved") -> dict | None:
    """The actor object (login, type, id) of the most recent ``labeled`` event for *label*, or None (fail closed)."""
    labeled = [
        event for event in events
        if event.get("event") == "labeled" and (event.get("label") or {}).get("name") == label
    ]
    if not labeled:
        return None
    newest = max(labeled, key=lambda event: int(event.get("id") or 0))
    actor = newest.get("actor")
    if not isinstance(actor, dict) or not actor.get("login"):
        return None
    return actor


def latest_labeler(events: list[dict], label: str = "upstream:approved") -> str | None:
    """Login of the actor behind the most recent ``labeled`` event for *label*, or None (fail closed)."""
    actor = latest_labeler_actor(events, label)
    return actor["login"] if actor else None


def _as_int(value) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def allowlisted(login: str | None, sender_type: str | None, sender_id) -> bool:
    """M2 and C9 (M-1): True when *login* is an allowlisted actor for a sender of this *sender_type* and *sender_id*.

    - the bot logins in TRUSTED_BOT_LOGINS (github-actions[bot] and the named bots) are trusted only when the sender
      is a Bot. No other '[bot]' login is trusted, whatever its suffix;
    - the human handle is trusted only when the sender is a User with HUMAN_ALLOWLIST_ID;
    - anything else is not allowlisted here. The Verifier index decides it.
    """
    if not isinstance(login, str) or not login:
        return False
    if login in TRUSTED_BOT_LOGINS:
        return sender_type == "Bot"
    if login == HUMAN_ALLOWLIST_LOGIN:
        return sender_type == "User" and _as_int(sender_id) == HUMAN_ALLOWLIST_ID
    return False


def star_level(value) -> int | None:
    """M1: the star level of an index entry as an int, or None. 4, '4', '4★', '4 ★' and '★★★★' are all 4-star."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        match = re.match(r"(\d+)", text)
        if match:
            return int(match.group(1))
        return text.count("★") or None
    return None


def skip_label_authorized(events: list[dict], index_path: str) -> bool:
    """L5: True when the most recent ``skip-child-gate`` labeling was by an allowlisted actor or a Verifier.

    Fail closed: no labeling event, an unreadable index, or any other labeler means the label is not honoured.
    """
    actor = latest_labeler_actor(events, SKIP_LABEL)
    if actor is None:
        return False
    login = actor.get("login")
    if allowlisted(login, actor.get("type"), actor.get("id")):
        return True
    return verifier_status(index_path, login) == "yes"


def verifier_status(index_path: str, actor: str | None) -> str:
    """``yes``, ``no`` or a ``deny-*`` reason, for *actor* against the built index.

    A missing, unparseable or empty index is a denial (H1, M1). There is no bootstrap grant (M1): an index that
    names no authorised Verifier denies every actor, and only the allowlist (allowlisted) can authorize one.
    Handles match case-insensitively (L9).
    """
    if not os.path.isfile(index_path):
        return "deny-missing-index"
    try:
        with open(index_path, "r", encoding="utf-8") as handle:
            index = json.load(handle)
    except Exception:  # noqa: BLE001 - any read or parse failure is unparseable
        return "deny-unparseable-index"
    buckets = index.get("buckets") if isinstance(index, dict) else None
    if not isinstance(buckets, dict):
        return "deny-unparseable-index"
    for entries in buckets.values():
        if not isinstance(entries, list) or not all(isinstance(entry, dict) for entry in entries):
            return "deny-unparseable-index"
    if not any(entries for entries in buckets.values()):
        return "deny-empty-index"
    wanted = actor.lower() if isinstance(actor, str) and actor else ""
    for entries in buckets.values():
        for entry in entries:
            level = star_level(entry.get("level"))
            contributor = entry.get("contributor")
            if level is not None and level >= 4 and wanted and isinstance(contributor, str):
                if contributor.lower() == wanted:
                    return "yes"
    return "no"


def changed_fields(previous: dict | None, payload: dict) -> list[str]:
    """Names of the hashed payload fields that differ from *previous*, for the reviewer note."""
    if previous is None:
        return ["payload (no readable previous payload)"]
    names: list[str] = []
    for key in sorted((set(previous) | set(payload)) - {"payloadSha256"}):
        if key == "candidates":
            before = {row["id"]: row for row in previous.get("candidates", [])}
            after = {row["id"]: row for row in payload.get("candidates", [])}
            added = sorted(set(after) - set(before))
            removed = sorted(set(before) - set(after))
            changed = sorted(rid for rid in set(after) & set(before) if before[rid] != after[rid])
            if added or removed or changed:
                names.append(
                    "candidates (added: "
                    f"{', '.join(f'cand:{r}' for r in added) or 'none'}; changed: "
                    f"{', '.join(f'cand:{r}' for r in changed) or 'none'}; removed: "
                    f"{', '.join(f'cand:{r}' for r in removed) or 'none'})"
                )
        elif previous.get(key) != payload.get(key):
            names.append(key)
    return names


def reset_note(approved: str, new_version: str, changed: list[str], added_rows: list[str], payload_hash: str) -> str:
    """The one reviewer note an approval reset posts. It names the versions, the changed fields and the marker."""
    fields = ", ".join(f"`{name}`" for name in changed) or "none"
    added = ", ".join(f"`cand:{rid}`" for rid in added_rows) or "none"
    return (
        f"Approval reset: `{approved}` was approved, but the umbrella payload changed "
        f"(upstream is now `{new_version}`). Changed fields: {fields}. "
        f"Added rows: {added}.\n\n"
        "`upstream:approved` was removed and `upstream:needs-info` applied. "
        "Re-apply `upstream:approved` after review.\n\n"
        f"{reset_marker(payload_hash)}"
    )
