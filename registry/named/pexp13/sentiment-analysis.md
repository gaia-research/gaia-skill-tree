---
id: pexp13/sentiment-analysis
name: Sentiment Analysis
contributor: pexp13
origin: true
genericSkillRef: sentiment-analysis
status: awakened
level: 1★
description: 'Classifies the affective polarity (positive / negative / neutral, or
  fine-grained) of user-generated text. Covers the full pipeline from raw noisy input
  through preprocessing, inference, and output normalisation. Stack is intentionally
  tool-agnostic — three implementation tracks are documented below.

  '
createdAt: '2026-05-17'
updatedAt: '2026-07-05'
trustMagnitude: 0.0
overallTrustGrade: ungraded
apexGateStatus:
  aGradedOriginsGte5: false
  sourceTenureDaysGte180AorS: false
  directNestedSuiteGte1: false
  depth2OnlyReachableGte1: false
  overallGradeS: false
  apexPromotionPrSigned: false
  crossOrgVerifier: null
  systemWideCap: null
timeline:
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:19Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-19T09:26:06Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://aclanthology.org/S17-2088/ (type: peer-review)'
- timestamp: '2026-06-19T09:26:24Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://arxiv.org/abs/2202.03829 (type: arxiv)'
- timestamp: '2026-06-19T09:26:57Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://ojs.aaai.org/index.php/ICWSM/article/view/14550
    (type: peer-review)'
- timestamp: '2026-06-19T09:27:15Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://arxiv.org/abs/2203.01054 (type: arxiv)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T09:29:08Z'
  details: TM 0.0 -> 45.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T09:34:47Z'
  details: TM 45.0 -> 192.8, grade C -> A (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 192.8, grade ungraded -> A (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:43Z'
  details: TM 0.0 -> 192.8, grade ungraded -> A (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:35Z'
  action: rank_up
  contributor: mbtiongson1
  details: Level updated from 2★ to 4★ per G7 final rankings calibration.
- timestamp: '2026-06-26T18:30:56Z'
  action: note
  contributor: unknown
  details: Updated GitHub link to https://github.com/pexp13/basic-nlp-text-processor-python/blob/main/SKILL.md
- timestamp: '2026-07-04T18:06:12Z'
  action: evidence_removed
  contributor: unknown
  details: 'Removed dead/invalid evidence: https://aclanthology.org/S17-2088/'
- timestamp: '2026-07-04T18:06:17Z'
  action: evidence_removed
  contributor: unknown
  details: 'Removed dead/invalid evidence: https://arxiv.org/abs/2202.03829'
- timestamp: '2026-07-04T18:06:22Z'
  action: evidence_removed
  contributor: unknown
  details: 'Removed dead/invalid evidence: https://ojs.aaai.org/index.php/ICWSM/article/view/14550'
- timestamp: '2026-07-04T18:06:27Z'
  action: evidence_removed
  contributor: unknown
  details: 'Removed dead/invalid evidence: https://arxiv.org/abs/2203.01054'
evidence: []
verification:
  firstEvidenceAt: '2026-06-19T09:26:06Z'
trustMagnitudeInputHash: null
links: {}
---

## Implementation

### Pipeline stages

1. **Ingestion & normalisation** — strip HTML/markup, decode emojis to text tokens or
   drop them per domain policy, lower-case, collapse repeated punctuation.
2. **Language detection** — route multilingual corpora to language-specific models or
   a multilingual backbone; flag low-confidence detections for human review.
3. **Inference** — see stack options below.
4. **Confidence filtering** — discard or escalate predictions below a calibrated
   threshold (typically 0.65–0.75 probability); do not force a label on ambiguous text.
5. **Output normalisation** — map raw scores to a stable schema
   (`{label, score, model_version, input_len}`); store model version alongside each
   prediction to enable reproducible re-scoring after model updates.

---

### Stack options

#### Track A — Transformer-based (recommended for accuracy)

Use `cardiffnlp/twitter-roberta-base-sentiment-latest` or `nlptown/bert-base-multilingual-uncased-sentiment` (5-class) as backbone, or a domain-fine-tuned checkpoint. Serve via HuggingFace `pipeline("text-classification")` for batch jobs, vLLM or TGI for latency-sensitive APIs. For inputs > 512 tokens, split into overlapping windows and aggregate by majority vote or mean-pooled logits — do not silently truncate. Highest accuracy on informal and ironic text; GPU preferred; inference cost scales with throughput.

#### Track B — Lexicon-based (interpretable, zero-shot)

VADER covers English social media out of the box with negation handling and intensifier boosting; alternatives include SentiWordNet, AFINN, or domain-specific word lists. No training data required, CPU-only, fast — but degrades on domain-specific jargon and sarcasm. Compound score threshold needs tuning per corpus.

#### Track C — Instruction-tuned LLM (flexible, slower)

Prompt a chat-capable model with a structured classification prompt requesting JSON output with `label` and `rationale` fields. Best suited for low-volume pipelines, aspect-based SA, or cases where explanations are required alongside labels. Cache identical inputs and use batch APIs to control cost; fall back to Track A for high-volume paths.

---

### Aspect-based extension (optional)

For reviews requiring per-aspect scores (e.g. *price*, *delivery*, *quality*), extract aspect spans with an NER or dependency-parse step, run sentiment inference per span rather than over the full review, then aggregate to a per-aspect sentiment vector alongside an overall label.

---

### Evaluation

Benchmark on a held-out set that mirrors production distribution.
Standard metrics: **macro-F1** (primary), accuracy, and confusion matrix.
Report separately for each star-rating bucket or domain slice if data permits.
Minimum acceptable macro-F1 on SST-2 or equivalent: **0.88** for Track A,
**0.72** for Track B.

---

## Evidence

> All evidence rows rerouted to the starless generic node (`sentiment-analysis`) per issue #934 — generic SA literature, not specific to this implementation. Inherited via `genericSkillRef: sentiment-analysis`.
