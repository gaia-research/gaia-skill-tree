import copy
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from challenge_case_support import (
    BUILDKWARGS, CASE, SYNTHETICTOKENS, SyntheticVerifiedResolver, availableProbe, corrupt, makeCase, tamper,
    unavailableProbe,
)
from gaia_cli import challengeAdmission as admission
from gaia_cli import challengeProjection as projection
from gaia_cli.committedChallenges import collect, lifecyclePorts, reviewsBySubject

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"


def heldCase(tmp_path, built=False):
    root, directory = makeCase(tmp_path)
    if built:
        admission.buildRequest(root, CASE, **BUILDKWARGS)
    return root, directory


def collectHeld(root):
    return collect(root, probe=availableProbe)


# --- live state ---------------------------------------------------------------------

def test_live_projection_is_unavailable_with_empty_collections_and_mirrors_are_identical():
    graph, api = REPO / projection.GRAPHPATH, REPO / projection.APIPATH
    if not graph.exists():
        pytest.skip("run `gaia dev docs` first")
    document = json.loads(graph.read_text())
    assert graph.read_bytes() == api.read_bytes()
    assert document == {"contract": "gaia-challenge-projection/v1", "sourceStatus": "unavailable",
                        "subjects": [], "reviews": []}
    assert projection.build(REPO)["sourceStatus"] == "unavailable"  # no committed case ledger


def test_no_synthetic_data_under_docs():
    """Synthetic fixtures live only under tests/fixtures; nothing fixture-looking is ever published."""
    done = subprocess.run(["git", "-C", str(REPO), "grep", "-l", "-i", "-F", *sum((["-e", t] for t in SYNTHETICTOKENS), []),
                           "--", "docs"], capture_output=True, text=True)
    if done.returncode not in (0, 1):
        pytest.skip("git grep unavailable")
    assert done.stdout.strip() == ""
    base = REPO / admission.EVIDENCE
    if base.is_dir():  # a real ledger must never hold fixture cases either
        assert not [p for p in base.iterdir() if "synthetic" in p.name.lower()]


# --- unavailable / verified-empty ----------------------------------------------------

def test_absent_ledger_is_unavailable(tmp_path):
    found = collect(tmp_path, probe=availableProbe)
    assert found.sourceStatus == "unavailable" and not found.reviews
    assert projection.build(tmp_path, collected=found) == projection.emptyDocument()


def test_unverifiable_issuer_path_hides_everything(tmp_path):
    root, _ = heldCase(tmp_path)
    found = collect(root, probe=unavailableProbe)
    assert found.reviews and found.sourceStatus == "unavailable"
    assert projection.build(root, collected=found) == projection.emptyDocument()
    assert reviewsBySubject(found) == {}


def test_empty_ledger_with_verifiable_issuer_is_verified_empty(tmp_path):
    (tmp_path / admission.EVIDENCE).mkdir(parents=True)
    document = projection.build(tmp_path, collected=collect(tmp_path, probe=availableProbe))
    assert document == projection.emptyDocument("verified-empty")


# --- held reviews --------------------------------------------------------------------

def test_held_review_is_a_labelled_review_and_never_contested(tmp_path):
    root, directory = heldCase(tmp_path, built=True)
    found = collectHeld(root)
    assert found.admitted == {} and lifecyclePorts(found) is None  # nothing reaches trustLifecycle
    document = projection.build(root, collected=found)
    assert document["sourceStatus"] == "verified-empty" and document["subjects"] == []
    [review] = document["reviews"]
    assert review["contract"] == "gaia-challenge-review/v1" and review["status"] == "admission-held"
    assert review["held"]["reason"] == "trusted-issuer-unavailable"
    assert review["assessment"]["independence"] == "declared-unauthenticated"
    assert not re.search("contested", json.dumps(document), re.IGNORECASE)
    assert projection.validate(document) == []
    assert set(reviewsBySubject(found)) == {review["subjectId"]}


def test_a_review_labelled_contested_fails_the_whole_file():
    document = projection.emptyDocument("verified-empty")
    document["reviews"] = [{"contract": "gaia-challenge-review/v1", "status": "admission-held", "note": "Contested claim"}]
    assert any("contested" in error for error in projection.validate(document))


# --- tamper / fail closed ------------------------------------------------------------

@pytest.mark.parametrize("target", ["meta-verification.json", "receipt.json", "lead.json"])
def test_tampered_bundle_item_is_rejected_and_never_published(tmp_path, target):
    root, directory = heldCase(tmp_path, built=True)
    tamper(directory, target) if target == "meta-verification.json" else None
    if target == "receipt.json":
        data = json.loads((directory / target).read_text())
        data["result"] = "contradicted"
        (directory / target).write_text(json.dumps(data))
    if target == "lead.json":
        data = json.loads((directory / target).read_text())
        data["capability"]["claim"] += " (edited)"
        (directory / target).write_text(json.dumps(data))
    found = collectHeld(root)
    assert found.reviews == () and [item["caseId"] for item in found.rejected] == [CASE]
    assert projection.build(root, collected=found)["reviews"] == []


def test_tampered_artifact_bytes_are_rejected(tmp_path):
    root, directory = heldCase(tmp_path, built=True)
    (directory / "artifacts" / "target.txt").write_bytes(b"altered\n")
    assert collectHeld(root).rejected


def test_one_bad_case_does_not_hide_a_good_one_but_is_itself_dropped(tmp_path):
    root, _ = heldCase(tmp_path, built=True)
    other, otherDir = makeCase(tmp_path / "second", "second-case")
    shutil.copytree(otherDir, root / admission.EVIDENCE / "second-case")
    corrupt(root / admission.EVIDENCE / "second-case")
    found = collectHeld(root)
    assert [r["caseId"] for r in found.reviews] == [CASE] and [r["caseId"] for r in found.rejected] == ["second-case"]


# --- admitted path (synthetic resolver; production never accepts it) ------------------

def admittedCollected(tmp_path, material=False):
    root, directory = makeCase(tmp_path)
    admission.buildRequest(root, CASE, materialToOrigin=material, **BUILDKWARGS)
    return root, collect(root, resolver=SyntheticVerifiedResolver(directory), probe=availableProbe)


def test_admitted_challenge_feeds_the_lifecycle_channel(tmp_path):
    root, found = admittedCollected(tmp_path, material=True)
    assert found.sourceStatus == "verified" and found.reviews == ()
    document = projection.build(root, collected=found)
    [subject] = document["subjects"]
    assert subject["materialOriginContested"] is True
    assert subject["consequence"] == {"kind": "unavailable"} and subject["pendingProposal"] is None
    assert subject["challenges"][0]["status"] == "verified-pending"
    assert projection.validate(document) == []


def test_pending_proposal_is_only_a_pointer(tmp_path):
    root, found = admittedCollected(tmp_path)
    subject = found.admitted and next(iter(found.admitted))
    ok = projection.build(root, collected=found, pending={subject: {"id": "ADJ-1", "path": "founder/ledger.json"}})
    assert ok["subjects"][0]["pendingProposal"] == {"id": "ADJ-1", "path": "founder/ledger.json"}
    for bad in ({"id": "ADJ-1", "path": "x", "tm": 99}, {"id": "ADJ-1", "path": "../x"}, {"id": "", "path": "x"}):
        assert projection.build(root, collected=found, pending={subject: bad}) == projection.emptyDocument()


def test_unprovable_admission_fails_the_whole_file(tmp_path):
    root, found = admittedCollected(tmp_path)
    broken = type(found)(**{**found.__dict__, "resolver": None})
    assert projection.build(root, collected=broken) == projection.emptyDocument()
    assert projection.build(root, collected=type(found)(**{**found.__dict__, "genericRefs": {}})) == projection.emptyDocument()


def test_validator_rejects_proposals_unavailable_payloads_and_bad_consequences():
    document = projection.emptyDocument()
    document["reviews"] = [{"contract": "gaia-challenge-review/v1", "status": "admission-held"}]
    assert projection.validate(document)
    subject = {"subjectId": "a/b", "genericSkillRef": "g", "materialOriginContested": False,
               "consequence": {"kind": "proposed-decision"}, "pendingProposal": None, "challenges": [{"x": 1}]}
    assert any("consequence" in e for e in projection.validate({**projection.emptyDocument("verified"), "subjects": [subject]}))
    subject = {**subject, "consequence": {"kind": "current-baseline", "proposedTm": 12}}
    assert any("proposed values" in e for e in projection.validate({**projection.emptyDocument("verified"), "subjects": [subject]}))


# --- parity: no number ever depends on a challenge bundle ------------------------------

def loadGenerator():
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location("generateNamedIndexUnderTest", SCRIPTS / "generateNamedIndex.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stripChannels(value):
    if isinstance(value, dict):
        return {k: stripChannels(v) for k, v in value.items() if k not in {"challengeReviews", "trustLifecycle"}}
    if isinstance(value, list):
        return [stripChannels(v) for v in value]
    return value


def sampleEntries():
    return {"g": [{"id": "trailhq/graft", "genericSkillRef": "g", "level": "3★", "trustMagnitude": 72,
                   "overallTrustGrade": "B", "origin": True, "contributor": "trailhq"}],
            "h": [{"id": "other/skill", "genericSkillRef": "h", "level": "2★", "trustMagnitude": 30,
                   "origin": False, "contributor": "other"}]}


def write(module, tmp_path, name, **kwargs):
    out = tmp_path / name
    module.write_index(copy.deepcopy(sampleEntries()), [], {}, str(out), "2026-10-29", **kwargs)
    return out.read_bytes()


def test_named_index_numbers_are_byte_identical_with_and_without_bundles(tmp_path):
    module = loadGenerator()
    root, _ = heldCase(tmp_path / "case", built=True)
    found = collectHeld(root)
    plain = write(module, tmp_path, "plain.json")
    with_bundle = write(module, tmp_path, "bundle.json", lifecycle_ports=lifecyclePorts(found),
                        challenge_reviews=reviewsBySubject(found))
    assert plain != with_bundle  # the held review travels on its own channel
    assert json.loads(with_bundle)["buckets"]["g"][0]["challengeReviews"][0]["status"] == "admission-held"
    assert "trustLifecycle" not in json.loads(with_bundle)["buckets"]["g"][0]
    assert stripChannels(json.loads(plain)) == stripChannels(json.loads(with_bundle))
    assert json.dumps(stripChannels(json.loads(plain)), sort_keys=True) == json.dumps(stripChannels(json.loads(with_bundle)), sort_keys=True)


def test_contributor_supplied_review_channel_is_never_published(tmp_path):
    module = loadGenerator()
    entries = sampleEntries()
    entries["g"][0]["challengeReviews"] = [{"forged": True}]
    entries["g"][0]["trustLifecycle"] = {"forged": True}
    out = tmp_path / "forged.json"
    module.write_index(entries, [], {}, str(out), "2026-10-29")
    entry = json.loads(out.read_text())["buckets"]["g"][0]
    assert "challengeReviews" not in entry and "trustLifecycle" not in entry


def test_numeric_generators_take_no_challenge_input():
    """Leaderboard, ledger, badges, API and Trust Magnitude never read bundles or either channel."""
    numeric = ["generateLeaderboardData.py", "buildApiProjection.py", "generateBadges.py", "generateProfilePages.py"]
    for name in numeric:
        text = (SCRIPTS / name).read_text(encoding="utf-8")
        for token in ("frontier-challenges", "challengeReviews", "committedChallenges", "challengeProjection", "challengeAdmission"):
            assert token not in text, f"{name} must not depend on {token}"
    for module in ("trustMagnitude", "taxonomy", "evidenceLifecycle"):
        path = REPO / "src/gaia_cli" / f"{module}.py"
        if path.exists():
            assert "committedChallenges" not in path.read_text(encoding="utf-8")


@pytest.mark.timeout(600)
@pytest.mark.slow
def test_real_registry_named_index_is_unchanged_by_a_bundle(tmp_path, monkeypatch):
    """End to end on the real registry: a held bundle adds only challengeReviews on its subject."""
    if not (REPO / "registry/gaia.json").exists():
        pytest.skip("Class P not generated")
    module = loadGenerator()
    root, _ = heldCase(tmp_path / "case", built=True)
    outputs = []
    for label, patched in (("plain", False), ("bundle", True)):
        if patched:
            monkeypatch.setattr(module, "collect_challenges", lambda _repo: collectHeld(root))
        else:
            monkeypatch.setattr(module, "collect_challenges", lambda _repo: collect(tmp_path / "nowhere"))
        out = tmp_path / f"{label}.json"
        monkeypatch.setattr(sys, "argv", ["generateNamedIndex.py", "--out", str(out)])
        module.main()
        outputs.append(json.loads(out.read_text()))
    plain, bundled = outputs
    assert stripChannels(plain) == stripChannels(bundled)
    subjects = [e["id"] for group in bundled["buckets"].values() for e in group if "challengeReviews" in e]
    assert subjects == ["trailhq/graft"]  # registry/named/trailhq/graft.md exists in this repo
