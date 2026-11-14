"""Regression matrix for Arbor behavioural identity and projection drift (#2441).

Every case runs against a synthetic store: no network, no committed registry.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from gaia_cli.arbor import (
    ArborError,
    EDGE_DECLARATION_SCHEMA,
    behavioralDigest,
    buildArborProjection,
    checkStore,
    contentDigest,
    importSource,
    pinPath,
    pinSubject,
    readJson,
    recordObservation,
    replay,
    runtimePath,
    upstreamCheck,
)

CONTRACTS = Path(__file__).parents[1] / "registry" / "arbor" / "contracts"
BASE_COMMIT = "a" * 40
LATER_COMMIT = "b" * 40
SOURCE_V1 = b"# Skill\nStep 1: read the code.\n"
SOURCE_V2 = b"# Skill\nStep 1: rewrite everything.\n"


def namedRecord(
    skillId: str,
    *,
    level: str = "2★",
    link: str | None = None,
    description: str = "Reviews code before it merges.",
    timeline: list | None = None,
    evidence: list | None = None,
    extra: str = "",
    body: str = "## Usage\nRun it.\n",
) -> bytes:
    owner, slug = skillId.split("/")
    link = link or f"https://github.com/{owner}/skills/blob/main/{slug}/SKILL.md"
    timeline = timeline or [{"timestamp": "2026-06-01T00:00:00Z", "action": "named"}]
    evidence = evidence or [{"source": link, "type": "repo"}]
    lines = [
        "---",
        f"id: {skillId}",
        f"name: {slug.title()}",
        f"contributor: {owner}",
        "origin: false",
        "genericSkillRef: code-review",
        "status: named",
        f"level: {level}",
        f"description: {description}",
        "links:",
        f"  github: {link}",
        "upstream:",
        "  repo: x/y",
        "  version: 1.0.0",
        "  syncedAt: '2026-11-01T00:00:00Z'",
        "trustMagnitude: 36.0",
        "overallTrustGrade: C",
        "updatedAt: '2026-08-30'",
        "timeline:",
    ]
    for event in timeline:
        lines.append(f"- timestamp: '{event['timestamp']}'")
        lines.append(f"  action: {event['action']}")
    lines.append("evidence:")
    for item in evidence:
        lines.append(f"- source: {item['source']}")
        lines.append(f"  type: {item['type']}")
    if extra:
        lines.append(extra)
    lines.append("---")
    return ("\n".join(lines) + "\n" + body).encode()


def nodeRecord(skillId: str, **fields) -> bytes:
    record = {
        "id": skillId,
        "name": skillId.title(),
        "type": "basic",
        "description": "A generic capability.",
        "prerequisites": [],
        "derivatives": [],
        "evidence": [],
        "knownAgents": [],
        "status": "provisional",
        "createdAt": "2026-05-23",
        "updatedAt": "2026-06-21",
        "version": "0.1.0",
        "timeline": [],
    }
    record.update(fields)
    return (json.dumps(record, indent=2) + "\n").encode()


def store(tmpPath: Path) -> Path:
    root = tmpPath / "repo"
    shutil.copytree(CONTRACTS, root / "registry" / "arbor" / "contracts")
    return root


def write(root: Path, skillId: str, data: bytes) -> str:
    if "/" in skillId:
        owner, slug = skillId.split("/")
        path = root / "registry" / "named" / owner / f"{slug}.md"
    else:
        path = root / "registry" / "nodes" / "basic" / f"{skillId}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def declare(root: Path, tmpPath: Path, skillId: str, skillHash: str, declarationId: str = "d1") -> str:
    record = {
        "schema": "gaia.arbor-expert-declaration/v1",
        "declarationId": declarationId,
        "declaredAt": "2026-11-10T00:00:00Z",
        "skill": {"id": skillId, "contentSha256": skillHash},
        "claims": [
            {
                "id": "claim",
                "facet": "model-led",
                "conditions": "synthetic conditions",
                "rationale": "synthetic rationale",
                "authority": {"actor": "fixture", "basis": "fixture"},
            }
        ],
    }
    path = tmpPath / f"{declarationId}.json"
    path.write_text(json.dumps(record))
    return importSource(path, root)[1]


def declareEdge(root: Path, tmpPath: Path, left: tuple[str, str], right: tuple[str, str]) -> str:
    record = {
        "schema": EDGE_DECLARATION_SCHEMA,
        "declarationId": "edge",
        "declaredAt": "2026-11-10T00:00:00Z",
        "pair": {
            "from": {"id": left[0], "contentSha256": left[1]},
            "to": {"id": right[0], "contentSha256": right[1]},
        },
        "claims": [
            {
                "id": "edge-claim",
                "relation": "unlocks",
                "conditions": "synthetic",
                "rationale": "synthetic",
                "authority": {"actor": "fixture", "basis": "fixture"},
            }
        ],
    }
    path = tmpPath / "edge.json"
    path.write_text(json.dumps(record))
    return importSource(path, root)[1]


def runtime(root: Path, skillId: str, skillHash: str) -> dict:
    return readJson(runtimePath(root / "registry" / "arbor", skillId, skillHash))


def fakeUpstream(files: dict[tuple[str, str], bytes | None]):
    def fetch(repository, ref, path):
        return files.get((ref, path))

    return fetch


def resolveTo(commit: str):
    return lambda repository, ref: commit


# (1) and (2): timeline-only and trust-evidence-only edits ---------------------


@pytest.mark.parametrize(
    "edit",
    [
        {"timeline": [
            {"timestamp": "2026-06-01T00:00:00Z", "action": "named"},
            {"timestamp": "2026-11-11T00:00:00Z", "action": "rank_up"},
        ]},
        {"evidence": [
            {"source": "https://github.com/alice/skills/blob/main/review/SKILL.md", "type": "repo"},
            {"source": "https://example.com/review", "type": "blog"},
        ]},
        {"level": "3★"},
    ],
    ids=["timeline-only", "evidence-only", "level-only"],
)
def test_prestige_only_edit_keeps_knowledge_and_projection_bytes(tmp_path, edit):
    root = store(tmp_path)
    skillHash = write(root, "alice/review", namedRecord("alice/review"))
    declare(root, tmp_path, "alice/review", skillHash)
    replay(root)
    before = buildArborProjection(root)
    beforeFiles = {
        path: path.read_bytes() for path in (root / "registry" / "arbor").rglob("*.json")
    }

    newHash = write(root, "alice/review", namedRecord("alice/review", **edit))
    assert newHash != skillHash

    assert checkStore(root) == 2  # no replay needed: nothing generated changed
    assert buildArborProjection(root) == before
    replay(root)
    assert {
        path: path.read_bytes() for path in (root / "registry" / "arbor").rglob("*.json")
    } == beforeFiles
    applicability = runtime(root, "alice/review", skillHash)["applicability"]
    assert applicability["applicable"] is True
    assert applicability["canonical"] == "behavior-equivalent"


def test_upstream_sync_timestamp_is_not_behaviour_but_version_is():
    base = namedRecord("alice/review")
    assert behavioralDigest("alice/review", base) == behavioralDigest(
        "alice/review", base.replace(b"2026-11-01T00:00:00Z", b"2026-11-12T00:00:00Z")
    )
    assert behavioralDigest("alice/review", base) != behavioralDigest(
        "alice/review", base.replace(b"version: 1.0.0", b"version: 1.1.0")
    )


@pytest.mark.parametrize(
    "edit",
    [
        {"description": "Rewrites code instead of reviewing it."},
        {"body": "## Usage\nRun it twice.\n"},
        {"extra": "installable: false"},
    ],
    ids=["description", "body", "unknown-new-field-fails-closed"],
)
def test_behavioural_canonical_edit_invalidates_and_check_fails_closed(tmp_path, edit):
    root = store(tmp_path)
    skillHash = write(root, "alice/review", namedRecord("alice/review"))
    declare(root, tmp_path, "alice/review", skillHash)
    replay(root)
    profileBytes = {p: p.read_bytes() for p in (root / "registry" / "arbor" / "profiles").rglob("*.json")}

    write(root, "alice/review", namedRecord("alice/review", **edit))
    with pytest.raises(ArborError, match="stale"):
        checkStore(root)
    replay(root)
    assert checkStore(root) == 2
    applicability = runtime(root, "alice/review", skillHash)["applicability"]
    assert applicability == {**applicability, "applicable": False, "canonical": "behavior-changed"}
    # Historical declarations and profiles are never rebound to the new bytes.
    assert {p: p.read_bytes() for p in (root / "registry" / "arbor" / "profiles").rglob("*.json")} == profileBytes


# (3) upstream SKILL.md change behind a mutable link ---------------------------


def test_upstream_change_behind_mutable_link_is_recorded_and_fails_closed(tmp_path):
    root = store(tmp_path)
    skillHash = write(root, "alice/review", namedRecord("alice/review"))
    declare(root, tmp_path, "alice/review", skillHash)
    replay(root)
    assert runtime(root, "alice/review", skillHash)["applicability"]["instruction"]["status"] == "mutable-ref-unobserved"

    upstream = {(BASE_COMMIT, "review/SKILL.md"): SOURCE_V1, ("main", "review/SKILL.md"): SOURCE_V1}
    with pytest.raises(ArborError, match="not the cited"):
        recordObservation(root, "alice/review", skillHash, "baseline", BASE_COMMIT,
                          fetch=fakeUpstream(upstream), expectedSha256="0" * 64)
    recordObservation(root, "alice/review", skillHash, "baseline", BASE_COMMIT,
                      fetch=fakeUpstream(upstream),
                      expectedSha256=hashlib.sha256(SOURCE_V1).hexdigest(),
                      observedAt="2026-11-14T00:00:00Z")
    replay(root)
    assert checkStore(root) == 2
    status = runtime(root, "alice/review", skillHash)["applicability"]
    assert status["applicable"] is True
    assert status["instruction"] == {
        "status": "baseline-observed",
        "refKind": "mutable",
        "baselineSha256": hashlib.sha256(SOURCE_V1).hexdigest(),
    }

    # Unchanged upstream: report only, nothing written.
    report = upstreamCheck(root, record=True, fetch=fakeUpstream(upstream), resolve=resolveTo(BASE_COMMIT))
    assert [entry["status"] for entry in report] == ["unchanged"]
    assert "recorded" not in report[0]

    upstream[("main", "review/SKILL.md")] = SOURCE_V2
    report = upstreamCheck(root, record=False, fetch=fakeUpstream(upstream), resolve=resolveTo(LATER_COMMIT))
    assert [entry["status"] for entry in report] == ["changed"]
    assert checkStore(root) == 2  # report-only run wrote nothing

    upstreamCheck(root, record=True, fetch=fakeUpstream(upstream), resolve=resolveTo(LATER_COMMIT))
    with pytest.raises(ArborError, match="stale"):
        checkStore(root)
    replay(root)
    status = runtime(root, "alice/review", skillHash)["applicability"]
    assert status["applicable"] is False
    assert status["canonical"] == "behavior-equivalent"
    assert status["instruction"]["status"] == "instruction-changed"


def test_immutable_commit_link_needs_no_observation(tmp_path):
    root = store(tmp_path)
    link = f"https://github.com/alice/skills/blob/{BASE_COMMIT}/review/SKILL.md"
    skillHash = write(root, "alice/review", namedRecord("alice/review", link=link))
    declare(root, tmp_path, "alice/review", skillHash)
    replay(root)
    status = runtime(root, "alice/review", skillHash)["applicability"]
    assert status["applicable"] is True
    assert status["instruction"]["status"] == "immutable-ref"


# (4) canonical link change ----------------------------------------------------


def test_canonical_instruction_link_change_invalidates(tmp_path):
    root = store(tmp_path)
    skillHash = write(root, "alice/review", namedRecord("alice/review"))
    declare(root, tmp_path, "alice/review", skillHash)
    write(root, "alice/review", namedRecord(
        "alice/review", link="https://github.com/alice/skills/blob/main/review-v2/SKILL.md"
    ))
    replay(root)
    assert runtime(root, "alice/review", skillHash)["applicability"]["canonical"] == "behavior-changed"


# (5) missing upstream, missing canonical --------------------------------------


def test_unavailable_upstream_is_recorded_and_fails_closed(tmp_path):
    root = store(tmp_path)
    skillHash = write(root, "alice/review", namedRecord("alice/review"))
    declare(root, tmp_path, "alice/review", skillHash)
    upstream = {(BASE_COMMIT, "review/SKILL.md"): SOURCE_V1}
    with pytest.raises(ArborError, match="unavailable"):
        recordObservation(root, "alice/review", skillHash, "baseline", LATER_COMMIT,
                          fetch=fakeUpstream(upstream))
    recordObservation(root, "alice/review", skillHash, "baseline", BASE_COMMIT,
                      fetch=fakeUpstream(upstream))
    report = upstreamCheck(root, record=True, fetch=fakeUpstream(upstream))
    assert report[0]["status"] == "unavailable"
    replay(root)
    status = runtime(root, "alice/review", skillHash)["applicability"]
    assert status["applicable"] is False
    assert status["instruction"]["status"] == "instruction-unavailable"


def test_removed_canonical_skill_is_missing_and_inapplicable(tmp_path):
    root = store(tmp_path)
    skillHash = write(root, "alice/review", namedRecord("alice/review"))
    declare(root, tmp_path, "alice/review", skillHash)
    (root / "registry" / "named" / "alice" / "review.md").unlink()
    replay(root)
    status = runtime(root, "alice/review", skillHash)["applicability"]
    assert status["applicable"] is False
    assert status["canonical"] == "missing"


# (6) generic and named --------------------------------------------------------


def test_generic_node_prestige_edit_is_equivalent_and_behaviour_edit_is_not(tmp_path):
    root = store(tmp_path)
    skillHash = write(root, "code-review", nodeRecord("code-review"))
    declare(root, tmp_path, "code-review", skillHash)
    replay(root)
    write(root, "code-review", nodeRecord(
        "code-review", status="canonical", updatedAt="2026-11-14",
        evidence=[{"source": "x"}], derivatives=["alice/review"], knownAgents=["a"],
    ))
    assert checkStore(root) == 2
    write(root, "code-review", nodeRecord("code-review", prerequisites=["reading"]))
    with pytest.raises(ArborError, match="stale"):
        checkStore(root)
    replay(root)
    status = runtime(root, "code-review", skillHash)["applicability"]
    assert status["canonical"] == "behavior-changed"
    assert status["instruction"]["status"] == "no-instruction-link"


# (7) same-owner and cross-owner edges ------------------------------------------


@pytest.mark.parametrize(
    "right", ["alice/deploy", "bob/deploy", "code-review"],
    ids=["same-owner", "cross-owner", "named-to-generic"],
)
def test_edge_survives_prestige_edit_and_flips_on_behaviour_edit(tmp_path, right):
    root = store(tmp_path)
    leftHash = write(root, "alice/review", namedRecord("alice/review"))
    rightHash = write(root, right, namedRecord(right) if "/" in right else nodeRecord(right))
    declareEdge(root, tmp_path, ("alice/review", leftHash), (right, rightHash))
    replay(root)
    edges = readJson(root / "registry" / "arbor" / "edges.json")["edges"]
    assert edges[0]["pairApplicable"] is True

    if "/" in right:
        write(root, right, namedRecord(right, level="4★"))
    else:
        write(root, right, nodeRecord(right, status="canonical"))
    assert checkStore(root) == 1

    if "/" in right:
        write(root, right, namedRecord(right, description="Deploys without review."))
    else:
        write(root, right, nodeRecord(right, description="Something else."))
    with pytest.raises(ArborError, match="edge index is stale"):
        checkStore(root)
    replay(root)
    assert readJson(root / "registry" / "arbor" / "edges.json")["edges"][0]["pairApplicable"] is False
    assert runtime(root, "alice/review", leftHash)["lenses"]["interactions"]["edges"][0]["pairApplicable"] is False


# (8) legacy immutable records and replay ---------------------------------------


def test_legacy_unpinned_store_fails_check_until_backfilled_from_git(tmp_path):
    root = store(tmp_path)
    original = namedRecord("alice/review")
    skillHash = write(root, "alice/review", original)
    declarationDigest = declare(root, tmp_path, "alice/review", skillHash)
    replay(root)
    sourceBytes = {p: p.read_bytes() for p in (root / "registry" / "arbor" / "sources").rglob("*.json")}
    shutil.rmtree(root / "registry" / "arbor" / "pins")  # a pre-#2441 store
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "registry/named"], check=True)
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "v1"],
        check=True,
    )
    write(root, "alice/review", namedRecord("alice/review", level="3★"))

    with pytest.raises(ArborError, match="have no pin"):
        checkStore(root)
    with pytest.raises(ArborError, match="hash to"):
        pinSubject("alice/review", root, contentSha256=skillHash)  # current bytes differ
    path, created = pinSubject("alice/review", root, contentSha256=skillHash, fromGit="HEAD")
    assert created and path == pinPath(root / "registry" / "arbor", "alice/review", skillHash)
    replay(root)
    assert checkStore(root) == 2
    assert runtime(root, "alice/review", skillHash)["applicability"]["applicable"] is True
    # The immutable source and its digest are untouched by the backfill.
    assert {p: p.read_bytes() for p in (root / "registry" / "arbor" / "sources").rglob("*.json")} == sourceBytes
    assert (root / "registry" / "arbor" / "sources" / "declarations" / f"{declarationDigest}.json").is_file()


def test_forged_pin_for_current_bytes_is_rejected(tmp_path):
    root = store(tmp_path)
    skillHash = write(root, "alice/review", namedRecord("alice/review"))
    declare(root, tmp_path, "alice/review", skillHash)
    replay(root)
    path = pinPath(root / "registry" / "arbor", "alice/review", skillHash)
    record = readJson(path)
    record["identity"]["behavioralSha256"] = "0" * 64
    path.write_bytes(json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode() + b"\n")
    with pytest.raises(ArborError, match="does not match its pinned canonical bytes"):
        checkStore(root)


def test_observation_must_match_pinned_link(tmp_path):
    root = store(tmp_path)
    skillHash = write(root, "alice/review", namedRecord("alice/review"))
    declare(root, tmp_path, "alice/review", skillHash)
    path, record, _created = recordObservation(
        root, "alice/review", skillHash, "baseline", BASE_COMMIT,
        fetch=fakeUpstream({(BASE_COMMIT, "review/SKILL.md"): SOURCE_V1}),
        observedAt="2026-11-14T00:00:00Z",
    )
    record["instruction"]["path"] = "other/SKILL.md"
    path.unlink()
    forged = path.parent / f"{contentDigest(record)}.json"
    forged.write_bytes(json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode() + b"\n")
    with pytest.raises(ArborError, match="does not match the pinned link"):
        checkStore(root)
