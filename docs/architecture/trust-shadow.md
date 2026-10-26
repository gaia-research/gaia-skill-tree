# Yggdrasil IV Trust Magnitude Shadow Evaluation & Corpus Census

**Specification and Architecture Guide**  
**Status:** Shadow Diagnostic Seam (P1/P2 Implementation)  
**Ratification Context:** [Yggdrasil IV Ratification (2026-10-25)](../../founder/YGGDRASIL_IV_RATIFICATION_2026-10-25.md), [RFC #2148](../../docs/rfc-2148-trust-degradation.md)  
**Module Ownership:** `src/gaia_cli/shadowCorpus.py`, `src/gaia_cli/commands/shadow_cmd.py`  
**Consumes:** `src/gaia_cli/shadowEvaluation.py` (`evaluateShadow`, `evaluateShadowRegistry`, `ShadowEvaluationContext`)  

---

## 1. Overview & Purpose

Yggdrasil IV establishes challenge-driven, reversible trust governance. A core requirement of RFC #2148 is the complete separation of **observation**, **shadow recalculation**, **governance adjudication**, and **canonical publication**.

`gaia shadow` provides an offline, read-only census and shadow evaluation replay over the entire registry corpus without mutating canonical sources (`registry/nodes/`, `registry/named/`), timelines (`skill-trees/`), schemas, or public site-served artifacts (`docs/`).

### Invariants
1. **Zero Canonical Mutation:** Under no circumstances does shadow replay write to canonical frontmatter, user skill-trees, or public generated docs.
2. **Explicit Context:** Scoring functions perform zero network I/O and rely exclusively on an immutable caller-supplied `ShadowEvaluationContext`.
3. **Fail-Closed Census & Complete Inventory:** Scans all 398 named skills (including both `status: named` and `status: awakened`) and all 299 generic JSON nodes, reconciling `yaml.safe_load` and `load_yaml_simple` rather than silently skipping corrupted records.
4. **Transparent Unknown Accounting:** Unresolvable references, temporal anomalies, and unknown verifier standings are logged honestly as `not-evaluated` or warnings; no unknown is coerced to `0` or used to force demotion.
5. **Concurrent Mutation Detection:** Pre-evaluation and post-evaluation file digest manifests catch concurrent filesystem modifications.
6. **Output Path Safeguards:** Output is strictly rejected if aimed at canonical or public repository paths (`registry/`, `docs/`, `skill-trees/`, `src/`).

> **Independent Review Notice:** The underlying shadow evaluation engine (`src/gaia_cli/shadowEvaluation.py`) is subject to ongoing independent review and repair (addressing stale stored peer-review grades for S-witness, raw-vs-bounded row contributions, partial corpus abort, nonfinite inputs, and dedup comparator precision). Shadow diagnostic outputs are **provisional comparisons**, not verified authoritative numbers for production publication.

---

## 2. Explicit Evaluation Context

Every calculation runs against a frozen, reproducible context snapshot defined in `ShadowEvaluationContext`:

```python
@dataclass(frozen=True)
class ShadowEvaluationContext:
    evaluationAtUTC: datetime.datetime      # Timezone-aware UTC evaluation clock (e.g. 2026-10-25T00:00:00Z)
    policyVersion: str                      # Current trust policy version (e.g. 'g7-v1')
    policyDigest: str                       # SHA-256 digest of registry/schema/meta.json
    benchmarkCatalog: dict[str, Any]        # Canonical benchmark catalog from registry/benchmark-sources.json
    benchmarkCatalogDigest: str             # SHA-256 digest of benchmark catalog payload
    registryRevision: str                   # Git commit SHA of the examined checkout
    canonicalInputDigest: str               # Combined SHA-256 digest of all registry input files
    genericSkillMap: dict[str, dict]        # Complete generic nodes map {nodeId: nodeDict}
    namedSkillMap: dict[str, dict]          # Complete named skills map {skillId: skillDict}
    verifierStanding: dict[str, bool]       # Mapping of verifier IDs to boolean active standing
    perRowGradeThresholds: dict[str, Any]   # Per-evidence-type floors from meta.json
    gradeCeiling: dict[str, str]            # Per-type grade ceilings (S/A/B/C) from meta.json
    gradeThresholds: dict[str, float]       # Overall Trust Grade floors (S: 250, A: 100, B: 50, C: 20)
```

Scoring is deterministic: identical inputs and evaluation timestamps yield identical cryptographic fingerprints across runs.

---

## 3. Complete Registry Census & Parser Reconciliation

### 3.1 Census Scope
The repository contains records across multiple statuses and legacy migration boundaries:
- **398 Named Markdown Records:** Located in `registry/named/**/*.md`.
  - 350 active named skills (`status: named`)
  - 48 awakened legacy skills (`status: awakened`)
- **299 Generic JSON Nodes:** Located in `registry/nodes/**/*.json`.
- **613 Named Evidence Rows** and **254 Generic Evidence Rows**.
- **347 Frontmatter Cache Hashes:** Records carrying `trustMagnitudeInputHash`.

### 3.2 Parser Reconciliation
Legacy tooling exhibits parser divergence:
- `TrustCalibrationDriftSensor` splits on `"---"` and calls `yaml.safe_load(parts[1])`.
- `registryMaps.buildMergedSkillMap` uses regex `split_frontmatter` and calls `load_yaml_simple(fmText)`.
- `buildMergedSkillMap` silently skips unparseable JSON/markdown files and skips records where `status != "named"`.

`gaia shadow` executes both parsers on every record, compares the parsed dictionary structures, and reports any discrepancies. When `--fail-closed` is passed, syntax errors or invalid JSON immediately flag `isValid: false` and prevent misleading partial appraisal.

---

## 4. Seam Coordination & Cause Classification

### 4.1 Coordinating the Seam
The initial shadow engine aborts evaluation of the entire registry if a single record fails context validation or contains a future date.

`shadowCorpus.py` coordinates this seam:
1. It attempts `evaluateShadowRegistry(skills, context)`.
2. If `evaluateShadowRegistry` returns `evaluated` or `partial`, its assessments are consumed directly.
3. If `evaluateShadowRegistry` aborts with `not-evaluated` due to an isolated invalid record or dependency cycle, the runner switches to topological per-record evaluation:
   - Sorts skills topologically: components before containing suites.
   - Evaluates each ready skill via `evaluateShadow(skill, context)`.
   - Records honest `not-evaluated` statuses with exact diagnostic reasons for failing records without erasing valid coverage for the rest of the corpus.
   - Propagates evaluated component grades into downstream suite Apex evaluations using an accumulated `computedNamed` map.

### 4.2 RFC §10/§11 Implementation Correction Causes
The shadow evaluator classifies divergence between legacy production TM and corrected shadow TM into four distinct implementation-correction causes:

| Cause Key | Trigger Condition | Classification |
|---|---|---|
| `source-only-inheritance-merge` | Raw source-string dedup collapses distinct Evidence Types or drops sourceless rows under `genericSkillRef`. | `implementation-correction` |
| `eligibility-before-dedup` | Dedup winner selection runs before catalog/lane eligibility checks, allowing an ineligible high-score row to mask an eligible lower one. | `implementation-correction` |
| `component-before-suite-grade` | Suite Apex gate reads stored component grades from frontmatter rather than recomputing component grades within the same evaluation context. | `implementation-correction` |
| `named-row-grade-context` | Named evidence rows graded without suite/generic context, or `trustNumber` fallback grades leakage into gate predicates (`gateGradeRisk`). | `implementation-correction` |

---

## 5. CLI Usage & Safeguards

### 5.1 Command Interface
`gaia shadow` is a top-level discoverable read-only command:

```bash
# Run shadow census and print human impact summary to stdout
python -m gaia_cli shadow --stdout

# Output machine JSON and summary to local ignored scratch
python -m gaia_cli shadow --output-dir generated-output/shadow

# Run with explicit evaluation time and fail-closed integrity
python -m gaia_cli shadow --at 2026-10-25T00:00:00Z --fail-closed --output-dir .gaia/shadow

# Output machine JSON directly to stdout for piping
python -m gaia_cli shadow --json
```

### 5.2 Command Flags
- `--registry <path>`: Local registry path (default: `.`).
- `--at <iso-time>`: Pinned UTC evaluation datetime (default: `2026-10-25T00:00:00Z`).
- `--output-dir <path>`: Explicit directory to write `shadow-report.json` and `shadow-summary.txt`.
- `--stdout`: Print readable impact summary to stdout.
- `--json`: Print deterministic machine JSON report to stdout.
- `--fail-closed`: Exit non-zero if parse errors, unresolvable records, or unhandled cycles occur.
- `--filter-status <status>`: Narrow evaluation to a specific status subset (e.g. `'named'` or `'awakened'`).

### 5.3 Output Path Safeguards
Writing shadow output into canonical or public directories is strictly forbidden. `validateOutputPath` raises a `ValueError` if output targets:
- `registry/`
- `docs/`
- `skill-trees/`
- `src/`
- `.agents/skills/`, `.claude/skills/`
- `.github/`

Allowed targets include external system paths (e.g. `/tmp/shadow`) or explicitly permitted ignored local directories (`.gaia/`, `generated-output/`, `.tmp/`).

---

## 6. Full Corpus Shadow Replay Receipt (Baseline Snapshot)

Executed against repository revision `a496dbf7a4d1c9a13ea0c64f4f86bffc1dc1ccb2` pinned at `2026-10-25T00:00:00Z`:

```text
================================================================================
GAIA YGGDRASIL IV TRUST MAGNITUDE — SHADOW REPLAY & REGISTRY CENSUS
================================================================================
NOTICE: Read-only shadow diagnostic output. Zero canonical writes performed.
Core engine under independent review; results are provisional, not authoritative.
--------------------------------------------------------------------------------
Pinned UTC Evaluation Time : 2026-10-25T00:00:00+00:00
Registry Revision          : a496dbf7a4d1c9a13ea0c64f4f86bffc1dc1ccb2
Engine Version             : gaia-tm-shadow-v1
Policy Version             : g7-v1 (digest: 964bfef4842f...)
Benchmark Catalog Digest   : 503a0ead7156...
Canonical Input Digest     : f6f9569e2147...
--------------------------------------------------------------------------------
REGISTRY CENSUS OVERVIEW:
  Total Named Records       : 398
  Status Subsets            : {'named': 350, 'awakened': 48}
  Total Generic Nodes       : 299
  Named Evidence Rows       : 613
  Generic Evidence Rows     : 254
  Frontmatter Cache Hashes  : 347
  Parse Failures            : 0
  Parser Discrepancies      : 0
  Unresolved Generic Refs   : 0
  Dependency Cycles         : 22
  Temporal Anomalies        : 0
--------------------------------------------------------------------------------
SHADOW REPLAY EVALUATION:
  Overall Status            : evaluated
  Evaluated Skills          : 398 / 398
  Not-Evaluated Skills      : 0
  Implementation TM Deltas  : 4 skills with TM delta != 0
  Grade Changes             : 1 skills change Overall Trust Grade
--------------------------------------------------------------------------------
STAR CEILING PROPOSALS VS STORED CANONICAL STARS:
  Ceiling < Stored Stars    : 39 (provisional demotion risk)
  Ceiling == Stored Stars   : 345 (neutral)
  Ceiling > Stored Stars    : 14 (provisional promotion headroom)
--------------------------------------------------------------------------------
RFC §10/§11 IMPLEMENTATION CORRECTION CAUSES TRIGGERED:
  1. source-only-inheritance-merge : 31 skills
  2. eligibility-before-dedup      : 0 skills
  3. component-before-suite-grade  : 2 skills
  4. named-row-grade-context       : 98 skills
--------------------------------------------------------------------------------
RISK & INTEGRITY AUDIT:
  Gate Grade Risks (trustNum fallbacks) : 0 skills
  Temporal Date Warnings                : 0
  Input Manifest Verification           : CLEAN (no concurrent mutation)
================================================================================
```

### Full Corpus Machine Receipt Pointers
- Machine JSON: `generated-output/shadow/shadow-report.json` (7.8 MB)
- Text Summary: `generated-output/shadow/shadow-summary.txt` (2.6 KB)

---

## 7. Limitations & Governance Seam

1. **Informational Only:** The shadow evaluator generates proposals and cause classifications; it possesses zero mutation authority. Any eventual star adjustment or frontmatter update requires Class C approval and dedicated CLI verbs (`gaia dev calibrate`).
2. **Engine Repair Dependency:** While the census and seam runner are complete and fully tested, the numerical scoring arithmetic in `shadowEvaluation.py` remains under independent review.
3. **Fusion Score Separation:** Fusion Score is purely structural (`gaia_cli.fusionScore`) and remains completely invariant across evidence and trust magnitude recalculations.
