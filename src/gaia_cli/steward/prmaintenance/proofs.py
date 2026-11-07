"""Local, deterministic proofs about a PR head, read from git objects only (no network).

The census collector fetches each PR head into the local object store. Everything here reads those
objects with ``git ls-tree`` / ``git cat-file``. A missing object is ``unknown``, never ``pass``.
The content-engine proofs regenerate a report from its own canonical JSON using the templates of the
*base* commit and compare the result to what the PR committed, so a PR can neither smuggle in a template
change nor drop a historical report from the shared indexes.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import selectors
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

PASS, FAIL, UNKNOWN = "pass", "fail", "unknown"
STAMP = re.compile(r"\?v=[0-9]+\.[0-9]+\.[0-9]+")
GAIAVERSION = re.compile(r'GAIA_VERSION = "[0-9.]+"')
LABEL = re.compile(r"^[0-9]{4}-[0-9]{2}$")


@dataclass(frozen=True)
class Proof:
    name: str
    state: str
    detail: str


SAFE_GIT_ENV_EXCLUDE = frozenset({
    "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_REPLACE_REF_BASE",
    "GIT_GRAFT_FILE", "GIT_COMMON_DIR",
})


def safeGitEnv(env: Mapping[str, str] | None = None) -> dict[str, str]:
    sub_env = {
        key: value
        for key, value in os.environ.items()
        if key not in SAFE_GIT_ENV_EXCLUDE
    }
    sub_env.update(
        {
            "LC_ALL": "C",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_GRAFT_FILE": os.devnull,
        }
    )
    if env:
        sub_env.update(env)
    return sub_env


def git(root: Path, *args: str, timeout: float = 60.0, env: Mapping[str, str] | None = None) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            ["git", "--no-replace-objects", "-c", "core.useReplaceRefs=false", "-C", str(root), *args],
            capture_output=True,
            timeout=timeout,
            env=safeGitEnv(env),
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(args, 127, b"", str(exc).encode())


def hasCommit(root: Path, sha: str) -> bool:
    return git(root, "cat-file", "-e", f"{sha}^{{commit}}").returncode == 0


def blob(root: Path, sha: str, path: str) -> bytes | None:
    result = git(root, "cat-file", "blob", f"{sha}:{path}")
    return result.stdout if result.returncode == 0 else None


def normalizeStamps(text: str) -> str:
    return GAIAVERSION.sub('GAIA_VERSION = "X"', STAMP.sub("?v=X", text))


def baseVersion(root: Path, baseSha: str) -> str | None:
    data = blob(root, baseSha, "pyproject.toml")
    if data is None:
        return None
    for line in data.decode("utf-8", "replace").splitlines():
        if line.startswith("version = "):
            return line.split("=", 1)[1].strip().strip('"')
    return None


def stampProof(root: Path, baseSha: str, headSha: str, paths: list[str]) -> Proof:
    """Every ``?v=`` stamp in the PR's HTML must equal the base version, or CI's cache-busting step fails."""

    expected = baseVersion(root, baseSha)
    if expected is None:
        return Proof("cache-bust-current", UNKNOWN, "base version could not be read from git objects")
    stale: list[str] = []
    for path in paths:
        if not path.endswith(".html"):
            continue
        data = blob(root, headSha, path)
        if data is None:
            return Proof("cache-bust-current", UNKNOWN, f"{path} is not readable at the head commit")
        found = set(re.findall(r"\?v=([0-9]+\.[0-9]+\.[0-9]+)", data.decode("utf-8", "replace")))
        found |= set(re.findall(r'GAIA_VERSION = "([0-9.]+)"', data.decode("utf-8", "replace")))
        if found - {expected}:
            stale.append(f"{path} carries {sorted(found - {expected})}")
    if stale:
        return Proof("cache-bust-current", FAIL, f"stale version stamps (base is {expected}): " + "; ".join(stale))
    return Proof("cache-bust-current", PASS, f"every stamp equals base version {expected}")


SEMVER = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]{1,40})?$")
DANGEROUS = re.compile(r"[<>\"'`=&\\\x00-\x08\x0b\x0c\x0e-\x1f\u2028\u2029]|javascript:|vbscript:|data:", re.IGNORECASE)
URLISH = re.compile(r"(?:^|[a-z])(?:url|urls|href|link|canonical)$|^(?:json|previous|archive|next)$", re.IGNORECASE)
SAFEURL = re.compile(r"^(?:/(?!/)[A-Za-z0-9._~/%?#-]*|https://(?:gaiaskilltree\.com|github\.com)/[A-Za-z0-9._~/%?#:@+-]*|)$")


def payloadProblems(value: Any, path: str = "report") -> list[str]:
    """Strict, structural safety of a report payload.

    The report template renders ``generatorVersion`` inside a ``<script>`` and several URLs into attributes without
    autoescaping. A byte-for-byte regeneration proof cannot see an injected value because the render reproduces it, so the
    payload itself must be proven inert: a semver where a version belongs, relative or allow-listed absolute URLs, and no
    markup, control character or script scheme in any string.
    """

    found: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            where = f"{path}.{key}"
            if key == "generatorVersion" and not (isinstance(item, str) and SEMVER.match(item)):
                found.append(f"{where} is not a semantic version")
            if URLISH.search(str(key)) and key not in ("urls",) and not isinstance(item, (dict, str)):
                found.append(f"{where} must be a string URL")
            if URLISH.search(str(key)) and isinstance(item, str) and not SAFEURL.match(item):
                found.append(f"{where} is not a relative or allow-listed URL")
            found += payloadProblems(item, where)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found += payloadProblems(item, f"{path}[{index}]")
    elif isinstance(value, str) and DANGEROUS.search(value):
        found.append(f"{path} contains markup, a control character or a script scheme")
    return found


def reportJsonProof(root: Path, headSha: str, label: str) -> Proof:
    data = blob(root, headSha, f"docs/api/v1/reports/{label}.json")
    if data is None:
        return Proof("report-json", UNKNOWN, "canonical JSON is not readable at the head commit")
    try:
        report = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return Proof("report-json", FAIL, "canonical JSON does not parse")
    problems = []
    year, week = label.split("-")
    if report.get("reportId", label) != label:
        problems.append(f"reportId {report.get('reportId')!r} != {label!r}")
    if report.get("isoYear") != int(year) or report.get("isoWeek") != int(week):
        problems.append("isoYear/isoWeek do not match the label")
    if not report.get("salvageLayer"):
        problems.append("salvageLayer is absent")
    if not isinstance(report.get("generatedAt"), str) or not report["generatedAt"]:
        problems.append("generatedAt is absent")
    problems += payloadProblems(report)[:4]
    return Proof("report-json", FAIL if problems else PASS, "; ".join(problems) or f"canonical JSON for {label} is well formed")


ALLOWEDATTRS = frozenset({"aria-disabled", "aria-label", "aria-labelledby", "async", "charset", "class", "content", "crossorigin", "data-ga4",
                          "data-grade", "data-icon-base", "data-injector", "href", "http-equiv", "id", "lang", "name", "property", "rel", "src", "type"})
ALLOWEDHOSTS = frozenset({"gaiaskilltree.com", "fonts.googleapis.com", "fonts.gstatic.com", "github.com", "www.googletagmanager.com"})
GRADE = re.compile(r"^[A-FS][+-]?$")


def surfaceProblems(html: str) -> list[str]:
    """Defense in depth on the RENDERED page: only the attribute names every published report uses, no inline event handler,
    only allow-listed hosts in any URL, and a data-grade that is a grade. A render that reproduces an injected value still fails here."""

    from html.parser import HTMLParser

    problems: list[str] = []

    class Scan(HTMLParser):
        def handle_starttag(self, tag: str, attrs: list) -> None:
            for name, value in attrs:
                if name not in ALLOWEDATTRS:
                    problems.append(f"<{tag}> carries the attribute {name!r}")
                    continue
                if name == "data-grade" and value is not None and not GRADE.match(value):
                    problems.append(f"data-grade {value!r} is not a grade")
                if name in ("href", "src", "content") and value:
                    host = re.match(r"^(?:https?:)?//([^/\s]+)", value)
                    if value.startswith("//") or (host and host.group(1).lower() not in ALLOWEDHOSTS):
                        problems.append(f"{name} points outside the allow-listed hosts: {value[:60]!r}")
                    if re.match(r"^\s*(javascript|vbscript|data):", value, re.IGNORECASE):
                        problems.append(f"{name} uses a script scheme")

    Scan(convert_charrefs=False).feed(html)
    return problems[:6]


def boundedObjectRead(root: Path, args: list[str], limit: int, deadline: float) -> bytes | None:
    """Read bounded raw Git output without archive, checkout, or attribute filters."""
    command = ["git", "--no-replace-objects", "-c", "core.useReplaceRefs=false",
               "--literal-pathspecs", "-C", str(root), *args]
    process = None
    try:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL, env=safeGitEnv())
        data = bytearray()
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not selector.select(remaining):
                    return None
                chunk = os.read(process.stdout.fileno(), min(65536, limit + 1 - len(data)))
                if not chunk:
                    break
                data.extend(chunk)
                if len(data) > limit:
                    return None
        if process.wait(timeout=max(0.001, deadline - time.monotonic())) != 0:
            return None
        return bytes(data)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None
    finally:
        if process is not None:
            if process.poll() is None:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
            process.wait()
            if process.stdout is not None:
                process.stdout.close()


def exportBase(root: Path, baseSha: str, paths: list[str], target: Path) -> bool:
    """Materialize exact committed regular blobs; attributes cannot omit or rewrite them."""
    if not re.fullmatch(r"[0-9a-f]{40}", baseSha) or not paths:
        return False
    def safePath(value: str) -> bool:
        parts = value.split("/")
        return bool(value) and all(part not in ("", ".", "..") and "\\" not in part for part in parts)
    if not all(safePath(path) for path in paths):
        return False
    deadline = time.monotonic() + 120.0
    listing = boundedObjectRead(root, ["ls-tree", "-r", "-l", "-z", "--full-tree", baseSha, "--", *paths], 4 * 1024 * 1024, deadline)
    if listing is None or not listing.endswith(b"\0"):
        return False
    entries = []
    total = 0
    try:
        for row in listing[:-1].split(b"\0"):
            header, rawPath = row.split(b"\t", 1)
            mode, kind, oid, rawSize = header.split()
            path = rawPath.decode("utf-8", "strict")
            if (mode not in (b"100644", b"100755") or kind != b"blob"
                    or not re.fullmatch(rb"[0-9a-f]{40}", oid) or not safePath(path)
                    or not any(path == selected or path.startswith(selected + "/") for selected in paths)):
                return False
            size = int(rawSize)
            total += size
            if size < 0 or size > 16 * 1024 * 1024 or total > 64 * 1024 * 1024 or len(entries) >= 16384:
                return False
            entries.append((path, mode, oid, size))
        if len({entry[0] for entry in entries}) != len(entries) or any(
                not any(path == selected or path.startswith(selected + "/") for path, *_ in entries) for selected in paths):
            return False
        # Even a pre-existing symlink above the target would escape the intended
        # output path. Production uses a fresh private temporary directory.
        if target.resolve() != Path(os.path.abspath(target)):
            return False
        target.mkdir(parents=True, exist_ok=True)
        for path, mode, oid, size in entries:
            data = boundedObjectRead(root, ["cat-file", "blob", oid.decode("ascii")], size, deadline)
            if data is None or len(data) != size or hashlib.sha1(b"blob " + str(size).encode() + b"\0" + data).hexdigest().encode() != oid:
                return False
            dest = target
            for part in path.split("/")[:-1]:
                dest = dest / part
                if dest.is_symlink():
                    return False
                dest.mkdir(exist_ok=True)
            dest = dest / path.split("/")[-1]
            if dest.exists() or dest.is_symlink():
                return False
            with dest.open("xb") as output:
                output.write(data)
            dest.chmod(0o755 if mode == b"100755" else 0o644)
        return True
    except (OSError, ValueError, UnicodeError):
        return False


RENDER = """
import json, sys
from pathlib import Path
work = Path(sys.argv[1])
sys.path.insert(0, str(work / "base" / "scripts"))
from contentEngine import generate_weekly_report as gen
templates = work / "base" / "scripts" / "contentEngine" / "templates"
report = json.loads((work / "report.json").read_text(encoding="utf-8"))
gen.renderHtml(report, templates, work / "rendered.html")
docs = work / "docs"
(docs / "reports" / report["reportId"]).mkdir(parents=True, exist_ok=True)
(docs / "reports" / report["reportId"] / "index.html").write_text((work / "rendered.html").read_text(encoding="utf-8"), encoding="utf-8")
(docs / "api" / "v1" / "reports").mkdir(parents=True, exist_ok=True)
(docs / "api" / "v1" / "reports" / (report["reportId"] + ".json")).write_text((work / "report.json").read_text(encoding="utf-8"), encoding="utf-8")
head = json.loads((work / "index.json").read_text(encoding="utf-8"))
gen._rebuildArchive(docs, templates, work / "rebuilt-index.json", work / "rebuilt-index.html", head.get("generatedAt"), "0.0.0")
"""


def contentEngineProofs(root: Path, baseSha: str, headSha: str, label: str) -> list[Proof]:
    """Regenerate the report and both shared indexes from base templates and base reports; compare to the head."""

    if not LABEL.match(label):
        return [Proof("rendered-html", FAIL, "label is not an ISO week")]
    needed = {
        "report": blob(root, headSha, f"docs/api/v1/reports/{label}.json"),
        "html": blob(root, headSha, f"docs/reports/{label}/index.html"),
        "indexJson": blob(root, headSha, "docs/api/v1/reports/index.json"),
        "indexHtml": blob(root, headSha, "docs/reports/index.html"),
    }
    if any(value is None for value in needed.values()) or not hasCommit(root, baseSha):
        return [Proof("rendered-html", UNKNOWN, "head or base objects are not available locally"),
                Proof("index-rebuild", UNKNOWN, "head or base objects are not available locally")]
    with tempfile.TemporaryDirectory(prefix="steward-ce-") as tmp:
        # Resolve the private directory once: exportBase refuses any target whose resolved path differs from its
        # literal path, and macOS temp roots (/var -> /private/var) are symlinked. The check itself is unchanged.
        work = Path(tmp).resolve()
        (work / "base").mkdir()
        if not exportBase(root, baseSha, ["scripts/contentEngine", "scripts/publication_context.py"], work / "base") \
                or not exportBase(root, baseSha, ["docs/reports", "docs/api/v1/reports"], work / "docs-base"):
            return [Proof("rendered-html", UNKNOWN, "base export failed"), Proof("index-rebuild", UNKNOWN, "base export failed")]
        # The base's own reports are the history the rebuilt indexes must preserve.
        (work / "docs").mkdir()
        for sub in ("reports", "api/v1/reports"):
            source = work / "docs-base" / "docs" / sub
            if source.is_dir():
                target = work / "docs" / sub
                target.mkdir(parents=True, exist_ok=True)
                for item in source.rglob("*"):
                    if item.is_file() and item.name != "index.json" and not (item.parent == source and item.name == "index.html"):
                        destination = target / item.relative_to(source)
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        destination.write_bytes(item.read_bytes())
        (work / "report.json").write_bytes(needed["report"])
        (work / "index.json").write_bytes(needed["indexJson"])
        try:
            run = subprocess.run([sys.executable, "-c", RENDER, str(work)], capture_output=True, text=True,
                                 timeout=120, cwd=work, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return [Proof("rendered-html", UNKNOWN, f"renderer did not run: {type(exc).__name__}")] * 1 + \
                   [Proof("index-rebuild", UNKNOWN, "renderer did not run")]
        if run.returncode != 0:
            tail = (run.stderr.strip().splitlines() or ["no output"])[-1][:160]
            return [Proof("rendered-html", UNKNOWN, f"renderer failed: {tail}"), Proof("index-rebuild", UNKNOWN, "renderer failed")]
        proofs = []
        rendered = normalizeStamps((work / "rendered.html").read_text(encoding="utf-8"))
        committed = normalizeStamps(needed["html"].decode("utf-8", "replace"))
        surface = surfaceProblems(committed)
        same = rendered == committed
        proofs.append(Proof("rendered-html", PASS if same and not surface else FAIL,
                            ("HTML equals the base-template render of its canonical JSON and uses only the published attribute and host set"
                             if same and not surface else
                             "HTML differs from the base-template render of its canonical JSON" if not same
                             else "rendered page breaks the attribute or host allow-list: " + "; ".join(surface))))
        rebuiltJson = json.loads((work / "rebuilt-index.json").read_text(encoding="utf-8"))
        committedJson = json.loads(needed["indexJson"].decode("utf-8"))
        sameRows = rebuiltJson.get("reports") == committedJson.get("reports")
        rebuiltHtml = normalizeStamps((work / "rebuilt-index.html").read_text(encoding="utf-8"))
        committedHtml = normalizeStamps(needed["indexHtml"].decode("utf-8", "replace"))
        ids = [row.get("reportId") for row in committedJson.get("reports", [])]
        ordered = ids == sorted(ids, reverse=True) and len(set(ids)) == len(ids)
        good = sameRows and ordered and rebuiltHtml == committedHtml
        detail = "both indexes equal a rebuild from base history plus this report; descending, no duplicates" if good else (
            ("index.json rows differ from the rebuild (a historical report may be dropped or misplaced)" if not sameRows else "")
            + ("; index not strictly descending or has duplicates" if not ordered else "")
            + ("; index.html differs from the rebuild" if rebuiltHtml != committedHtml else "")).lstrip("; ")
        proofs.append(Proof("index-rebuild", PASS if good else FAIL, detail))
        return proofs


def asMapping(proof: Proof) -> Mapping[str, Any]:
    return {"name": proof.name, "state": proof.state, "detail": proof.detail}
