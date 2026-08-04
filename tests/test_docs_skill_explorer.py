from pathlib import Path
import pytest
pytestmark = [pytest.mark.integration, pytest.mark.slow]



ROOT = Path(__file__).resolve().parents[1]


def test_skill_explorer_uses_open_source_skills_npx_install():
    js = (ROOT / "docs" / "js" / "skill-explorer.js").read_text(encoding="utf-8")

    assert "npx skills add " in js
    assert "skills package" in js
    assert "npx @gaia-registry/cli install " not in js
    assert "@gaia-registry/cli" not in js


def test_skill_explorer_normalizes_github_skill_file_urls_for_skills_add():
    js = (ROOT / "docs" / "js" / "skill-explorer.js").read_text(encoding="utf-8")

    assert ".replace('/blob/', '/tree/')" in js
    assert ".replace(/\\/SKILL\\.md$/i, '')" in js


def test_skill_explorer_adds_demerits_to_update_timeline():
    js = (ROOT / "docs" / "js" / "skill-explorer.js").read_text(encoding="utf-8")

    assert "function demeritTimelineEvents(generic)" in js
    assert "Demerit noted: " in js
    assert "mergeTimeline(evts, generic, ns)" in js
    assert "renderTimeline(ns, generic)" in js


def test_skill_explorer_routes_to_named_page_from_homepage():
    js = (ROOT / "docs" / "js" / "skill-explorer.js").read_text(encoding="utf-8")

    assert "named-explorer-page" in js
    assert "match(/^#explorer\\/(.+)$/)" in js
    assert "item2.catalogRef" in js


def test_flowchart_labels_suite_nodes_with_component_not_bucket_origin():
    """Suite lens regression guard.

    Path and Fusion keep the original bucket[0] origin labels. The Suite lens
    alone swaps shared generic nodes to the suite's own component label (e.g.
    addy-osmani/incremental-implementation instead of obra/executing-plans).
    """
    js = (ROOT / "docs" / "js" / "skill-explorer.js").read_text(encoding="utf-8")
    css = (ROOT / "docs" / "css" / "styles.css").read_text(encoding="utf-8")

    # The suite-member map is built as an alternate label source.
    assert "var suiteMemberByNode = {}" in js
    assert "collectSuiteMembers" in js
    assert "var suiteMember = suiteMemberByNode[id];" in js
    # Base node identity remains the original named bucket for Path/Fusion.
    assert "var nb = namedBucket && namedBucket.length ? namedBucket[0] : null;" in js
    assert "suiteMember || (namedBucket" not in js
    # Suite labels are rendered as alternates, then CSS-swapped only under Suite.
    assert "dag-node-label--origin" in js
    assert "dag-node-label--suite" in js
    assert 'data-suite-member="' in js
    assert '#se-upgrade.lens-suite .git-node[data-suite-member="true"] .dag-node-label--origin' in css
    assert '#se-upgrade.lens-suite .git-node[data-suite-member="true"] .dag-node-label--suite' in css
    # apex node is never overwritten by a component sharing its generic ref.
    assert "gid !== genericId" in js


def test_flowchart_renders_suite_components_side_panel():
    """Marcus follow-up + refinement: a compact, transparent, collapsed-by-
    default roster of every declared suiteComponent, parked in a quiet rail
    OUTSIDE the Progression Path canvas padding.

    The panel must list slash-skill names only (not generic origin names, not
    full display names, not synthetic graph nodes), recurse into nested suites,
    default to COLLAPSED, and sit beside the flowchart in a grid rail that
    stacks on narrow screens. Rows FOCUS the matching graph node on click
    (never navigate); off-path rows are inert and marked unavailable.
    """
    js = (ROOT / "docs" / "js" / "skill-explorer.js").read_text(encoding="utf-8")
    css = (ROOT / "docs" / "css" / "styles.css").read_text(encoding="utf-8")

    # Panel is built from a skill's own suiteComponents, so non-suite/component
    # pages with only suiteRef do not show the roster.
    assert "var suiteListHtml = ''" in js
    assert "collectSuiteList" in js
    assert "if (ownSuiteComponents.length)" in js
    assert "})(ownSuiteComponents, 0);" in js
    # Uses slash-skill names from the component id, not bucket origins or full display names.
    assert "slash: '/' + slug" in js
    assert "var displayName = (entry && entry.name) || slug;" not in js
    assert 'String(compNamedId).split(\'/\').pop()' in js
    # Recurses into nested suites and marks them simply.
    assert "if (nested) collectSuiteList(entry.suiteComponents, listDepth + 1);" in js
    assert "se-suite-list__badge" in js
    # Rendered into a collapsible flow-body rail beside the flowchart canvas,
    # COLLAPSED BY DEFAULT (native <details> with no `open`).
    assert '<details class="se-suite-list" aria-label="Suite components">' in js
    assert '<details class="se-suite-list" open' not in js
    assert 'class="se-flow-body' in js
    assert "se-suite-list__scroll" in js

    # Row click ONLY focuses the matching graph node (via genericSkillRef ->
    # selectFlowNode) and NEVER navigates. No openExplorer from the panel.
    assert "var nodeRef = (entry && entry.genericSkillRef) || '';" in js
    assert "var onPath = !!(nodeRef && relatedNodes[nodeRef]);" in js
    assert "data-focus-node" in js
    assert ".se-suite-list__item[data-focus-node]" in js
    assert "window.selectFlowNode(focusRef);" in js
    # Off-path rows are inert + unobtrusively marked unavailable.
    assert "se-suite-list__item--off" in js
    assert ".se-suite-list__item--off" in css
    assert 'aria-disabled="true"' in js
    # The roster wires no navigation of its own.
    assert "data-suite-nav" not in js
    assert ".se-suite-list__item[data-suite-nav]" not in css
    # The focus click branch must not call openExplorer.
    focus_branch = js[js.index("var suiteRow = e.target.closest"):]
    focus_branch = focus_branch[: focus_branch.index("var node = e.target.closest('.git-node');")]
    assert "openExplorer" not in focus_branch

    # CSS: compact, transparent, outboard rail on wide screens; inline fallback on narrower screens.
    assert ".se-flow-body.has-suite-list {" in css
    assert "position: relative;" in css
    assert "left: calc(100% + .75rem);" in css
    assert "position: absolute;" in css
    assert "background: transparent;" in css
    # Compact + transparent are anchored to the .se-suite-list block itself.
    _panel = css[css.index(".se-suite-list {"): css.index(".se-suite-list__head {")]
    assert "background: transparent;" in _panel
    assert "width: max-content;" in _panel
    assert "left: calc(100% + .75rem);" in _panel
    assert ".se-suite-list__scroll {" in css
    assert "max-height: 260px;" in css
    assert "@media (max-width: 1120px)" in css
    assert "@media (max-width: 760px)" in css
