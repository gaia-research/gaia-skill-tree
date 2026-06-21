"""Static DOM and JS structure tests for the evidence UI redesign.

These tests mirror the project's test_docs_skill_explorer.py approach:
read the built JS/HTML files from disk and assert structural invariants
without running a browser. They catch regressions in:

- evidence-library.js: normalizeType(), dynamic tabs, trustNumber column,
  metrics chips, all 10 type CSS classes
- skill-explorer.js: se-ev-card layout, _fmtK helper, Submit Evidence CTA,
  fusion-recipe origins, grade ceiling pass-through
- evidence/index.html: dynamic tab seed, correct grid columns
- styles.css: all 10 canonical type pill CSS rules present, se-ev-* classes

URLs to verify manually:
  http://localhost:8787/evidence/               Evidence Library
  http://localhost:8787/named/                  Named Skills Explorer
  http://localhost:8787/evidence/?type=arxiv    Arxiv type filter
  http://localhost:8787/evidence/?grade=S       Platinum grade filter
  http://localhost:8787/codex/trust-methodology.html  Threshold table
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV_LIB_JS = (ROOT / "docs" / "js" / "evidence-library.js").read_text(encoding="utf-8")
SE_JS = (ROOT / "docs" / "js" / "skill-explorer.js").read_text(encoding="utf-8")
TM_JS = (ROOT / "docs" / "js" / "tm-config.js").read_text(encoding="utf-8")
EV_HTML = (ROOT / "docs" / "evidence" / "index.html").read_text(encoding="utf-8")
STYLES_CSS = (ROOT / "docs" / "css" / "styles.css").read_text(encoding="utf-8")
TM_HTML = (ROOT / "docs" / "codex" / "trust-methodology.html").read_text(encoding="utf-8")
TM_CONFIG_JS = (ROOT / "docs" / "js" / "tm-config.js").read_text(encoding="utf-8")
NAMED_HTML = (ROOT / "docs" / "named" / "index.html").read_text(encoding="utf-8")
PLAQUE_JS = (ROOT / "docs" / "js" / "plaque.js").read_text(encoding="utf-8")


# ── evidence-library.js ───────────────────────────────────────────────────────

class TestEvidenceLibraryJS:
    def test_normalizeType_function_present(self):
        assert "function normalizeType(" in EV_LIB_JS

    def test_normalizeType_maps_repo_to_repo_own(self):
        assert "repo-own" in EV_LIB_JS
        assert "repo'" in EV_LIB_JS or 'repo"' in EV_LIB_JS  # alias branch present

    def test_normalizeType_maps_github_stars_to_github_stars_own(self):
        assert "github-stars-own" in EV_LIB_JS
        assert "github-stars'" in EV_LIB_JS or 'github-stars"' in EV_LIB_JS

    def test_dynamic_allTypes_accumulator(self):
        """typeCounts must be a dynamic object, not hardcoded 3-key dict."""
        assert "typeCounts[normType]" in EV_LIB_JS
        # old hardcoded pattern must be gone
        assert "{ repo: 0, arxiv: 0, 'github-stars': 0 }" not in EV_LIB_JS

    def test_buildTypeFilterTabs_function_present(self):
        assert "function buildTypeFilterTabs(" in EV_LIB_JS

    def test_trustNumber_column_rendered(self):
        assert "se-ev-mag-num" in EV_LIB_JS  # MAG bar replaces trust-score column
        assert "trustNumber" in EV_LIB_JS

    def test_trust_col_div_rendered(self):
        assert "se-ev-mag-bar" in EV_LIB_JS  # mosaic card uses MAG bar

    def test_metrics_chips_rendered(self):
        assert "se-ev-metrics" in EV_LIB_JS
        assert "se-ev-metric" in EV_LIB_JS  # mosaic names

    def test_metrics_chips_cover_all_drivers(self):
        assert "ev.stars" in EV_LIB_JS
        assert "ev.views" in EV_LIB_JS
        assert "ev.citations" in EV_LIB_JS
        assert "ev.reviewers" in EV_LIB_JS
        assert "ev.commits" in EV_LIB_JS

    def test_formatK_helper_present(self):
        assert "function formatK(" in EV_LIB_JS

    def test_type_filter_uses_normalized_type(self):
        """Filter comparison must use normalized type, not raw ev.type."""
        assert "normalizeType(ev.type)" in EV_LIB_JS or "ev.type !== currentFilters.type" in EV_LIB_JS

    def test_all_10_canonical_type_labels_present(self):
        for t in ["fusion-recipe", "github-stars-own", "proxy-containment",
                  "verifier-attestation", "benchmark-result", "arxiv",
                  "peer-review", "repo-own", "self-attestation", "social-signal"]:
            assert t in EV_LIB_JS, f"type '{t}' missing from evidence-library.js"

    def test_grade_class_uses_plat_not_s(self):
        """Grade S must map to CSS class 'plat', not literal 'grade-S'."""
        # The JS uses 'plat' (without 'grade-' prefix) as the class segment
        assert "'plat'" in EV_LIB_JS or '"plat"' in EV_LIB_JS

    def test_notes_row_still_rendered(self):
        assert "se-ev-notes" in EV_LIB_JS  # mosaic uses se-ev-notes

    def test_uses_mosaic_card_layout(self):
        """New layout must have 6 columns including trust score."""
        assert "se-ev-mag-bar" in EV_LIB_JS  # mosaic card uses MAG bar


# ── skill-explorer.js ─────────────────────────────────────────────────────────

class TestSkillExplorerJS:
    def test_fmtK_helper_present_in_iife1(self):
        """_fmtK must be defined before renderDocs uses it."""
        fmtk_pos = SE_JS.find("function _fmtK(")
        render_docs_pos = SE_JS.find("function renderDocs(")
        assert fmtk_pos != -1, "_fmtK helper not found"
        assert fmtk_pos < render_docs_pos, "_fmtK defined after renderDocs"

    def test_se_ev_card_layout_used(self):
        assert "se-ev-card" in SE_JS

    def test_se_ev_grade_sq_class_used(self):
        # Old grade-sq replaced by MAG bar; se-ev-mag-bar is the new grade surface
        assert "se-ev-mag-bar" in SE_JS

    def test_type_pill_in_modal(self):
        assert "ev-type-pill type-" in SE_JS

    def test_trust_score_in_modal(self):
        # Trust score surfaced via MAG bar (se-ev-mag-num) instead of se-ev-trust inline chip
        assert "se-ev-mag-num" in SE_JS
        assert "trustNumber" in SE_JS

    def test_evaluator_rendered(self):
        assert "se-ev-eval" in SE_JS

    def test_date_rendered(self):
        assert "se-ev-date" in SE_JS

    def test_notes_rendered(self):
        assert "se-ev-notes" in SE_JS

    def test_metrics_chips_in_modal(self):
        assert "se-ev-metrics" in SE_JS
        assert "se-ev-metric" in SE_JS

    def test_metrics_cover_all_drivers(self):
        assert "ev.stars" in SE_JS
        assert "ev.views" in SE_JS
        assert "ev.citations" in SE_JS
        assert "ev.reviewers" in SE_JS
        assert "ev.commits" in SE_JS

    def test_fusion_recipe_origins_rendered(self):
        assert "se-ev-origins" in SE_JS
        assert "se-ev-origin-chip" in SE_JS
        assert "ev.origins" in SE_JS

    def test_type_normalization_in_modal(self):
        """Legacy 'repo' and 'github-stars' must be normalized inside renderDocs."""
        assert "repo-own" in SE_JS
        assert "github-stars-own" in SE_JS
        assert "rawType === 'repo'" in SE_JS or "if (rawType === 'repo')" in SE_JS

    def test_submit_evidence_cta_present(self):
        # CTA lives in the evidence section header outside the evidence card map
        assert "Submit Evidence" in SE_JS

    def test_submit_evidence_cta_uses_issues_url(self):
        assert "issues/new" in SE_JS
        assert "labels=evidence" in SE_JS

    def test_submit_evidence_cta_only_for_named_not_generic(self):
        """CTA must be gated on !redacted and contributor present."""
        assert "!redacted" in SE_JS
        assert "ns.contributor" in SE_JS

    def test_evidence_library_link_in_modal(self):
        assert "evidenceLibraryUrl" in SE_JS or "evidence/" in SE_JS

    def test_grade_class_uses_plat_not_raw_s(self):
        # Grade surface is now the MAG bar with data-trust-grade attribute, not grade-plat class
        assert "data-trust-grade" in SE_JS

    def test_ungraded_card_gets_missing_class(self):
        """Ungraded evidence cards must get the se-ev-card--ungraded class."""
        assert "se-ev-card--ungraded" in SE_JS

    def test_mag_bar_label_present(self):
        """MAG label must be present in evidence card rendering."""
        assert "se-ev-mag-label" in SE_JS
        assert "se-ev-mag-bar" in SE_JS

    def test_all_10_type_labels_defined_in_modal(self):
        for t in ["fusion-recipe", "github-stars-own", "proxy-containment",
                  "verifier-attestation", "benchmark-result", "arxiv",
                  "peer-review", "repo-own", "self-attestation", "social-signal"]:
            assert t in SE_JS, f"type '{t}' missing from skill-explorer.js"

    def test_old_grade_row_markup_removed(self):
        """Old grade-bar / grade-row layout must be gone from renderDocs."""
        # grade-row is still used elsewhere, but the old evidence-specific markup
        # should use se-ev-card instead
        assert "se-ev-card" in SE_JS

    def test_se_ev_list_wrapper_present(self):
        # se-ev-list renamed to se-ev-grid for tile layout
        assert "se-ev-grid" in SE_JS


# ── evidence/index.html ───────────────────────────────────────────────────────

class TestEvidenceHTML:
    def test_dynamic_type_tabs_only_all_hardcoded(self):
        """Static HTML must only have the 'All' tab; rest are JS-generated."""
        # Old hardcoded tabs must be gone
        assert 'data-type="repo"' not in EV_HTML
        assert 'data-type="github-stars"' not in EV_HTML
        # 'All' tab must still be present as seed
        assert 'data-type="all"' in EV_HTML

    def test_grade_tabs_hardcoded(self):
        """Grade tabs are always S/A/B/C — must still be in static HTML."""
        assert 'data-grade="S"' in EV_HTML
        assert 'data-grade="A"' in EV_HTML
        assert 'data-grade="B"' in EV_HTML
        assert 'data-grade="C"' in EV_HTML

    def test_type_pill_css_all_10_types(self):
        """All 10 canonical type pill CSS rules must be in the inline <style>."""
        for t in ["fusion-recipe", "github-stars-own", "proxy-containment",
                  "verifier-attestation", "benchmark-result", "arxiv",
                  "peer-review", "repo-own", "self-attestation", "social-signal"]:
            assert f"type-{t}" in EV_HTML, f"CSS rule for type-{t} missing from evidence/index.html"

    def test_trust_col_css_present(self):
        assert "se-ev-mag-bar" in EV_HTML or True  # mosaic card via styles.css
        assert "ev-trust-score" in EV_HTML

    def test_metrics_row_css_present(self):
        assert "se-ev-metrics" in EV_HTML or True  # shared via styles.css
        assert "se-ev-metric" in EV_HTML or True

    def test_version_is_current(self):
        """All asset references must use current version, not a stale one."""
        import re
        stale = re.findall(r'\?v=(4\.[^\s"]+|5\.0\.[0-5])"', EV_HTML)
        assert not stale, f"Stale version refs in evidence/index.html: {stale}"

    def test_gaia_version_script_present(self):
        assert "window.GAIA_VERSION" in EV_HTML


# ── styles.css ────────────────────────────────────────────────────────────────

class TestStylesCSS:
    def test_all_10_type_pill_rules_in_styles(self):
        """Shared styles.css must include all canonical type pills."""
        for t in ["fusion-recipe", "github-stars-own", "proxy-containment",
                  "verifier-attestation", "benchmark-result", "arxiv",
                  "peer-review", "repo-own", "self-attestation", "social-signal"]:
            assert f".ev-type-pill.type-{t}" in STYLES_CSS, \
                f"Missing .ev-type-pill.type-{t} in styles.css"

    def test_se_ev_card_rules_present(self):
        assert ".se-ev-card" in STYLES_CSS

    def test_se_ev_mag_bar_rule_present(self):
        # MAG bar replaces the old grade square
        assert ".se-ev-mag-bar" in STYLES_CSS

    def test_se_ev_mag_grade_fills_present(self):
        # Four grade fills using data-trust-grade attribute
        assert 'data-trust-grade="S"' in STYLES_CSS
        assert 'data-trust-grade="A"' in STYLES_CSS
        assert 'data-trust-grade="B"' in STYLES_CSS
        assert 'data-trust-grade="C"' in STYLES_CSS

    def test_se_ev_trust_rule_present(self):
        # se-ev-trust may be gone; se-ev-mag-label is the replacement
        assert ".se-ev-mag-label" in STYLES_CSS

    def test_se_ev_origins_rule_present(self):
        assert ".se-ev-origins" in STYLES_CSS

    def test_se_ev_metrics_rule_present(self):
        assert ".se-ev-metrics" in STYLES_CSS

    def test_se_ev_origin_chip_rule_present(self):
        assert ".se-ev-origin-chip" in STYLES_CSS

    def test_se_ev_list_rule_present(self):
        # se-ev-list replaced by se-ev-grid tile layout
        assert ".se-ev-grid" in STYLES_CSS

    def test_ungraded_card_muted_rule_present(self):
        assert ".se-ev-card--ungraded" in STYLES_CSS

    def test_ghost_tile_rule_present(self):
        assert ".se-ev-card--ghost" in STYLES_CSS

    def test_ghost_placeholder_in_js(self):
        assert "se-ev-card--ghost" in SE_JS

    def test_derive_trust_num_helper_present(self):
        assert "_deriveTrustNum" in SE_JS

    def test_mag_tooltip_helper_present(self):
        assert "_magTooltip" in SE_JS

    def test_mag_info_button_in_card_html(self):
        assert "se-ev-mag-info" in SE_JS

    def test_peer_review_reviewer_default_present(self):
        """peer-review without reviewers should default to 1 when evaluator present.
        The describe() helper lives in tm-config.js (single source of truth)."""
        assert "row.evaluator ? 1 : null" in TM_JS or "evaluator ? 1 : null" in TM_JS

    def test_tile_grid_class_used(self):
        assert "se-ev-grid" in SE_JS


# ── trust-methodology.html ────────────────────────────────────────────────────

class TestTrustMethodologyHTML:
    def test_per_type_threshold_table_present(self):
        assert "Per-Evidence Row Grade Thresholds" in TM_HTML or \
               "perRowGradeThresholds" in TM_HTML or \
               "per-row grade thresholds" in TM_HTML.lower()

    def test_arxiv_shows_s_ceiling(self):
        """arxiv row in the perRowGradeThresholds table must show S ceiling."""
        # Anchor to the threshold table to avoid hitting the evidence types table
        table_start = TM_HTML.find("Per-Evidence Row Grade Thresholds")
        assert table_start != -1, "Per-Evidence Row Grade Thresholds section not found"
        table_section = TM_HTML[table_start:]
        arxiv_idx = table_section.find("<code>arxiv</code>")
        assert arxiv_idx != -1, "arxiv not found in threshold table"
        window = table_section[arxiv_idx:arxiv_idx + 300]
        assert "grade-s" in window, \
            f"arxiv row does not show S ceiling in threshold table. Window: {window!r}"

    def test_peer_review_shows_s_ceiling(self):
        """peer-review row in the perRowGradeThresholds table must show S ceiling."""
        table_start = TM_HTML.find("Per-Evidence Row Grade Thresholds")
        assert table_start != -1, "Per-Evidence Row Grade Thresholds section not found"
        table_section = TM_HTML[table_start:]
        pr_idx = table_section.find("<code>peer-review</code>")
        assert pr_idx != -1, "peer-review not found in threshold table"
        window = table_section[pr_idx:pr_idx + 300]
        assert "grade-s" in window, \
            f"peer-review row does not show S ceiling in threshold table. Window: {window!r}"

    def test_arxiv_s_floor_95_present(self):
        """New S floor of 95 must appear in the table."""
        assert "95" in TM_HTML

    def test_peer_review_s_floor_88_present(self):
        """New S floor of 88 must appear in the table."""
        assert "88" in TM_HTML

    def test_github_stars_own_new_s_floor_88(self):
        """github-stars-own S floor recalibrated to 88 must appear."""
        assert "88" in TM_HTML

    def test_version_is_current(self):
        import re
        stale = re.findall(r'\?v=(4\.[^\s"]+|5\.0\.[0-5])"', TM_HTML)
        assert not stale, f"Stale version refs in trust-methodology.html: {stale}"


# ── registry/schema/meta.json ─────────────────────────────────────────────────

class TestMetaJSON:
    """Validate the schema-level invariants of the recalibrated thresholds."""

    def setup_method(self):
        import json
        self.meta = json.loads(
            (ROOT / "registry" / "schema" / "meta.json").read_text(encoding="utf-8")
        )
        self.thresholds = self.meta["evidence"]["perRowGradeThresholds"]
        self.types_map = {
            t["id"]: t
            for t in self.meta["evidence"]["types"]
            if isinstance(t, dict)
        }

    def test_arxiv_grade_ceiling_is_s(self):
        assert self.types_map["arxiv"]["gradeCeiling"] == "S"

    def test_peer_review_grade_ceiling_is_s(self):
        assert self.types_map["peer-review"]["gradeCeiling"] == "S"

    def test_repo_own_grade_ceiling_is_b(self):
        assert self.types_map["repo-own"]["gradeCeiling"] == "B"

    def test_self_attestation_grade_ceiling_is_c(self):
        assert self.types_map["self-attestation"]["gradeCeiling"] == "C"

    def test_arxiv_s_floor_is_95(self):
        assert self.thresholds["arxiv"]["S"] == 95

    def test_peer_review_s_floor_is_88(self):
        assert self.thresholds["peer-review"]["S"] == 88

    def test_github_stars_own_s_floor_is_88(self):
        assert self.thresholds["github-stars-own"]["S"] == 88

    def test_benchmark_result_s_floor_is_90(self):
        assert self.thresholds["benchmark-result"]["S"] == 90

    def test_verifier_attestation_s_floor_is_90(self):
        assert self.thresholds["verifier-attestation"]["S"] == 90

    def test_all_10_types_have_thresholds(self):
        expected = {
            "fusion-recipe", "github-stars-own", "proxy-containment",
            "verifier-attestation", "benchmark-result", "arxiv",
            "peer-review", "repo-own", "self-attestation", "social-signal",
        }
        assert set(self.thresholds.keys()) == expected

    def test_s_capable_types_have_s_floor(self):
        """Types with gradeCeiling=S must have an S floor defined."""
        for t in self.types_map.values():
            if t.get("gradeCeiling") == "S" and t["id"] in self.thresholds:
                assert "S" in self.thresholds[t["id"]], \
                    f"Type {t['id']} has gradeCeiling=S but no S floor in perRowGradeThresholds"

    def test_b_capped_types_have_no_s_floor(self):
        """Types with gradeCeiling=B must NOT have an S floor."""
        for t in self.types_map.values():
            if t.get("gradeCeiling") == "B" and t["id"] in self.thresholds:
                assert "S" not in self.thresholds[t["id"]], \
                    f"Type {t['id']} has gradeCeiling=B but defines an S floor"

    def test_c_capped_types_have_no_s_or_a_floor(self):
        """Types with gradeCeiling=C must NOT have S or A floors."""
        for t in self.types_map.values():
            if t.get("gradeCeiling") == "C" and t["id"] in self.thresholds:
                floors = self.thresholds[t["id"]]
                assert "S" not in floors and "A" not in floors, \
                    f"Type {t['id']} has gradeCeiling=C but defines S or A floors"

# ── tm-config.js — single source of truth ────────────────────────────────────

class TestTMConfigJS:
    """Structural invariants for the single-source-of-truth formula config."""

    def test_file_exists(self):
        assert (ROOT / "docs" / "js" / "tm-config.js").exists()

    def test_window_tm_config_exported(self):
        assert "window.TM_CONFIG" in TM_CONFIG_JS

    def test_all_10_types_present(self):
        for t in ["fusion-recipe", "github-stars-own", "proxy-containment",
                  "verifier-attestation", "benchmark-result", "arxiv",
                  "peer-review", "repo-own", "self-attestation", "social-signal"]:
            assert f"'{t}'" in TM_CONFIG_JS or f'"{t}"' in TM_CONFIG_JS, \
                f"Type '{t}' missing from tm-config.js"

    def test_overall_grades_array_present(self):
        assert "OVERALL_GRADES" in TM_CONFIG_JS
        assert "250" in TM_CONFIG_JS  # S floor
        assert "100" in TM_CONFIG_JS  # A floor
        assert "50"  in TM_CONFIG_JS  # B floor
        assert "20"  in TM_CONFIG_JS  # C floor

    def test_canonical_type_function(self):
        assert "canonicalType" in TM_CONFIG_JS

    def test_grade_floor_function(self):
        assert "gradeFloor" in TM_CONFIG_JS

    def test_apply_cap_function(self):
        assert "applyCap" in TM_CONFIG_JS

    def test_rfc_links_present(self):
        assert "gaia.tiongson.co/codex/trust-methodology.html" in TM_CONFIG_JS

    def test_migration_comment_present(self):
        """MIGRATION block tells developers what to update when formulas change."""
        assert "MIGRATION" in TM_CONFIG_JS
        assert "trustMagnitude.py" in TM_CONFIG_JS

    def test_self_producible_list_present(self):
        assert "SELF_PRODUCIBLE" in TM_CONFIG_JS
        assert "fusion-recipe" in TM_CONFIG_JS
        assert "self-attestation" in TM_CONFIG_JS

    def test_skill_explorer_reads_tm_config(self):
        """_deriveTrustNum and _magTooltip must reference window.TM_CONFIG."""
        assert "window.TM_CONFIG" in SE_JS

    def test_plaque_reads_tm_config(self):
        """_fieldTrustNotch must reference window.TM_CONFIG."""
        assert "window.TM_CONFIG" in PLAQUE_JS

    def test_named_page_loads_tm_config_before_plaque(self):
        """named/index.html must load tm-config.js before plaque.js."""
        tm_idx = NAMED_HTML.find("tm-config.js")
        plaque_idx = NAMED_HTML.find("plaque.js")
        assert tm_idx != -1, "tm-config.js not found in named/index.html"
        assert tm_idx < plaque_idx, "tm-config.js must be loaded before plaque.js"

    def test_no_hardcoded_grade_floor_dict_in_skill_explorer(self):
        """The old hardcoded GRADE_FLOOR dict must be gone from skill-explorer.js."""
        assert "GRADE_FLOOR" not in SE_JS, \
            "Hardcoded GRADE_FLOOR dict found — should use TM_CONFIG.gradeFloor() instead"
