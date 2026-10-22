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

Verifier. ``verifier_status`` is the labeler check the workflows run against the freshly built index.
"""

from __future__ import annotations

import hashlib
import json
import os
import re

from scripts.upstream_watcher import records

# D7: the payload ends at the first newline + '-->'. Every writer emits the terminator on its own line,
# and JSON never contains a raw newline, so '-->' inside a string cannot end the block early.
PAYLOAD_RE = re.compile(r"<!-- gaia-upstream-payload\s+(.*?)\n-->", re.DOTALL)
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
    match = PAYLOAD_RE.search(body or "")
    if not match:
        raise PayloadError("no gaia-upstream-payload block was found in the umbrella body")
    try:
        data = json.loads(match.group(1))
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


def latest_labeler(events: list[dict], label: str = "upstream:approved") -> str | None:
    """Login of the actor behind the most recent ``labeled`` event for *label*, or None (fail closed)."""
    labeled = [
        event for event in events
        if event.get("event") == "labeled" and (event.get("label") or {}).get("name") == label
    ]
    if not labeled:
        return None
    newest = max(labeled, key=lambda event: int(event.get("id") or 0))
    login = (newest.get("actor") or {}).get("login")
    return login or None


def verifier_status(index_path: str, actor: str | None) -> str:
    """``yes``, ``bootstrap``, ``no`` or a ``deny-*`` reason, for *actor* against the built index.

    A missing, unparseable or empty index is a denial (H1, M1). Bootstrap (zero 4-star Verifiers) is
    granted only for a parseable, non-empty index that holds no Verifier at all.
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
    has_any_verifier = False
    for entries in buckets.values():
        for entry in entries:
            level = entry.get("level", "")
            if isinstance(level, str) and level[:1].isdigit() and int(level[0]) >= 4:
                has_any_verifier = True
                if actor and entry.get("contributor") == actor:
                    return "yes"
    return "no" if has_any_verifier else "bootstrap"


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
