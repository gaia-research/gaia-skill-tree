"""scripts.upstream_watcher.records — record comments for umbrella batch rows (#2131, M5).

GitHub caps an issue body at 65,536 characters. A suite that accumulates enough batch rows
would overflow it, and the umbrella would wedge. Such a suite is written in *records mode*:

- the umbrella body keeps a compact index (``id``, ``status``, ``child``) in its payload,
  which is all the approval gates and the unresolved-row count read, plus the row digest;
- the full rows live in numbered ``gaia-upstream-record`` comments on the umbrella, at most
  ROWS_PER_CHUNK rows per comment, in sorted id order.

Each record comment's header carries the SHA-256 of everything below the header line, so the
human table and the machine rows block are both covered. An edited comment therefore fails
closed. The body in turn commits to the ordered full rows through ``candidateRecords.sha256``.
A reader verifies every chunk's own digest, that every chunk 1..N is present exactly once, and
that the concatenated rows match the body digest. Anything else raises RecordError, which is a
GhError, so the run fails closed with zero writes.

Only comments whose ``of=`` equals the body's chunk count are part of the record. A comment
that is not a record (any human comment) is ignored.
"""

from __future__ import annotations

import hashlib
import json
import re

from scripts.upstream_watcher.live import GhError

ROWS_PER_CHUNK = 50
COMMENT_LIMIT = 65_536  # GitHub's limit for one comment, as for the body
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
    """Rebuild the ordered full rows of an umbrella from its record comments. Fails closed."""
    try:
        total = int(meta["chunks"])
        expected_rows = int(meta["rows"])
        expected_digest = str(meta["sha256"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RecordError(f"candidateRecords is malformed: {exc}") from exc
    found: dict[int, dict[str, list[dict]]] = {}
    for comment in comments:
        parsed = parse_chunk(comment.get("body"))
        if parsed is None:
            continue
        index, of, digest, rows = parsed
        if of != total:
            continue
        found.setdefault(index, {}).setdefault(digest, rows)
    ordered: list[dict] = []
    for index in range(1, total + 1):
        copies = found.get(index)
        if not copies:
            raise RecordError(f"record chunk {index} of {total} is missing")
        if len(copies) > 1:
            raise RecordError(f"record chunk {index} of {total} has conflicting copies")
        ordered.extend(next(iter(copies.values())))
    if len(ordered) != expected_rows or rows_digest(ordered) != expected_digest:
        raise RecordError("record rows do not match the umbrella digest")
    return ordered


def plan_writes(comments: list[dict], rows: list[dict]) -> list[tuple[str, int | None, str]]:
    """Return the record comment writes that bring *comments* in line with *rows*.

    Each write is ``(kind, comment_id, text)`` where kind is ``create`` (comment_id None) or
    ``edit``. A chunk whose existing comment already holds the same text is not rewritten, so an
    unchanged rerun writes nothing and a changed row rewrites only its own chunk.
    """
    chunks = chunk_rows(rows)
    total = len(chunks)
    existing: dict[int, list[tuple[int, str]]] = {}
    for comment in comments:
        parsed = parse_chunk(comment.get("body"))
        if parsed is None:
            continue
        index, of, digest, _rows = parsed
        if of == total:
            existing.setdefault(index, []).append((comment["id"], digest))
    writes: list[tuple[str, int | None, str]] = []
    for index, chunk in enumerate(chunks, start=1):
        matches = existing.get(index, [])
        if not matches:
            writes.append(("create", None, render_chunk(index, total, chunk)))
            continue
        wanted = _text_digest(_chunk_rest(index, total, chunk))
        for comment_id, digest in matches:
            if digest != wanted:
                writes.append(("edit", comment_id, render_chunk(index, total, chunk)))
    return writes
