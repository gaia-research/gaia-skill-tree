"""Tests for adjudication approvals tooling and founder rulings mapping (EPIC #2189)."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ADJ_TOOLS = ROOT / "founder/reports/yggdrasil-iv-october-2026/adjudication/tools"
APPROVALS_PATH = ROOT / "founder/reports/yggdrasil-iv-october-2026/adjudication/approvals.json"

sys.path.insert(0, str(ADJ_TOOLS))
import adjcore as ac  # noqa: E402
import build_adjudication as ba  # noqa: E402


class TestFallbackOriginExactFloatTM:
    """Requirement 1: _FallbackOrigin must use exact float(tm), not round(tm, 4)."""

    def test_close_unequal_tms_do_not_tie(self):
        """Two candidates with TMs differing only past the 4th decimal place must not tie."""
        pool = {
            "cand-b": {
                "genericSkillRef": "bucket-test",
                "contributor": "author-b",
                "status": "named",
                "level": "3★",
                "overallTrustGrade": "B",
                "trustMagnitude": 100.12349,
            },
            "cand-a": {
                "genericSkillRef": "bucket-test",
                "contributor": "author-a",
                "status": "named",
                "level": "3★",
                "overallTrustGrade": "B",
                "trustMagnitude": 100.12341,
            },
        }
        holders = ac._FallbackOrigin.bucketHolders("bucket-test", pool)
        # Exact comparison means cand-b strictly wins with higher float TM
        assert holders == frozenset({"cand-b"})

    def test_exact_equal_tms_share_origin(self):
        """Exact equal float TMs must share Origin per founder ruling."""
        pool = {
            "cand-a": {
                "genericSkillRef": "bucket-test",
                "contributor": "author-a",
                "status": "named",
                "level": "3★",
                "overallTrustGrade": "B",
                "trustMagnitude": 100.123456,
            },
            "cand-b": {
                "genericSkillRef": "bucket-test",
                "contributor": "author-b",
                "status": "named",
                "level": "3★",
                "overallTrustGrade": "B",
                "trustMagnitude": 100.123456,
            },
        }
        holders = ac._FallbackOrigin.bucketHolders("bucket-test", pool)
        assert holders == frozenset({"cand-a", "cand-b"})

    def test_higher_level_wins_regardless_of_tm(self):
        """Published level is higher precedence than TM in merit ordering."""
        pool = {
            "cand-low-level-high-tm": {
                "genericSkillRef": "bucket-test",
                "contributor": "author-a",
                "status": "named",
                "level": "2★",
                "overallTrustGrade": "B",
                "trustMagnitude": 500.0,
            },
            "cand-high-level-low-tm": {
                "genericSkillRef": "bucket-test",
                "contributor": "author-b",
                "status": "named",
                "level": "3★",
                "overallTrustGrade": "B",
                "trustMagnitude": 10.0,
            },
        }
        holders = ac._FallbackOrigin.bucketHolders("bucket-test", pool)
        assert holders == frozenset({"cand-high-level-low-tm"})


class TestApprovalsSchemaAndRulings:
    """Requirement 2: Validate approvals.json schema and required founder rulings."""

    @pytest.fixture
    def approvals_data(self):
        assert APPROVALS_PATH.exists(), f"Missing {APPROVALS_PATH}"
        return json.loads(APPROVALS_PATH.read_text())

    def test_approvals_structure(self, approvals_data):
        assert approvals_data.get("$schema") == "adjudication-approvals-v1"
        assert "metadata" in approvals_data
        assert "decisions" in approvals_data
        assert len(approvals_data["decisions"]) >= 15

    def test_required_rulings_present(self, approvals_data):
        decisions = approvals_data["decisions"]
        dec_map = {d.get("decision"): d for d in decisions}
        aliases = {d.get("alias"): d for d in decisions if d.get("alias")}

        # FD-7 through FD-18 coverage
        assert "FD-7" in dec_map
        assert dec_map["FD-7"]["status"] == "approved"
        assert dec_map["FD-7"]["action"] == "align_clamp"
        assert "mattpocock/personal" in dec_map["FD-7"].get("constraints", {}).get("exemptTargets", [])

        assert "FD-8" in dec_map
        assert dec_map["FD-8"]["status"] == "approved"
        assert "heygen-com/hyperframes" in dec_map["FD-8"]["targets"]

        assert "FD-9" in dec_map
        assert dec_map["FD-9"]["status"] == "held"
        assert "mattpocock/skills" in dec_map["FD-9"]["targets"]

        assert "FD-10" in dec_map
        assert dec_map["FD-10"]["status"] == "approved"
        assert set(dec_map["FD-10"]["targets"]) == {
            "addy-osmani/code-simplification",
            "ayghri/i-have-adhd",
            "dietrichgebert/ponytail",
            "vercel-labs/vercel-react-best-practices",
        }

        # r2-graphify
        assert "r2-graphify" in dec_map
        assert dec_map["r2-graphify"]["status"] == "approved"
        assert "safishamsi/graphify" in dec_map["r2-graphify"]["targets"]

        assert "FD-11" in dec_map
        assert dec_map["FD-11"]["status"] == "approved"
        assert "google-deepmind/workflow-skill-creator" in dec_map["FD-11"]["targets"]

        assert "FD-12" in dec_map
        assert dec_map["FD-12"]["status"] == "approved"
        assert "latent-spaces/brag" in dec_map["FD-12"]["targets"]

        assert "FD-13" in dec_map
        assert dec_map["FD-13"]["status"] == "approved"
        assert "xquik-dev/hermes-tweet" in dec_map["FD-13"]["targets"]

        assert "FD-14" in dec_map
        assert dec_map["FD-14"]["status"] == "held"
        assert set(dec_map["FD-14"]["targets"]) == {
            "laravel/upgrade-laravel-v13",
            "martin-stepanoski/nielsen-heuristics-audit",
        }

        assert "FD-15" in dec_map
        assert dec_map["FD-15"]["status"] == "approved"
        assert "obra/superpowers" in dec_map["FD-15"]["targets"]

        assert "FD-16" in dec_map
        assert dec_map["FD-16"]["status"] == "superseded"
        assert dec_map["FD-16"]["action"] == "automatic_origin"

        assert "FD-17" in dec_map
        assert dec_map["FD-17"]["status"] == "proposed"

        assert "r3-fd17-leftovers" in dec_map
        assert dec_map["r3-fd17-leftovers"]["status"] == "approved"

        assert "FD-18" in dec_map
        assert dec_map["FD-18"]["status"] == "proposed"

        assert "r2-general-video" in dec_map
        assert dec_map["r2-general-video"]["status"] == "approved"
        assert "heygen-com/general-video" in dec_map["r2-general-video"]["targets"]

        # ADJ-126
        adj126 = dec_map.get("ADJ-126") or aliases.get("r3-adj-judgement")
        assert adj126 is not None
        assert adj126["status"] == "approved"
        assert "panniantong/agent-reach" in adj126["targets"]

        # r4-peer-review-rows
        assert "r4-peer-review-rows" in dec_map
        assert dec_map["r4-peer-review-rows"]["status"] == "held"

        # November holds #2261, #2262, #2263
        h2261 = dec_map.get("november-hold-2261") or aliases.get("r3-structural")
        assert h2261 is not None
        assert h2261["status"] == "deferred"
        assert h2261.get("issue") == 2261

        h2262 = dec_map.get("november-hold-2262") or aliases.get("r3-adj-evidence")
        assert h2262 is not None
        assert h2262["status"] == "deferred"
        assert h2262.get("issue") == 2262
        assert set(h2262.get("candidate_ids", [])) == {"ADJ-090", "ADJ-152", "ADJ-179"}

        h2263 = dec_map.get("november-hold-2263") or aliases.get("sibling-cap-deferral")
        assert h2263 is not None
        assert h2263["status"] == "deferred"
        assert h2263.get("issue") == 2263


@pytest.mark.slow
class TestCandidateApprovalsWiring:
    """Requirement 2 & 3: Candidates receive deterministic approval/status mapping."""

    @pytest.fixture(scope="class")
    def rendered_ledger(self):
        c = ba.buildCtx()
        cands = ba.build(c)
        doc = ba.ledgerDoc(c, cands)
        return doc, {cd["target"]: cd for cd in cands}, {cd["id"]: cd for cd in cands}

    def test_total_counts(self, rendered_ledger):
        doc, by_tgt, by_id = rendered_ledger
        cnts = doc["counts"]
        assert cnts["candidates"] == 180
        assert cnts["approved"] == 18
        assert cnts["superseded"] == 88
        assert cnts["proposed"] == 62
        assert cnts["held"] == 6
        assert cnts["deferred"] == 6
        assert sum(cnts["byStatus"].values()) == 180

    def test_key_approved_targets(self, rendered_ledger):
        _, by_tgt, _ = rendered_ledger
        assert by_tgt["safishamsi/graphify"]["status"] == "approved"
        assert by_tgt["safishamsi/graphify"]["approved"]["action"] == "rule_change_keep_5star"

        assert by_tgt["google-deepmind/workflow-skill-creator"]["status"] == "approved"
        assert by_tgt["google-deepmind/workflow-skill-creator"]["approved"]["action"] == "promote_to_named"

        assert by_tgt["latent-spaces/brag"]["status"] == "approved"
        assert by_tgt["latent-spaces/brag"]["approved"]["action"] == "raise_to_4star"

        assert by_tgt["obra/superpowers"]["status"] == "approved"
        assert by_tgt["obra/superpowers"]["approved"]["action"] == "regenerate_apex_cache"

        assert by_tgt["panniantong/agent-reach"]["status"] == "approved"
        assert by_tgt["panniantong/agent-reach"]["approved"]["action"] == "re_derive_evidence"

        assert by_tgt["heygen-com/general-video"]["status"] == "approved"
        assert by_tgt["heygen-com/general-video"]["approved"]["action"] == "freeze"

        assert by_tgt["heygen-com/hyperframes"]["status"] == "approved"
        assert by_tgt["heygen-com/hyperframes"]["approved"]["action"] == "freeze_dropped_components"

    def test_key_held_and_deferred_targets(self, rendered_ledger):
        _, by_tgt, by_id = rendered_ledger
        # Held targets
        assert by_tgt["mattpocock/personal"]["status"] == "held"
        assert by_tgt["mattpocock/personal"]["approved"] is None

        assert by_tgt["mattpocock/skills"]["status"] == "held"
        assert by_tgt["mattpocock/skills"]["approved"] is None

        assert by_tgt["laravel/upgrade-laravel-v13"]["status"] == "held"
        assert by_tgt["martin-stepanoski/nielsen-heuristics-audit"]["status"] == "held"

        # Deferred targets (issue #2262)
        assert by_id["ADJ-090"]["status"] == "deferred"
        assert by_id["ADJ-090"]["decision"]["issue"] == 2262

        assert by_id["ADJ-152"]["status"] == "deferred"
        assert by_id["ADJ-152"]["decision"]["issue"] == 2262

        assert by_id["ADJ-179"]["status"] == "deferred"
        assert by_id["ADJ-179"]["decision"]["issue"] == 2262

    def test_superseded_origin_candidates(self, rendered_ledger):
        _, _, by_id = rendered_ledger
        # Candidates in packet FD-16 without individual rulings are superseded by automatic Origin
        superseded = [cd for cd in by_id.values() if cd["status"] == "superseded"]
        assert len(superseded) == 88
        for cd in superseded:
            assert cd["requiredDecision"]["packet"] == "FD-16"
            assert cd["decision"]["action"] == "automatic_origin"


@pytest.mark.slow
class TestFrozenRecordsImmutability:
    """Requirement 2: Never recommend mutations on frozen records.

    Marked slow: it rebuilds the whole adjudication context (9-20s locally), and
    the fast tier's ``--timeout=30`` hard-kills an xdist worker under CI load
    ("node down: Not properly terminated"). It still runs in ``gaia dev test all``.
    """

    def test_frozen_records_do_not_recommend_option_d(self):
        c = ba.buildCtx()
        cands = ba.build(c)
        by_tgt = {cd["target"]: cd for cd in cands}

        # mattpocock/personal is a D6 candidate but frozen
        mp = by_tgt["mattpocock/personal"]
        assert mp.get("frozen") is True
        prop = mp["proposed"]
        assert prop.get("frozen") is True
        assert prop.get("mutationProhibited") is True
        assert "D-calibrate-stored-level-to-ceiling" not in prop.get("optionOutcomes", {})

        # heygen-com/general-video is also frozen
        gv = by_tgt["heygen-com/general-video"]
        assert gv.get("frozen") is True
        assert "D-calibrate-stored-level-to-ceiling" not in gv["proposed"].get("optionOutcomes", {})

        # heygen-com/hyperframes is ruled freeze under FD-8
        hf = by_tgt["heygen-com/hyperframes"]
        assert hf["proposed"]["kind"] == "frozen"
        assert hf["proposed"]["mutationProhibited"] is True

        # Non-frozen D6 candidate DOES have option D
        for tgt, cd in by_tgt.items():
            if tgt not in ("mattpocock/personal", "heygen-com/general-video") and cd["target"] in c.d6:
                assert "D-calibrate-stored-level-to-ceiling" in cd["proposed"]["optionOutcomes"]
                break


@pytest.mark.slow
class TestTempdirBuildAndCheck:
    """Requirement 3: Verify build_adjudication.py runs and passes byte-check in a tempdir."""

    def test_tempdir_render_and_check(self, tmp_path):
        build_script = str(ADJ_TOOLS / "build_adjudication.py")

        # 1. Run build to tempdir
        res_build = subprocess.run(
            [sys.executable, build_script, "--out-dir", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        assert res_build.returncode == 0, f"Build failed: {res_build.stderr}"

        # 2. Check generated files exist
        assert (tmp_path / "ledger.json").exists()
        assert (tmp_path / "LEDGER.md").exists()
        assert (tmp_path / "DECISIONS.md").exists()

        # 3. Verify ledger.json content
        ledger = json.loads((tmp_path / "ledger.json").read_text())
        assert ledger["counts"]["candidates"] == 180
        assert ledger["counts"]["approved"] == 18

        # 4. Run --check on the tempdir (must succeed with 0 drift)
        res_check = subprocess.run(
            [sys.executable, build_script, "--check", "--out-dir", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        assert res_check.returncode == 0, f"Check failed: {res_check.stderr}"
        assert "byte-identical rebuild" in res_check.stdout


class TestFrozenLocksInAdjudication:
    """A frozen skill's standing is its locked TM/grade, never a recomputation.

    The 49.9 suite cap (#2378) moved the recomputed grade of 12 frozen heygen-com skills
    (locked B -> recomputed C), which put them in the D6 ceiling-clamp set and added 12
    candidates for records nobody may touch. The adjudication tools must derive state the
    way the index generator and Origin do.
    """

    @staticmethod
    def registry(**extra):
        frozen = {"id": "x/frozen", "level": "3★", "status": "named", "frozen": True,
                  "trustMagnitude": 50.0, "overallTrustGrade": "B", "evidence": [], **extra}
        live = {"id": "x/live", "level": "3★", "status": "named", "evidence": [],
                "trustMagnitude": 50.0, "overallTrustGrade": "B"}
        return ac.Registry({}, {"x/frozen": frozen, "x/live": live})

    def test_a_frozen_skill_derives_its_lock_and_a_live_one_recomputes(self):
        reg = self.registry()
        assert ac.derive(reg.named["x/frozen"], reg)[:2] == (50.0, "B")
        # Same stamp, no evidence: the live skill is recomputed (0 TM, ungraded), not trusted.
        assert ac.derive(reg.named["x/live"], reg)[:2] == (0.0, "ungraded")

    def test_a_frozen_skill_is_not_in_the_ceiling_clamp_set_after_a_refresh(self):
        reg = self.registry()
        state = ac.snapshot(reg)["named"]
        assert state["x/frozen"]["grade"] == "B" and state["x/frozen"]["ceilingN"] == 3
        assert state["x/frozen"]["storedN"] <= state["x/frozen"]["ceilingN"]
        assert state["x/live"]["ceilingN"] == 1 and state["x/live"]["storedN"] > state["x/live"]["ceilingN"]

    def test_a_skill_in_a_frozen_suite_derives_its_lock(self):
        reg = self.registry(suiteComponents=["x/member"])
        reg.named["x/member"] = {"id": "x/member", "level": "3★", "status": "named", "suiteRef": "x/frozen",
                                 "evidence": [], "trustMagnitude": 50.0, "overallTrustGrade": "B"}
        assert ac.derive(reg.named["x/member"], reg)[:2] == (50.0, "B")
