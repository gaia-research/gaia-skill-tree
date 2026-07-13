# Source Report — 2026-07-13

## Star Verification

`generate_source_dump.py` completed against the fetched v6.6.1 registry snapshot.

## 6. Adversarial Data Lake Audit Findings (2026-07-13)

Four independent read-only reviewers found the following systemic issues in the pre-existing evidence lake:

- **Tier/rank drift:** tier files do not consistently match current named-skill ranks. This affects entries in tiers 1, 3, 4, 5, and 6; the tier partitions must be regenerated from corrected source data before treating them as rank evidence.
- **Evaluative wording:** reviewers found unsupported qualifiers such as `reliable and efficient`, `high-fidelity`, `state-of-the-art`, `production-grade`, `Most widely adopted`, and `Elite` across tiers 1–6. These must be replaced by source-backed facts.
- **GitHub source formats:** several entries use bare repository URLs, `blob/` directory paths without `SKILL.md`, or a lowercase `skill.md` path. Installable skill references must use the exact `blob/<branch>/<path>/SKILL.md` form.
- **Same-source duplication:** Google DeepMind science-skills entries in tier 2 commonly pair a SKILL.md blob with a bare repository-root row from the same source. These need deduplication or a documented distinction.

The Firecrawl intake candidates are not in the existing lake yet. Their evidence still needs to be collected and verified before rank calibration; no Firecrawl rank has been assigned by this run.
