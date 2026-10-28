import copy
import os
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from challenge_case_support import (
    BUILDKWARGS, CASE, SYNTHETICTOKENS, SyntheticVerifiedResolver, addCase, corrupt, makeCase, stubReceiptDir, tamper,
)
from gaia_cli import challengeAdmission as admission
from gaia_cli import challengeProjection as projection
from gaia_cli.committedChallenges import (
    Collected, collect, lifecyclePorts, rejectCollisions, reviewsBySubject,
)
from gaia_cli.steward.challenge_receipts import CONFIG_ENV

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"


def heldCase(tmp_path, built=False):
    root, directory = makeCase(tmp_path)
    if built:
        admission.buildRequest(root, CASE, **BUILDKWARGS)
    return root, directory


# --- live state ---------------------------------------------------------------------

def test_live_artifacts_are_unavailable_empty_and_mirrored_identically():
    for name, expected in (("index", projection.emptyIndex()), ("reviews", projection.emptyReviews())):
        graph, api = (REPO / relative for relative in projection.FILES[name])
        if not graph.exists():
            pytest.skip("run `gaia dev docs` first")
        assert graph.read_bytes() == api.read_bytes()
        assert json.loads(graph.read_text()) == expected
    assert json.loads((REPO / projection.FILES["index"][0]).read_text())["sourceStatus"] == "unavailable"


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


# --- unavailable; never verified-empty -------------------------------------------------

def test_absent_or_empty_ledger_is_unavailable_and_needs_no_gh(tmp_path):
    def noGh(_):
        raise AssertionError("no bundle claims admission: gh must not be consulted")
    assert collect(tmp_path, which=noGh).sourceStatus == "unavailable"
    (tmp_path / admission.EVIDENCE).mkdir(parents=True)
    found = collect(tmp_path, which=noGh, shallow=noGh)
    assert found.sourceStatus == "unavailable" and projection.buildIndex(tmp_path, collected=found) == projection.emptyIndex()


def test_held_cases_never_make_the_index_verified(tmp_path):
    root, _ = heldCase(tmp_path, built=True)
    found = collect(root)
    assert found.sourceStatus == "unavailable" and found.reviews
    assert projection.buildIndex(root, collected=found) == projection.emptyIndex()


# --- held reviews --------------------------------------------------------------------

def test_held_review_is_a_separate_labelled_record_and_never_contested(tmp_path):
    root, directory = heldCase(tmp_path, built=True)
    found = collect(root)
    assert found.admitted == {} and lifecyclePorts(found) is None  # nothing reaches trustLifecycle
    document = projection.buildReviews(root, collected=found)
    [review] = document["reviews"]
    assert document["contract"] == "gaia-challenge-review/v1" and review["status"] == "admission-held"
    assert review["held"]["reason"] == "trusted-issuer-unavailable"
    assert review["assessment"]["independence"] == "declared-unauthenticated"
    assert not re.search("contested", json.dumps(document), re.IGNORECASE)
    assert projection.validateReviews(document) == []
    assert set(reviewsBySubject(found)) == {review["subjectId"]}


def test_contested_guard_covers_only_system_fields():
    base = projection.buildReviews(REPO, collected=Collected(True, {}, {}, (), ()))
    review = {"contract": "gaia-challenge-review/v1", "status": "admission-held", "claim": "graft is uncontested at callers",
              "held": {"reason": "trusted-issuer-unavailable", "explanation": "x"}, "disclosure": "d"}
    assert projection.validateReview(review) == []  # challenger-authored text is data
    for field in ("status", "disclosure"):
        assert projection.validateReview({**review, field: "Contested"})
    assert projection.validateReview({**review, "held": {"reason": "trusted-issuer-unavailable", "explanation": "contested"}})
    assert projection.validateReview({**review, "contested": True})
    assert projection.validateReview({**review, "held": {"reason": "invented", "explanation": "x"}})
    bad = copy.deepcopy(base)
    bad["reviews"] = [{**review, "status": "contested"}]
    assert projection.validateReviews(bad)


def test_one_bad_review_makes_the_reviews_file_fail_closed(tmp_path):
    root, _ = heldCase(tmp_path, built=True)
    found = collect(root)
    poisoned = Collected(True, {}, {}, ({**found.reviews[0], "status": "contested"},), ())
    assert projection.buildReviews(root, collected=poisoned) == projection.emptyReviews()
    assert reviewsBySubject(poisoned) == {}  # the named-index channel uses the same validator


# --- tamper / collisions / fail closed -------------------------------------------------

@pytest.mark.parametrize("target", ["meta-verification.json", "receipt.json", "lead.json"])
def test_tampered_bundle_item_is_rejected_and_never_published(tmp_path, target):
    root, directory = heldCase(tmp_path, built=True)
    if target == "meta-verification.json":
        tamper(directory, target)
    else:
        data = json.loads((directory / target).read_text())
        if target == "receipt.json":
            data["result"] = "contradicted"
        else:
            data["capability"]["claim"] += " (edited)"
        (directory / target).write_text(json.dumps(data))
    found = collect(root)
    assert found.reviews == () and [item["caseId"] for item in found.rejected] == [CASE]
    assert projection.buildReviews(root, collected=found)["reviews"] == []


def test_tampered_artifact_bytes_are_rejected(tmp_path):
    root, directory = heldCase(tmp_path, built=True)
    (directory / "artifacts" / "target.txt").write_bytes(b"altered\n")
    assert collect(root).rejected


def test_one_bad_case_does_not_hide_a_good_one_but_is_itself_dropped(tmp_path):
    root, _ = heldCase(tmp_path, built=True)
    _, otherDir = makeCase(tmp_path / "second", "second-case")
    shutil.copytree(otherDir, root / admission.EVIDENCE / "second-case")
    corrupt(root / admission.EVIDENCE / "second-case")
    found = collect(root)
    assert [r["caseId"] for r in found.reviews] == [CASE] and [r["caseId"] for r in found.rejected] == ["second-case"]


def test_cases_sharing_a_challenge_id_are_both_rejected_not_first_wins(tmp_path):
    """Reviewer attack a2: identical drafts give identical challenge ids; neither case may admit."""
    root, directory = heldCase(tmp_path, built=True)
    addCase(root, tmp_path / "b", "case-b")
    found = collect(root, resolver=SyntheticVerifiedResolver(directory))
    assert sorted(r["caseId"] for r in found.rejected) == ["case-b", CASE]
    assert found.admitted == {} and found.reviews == ()
    assert "challenge id" in found.rejected[0]["reason"]


def test_receipt_id_collisions_are_detected_directly():
    from types import SimpleNamespace as NS
    reports = {"a": NS(challengeId="x", receiptId="r1"), "b": NS(challengeId="y", receiptId="r1"),
               "c": NS(challengeId="z", receiptId="r3")}
    assert sorted(rejectCollisions(reports)) == ["a", "b"]


def test_a_case_that_claims_a_receipt_needs_gh_and_full_history(tmp_path):
    """Machine-dependent bytes are a hard build error only when a bundle claims admission."""
    root, directory = heldCase(tmp_path, built=True)
    stubReceiptDir(directory)
    with pytest.raises(admission.BuildEnvironmentError, match="gh CLI"):
        collect(root, which=lambda _: None)
    with pytest.raises(admission.BuildEnvironmentError, match="shallow"):
        collect(root, which=lambda _: "/usr/bin/gh", shallow=lambda _: True)
    found = collect(root, which=lambda _: "/usr/bin/gh", shallow=lambda _: False)
    assert found.admitted == {} and found.reviews[0]["held"]["reason"] == "receipt-unverifiable"


def test_generate_named_index_fails_the_build_when_tooling_is_missing(tmp_path, monkeypatch, capsys):
    module = loadGenerator()
    root, directory = heldCase(tmp_path / "case", built=True)
    stubReceiptDir(directory)
    monkeypatch.setattr(module, "collect_challenges", lambda _repo: collect(root, which=lambda _: None))
    monkeypatch.setattr(sys, "argv", ["generateNamedIndex.py", "--out", str(tmp_path / "x.json")])
    if not (REPO / "registry/gaia.json").exists():
        pytest.skip("Class P not generated")
    with pytest.raises(SystemExit) as exc:
        module.main()
    assert exc.value.code == 1 and "gh CLI" in capsys.readouterr().out


def test_environment_trust_pin_overrides_disable_publication(tmp_path, monkeypatch, capsys):
    root, _ = heldCase(tmp_path, built=True)
    monkeypatch.setenv(CONFIG_ENV["workflowBlobSha"], "a" * 40)
    found = collect(root)
    assert found.disabled and found.sourceStatus == "unavailable" and found.reviews == ()
    assert projection.buildReviews(root, collected=found) == projection.emptyReviews()
    assert reviewsBySubject(found) == {} and lifecyclePorts(found) is None
    assert "overrides" in capsys.readouterr().err


def test_broken_event_log_is_loud_and_held_not_silently_dropped(tmp_path, capsys):
    root, directory = heldCase(tmp_path, built=True)
    admission.admit(root, CASE, online=False)
    lines = (directory / "events.jsonl").read_text().splitlines()  # an edit is visible once a later line chains to it
    (directory / "events.jsonl").write_text("\n".join([lines[0].replace("admission-request-built", "x"), lines[1]]) + "\n")
    found = collect(root)
    assert found.reviews[0]["held"]["reason"] == "event-log-broken" and not found.rejected
    assert "event log is broken" in capsys.readouterr().err


# --- admitted path (synthetic resolver; production never accepts it) ------------------

def admittedCollected(tmp_path, material=False):
    root, directory = makeCase(tmp_path)
    admission.buildRequest(root, CASE, materialToOrigin=material, **BUILDKWARGS)
    return root, collect(root, resolver=SyntheticVerifiedResolver(directory))


def test_admitted_challenge_feeds_the_lifecycle_channel(tmp_path):
    root, found = admittedCollected(tmp_path, material=True)
    assert found.sourceStatus == "verified" and found.reviews == ()
    document = projection.buildIndex(root, collected=found)
    [subject] = document["subjects"]
    assert document["sourceStatus"] == "verified" and subject["materialOriginContested"] is True
    assert subject["consequence"] == {"kind": "unavailable"} and "pendingProposal" not in subject
    assert subject["challenges"][0]["status"] == "verified-pending"
    assert subject["genericSkillRef"] == json.loads(
        (root / admission.EVIDENCE / CASE / "transcript.json").read_text())["subject"]["genericSkillId"]
    assert projection.validate(document) == []


def test_unprovable_admission_fails_the_whole_file_and_logs(tmp_path, capsys):
    root, found = admittedCollected(tmp_path)
    broken = Collected(**{**found.__dict__, "resolver": None})
    assert projection.buildIndex(root, collected=broken) == projection.emptyIndex()
    assert "failed closed" in capsys.readouterr().err
    assert projection.buildIndex(root, collected=Collected(**{**found.__dict__, "genericRefs": {}})) == projection.emptyIndex()


def test_validator_rejects_reserved_status_proposals_and_bad_consequences():
    assert projection.validate({**projection.emptyIndex(), "sourceStatus": "verified-empty"})
    assert projection.validate({**projection.emptyIndex(), "subjects": [{"x": 1}]})
    subject = {"subjectId": "a/b", "genericSkillRef": "g", "materialOriginContested": False,
               "consequence": {"kind": "proposed-decision"}, "challenges": [{"x": 1}]}
    verified = {**projection.emptyIndex(), "sourceStatus": "verified"}
    assert any("consequence" in e for e in projection.validate({**verified, "subjects": [subject]}))
    subject = {**subject, "consequence": {"kind": "current-baseline", "proposedTm": 12}}
    assert any("proposed values" in e for e in projection.validate({**verified, "subjects": [subject]}))


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
    found = collect(root)
    plain = write(module, tmp_path, "plain.json")
    with_bundle = write(module, tmp_path, "bundle.json", lifecycle_ports=lifecyclePorts(found),
                        challenge_reviews=reviewsBySubject(found))
    assert plain != with_bundle  # the held review travels on its own channel
    entry = json.loads(with_bundle)["buckets"]["g"][0]
    assert entry["challengeReviews"][0]["status"] == "admission-held" and "trustLifecycle" not in entry
    assert stripChannels(json.loads(plain)) == stripChannels(json.loads(with_bundle))


def test_contributor_supplied_channels_are_never_published(tmp_path):
    module = loadGenerator()
    entries = sampleEntries()
    entries["g"][0]["challengeReviews"] = [{"forged": True}]
    entries["g"][0]["trustLifecycle"] = {"forged": True}
    out = tmp_path / "forged.json"
    module.write_index(entries, [], {}, str(out), "2026-10-29")
    entry = json.loads(out.read_text())["buckets"]["g"][0]
    assert "challengeReviews" not in entry and "trustLifecycle" not in entry


def treeDigest(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(Path(root).rglob("*")) if p.is_file()}


@pytest.mark.timeout(600)
@pytest.mark.slow
def test_ledger_leaderboard_and_badges_are_byte_identical_with_and_without_channels(tmp_path, monkeypatch):
    """Dynamic parity: the real generators on fixture indexes with and without both channels."""
    index = REPO / "registry/named-skills.json"
    if not index.exists() or not (REPO / "registry/gaia.json").exists():
        pytest.skip("Class P not generated")
    env = {**os.environ, "PYTHONPATH": str(REPO / "src") + os.pathsep + str(SCRIPTS)}

    def run(code, *args):  # subprocess: the generators reconfigure stdout and patch module globals
        done = subprocess.run([sys.executable, "-c", code, *map(str, args)], capture_output=True, text=True, env=env, cwd=REPO)
        assert done.returncode == 0, done.stderr[-800:]

    root, _ = heldCase(tmp_path / "case", built=True)
    review = collect(root).reviews[0]
    base = json.loads(index.read_text())
    plain, channeled = copy.deepcopy(base), copy.deepcopy(base)
    for group in channeled["buckets"].values():
        for entry in group:
            entry["challengeReviews"] = [review]
            entry["trustLifecycle"] = {"contract": "gaia-trust-lifecycle/v1", "challenges": []}
    assert plain != channeled
    ledgerOut = {}
    for label, data in (("plain", plain), ("channeled", channeled)):
        tree = tmp_path / label
        (tree / "registry/schema").mkdir(parents=True)
        (tree / "docs/graph/ledger").mkdir(parents=True)
        (tree / "docs/graph/named").mkdir(parents=True)
        (tree / "registry/named-skills.json").write_text(json.dumps(data))
        (tree / "docs/graph/named/index.json").write_text(json.dumps(data))
        shutil.copy(REPO / "registry/schema/meta.json", tree / "registry/schema/meta.json")
        shutil.copy(REPO / "pyproject.toml", tree / "pyproject.toml")
        ledgerPath = tree / "docs/graph/ledger/data.json"  # reads nodes/named/skill-trees, never the index
        run("import sys, generateLeaderboardData as g; sys.argv=['x','--out',sys.argv[1]]; sys.exit(g.main())", ledgerPath)
        ledgerOut[label] = ledgerPath.read_bytes()
        run("import sys; from pathlib import Path; import generateBadges as g; g.NAMED_JSON=Path(sys.argv[1]); sys.exit(g.main(['--out-dir', sys.argv[2]]))",
            tree / "docs/graph/named/index.json", tree / "badges")
    for label in ("plain", "channeled"):  # same ledger bytes in, so only the index differs between API runs
        tree = tmp_path / label
        (tree / "docs/graph/ledger/data.json").write_bytes(ledgerOut["plain"])
        run("import sys; from pathlib import Path; import buildApiProjection as b; b.ROOT=Path(sys.argv[1]); sys.exit(b.run(Path(sys.argv[2])))",
            tree, tree / "api")
    stamp = lambda raw: {k: v for k, v in json.loads(raw).items() if k != "generatedAt"}  # wall-clock stamp only
    assert stamp(ledgerOut["plain"]) == stamp(ledgerOut["channeled"])
    for name in ("leaderboard.json", "skills/index.json", "search-index.json", "health.json"):
        assert (tmp_path / "plain/api" / name).read_bytes() == (tmp_path / "channeled/api" / name).read_bytes(), name
    assert treeDigest(tmp_path / "plain/badges") == treeDigest(tmp_path / "channeled/badges")


def test_numeric_generators_take_no_challenge_input():
    numeric = ["generateLeaderboardData.py", "buildApiProjection.py", "generateBadges.py", "generateProfilePages.py"]
    for name in numeric:
        text = (SCRIPTS / name).read_text(encoding="utf-8")
        for token in ("frontier-challenges", "committedChallenges", "challengeProjection", "challengeAdmission"):
            assert token not in text, f"{name} must not depend on {token}"


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
        found = collect(root) if patched else collect(tmp_path / "nowhere")
        monkeypatch.setattr(module, "collect_challenges", lambda _repo, found=found: found)
        out = tmp_path / f"{label}.json"
        monkeypatch.setattr(sys, "argv", ["generateNamedIndex.py", "--out", str(out)])
        module.main()
        outputs.append(json.loads(out.read_text()))
    plain, bundled = outputs
    assert stripChannels(plain) == stripChannels(bundled)
    subjects = [e["id"] for group in bundled["buckets"].values() for e in group if "challengeReviews" in e]
    assert subjects == ["trailhq/graft"]  # registry/named/trailhq/graft.md exists in this repo
