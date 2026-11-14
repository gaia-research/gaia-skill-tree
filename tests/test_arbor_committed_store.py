"""Doctrine invariants over the committed Arbor store.

`tests/test_arbor.py` proves the contracts on synthetic fixtures. This file
replays the real `registry/arbor` sources and asserts what the declaration-first
doctrine promises about them, so admitting declarations can never quietly turn
into claiming measurements:

* an un-interpreted claim or edge projects `expert-declared`, and nothing else;
* a declared edge is a hypothesis and never counts as evaluated coverage;
* the Hell-Heaven lens stays absent until an acceptance source exists;
* replay never alters an immutable source.

The store is copied to a temporary root first. Since #2441 the committed runtime
and edge projections follow only the behavioural identity of each pinned
subject, so they are compared byte-for-byte with a fresh replay as well, and
every seeded subject must carry a pin and a verified instruction baseline.
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import pytest

from gaia_cli.arbor import (
    ArborError,
    DECLARATION_SCHEMA,
    EDGE_DECLARATION_SCHEMA,
    EDGE_INTERPRETATION_SCHEMA,
    EDGE_OBSERVATION_SCHEMA,
    HH_ACCEPTANCE_SCHEMA,
    INTERPRETATION_SCHEMA,
    allSourceRecords,
    canonicalSkillPath,
    currentEndpointMatches,
    pairKey,
    readJson,
    replay,
)

REPO = Path(__file__).parents[1]
GOVERNED_SUPPORT = {
    "benchmark-confirmed",
    "benchmark-qualified",
    "benchmark-revised",
    "inconclusive",
}


def subjects(sources: dict) -> set[str]:
    ids = {record["skill"]["id"] for record in sources[DECLARATION_SCHEMA].values()}
    for record in sources[EDGE_DECLARATION_SCHEMA].values():
        ids.update(endpoint["id"] for endpoint in record["pair"].values())
    ids.update(record["subject"]["id"] for record in sources[HH_ACCEPTANCE_SCHEMA].values())
    return ids


def fileDigests(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*.json"))
    }


@pytest.fixture(scope="module")
def store(tmp_path_factory):
    """Replay the committed sources in an isolated copy of the store."""

    root = tmp_path_factory.mktemp("committed-arbor")
    shutil.copytree(REPO / "registry" / "arbor", root / "registry" / "arbor")
    committedGenerated = {
        **fileDigests(root / "registry" / "arbor" / "runtime"),
        "edges.json": hashlib.sha256(
            (root / "registry" / "arbor" / "edges.json").read_bytes()
        ).hexdigest(),
    }
    committed = allSourceRecords(REPO)
    for skillId in sorted(subjects(committed)):
        try:
            source = canonicalSkillPath(skillId, REPO)
        except ArborError:
            # A subject whose canonical record was later removed is immutable
            # history; replay must still succeed without it.
            continue
        target = root / source.relative_to(REPO)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)

    arbor = root / "registry" / "arbor"
    before = fileDigests(arbor / "sources")
    committedProfiles = fileDigests(arbor / "profiles")
    replay(root)
    return {
        "root": root,
        "arbor": arbor,
        "sources": allSourceRecords(root),
        "sourceDigestsBefore": before,
        "committedProfiles": committedProfiles,
        "committedGenerated": committedGenerated,
    }


def runtimes(store: dict) -> list[dict]:
    return [readJson(path) for path in sorted((store["arbor"] / "runtime").rglob("*.json"))]


def test_replay_leaves_every_immutable_source_untouched(store):
    assert store["sourceDigestsBefore"], "the committed Arbor store has no sources"
    assert fileDigests(store["arbor"] / "sources") == store["sourceDigestsBefore"]


def test_committed_profiles_match_a_fresh_replay(store):
    # Profiles are built from immutable sources only, so unlike the runtime and
    # edge projections they must be byte-identical to a fresh replay.
    assert fileDigests(store["arbor"] / "profiles") == store["committedProfiles"]


def test_claims_without_a_governed_interpretation_stay_expert_declared(store):
    interpreted = {
        (record["target"]["declarationSha256"], record["target"]["claimId"])
        for record in store["sources"][INTERPRETATION_SCHEMA].values()
    }
    seen = 0
    for path in sorted((store["arbor"] / "profiles").rglob("*.json")):
        for claim in readJson(path)["claims"]:
            seen += 1
            target = (claim["declarationSource"], claim["id"])
            if target in interpreted:
                assert claim["support"] in GOVERNED_SUPPORT
                assert claim["interpretationSource"] is not None
            else:
                assert claim["support"] == "expert-declared", claim["id"]
                assert claim["interpretationSource"] is None, claim["id"]
    declared = sum(len(record["claims"]) for record in store["sources"][DECLARATION_SCHEMA].values())
    assert seen == declared


def test_declared_edges_are_hypotheses_and_never_count_as_evaluated(store):
    index = readJson(store["arbor"] / "edges.json")
    observedPairs = {
        pairKey(record["pair"])
        for record in store["sources"][EDGE_OBSERVATION_SCHEMA].values()
    }
    interpreted = {
        (record["target"]["declarationSha256"], record["target"]["claimId"])
        for record in store["sources"][EDGE_INTERPRETATION_SCHEMA].values()
    }
    assert index["coverage"]["absenceMeaning"] == "not-evaluated"
    assert index["coverage"]["pairsEvaluated"] == len(observedPairs)
    declared = sum(
        len(record["claims"]) for record in store["sources"][EDGE_DECLARATION_SCHEMA].values()
    )
    assert len(index["edges"]) == declared
    for edge in index["edges"]:
        target = (edge["target"]["declarationSha256"], edge["target"]["claimId"])
        assert edge["structuralOverlap"] == "not-evaluated"
        if target not in interpreted:
            assert edge["support"] == "expert-declared", edge["edgeKey"]
            assert edge["interpretationSource"] is None, edge["edgeKey"]


def test_hell_heaven_lens_is_absent_without_an_acceptance_source(store):
    accepted = {
        (record["subject"]["id"], record["subject"]["contentSha256"])
        for record in store["sources"][HH_ACCEPTANCE_SCHEMA].values()
    }
    records = runtimes(store)
    assert records, "replay produced no runtime aggregate"
    for runtime in records:
        subject = (runtime["subject"]["id"], runtime["subject"]["contentSha256"])
        lens = runtime["lenses"]["hellHeaven"]
        # No accepted HH payload contract exists, so a result is never projected.
        assert lens["result"] is None
        if subject not in accepted:
            assert lens["status"] == "absent-no-accepted-record"
            assert lens["sourceDigest"] is None


def test_every_edge_endpoint_sees_its_interaction_and_no_other(store):
    index = readJson(store["arbor"] / "edges.json")
    expected: dict[tuple[str, str], set[str]] = {}
    for edge in index["edges"]:
        for endpoint in edge["pair"].values():
            expected.setdefault((endpoint["id"], endpoint["contentSha256"]), set()).add(edge["edgeKey"])
    bySubject = {
        (runtime["subject"]["id"], runtime["subject"]["contentSha256"]): runtime
        for runtime in runtimes(store)
    }
    # An endpoint with no runtime aggregate would hide its interactions entirely.
    assert set(expected) <= set(bySubject)
    for subject, runtime in bySubject.items():
        lens = runtime["lenses"]["interactions"]
        keys = {edge["edgeKey"] for edge in lens["edges"]}
        wanted = expected.get(subject, set())
        pinHolds = currentEndpointMatches(runtime["subject"], store["root"])
        if wanted and pinHolds:
            # The lens may not silently drop a relation whose pin still holds.
            assert lens["status"] == "present", subject
            assert keys == wanted
        elif wanted:
            assert lens["status"] == "absent-subject-version-mismatch", subject
            assert keys == set()
        else:
            assert lens["status"] == "absent-no-accepted-record", subject
            assert keys == set()


def test_committed_runtime_and_edges_match_a_fresh_replay(store):
    fresh = {
        **fileDigests(store["arbor"] / "runtime"),
        "edges.json": hashlib.sha256((store["arbor"] / "edges.json").read_bytes()).hexdigest(),
    }
    assert fresh == store["committedGenerated"]


def test_every_subject_is_pinned_and_seeded_subjects_have_a_baseline(store):
    pins = {path.parent.relative_to(store["arbor"] / "pins").as_posix() for path in (store["arbor"] / "pins").rglob("*.json")}
    assert subjects(store["sources"]) <= pins
    for runtime in runtimes(store):
        applicability = runtime["applicability"]
        if runtime["subject"]["id"] != "obra/receiving-code-review":
            # Every Arbor I seed subject cites the exact upstream bytes it was read from.
            assert applicability["instruction"]["status"] == "baseline-observed", runtime["subject"]
