#!/usr/bin/env python3
"""Maintainer-authorized, issue-backed recovery of a `gaia push` intake batch (#2050).

`gaia push` writes its batch JSON only to the submitter's disk. When that file was
never committed, the topology job in `.github/workflows/intake-approval.yml` cannot
find `registry-for-review/skill-batches/<batchId>.json`. This script builds a
*normalized current review record* from what the intake issue actually shows plus
upstream SKILL.md blobs that it fetches and hashes, and states plainly that the
result is a reconstruction. It never claims the original bytes were recovered.

Honesty rules (each is enforced and tested):
  * only a repository admin/maintain/write actor may recover, with a rationale;
  * nothing is written unless every required fact is present and every source
    verified; missing facts are listed by name instead of being guessed;
  * no evidence rows, approvals, L4 attestations, discovery packets or assessment
    receipts are invented; evidence is carried over only if the issue showed it;
  * an existing batch file is never overwritten;
  * receipts and records carry no timestamps, so replaying the same inputs
    produces the same bytes.

Everything past recovery (schema validation, intake validation, L4 human review,
evidence-ready / evidence-approved, the single promotion PR) is unchanged.

Subcommands: recover, payload, materialize. Standard library only.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
import re
import sys
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import zipfile

SCHEMA_VERSION = 1
AUTHORIZED_PERMISSIONS = {"admin", "maintain", "write"}
BOT_LOGINS = {"github-actions", "github-actions[bot]"}
MIN_RATIONALE = 10
MAX_SOURCE_BYTES = 512 * 1024
MAX_RECORD_COMMENT = 60000  # GitHub caps comments at 65,536 characters
FACT_KEYS = {"name", "type", "description", "prerequisites", "skillFileUrl"}

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_REFUSED = 2
EXIT_BLOCKED = 3
EXIT_STALE = 4

BATCH_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SKILL_ID_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
SOURCE_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
GENERATED_AT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
SEGMENT_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
APPROVAL_MARKER = re.compile(r"<!-- gaia-intake-approval (\{.*?\}) -->", re.S)
RECORD_MARKER = re.compile(r"<!-- gaia-intake-recovery-record ([A-Za-z0-9+/=]+) -->")
# Headers keep failure logs out of the pointer parser. They do not authenticate
# approvals: only the verified immutable workflow artifact grants authority.
RECORD_HEADER = "## Intake recovery record (reconstruction)"
APPROVAL_HEADER = "## Intake topology approved — evidence review queued"
WORKFLOW_PATH = ".github/workflows/intake-approval.yml"
MAX_HANDOFF_BYTES = 4 * 1024 * 1024


class RecoveryError(Exception):
    """A refusal with an exit code and a message safe to show a maintainer."""

    def __init__(self, message, code=EXIT_ERROR, lines=None):
        super().__init__(message)
        self.code = code
        self.lines = list(lines or [])


# ---------------------------------------------------------------------------
# hashing / canonical JSON
# ---------------------------------------------------------------------------


def canonicalJson(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256Hex(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# upstream sources
# ---------------------------------------------------------------------------


def parseSkillBlobUrl(url):
    """Return (owner, repo, ref, path) for an exact GitHub SKILL.md blob URL, else None."""
    if not isinstance(url, str) or url != url.strip() or not url:
        return None
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc != "github.com":
        return None
    if parsed.query or parsed.fragment or "@" in url or "\\" in url:
        return None
    parts = parsed.path.split("/")
    # ['', owner, repo, 'blob', ref, *path]
    if len(parts) < 6 or parts[0] != "" or parts[3] != "blob":
        return None
    owner, repo, ref = parts[1], parts[2], parts[4]
    path = parts[5:]
    if not (SEGMENT_RE.match(owner) and SEGMENT_RE.match(repo) and SEGMENT_RE.match(ref)):
        return None
    if any(segment in ("", ".", "..") or not SEGMENT_RE.match(segment) for segment in path):
        return None
    if path[-1] != "SKILL.md":
        return None
    return owner, repo, ref, "/".join(path)


def rawUrlFor(parsed):
    owner, repo, ref, path = parsed
    quoted = "/".join(urllib.parse.quote(segment, safe="") for segment in path.split("/"))
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{quoted}"


def defaultFetcher(rawUrl):
    """Fetch bytes from raw.githubusercontent.com only; bounded size and time."""
    parsed = urllib.parse.urlsplit(rawUrl)
    if parsed.scheme != "https" or parsed.netloc != "raw.githubusercontent.com":
        raise RecoveryError(f"Refusing to fetch non-GitHub raw URL: {rawUrl}", EXIT_BLOCKED)
    request = urllib.request.Request(rawUrl, headers={"User-Agent": "gaia-intake-recovery"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310 (host pinned above)
            data = response.read(MAX_SOURCE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raise RecoveryError(f"Upstream source returned HTTP {exc.code}: {rawUrl}", EXIT_BLOCKED) from exc
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        raise RecoveryError(f"Could not fetch upstream source {rawUrl}: {exc}", EXIT_ERROR) from exc
    return data


def verifySources(skillUrls, fetcher):
    """Fetch and hash each (skillId -> url). Returns a deterministic list of source records."""
    problems = []
    seen = {}
    for skillId, url in skillUrls.items():
        parsed = parseSkillBlobUrl(url)
        if parsed is None:
            problems.append(
                f"skills[{skillId}] source is not an exact "
                f"https://github.com/<owner>/<repo>/blob/<ref>/.../SKILL.md URL: {url!r}"
            )
        elif url in seen:
            problems.append(f"skills[{skillId}] repeats the source already used by skills[{seen[url]}]: {url}")
        else:
            seen[url] = skillId
    if problems:
        raise RecoveryError("Malformed upstream sources.", EXIT_BLOCKED, problems)
    records = []
    for skillId, url in skillUrls.items():
        raw = rawUrlFor(parseSkillBlobUrl(url))
        data = fetcher(raw)
        if not isinstance(data, (bytes, bytearray)) or not data:
            problems.append(f"skills[{skillId}] source is empty: {url}")
            continue
        if len(data) > MAX_SOURCE_BYTES:
            problems.append(f"skills[{skillId}] source exceeds {MAX_SOURCE_BYTES} bytes: {url}")
            continue
        if b"\x00" in data:
            problems.append(f"skills[{skillId}] source is not text: {url}")
            continue
        try:
            bytes(data).decode("utf-8")
        except UnicodeDecodeError:
            problems.append(f"skills[{skillId}] source is not valid UTF-8: {url}")
            continue
        records.append({"skillId": skillId, "url": url, "sha256": sha256Hex(bytes(data)), "bytes": len(data)})
    if problems:
        raise RecoveryError("Upstream sources failed verification.", EXIT_BLOCKED, problems)
    return records


# ---------------------------------------------------------------------------
# parsing the intake issue body (the renderer lives in src/gaia_cli/prWriter.py)
# ---------------------------------------------------------------------------


def firstBacktick(text):
    match = re.search(r"`([^`]+)`", text or "")
    return match.group(1) if match else None


def section(body, heading):
    match = re.search(rf"^### {re.escape(heading)}[^\n]*\n(.*?)(?=^### |^---$|\Z)", body, re.S | re.M)
    return match.group(1) if match else ""


def parseMetadata(body):
    rows = {}
    for line in section(body, "Batch metadata").splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[0] not in ("Field", "---", ""):
            rows[cells[0]] = cells[1]
    return rows


def parseEvidenceRows(block):
    evidence = []
    for line in block.splitlines():
        if not line.startswith("|") or line.startswith("| Grade") or line.startswith("|---"):
            continue
        cells = [cell.strip() for cell in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
        if len(cells) < 4:
            continue
        grade = re.search(r"\*\*([^*]+)\*\*", cells[0])
        urlMatch = re.search(r"\]\(([^)]+)\)", cells[2])
        item = {"grade": grade.group(1) if grade else cells[0]}
        evType = firstBacktick(cells[1])
        if evType and evType != "-":
            item["type"] = evType
        item["url"] = urlMatch.group(1) if urlMatch else cells[2]
        notes = cells[3].replace("\\|", "|")
        if notes:
            item["notes"] = notes
        evidence.append(item)
    return evidence


def parseDetailsBlock(skillId, name, skillType, body):
    skill = {"id": skillId, "name": name.strip(), "type": skillType}
    description = re.search(r"\*\*Description:\*\* (.*?)\n\n\*\*Prerequisites:\*\*", body, re.S)
    if description and description.group(1).strip() not in ("", "-"):
        skill["description"] = description.group(1).strip()
    prereqLine = re.search(r"\*\*Prerequisites:\*\* ([^\n]*)", body)
    if prereqLine:
        skill["prerequisites"] = re.findall(r"`([^`]+)`", prereqLine.group(1))
    attributionLine = re.search(r"\*\*Attribution:\*\* ([^\n]*)", body)
    if attributionLine and attributionLine.group(1).strip() != "-":
        text = attributionLine.group(1)
        attribution = {}
        for kind in ("self-made", "aggregator", "attributed", "abstract"):
            if kind in text.split(" · ")[0]:
                attribution["type"] = kind
        author = re.search(r"upstream: `([^`]+)`", text)
        if author:
            attribution["upstream_author"] = author.group(1)
        link = re.search(r"\]\((https?://[^)]+)\)", text)
        if link:
            attribution["skill_file_url"] = link.group(1)
        if attribution:
            skill["attribution"] = attribution
    evidence = re.search(r"\*\*Evidence:\*\*\n\n(.*?)\n\n(?=\*\*|</)", body, re.S)
    skill["evidence"] = parseEvidenceRows(evidence.group(1)) if evidence else []
    named = re.search(r"\*\*Named skill request:\*\* 📌 Named: `([^`/]+)/([^`]+)`(?:\s+·\s+([^\s·\[]+))?(?:\s+·\s+\[blob link\]\(([^)]+)\))?", body)
    if named:
        block = {"contributor": named.group(1), "skill_name": named.group(2)}
        if named.group(3) and named.group(3) != "?":
            block["level"] = named.group(3)
        if named.group(4):
            block["links_github"] = named.group(4)
        skill["named"] = block
    return skill


def parseIssueBody(body):
    """Parse the `gaia push` intake issue body into (record, problems)."""
    problems = []
    meta = parseMetadata(body)
    record = {
        "userId": firstBacktick(meta.get("User", "")),
        "sourceRepo": firstBacktick(meta.get("Source repo", "")),
        "generatedAt": firstBacktick(meta.get("Generated at", "")),
        "batchId": firstBacktick(meta.get("Batch ID", "")),
        "batchBranch": firstBacktick(meta.get("Batch Branch", "")),
    }
    for key, label in (("userId", "User"), ("sourceRepo", "Source repo"), ("generatedAt", "Generated at"), ("batchId", "Batch ID")):
        if not record[key]:
            problems.append(f"issue metadata row '{label}' is missing")
    if record["batchId"] and not BATCH_ID_RE.match(record["batchId"]):
        problems.append(f"issue Batch ID {record['batchId']!r} is not a safe file name")
        record["batchId"] = None
    if record["sourceRepo"] and not SOURCE_REPO_RE.match(record["sourceRepo"]):
        problems.append(f"issue Source repo {record['sourceRepo']!r} is not owner/repo")
        record["sourceRepo"] = None
    if record["generatedAt"] and not GENERATED_AT_RE.match(record["generatedAt"]):
        problems.append(f"issue Generated at {record['generatedAt']!r} is not a UTC timestamp")
        record["generatedAt"] = None

    skills = {}
    order = []
    detailPattern = re.compile(
        r"<details>\s*<summary><b><code>([^<]+)</code></b> — (.*?) &nbsp;·&nbsp; <code>([^<]+)</code></summary>(.*?)</details>",
        re.S,
    )
    for match in detailPattern.finditer(body):
        skillId = match.group(1).strip()
        if skillId in skills:
            problems.append(
                f"issue lists generic id '{skillId}' more than once (an N:1 fan-out intake). Recovery does not "
                "reconstruct these: the blocks cannot be told apart reliably. Rebuild the batch from the committed "
                "ratified packets with `gaia push --from-file <discovery-packet-manifest-v1>`"
            )
            continue
        skills[skillId] = parseDetailsBlock(skillId, match.group(2), match.group(3).strip(), match.group(4))
        order.append(skillId)
    for line in section(body, "Quick decision table").splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and cells[0].isdigit():
            skillId = firstBacktick(cells[1])
            if skillId and skillId not in skills:
                skills[skillId] = {"id": skillId, "type": firstBacktick(cells[2]), "evidence": []}
                order.append(skillId)
    for line in section(body, "Skill details").splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 4 and cells[0].startswith("`") and cells[0].endswith("`"):
            skillId = firstBacktick(cells[0])
            if skillId in skills:
                skills[skillId].setdefault("name", cells[1])
                skills[skillId].setdefault("type", firstBacktick(cells[2]))

    expected = firstBacktick(meta.get("Proposed new skills", ""))
    if expected is not None and expected.isdigit() and int(expected) != len(order):
        problems.append(f"issue states {expected} proposed skill(s) but {len(order)} could be read")
    if not order:
        problems.append("issue lists no proposed skills")
    record["skills"] = [skills[skillId] for skillId in order]

    known = []
    for line in section(body, "Detected canonical skills").splitlines():
        match = re.match(r"- `([^`]+)`", line.strip())
        if match:
            known.append({"skillId": match.group(1)})
    record["knownSkills"] = known
    knownExpected = firstBacktick(meta.get("Known canonical skills", ""))
    if knownExpected is not None and knownExpected.isdigit() and int(knownExpected) != len(known):
        problems.append(f"issue states {knownExpected} known skill(s) but {len(known)} could be read")

    identity = re.search(r"<!-- gaia:identity (\{.*?\}) gaia:identity-end -->", body, re.S)
    record["identity"] = None
    if identity:
        try:
            record["identity"] = json.loads(identity.group(1))
        except ValueError:
            problems.append("issue identity block is not valid JSON")
        else:
            if record["sourceRepo"] and record["identity"].get("sourceRepo") not in (None, record["sourceRepo"]):
                problems.append("issue identity block names a different source repo than the metadata table")
    return record, problems


# ---------------------------------------------------------------------------
# facts supplied by the authorized maintainer
# ---------------------------------------------------------------------------


def parseFacts(raw):
    """Parse the optional maintainer-supplied facts: {skillId: {description, ...}}."""
    if raw is None or not str(raw).strip():
        return {}
    try:
        facts = json.loads(raw)
    except ValueError as exc:
        raise RecoveryError(f"Recovery facts are not valid JSON: {exc}", EXIT_BLOCKED) from exc
    if not isinstance(facts, dict):
        raise RecoveryError("Recovery facts must be a JSON object keyed by skill id.", EXIT_BLOCKED)
    problems = []
    for skillId, fields in facts.items():
        if not isinstance(fields, dict):
            problems.append(f"facts[{skillId}] must be an object")
            continue
        unknown = sorted(set(fields) - FACT_KEYS)
        if unknown:
            problems.append(f"facts[{skillId}] has unsupported key(s): {', '.join(unknown)} (allowed: {', '.join(sorted(FACT_KEYS))})")
        for key, value in fields.items():
            if key == "prerequisites":
                valid = isinstance(value, list) and all(isinstance(item, str) for item in value)
            else:
                valid = isinstance(value, str) and 0 < len(value.strip()) <= 2000
            if key in FACT_KEYS and not valid:
                problems.append(f"facts[{skillId}].{key} has an unusable value")
    if problems:
        raise RecoveryError("Malformed recovery facts.", EXIT_BLOCKED, problems)
    return facts


def applyFacts(record, facts):
    """Fill gaps from facts; a fact that contradicts the issue is an error."""
    byId = {skill["id"]: skill for skill in record["skills"]}
    problems = []
    for skillId, fields in facts.items():
        skill = byId.get(skillId)
        if skill is None:
            problems.append(f"facts name skill '{skillId}' which the issue does not list")
            continue
        for key, value in fields.items():
            if key == "skillFileUrl":
                current = (skill.get("attribution") or {}).get("skill_file_url") or namedBlob(skill)
                if current and current != value:
                    problems.append(f"facts[{skillId}].skillFileUrl contradicts the issue ({current})")
                else:
                    skill["skillFileUrlFact"] = value
                    skill["factKeys"] = skill.get("factKeys", []) + [key]
                continue
            if skill.get(key) not in (None, "", []) and skill.get(key) != value:
                problems.append(f"facts[{skillId}].{key} contradicts the issue")
                continue
            skill[key] = value
            skill["factKeys"] = skill.get("factKeys", []) + [key]
    if problems:
        raise RecoveryError("Recovery facts conflict with the issue.", EXIT_BLOCKED, problems)


def namedBlob(skill):
    link = (skill.get("named") or {}).get("links_github")
    return link if parseSkillBlobUrl(link) else None


def resolveSourceUrls(record):
    return {
        skill["id"]: skill.get("skillFileUrlFact")
        or (skill.get("attribution") or {}).get("skill_file_url")
        or namedBlob(skill)
        for skill in record["skills"]
    }


def validateContributor(value):
    """Stdlib-only counterpart of gaia_cli.namedIdentity for sparse workflow tooling.

    Source repository owner spelling and upstream attribution are external
    provenance; this contract applies only to Gaia's named contributor identity.
    """
    if not isinstance(value, str) or not value.strip():
        return "contributor is required"
    if "/" in value:
        return f"contributor '{value}' cannot contain '/'"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", value):
        return (f"contributor '{value}' is not a valid handle "
                "(lowercase alphanumeric, underscore or hyphen)")
    if value != value.lower():
        return (f"contributor '{value}' must be lowercase; expected '{value.lower()}'. "
                "Gaia never normalizes identities silently")
    return None


def requireLowercaseNamedContributors(batch):
    for skill in batch.get("proposedSkills") or []:
        if skill.get("named"):
            problem = validateContributor(skill["named"].get("contributor"))
            if problem:
                raise RecoveryError(problem, EXIT_BLOCKED)


def findMissingFacts(record):
    missing = []
    urls = resolveSourceUrls(record)
    for skill in record["skills"]:
        skillId = skill["id"]
        if skill.get("named"):
            identityProblem = validateContributor(skill["named"].get("contributor"))
            if identityProblem:
                missing.append(f"skills[{skillId}].named: {identityProblem}")
        if not SKILL_ID_RE.match(skillId or ""):
            missing.append(f"skills[{skillId!r}].id is not a kebab-case skill id")
        if not str(skill.get("name") or "").strip():
            missing.append(f"skills[{skillId}].name")
        if skill.get("type") not in ("basic", "fusion"):
            missing.append(f"skills[{skillId}].type (basic or fusion)")
        if len(str(skill.get("description") or "").strip()) < 10:
            missing.append(f"skills[{skillId}].description (at least 10 characters)")
        if skill.get("type") == "fusion" and not skill.get("prerequisites"):
            missing.append(f"skills[{skillId}].prerequisites (a fusion needs at least one)")
        if skill.get("type") == "basic" and skill.get("prerequisites"):
            missing.append(f"skills[{skillId}].prerequisites (a basic skill has none)")
        for prereq in skill.get("prerequisites") or []:
            if not SKILL_ID_RE.match(str(prereq)):
                missing.append(f"skills[{skillId}].prerequisites contains non-kebab id {prereq!r}")
        if not urls.get(skillId):
            missing.append(f"skills[{skillId}].skillFileUrl (exact upstream SKILL.md blob URL)")
    return missing


# ---------------------------------------------------------------------------
# building the reconstruction
# ---------------------------------------------------------------------------


def batchRelPath(batchId):
    return f"registry-for-review/skill-batches/{batchId}.json"


def receiptRelPath(issueNumber):
    return f"registry-for-review/recoveries/intake-{int(issueNumber)}.json"


def buildReconstruction(record, sources, issue, actor, permission, rationale, bodySha256):
    issueNumber = int(issue["number"])
    batchId = record["batchId"]
    urls = resolveSourceUrls(record)
    marker = (
        f"Reconstructed from intake issue #{issueNumber} by maintainer-authorized recovery; "
        f"these are not the original batch bytes. See {receiptRelPath(issueNumber)}."
    )
    proposed = []
    for skill in record["skills"]:
        entry = {
            "id": skill["id"],
            "name": skill["name"],
            "type": skill["type"],
            "description": skill["description"].strip(),
            "sourceRepo": record["sourceRepo"],
            "lifecycle": "pending",
            "prerequisites": list(skill.get("prerequisites") or []),
        }
        attribution = dict(skill.get("attribution") or {})
        if not attribution.get("skill_file_url"):
            attribution["skill_file_url"] = urls[skill["id"]]
        entry["attribution"] = attribution
        if skill.get("named"):
            entry["named"] = dict(skill["named"])
        entry["evidence"] = list(skill.get("evidence") or [])
        entry["rationale"] = marker
        entry["openQuestions"] = [
            "Original batch bytes, discovery packet and assessment receipts are absent; "
            "current review obligations need fresh canonical assessments."
        ]
        proposed.append(entry)
    batch = {
        "batchId": batchId,
        "userId": record["userId"],
        "sourceRepo": record["sourceRepo"],
        "generatedAt": record["generatedAt"],
        "knownSkills": list(record["knownSkills"]),
        "proposedSkills": proposed,
        "similarity": [],
    }
    batchSha = sha256Hex(canonicalJson(batch))
    receipt = {
        "schemaVersion": SCHEMA_VERSION,
        "kind": "intake-batch-reconstruction",
        "reconstruction": True,
        "originalBytesRecovered": False,
        "issue": issueNumber,
        "issueAuthor": (issue.get("author") or {}).get("login"),
        "issueBodySha256": bodySha256,
        "original": {
            "batchId": batchId,
            "generatedAt": record["generatedAt"],
            "userId": record["userId"],
            "sourceRepo": record["sourceRepo"],
            "batchBranch": record.get("batchBranch"),
            "candidateIds": [skill["id"] for skill in record["skills"]],
            "identity": record.get("identity"),
        },
        "authorization": {
            "recoveredBy": actor,
            "permission": permission,
            "rationale": rationale.strip(),
        },
        "maintainerSuppliedFacts": {
            skill["id"]: sorted(set(skill.get("factKeys", []))) for skill in record["skills"] if skill.get("factKeys")
        },
        "sources": [
            {**source, "origin": "maintainer-supplied" if "skillFileUrl" in recordFactKeys(record, source["skillId"]) else "issue"}
            for source in sources
        ],
        "reconstructedBatch": {"path": batchRelPath(batchId), "sha256": batchSha},
        "notRecovered": [
            "original local batch JSON bytes",
            "original discovery packets and assessment receipts",
            "lexical similarity links from the original scan",
        ],
        "gatesNotWaived": [
            "maintainer authorization",
            "schema and intake validation",
            "L4 human review through gaia dev ratify",
            "intake:evidence-ready and intake:evidence-approved",
            "single review/meta/intake-<N> promotion PR",
        ],
    }
    return batch, receipt


def recordFactKeys(record, skillId):
    for skill in record["skills"]:
        if skill["id"] == skillId:
            return skill.get("factKeys", [])
    return []


def writeAtomic(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temp = f"{path}.tmp"
    with open(temp, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    os.replace(temp, path)


def serialize(value):
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


# ---------------------------------------------------------------------------
# recover
# ---------------------------------------------------------------------------


def requireAuthorized(actor, permission, rationale):
    if not actor or permission not in AUTHORIZED_PERMISSIONS:
        raise RecoveryError(
            f"{actor or 'The actor'} cannot authorize intake recovery (permission: {permission or 'none'}); "
            "admin, maintain or write is required.",
            EXIT_REFUSED,
        )
    if len((rationale or "").strip()) < MIN_RATIONALE:
        raise RecoveryError(
            f"A recovery rationale of at least {MIN_RATIONALE} characters is required.", EXIT_REFUSED
        )


def requireIntakeIssue(issue):
    labels = {label.get("name") if isinstance(label, dict) else label for label in issue.get("labels") or []}
    if "intake" not in labels:
        raise RecoveryError("The issue does not carry the 'intake' label; refusing to recover.", EXIT_REFUSED)
    if str(issue.get("state", "OPEN")).upper() != "OPEN":
        raise RecoveryError("The intake issue is not open; refusing to recover.", EXIT_REFUSED)


def verifyIssueRevision(issue, eventName, event, transition, expectedBodySha=None):
    """Pin a label approval to its event snapshot, not a later issue-author edit."""
    body = issue.get("body")
    if not isinstance(body, str):
        raise RecoveryError("The current intake issue body is unavailable.", EXIT_STALE)
    if eventName == "issues":
        snapshot = event.get("issue") or {}
        if (event.get("action") != "labeled" or snapshot.get("number") != issue.get("number")
                or (event.get("label") or {}).get("name") != f"intake:{transition}-approved"
                or snapshot.get("body") != body):
            raise RecoveryError("The issue revision differs from its authenticated approval event; re-approve it.", EXIT_STALE)
    elif eventName == "workflow_dispatch":
        if not isinstance(expectedBodySha, str) or not re.fullmatch(r"[0-9a-f]{64}", expectedBodySha):
            raise RecoveryError("Dispatch requires issue_body_sha256 for the maintainer-selected revision.", EXIT_REFUSED)
        if sha256Hex(body) != expectedBodySha:
            raise RecoveryError("The current issue differs from the revision selected for dispatch.", EXIT_STALE)
    else:
        raise RecoveryError("Only an authenticated label or dispatch event can approve intake.", EXIT_REFUSED)


def recover(issue, actor, permission, rationale, factsRaw, repoRoot, fetcher, existingComments=None):
    requireAuthorized(actor, permission, rationale)
    requireIntakeIssue(issue)
    body = issue.get("body") or ""
    record, problems = parseIssueBody(body)
    facts = parseFacts(factsRaw)
    applyFacts(record, facts)
    missing = findMissingFacts(record)
    if problems or missing:
        lines = [f"- {item}" for item in problems] + [f"- missing: {item}" for item in missing]
        raise RecoveryError(
            "Recovery is blocked: the issue does not yet state every fact a review record needs. "
            "Edit the issue body, or pass these as recovery facts. Nothing was written.",
            EXIT_BLOCKED,
            lines,
        )

    sources = verifySources(resolveSourceUrls(record), fetcher)
    batch, receipt = buildReconstruction(
        record, sources, issue, actor, permission, rationale, sha256Hex(body)
    )
    batchPath = os.path.join(repoRoot, batchRelPath(batch["batchId"]))
    receiptPath = os.path.join(repoRoot, receiptRelPath(issue["number"]))

    status = "recovered"
    if os.path.exists(batchPath):
        status = checkReplay(batch, receipt, batchPath, receiptPath)
    else:
        writeAtomic(batchPath, serialize(batch))
        writeAtomic(receiptPath, serialize(receipt))

    recordDigest = recordIdentityDigest(batch, receipt)
    alreadyRecorded = any(
        recordDigestOf(comment) == recordDigest
        for comment in botComments(existingComments, RECORD_MARKER, RECORD_HEADER)
    )
    return {
        "status": status,
        "batch": batch,
        "receipt": receipt,
        "batchPath": batchRelPath(batch["batchId"]),
        "receiptPath": receiptRelPath(issue["number"]),
        "recordDigest": recordDigest,
        "alreadyRecorded": alreadyRecorded,
    }


def receiptIdentity(receipt):
    """The part of a receipt that must match on replay (excludes who replayed it)."""
    clone = json.loads(canonicalJson(receipt))
    clone.pop("authorization", None)
    clone.pop("issueBodySha256", None)
    return clone


def checkReplay(batch, receipt, batchPath, receiptPath):
    """An existing batch file may only be a prior, identical recovery; never overwritten."""
    if not os.path.exists(receiptPath):
        raise RecoveryError(
            f"{batchRelPath(batch['batchId'])} already exists and is not a recorded recovery; "
            "recovery is only for absent batches and never overwrites existing bytes.",
            EXIT_REFUSED,
        )
    with open(receiptPath, encoding="utf-8") as handle:
        prior = json.load(handle)
    with open(batchPath, encoding="utf-8") as handle:
        onDisk = json.load(handle)
    if canonicalJson(onDisk) != canonicalJson(batch) or canonicalJson(receiptIdentity(prior)) != canonicalJson(receiptIdentity(receipt)):
        priorSources = {item["skillId"]: item["sha256"] for item in prior.get("sources", [])}
        newSources = {item["skillId"]: item["sha256"] for item in receipt["sources"]}
        if priorSources != newSources:
            raise RecoveryError(
                "Stale recovery: upstream SKILL.md bytes differ from the hashes recorded in the existing recovery receipt.",
                EXIT_STALE,
            )
        raise RecoveryError(
            "The reconstruction differs from the existing recorded recovery; refusing to overwrite it.",
            EXIT_STALE,
        )
    return "already-recovered"


# ---------------------------------------------------------------------------
# comments: the durable hand-off between the topology and evidence jobs
# ---------------------------------------------------------------------------


def commentList(commentsDoc):
    comments = commentsDoc.get("comments") if isinstance(commentsDoc, dict) else commentsDoc
    return comments if isinstance(comments, list) else []


def botComments(commentsDoc, marker, header):
    """Bodies written by github-actions, starting with `header`, carrying `marker`; oldest first."""
    found = []
    for comment in commentList(commentsDoc):
        if not isinstance(comment, dict):
            continue
        author = (comment.get("author") or {}).get("login")
        body = comment.get("body") or ""
        if author in BOT_LOGINS and body.startswith(header) and marker.search(body):
            found.append(body)
    return found


def sanitizeLog(text):
    """Make echoed log text inert: no HTML comment can open or close inside a bot comment."""
    return str(text).replace("<!--", "<! --").replace("-->", "-- >")


def recordIdentityDigest(batch, receipt):
    """Replay-stable digest of a record: excludes who ran the recovery and the body hash."""
    return sha256Hex(canonicalJson({"batch": batch, "receipt": receiptIdentity(receipt)}))


def recordDigestOf(body):
    decoded = decodeRecord(body)
    if not decoded:
        return None
    return recordIdentityDigest(decoded["batch"], decoded["receipt"])


def encodeRecord(batch, receipt):
    return base64.b64encode(canonicalJson({"batch": batch, "receipt": receipt}).encode("utf-8")).decode("ascii")


def decodeRecord(body):
    matches = RECORD_MARKER.findall(body or "")
    if not matches:
        return None
    try:
        decoded = json.loads(base64.b64decode(matches[-1]).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(decoded, dict) or not isinstance(decoded.get("batch"), dict) or not isinstance(decoded.get("receipt"), dict):
        return None
    return decoded


def buildApprovalPayload(batchPath, issueNumber, approver, repoRoot, receipt=None,
                         issueBody=None, runId=None, runAttempt=None, headSha=None):
    """The topology hand-off payload. Without a recovery it is byte-identical to the historical one."""
    with open(os.path.join(repoRoot, batchPath), encoding="utf-8") as handle:
        batch = json.load(handle)
    requireLowercaseNamedContributors(batch)
    payload = {
        "schemaVersion": 1,
        "batchId": batch["batchId"],
        "batchPath": batchPath,
        "issue": int(issueNumber),
        "topologyApprovedBy": approver,
        "evidenceReviewStatus": "pending",
    }
    if receipt is None:
        receiptFile = os.path.join(repoRoot, receiptRelPath(issueNumber))
        if os.path.exists(receiptFile):
            with open(receiptFile, encoding="utf-8") as handle:
                receipt = json.load(handle)
    if receipt is not None:
        payload["recovery"] = {
            "receiptPath": receiptRelPath(issueNumber),
            # Identity digest, not the full receipt: a replay from a fresh checkout
            # (another actor, an immaterial issue edit) must bind to the same record.
            "recordDigest": recordIdentityDigest(batch, receipt),
            "batchSha256": receipt["reconstructedBatch"]["sha256"],
            "issueBodySha256": receipt["issueBodySha256"],
            "reconstruction": True,
        }
        if issueBody is not None:
            payload["recovery"]["issueBodySha256"] = sha256Hex(issueBody)
    if issueBody is not None:
        payload.update({
            "issueBodySha256": sha256Hex(issueBody),
            "batchSha256": sha256Hex(canonicalJson(batch)),
            "workflowRunId": int(runId),
            "workflowRunAttempt": int(runAttempt),
            "workflowHeadSha": headSha,
        })
    return json.dumps(payload, separators=(",", ":"))


def handoffArtifactName(issueNumber, runId, attempt):
    return f"gaia-intake-topology-{int(issueNumber)}-{int(runId)}-{int(attempt)}"


def githubApi(endpoint, binary=False):
    """Authenticated API only, with argument arrays (never a shell or issue-controlled URL)."""
    try:
        result = subprocess.run(["gh", "api", "--method", "GET", endpoint],
                                capture_output=True, check=True, timeout=60)
        return result.stdout if binary else json.loads(result.stdout)
    except (subprocess.SubprocessError, ValueError) as exc:
        raise RecoveryError("Could not verify the topology workflow handoff; re-run topology approval.", EXIT_REFUSED) from exc


def verifyHandoff(approval, api=None, repository=None):
    """Authenticate immutable run artifacts; a bot comment is only an untrusted pointer.

    The Actions API supplies the repository, canonical workflow, event, actors and
    artifact ownership. The ZIP supplies the exact approved bytes. No permission,
    actor or event assertion from issue text or the comment itself grants access.
    """
    api = api or githubApi
    repository = repository or os.environ.get("GH_REPO")
    if not isinstance(repository, str) or not SOURCE_REPO_RE.fullmatch(repository):
        raise RecoveryError("GH_REPO must name the authenticated repository.", EXIT_REFUSED)
    runId, attempt = approval.get("workflowRunId"), approval.get("workflowRunAttempt")
    if type(runId) is not int or type(attempt) is not int or runId <= 0 or attempt <= 0:
        raise RecoveryError("Topology approval lacks verified workflow provenance. Re-run the topology approval.", EXIT_REFUSED)
    prefix = f"repos/{repository}"
    workflow = api(f"{prefix}/actions/workflows/intake-approval.yml")
    run = api(f"{prefix}/actions/runs/{runId}/attempts/{attempt}")
    actor = (run.get("actor") or {}).get("login")
    if (run.get("id") != runId or run.get("run_attempt") != attempt
            or run.get("workflow_id") != workflow.get("id") or workflow.get("path") != WORKFLOW_PATH
            or run.get("path", "").split("@", 1)[0] != WORKFLOW_PATH
            or (run.get("repository") or {}).get("full_name") != repository
            or (run.get("head_repository") or {}).get("full_name") != repository
            or run.get("head_sha") != approval.get("workflowHeadSha")
            or run.get("event") not in {"issues", "workflow_dispatch"}
            or run.get("status") != "completed" or run.get("conclusion") != "success"
            or not actor or actor != approval.get("topologyApprovedBy")):
        raise RecoveryError("Topology approval does not match an authenticated successful intake workflow event.", EXIT_REFUSED)
    for login in {actor, (run.get("triggering_actor") or {}).get("login")}:
        if not isinstance(login, str) or not re.fullmatch(r"[A-Za-z0-9-]+(?:\[bot\])?", login):
            raise RecoveryError("Topology event actor identity is missing or invalid.", EXIT_REFUSED)
        permission = api(f"{prefix}/collaborators/{login}/permission").get("permission")
        if permission not in AUTHORIZED_PERMISSIONS:
            raise RecoveryError("Topology event actor no longer has maintainer authorization.", EXIT_REFUSED)
    name = handoffArtifactName(approval["issue"], runId, attempt)
    artifacts = api(f"{prefix}/actions/runs/{runId}/artifacts?per_page=100").get("artifacts", [])
    artifacts = [item for item in artifacts if item.get("name") == name and not item.get("expired")]
    if len(artifacts) != 1 or type(artifacts[0].get("id")) is not int:
        raise RecoveryError("The immutable topology handoff artifact is absent or expired. Re-run the topology approval.", EXIT_STALE)
    artifact = artifacts[0]
    if artifact.get("size_in_bytes", MAX_HANDOFF_BYTES + 1) > MAX_HANDOFF_BYTES:
        raise RecoveryError("Topology handoff artifact exceeds the size limit.", EXIT_BLOCKED)
    archive = api(f"{prefix}/actions/artifacts/{artifact['id']}/zip", binary=True)
    if len(archive) > MAX_HANDOFF_BYTES:
        raise RecoveryError("Topology handoff archive exceeds the size limit.", EXIT_BLOCKED)
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            if bundle.namelist() != ["intake-handoff.json"]:
                raise ValueError("unexpected files")
            if bundle.getinfo("intake-handoff.json").file_size > MAX_HANDOFF_BYTES:
                raise ValueError("oversize handoff")
            handoff = json.loads(bundle.read("intake-handoff.json"))
    except (ValueError, KeyError, RuntimeError, zipfile.BadZipFile) as exc:
        raise RecoveryError("Invalid immutable topology handoff artifact.", EXIT_BLOCKED) from exc
    if not isinstance(handoff, dict) or handoff.get("approval") != approval:
        raise RecoveryError("Comment approval differs from its immutable workflow handoff.", EXIT_REFUSED)
    return handoff


def recoveryComment(result):
    receipt = result["receipt"]
    lines = [
        RECORD_HEADER,
        "",
        f"The batch file for this intake was not available, so a maintainer-authorized recovery built "
        f"`{result['batchPath']}` from this issue and the upstream SKILL.md blobs below.",
        "This is a **reconstruction, not the original batch bytes**. It does not waive maintainer authorization, "
        "L4 human review, evidence-ready or evidence-approved, schema validation, or the single promotion PR.",
        "",
        f"- Recovered by: `{receipt['authorization']['recoveredBy']}` ({receipt['authorization']['permission']})",
        f"- Rationale: {sanitizeLog(receipt['authorization']['rationale'])}",
        f"- Reconstructed batch SHA-256: `{receipt['reconstructedBatch']['sha256']}`",
        "",
        "| Skill | Source | SHA-256 | Origin |",
        "|---|---|---|---|",
    ]
    for source in receipt["sources"]:
        lines.append(f"| `{source['skillId']}` | {source['url']} | `{source['sha256']}` | {source['origin']} |")
    lines += ["", f"<!-- gaia-intake-recovery-record {encodeRecord(result['batch'], receipt)} -->"]
    text = "\n".join(lines) + "\n"
    if len(text) > MAX_RECORD_COMMENT:
        raise RecoveryError(
            f"The recovery record is {len(text)} characters, over the {MAX_RECORD_COMMENT} comment budget; "
            "split the intake before recovering it.",
            EXIT_BLOCKED,
        )
    return text


# ---------------------------------------------------------------------------
# materialize (evidence job)
# ---------------------------------------------------------------------------


def materialize(issueNumber, commentsDoc, repoRoot, fetcher, verifier=None):
    """Write the recorded reconstruction into the promotion branch; no-op when none was recorded.

    `commentsDoc` is `gh issue view --json body,comments`. The latest bot pointer must
    match a successful authenticated workflow's immutable artifact. The artifact
    authorizes the exact batch and issue revision; comment text cannot grant approval.
    """
    verifier = verifier or verifyHandoff
    approvals = []
    for body in botComments(commentsDoc, APPROVAL_MARKER, APPROVAL_HEADER):
        if len(APPROVAL_MARKER.findall(body)) != 1:
            raise RecoveryError("Ambiguous topology approval markers; re-run topology approval.", EXIT_REFUSED)
        try:
            approvals.append(json.loads(APPROVAL_MARKER.search(body).group(1)))
        except ValueError:
            continue
    approvals = [item for item in approvals if isinstance(item, dict) and item.get("issue") == int(issueNumber)]
    if not approvals:
        raise RecoveryError("No authenticated topology approval was found. Re-run the topology approval.", EXIT_REFUSED)
    approval = approvals[-1]
    handoff = verifier(approval)
    body = commentsDoc.get("body") if isinstance(commentsDoc, dict) else None
    if not isinstance(body, str) or sha256Hex(body) != approval.get("issueBodySha256"):
        raise RecoveryError(
            "The intake issue body changed (or could not be read) after approval. "
            "Re-run the topology approval so a maintainer approves the current body.", EXIT_STALE)
    batchId = approval.get("batchId")
    if not isinstance(batchId, str) or not BATCH_ID_RE.fullmatch(batchId):
        raise RecoveryError("The topology approval has an unsafe batch id.", EXIT_BLOCKED)
    if approval.get("batchPath") != batchRelPath(batchId):
        raise RecoveryError("The topology approval has a noncanonical batch path.", EXIT_BLOCKED)
    batchPath = os.path.join(repoRoot, batchRelPath(batchId))
    if os.path.exists(batchPath):
        with open(batchPath, encoding="utf-8") as handle:
            onDisk = json.load(handle)
        if sha256Hex(canonicalJson(onDisk)) != approval.get("batchSha256"):
            raise RecoveryError("The checked-out batch differs from the topology-approved batch.", EXIT_STALE)
        requireLowercaseNamedContributors(onDisk)
    bound = approval.get("recovery") or None
    if not isinstance(bound, dict):
        if not os.path.exists(batchPath):
            raise RecoveryError("The topology-approved batch is absent; explicit recovery is required.", EXIT_BLOCKED)
        return {"status": "no-recovery", "files": []}
    decoded = handoff.get("record")
    if (not isinstance(decoded, dict) or not isinstance(decoded.get("batch"), dict)
            or not isinstance(decoded.get("receipt"), dict)
            or recordIdentityDigest(decoded["batch"], decoded["receipt"]) != bound.get("recordDigest")):
        raise RecoveryError(
            "The topology handoff lacks its approved recovery record; re-run recovery.",
            EXIT_STALE,
        )
    batch, receipt = decoded["batch"], decoded["receipt"]
    requireLowercaseNamedContributors(batch)
    if receipt.get("issue") != int(issueNumber) or receipt.get("reconstruction") is not True:
        raise RecoveryError("The recovery record does not belong to this intake issue.", EXIT_BLOCKED)
    if receipt.get("reconstructedBatch", {}).get("sha256") != sha256Hex(canonicalJson(batch)) or bound.get("batchSha256") != receipt["reconstructedBatch"]["sha256"]:
        raise RecoveryError("The recovery record's batch does not match its recorded digest.", EXIT_BLOCKED)
    if approval.get("batchSha256") != receipt["reconstructedBatch"]["sha256"] or bound.get("issueBodySha256") != approval.get("issueBodySha256"):
        raise RecoveryError("The recovery binding disagrees with the approved batch or issue revision.", EXIT_BLOCKED)
    batchId = batch.get("batchId")
    if batchId != approval.get("batchId") or not isinstance(batchId, str) or not BATCH_ID_RE.fullmatch(batchId):
        raise RecoveryError("The recovery record has an unsafe batch id.", EXIT_BLOCKED)

    batchPath = os.path.join(repoRoot, batchRelPath(batchId))
    receiptPath = os.path.join(repoRoot, receiptRelPath(issueNumber))
    urls = {item["skillId"]: item["url"] for item in receipt.get("sources", [])}
    current = verifySources(urls, fetcher)
    if {item["skillId"]: item["sha256"] for item in current} != {item["skillId"]: item["sha256"] for item in receipt["sources"]}:
        raise RecoveryError(
            "Stale recovery: upstream SKILL.md bytes changed since the recovery was recorded. Re-run recovery.",
            EXIT_STALE,
        )

    batchPresent = os.path.exists(batchPath)
    if os.path.exists(receiptPath):
        with open(receiptPath, encoding="utf-8") as handle:
            existingReceipt = json.load(handle)
        if canonicalJson(existingReceipt) != canonicalJson(receipt):
            raise RecoveryError("The checked-out recovery receipt conflicts with the authenticated handoff.", EXIT_STALE)
    files = []
    for path, value in ((batchPath, batch), (receiptPath, receipt)):
        if not os.path.exists(path):
            writeAtomic(path, serialize(value))
            files.append(os.path.relpath(path, repoRoot).replace(os.sep, "/"))
    return {"status": "recovery-already-present" if batchPresent else "materialized", "files": files}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def loadJson(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def report(error):
    print(f"ERROR: {error}", file=sys.stderr)
    for line in error.lines:
        print(line, file=sys.stderr)


def main(argv=None, fetcher=None):
    fetcher = fetcher or defaultFetcher
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    rec = sub.add_parser("recover", help="build and write a reconstruction for an absent batch")
    rec.add_argument("--issue-json", required=True, help="`gh issue view --json number,state,labels,body,author` output")
    rec.add_argument("--actor", required=True)
    rec.add_argument("--permission", required=True, help="the actor's repository permission")
    rec.add_argument("--rationale", required=True)
    rec.add_argument("--facts", default="", help="JSON {skillId: {description,name,type,prerequisites,skillFileUrl}}")
    rec.add_argument("--comments-json", default=None, help="`gh issue view --json comments` output, to skip duplicate records")
    rec.add_argument("--repo-root", default=".")
    rec.add_argument("--comment-out", default=None, help="write the recovery record comment here")
    rec.add_argument("--no-fetch", action="store_true", help="refuse: sources must be fetched and hashed")

    pay = sub.add_parser("payload", help="print the topology approval payload JSON")
    pay.add_argument("--batch", required=True)
    pay.add_argument("--issue", required=True)
    pay.add_argument("--approver", required=True)
    pay.add_argument("--repo-root", default=".")
    pay.add_argument("--issue-json", help="current issue snapshot for revision binding")
    pay.add_argument("--handoff-out", help="write the immutable Actions artifact")

    mat = sub.add_parser("materialize", help="carry a recorded reconstruction into the promotion branch")
    mat.add_argument("--issue", required=True)
    mat.add_argument("--comments-json", required=True)
    mat.add_argument("--repo-root", default=".")
    mat.add_argument("--files-out", default=None, help="write the list of files to add, one per line")

    revision = sub.add_parser("check-revision", help="verify the current issue matches its approval event")
    revision.add_argument("--issue-json", required=True)
    revision.add_argument("--transition", choices=("topology", "evidence"), required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "check-revision":
            verifyIssueRevision(loadJson(args.issue_json), os.environ.get("GITHUB_EVENT_NAME"),
                loadJson(os.environ["GITHUB_EVENT_PATH"]), args.transition,
                os.environ.get("ISSUE_BODY_SHA256"))
            return EXIT_OK
        if args.command == "payload":
            body = loadJson(args.issue_json)["body"] if args.issue_json else None
            if args.handoff_out and body is None:
                raise RecoveryError("An issue snapshot is required for the handoff.", EXIT_REFUSED)
            payload = buildApprovalPayload(args.batch, args.issue, args.approver, args.repo_root,
                issueBody=body, runId=os.environ.get("GITHUB_RUN_ID"),
                runAttempt=os.environ.get("GITHUB_RUN_ATTEMPT"), headSha=os.environ.get("GITHUB_SHA"))
            if args.handoff_out:
                receiptFile = os.path.join(args.repo_root, receiptRelPath(args.issue))
                record = None
                if os.path.exists(receiptFile):
                    record = {"batch": loadJson(os.path.join(args.repo_root, args.batch)), "receipt": loadJson(receiptFile)}
                writeAtomic(args.handoff_out, serialize({"approval": json.loads(payload), "record": record}))
            print(payload)
            return EXIT_OK
        if args.command == "recover":
            if args.no_fetch:
                raise RecoveryError("Sources must be fetched and hashed; --no-fetch is not a recovery mode.", EXIT_REFUSED)
            comments = loadJson(args.comments_json) if args.comments_json else None
            result = recover(
                loadJson(args.issue_json), args.actor, args.permission, args.rationale, args.facts,
                args.repo_root, fetcher, comments,
            )
            print(f"Recovery {result['status']}: {result['batchPath']} (reconstruction, not original bytes)")
            print(f"Receipt: {result['receiptPath']}")
            if args.comment_out:
                if result["alreadyRecorded"]:
                    writeAtomic(args.comment_out, "")
                    print("An identical recovery record is already on the issue; no new comment needed.")
                else:
                    writeAtomic(args.comment_out, recoveryComment(result))
            return EXIT_OK
        result = materialize(args.issue, loadJson(args.comments_json), args.repo_root, fetcher)
        print(f"Recovery materialization: {result['status']}")
        if args.files_out:
            writeAtomic(args.files_out, "".join(f"{path}\n" for path in result["files"]))
        return EXIT_OK
    except RecoveryError as exc:
        report(exc)
        return exc.code
    except (OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
