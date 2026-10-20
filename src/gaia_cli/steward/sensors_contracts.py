"""Deterministic contract sensors: schema validity, timeline causality, frontend HTML.

Each sensor is read-only, inventories through ``gaia_cli.steward.primitives``,
emits only ``drift`` observations (one per subject), and reports findings in a
stable order. Coverage is exhaustive over its domain, so a completed scan may
resolve debt that it no longer re-observes.

Skip accounting: a subject that cannot be interpreted at all (undecodable text,
unparseable frontmatter) is skipped and counted, never silently treated as
healthy. ``scan_with_stats`` returns those counts; ``scan`` returns only the
observations and is what the controller calls.
"""

from __future__ import annotations

import datetime as _dt
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import unquote, urlsplit

import yaml
from jsonschema import Draft7Validator
from jsonschema.exceptions import SchemaError
from jsonschema.validators import validator_for

from gaia_cli.steward.models import Observation, Subject
from gaia_cli.steward.primitives import (
    SensorUnavailable,
    finding_payload,
    git_root,
    read_text_bounded,
    tracked_files,
)

_SUBJECT_LIMIT_BYTES = 2 * 1024 * 1024
_UTC = _dt.timezone.utc

# Keys whose values are data, not schema references. A "$ref" inside them is
# an example or a literal default, so it is not followed.
_NON_SCHEMA_KEYS = frozenset({"enum", "const", "default", "examples"})

# Generated Class S directories and Class-S-adjacent trees that are not
# hand-authored contract surfaces (CLAUDE.md, "Generated Artifacts").
_FRONTEND_EXCLUDES = (
    "docs/u",
    "docs/api",
    "docs/og",
    "docs/graph",
    "docs/okf",
    "docs/experiments",
)


def _read_subject(path: Path) -> str | None:
    """Read one tracked subject as UTF-8 text.

    Oversize input is a truncated observation and makes the sensor unavailable.
    Undecodable bytes are a malformed subject and return ``None`` so the caller
    can report it as a finding or a counted skip, never a whole-sensor crash.
    """

    try:
        size = path.stat().st_size
    except OSError as exc:
        raise SensorUnavailable(f"cannot stat {path.name}: {exc}") from exc
    if size > _SUBJECT_LIMIT_BYTES:
        raise SensorUnavailable(f"{path.name} exceeds the {_SUBJECT_LIMIT_BYTES}-byte read limit")
    try:
        path.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        return None
    except OSError as exc:
        raise SensorUnavailable(f"cannot read {path.name}: {exc}") from exc
    return read_text_bounded(path, limit=_SUBJECT_LIMIT_BYTES)


def _sort_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(findings, key=lambda item: json.dumps(item, sort_keys=True))


# ---------------------------------------------------------------------------
# 1. Schema validity (routine 8)
# ---------------------------------------------------------------------------


def _iter_refs(node: Any) -> Iterator[str]:
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str):
                yield value
            if key in _NON_SCHEMA_KEYS:
                continue
            yield from _iter_refs(value)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_refs(item)


def _pointer_resolves(document: Any, fragment: str) -> bool:
    """Return whether a JSON-pointer fragment resolves inside ``document``.

    Non-pointer fragments (plain-name anchors such as ``#foo``) are not
    verified here; the caller treats them as out of scope, not as broken.
    """

    pointer = unquote(fragment)
    if pointer == "":
        return True
    if not pointer.startswith("/"):
        return True
    node = document
    for raw in pointer[1:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(node, dict) and token in node:
            node = node[token]
        elif isinstance(node, list) and token.isdigit() and int(token) < len(node):
            node = node[int(token)]
        else:
            return False
    return True


class SchemaValiditySensor:
    """Validate tracked top-level registry JSON Schemas."""

    id = "schema-validity"
    routine_ids = (8,)
    resolution_scope = "exhaustive"
    _prefix = "registry/schema/"

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        observations, _stats = self.scan_with_stats(repo_root, observed_at)
        return observations

    def scan_with_stats(
        self, repo_root: Path, observed_at: str
    ) -> tuple[list[Observation], dict[str, int]]:
        root = git_root(repo_root)
        inventory = [
            path
            for path in tracked_files(root, [self._prefix], suffixes=(".json",))
            if "/" not in path[len(self._prefix):]
        ]
        if not inventory:
            raise SensorUnavailable("required schema inventory is empty: registry/schema/*.json")

        documents: dict[str, Any] = {}
        findings: dict[str, list[dict[str, Any]]] = {path: [] for path in inventory}
        for relative in inventory:
            text = _read_subject(root / relative)
            if text is None:
                findings[relative].append(
                    {"rule": "invalid-json", "detail": "file is not valid UTF-8"}
                )
                continue
            try:
                documents[relative] = json.loads(text)
            except json.JSONDecodeError as exc:
                findings[relative].append(
                    {
                        "rule": "invalid-json",
                        "detail": f"{exc.msg} at line {exc.lineno} column {exc.colno}",
                    }
                )

        for relative, document in documents.items():
            findings[relative].extend(self._check_document(root, relative, document))
        findings_by_id = self._duplicate_ids(documents)
        for relative, items in findings_by_id.items():
            findings[relative].extend(items)

        observations: list[Observation] = []
        for relative in inventory:
            found = _sort_findings(findings[relative])
            if not found:
                continue
            observations.append(
                Observation(
                    kind="schema_contract_drift",
                    subject=Subject(type="schema", id=relative),
                    observed_at=observed_at,
                    source=self.id,
                    status="drift",
                    current_state={"findingCount": 0},
                    observed_state=finding_payload(found),
                    confidence=1.0,
                    provenance={
                        "sensor": self.id,
                        "rules": ["invalid-json", "invalid-schema", "unresolved-local-ref", "duplicate-id"],
                        "inventoryCount": len(inventory),
                    },
                )
            )
        stats = {"inventory": len(inventory), "documentsParsed": len(documents)}
        return observations, stats

    @staticmethod
    def _check_document(root: Path, relative: str, document: Any) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        validator_cls = (
            validator_for(document, default=Draft7Validator)
            if isinstance(document, dict)
            else Draft7Validator
        )
        try:
            validator_cls.check_schema(document)
        except SchemaError as exc:
            found.append({"rule": "invalid-schema", "detail": exc.message.splitlines()[0][:240]})

        schema_dir = (root / relative).parent
        for ref in _iter_refs(document):
            scheme = urlsplit(ref).scheme
            if scheme:
                # Remote references are never fetched: Steward does not use the network.
                continue
            base, _, fragment = ref.partition("#")
            if not base:
                if fragment and not _pointer_resolves(document, fragment):
                    found.append(
                        {
                            "rule": "unresolved-local-ref",
                            "detail": f"$ref {ref!r} does not resolve inside the document",
                        }
                    )
                continue
            target = (schema_dir / base).resolve()
            inside = target == root or root in target.parents
            if not inside or not target.is_file():
                found.append(
                    {
                        "rule": "unresolved-local-ref",
                        "detail": f"$ref {ref!r} names no file {base!r} beside this schema",
                    }
                )
        return found

    @staticmethod
    def _duplicate_ids(documents: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
        declared: dict[str, list[str]] = {}
        for relative, document in documents.items():
            if isinstance(document, dict) and isinstance(document.get("$id"), str):
                identity = document["$id"].rstrip("#")
                declared.setdefault(identity, []).append(relative)
        result: dict[str, list[dict[str, Any]]] = {}
        for identity, owners in declared.items():
            if len(owners) < 2:
                continue
            for owner in owners:
                others = [item for item in owners if item != owner]
                result.setdefault(owner, []).append(
                    {
                        "rule": "duplicate-id",
                        "detail": f"$id {identity!r} is also declared by {', '.join(others)}",
                    }
                )
        return result


# ---------------------------------------------------------------------------
# 2. Timeline causality (routine 10)
# ---------------------------------------------------------------------------

_FENCE = "---"


def _frontmatter(text: str) -> dict[str, Any] | None:
    """Return the YAML mapping between the first two ``---`` fences, or None."""

    lines = text.split("\n")
    if not lines or lines[0].strip() != _FENCE:
        return None
    for index in range(1, len(lines)):
        if lines[index].strip() == _FENCE:
            try:
                loaded = yaml.safe_load("\n".join(lines[1:index]))
            except yaml.YAMLError:
                return None
            return loaded if isinstance(loaded, dict) else None
    return None


def _parse_instant(value: Any) -> tuple[_dt.datetime, bool] | None:
    """Return ``(UTC datetime, day_precision)`` for a timestamp, or None.

    YAML may hand back a ``date`` (unquoted ``2026-06-10``), a naive or aware
    ``datetime``, or a string. Naive values are UTC, matching the CLI's Z form.
    A date without a time is day precision: it is compared by calendar day.
    """

    day_precision = False
    if isinstance(value, _dt.datetime):
        parsed = value
    elif isinstance(value, _dt.date):
        parsed = _dt.datetime(value.year, value.month, value.day)
        day_precision = True
    elif isinstance(value, str):
        text = value.strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            try:
                parsed = _dt.datetime.combine(_dt.date.fromisoformat(text), _dt.time())
            except ValueError:
                return None
            day_precision = True
        else:
            normalized = text[:-1] + "+00:00" if text[-1:] in ("Z", "z") else text
            try:
                parsed = _dt.datetime.fromisoformat(normalized)
            except ValueError:
                return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_UTC)
    return parsed.astimezone(_UTC), day_precision


def _compare(
    left: tuple[_dt.datetime, bool], right: tuple[_dt.datetime, bool]
) -> int:
    """Compare two instants; day precision on either side compares calendar days."""

    if left[1] or right[1]:
        left_key, right_key = left[0].date(), right[0].date()
    else:
        left_key, right_key = left[0], right[0]
    return (left_key > right_key) - (left_key < right_key)


def _describe(value: Any) -> str:
    """Render a timestamp for a finding detail, bounded and unquoted."""

    if isinstance(value, str):
        return value[:64]
    if hasattr(value, "isoformat"):
        return value.isoformat()[:64]
    return repr(value)[:64]


class TimelineCausalitySensor:
    """Check named-skill timeline timestamps for parseability and ordering."""

    id = "timeline-causality"
    routine_ids = (10,)
    resolution_scope = "exhaustive"
    _prefix = "registry/named/"

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        observations, _stats = self.scan_with_stats(repo_root, observed_at)
        return observations

    def scan_with_stats(
        self, repo_root: Path, observed_at: str
    ) -> tuple[list[Observation], dict[str, int]]:
        root = git_root(repo_root)
        now = _parse_instant(observed_at)
        if now is None:
            raise SensorUnavailable("observed_at is not a parseable timestamp")
        inventory = tracked_files(root, [self._prefix], suffixes=(".md",))

        stats = {
            "inventory": len(inventory),
            "skippedUndecodable": 0,
            "skippedUnparseableFrontmatter": 0,
            "skippedUnsupportedTimeline": 0,
            "skillsWithTimeline": 0,
            "events": 0,
        }
        pending: list[tuple[str, str, list[dict[str, Any]], int]] = []
        for relative in inventory:
            text = _read_subject(root / relative)
            if text is None:
                stats["skippedUndecodable"] += 1
                continue
            frontmatter = _frontmatter(text)
            if frontmatter is None:
                stats["skippedUnparseableFrontmatter"] += 1
                continue
            events = frontmatter.get("timeline")
            if events is None:
                continue
            if not isinstance(events, list):
                stats["skippedUnsupportedTimeline"] += 1
                continue
            identity = frontmatter.get("id")
            subject_id = identity.strip() if isinstance(identity, str) and identity.strip() else relative
            pending.append((relative, subject_id, events, len(events)))
            stats["skillsWithTimeline"] += 1
            stats["events"] += len(events)

        # One observation per subject: an id shared by two files falls back to
        # each file's path, so neither is silently merged into the other.
        counts: dict[str, int] = {}
        for _relative, subject_id, _events, _count in pending:
            counts[subject_id] = counts.get(subject_id, 0) + 1

        observations: list[Observation] = []
        for relative, subject_id, events, count in pending:
            if counts[subject_id] > 1:
                subject_id = relative
            found = _sort_findings(self._check_events(events, now))
            if not found:
                continue
            observed_state = finding_payload(found)
            observed_state["eventCount"] = count
            observations.append(
                Observation(
                    kind="timeline_causality_drift",
                    subject=Subject(type="named-skill", id=subject_id),
                    observed_at=observed_at,
                    source=self.id,
                    status="drift",
                    current_state={"findingCount": 0},
                    observed_state=observed_state,
                    confidence=1.0,
                    provenance={
                        "sensor": self.id,
                        "path": relative,
                        "rules": ["unparseable-timestamp", "out-of-order", "future-timestamp"],
                        "inventoryCount": len(inventory),
                    },
                )
            )
        return observations, stats

    @staticmethod
    def _check_events(events: list[Any], now: tuple[_dt.datetime, bool]) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        previous: tuple[int, tuple[_dt.datetime, bool], Any] | None = None
        for index, event in enumerate(events):
            if not isinstance(event, dict):
                found.append(
                    {"rule": "unparseable-timestamp", "detail": f"event {index} is not a mapping"}
                )
                continue
            raw = event.get("timestamp")
            instant = _parse_instant(raw)
            if instant is None:
                found.append(
                    {
                        "rule": "unparseable-timestamp",
                        "detail": f"event {index} has no parseable timestamp: {_describe(raw)!r}",
                    }
                )
                continue
            if _compare(instant, now) > 0:
                found.append(
                    {
                        "rule": "future-timestamp",
                        "detail": f"event {index} at {_describe(raw)} is after observed_at",
                    }
                )
            if previous is not None and _compare(instant, previous[1]) < 0:
                found.append(
                    {
                        "rule": "out-of-order",
                        "detail": (
                            f"event {index} at {_describe(raw)} precedes event {previous[0]} "
                            f"at {_describe(previous[2])}"
                        ),
                    }
                )
            previous = (index, instant, raw)
        return found


# ---------------------------------------------------------------------------
# 3. Frontend contract (routine 15)
# ---------------------------------------------------------------------------


class _ContractParser(HTMLParser):
    """Record only the contract facts the frontend sensor needs."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.html_line: int | None = None
        self.head_line: int | None = None
        self.html_has_lang = False
        self.has_viewport = False
        self.title_seen = False
        self.title_text = ""
        self._in_title = False
        self.images_missing_alt: list[int] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        line = self.getpos()[0]
        present = {}
        for name, value in attrs:
            # HTML keeps the first occurrence of a duplicated attribute.
            present.setdefault(name.lower(), value)
        if tag == "html" and self.html_line is None:
            self.html_line = line
            self.html_has_lang = "lang" in present
        elif tag == "head" and self.head_line is None:
            self.head_line = line
        elif tag == "meta":
            if (present.get("name") or "").strip().lower() == "viewport":
                self.has_viewport = True
        elif tag == "title" and not self.title_seen:
            self.title_seen = True
            self._in_title = True
        elif tag == "img" and "alt" not in present:
            self.images_missing_alt.append(line)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_text += data


class FrontendContractSensor:
    """Check hand-authored HTML pages for the baseline document contract."""

    id = "frontend-contract"
    routine_ids = (15,)
    resolution_scope = "exhaustive"

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        observations, _stats = self.scan_with_stats(repo_root, observed_at)
        return observations

    def scan_with_stats(
        self, repo_root: Path, observed_at: str
    ) -> tuple[list[Observation], dict[str, int]]:
        root = git_root(repo_root)
        inventory = tracked_files(
            root,
            ["docs/"],
            suffixes=(".html",),
            exclude=_FRONTEND_EXCLUDES,
        )
        stats = {"inventory": len(inventory), "skippedFragment": 0, "skippedUndecodable": 0}
        observations: list[Observation] = []
        for relative in inventory:
            text = _read_subject(root / relative)
            if text is None:
                stats["skippedUndecodable"] += 1
                continue
            parser = _ContractParser()
            try:
                parser.feed(text)
                parser.close()
            except Exception:  # HTMLParser is lenient; anything escaping it is a malformed subject.
                stats["skippedUndecodable"] += 1
                continue
            if parser.html_line is None:
                # A partial or fragment has no document element; it is a
                # component of another page, not a page with a contract.
                stats["skippedFragment"] += 1
                continue
            found = self._findings(parser)
            if not found:
                continue
            observations.append(
                Observation(
                    kind="frontend_contract_drift",
                    subject=Subject(type="html-page", id=relative),
                    observed_at=observed_at,
                    source=self.id,
                    status="drift",
                    current_state={"findingCount": 0},
                    observed_state=finding_payload(found),
                    confidence=1.0,
                    provenance={
                        "sensor": self.id,
                        "rules": ["missing-lang", "missing-viewport", "missing-title", "img-missing-alt"],
                        "excludedDirectories": list(_FRONTEND_EXCLUDES),
                        "inventoryCount": len(inventory),
                    },
                )
            )
        return observations, stats

    @staticmethod
    def _findings(parser: _ContractParser) -> list[dict[str, Any]]:
        head_or_html = parser.head_line if parser.head_line is not None else parser.html_line
        found: list[dict[str, Any]] = []
        if not parser.html_has_lang:
            found.append({"rule": "missing-lang", "line": parser.html_line})
        if not parser.has_viewport:
            found.append({"rule": "missing-viewport", "line": head_or_html})
        if not parser.title_seen or not parser.title_text.strip():
            found.append({"rule": "missing-title", "line": head_or_html})
        for line in parser.images_missing_alt:
            found.append({"rule": "img-missing-alt", "line": line})
        return sorted(found, key=lambda item: (item["line"], item["rule"]))
