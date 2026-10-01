"""Offline, provenance-aware evaluation for curation semantic retrieval."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import resource
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASELINE = "all-MiniLM-L6-v2"
CHALLENGER = "BAAI/bge-small-en-v1.5"
DEFAULT_RERANKER = "cross-encoder/ms-marco-MiniLM-L-6-v2"
DEFAULT_RERANKER_REVISION = "233902d25c440f23af6f7d6e94d2946bac0bee0a"


def sha256_file(path: str | Path) -> str:
    """Compute deterministic SHA-256 digest of file contents."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_catalog(root: str | Path) -> list[dict[str, str]]:
    """Read the complete active GENERIC-only canonical node set from source nodes."""
    root = Path(root)
    nodes: dict[str, dict[str, str]] = {}
    for kind in ("basic", "fusion"):
        node_dir = root / "registry" / "nodes" / kind
        if not node_dir.is_dir():
            continue
        for path in sorted(node_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                raise ValueError(f"Malformed canonical node source at {path}: {exc}") from exc
            if not isinstance(data, dict):
                raise ValueError(f"Canonical node source at {path} must be a JSON object")
            sid = data.get("id")
            if not sid:
                raise ValueError(f"Canonical node source at {path} missing required 'id' field")
            nodes[sid] = {
                "id": sid,
                "name": str(data.get("name", sid)),
                "description": str(data.get("description", "")),
            }
    if not nodes:
        raise ValueError(f"no generic canonical nodes found under {root / 'registry/nodes'}")
    return [nodes[k] for k in sorted(nodes)]


def find_model_weight_size(
    model_id: str | None,
    root: str | Path | None = None,
    revision: str | None = None,
) -> tuple[int | None, str | None]:
    """Inspect local cache directories to measure model weight size in bytes.

    Counts actual weight parameter files (.safetensors, .bin, etc.) at the pinned
    revision snapshot, strictly ignoring READMEs, tokenizers, vocabularies, configs,
    and duplicate cache blobs.

    Returns:
        (size_in_bytes, None) if files are found and accessible.
        (None, reason_str) if not found or inaccessible.
    """
    if not model_id or model_id == "mock":
        return None, "Offline or mock model; no local weight files"

    base_dirs: list[Path] = []
    if root:
        base_dirs.append(Path(root) / ".gaia" / "models")
    base_dirs.append(Path.cwd() / ".gaia" / "models")
    try:
        from gaia_cli.curation.retrieval import getModelCacheDir
        base_dirs.append(getModelCacheDir())
    except Exception:
        pass
    base_dirs.append(Path.home() / ".gaia" / "models")
    base_dirs.append(Path.home() / ".cache" / "huggingface" / "hub")
    for env_var in ("HF_HOME", "HUGGINGFACE_HUB_CACHE"):
        val = os.environ.get(env_var)
        if val:
            p = Path(val)
            base_dirs.append(p / "hub" if env_var == "HF_HOME" else p)

    # De-duplicate while preserving order
    unique_base_dirs: list[Path] = []
    for b in base_dirs:
        try:
            rb = b.resolve()
            if rb not in unique_base_dirs and b.is_dir():
                unique_base_dirs.append(b)
        except Exception:
            if b.is_dir() and b not in unique_base_dirs:
                unique_base_dirs.append(b)

    norm = model_id.replace("/", "--")
    folder_candidates = [f"models--{norm}"]
    if "/" not in model_id:
        folder_candidates.append(f"models--sentence-transformers--{norm}")
    folder_candidates.extend([norm, model_id])

    weight_extensions = {".safetensors", ".bin", ".onnx", ".pt", ".pth", ".msgpack", ".h5", ".ot"}

    for base in unique_base_dirs:
        for fname in folder_candidates:
            repo_dir = base / fname
            if not repo_dir.is_dir():
                continue

            snapshots_dir = repo_dir / "snapshots"
            target_snapshot_dir: Path | None = None
            if snapshots_dir.is_dir():
                if revision and (snapshots_dir / revision).is_dir():
                    target_snapshot_dir = snapshots_dir / revision
                else:
                    snaps = [s for s in snapshots_dir.iterdir() if s.is_dir()]
                    if snaps:
                        snaps.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                        target_snapshot_dir = snaps[0]

            eval_dir = target_snapshot_dir if target_snapshot_dir else repo_dir
            weight_files = [
                f for f in eval_dir.rglob("*")
                if f.is_file()
                and f.suffix.lower() in weight_extensions
                and "blobs" not in f.parts
                and not f.name.startswith("tokenizer")
            ]
            if weight_files:
                total = sum(f.stat().st_size for f in weight_files)
                if total > 0:
                    return total, None

    return None, f"Local model weight files not found for '{model_id}' in cache directories"


def _get_cache_dir(root: str | Path) -> Path:
    """Return cache directory for evaluation document vectors."""
    cache_dir = Path(root) / "generated-output" / "curation" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _compute_config_hash(cfg: dict[str, Any]) -> str:
    """Deterministic hash of retrieval configuration fields influencing embeddings."""
    payload = {
        "backend": cfg.get("backend", "torch"),
        "dimensions": cfg.get("dimensions"),
        "modelId": cfg.get("modelId") or cfg.get("defaultModel"),
        "normalize": bool(cfg.get("normalize", True)),
        "pooling": cfg.get("pooling", "mean"),
        "queryPrefix": cfg.get("queryPrefix") or cfg.get("query_prefix", ""),
        "revision": cfg.get("revision"),
        "textTemplate": cfg.get("textTemplate") or cfg.get("text_template", "{name}: {description}"),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _load_cached_catalog_vectors(
    cache_dir: Path,
    catalog_hash: str,
    config_hash: str,
    catalog: list[dict[str, str]],
) -> Any | None:
    """Attempt to load cached document vectors matching catalog hash and config hash."""
    cache_key = hashlib.sha256(f"{catalog_hash}:{config_hash}".encode("utf-8")).hexdigest()
    cache_file = Path(cache_dir) / f"catalog_vectors_{cache_key}.json"
    if not cache_file.is_file():
        return None
    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        if data.get("catalog_hash") != catalog_hash:
            return None
        if data.get("config_hash") != config_hash:
            return None
        # Check actual identities match catalog order exactly
        expected_ids = [s["id"] for s in catalog]
        if data.get("ids") != expected_ids:
            return None
        vectors = data.get("vectors")
        if not isinstance(vectors, list) or len(vectors) != len(catalog):
            return None
        if len(vectors) == 0:
            return None

        import numpy as np
        arr = np.array(vectors, dtype=np.float32)
        if arr.ndim != 2:
            return None
        if arr.shape[0] != len(catalog):
            return None
        if arr.shape[1] <= 0:
            return None

        # Verify stored dimensions matches actual array column count
        stored_dim = data.get("dimensions")
        if stored_dim is not None and stored_dim != arr.shape[1]:
            return None

        # Finite dimension check: all vector values must be finite (no NaN, no Inf)
        if not np.isfinite(arr).all():
            return None
        return arr
    except Exception:
        return None


def _save_cached_catalog_vectors_atomic(
    cache_dir: Path,
    catalog_hash: str,
    config_hash: str,
    cfg: dict[str, Any],
    catalog: list[dict[str, str]],
    vectors: Any,
) -> None:
    """Atomically cache catalog document vectors using tempfile and os.replace."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.sha256(f"{catalog_hash}:{config_hash}".encode("utf-8")).hexdigest()
    cache_file = cache_dir / f"catalog_vectors_{cache_key}.json"
    vec_list = vectors.tolist() if hasattr(vectors, "tolist") else [list(v) for v in vectors]
    payload = {
        "cache_key": cache_key,
        "catalog_hash": catalog_hash,
        "config_hash": config_hash,
        "modelId": cfg.get("modelId"),
        "dimensions": len(vec_list[0]) if vec_list else cfg.get("dimensions"),
        "ids": [s["id"] for s in catalog],
        "vectors": vec_list,
    }
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=cache_dir,
            prefix="cat_vec_",
            suffix=".tmp",
            delete=False,
            encoding="utf-8",
        ) as f:
            tmp_path = Path(f.name)
            json.dump(payload, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, cache_file)
    except Exception:
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def classification_metrics(
    cases: list[dict[str, Any]],
    predictions_meta: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Compute classification metrics strictly on cases with labelled fields.

    Calculates:
      - false_new_generic
      - false_consolidation (no-match boundary mapped to generic)
      - false_splitting (existing generic proposed new)
      - false_consolidation_splitting
      - capability_type_mistakes (basic vs fusion taxonomy errors)
      - no_match_quality
      - packaging_mistakes (package vs router vs wrapper shapes)
      - human_overturn
      - jev_disagreement

    Every metric reports explicit count, explicit denominator, and rate (or null if denominator is 0).
    """
    if not predictions_meta:
        return {
            "false_new_generic": {"count": 0, "denominator": 0, "rate": None},
            "false_consolidation": {"count": 0, "denominator": 0, "rate": None},
            "false_splitting": {"count": 0, "denominator": 0, "rate": None},
            "false_consolidation_splitting": {"count": 0, "denominator": 0, "rate": None},
            "capability_type_mistakes": {"count": 0, "denominator": 0, "rate": None},
            "no_match_quality": {"correct": 0, "false_matches": 0, "denominator": 0, "accuracy": None},
            "packaging_mistakes": {"count": 0, "denominator": 0, "rate": None},
            "human_overturn": {"count": 0, "denominator": 0, "rate": None},
            "jev_disagreement": {"count": 0, "denominator": 0, "rate": None},
        }

    # 1. False new generic: expected existing generic, predictor proposed new generic
    fng_count = 0
    fng_denom = 0
    for c in cases:
        meta = predictions_meta.get(c["id"])
        if not meta:
            continue
        exp_target = c.get("expected_generic_id")
        exp_disp = (c.get("expected_disposition") or "").lower()
        pred_disp = (meta.get("disposition") or "").lower() if meta.get("disposition") else None
        pred_map = meta.get("mapping")
        if (exp_target is not None or exp_disp in ("map", "map_existing")) and (pred_disp is not None or pred_map is not None):
            fng_denom += 1
            if pred_disp in ("new_generic", "new", "novel") or pred_map in ("new", "new_generic"):
                fng_count += 1

    # 2. False consolidation: expected no-match / distinct boundary, mapped to generic
    fc_count = 0
    fc_denom = 0
    for c in cases:
        meta = predictions_meta.get(c["id"])
        if not meta:
            continue
        exp_target = c.get("expected_generic_id")
        exp_disp = (c.get("expected_disposition") or "").lower()
        pred_disp = (meta.get("disposition") or "").lower() if meta.get("disposition") else None
        pred_map = meta.get("mapping")

        is_no_match = exp_target is None and exp_disp in ("no_match", "no-match", "novel", "orthogonal", "distinct")
        if is_no_match and (pred_disp is not None or pred_map is not None or "mapping" in meta or "disposition" in meta):
            fc_denom += 1
            mapped_to_generic = False
            if pred_disp in ("map", "map_existing", "mapped", "consolidate"):
                mapped_to_generic = True
            elif pred_map is not None and str(pred_map).lower() not in ("none", "no_match", "no-match", "novel", "reject", "unresolved", "new", "new_generic", ""):
                mapped_to_generic = True
            if mapped_to_generic:
                fc_count += 1

    # 3. False splitting: expected existing generic, proposed NEW
    fs_count = 0
    fs_denom = 0
    for c in cases:
        meta = predictions_meta.get(c["id"])
        if not meta:
            continue
        exp_target = c.get("expected_generic_id")
        exp_disp = (c.get("expected_disposition") or "").lower()
        pred_disp = (meta.get("disposition") or "").lower() if meta.get("disposition") else None
        pred_map = meta.get("mapping")

        if (exp_target is not None or exp_disp in ("map", "map_existing")) and (pred_disp is not None or pred_map is not None):
            fs_denom += 1
            if pred_disp in ("new_generic", "new", "novel", "split") or pred_map in ("new", "new_generic"):
                fs_count += 1

    fcs_count = fc_count + fs_count
    fcs_denom = fc_denom + fs_denom

    # 4. Capability type mistakes: basic vs fusion taxonomy mistakes
    type_mistakes = 0
    type_denom = 0
    for c in cases:
        meta = predictions_meta.get(c["id"])
        if not meta:
            continue
        exp_type = c.get("expected_type")
        if not exp_type:
            cand = c.get("expected_shape")
            if cand and cand.strip().lower() in ("basic", "fusion", "basic_or_fusion_skill"):
                exp_type = cand

        pred_type = meta.get("type")
        if not pred_type:
            cand_pred = meta.get("shape")
            if cand_pred and cand_pred.strip().lower() in ("basic", "fusion", "basic_or_fusion_skill"):
                pred_type = cand_pred

        if exp_type is not None and pred_type is not None:
            e_norm = exp_type.strip().lower()
            p_norm = pred_type.strip().lower()
            if e_norm and p_norm:
                type_denom += 1
                if e_norm != p_norm:
                    if e_norm == "basic_or_fusion_skill" and p_norm in ("basic", "fusion"):
                        pass
                    else:
                        type_mistakes += 1

    # 5. No match quality: missing pred mapping must NOT count as correct no-match when disposition is map
    nm_correct = 0
    nm_false_matches = 0
    nm_denom = 0
    for c in cases:
        meta = predictions_meta.get(c["id"])
        if not meta:
            continue
        exp_target = c.get("expected_generic_id")
        exp_disp = (c.get("expected_disposition") or "").lower()
        is_no_match = exp_target is None and exp_disp in ("no_match", "no-match", "novel", "orthogonal", "distinct")
        pred_disp = (meta.get("disposition") or "").lower() if meta.get("disposition") else None
        pred_map = meta.get("mapping")
        if is_no_match and (pred_disp is not None or pred_map is not None or "mapping" in meta or "disposition" in meta):
            nm_denom += 1
            if pred_disp in ("map", "map_existing", "mapped"):
                # Disposition says to map; even with missing mapping key, this is a false match
                nm_false_matches += 1
            elif pred_map is not None and str(pred_map).lower() not in ("none", "no_match", "no-match", "novel", "reject", "unresolved", ""):
                # Concrete mapping supplied
                nm_false_matches += 1
            elif pred_disp in ("no_match", "no-match", "novel", "none", "reject", "unresolved"):
                nm_correct += 1
            else:
                nm_false_matches += 1

    # 6. Packaging shape mistakes: package vs router vs wrapper
    pkg_mistakes = 0
    pkg_denom = 0
    for c in cases:
        meta = predictions_meta.get(c["id"])
        if not meta:
            continue
        exp_shape = c.get("expected_packaging_shape") or c.get("packaging_shape")
        if not exp_shape:
            cand = c.get("expected_shape")
            if cand and cand.strip().lower() not in ("basic", "fusion", "basic_or_fusion_skill"):
                exp_shape = cand

        pred_shape = meta.get("packaging_shape") or meta.get("expected_packaging_shape")
        if not pred_shape:
            cand_pred = meta.get("shape")
            if cand_pred and cand_pred.strip().lower() not in ("basic", "fusion", "basic_or_fusion_skill"):
                pred_shape = cand_pred

        if exp_shape is not None and pred_shape is not None:
            e_s = exp_shape.strip().lower()
            p_s = pred_shape.strip().lower()
            if e_s and p_s:
                pkg_denom += 1
                if e_s != p_s:
                    pkg_mistakes += 1

    # 7. Human overturn
    ho_count = 0
    ho_denom = 0
    for c in cases:
        meta = predictions_meta.get(c["id"])
        if not meta:
            continue
        human_tgt = c.get("human_target") or meta.get("humanTarget")
        if not human_tgt:
            continue
        proposal = meta.get("mapping") or meta.get("jevTarget")
        if proposal is not None:
            ho_denom += 1
            if proposal != human_tgt:
                ho_count += 1

    # 8. Jev disagreement
    jd_count = 0
    jd_denom = 0
    for c in cases:
        meta = predictions_meta.get(c["id"])
        if not meta:
            continue
        jev_tgt = c.get("jev_target") or meta.get("jevTarget")
        if not jev_tgt:
            continue
        compare_target = c.get("human_target") or meta.get("humanTarget") or meta.get("mapping")
        if compare_target is not None:
            jd_denom += 1
            if jev_tgt != compare_target:
                jd_count += 1

    return {
        "false_new_generic": {
            "count": fng_count,
            "denominator": fng_denom,
            "rate": (fng_count / fng_denom) if fng_denom else None,
        },
        "false_consolidation": {
            "count": fc_count,
            "denominator": fc_denom,
            "rate": (fc_count / fc_denom) if fc_denom else None,
        },
        "false_splitting": {
            "count": fs_count,
            "denominator": fs_denom,
            "rate": (fs_count / fs_denom) if fs_denom else None,
        },
        "false_consolidation_splitting": {
            "count": fcs_count,
            "denominator": fcs_denom,
            "rate": (fcs_count / fcs_denom) if fcs_denom else None,
        },
        "capability_type_mistakes": {
            "count": type_mistakes,
            "denominator": type_denom,
            "rate": (type_mistakes / type_denom) if type_denom else None,
        },
        "no_match_quality": {
            "correct": nm_correct,
            "false_matches": nm_false_matches,
            "denominator": nm_denom,
            "accuracy": (nm_correct / nm_denom) if nm_denom else None,
        },
        "packaging_mistakes": {
            "count": pkg_mistakes,
            "denominator": pkg_denom,
            "rate": (pkg_mistakes / pkg_denom) if pkg_denom else None,
        },
        "human_overturn": {
            "count": ho_count,
            "denominator": ho_denom,
            "rate": (ho_count / ho_denom) if ho_denom else None,
        },
        "jev_disagreement": {
            "count": jd_count,
            "denominator": jd_denom,
            "rate": (jd_count / jd_denom) if jd_denom else None,
        },
    }


def metrics(
    cases: list[dict[str, Any]],
    predictions: dict[str, list[str]],
    k: int = 5,
    predictions_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute retrieval metrics with both predicted and corpus-wide denominators."""
    eligible = [c for c in cases if c.get("expected_generic_id")]
    ranked = [(c, predictions.get(c["id"], [])) for c in eligible if c["id"] in predictions]
    n = len(ranked)
    total_eligible = len(eligible)

    top1_sum = sum(bool(r and r[0] == c["expected_generic_id"]) for c, r in ranked)
    topk_sum = sum(c["expected_generic_id"] in r[:k] for c, r in ranked)
    reciprocal = [
        1.0 / (r.index(c["expected_generic_id"]) + 1) if c["expected_generic_id"] in r else 0.0
        for c, r in ranked
    ]
    mrr_sum = sum(reciprocal)

    res: dict[str, Any] = {
        "labelled_cases": total_eligible,
        "predicted_labelled_cases": n,
        "coverage": (n / total_eligible) if total_eligible else None,
        "top1": (top1_sum / n) if n else None,
        "top1_corpus": (top1_sum / total_eligible) if n and total_eligible else None,
        f"top{k}": (topk_sum / n) if n else None,
        f"top{k}_corpus": (topk_sum / total_eligible) if n and total_eligible else None,
        "mrr": (mrr_sum / n) if n else None,
        "mrr_corpus": (mrr_sum / total_eligible) if n and total_eligible else None,
        "denominator": n,
        "corpus_denominator": total_eligible,
        "unlabelled_predictions": sum(
            c["id"] in predictions for c in cases if not c.get("expected_generic_id")
        ),
    }
    if predictions_meta:
        res["classification"] = classification_metrics(cases, predictions_meta)
    return res


def _resolve_retrieval_config(
    root: str | Path,
    model: str | None,
    revision: str | None = None,
) -> dict[str, Any]:
    """Load full canonical retrieval config honoring model declaration or fallback."""
    from gaia_cli.curation.retrieval import loadRetrievalConfig
    try:
        cfg = loadRetrievalConfig(registryPath=root, modelName=model)
    except (ValueError, FileNotFoundError):
        cfg = {
            "modelId": model or "all-MiniLM-L6-v2",
            "backend": "torch",
            "dimensions": 384,
            "normalize": True,
            "pooling": "mean",
            "queryPrefix": "",
            "revision": revision,
            "textTemplate": "{name}: {description}",
            "defaultModel": "all-MiniLM-L6-v2",
        }
    if revision is not None:
        cfg["revision"] = revision
    return cfg


def run(
    *,
    root: str | Path,
    corpus_path: str | Path,
    model: str | None = None,
    revision: str | None = None,
    reranker: str | None = None,
    reranker_revision: str | None = DEFAULT_RERANKER_REVISION,
    predictions_path: str | Path | None = None,
    limit: int | None = None,
    top_k: int = 5,
    batch_size: int = 16,
    threads: int | None = None,
    use_cache: bool = True,
) -> dict[str, Any]:
    """Execute evaluation benchmark across oracle corpus."""
    started = time.perf_counter()
    root = Path(root)

    if threads is not None:
        try:
            import torch
            torch.set_num_threads(threads)
        except Exception:
            pass

    corpus_file = Path(corpus_path)
    corpus_data = json.loads(corpus_file.read_text(encoding="utf-8"))
    cases = corpus_data["cases"] if isinstance(corpus_data, dict) and "cases" in corpus_data else corpus_data
    if limit is not None:
        cases = cases[:limit]

    catalog = load_catalog(root)
    catalog_hash = hashlib.sha256(
        json.dumps(catalog, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    known = {s["id"] for s in catalog}
    catalog_by_id = {s["id"]: s for s in catalog}

    predfile = Path(predictions_path) if predictions_path else None
    predictions_meta: dict[str, dict[str, Any]] = {}
    retrieval_scores_by_case: dict[str, list[float]] = {}
    reranker_scores_by_case: dict[str, list[float]] = {}

    latency_load = 0.0
    latency_document = 0.0
    latency_query = 0.0
    latency_rerank = 0.0

    if predfile:
        captured = json.loads(predfile.read_text(encoding="utf-8"))
        raw_rankings = captured.get("rankings", captured)
        rankings: dict[str, list[str]] = {}
        for cid, val in raw_rankings.items():
            if isinstance(val, list):
                rankings[cid] = [str(x) for x in val]
            elif isinstance(val, dict):
                rankings[cid] = [str(x) for x in val.get("ranking", [])]
                predictions_meta[cid] = val

        # Additional metadata extraction
        if "predictions" in captured and isinstance(captured["predictions"], dict):
            for cid, meta in captured["predictions"].items():
                if isinstance(meta, dict):
                    predictions_meta.setdefault(cid, {}).update(meta)
        if "cases" in captured and isinstance(captured["cases"], dict):
            for cid, meta in captured["cases"].items():
                if isinstance(meta, dict):
                    predictions_meta.setdefault(cid, {}).update(meta)

        for meta_key in ("dispositions", "shapes", "mappings", "jevTargets", "humanTargets"):
            if meta_key in captured and isinstance(captured[meta_key], dict):
                single_key = meta_key[:-1] if meta_key.endswith("s") else meta_key
                for cid, val in captured[meta_key].items():
                    predictions_meta.setdefault(cid, {})[single_key] = val

        if "scores" in captured and isinstance(captured["scores"], dict):
            retrieval_scores_by_case = captured["scores"]
        if "retrieval_scores" in captured and isinstance(captured["retrieval_scores"], dict):
            retrieval_scores_by_case = captured["retrieval_scores"]
        if "reranker_scores" in captured and isinstance(captured["reranker_scores"], dict):
            reranker_scores_by_case = captured["reranker_scores"]

        config = captured.get("config", {
            "mode": "captured-predictions",
            "model": None,
            "revision": None,
            "reranker": None,
            "rerankerRevision": None,
        })
        model_id = config.get("model") or config.get("modelId")
        model_rev = config.get("revision")
        weight_bytes, weight_reason = find_model_weight_size(model_id, root, revision=model_rev)
        model_load_state = "offline"
        latency_reranker_load = 0.0
    else:
        cfg = _resolve_retrieval_config(root, model, revision)
        model_id = cfg.get("modelId")
        model_rev = cfg.get("revision")
        backend = cfg.get("backend", "torch")
        pooling = cfg.get("pooling", "mean")

        weight_bytes, weight_reason = find_model_weight_size(model_id, root, revision=model_rev)

        # Warm load using shared getSentenceTransformer before encode
        from gaia_cli.curation.retrieval import getSentenceTransformer, _MODEL_CACHE
        cache_key = (model_id, model_rev, backend)
        was_cached = cache_key in _MODEL_CACHE
        model_load_state = "cached" if was_cached else "cold"

        t_load_start = time.perf_counter()
        _st_model = getSentenceTransformer(model_id, revision=model_rev, backend=backend, pooling=pooling)
        latency_load = time.perf_counter() - t_load_start

        cache_dir = _get_cache_dir(root)
        config_hash = _compute_config_hash(cfg)

        t_doc_start = time.perf_counter()
        doc_vectors = None
        if use_cache:
            doc_vectors = _load_cached_catalog_vectors(cache_dir, catalog_hash, config_hash, catalog)

        if doc_vectors is None:
            t_enc_start = time.perf_counter()
            from gaia_cli.embeddings import embed_skills
            entries, _ = embed_skills(catalog, config=cfg)
            import numpy as np
            doc_vectors = np.array([e["vector"] for e in entries], dtype=np.float32)
            latency_document = time.perf_counter() - t_enc_start

            if use_cache:
                _save_cached_catalog_vectors_atomic(cache_dir, catalog_hash, config_hash, cfg, catalog, doc_vectors)
        else:
            latency_document = time.perf_counter() - t_doc_start

        from gaia_cli.semantic_search import embed_query
        t_query_start = time.perf_counter()
        query_vectors = []
        for c in cases:
            q_text = f"{c['name']}: {c['description']}"
            q_vec = embed_query(q_text, config=cfg)
            query_vectors.append(q_vec)
        latency_query = time.perf_counter() - t_query_start

        import numpy as np
        rankings = {}
        for case, q_vec in zip(cases, query_vectors):
            q_arr = np.array(q_vec, dtype=np.float32)
            sim_scores = doc_vectors @ q_arr
            order = np.argsort(-sim_scores)
            top_indices = order[: max(top_k, 20)]
            cand_ids = [catalog[int(i)]["id"] for i in top_indices]
            rankings[case["id"]] = cand_ids
            retrieval_scores_by_case[case["id"]] = [float(sim_scores[int(i)]) for i in top_indices]

        latency_reranker_load = 0.0
        if reranker:
            t_rerank_load = time.perf_counter()
            from sentence_transformers import CrossEncoder
            cross_kwargs: dict[str, Any] = {}
            if reranker_revision:
                cross_kwargs["revision"] = reranker_revision
            cross = CrossEncoder(reranker, **cross_kwargs)
            latency_reranker_load = time.perf_counter() - t_rerank_load

            t_rerank_start = time.perf_counter()
            for case in cases:
                cand_ids = rankings[case["id"]]
                ret_scores = retrieval_scores_by_case.get(case["id"], [])
                score_map = dict(zip(cand_ids, ret_scores))

                q_text = f"{case['name']}: {case['description']}"
                pairs = [
                    [q_text, f"{catalog_by_id[cid]['name']}: {catalog_by_id[cid]['description']}"]
                    for cid in cand_ids
                ]
                scores = cross.predict(pairs, batch_size=batch_size)
                reranked_tuples = sorted(zip(scores, cand_ids), reverse=True)
                reranked_ids = [cid for _, cid in reranked_tuples]
                rankings[case["id"]] = reranked_ids
                reranker_scores_by_case[case["id"]] = [float(s) for s, _ in reranked_tuples]
                retrieval_scores_by_case[case["id"]] = [score_map.get(cid, 0.0) for cid in reranked_ids]
            latency_rerank = time.perf_counter() - t_rerank_start

        config = {
            "mode": "sentence-transformers",
            "model": cfg.get("modelId"),
            "modelId": cfg.get("modelId"),
            "revision": cfg.get("revision"),
            "backend": cfg.get("backend", "torch"),
            "dimensions": cfg.get("dimensions"),
            "normalize": cfg.get("normalize", True),
            "pooling": cfg.get("pooling", "mean"),
            "queryPrefix": cfg.get("queryPrefix", ""),
            "textTemplate": cfg.get("textTemplate", "{name}: {description}"),
            "reranker": reranker,
            "rerankerRevision": reranker_revision if reranker else None,
            "batchSize": batch_size,
            "threads": threads,
        }

    # Filter candidates to known generic nodes
    rankings = {cid: [x for x in ids if x in known] for cid, ids in rankings.items()}

    details = []
    for case in cases:
        cid = case["id"]
        rank = rankings.get(cid, [])
        target = case.get("expected_generic_id")
        case_meta = predictions_meta.get(cid, {})

        case_ret_scores = retrieval_scores_by_case.get(cid)
        case_rerank_scores = reranker_scores_by_case.get(cid)

        exp_type = case.get("expected_type") or (
            case.get("expected_shape")
            if case.get("expected_shape") in ("basic", "fusion", "basic_or_fusion_skill")
            else None
        )
        details.append({
            "case_id": cid,
            "provenance_class": case.get("provenance_class"),
            "expected_generic_id": target,
            "expected_type": exp_type,
            "expected_shape": case.get("expected_shape"),
            "expected_disposition": case.get("expected_disposition"),
            "ranking": rank[:top_k],
            "rank": rank.index(target) + 1 if target and target in rank else None,
            "retrieval_scores": case_ret_scores[:top_k] if case_ret_scores is not None else None,
            "reranker_scores": case_rerank_scores[:top_k] if case_rerank_scores is not None else None,
            "error": bool(target and (not rank or rank[0] != target)),
            "disposition": case_meta.get("disposition"),
            "shape": case_meta.get("shape"),
            "mapping": case_meta.get("mapping"),
            "human_target": case_meta.get("humanTarget") or case.get("human_target"),
            "jev_target": case_meta.get("jevTarget") or case.get("jev_target"),
        })

    human = [c for c in cases if c.get("provenance_class") == "human-approved"]
    synthetic = [c for c in cases if c.get("provenance_class") == "synthetic-doctrine"]
    unresolved = [c for c in cases if c.get("provenance_class") == "unresolved-discussion"]

    elapsed = time.perf_counter() - started
    peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_rss_bytes = int(peak_rss if sys.platform == "darwin" else peak_rss * 1024)
    peak_rss_unit = (
        "kilobytes"
        if sys.platform.startswith("linux") or "android" in sys.platform.lower()
        else ("bytes" if sys.platform == "darwin" else "platform-dependent")
    )

    return {
        "schema_version": 1,
        "status": "completed",
        "evaluatedAt": datetime.now(timezone.utc).isoformat(),
        "config": config,
        "corpus_sha256": sha256_file(corpus_path),
        "catalog_sha256": catalog_hash,
        "catalog_count": len(catalog),
        "elapsed_seconds": elapsed,
        "latencies": {
            "load_seconds": latency_load,
            "reranker_load_seconds": latency_reranker_load,
            "document_seconds": latency_document,
            "query_seconds": latency_query,
            "rerank_seconds": latency_rerank,
            "total_seconds": elapsed,
        },
        "latency_load_seconds": latency_load,
        "latency_reranker_load_seconds": latency_reranker_load,
        "latency_document_seconds": latency_document,
        "latency_query_seconds": latency_query,
        "latency_rerank_seconds": latency_rerank,
        "model_load_state": model_load_state,
        "peak_rss_bytes": peak_rss_bytes,
        "peak_rss_platform_units": peak_rss,
        "peak_rss_unit": peak_rss_unit,
        "model_weight_bytes": weight_bytes,
        "model_weight_size_reason": weight_reason,
        "metrics": metrics(cases, rankings, top_k, predictions_meta),
        "by_provenance": {
            "human-approved": metrics(human, rankings, top_k, predictions_meta),
            "synthetic-doctrine": metrics(synthetic, rankings, top_k, predictions_meta),
            "unresolved-discussion": metrics(unresolved, rankings, top_k, predictions_meta),
        },
        "classification_metrics": classification_metrics(cases, predictions_meta),
        "details": details,
    }
