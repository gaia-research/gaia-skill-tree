# Curation retrieval oracle

`python scripts/curation_benchmark.py` measures generic retrieval without registry writes. It reads the complete current canonical generic node corpus from `registry/nodes/{basic,fusion}` (299 canonical nodes), never restricts catalog candidates to oracle targets, and only encodes candidate name/description (`"{name}: {description}"`). Expected labels and targets are strictly excluded from model input.

## Architecture and Retrieval Alignment

- **Canonical Configuration**: Model configurations are loaded from `src/gaia_cli/data/curation/retrieval.json` via `loadRetrievalConfig`, matching production runtime. Models include:
  - `all-MiniLM-L6-v2`: Production baseline (revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, pooling `mean`, dimensions 384, empty query prefix).
  - `BAAI/bge-small-en-v1.5`: Modern compact challenger (revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, pooling `cls`, dimensions 384, query prefix `"Represent this sentence for searching relevant passages: "`).
  - `Qwen/Qwen3-Embedding-0.6B` (`Qwen3`): Optional experimental candidate (revision `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3`, pooling `last_token`, dimensions 1024).
- **Reranker**: Optional CrossEncoder reranker `cross-encoder/ms-marco-MiniLM-L-6-v2` pinned to revision `233902d25c440f23af6f7d6e94d2946bac0bee0a` via CLI `--reranker-revision`. Evaluates pairs across top retrieval candidates and re-orders results while retaining both retrieval cosine scores and cross-encoder reranker scores.
- **Production Embedding APIs**: Uses `embed_skills` for catalog documents and `embed_query` for candidate queries, ensuring that query instruction prefixes (e.g. BGE's prefix) and pooling normalizations are applied identically to production.
- **Document Vector Caching**: Evaluated document vectors are cached in the ignored directory `generated-output/curation/cache/`. The cache key is a deterministic SHA-256 hash of the complete sorted generic catalog and the effective retrieval configuration (`catalog_hash` + `config_hash`). Writes are atomic via `tempfile` and `os.replace`. Caching automatically invalidates whenever catalog nodes or retrieval configuration parameters change.
- **Hardware & Termux Boundedness**: Default `batch_size` is bounded at 16. The verified portable inference contract uses evaluation mode and one CPU thread (`--threads 1`). Native Android Torch 2.11 produced repeat-query drift with multiple threads; pre-contract measurements and vector caches are invalid. Latencies are split into `load_seconds` (warm load via shared `getSentenceTransformer`), `reranker_load_seconds` (separated from model load), `document_seconds`, `query_seconds`, and `rerank_seconds`. `model_load_state` records `"cold"` vs `"cached"`. Peak RSS is reported as exact normalized bytes in `peak_rss_bytes` (avoiding ambiguous platform units). Model weight size is measured in `model_weight_bytes` by inspecting the pinned revision snapshot path and counting actual parameter tensors (`.safetensors`, `.bin`), strictly excluding READMEs, tokenizers, vocabularies, configs, and duplicate cache blobs.

## Provenance and Oracle Integrity

The evaluation fixture at `tests/fixtures/curation-oracle.json` contains 14 cases with strictly segregated provenance:

1. **`human-approved` (1 case)**:
   - Only 1 real historical human L4 adjudicated case exists: issue #1677's L4 approval of `citrolabs/ego-browser` into `browser-control` at 2★.
   - This single human case remains completely honest. It is never conflated with synthetic probes or unadjudicated discussions.
2. **`synthetic-doctrine` (regression probes)**:
   - Self-contained synthetic probes authored from repository doctrine, covering shapes `basic`, `fusion`, `package`, and `router`, as well as orthogonal `no_match` cases.
   - Includes real canonical generic targets (`browser-control`, `context-compression`, `memory-manage`, `route-intent`) with natural descriptions that avoid trivial token name echoing.
   - Probes are strictly labelled `synthetic-doctrine` and never called human.
3. **`unresolved-discussion` (open issues)**:
   - Historical open questions (e.g. #1675 context-mode retrieval complaints, #1483 product coupling RFC, #1922 assurance sensors).
   - Expected generic ID is `null`, preventing unresolved debates from being treated as fabricated negative or positive targets.

### Diagnostic Suite Disclosure (No Model Migration Justified)

**Important**: This 14-case oracle is a diagnostic regression suite designed to validate harness correctness, test latency and memory footprints, and detect boundary drift. **No production model migration (e.g. MiniLM to BGE or Qwen) is justified from a tiny diagnostic corpus alone.** Real architectural migrations require larger real-world curation evaluation batches, end-to-end Termux performance verification, and formal human L4 adjudication.

## Offline Predictions and Classification Metrics

For offline evaluation or sidecar analysis, pass `--predictions FILE`. The predictions file can provide candidate rankings as well as per-case metadata (`disposition`, `shape`, `mapping`, `humanTarget`, `jevTarget`).

The harness computes classification metrics **only on cases with explicitly labelled fields**, reporting an explicit denominator and returning `null` when fields are absent or denominator is 0 (no manufactured metrics):

- **`false_new_generic`**: Cases where an existing generic was expected but the predictor proposed a new generic. Denominator: labelled generic cases with predicted disposition/mapping.
- **`false_consolidation`**: Cases where a distinct / no-match boundary was expected but the predictor consolidated it into an existing or disallowed generic. Denominator: labelled no-match/distinct cases with predicted disposition/mapping.
- **`false_splitting`**: Cases where an existing generic was expected but the predictor proposed a new generic or split. Denominator: labelled generic cases with predicted disposition/mapping.
- **`false_consolidation_splitting`**: Sum of ontology consolidation and splitting errors across generic boundary decisions.
- **`capability_type_mistakes`**: Evaluates basic vs fusion taxonomy misclassifications. Segregated from ontology consolidation/splitting and packaging shapes.
- **`no_match_quality`**: Evaluates whether orthogonal capabilities with no existing generic are correctly identified as `no_match`. Missing prediction mapping when disposition is `map` is strictly counted as a false match, never credited as a correct no-match.
- **`packaging_mistakes`**: Evaluates agreement on artifact packaging shapes (`package`, `router`, `wrapper`, `suite`), separating `expected_type` (basic/fusion) from `expected_shape`.
- **`human_overturn`**: Cases where human target is labelled and the automated proposal or Jev target differs.
- **`jev_disagreement`**: Cases where Jev target and human target (or machine mapping) differ.

To prevent inflated accuracy when predictions cover only a few easy cases, retrieval metrics report both `denominator` (count of predicted labelled cases) and `corpus_denominator` (total labelled cases in corpus), along with `coverage` and corpus-denominated metrics (`top1_corpus`, `topk_corpus`, `mrr_corpus`).

## Environment Diagnostics (Doctor)

`python scripts/environment/doctor.py` provides lightweight verification without importing heavy ML packages:

- **Receipt Discovery by Schema**: Locates evaluation receipts in `generated-output/curation/` by schema (`corpus_sha256`, `catalog_sha256`, `config`), rather than matching arbitrary filename substrings (e.g. `minilm-report.json`, `bge-report.json`).
- **Encoder Configuration & Hash Verification**: Compares encoder identity (`model`, `revision`, `backend`, `dimensions`, `normalize`, `pooling`, `queryPrefix`), the deterministic `encoder_contract` stamp, reranker presence/revision, thread setting, and SHA-256 hashes of the corpus fixture and canonical generic catalog. `reranker`-bearing runs are not accepted as matching a non-reranked default config.
- **Baseline-Gated Regression Reporting**: Reports `time` and `metrics` regression status against an explicit baseline receipt (`all-MiniLM-L6-v2`) only; returns `unknown` when no explicit baseline exists.
- **Artifact Freshness**: `--check-artifact` correctly fails with status code 1 and outputs the mismatch reason when embeddings are stale.
- **Termux & Hardware Proof**: Requires genuine Android runtime verification via Python Android API (`sys.getandroidapilevel`) or `/system` filesystem markers (`/system/build.prop`), alongside `aarch64` CPU architecture. Fake environment variables (`TERMUX_VERSION`) on non-Android platforms are rejected as `non-termux`. Smoke receipts reject missing fingerprints and incomplete semantic configs.
- **Dependency Integrity**: Verifies `torch` and `numpy` for the selected `torch` backend without importing them at diagnostic preflight.

## Runnable Compare Commands

Run baseline production evaluation:
```sh
python scripts/curation_benchmark.py --model all-MiniLM-L6-v2 --output generated-output/curation/minilm_report.json
```

Run challenger compact model with declared instruction prefix and pinned revision:
```sh
python scripts/curation_benchmark.py --model BAAI/bge-small-en-v1.5 --output generated-output/curation/bge_report.json
```

Run baseline with cross-encoder reranker on Termux (1 CPU thread, batch size 16):
```sh
python scripts/curation_benchmark.py \
  --model all-MiniLM-L6-v2 \
  --reranker cross-encoder/ms-marco-MiniLM-L-6-v2 \
  --reranker-revision 233902d25c440f23af6f7d6e94d2946bac0bee0a \
  --threads 1 \
  --batch-size 16 \
  --output generated-output/curation/minilm_reranked_report.json
```

Run offline prediction evaluation without loading ML models:
```sh
python scripts/curation_benchmark.py \
  --predictions path/to/predictions.json \
  --output generated-output/curation/offline_report.json
```

Compare outputs between baseline and challenger:
```sh
python -c "
import json
m = json.load(open('generated-output/curation/minilm_report.json'))
b = json.load(open('generated-output/curation/bge_report.json'))
print('MiniLM top1:', m['metrics']['top1'], 'mrr:', m['metrics']['mrr'])
print('BGE    top1:', b['metrics']['top1'], 'mrr:', b['metrics']['mrr'])
"
```
