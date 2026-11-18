"""Regression coverage for G7 social/proxy evidence policy repair (#2473)."""

from __future__ import annotations

import copy
import datetime as dt
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from gaia_cli.commands.dev.evidence import meta_evidence_command
from gaia_cli.curation.freshness import verifyPacketFreshness
from gaia_cli.steward import evidencediscovery
from gaia_cli.steward.knowledge_contracts import (
    EVIDENCE_POLICY_SURFACES,
    check_evidence_policy,
)
from gaia_cli.trustMagnitude import (
    computeArtifactScore,
    computeOverallTrustGrade,
    computeOverallTrustGradeFromSkill,
    computeTrustMagnitude,
)
from gaia_cli.validate import check_proxy_containment_policy
from tests.authindex import writeBootstrapIndex

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "evidence_policy_cases.json"
EVAL_NOW = dt.datetime(2026, 11, 17, 0, 0, 0, tzinfo=dt.timezone.utc)


def _load_cases() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _minimal_named_repo(
    tmp_path: Path, *, contributor: str = "acme", slug: str = "tool", suite_ref: str | None = None
) -> Path:
    (tmp_path / "registry" / "schema").mkdir(parents=True)
    (tmp_path / "registry" / "nodes" / "basic").mkdir(parents=True)
    (tmp_path / "registry" / "named" / contributor).mkdir(parents=True)
    for schema_name in ("meta.json", "skill.schema.json", "namedSkill.schema.json"):
        (tmp_path / "registry" / "schema" / schema_name).write_text(
            (ROOT / "registry" / "schema" / schema_name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    suite_line = f"suiteRef: {suite_ref}\n" if suite_ref else ""
    skill_md = (
        "---\n"
        f"id: {contributor}/{slug}\n"
        f"name: {slug}\n"
        f"contributor: {contributor}\n"
        "genericSkillRef: demo-generic\n"
        "status: named\n"
        "level: 2★\n"
        "description: Test skill\n"
        "links:\n"
        f"  github: https://github.com/{contributor}/{slug}/blob/main/SKILL.md\n"
        f"{suite_line}"
        "---\n"
    )
    (tmp_path / "registry" / "named" / contributor / f"{slug}.md").write_text(skill_md, encoding="utf-8")
    if suite_ref:
        sc, ss = suite_ref.split("/", 1)
        (tmp_path / "registry" / "named" / sc).mkdir(parents=True, exist_ok=True)
        (tmp_path / "registry" / "named" / sc / f"{ss}.md").write_text(
            "---\n"
            f"id: {suite_ref}\n"
            f"name: {ss}\n"
            f"contributor: {sc}\n"
            "genericSkillRef: demo-suite\n"
            "status: named\n"
            "level: 2★\n"
            "description: Suite root\n"
            "links:\n"
            f"  github: https://github.com/{suite_ref}/blob/main/README.md\n"
            "---\n",
            encoding="utf-8",
        )
    writeBootstrapIndex(tmp_path)
    return tmp_path


def _evidence_args(root: str, *, skill_id: str, source: str, **overrides) -> SimpleNamespace:
    base = dict(
        registry=root,
        skill_id=skill_id,
        source=source,
        index=None,
        evidence_type=None,
        trust=None,
        evaluator="mbtiongson1",
        date="2026-11-17",
        notes=None,
        stars=None,
        external_stars=None,
        views=None,
        citations=None,
        reviewers=None,
        commits=None,
        contributors=None,
        skill_count_in_repo=None,
        percentile=None,
        source_started_at=None,
        downloads=None,
        likes=None,
        comments=None,
        creator=None,
        creator_relation=None,
        relevance_note=None,
        benchmark_id=None,
        score=None,
        unit=None,
        run_at=None,
        provenance=None,
        attestor=None,
        dataset_hash=None,
        benchmark_input_hash=None,
        harness_url=None,
        no_build=True,
        cosign_with=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


# ---------------------------------------------------------------------------
# 1. Canonical metadata, mirrors, API projection, and policy guard
# ---------------------------------------------------------------------------


def test_canonical_and_mirrored_social_policy_values():
    paths = [
        ROOT / "registry" / "schema" / "meta.json",
        ROOT / "src" / "gaia_cli" / "data" / "registry" / "schema" / "meta.json",
        ROOT / "docs" / "schema" / "meta.json",
        ROOT / "docs" / "api" / "v1" / "evidence-types.json",
    ]
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        types = data.get("evidence", {}).get("types") or data.get("types") or []
        by_id = {entry["id"]: entry for entry in types}
        social = by_id["social-signal"]
        assert social["creatorMultipliers"]["sameAsAuthor"] == 1.0, path
        assert social["publishCooldownDays"] == 0, path
        assert "external creators" not in social["description"].lower(), path
        assert "external" in by_id["proxy-containment"]["description"].lower(), path


def test_evidence_policy_guard_passes_on_live_repo():
    assert check_evidence_policy(ROOT) == []


def test_evidence_policy_guard_rejects_reintroduced_ban_or_cooldown(tmp_path: Path):
    required = {
        "registry/schema/meta.json",
        "src/gaia_cli/data/registry/schema/meta.json",
        "docs/schema/meta.json",
        "docs/api/v1/evidence-types.json",
        "docs/agents/curation-authority-map.md",
        "docs/js/tm-config.js",
        "founder/handovers/done/G7_TRUST_TAXONOMY_RFC.md",
        *EVIDENCE_POLICY_SURFACES,
    }
    for rel in sorted(required):
        dest = tmp_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text((ROOT / rel).read_text(encoding="utf-8"), encoding="utf-8")

    assert check_evidence_policy(tmp_path) == []

    # Negative control 1: restoring sameAsAuthor: 0 in meta.json fails
    meta = json.loads((tmp_path / "registry/schema/meta.json").read_text(encoding="utf-8"))
    for entry in meta["evidence"]["types"]:
        if entry["id"] == "social-signal":
            entry["creatorMultipliers"]["sameAsAuthor"] = 0
    (tmp_path / "registry/schema/meta.json").write_text(json.dumps(meta), encoding="utf-8")
    violations = check_evidence_policy(tmp_path)
    assert any("sameAsAuthor" in v["detail"] for v in violations)

    # Restore meta.json and test Negative control 2: publishCooldownDays: 30
    (tmp_path / "registry/schema/meta.json").write_text(
        (ROOT / "registry/schema/meta.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    api = json.loads((tmp_path / "docs/api/v1/evidence-types.json").read_text(encoding="utf-8"))
    for entry in api["types"]:
        if entry["id"] == "social-signal":
            entry["publishCooldownDays"] = 30
    (tmp_path / "docs/api/v1/evidence-types.json").write_text(json.dumps(api), encoding="utf-8")
    violations = check_evidence_policy(tmp_path)
    assert any("publishCooldownDays" in v["detail"] for v in violations)

    # Restore API file and test Negative control 3: retired claim reintroduced in active surface
    (tmp_path / "docs/api/v1/evidence-types.json").write_text(
        (ROOT / "docs/api/v1/evidence-types.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (tmp_path / "evidence/README.md").write_text(
        "See curation-authority-map.md.\nSocial signal is from external creators only; 30-day publish cooldown applies.\n",
        encoding="utf-8",
    )
    violations = check_evidence_policy(tmp_path)
    assert any(v["source"] == "evidence/README.md" for v in violations)


# ---------------------------------------------------------------------------
# 2. Eligible first-party & recent third-party social evidence TM + no 30d hold
# ---------------------------------------------------------------------------


def test_eligible_first_party_and_third_party_social_score_equally():
    first_party = {
        "id": "example/tool",
        "evidence": [
            {
                "type": "social-signal",
                "source": "https://www.youtube.com/watch?v=fp10k",
                "views": 10000,
                "likes": 200,
                "comments": 0,
                "creatorMultiplier": 1.0,
                "lastVerified": "2026-11-17",
            }
        ],
    }
    third_party_yesterday = {
        "id": "example/tool",
        "evidence": [
            {
                "type": "social-signal",
                "source": "https://www.youtube.com/watch?v=tp10k",
                "views": 10000,
                "likes": 200,
                "comments": 0,
                "creatorMultiplier": 1.0,
                "sourceStartedAt": "2026-11-16",
                "lastVerified": "2026-11-17",
            }
        ],
    }
    assert computeTrustMagnitude(first_party, evaluationAtUTC=EVAL_NOW) == pytest.approx(32.0, abs=1e-4)
    assert computeTrustMagnitude(third_party_yesterday, evaluationAtUTC=EVAL_NOW) == pytest.approx(32.0, abs=1e-4)


@pytest.mark.parametrize("age_days", [0, 1, 29, 30, 31])
def test_no_publication_age_hold_across_30_day_boundary(age_days: int):
    pub_date = (EVAL_NOW - dt.timedelta(days=age_days)).date().isoformat()
    skill = {
        "id": "example/tool",
        "evidence": [
            {
                "type": "social-signal",
                "source": f"https://www.youtube.com/watch?v=vid{age_days}",
                "views": 10000,
                "likes": 200,
                "comments": 0,
                "sourceStartedAt": pub_date,
                "lastVerified": "2026-11-17",
            }
        ],
    }
    assert computeTrustMagnitude(skill, evaluationAtUTC=EVAL_NOW) == pytest.approx(32.0, abs=1e-4)


def test_evidence_policy_fixture_cases_match_engine_and_validator():
    data = _load_cases()
    cases = {c["id"]: c for c in data["cases"]}

    fp = cases["eligible-first-party-video"]
    fp_tm = computeTrustMagnitude(fp["skill"], evaluationAtUTC=EVAL_NOW)
    assert fp_tm == pytest.approx(fp["expected"]["trustMagnitude"], abs=1e-4)
    assert computeOverallTrustGrade(fp_tm, 1, True) == fp["expected"]["overallTrustGrade"]

    tp = cases["recent-third-party-video"]
    assert computeTrustMagnitude(tp["skill"], evaluationAtUTC=EVAL_NOW) == pytest.approx(
        tp["expected"]["trustMagnitude"], abs=1e-4
    )

    sub = cases["below-view-floor-video-scores-zero"]
    assert computeTrustMagnitude(sub["skill"], evaluationAtUTC=EVAL_NOW) == 0.0

    proxy = cases["first-party-proxy-containment-rejected"]
    violations = check_proxy_containment_policy(proxy["skill"])
    assert len(violations) == 1
    assert violations[0]["error_code"] == proxy["expected"]["validatorErrorCode"]

    cap = cases["suite-component-cap-no-synthetic-self-attestation"]
    assert computeTrustMagnitude(cap["skill"], evaluationAtUTC=EVAL_NOW) == pytest.approx(
        cap["expected"]["baselineTrustMagnitude"], abs=1e-4
    )
    assert computeOverallTrustGradeFromSkill(cap["skill"]) == cap["expected"]["baselineOverallTrustGrade"]

    plateau = cases["same-creator-plateau-and-same-type-url-dedup"]
    assert computeTrustMagnitude(plateau["skill"], evaluationAtUTC=EVAL_NOW) == pytest.approx(
        plateau["expected"]["trustMagnitude"], abs=1e-4
    )
    assert computeOverallTrustGradeFromSkill(plateau["skill"]) == plateau["expected"]["overallTrustGrade"]


# ---------------------------------------------------------------------------
# 3. First-party proxy-containment rejected; external proxy-containment works
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "source_url",
    [
        "https://github.com/acme/tool",
        "https://github.com/acme/tool.git/",
        "https://github.com/acme/tool/blob/main/SKILL.md",
        "https://github.com/acme/other-repo",
        "https://github.com/acme-suite/monorepo",
    ],
)
def test_check_proxy_containment_rejects_first_party_sources(source_url: str):
    skill = {
        "id": "acme/tool",
        "contributor": "acme",
        "links": {"github": "https://github.com/acme/tool/blob/main/SKILL.md"},
        "evidence": [{"type": "proxy-containment", "source": source_url, "externalStars": 25000}],
    }
    suite_skill = (
        {"id": "acme-suite/bundle", "links": {"github": "https://github.com/acme-suite/monorepo/blob/main/README.md"}}
        if "acme-suite" in source_url
        else None
    )
    violations = check_proxy_containment_policy(skill, suite_skill=suite_skill)
    assert len(violations) == 1
    assert violations[0]["error_code"] == "first-party-proxy-containment"


def test_proxy_containment_external_star_threshold_and_cli_enforcement(tmp_path: Path):
    # Engine arithmetic: 9,999 -> 0; 10,000 -> 8; 20,000 -> 16
    assert computeArtifactScore({"type": "proxy-containment", "externalStars": 9999}) == 0.0
    assert computeArtifactScore({"type": "proxy-containment", "externalStars": 10000}) == pytest.approx(8.0, abs=1e-4)
    assert computeArtifactScore({"type": "proxy-containment", "externalStars": 20000}) == pytest.approx(16.0, abs=1e-4)

    # CLI rejects first-party proxy-containment before any disk write
    root = _minimal_named_repo(tmp_path, contributor="acme", slug="tool", suite_ref="acme-suite/bundle")
    named_file = root / "registry" / "named" / "acme" / "tool.md"
    before = named_file.read_text(encoding="utf-8")

    with pytest.raises(SystemExit):
        meta_evidence_command(
            _evidence_args(
                str(root),
                skill_id="acme/tool",
                source="https://github.com/acme/tool",
                evidence_type="proxy-containment",
                external_stars=25000,
                notes="First-party own repo",
            )
        )
    assert named_file.read_text(encoding="utf-8") == before

    # CLI rejects suite-root first-party proxy-containment as well
    with pytest.raises(SystemExit):
        meta_evidence_command(
            _evidence_args(
                str(root),
                skill_id="acme/tool",
                source="https://github.com/acme-suite/bundle",
                evidence_type="proxy-containment",
                external_stars=25000,
                notes="Suite root repo",
            )
        )
    assert named_file.read_text(encoding="utf-8") == before

    # Validator emits warning by default for missing externalStars, error when require_external_stars=True
    missing_stars = {
        "id": "acme/tool",
        "contributor": "acme",
        "evidence": [
            {"type": "proxy-containment", "source": "https://github.com/external-org/legacy-container"}
        ],
    }
    warn_violations = check_proxy_containment_policy(missing_stars)
    assert len(warn_violations) == 1
    assert warn_violations[0]["error_code"] == "proxy-containment-missing-external-stars"
    assert warn_violations[0]["severity"] == "warning"

    err_violations = check_proxy_containment_policy(missing_stars, require_external_stars=True)
    assert len(err_violations) == 1
    assert err_violations[0]["error_code"] == "proxy-containment-missing-external-stars"
    assert err_violations[0]["severity"] == "error"

    # Validator rejects sub-10k externalStars on proxy-containment
    sub_floor = {
        "id": "acme/tool",
        "contributor": "acme",
        "evidence": [
            {"type": "proxy-containment", "source": "https://github.com/external-org/small", "externalStars": 9999}
        ],
    }
    floor_violations = check_proxy_containment_policy(sub_floor)
    assert len(floor_violations) == 1
    assert floor_violations[0]["error_code"] == "proxy-containment-below-star-floor"

    # CLI rejects --external-stars < 10000 and rejects --index conversion without >= 10000 stars
    with pytest.raises(SystemExit):
        meta_evidence_command(
            _evidence_args(
                str(root),
                skill_id="acme/tool",
                source="https://github.com/external-org/small",
                evidence_type="proxy-containment",
                external_stars=1,
                notes="Below 10k floor",
            )
        )
    assert named_file.read_text(encoding="utf-8") == before

    # Add a repo-own row, then ensure --index conversion to proxy-containment without externalStars fails
    meta_evidence_command(
        _evidence_args(
            str(root),
            skill_id="acme/tool",
            source="https://github.com/external-org/later-proxy",
            evidence_type="repo-own",
            commits=10,
            contributors=1,
            notes="Initial row",
        )
    )
    before_index = named_file.read_text(encoding="utf-8")
    with pytest.raises(SystemExit):
        meta_evidence_command(
            _evidence_args(
                str(root),
                skill_id="acme/tool",
                source="https://github.com/external-org/later-proxy",
                index=0,
                evidence_type="proxy-containment",
                notes="Missing externalStars on index conversion",
            )
        )
    assert named_file.read_text(encoding="utf-8") == before_index

    # CLI rejects --external-stars on --index when target row is not proxy-containment
    with pytest.raises(SystemExit):
        meta_evidence_command(
            _evidence_args(
                str(root),
                skill_id="acme/tool",
                source="https://github.com/external-org/later-proxy",
                index=0,
                external_stars=20000,
                notes="Reject externalStars on non-proxy indexed row",
            )
        )
    assert named_file.read_text(encoding="utf-8") == before_index

    # CLI rejects --external-stars on append without --type proxy-containment
    with pytest.raises(SystemExit):
        meta_evidence_command(
            _evidence_args(
                str(root),
                skill_id="acme/tool",
                source="https://github.com/external-org/untyped-stars",
                external_stars=20000,
                notes="Reject externalStars on untyped append row",
            )
        )
    assert named_file.read_text(encoding="utf-8") == before_index

    # CLI accepts genuinely external container with --external-stars 20000
    meta_evidence_command(
        _evidence_args(
            str(root),
            skill_id="acme/tool",
            source="https://github.com/external-org/container-repo",
            evidence_type="proxy-containment",
            external_stars=20000,
            notes="External container bundling acme/tool",
        )
    )
    after = named_file.read_text(encoding="utf-8")
    assert "externalStars: 20000" in after


# ---------------------------------------------------------------------------
# 4. Challenger / packet freshness vs discovery age vs lastVerified decay
# ---------------------------------------------------------------------------


def test_freshness_mechanisms_remain_independently_scoped(tmp_path: Path):
    # Steward discovery age buckets are descriptive only and do not block admission/review
    assert evidencediscovery._freshness(dt.date(2026, 11, 16), dt.date(2026, 11, 17))["class"] == "fresh"
    assert evidencediscovery._freshness(dt.date(2024, 1, 1), dt.date(2026, 11, 17))["class"] == "aging"

    # Typed dedup in buildDiscoveryReceipt keeps distinct evidence types at the same URL separate
    root = _minimal_named_repo(tmp_path, contributor="acme", slug="tool")
    named_file = root / "registry" / "named" / "acme" / "tool.md"
    named_file.write_text(
        "---\n"
        "id: acme/tool\n"
        "name: tool\n"
        "contributor: acme\n"
        "genericSkillRef: demo-generic\n"
        "status: named\n"
        "level: 2★\n"
        "description: Test\n"
        "links:\n"
        "  github: https://github.com/acme/tool/blob/main/SKILL.md\n"
        "evidence:\n"
        "  - source: https://github.com/acme/tool\n"
        "    type: repo-own\n"
        "    commits: 6\n"
        "    contributors: 1\n"
        "---\n",
        encoding="utf-8",
    )
    receipt = evidencediscovery.buildDiscoveryReceipt(
        {
            "skillId": "acme/tool",
            "searchedBy": "tester",
            "searches": [
                {
                    "query": "acme/tool",
                    "channel": "upstream-repo",
                    "searchedAt": "2026-11-17T00:00:00Z",
                    "results": [
                        {
                            "url": "https://github.com/acme/tool",
                            "title": "Stars",
                            "evidenceType": "github-stars-own",
                            "attribution": "acme",
                            "publishedAt": "2026-11-16",
                        },
                        {
                            "url": "https://github.com/acme/tool/",
                            "title": "Repo dup",
                            "evidenceType": "repo-own",
                            "attribution": "acme",
                            "publishedAt": "2026-11-16",
                        },
                    ],
                }
            ],
        },
        repoRoot=root,
        generatedAt="2026-11-17T00:00:00Z",
    )
    results = receipt["searches"][0]["candidates"]
    assert results[0]["admissibility"]["state"] == "needs-review"  # github-stars-own NOT collapsed onto repo-own
    assert results[1]["admissibility"]["state"] == "inadmissible"  # repo-own duplicate IS caught

    # verifyPacketFreshness fails closed when source fetch is unavailable (not a 30d pub hold)
    packet = {
        "schemaVersion": "discovery-packet-v2",
        "sourceRef": {"url": "https://github.com/example/repo/blob/main/SKILL.md", "sha256": "0" * 64},
        "genericSnapshot": {},
        "dedupeProof": {"executed": True},
        "selectedDefinition": {},
    }
    errs = verifyPacketFreshness(packet, registryPath=str(tmp_path), fetcher=lambda _u: None)
    assert errs


# ---------------------------------------------------------------------------
# 5. Deduplication, plateau, engagement, and source-dump integrity
# ---------------------------------------------------------------------------


def test_social_safeguards_plateau_floor_engagement_and_cap():
    # View floor: 999 -> 0; 1000 -> 24
    assert computeTrustMagnitude({"id": "x", "evidence": [{"type": "social-signal", "views": 999}]}) == 0.0
    assert computeTrustMagnitude({"id": "x", "evidence": [{"type": "social-signal", "views": 1000}]}) == pytest.approx(24.0, abs=1e-4)

    # Engagement ratio cap: 10000 views, 200 likes, 50 comments -> ratio 1.5 -> 32 * 1.5 = 48
    engaged = {
        "id": "x",
        "evidence": [{"type": "social-signal", "views": 10000, "likes": 200, "comments": 50}],
    }
    assert computeTrustMagnitude(engaged) == pytest.approx(48.0, abs=1e-4)

    # Same-creator plateau: 32 + 16 + 8 + 0 = 56
    stacked = {
        "id": "x",
        "evidence": [
            {"type": "social-signal", "source": f"https://yt.example/{i}", "views": 10000, "creator": "theo"}
            for i in range(4)
        ],
    }
    assert computeTrustMagnitude(stacked) == pytest.approx(56.0, abs=1e-4)

    # Hard A-cap at 80 across distinct creators
    over_cap = {
        "id": "x",
        "evidence": [
            {"type": "social-signal", "source": f"https://yt.example/{i}", "views": 1000000, "likes": 10000, "comments": 1000, "creator": f"c{i}"}
            for i in range(3)
        ],
    }
    assert computeTrustMagnitude(over_cap) == pytest.approx(80.0, abs=1e-4)


def test_generate_source_dump_preserves_social_metrics_and_does_not_fabricate_self_attestation(tmp_path: Path):
    ev_scripts = str(ROOT / "evidence" / "scripts")
    if ev_scripts not in sys.path:
        sys.path.insert(0, ev_scripts)
    import generate_source_dump as gsd  # type: ignore

    untyped = {"source": "https://example.org/post"}
    assert gsd.dedupeKey(untyped)[1] == "untyped"
    norm_untyped = gsd.normalizeEvidenceRow(copy.deepcopy(untyped), skipLiveStars=True)
    assert norm_untyped["normalized_type"] == "untyped"
    assert norm_untyped["untyped"] is True

    # Untyped rows are written to untyped_rows.md with full payload preserved,
    # and a subsequent run with no untyped rows removes the stale queue.
    rich_untyped = {
        "source": "https://example.org/post",
        "commits": 42,
        "citations": 7,
        "externalStars": 15000,
        "evaluator": "mbtiongson1",
        "creatorRelation": "first-party",
    }
    norm_rich = gsd.normalizeEvidenceRow(copy.deepcopy(rich_untyped), skipLiveStars=True)
    untyped_skill = {
        "id": "acme/untyped",
        "name": "untyped",
        "contributor": "acme",
        "compiled_evidence": [norm_rich],
    }
    q_path = gsd.writeUntypedReviewQueue(str(tmp_path), gsd.collectUntypedSkills([untyped_skill]))
    assert q_path is not None
    q_text = Path(q_path).read_text(encoding="utf-8")
    assert "https://example.org/post" in q_text
    for field in ('"commits": 42', '"citations": 7', '"externalStars": 15000', '"evaluator": "mbtiongson1"', '"creatorRelation": "first-party"'):
        assert field in q_text

    # Consecutive clean run removes stale untyped_rows.md
    cleared = gsd.writeUntypedReviewQueue(str(tmp_path), [])
    assert cleared is None
    assert not Path(q_path).exists()

    # End-to-end named-skill Markdown loading with unquoted YAML dates and
    # two untyped rows sharing the same source: neither collapses, original row is preserved
    named_dir = tmp_path / "named" / "acme"
    named_dir.mkdir(parents=True)
    (named_dir / "yaml-untyped.md").write_text(
        "---\n"
        "id: acme/yaml-untyped\n"
        "name: yaml-untyped\n"
        "contributor: acme\n"
        "genericSkillRef: demo\n"
        "evidence:\n"
        "  - source: https://github.com/acme/yaml-untyped\n"
        "    date: 2026-11-17\n"
        "    commits: 10\n"
        "    stars_verified: 42\n"
        "  - source: https://github.com/acme/yaml-untyped\n"
        "    date: 2026-11-17\n"
        "    stars: 999\n"
        "---\n",
        encoding="utf-8",
    )
    compiled = gsd.compileNamedSkills(str(tmp_path / "named"), {}, skipLiveStars=True)
    untyped_group = gsd.collectUntypedSkills(compiled)
    assert len(untyped_group) == 1
    assert len(untyped_group[0]["compiled_evidence"]) == 2
    q_yaml = gsd.writeUntypedReviewQueue(str(tmp_path / "out"), untyped_group)
    assert q_yaml is not None
    q_yaml_text = Path(q_yaml).read_text(encoding="utf-8")
    assert '"date": "2026-11-17"' in q_yaml_text
    assert '"commits": 10' in q_yaml_text
    assert '"stars": 999' in q_yaml_text
    assert '"stars_verified": 42' in q_yaml_text

    social = {
        "type": "social-signal",
        "source": "https://www.youtube.com/watch?v=abc",
        "views": 12345,
        "likes": 200,
        "comments": 15,
        "creator": "theo",
        "creatorRelation": "first-party",
    }
    norm_social = gsd.normalizeEvidenceRow(copy.deepcopy(social), skipLiveStars=True)
    assert norm_social["views"] == 12345
    assert norm_social["likes"] == 200
    assert norm_social["comments"] == 15
    assert norm_social["creator"] == "theo"
    assert norm_social["creatorRelation"] == "first-party"


def test_schemas_accept_social_provenance_fields():
    import jsonschema

    ev_row = {
        "type": "social-signal",
        "source": "https://www.youtube.com/watch?v=demo2473",
        "evaluator": "mbtiongson1",
        "date": "2026-11-17",
        "views": 10000,
        "creator": "theo",
        "creatorRelation": "third-party",
        "relevanceNote": "Substantive walkthrough of the target skill.",
    }
    named_schema = json.loads((ROOT / "registry" / "schema" / "namedSkill.schema.json").read_text(encoding="utf-8"))
    named_doc = {
        "id": "acme/tool",
        "name": "tool",
        "contributor": "acme",
        "origin": True,
        "genericSkillRef": "demo-generic",
        "status": "named",
        "level": "2★",
        "description": "Test skill with social provenance fields.",
        "evidence": [ev_row],
        "createdAt": "2026-11-17",
        "updatedAt": "2026-11-17",
    }
    jsonschema.validate(instance=named_doc, schema=named_schema)

    skill_schema = json.loads((ROOT / "registry" / "schema" / "skill.schema.json").read_text(encoding="utf-8"))
    skill_doc = {
        "id": "demo-generic",
        "name": "Demo Generic",
        "type": "basic",
        "description": "Generic skill with social provenance fields.",
        "prerequisites": [],
        "derivatives": [],
        "knownAgents": ["claude-code"],
        "status": "validated",
        "evidence": [ev_row],
        "createdAt": "2026-11-17",
        "updatedAt": "2026-11-17",
        "version": "1.0.0",
    }
    jsonschema.validate(instance=skill_doc, schema=skill_schema)


def test_distinct_creators_keep_separate_plateau_slots():
    # 1,000 views -> log10(1000) * 8 = 24.0 raw score per row
    rows_with_creators = [
        {"type": "social-signal", "source": "https://youtu.be/a1", "views": 1000, "creator": "alice", "lastVerified": "2026-11-17"},
        {"type": "social-signal", "source": "https://youtu.be/a2", "views": 1000, "creator": "alice", "lastVerified": "2026-11-17"},
        {"type": "social-signal", "source": "https://youtu.be/a3", "views": 1000, "creator": "alice", "lastVerified": "2026-11-17"},
        {"type": "social-signal", "source": "https://youtu.be/b1", "views": 1000, "creator": "bob", "lastVerified": "2026-11-17"},
    ]
    rows_without_creators = [
        {"type": "social-signal", "source": f"https://youtu.be/u{i}", "views": 1000, "lastVerified": "2026-11-17"}
        for i in range(4)
    ]
    # Distinct creators: alice gets 24*(1 + 0.5 + 0.25) = 42.0, bob gets 24*1.0 = 24.0 -> 66.0
    assert computeTrustMagnitude({"id": "example/tool", "evidence": rows_with_creators}, evaluationAtUTC=EVAL_NOW) == pytest.approx(66.0, abs=1e-4)
    # Without creator: all 4 collapse into _unknown, 4th row gets 0 -> 42.0
    assert computeTrustMagnitude({"id": "example/tool", "evidence": rows_without_creators}, evaluationAtUTC=EVAL_NOW) == pytest.approx(42.0, abs=1e-4)


def test_generate_source_dump_renders_creator_relation_and_relevance_note():
    import io
    sys.path.insert(0, str(ROOT / "evidence" / "scripts"))
    import generate_source_dump as gsd

    buf = io.StringIO()
    gsd.writeEvidenceRows(
        buf,
        [
            {
                "type": "social-signal",
                "source": "https://www.youtube.com/watch?v=demo2473",
                "date": "2026-11-17",
                "views": 10000,
                "creator": "theo",
                "creatorRelation": "first-party",
                "relevanceNote": "Author walkthrough of the skill",
                "notes": "Demo video",
            }
        ],
    )
    rendered = buf.getvalue()
    assert "**Creator:** theo" in rendered
    assert "**Creator Relation:** first-party" in rendered
    assert "**Relevance Note:** Author walkthrough of the skill" in rendered
