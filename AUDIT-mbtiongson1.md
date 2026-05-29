# mbtiongson1 named-skill meta audit

Audit run: 2026-05-30. Surface: `registry/named/mbtiongson1/` (14 entries).

## Cross-cutting findings

- **Case-mismatched `links.github`:** 7 named skills point at `/SKILL.md` (uppercase) when the on-disk file is `skill.md` (lowercase). GitHub raw paths are case-sensitive, so those URLs 404. Star Bar miss for every skill at 3★+.
- **Wrong-target `links.github`:** 3 named skills point at unrelated directories (`gaia-curate`, `gaia-curate`, `gaia-curate`).
- **Empty bodies:** Every named-skill markdown has the placeholder `## Installation\nAdd installation instructions here.` (51 chars) and nothing else.
- **`contributor: testuser`** in every timeline entry — should be `mbtiongson1`.
- **`origin: false`** on 7 first-party gaia-* curation skills that originated in this repo.

## Per-skill plan

| Named skill | Action | Generic ref | Level | `origin` | `links.github` |
|---|---|---|---|---|---|
| `gaia-audit` | Fix link casing, backfill body | `gaia-audit` ✓ | 3★ ✓ | true ✓ | `.../skill.md` |
| `gaia-bot-curate` | Fix link casing, flip origin, backfill | `registry-curation` ✓ | 3★ ✓ | **true** | `.../skill.md` |
| `gaia-curate` | Fix link casing, backfill | `registry-curation` ✓ | 4★ ✓ | true ✓ | `.../skill.md` |
| `gaia-curation-review` | Remap, fix link, flip origin, backfill | **`gaia-audit`** | 3★ ✓ | **true** | own dir `.../skill.md` |
| `gaia-docs-sync` | Remap, flip origin, backfill | **`registry-curation`** | 2★ ✓ | **true** | (already correct) |
| `gaia-draft-curate` | Fix link casing, flip origin, backfill | `registry-curation` ✓ | 3★ ✓ | **true** | `.../skill.md` |
| `gaia-integrity` | Flip origin, backfill | `registry-curation` ✓ | 3★ ✓ | **true** | (already correct) |
| `gaia-meta-audit` | Fix link casing, **demote level**, backfill | `gaia-meta-audit` ✓ | **3★** (was 4★) | true ✓ | `.../skill.md` |
| `gaia-preview` | Remap, fix link target, flip origin, backfill | **`deployment-automation`** | 2★ ✓ | **true** | own dir `.../SKILL.md` |
| `gaia-triage` | Remap, flip origin, backfill | **`issue-triage`** | 2★ ✓ | **true** | (already correct) |
| `gaia-wiki-sync` | Remap, fix link casing, flip origin, backfill | **`registry-curation`** | 2★ ✓ | **true** | `.../skill.md` |
| `graphify-triage` | Remap, flip origin, backfill | **`issue-triage`** | 3★ ✓ | **true** | (already correct) |
| `research` | **Remove** — no `.agents/skills/research/` exists, origin claim unsupported | — | — | — | — |
| `web-scrape` | **Remove** — `.agents/skills/scrape/` is empty, no implementation | — | — | — | — |

## Canonical promotions to set

After the named-skill cleanup:

- `registry-curation` → `promotedNamedSkillId: mbtiongson1/gaia-curate`
- `gaia-audit` → `promotedNamedSkillId: mbtiongson1/gaia-audit`
- `gaia-meta-audit` → `promotedNamedSkillId: mbtiongson1/gaia-meta-audit`

## Fusion candidates (post-cleanup)

The remapped registry-curation cluster is still tight:
`gaia-bot-curate` + `gaia-curate` + `gaia-draft-curate` + `gaia-integrity` + `gaia-docs-sync` + `gaia-wiki-sync` (6 specialized phases). Recommend `/gaia-fuse-full-suite mbtiongson1` once the cluster is stable. Defer to user.

## Commits planned

1. `chore(audit): track mbtiongson1 named-skill audit plan` (this doc, opens draft PR)
2. `feat(named): remove unsupported research and web-scrape claims [skip-gen]`
3. `fix(named): correct links.github casing + wrong-target URLs [skip-gen]`
4. `chore(named): flip origin: true for first-party gaia-* curation skills [skip-gen]`
5. `feat(named): remap genericSkillRef on misclassified skills [skip-gen]`
6. `chore(named): demote gaia-meta-audit named claim to 3★ to match canonical [skip-gen]`
7. `docs(named): backfill bodies + correct testuser timeline contributor [skip-gen]`
8. `chore(graph): set promotedNamedSkillId on registry-curation/gaia-audit/gaia-meta-audit [skip-gen]`
9. `chore: gaia docs build + gaia validate after meta-audit [skip-gen]`
