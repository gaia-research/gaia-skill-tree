"""scripts.upstream_watcher.records — record comments for umbrella batch rows (#2131, M5, H2, M7).

GitHub caps an issue body at 65,536 characters. A suite that accumulates enough batch rows
would overflow it, and the umbrella would wedge. Such a suite is written in *records mode*:

- the umbrella body keeps a compact index (``id``, ``status``, ``child``) in its payload,
  which is all the approval gates and the unresolved-row count read, plus the row digest;
- the full rows live in numbered ``gaia-upstream-record`` comments on the umbrella, at most
  ROWS_PER_CHUNK rows per comment, in sorted id order.

Trust (H2). A record comment counts only when the watcher identity (WATCHER_LOGIN) authored it.
Any other user's record-looking comment is ignored and counted in a ``::notice::``. Anyone can
post a comment, so an untrusted header must never be able to wedge a run.

Integrity. Each record comment's header carries the SHA-256 of everything below the header line,
so an edited trusted comment fails closed. The umbrella body commits to the ordered full rows
through ``candidateRecords.sha256``. A reader checks, for the current chunk count only:

- every chunk 1..N is present exactly once (two trusted comments for one chunk fail closed,
  even when their text is identical; the same comment listed twice by pagination is one copy);
- each trusted chunk's text matches its own header digest;
- the concatenated rows match the body digest.

Any failure raises RecordError, which is a GhError, so the run fails closed for that suite with
zero writes to it. A trusted comment whose ``of=`` is not the current chunk count is a stale set.
It is never read (its ``of`` is checked before its digest), and the writer removes it (M7).

Churn (M7). A chunk-set change edits the existing chunk comments in place and creates only
trailing chunks that have no comment yet. Surplus chunks are deleted, so exactly the current
chunk set remains. Every chunk header carries ``of=N``, so a count change edits each chunk once.
Edits do not notify, and no unchanged row is rewritten at a stable count.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys

from scripts.upstream_watcher.live import GhError

ROWS_PER_CHUNK = 50
COMMENT_LIMIT = 65_536  # GitHub's limit for one comment, as for the body
# H2: the only author whose record comments are trusted. It is the login the watcher's workflow
# token writes as (github-actions[bot]). Change it here if the write identity changes.
WATCHER_LOGIN = "github-actions[bot]"
PAYLOAD_RE = re.compile(r"<!-- gaia-upstream-payload\n(.*?)\n-->", re.DOTALL)
HEADER_RE = re.compile(r"<!-- gaia-upstream-record chunk=(\d+) of=(\d+) sha256=([0-9a-f]{64}) -->")
ROWS_RE = re.compile(r"<!-- gaia-upstream-rows\n(.*?)\n-->", re.DOTALL)


class RecordError(GhError):
    """A record comment is missing, duplicated, tampered with or unreadable. The caller fails closed."""


def canonical(rows: list[dict]) -> str:
    return json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def rows_digest(rows: list[dict]) -> str:
    """SHA-256 over the canonical JSON of an ordered row list."""
    return hashlib.sha256(canonical(rows).encode("utf-8")).hexdigest()


def _text_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def chunk_rows(rows: list[dict], size: int = ROWS_PER_CHUNK) -> list[list[dict]]:
    """Split *rows* into consecutive chunks. Boundaries depend only on the row order and count,
    so a change to one row alters only the chunk that holds it."""
    return [rows[start:start + size] for start in range(0, len(rows), size)]


def _chunk_rest(index: int, total: int, chunk: list[dict]) -> str:
    """Everything in a record comment below its header line. The header digest covers this text."""
    table = "\n".join(
        f"| `cand:{row['id']}` | `{row['suggestedId']}` | `{row['status']}` | "
        f"{('#' + str(row['child'])) if row.get('child') else '—'} |"
        for row in chunk
    )
    return (
        f"### Batch record {index} of {total}\n\n"
        "Full batch rows for this umbrella, kept losslessly here because they do not fit in the body. "
        "Written by the Gaia upstream watcher; never edit by hand. Any edit makes the record fail closed, "
        "and the umbrella body commits to these rows by digest.\n\n"
        "| Row | Suggested ID | Status | Child |\n"
        "|---|---|---|---|\n"
        f"{table}\n\n"
        "<!-- gaia-upstream-rows\n"
        f"{json.dumps(chunk, indent=2, sort_keys=True, ensure_ascii=False)}\n"
        "-->"
    )


def render_chunk(index: int, total: int, chunk: list[dict]) -> str:
    rest = _chunk_rest(index, total, chunk)
    header = f"<!-- gaia-upstream-record chunk={index} of={total} sha256={_text_digest(rest)} -->"
    text = f"{header}\n{rest}"
    if len(text) > COMMENT_LIMIT:
        raise RecordError(
            f"record chunk {index} of {total} is {len(text)} characters, over the {COMMENT_LIMIT} comment limit"
        )
    return text


def is_watcher_comment(comment: dict) -> bool:
    user = comment.get("user")
    return isinstance(user, dict) and user.get("login") == WATCHER_LOGIN


def trusted_comments(comments: list[dict]) -> list[dict]:
    """The comments the watcher wrote. A record-looking comment from anyone else is ignored and counted (H2)."""
    trusted: list[dict] = []
    ignored = 0
    for comment in comments:
        if is_watcher_comment(comment):
            trusted.append(comment)
        elif HEADER_RE.match(comment.get("body") or ""):
            ignored += 1
    if ignored:
        print(
            f"::notice::ignored {ignored} record-looking comment(s) not authored by {WATCHER_LOGIN}",
            file=sys.stderr,
        )
    return trusted


def parse_header(body: str | None) -> tuple[int, int, str] | None:
    """(index, of, digest) from a record header, or None. Does not check the digest against the text."""
    match = HEADER_RE.match(body or "")
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)), match.group(3)


def parse_chunk(body: str | None) -> tuple[int, int, str, list[dict]] | None:
    """Return (index, total, text digest, rows) for a record comment, or None for an ordinary comment.

    A comment that opens with a record header must be intact: its text must match the header digest,
    and its rows block must parse. Anything else raises RecordError.
    """
    match = HEADER_RE.match(body or "")
    if not match:
        return None
    rest = body[match.end():]
    if not rest.startswith("\n"):
        raise RecordError(f"record chunk {match.group(1)} has a malformed header")
    rest = rest[1:]
    index, total, digest = int(match.group(1)), int(match.group(2)), match.group(3)
    if _text_digest(rest) != digest:
        raise RecordError(f"record chunk {index} of {total} does not match its digest (edited?)")
    block = ROWS_RE.search(rest)
    if not block:
        raise RecordError(f"record chunk {index} of {total} has no rows block")
    try:
        rows = json.loads(block.group(1))
    except ValueError as exc:
        raise RecordError(f"record chunk {index} of {total} rows do not parse: {exc}") from exc
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise RecordError(f"record chunk {index} of {total} rows are not a list of objects")
    return index, total, digest, rows


def read_rows(comments: list[dict], meta: dict) -> list[dict]:
    """Rebuild the ordered full rows of an umbrella from its trusted record comments. Fails closed.

    Order of checks for each trusted comment: its header first. A header whose ``of`` is not the
    current chunk count is a stale set and is skipped without its digest being read. A current chunk
    is then fully verified (RecordError on any mismatch).
    """
    try:
        total = int(meta["chunks"])
        expected_rows = int(meta["rows"])
        expected_digest = str(meta["sha256"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RecordError(f"candidateRecords is malformed: {exc}") from exc
    found: dict[int, dict[object, list[dict]]] = {}
    for comment in trusted_comments(comments):
        header = parse_header(comment.get("body"))
        if header is None:
            continue
        index, of, _digest = header
        if of != total:
            continue
        parsed = parse_chunk(comment.get("body"))
        if parsed is None:  # unreachable: the header matched
            continue
        index, _of, _digest, rows = parsed
        if not 1 <= index <= total:
            raise RecordError(f"record chunk {index} is outside the {total} chunk(s) of this umbrella")
        found.setdefault(index, {}).setdefault(comment.get("id"), rows)
    ordered: list[dict] = []
    for index in range(1, total + 1):
        copies = found.get(index)
        if not copies:
            raise RecordError(f"record chunk {index} of {total} is missing")
        if len(copies) > 1:
            raise RecordError(
                f"record chunk {index} of {total} has {len(copies)} trusted copies; fail closed until the "
                "extra comment is deleted by a maintainer"
            )
        ordered.extend(next(iter(copies.values())))
    if len(ordered) != expected_rows or rows_digest(ordered) != expected_digest:
        raise RecordError("record rows do not match the umbrella digest")
    return ordered


def plan_writes(comments: list[dict], rows: list[dict]) -> list[tuple[str, int | None, str]]:
    """Return the record comment writes that leave exactly the current chunk set of *rows* on the umbrella.

    Each write is ``(kind, comment_id, text)``. Kinds: ``create`` (comment_id None), ``edit`` (a chunk
    rewritten in place: a stale comment of an older chunk set is reused for the same chunk index, so no
    comment is re-posted) and ``delete`` (a surplus comment, with empty text). Edits and creates come
    first and deletes last. A chunk whose comment already holds the same text is not written, so an
    unchanged rerun writes nothing.

    Trusted current chunks are verified first (RecordError on tamper or on a duplicate copy).
    """
    chunks = chunk_rows(rows)
    total = len(chunks)
    owned: list[tuple[dict, int, int]] = []
    for comment in trusted_comments(comments):
        header = parse_header(comment.get("body"))
        if header is not None:
            owned.append((comment, header[0], header[1]))
    kept: set[object] = set()
    writes: list[tuple[str, int | None, str]] = []
    for index, chunk in enumerate(chunks, start=1):
        wanted_text = render_chunk(index, total, chunk)
        wanted_digest = _text_digest(_chunk_rest(index, total, chunk))
        current = [comment for comment, i, of in owned if i == index and of == total]
        for comment in current:
            parse_chunk(comment.get("body"))  # a tampered current chunk fails closed here
        if len(current) > 1:
            raise RecordError(
                f"record chunk {index} of {total} has {len(current)} trusted copies; fail closed until the "
                "extra comment is deleted by a maintainer"
            )
        if current:
            comment = current[0]
            kept.add(comment["id"])
            if parse_header(comment.get("body"))[2] != wanted_digest:
                writes.append(("edit", comment["id"], wanted_text))
            continue
        stale = [comment for comment, i, of in owned if i == index and of != total and comment["id"] not in kept]
        if stale:
            kept.add(stale[0]["id"])
            writes.append(("edit", stale[0]["id"], wanted_text))
        else:
            writes.append(("create", None, wanted_text))
    for comment, index, of in owned:
        if comment["id"] in kept:
            continue
        if of == total:
            raise RecordError(f"record chunk {index} of {total} is outside the {total} chunk(s) of this umbrella")
        writes.append(("delete", comment["id"], ""))
    return writes
