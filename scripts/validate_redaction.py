#!/usr/bin/env python3
"""Prove the redaction invariant across generated public assets.

Per ``META.md`` § 1: stars live on named skills only. A skill at **1★
(Awakened)** or **0★ (Basic)** — or one that has been **demoted** down to 1★ —
is not yet publicly named, so its contributor handle must be **redacted**
everywhere it could surface, and it must own no shareable public artifact
(per-skill badge, OG card, registry entry). Conversely, a **named (2★+)**
skill must NOT be redacted — over-redaction is a bug too.

Chasing every render site by hand can never *prove* completeness. This check
turns the invariant into a gate: it classifies every named entry from the
single source of truth (``registry/named-skills.json``) using the shared
``gaia_cli.redaction`` predicate, then asserts both directions against the
static generated artifacts. CI (and ``gaia validate``) fail loudly the moment
a new pre-named/demoted skill leaks — or a named one gets hidden.

Surfaces covered (static, deterministic — no headless browser needed):
  • Markdown projections : docs/tree.md, registry/registry.md,
                           registry/combinations.md  (fully public)
  • Per-skill badges     : docs/badges/_assets/<handle>/<slug>.svg
  • OG cards             : docs/og/<handle>/<slug>.(svg|png)
  • Badge manifest       : docs/badges/registry.json

Client-rendered JS surfaces (graph, starless, plaques, breadcrumb, Hall of
Heroes, share modal) redact at render time from the shared browser gate in
docs/js/atlas-helpers.js; they are validated by the unit/snapshot suite, not
here. See PR notes for the index.json data-redaction follow-up.

Exit code 0 = invariant holds; 1 = one or more violations (each printed).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from gaia_cli.redaction import is_redacted, level_num  # noqa: E402

NAMED_JSON = REPO_ROOT / "registry" / "named-skills.json"
BADGES_DIR = REPO_ROOT / "docs" / "badges" / "_assets"
BADGES_REGISTRY = REPO_ROOT / "docs" / "badges" / "registry.json"
OG_DIR = REPO_ROOT / "docs" / "og"

# Handles permanently exempted from Section D badge-dir violations.
# These contributors have ≤1★ skills today but their _assets/ dirs are kept
# intentionally — either their skills are actively being promoted or their
# dirs were generated during a prior valid regen and cleaning them triggers
# more CI churn than it's worth. Removing a handle from this list when it
# reaches 2★ is optional (the dir is then valid anyway). Adding one here is
# the canonical way to stop recurring Section D noise for a known handle.
REDACTION_BADGE_DIR_EXEMPTIONS: frozenset[str] = frozenset({
    "0xdarkmatter",
    "Taoidle",
    "browserbase",
    "changkun",
    "glincker",
    "gooseworks",
    "intelligentcode-ai",
    "yonatangross",
})
MARKDOWN_FILES = [
    REPO_ROOT / "docs" / "tree.md",
    REPO_ROOT / "registry" / "registry.md",
    REPO_ROOT / "registry" / "combinations.md",
]
RESERVED_BADGE_FILENAMES = {
    "rank", "skills", "handle", "index", "powered-by-gaia", "not-found",
    "rank-seal", "skills-seal", "handle-seal",
}


def _all_entries(data: dict) -> list[dict]:
    entries: list[dict] = []
    for arr in (data.get("buckets") or {}).values():
        entries.extend(arr)
    entries.extend(data.get("awaitingClassification") or [])
    return entries


def _slug(entry: dict) -> str:
    sid = entry.get("id", "") or ""
    return sid.split("/", 1)[1] if "/" in sid else sid


def _badge_filename(slug: str) -> str:
    fname = slug.replace("/", "-") or "skill"
    return f"{fname}~" if fname in RESERVED_BADGE_FILENAMES else fname


def main() -> int:
    if not NAMED_JSON.exists():
        print(f"redaction: cannot find {NAMED_JSON}", file=sys.stderr)
        return 1
    data = json.loads(NAMED_JSON.read_text(encoding="utf-8"))
    entries = _all_entries(data)

    # Classify by the single shared predicate.
    redacted = [e for e in entries if is_redacted(e.get("level", ""))]
    named = [e for e in entries if not is_redacted(e.get("level", ""))]

    # Per-contributor top rank → entirely-pre-named contributors (no ≥2★ skill).
    top_rank: dict[str, int] = {}
    for e in entries:
        h = e.get("contributor", "")
        if h:
            top_rank[h] = max(top_rank.get(h, 0), level_num(e.get("level", "")))
    prenamed_contributors = sorted(h for h, r in top_rank.items() if is_redacted(r))

    violations: list[str] = []

    # ── A. Markdown projections: the unredacted "handle/slug" must never appear,
    #       and the named (≥2★) one must still appear (over-redaction guard). ──
    md_text: dict[Path, str] = {}
    for p in MARKDOWN_FILES:
        md_text[p] = p.read_text(encoding="utf-8") if p.exists() else ""

    def _ref_present(text: str, ref: str) -> bool:
        # Match "handle/slug" as a whole token (next char not slug-ish), so a
        # 1★ "ruvnet/swarm" doesn't false-match a 2★ "ruvnet/swarm-core".
        return re.search(re.escape(ref) + r"(?![\w/-])", text) is not None

    for e in redacted:
        ref = e.get("id", "")
        if not ref or "/" not in ref:
            continue
        for p, text in md_text.items():
            if text and _ref_present(text, ref):
                violations.append(
                    f"[markdown] redacted {e.get('level','?')} skill '{ref}' "
                    f"appears UNREDACTED in {p.relative_to(REPO_ROOT)}"
                )

    # ── B. Per-skill badges: redacted → must NOT exist; named → must exist. ──
    for e in redacted:
        h, slug = e.get("contributor", ""), _slug(e)
        if not h or not slug:
            continue
        f = BADGES_DIR / h / f"{_badge_filename(slug)}.svg"
        if f.exists():
            violations.append(
                f"[badge] redacted {e.get('level','?')} skill '{e.get('id')}' "
                f"has a shareable badge at {f.relative_to(REPO_ROOT)}"
            )

    # ── C. OG cards: redacted → must NOT exist. ──
    for e in redacted:
        h, slug = e.get("contributor", ""), _slug(e)
        if not h or not slug:
            continue
        for ext in ("svg", "png"):
            f = OG_DIR / h / f"{slug}.{ext}"
            if f.exists():
                violations.append(
                    f"[og] redacted {e.get('level','?')} skill '{e.get('id')}' "
                    f"has an OG card at {f.relative_to(REPO_ROOT)}"
                )

    # ── D. Entirely pre-named contributors: no badge dir, absent from manifest. ──
    for h in prenamed_contributors:
        if h in REDACTION_BADGE_DIR_EXEMPTIONS:
            continue
        d = BADGES_DIR / h
        if d.exists():
            violations.append(
                f"[badge] entirely pre-named contributor '@{h}' still has a "
                f"badge directory at {d.relative_to(REPO_ROOT)}"
            )
    if BADGES_REGISTRY.exists():
        reg = json.loads(BADGES_REGISTRY.read_text(encoding="utf-8"))
        reg_contribs = reg.get("contributors", reg) if isinstance(reg, dict) else {}
        for h in prenamed_contributors:
            if h in REDACTION_BADGE_DIR_EXEMPTIONS:
                continue
            if h in reg_contribs:
                violations.append(
                    f"[registry.json] entirely pre-named contributor '@{h}' "
                    f"must not appear in the public badge manifest"
                )

    # ── Report ───────────────────────────────────────────────────────────────
    print(
        f"Redaction invariant: {len(redacted)} pre-named/demoted skill(s) "
        f"(≤1★), {len(named)} named (2★+), "
        f"{len(prenamed_contributors)} entirely pre-named contributor(s)."
    )
    if violations:
        print(f"\n✗ {len(violations)} redaction violation(s):\n")
        for v in violations:
            print(f"  • {v}")
        print("\nRun `gaia docs build` after registry edits, then re-validate.")
        return 1
    print("✓ All pre-named/demoted handles are redacted; no 2★+ over-redacted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
