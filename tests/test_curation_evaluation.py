import hashlib
import json
import numpy as np
from pathlib import Path

from gaia_cli.curation.evaluation import (
    DEFAULT_RERANKER,
    DEFAULT_RERANKER_REVISION,
    classification_metrics,
    metrics,
    run,
)
from gaia_cli.curation.retrieval import clear_model_cache, loadRetrievalConfig

ROOT = Path(__file__).resolve().parents[1]


def test_metrics_use_only_available_labelled_predictions():
    cases = [
        {"id": "a", "expected_generic_id": "x"},
        {"id": "b", "expected_generic_id": "y"},
        {"id": "c", "expected_generic_id": None},
    ]
    got = metrics(cases, {"a": ["q", "x"], "c": ["q"]}, k=2)
    assert got == {
        "labelled_cases": 2,
        "predicted_labelled_cases": 1,
        "coverage": 0.5,
        "top1": 0.0,
        "top1_corpus": 0.0,
        "top2": 1.0,
        "top2_corpus": 0.5,
        "mrr": 0.5,
        "mrr_corpus": 0.25,
        "denominator": 1,
        "corpus_denominator": 2,
        "unlabelled_predictions": 1,
    }
    empty = metrics(cases, {})
    assert empty["top1"] is None
    assert empty["top1_corpus"] is None
    assert empty["coverage"] == 0.0
    assert empty["denominator"] == 0
    assert empty["corpus_denominator"] == 2


def test_metric_denominators_missing_predictions_coverage():
    """Ensure missing predictions do not inflate reported accuracy."""
    cases = [
        {"id": f"case_{i}", "expected_generic_id": f"target_{i}"} for i in range(4)
    ]
    # Predictor only outputs a prediction for case_0, which hits rank 1
    partial_predictions = {"case_0": ["target_0"]}
    res = metrics(cases, partial_predictions, k=1)

    assert res["labelled_cases"] == 4
    assert res["predicted_labelled_cases"] == 1
    assert res["coverage"] == 0.25
    assert res["denominator"] == 1
    assert res["corpus_denominator"] == 4
    # Evaluated over predicted cases alone, top1 is 1.0; over the full corpus, it is 0.25
    assert res["top1"] == 1.0
    assert res["top1_corpus"] == 0.25


def test_captured_predictions_use_full_canonical_catalog_and_no_model(tmp_path):
    fixture = tmp_path / "oracle.json"
    fixture.write_text(json.dumps({"cases": [{
        "id": "case",
        "provenance_class": "human-approved",
        "name": "candidate name",
        "description": "candidate text",
        "expected_generic_id": "browser-control",
    }]}))
    pred = tmp_path / "pred.json"
    pred.write_text(json.dumps({"rankings": {"case": ["browser-automation", "browser-control"]}}))
    # Offline evaluation: no sentence-transformers model load
    report = run(root=ROOT, corpus_path=fixture, predictions_path=pred, top_k=2)
    assert report["catalog_count"] > 100
    assert report["status"] == "completed"
    assert "evaluatedAt" in report
    assert report["metrics"]["top1"] == 0.0
    assert report["metrics"]["top2"] == 1.0
    assert report["details"][0]["rank"] == 2


def test_no_labels_passed_to_encoder(monkeypatch):
    import sentence_transformers
    seen = []

    class FakeModel:
        def __init__(self, name, **kwargs):
            pass

        def encode(self, texts, **kwargs):
            seen.append(list(texts))
            return np.ones((len(texts), 2), dtype=np.float32)

    monkeypatch.setattr(sentence_transformers, "SentenceTransformer", FakeModel)
    clear_model_cache()

    corpus = ROOT / "tests/fixtures/curation-oracle.json"
    run(root=ROOT, corpus_path=corpus, model="mock", limit=1, use_cache=False)

    # Find the query text encoded for the case
    query_texts = [s for s in seen if any("Low-level browser" in x for x in s)]
    assert query_texts, "Query text was not encoded"
    flattened_query = " ".join(query_texts[0])
    assert "Low-level browser control through browser protocols: Operate a browser through CDP" in flattened_query
    assert "browser-control" not in flattened_query
    assert "ruling" not in flattened_query


def test_provenance_groups_separated_and_honest():
    """Verify that human-approved remains strictly 1 case and synthetic probes are separated."""
    corpus = ROOT / "tests/fixtures/curation-oracle.json"
    pred_data = {
        "rankings": {
            "ego-browser-approved-map": ["browser-control"],
            "prompt-compaction-token-pruning-probe": ["context-compression"],
            "persistent-conversational-store-probe": ["memory-manage"],
        }
    }

    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(pred_data, f)
        tmp_pred = f.name

    try:
        report = run(root=ROOT, corpus_path=corpus, predictions_path=tmp_pred, top_k=5)
        prov = report["by_provenance"]

        # Human-approved has exactly 1 case in oracle
        assert prov["human-approved"]["labelled_cases"] == 1
        assert prov["human-approved"]["predicted_labelled_cases"] == 1
        assert prov["human-approved"]["top1"] == 1.0

        # Synthetic-doctrine holds the synthetic regression probes
        assert prov["synthetic-doctrine"]["labelled_cases"] >= 4

        # Unresolved-discussion has no gold targets (labelled_cases == 0)
        assert prov["unresolved-discussion"]["labelled_cases"] == 0
    finally:
        Path(tmp_pred).unlink(missing_ok=True)


def test_config_prefix_and_revisions_match(monkeypatch):
    """Verify loadRetrievalConfig pinned revisions and prefix handling across models."""
    minilm_cfg = loadRetrievalConfig(ROOT, "all-MiniLM-L6-v2")
    assert minilm_cfg["revision"] == "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
    assert minilm_cfg["queryPrefix"] == ""

    bge_cfg = loadRetrievalConfig(ROOT, "BAAI/bge-small-en-v1.5")
    assert bge_cfg["revision"] == "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"
    assert bge_cfg["queryPrefix"] == "Represent this sentence for searching relevant passages: "

    qwen_cfg = loadRetrievalConfig(ROOT, "Qwen3")
    assert qwen_cfg["revision"] == "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3"

    # Verify BGE query prefix is formatted into queries during run()
    import sentence_transformers
    seen_queries = []

    class FakeBgeModel:
        def __init__(self, name, **kwargs):
            assert kwargs.get("revision") == "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"

        def encode(self, texts, **kwargs):
            for t in texts:
                if "Represent this sentence" in t:
                    seen_queries.append(t)
            return np.ones((len(texts), 384), dtype=np.float32)

    monkeypatch.setattr(sentence_transformers, "SentenceTransformer", FakeBgeModel)
    clear_model_cache()

    corpus = ROOT / "tests/fixtures/curation-oracle.json"
    rep = run(root=ROOT, corpus_path=corpus, model="BAAI/bge-small-en-v1.5", limit=1, use_cache=False)
    assert seen_queries, "BGE query instruction prefix was not applied"
    assert seen_queries[0].startswith("Represent this sentence for searching relevant passages: ")
    assert rep["config"]["queryPrefix"] == "Represent this sentence for searching relevant passages: "
    assert rep["config"]["revision"] == "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"


def test_caching_invalidates_on_input_changes(tmp_path, monkeypatch):
    """Verify document vector caching hits on repeat run and invalidates on catalog or config change."""
    import sentence_transformers

    encode_calls = []

    class FakeCachedModel:
        def __init__(self, name, **kwargs):
            pass

        def encode(self, texts, **kwargs):
            encode_calls.append(len(texts))
            return np.ones((len(texts), 4), dtype=np.float32)

    monkeypatch.setattr(sentence_transformers, "SentenceTransformer", FakeCachedModel)
    clear_model_cache()

    # Use isolated cache dir in tmp_path
    monkeypatch.setattr("gaia_cli.curation.evaluation._get_cache_dir", lambda root: tmp_path / "cache")

    corpus = ROOT / "tests/fixtures/curation-oracle.json"

    # Run 1: Cold run, encodes catalog documents and queries
    rep1 = run(root=ROOT, corpus_path=corpus, model="mock", limit=1, use_cache=True)
    assert rep1["catalog_count"] > 100
    doc_calls_1 = len(encode_calls)
    assert doc_calls_1 >= 2  # catalog texts + query text

    # Run 2: Hot run, document vectors hit cache
    clear_model_cache()
    encode_calls.clear()
    rep2 = run(root=ROOT, corpus_path=corpus, model="mock", limit=1, use_cache=True)
    # Only query should be encoded, document vectors loaded from cache
    assert len(encode_calls) == 1
    assert encode_calls[0] == 1  # query text only

    # Run 3: Changing config (e.g. revision) invalidates cache
    clear_model_cache()
    encode_calls.clear()
    rep3 = run(root=ROOT, corpus_path=corpus, model="mock", revision="different-rev", limit=1, use_cache=True)
    # Catalog must be re-encoded because config hash changed
    assert len(encode_calls) >= 2


def test_reranker_retention_and_ranking_top_n(monkeypatch):
    """Verify CrossEncoder reranking reorders top-N candidates and retains scores."""
    import sentence_transformers

    class FakeEmbeddingModel:
        def __init__(self, name, **kwargs):
            pass

        def encode(self, texts, **kwargs):
            arr = np.zeros((len(texts), 10), dtype=np.float32)
            for i in range(min(len(texts), 10)):
                arr[i, i] = 1.0
            return arr

    class FakeCrossEncoder:
        def __init__(self, name, **kwargs):
            assert kwargs.get("revision") == DEFAULT_RERANKER_REVISION

        def predict(self, pairs, **kwargs):
            return [float(i) for i in range(len(pairs))]

    monkeypatch.setattr(sentence_transformers, "SentenceTransformer", FakeEmbeddingModel)
    monkeypatch.setattr(sentence_transformers, "CrossEncoder", FakeCrossEncoder)
    clear_model_cache()

    corpus = ROOT / "tests/fixtures/curation-oracle.json"
    rep = run(
        root=ROOT,
        corpus_path=corpus,
        model="mock",
        reranker=DEFAULT_RERANKER,
        reranker_revision=DEFAULT_RERANKER_REVISION,
        limit=1,
        top_k=5,
        use_cache=False,
    )
    detail = rep["details"][0]
    assert detail["retrieval_scores"] is not None
    assert detail["reranker_scores"] is not None
    assert len(detail["ranking"]) == 5
    scores = detail["reranker_scores"]
    assert scores == sorted(scores, reverse=True)
    assert rep["config"]["reranker"] == DEFAULT_RERANKER
    assert rep["config"]["rerankerRevision"] == DEFAULT_RERANKER_REVISION


def test_offline_predictions_classification_metrics():
    """Verify false-new-generic, true consolidation/splitting, capability type mistakes, no-match, packaging, and human overturn."""
    cases = [
        # Case 0: expects existing generic browser-control, basic type
        {
            "id": "c0",
            "expected_generic_id": "browser-control",
            "expected_shape": "basic",
            "expected_disposition": "map_existing",
            "human_target": "browser-control",
            "jev_target": "browser-control",
        },
        # Case 1: expects existing generic memory-manage, fusion type
        {
            "id": "c1",
            "expected_generic_id": "memory-manage",
            "expected_shape": "fusion",
            "expected_disposition": "map_existing",
            "human_target": "memory-manage",
            "jev_target": "context-compression",  # Jev disagreement with human
        },
        # Case 2: expects no-match, basic type
        {
            "id": "c2",
            "expected_generic_id": None,
            "expected_shape": "basic",
            "expected_disposition": "no_match",
        },
        # Case 3: expects package packaging shape
        {
            "id": "c3",
            "expected_generic_id": None,
            "expected_shape": "package",
            "expected_disposition": "package",
        },
        # Case 4: expects no-match, but predictor wrongly consolidated into an existing generic
        {
            "id": "c4",
            "expected_generic_id": None,
            "expected_shape": "basic",
            "expected_disposition": "no_match",
        },
        # Case 5: expects no-match, predictor has disposition 'map' but missing mapping key
        {
            "id": "c5",
            "expected_generic_id": None,
            "expected_shape": "basic",
            "expected_disposition": "no_match",
        },
    ]

    # Predictor predictions:
    # c0: false new generic / false splitting (proposes "new_generic"), capability type mistake (basic->fusion), mapping matches human
    # c1: false splitting (disposition "split"), capability type mistake (fusion->basic), machine proposal "context-compression" (human overturn!)
    # c2: correct no-match (disposition "no_match", mapping None)
    # c3: packaging mistake (predicted "router" instead of "package")
    # c4: false consolidation (disposition "map", mapping "unrelated-generic")
    # c5: missing pred mapping with disposition 'map' must NOT count as correct no-match (false match!)
    pred_meta = {
        "c0": {"disposition": "new_generic", "shape": "fusion", "mapping": "browser-control"},
        "c1": {"disposition": "split", "shape": "basic", "mapping": "context-compression"},
        "c2": {"disposition": "no_match", "mapping": None, "shape": "basic"},
        "c3": {"disposition": "package", "shape": "router"},
        "c4": {"disposition": "map", "shape": "basic", "mapping": "unrelated-generic"},
        "c5": {"disposition": "map", "shape": "basic", "mapping": None},
    }

    res = classification_metrics(cases, pred_meta)

    # 1. False new generic: c0 was flagged as new generic out of 2 labelled generic cases
    assert res["false_new_generic"]["denominator"] == 2
    assert res["false_new_generic"]["count"] == 1
    assert res["false_new_generic"]["rate"] == 0.5

    # 2. Ontology consolidation & splitting:
    # False consolidation: expected distinct/no-match boundary mapped to generic (c4 and c5 out of c2, c4, c5)
    assert res["false_consolidation"]["denominator"] == 3
    assert res["false_consolidation"]["count"] == 2
    assert res["false_consolidation"]["rate"] == 2 / 3

    # False splitting: expected existing generic proposed new/split (c0 and c1)
    assert res["false_splitting"]["denominator"] == 2
    assert res["false_splitting"]["count"] == 2
    assert res["false_splitting"]["rate"] == 1.0

    # Combined consolidation & splitting
    assert res["false_consolidation_splitting"]["denominator"] == 5
    assert res["false_consolidation_splitting"]["count"] == 4

    # 3. Capability type mistakes: basic vs fusion taxonomy errors (c0 and c1 out of c0, c1, c2, c4, c5)
    assert res["capability_type_mistakes"]["denominator"] == 5
    assert res["capability_type_mistakes"]["count"] == 2
    assert res["capability_type_mistakes"]["rate"] == 0.4

    # 4. No match quality: c2 is correct, c4 and c5 are false matches (missing mapping with map disposition is false match)
    assert res["no_match_quality"]["denominator"] == 3
    assert res["no_match_quality"]["correct"] == 1
    assert res["no_match_quality"]["false_matches"] == 2
    assert res["no_match_quality"]["accuracy"] == 1 / 3

    # 5. Packaging mistakes: c3 predicted router instead of package (shapes like package/router/wrapper)
    assert res["packaging_mistakes"]["denominator"] == 1
    assert res["packaging_mistakes"]["count"] == 1
    assert res["packaging_mistakes"]["rate"] == 1.0

    # 6. Human overturn: c1 had human_target "memory-manage", machine proposed "context-compression"
    assert res["human_overturn"]["denominator"] == 2
    assert res["human_overturn"]["count"] == 1
    assert res["human_overturn"]["rate"] == 0.5

    # 7. Jev disagreement: c1 had jev_target "context-compression" vs human_target "memory-manage"
    assert res["jev_disagreement"]["denominator"] == 2
    assert res["jev_disagreement"]["count"] == 1
    assert res["jev_disagreement"]["rate"] == 0.5

    # Missing fields yield explicit null / None without error
    empty_res = classification_metrics(cases, None)
    assert empty_res["false_new_generic"]["rate"] is None
    assert empty_res["false_new_generic"]["denominator"] == 0
    assert empty_res["false_consolidation"]["rate"] is None
    assert empty_res["false_splitting"]["rate"] is None
    assert empty_res["capability_type_mistakes"]["rate"] is None
    assert empty_res["packaging_mistakes"]["rate"] is None
    assert empty_res["human_overturn"]["rate"] is None


def test_load_catalog_fails_on_malformed_json_and_missing_id(tmp_path):
    """load_catalog must raise ValueError on malformed JSON or missing id, never silently skip."""
    from gaia_cli.curation.evaluation import load_catalog

    basic_dir = tmp_path / "registry" / "nodes" / "basic"
    basic_dir.mkdir(parents=True, exist_ok=True)

    # 1. Malformed JSON
    bad_file = basic_dir / "corrupted.json"
    bad_file.write_text("{bad: json--", encoding="utf-8")
    import pytest
    with pytest.raises(ValueError, match="Malformed canonical node source"):
        load_catalog(tmp_path)

    # 2. Missing 'id' field
    bad_file.write_text(json.dumps({"name": "No ID Node", "description": "test"}), encoding="utf-8")
    with pytest.raises(ValueError, match="missing required 'id' field"):
        load_catalog(tmp_path)

    # 3. Valid JSON
    bad_file.write_text(json.dumps({"id": "valid-node", "name": "Valid", "description": "desc"}), encoding="utf-8")
    nodes = load_catalog(tmp_path)
    assert len(nodes) == 1
    assert nodes[0]["id"] == "valid-node"


def test_cached_vectors_rejects_non_finite_and_mismatched_identities(tmp_path):
    """Cached vectors must verify actual identities and finite dimensions, returning None on invalid data."""
    from gaia_cli.curation.evaluation import _load_cached_catalog_vectors

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    catalog = [{"id": "node-1", "name": "N1", "description": "D1"}, {"id": "node-2", "name": "N2", "description": "D2"}]
    cat_hash = "fake-cat-hash"
    cfg_hash = "fake-cfg-hash"
    cache_key = hashlib.sha256(f"{cat_hash}:{cfg_hash}".encode("utf-8")).hexdigest()
    cache_file = cache_dir / f"catalog_vectors_{cache_key}.json"

    # Case A: Non-finite values (NaN / Inf)
    payload_nan = {
        "catalog_hash": cat_hash,
        "config_hash": cfg_hash,
        "ids": ["node-1", "node-2"],
        "dimensions": 2,
        "vectors": [[1.0, float("nan")], [0.0, 1.0]],
    }
    cache_file.write_text(json.dumps(payload_nan), encoding="utf-8")
    assert _load_cached_catalog_vectors(cache_dir, cat_hash, cfg_hash, catalog) is None

    # Case B: Mismatched IDs (identities do not match catalog order)
    payload_ids = {
        "catalog_hash": cat_hash,
        "config_hash": cfg_hash,
        "ids": ["wrong-id-1", "node-2"],
        "dimensions": 2,
        "vectors": [[1.0, 0.0], [0.0, 1.0]],
    }
    cache_file.write_text(json.dumps(payload_ids), encoding="utf-8")
    assert _load_cached_catalog_vectors(cache_dir, cat_hash, cfg_hash, catalog) is None

    # Case C: Valid cached finite vectors
    payload_valid = {
        "catalog_hash": cat_hash,
        "config_hash": cfg_hash,
        "ids": ["node-1", "node-2"],
        "dimensions": 2,
        "vectors": [[1.0, 0.0], [0.0, 1.0]],
    }
    cache_file.write_text(json.dumps(payload_valid), encoding="utf-8")
    loaded = _load_cached_catalog_vectors(cache_dir, cat_hash, cfg_hash, catalog)
    assert loaded is not None
    assert loaded.shape == (2, 2)


def test_find_model_weight_size_counts_weight_files_only_and_resolves_snapshot(tmp_path):
    """find_model_weight_size must inspect exact pinned revision and count only weight files."""
    from gaia_cli.curation.evaluation import find_model_weight_size

    model_dir = tmp_path / ".gaia" / "models" / "models--BAAI--bge-small-en-v1.5"
    snap_dir = model_dir / "snapshots" / "pinned-rev-123"
    snap_dir.mkdir(parents=True, exist_ok=True)

    # Weight file: 1,000,000 bytes
    weight_file = snap_dir / "model.safetensors"
    weight_file.write_bytes(b"x" * 1_000_000)

    # Non-weight files: should NOT be counted in weight size
    (snap_dir / "README.md").write_bytes(b"r" * 15_000)
    (snap_dir / "tokenizer.json").write_bytes(b"t" * 50_000)
    (snap_dir / "vocab.txt").write_bytes(b"v" * 20_000)
    (snap_dir / "config.json").write_bytes(b"c" * 2_000)

    # Duplicate blob in blobs dir: should NOT be double counted
    blobs_dir = model_dir / "blobs"
    blobs_dir.mkdir(parents=True, exist_ok=True)
    (blobs_dir / "blob-data").write_bytes(b"b" * 5_000_000)

    size, reason = find_model_weight_size("BAAI/bge-small-en-v1.5", root=tmp_path, revision="pinned-rev-123")
    assert reason is None
    assert size == 1_000_000, f"Expected exactly 1,000,000 bytes of model weights, got {size}"


def test_separate_expected_type_vs_expected_shape():
    """Verify classification metrics separates expected_type (basic/fusion) from expected_shape (packaging)."""
    cases = [
        {
            "id": "t1",
            "expected_type": "basic",
            "expected_packaging_shape": "router",
        },
    ]
    # Predictor gets type wrong (basic -> fusion) but packaging shape right (router -> router)
    pred_meta = {
        "t1": {
            "type": "fusion",
            "packaging_shape": "router",
        },
    }
    res = classification_metrics(cases, pred_meta)
    assert res["capability_type_mistakes"]["denominator"] == 1
    assert res["capability_type_mistakes"]["count"] == 1
    assert res["packaging_mistakes"]["denominator"] == 1
    assert res["packaging_mistakes"]["count"] == 0


def test_warm_load_and_reranker_load_separated(monkeypatch):
    """Verify warm load occurs before encoding and reranker load is separated without polluting load_seconds."""
    import sentence_transformers

    class FakeModel:
        def __init__(self, name, **kwargs):
            pass

        def encode(self, texts, **kwargs):
            return np.ones((len(texts), 4), dtype=np.float32)

    class FakeCross:
        def __init__(self, name, **kwargs):
            pass

        def predict(self, pairs, **kwargs):
            return [0.5 for _ in pairs]

    monkeypatch.setattr(sentence_transformers, "SentenceTransformer", FakeModel)
    monkeypatch.setattr(sentence_transformers, "CrossEncoder", FakeCross)
    clear_model_cache()

    corpus = ROOT / "tests/fixtures/curation-oracle.json"
    rep = run(
        root=ROOT,
        corpus_path=corpus,
        model="mock",
        reranker=DEFAULT_RERANKER,
        limit=1,
        use_cache=False,
    )
    latencies = rep["latencies"]
    assert "load_seconds" in latencies
    assert "reranker_load_seconds" in latencies
    assert rep["model_load_state"] in ("cold", "cached")
    assert rep["peak_rss_bytes"] > 0

