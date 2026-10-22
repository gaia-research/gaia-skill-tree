"""scripts.upstream_watcher.records — record comments for umbrella batch rows (#2131, M5, H2, D4, I3).

GitHub caps an issue body at 65,536 characters. A suite that accumulates enough batch rows
would overflow it, and the umbrella would wedge. Such a suite is written in *records mode*:

- the umbrella body keeps a compact index (``id``, ``status``, ``child``) in its payload,
  which is all the approval gates and the unresolved-row count read, plus the row digest;
- the full rows live in numbered ``gaia-upstream-record`` comments on the umbrella, at most
  ROWS_PER_CHUNK rows per comment, in sorted id order.

Generations (D4). Every record comment carries its *generation*: the SHA-256 of the full ordered row set,
which is also the digest the body commits to (``candidateRecords.sha256``). A change to the rows is a new
generation. Its chunks are written as NEW comments, the body is then switched to name the new generation,
and only then is the old generation deleted (best effort). A chunk is never edited in place, so a crash at
any step leaves the body naming a complete generation whose comments all still exist. The reader reads
exactly the generation the body names and ignores every other generation.

Trust (H2, I3). A record comment counts only when the watcher identity (WATCHER_LOGIN) with the Bot user
type authored it. A record-looking comment from anyone else is ignored and counted in a ``::notice::``, so
no outside comment can wedge a run.

Integrity. Each record comment's header carries the SHA-256 of everything below the header line, so an
edited trusted comment fails closed. A reader checks, for the named generation only:

- every chunk 1..N is present exactly once (two trusted copies of one chunk fail closed, even when identical;
  the same comment listed twice by pagination is one copy);
- each trusted chunk's text matches its own header digest;
- the concatenated rows match the generation digest.

Any failure raises RecordError, which is a GhError, so the run fails closed for that suite with zero writes.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass, field

from scripts.upstream_watcher.live import GhError

ROWS_PER_CHUNK = 50
COMMENT_LIMIT = 65_536  # GitHub's limit for one comment, as for the body
# H2, I3: the only author whose record comments are trusted. It is the login the watcher's workflow
# token writes as (github-actions[bot]), and the account must be typed as a Bot. Change it here if the
# write identity changes.
WATCHER_LOGIN = "github-actions[bot]"
WATCHER_USER_TYPE = "Bot"
PAYLOAD_RE = re.compile(r"<!-- gaia-upstream-payload\n(.*?)\n-->", re.DOTALL)
HEADER_RE = re.compile(
    r"<!-- gaia-upstream-record gen=([0-9a-f]{64}) chunk=(\d+) of=(\d+) sha256=([0-9a-f]{64}) -->"
)
ROWS_RE = re.compile(r"<!-- gaia-upstream-rows\n(.*?)\n-->", re.DOTALL)


class RecordError(GhError):
    """A record comment is missing, duplicated, tampered with or unreadable. The caller fails closed."""


@dataclass
class GenerationPlan:
    """The record writes for one umbrella, in the order they must run.

    ``prewrites`` run BEFORE the body switch: creates of the target generation's missing chunks, and
    nothing else. ``cleanup`` runs AFTER the body switch: deletes of every comment of another generation.
    ``generation`` is the target digest, or None for an inline umbrella (which has no record comments).
    """

    generation: str | None
    prewrites: list[tuple[str, int | None, str]] = field(default_factory=list)
    cleanup: list[tuple[str, int, str]] = field(default_factory=list)


def canonical(rows: list[dict]) -> str:
    return json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def rows_digest(rows: list[dict]) -> str:
    """SHA-256 over the canonical JSON of an ordered row list. This is the generation id."""
    return hashlib.sha256(canonical(rows).encode("utf-8")).hexdigest()


def _text_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def chunk_rows(rows: list[dict], size: int = ROWS_PER_CHUNK) -> list[list[dict]]:
    """Split *rows* into consecutive chunks. Boundaries depend only on the row order and count."""
    return [rows[start:start + size] for start in range(0, len(rows), size)]


def _chunk_rest(generation: str, index: int, total: int, chunk: list[dict]) -> str:
    """Everything in a record comment below its header line. The header digest covers this text."""
    table = "\n".join(
        f"| `cand:{row['id']}` | `{row['suggestedId']}` | `{row['status']}` | "
        f"{('#' + str(row['child'])) if row.get('child') else '—'} |"
        for row in chunk
    )
    return (
        f"### Batch record {index} of {total}\n\n"
        f"Generation `{generation}`. Full batch rows for this umbrella, kept losslessly here because they do not "
        "fit in the body. Written by the Gaia upstream watcher; never edit by hand. Any edit makes the record fail "
        "closed, and the umbrella body commits to these rows by digest.\n\n"
        "| Row | Suggested ID | Status | Child |\n"
        "|---|---|---|---|\n"
        f"{table}\n\n"
        "<!-- gaia-upstream-rows\n"
        f"{json.dumps(chunk, indent=2, sort_keys=True, ensure_ascii=False)}\n"
        "-->"
    )


def render_chunk(generation: str, index: int, total: int, chunk: list[dict]) -> str:
    rest = _chunk_rest(generation, index, total, chunk)
    header = (
        f"<!-- gaia-upstream-record gen={generation} chunk={index} of={total} "
        f"sha256={_text_digest(rest)} -->"
    )
    text = f"{header}\n{rest}"
    if len(text) > COMMENT_LIMIT:
        raise RecordError(
            f"record chunk {index} of {total} is {len(text)} characters, over the {COMMENT_LIMIT}-character "
            "limit on each record comment"
        )
    return text


def is_watcher_comment(comment: dict) -> bool:
    """I3: the watcher's own login AND the Bot user type. A user with the same login string is not trusted."""
    user = comment.get("user")
    return (
        isinstance(user, dict)
        and user.get("login") == WATCHER_LOGIN
        and user.get("type") == WATCHER_USER_TYPE
    )


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


def parse_header(body: str | None) -> tuple[str, int, int, str] | None:
    """(generation, index, of, digest) from a record header, or None. Does not check the digest against the text."""
    match = HEADER_RE.match(body or "")
    if not match:
        return None
    return match.group(1), int(match.group(2)), int(match.group(3)), match.group(4)


def parse_chunk(body: str | None) -> tuple[str, int, int, str, list[dict]] | None:
    """Return (generation, index, total, text digest, rows) for a record comment, or None for an ordinary comment.

    A comment that opens with a record header must be intact: its text must match the header digest,
    and its rows block must parse. Anything else raises RecordError.
    """
    match = HEADER_RE.match(body or "")
    if not match:
        return None
    rest = body[match.end():]
    if not rest.startswith("\n"):
        raise RecordError(f"record chunk {match.group(2)} has a malformed header")
    rest = rest[1:]
    generation, index, total, digest = match.group(1), int(match.group(2)), int(match.group(3)), match.group(4)
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
    return generation, index, total, digest, rows


def read_rows(comments: list[dict], meta: dict) -> list[dict]:
    """Rebuild the ordered full rows of the generation the body names. Fails closed.

    *meta* is the body's ``candidateRecords``: ``chunks`` (N), ``rows`` and ``sha256`` (the generation).
    Comments of any other generation, or of another chunk count, are not read at all.
    """
    try:
        total = int(meta["chunks"])
        expected_rows = int(meta["rows"])
        generation = str(meta["sha256"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RecordError(f"candidateRecords is malformed: {exc}") from exc
    found: dict[int, dict[object, list[dict]]] = {}
    for comment in trusted_comments(comments):
        header = parse_header(comment.get("body"))
        if header is None:
            continue
        gen, _index, of, _digest = header
        if gen != generation or of != total:
            continue
        parsed = parse_chunk(comment.get("body"))
        if parsed is None:  # unreachable: the header matched
            continue
        _gen, index, _of, _digest, rows = parsed
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
    if len(ordered) != expected_rows or rows_digest(ordered) != generation:
        raise RecordError("record rows do not match the umbrella digest")
    return ordered


def plan_generation(comments: list[dict], rows: list[dict] | None) -> GenerationPlan:
    """Plan the record writes that move an umbrella to *rows* (D4). Performs no writes.

    With *rows* None (an inline umbrella) every record comment is for cleanup. Otherwise the target
    generation is the digest of *rows*. Each target chunk that has no trusted comment is a prewrite
    create. A target chunk that already has its one comment is verified (a tampered one fails closed)
    and kept. Every trusted record comment of another generation, or of another chunk count, is cleanup,
    which runs only after the body names the target. Two trusted copies of a target chunk fail closed.
    """
    owned: list[tuple[dict, str, int, int]] = []
    for comment in trusted_comments(comments):
        header = parse_header(comment.get("body"))
        if header is not None:
            owned.append((comment, header[0], header[1], header[2]))
    if rows is None:
        return GenerationPlan(
            generation=None,
            cleanup=[("delete", comment["id"], "") for comment, _gen, _index, _of in owned],
        )
    target = rows_digest(rows)
    chunks = chunk_rows(rows)
    total = len(chunks)
    prewrites: list[tuple[str, int | None, str]] = []
    for index, chunk in enumerate(chunks, start=1):
        current = [comment for comment, gen, i, of in owned if gen == target and i == index and of == total]
        for comment in current:
            parse_chunk(comment.get("body"))  # a tampered target chunk fails closed here
        if len(current) > 1:
            raise RecordError(
                f"record chunk {index} of {total} has {len(current)} trusted copies; fail closed until the "
                "extra comment is deleted by a maintainer"
            )
        if not current:
            prewrites.append(("create", None, render_chunk(target, index, total, chunk)))
    cleanup = [
        ("delete", comment["id"], "")
        for comment, gen, _index, of in owned
        if gen != target or of != total
    ]
    return GenerationPlan(generation=target, prewrites=prewrites, cleanup=cleanup)
