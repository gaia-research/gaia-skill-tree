# Registry Audit: Non-Generalized / Misattributed Named Skills

**Date:** 2026-09-11 · **Scope:** `registry/named/` · **Mode:** read-only audit ·
**Origin:** gaia-research/gaia-skill-tree#1801, following the rejected intake in #1766
(`hikari9/office-skills`) and the tooling-gap follow-up in #1803.

## Method

Ran the `product-attribution` dimension shipped in #1803
(`scripts/check_product_attribution.py`) against `registry/named/`, then manually
inspected every sibling skill from the two contributors it surfaced
(`k-dense-ai`, `google-deepmind`) to check for the same shape: a named skill whose
body/description documents one specific third-party tool's own commands or API with
no credit to that tool's actual maker anywhere in frontmatter, body, or evidence notes.

This is not a blind sweep of the whole registry — it is bounded to the contributor
clusters where the pattern was already confirmed, per #1801's ask to hold the
**existing** registry to the same bar #1766 was rejected on. A wider sweep across
every contributor is out of scope for this pass; see Non-goals.

## Findings

### Tier A — already confirmed (#1803, not re-litigated here)

These five were the seed set that seeded the `product-attribution` detector; listed
for completeness, no new disposition here.

| Skill | Tool documented | Actual maker | Disposition |
|---|---|---|---|
| `gooseworks/notte-browser` | Notte Browser | Nottelabs | Per #1803 — demote/reclassify candidate (closest to the herdr misattribution pattern) |
| `google-deepmind/pymol` | PyMOL | Schrödinger / Warren DeLano | Per #1803 |
| `google-deepmind/uniprot-database` | UniProt API | UniProt Consortium (EBI/SIB/PIR) | Per #1803 |
| `k-dense-ai/rdkit` | RDKit | Greg Landrum / RDKit community | Per #1803 |
| `k-dense-ai/deepchem` | DeepChem | DeepChem project | Per #1803 |

### Tier B — new, high confidence (same contributor, same shape)

`k-dense-ai` ships ten "X Prompt Wrapper" named skills. Two (`rdkit`, `deepchem`) were
already known. The other eight were checked; six share the identical shape — a
placeholder `## Installation\nAdd installation instructions here.` body, a one-line
description naming the wrapped library, and zero attribution to that library's actual
maintainers anywhere in the file. Two (`qiskit`, `transformers`) are **not** flagged —
their descriptions already name IBM and Hugging Face respectively.

| Skill | Tool documented | Actual maker | Reason flagged | Suggested disposition |
|---|---|---|---|---|
| `k-dense-ai/pymc` | PyMC | PyMC Labs / PyMC Developers | Zero attribution; placeholder body | needs-info — generalize: author real docs body + credit maker |
| `k-dense-ai/pytorch-lightning` | PyTorch Lightning | Lightning AI | Zero attribution; placeholder body | needs-info — same |
| `k-dense-ai/scanpy` | Scanpy | Theis Lab / scverse project | Zero attribution; placeholder body | needs-info — same |
| `k-dense-ai/scvi-tools` | scvi-tools | YosefLab / scverse project | Zero attribution; placeholder body | needs-info — same |
| `k-dense-ai/stable-baselines3` | Stable-Baselines3 | DLR-RM | Zero attribution; placeholder body | needs-info — same |
| `k-dense-ai/torch-geometric` | PyTorch Geometric | PyG Team | Zero attribution; placeholder body | needs-info — same |

All six are 1★ with placeholder bodies, so they also independently trip
`gaia-meta-sweep` dimension 8 (`placeholder-bodies`) — the attribution gap and the
empty-body gap compound rather than being two unrelated defects. **needs-info** rather
than **demote** because there's nothing to demote *from*: these are already floor-rank
stubs. The fix is to author the body (closing the placeholder-bodies finding) with
attribution included, not a separate registry mutation.

All six added to `TOOL_MAKER_MAP` in `scripts/check_product_attribution.py` in this PR,
so `gaia-meta-sweep` dimension 13 now catches them going forward.

### Tier C — lower confidence, different category (needs-info, not demote)

`google-deepmind`'s remaining named skills are almost entirely thin API wrappers over
public government/consortium scientific databases (ChEMBL, ClinVar, dbSNP, Ensembl,
GTEx, InterPro, PDB, PubChem, PubMed, STRING, and others). Most of these **do** name
their operating institution somewhere in the body (EMBL-EBI, NCBI, NIH, etc. —
confirmed by grep across each file), because the resource's own canonical name already
carries the institution ("NCBI's dbSNP", "the EMBL-EBI Ontology Lookup Service"). That
functions as attribution in practice, even without a literal "maintained by" line, and
is a materially different case from Tier A/B's branded commercial/community tools with
*zero* institutional mention anywhere.

A small subset had **zero** hits for any institution name and are worth a human look,
but are flagged at lower confidence than Tier B — the public-resource name itself
already signals provenance in a way `herdr`/PyMOL/RDKit did not, so misattribution risk
here is lower and the fix (if any) is a documentation nicety, not a trust violation:

| Skill | Resource | Operator (not currently named in file) | Suggested disposition |
|---|---|---|---|
| `google-deepmind/gnomad-database` | gnomAD | Broad Institute | needs-info — add one-line attribution |
| `google-deepmind/gtex-database` | GTEx | GTEx Consortium (NIH Common Fund) | needs-info — same |
| `google-deepmind/jaspar-database` | JASPAR | JASPAR Consortium | needs-info — same |
| `google-deepmind/clinical-trials-database` | ClinicalTrials.gov | NIH / National Library of Medicine | needs-info — same |
| `google-deepmind/foldseek-structural-search` | Foldseek | Steinegger Lab / Söding Lab | needs-info — same (1 institutional mention found, borderline) |

**Not** added to `TOOL_MAKER_MAP` in this PR — confidence is lower and false-positive
risk higher than Tier B, so these stay as a documented audit finding for a human (or a
follow-up sweep) to confirm before the automated detector starts flagging them.

Excluded entirely (checked, not flagged): `google-deepmind/alphafold-database-fetch-and-analyze`
and `google-deepmind/alphagenome-single-variant-analysis` (DeepMind's own tools — the
contributor *is* the maker, no misattribution possible); `google-deepmind/protein-sequence-msa`
and `google-deepmind/protein-sequence-similarity-search` (already name EBI/Clustal
Omega/MMseqs2/BLAST in the description); `google-deepmind/uv` (references this repo's
own prerequisite `uv` skill, not a documented third-party product); `google-deepmind/workflow-skill-creator`
(meta-skill, not third-party tool documentation); `k-dense-ai/qiskit` and
`k-dense-ai/transformers` (already credit IBM and Hugging Face respectively).

## Secondary ask — tooling check (already answered in #1803)

Confirmed in #1803: neither `gaia dev audit` nor any of `gaia-meta-sweep`'s original 12
dimensions read named-skill body content against attribution. That gap is closed by
dimension 13, shipped in gaia-research/gaia-skill-tree#1804.

## Non-goals / what this PR does not do

- No registry mutation. Tier B additions to `TOOL_MAKER_MAP` change the *detector's*
  config only — they make dimension 13 catch these six going forward; they do not
  demote, reclassify, or edit any `registry/named/*.md` file.
- No disposition is executed for Tier A (that's #1803's own non-goal, unchanged) or
  Tier C (explicitly held back at lower confidence, pending human confirmation).
- This audit is bounded to the two contributor clusters the seed pattern came from,
  not a registry-wide sweep of every contributor — a wider pass is legitimate
  follow-on work, not this issue's own remainder, since #1801 scoped itself to
  "sweep... for skills that read the same way `herdr`/`office-learnings` did"
  starting from a concrete seed, not an exhaustive audit of all ~800+ named skills.
