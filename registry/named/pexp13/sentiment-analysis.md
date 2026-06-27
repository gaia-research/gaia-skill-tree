---
id: pexp13/sentiment-analysis
name: Sentiment Analysis
contributor: pexp13
origin: true
genericSkillRef: sentiment-analysis
status: awakened
level: 4★
description: 'Classifies the affective polarity (positive / negative / neutral, or
  fine-grained) of user-generated text. Covers the full pipeline from raw noisy input
  through preprocessing, inference, and output normalisation. Stack is intentionally
  tool-agnostic — three implementation tracks are documented below.

  '
createdAt: '2026-05-17'
updatedAt: '2026-06-27'
trustMagnitude: 192.8
overallTrustGrade: A
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
evidence:
- source: https://aclanthology.org/S17-2088/
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: SemEval-2017 Task 4 (Twitter SA benchmark) — ACL Anthology; establishes macro-F1
    as primary metric for sentiment analysis
  reviewers: 3
  grade: S
- source: https://arxiv.org/abs/2202.03829
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: arxiv
  class: A
  notes: CardiffNLP Twitter-RoBERTa-base-sentiment (Barbieri et al., 2022) — SOTA
    transformer baseline for social-media SA (arXiv:2202.03829)
  citations: 200
  grade: B
- source: https://ojs.aaai.org/index.php/ICWSM/article/view/14550
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: VADER (Hutto & Gilbert, 2014) — canonical lexicon-based SA baseline; AAAI/ICWSM;
    validated on social media corpora
  reviewers: 3
  grade: B
- source: https://arxiv.org/abs/2203.01054
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: arxiv
  class: A
  notes: Aspect-Based Sentiment Analysis survey (Zhang et al., 2022) — covers ABSA
    methods for structured review analysis (arXiv:2203.01054)
  citations: 89
verification:
  firstEvidenceAt: '2026-06-19T09:26:06Z'
trustMagnitudeInputHash: 0fe967fac44ef008cb3a675f5da2775693274cff366b4bfaf33bd2bf9112e728
links:
  github: https://github.com/pexp13/basic-nlp-text-processor-python/blob/main/SKILL.md
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

| Source | Relevance |
|--------|-----------|
| [SemEval-2017 Task 4](https://aclanthology.org/S17-2088/) | Standard Twitter sentiment benchmark; establishes macro-F1 as primary metric |
| [CardiffNLP Twitter-RoBERTa (Barbieri et al., 2022)](https://arxiv.org/abs/2202.03829) | SOTA transformer baseline for social-media SA; 3-class, multilingual variants available |
| [VADER (Hutto & Gilbert, 2014)](https://ojs.aaai.org/index.php/ICWSM/article/view/14550) | Canonical lexicon-based baseline; validated on social media corpora |
| [NLPTown BERT multilingual](https://huggingface.co/nlptown/bert-base-multilingual-uncased-sentiment) | 5-class (star-rating) model fine-tuned on product reviews; direct UGC applicability |
| [SST-2 (GLUE benchmark)](https://gluebenchmark.com/tasks) | Standard binary SA benchmark for cross-model comparison |
| [Aspect-Based SA survey (Zhang et al., 2022)](https://arxiv.org/abs/2203.01054) | Covers ABSA methods for structured review analysis |
| [declare-lab/awesome-sentiment-analysis](https://github.com/declare-lab/awesome-sentiment-analysis) | Curated reading list by DeCLaRe Lab; anchored by Poria et al. (2020) IEEE TAC survey on open challenges |
| [declare-lab/conv-emotion](https://github.com/declare-lab/conv-emotion) | Sentiment/emotion recognition in conversations (MELD, IEMOCAP); relevant for threaded comment SA |
