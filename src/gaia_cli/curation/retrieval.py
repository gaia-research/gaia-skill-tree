"""Bounded retrieval configuration, semantic fingerprinting, and cache management.

Implements model configuration declaration, cache validation, atomic writes,
and semantic fingerprinting for Gaia curation retrieval.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence


ENCODER_CONTRACT = "sentence-transformers-eval-single-thread-v2"
SUPPORTED_BACKENDS: set[str] = {"torch", "onnx"}
SUPPORTED_POOLING: set[str] = {"mean", "cls", "last_token", "max"}

_MODEL_CACHE: dict[tuple[str, Optional[str], str], Any] = {}


def getModelCache() -> dict[tuple[str, Optional[str], str], Any]:
    """Return the active in-memory SentenceTransformer model cache."""
    return _MODEL_CACHE


def clearModelCache() -> None:
    """Clear cached model instances (for testing or memory reclamation)."""
    _MODEL_CACHE.clear()


clear_model_cache = clearModelCache
get_model_cache = getModelCache


def getModelCacheDir() -> Path:
    """Return the model cache directory, honoring GAIA_MODEL_CACHE if set."""
    env_cache = os.environ.get("GAIA_MODEL_CACHE")
    if env_cache:
        return Path(env_cache)
    gaia_home = os.environ.get("GAIA_HOME")
    base = Path(gaia_home) if gaia_home else Path.home() / ".gaia"
    return base / "models"


get_model_cache_dir = getModelCacheDir


def normalize_pooling_mode(mode: Any) -> str:
    """Normalize pooling mode identifier strings."""
    if not isinstance(mode, str):
        raise ValueError(f"Pooling mode must be a string, got {type(mode).__name__}")
    norm = mode.strip().lower()
    if norm in ("lasttoken", "last_token"):
        return "last_token"
    if norm in ("cls", "cls_token"):
        return "cls"
    if norm in ("mean", "mean_tokens"):
        return "mean"
    if norm in ("max", "max_tokens"):
        return "max"
    return norm


def extract_model_pooling(model: Any) -> Optional[str]:
    """Inspect model or its modules to determine native pooling mode."""
    pool_attr = getattr(model, "pooling", None)
    if isinstance(pool_attr, str) and pool_attr.strip():
        return normalize_pooling_mode(pool_attr)
    mode_attr = getattr(model, "pooling_mode", None)
    if isinstance(mode_attr, str) and mode_attr.strip():
        return normalize_pooling_mode(mode_attr)

    if hasattr(model, "modules") and callable(model.modules):
        try:
            mods = model.modules()
        except Exception:
            mods = []
        for mod in mods:
            if mod is model:
                continue
            mod_pool = getattr(mod, "pooling_mode", None)
            if isinstance(mod_pool, str) and mod_pool.strip():
                return normalize_pooling_mode(mod_pool)
            if hasattr(mod, "get_config_dict") and callable(mod.get_config_dict):
                try:
                    cd = mod.get_config_dict()
                    if isinstance(cd, dict) and isinstance(cd.get("pooling_mode"), str):
                        return normalize_pooling_mode(cd["pooling_mode"])
                except Exception:
                    pass
            if getattr(mod, "pooling_mode_cls_token", False) is True:
                return "cls"
            if getattr(mod, "pooling_mode_mean_tokens", False) is True:
                return "mean"
            if getattr(mod, "pooling_mode_max_tokens", False) is True:
                return "max"
            if getattr(mod, "pooling_mode_lasttoken", False) is True:
                return "last_token"

    if hasattr(model, "_modules") and isinstance(model._modules, dict):
        for mod in model._modules.values():
            mod_pool = getattr(mod, "pooling_mode", None)
            if isinstance(mod_pool, str) and mod_pool.strip():
                return normalize_pooling_mode(mod_pool)
            if hasattr(mod, "get_config_dict") and callable(mod.get_config_dict):
                try:
                    cd = mod.get_config_dict()
                    if isinstance(cd, dict) and isinstance(cd.get("pooling_mode"), str):
                        return normalize_pooling_mode(cd["pooling_mode"])
                except Exception:
                    pass

    return None


def verify_model_pooling(model: Any, expected_pooling: str, model_id: str = "") -> str:
    """Verify that model's native pooling matches expected pooling, or reject."""
    norm_expected = normalize_pooling_mode(expected_pooling)
    if norm_expected not in SUPPORTED_POOLING:
        raise ValueError(
            f"Unsupported pooling mode '{expected_pooling}'. "
            f"Supported pooling modes: {sorted(SUPPORTED_POOLING)}"
        )
    native = extract_model_pooling(model)
    if native is not None:
        if native != norm_expected:
            label = f" for '{model_id}'" if model_id else ""
            raise ValueError(
                f"Model pooling mismatch{label}: model natively uses '{native}', "
                f"but configuration requested '{expected_pooling}'"
            )
        return native
    return norm_expected


def getSentenceTransformer(
    modelName: Optional[str] = None,
    revision: Optional[str] = None,
    backend: Optional[str] = None,
    pooling: Optional[str] = None,
) -> Any:
    """Retrieve or load a cached SentenceTransformer model instance.

    Reuses model objects and weights across query and document encoding to
    avoid redundant re-instantiation and ensure identical weights.
    Honors repository default configuration when modelName is None, while
    resolving declared aliases/config and defaults for explicit modelName too.
    Explicit revision argument overrides configured revision.
    """
    cfg: Optional[dict[str, Any]] = None
    try:
        cfg = loadRetrievalConfig(modelName=modelName)
    except Exception:
        cfg = None

    if cfg is not None:
        resolved_model = cfg["modelId"]
        resolved_rev = revision if revision is not None else cfg.get("revision")
        resolved_backend = backend if backend is not None else cfg.get("backend", "torch")
        resolved_pooling = pooling if pooling is not None else cfg.get("pooling")
    else:
        resolved_model = modelName or "all-MiniLM-L6-v2"
        resolved_rev = revision
        resolved_backend = backend if backend is not None else "torch"
        resolved_pooling = pooling

    if resolved_backend not in SUPPORTED_BACKENDS:
        raise ValueError(
            f"Unsupported backend '{resolved_backend}'. "
            f"Supported backends: {sorted(SUPPORTED_BACKENDS)}"
        )

    cacheKey = (resolved_model, resolved_rev, resolved_backend)
    if cacheKey in _MODEL_CACHE:
        torchRuntime = sys.modules.get("torch")
        if torchRuntime is not None:
            torchRuntime.set_num_threads(1)
        model = _MODEL_CACHE[cacheKey]
        if callable(getattr(model, "eval", None)):
            model.eval()
        if resolved_pooling:
            verify_model_pooling(model, resolved_pooling, model_id=resolved_model)
        return model

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise ImportError(
            "sentence-transformers is not installed. "
            "Install with: pip install sentence-transformers"
        ) from exc

    cache_folder = str(getModelCacheDir())
    kwargs: dict[str, Any] = {
        "backend": resolved_backend,
        "cache_folder": cache_folder,
    }
    if resolved_rev:
        kwargs["revision"] = resolved_rev

    # Native Android Torch 2.11 showed repeat-query drift with >1 CPU thread.
    # One thread is the verified portable inference contract; unlike weights,
    # this process setting must also be reasserted on cached model reuse.
    torchRuntime = sys.modules.get("torch")
    if torchRuntime is not None:
        torchRuntime.set_num_threads(1)
    model = SentenceTransformer(resolved_model, **kwargs)
    # encode() is not guaranteed to switch to inference mode across supported
    # sentence-transformers versions. Dropout corrupts deterministic recall.
    if callable(getattr(model, "eval", None)):
        model.eval()
    if resolved_pooling:
        verify_model_pooling(model, resolved_pooling, model_id=resolved_model)

    _MODEL_CACHE[cacheKey] = model
    return model


get_sentence_transformer = getSentenceTransformer


def _findRetrievalJsonPath(registryPath: str | Path = ".") -> Optional[Path]:
    """Find the retrieval.json configuration file path."""
    candidates = [
        Path(registryPath) / "data" / "curation" / "retrieval.json",
        Path(registryPath) / "src" / "gaia_cli" / "data" / "curation" / "retrieval.json",
        Path(__file__).resolve().parent.parent / "data" / "curation" / "retrieval.json",
    ]
    try:
        import importlib.resources as pkg_resources

        res_path = Path(str(pkg_resources.files("gaia_cli").joinpath("data", "curation", "retrieval.json")))
        candidates.append(res_path)
    except Exception:
        pass

    for p in candidates:
        if p.is_file():
            return p
    return None


def loadRetrievalConfig(
    registryPath: str | Path = ".",
    modelName: Optional[str] = None,
) -> dict[str, Any]:
    """Load retrieval configuration from packaged retrieval.json.

    Args:
        registryPath: Path to registry root or repository root.
        modelName: Optional model ID or alias (e.g. 'all-MiniLM-L6-v2',
            'BAAI/bge-small-en-v1.5', 'Qwen3'). Defaults to declared defaultModel.

    Returns:
        dict containing model configuration parameters:
            modelId, revision, backend, dimensions, normalize, pooling,
            textTemplate, queryPrefix, candidate, tier, description,
            defaultModel, availableModels.
    """
    jsonPath = _findRetrievalJsonPath(registryPath)
    if not jsonPath or not jsonPath.is_file():
        raise FileNotFoundError(
            f"Canonical retrieval configuration 'retrieval.json' not found. "
            f"Checked locations under '{registryPath}' and package data. "
            "Ensure gaia_cli package data is intact."
        )

    try:
        with open(jsonPath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        raise ValueError(
            f"Corrupt canonical retrieval configuration at '{jsonPath}': {exc}"
        ) from exc

    if not isinstance(data, dict) or "models" not in data or "defaultModel" not in data:
        raise ValueError(
            f"Corrupt canonical retrieval configuration at '{jsonPath}': missing 'models' or 'defaultModel'"
        )

    defaultModel = data["defaultModel"]
    models = data["models"]
    aliases = data.get("aliases", {})

    targetKey = modelName or defaultModel
    resolvedKey = aliases.get(targetKey, targetKey)
    selectedConfig: Optional[dict[str, Any]] = None

    if resolvedKey in models:
        selectedConfig = copy.deepcopy(models[resolvedKey])
    else:
        targetLower = targetKey.lower()
        for k, v in models.items():
            if k.lower() == targetLower:
                selectedConfig = copy.deepcopy(v)
                break
            mid = v.get("modelId", "")
            if mid == targetKey or mid.lower() == targetLower:
                selectedConfig = copy.deepcopy(v)
                break
            if "/" in mid and mid.split("/")[-1].lower() == targetLower:
                selectedConfig = copy.deepcopy(v)
                break
        if selectedConfig is None:
            for alias_key, target in aliases.items():
                if alias_key.lower() == targetLower and target in models:
                    selectedConfig = copy.deepcopy(models[target])
                    break

    if selectedConfig is None:
        availableKeys = sorted(models.keys())
        raise ValueError(
            f"Unknown retrieval model '{targetKey}'. Available models: {availableKeys}"
        )

    # Validate config fields
    pooling = selectedConfig.get("pooling")
    if pooling:
        norm_pooling = normalize_pooling_mode(pooling)
        if norm_pooling not in SUPPORTED_POOLING:
            raise ValueError(
                f"Unsupported pooling mode '{pooling}' in config for '{selectedConfig.get('modelId')}'. "
                f"Supported modes: {sorted(SUPPORTED_POOLING)}"
            )
        selectedConfig["pooling"] = norm_pooling

    backend = selectedConfig.get("backend", "torch")
    if backend not in SUPPORTED_BACKENDS:
        raise ValueError(
            f"Unsupported backend '{backend}' in config for '{selectedConfig.get('modelId')}'. "
            f"Supported backends: {sorted(SUPPORTED_BACKENDS)}"
        )

    # Augment with metadata and normalized keys for convenience
    selectedConfig["defaultModel"] = defaultModel
    selectedConfig["availableModels"] = sorted(models.keys())

    # Ensure aliases for both camelCase and snake_case access
    if "modelId" in selectedConfig and "model_id" not in selectedConfig:
        selectedConfig["model_id"] = selectedConfig["modelId"]
    if "textTemplate" in selectedConfig and "text_template" not in selectedConfig:
        selectedConfig["text_template"] = selectedConfig["textTemplate"]
    if "queryPrefix" in selectedConfig and "query_prefix" not in selectedConfig:
        selectedConfig["query_prefix"] = selectedConfig["queryPrefix"]

    return selectedConfig


load_retrieval_config = loadRetrievalConfig


def canonicalizeModelId(
    modelName: Optional[str],
    registryPath: str | Path = ".",
) -> Optional[str]:
    """Resolve model alias or identifier to canonical modelId."""
    if not modelName or not isinstance(modelName, str):
        return modelName
    try:
        cfg = loadRetrievalConfig(registryPath=registryPath, modelName=modelName)
        return cfg.get("modelId", modelName)
    except Exception:
        return modelName


canonicalize_model_id = canonicalizeModelId


def semanticFingerprint(
    skills: Sequence[Mapping[str, Any]] | Mapping[str, Any],
    config: Optional[dict[str, Any] | str] = None,
) -> str:
    """Compute a deterministic SHA-256 fingerprint for skills and retrieval configuration.

    Fingerprints sorted skill IDs, names, and descriptions (canonical nodes and
    named fields actually embedded). Excludes stars, TM, dates, levels, evidence,
    or other volatile metadata.
    Includes dimensions, modelId, revision, backend, normalize, pooling, textTemplate, queryPrefix.
    Normalizes pooling aliases and model aliases so equivalent configurations produce identical fingerprints.
    """
    if config is None:
        resolvedConfig = loadRetrievalConfig()
    elif isinstance(config, str):
        resolvedConfig = loadRetrievalConfig(modelName=config)
    else:
        resolvedConfig = config

    raw_dim = resolvedConfig.get("dimensions")
    dim_val = int(raw_dim) if raw_dim is not None else None

    raw_model = resolvedConfig.get("modelId") or resolvedConfig.get("model") or resolvedConfig.get("defaultModel")
    norm_model = canonicalizeModelId(raw_model) or raw_model

    raw_pooling = resolvedConfig.get("pooling")
    if raw_pooling is not None and isinstance(raw_pooling, str) and raw_pooling.strip():
        try:
            norm_pooling = normalize_pooling_mode(raw_pooling)
        except ValueError:
            norm_pooling = raw_pooling.strip().lower()
    else:
        norm_pooling = "mean"

    cfgPayload = {
        "encoderContract": ENCODER_CONTRACT,
        "backend": resolvedConfig.get("backend", "torch"),
        "dimensions": dim_val,
        "modelId": norm_model,
        "normalize": bool(resolvedConfig.get("normalize", True)),
        "pooling": norm_pooling,
        "queryPrefix": resolvedConfig.get("queryPrefix") or resolvedConfig.get("query_prefix", ""),
        "revision": resolvedConfig.get("revision"),
        "textTemplate": resolvedConfig.get("textTemplate") or resolvedConfig.get("text_template", "{name}: {description}"),
    }

    skillList: list[dict[str, str]] = []
    if isinstance(skills, Sequence):
        for s in skills:
            if not isinstance(s, Mapping):
                continue
            sid = s.get("id")
            if not sid:
                continue
            skillList.append({
                "description": str(s.get("description", "")),
                "id": str(sid),
                "name": str(s.get("name", sid)),
            })
    elif isinstance(skills, Mapping):
        for sid, s in skills.items():
            if isinstance(s, Mapping):
                skillList.append({
                    "description": str(s.get("description", "")),
                    "id": str(sid),
                    "name": str(s.get("name", sid)),
                })
            else:
                skillList.append({
                    "description": str(s or ""),
                    "id": str(sid),
                    "name": str(sid),
                })

    skillList.sort(key=lambda x: x["id"])

    payload = {
        "config": cfgPayload,
        "skills": skillList,
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


semantic_fingerprint = semanticFingerprint


def validateVector(
    vector: Sequence[Any],
    expectedDim: Optional[int] = None,
    label: str = "",
) -> None:
    """Validate that vector is a non-empty sequence of finite floats/ints.

    Rejects booleans, non-finite values (NaN, Inf), empty vectors (zero dimensions),
    and dimension mismatches.
    """
    prefix = f"{label}: " if label else ""
    if not isinstance(vector, (list, tuple)) or isinstance(vector, (str, bytes, bool)):
        raise ValueError(f"{prefix}Vector must be a list or tuple, got {type(vector).__name__}")
    if len(vector) == 0:
        raise ValueError(f"{prefix}Vector must not be empty (zero dimensions)")
    if expectedDim is not None:
        if expectedDim <= 0:
            raise ValueError(f"{prefix}Expected dimension must be positive, got {expectedDim}")
        if len(vector) != expectedDim:
            raise ValueError(
                f"{prefix}Vector dimension mismatch: expected {expectedDim}, got {len(vector)}"
            )
    for idx, val in enumerate(vector):
        if isinstance(val, bool):
            raise ValueError(
                f"{prefix}Vector element at index {idx} contains boolean value: {val!r}"
            )
        if not isinstance(val, (int, float)) or not math.isfinite(val):
            raise ValueError(
                f"{prefix}Vector element at index {idx} contains non-finite value: {val!r}"
            )


validate_vector = validateVector


def validateEmbeddingsData(
    data: Any,
    expectedDim: Optional[int] = None,
    expectedModel: Optional[str] = None,
) -> None:
    """Validate the schema and vector integrity of an embeddings dictionary.

    Raises:
        ValueError: If root is not a dict, entries are missing/invalid,
            duplicate IDs exist, vector dimensions mismatch, or non-finite vector values are found.
    """
    if not isinstance(data, dict):
        raise ValueError(f"Embeddings artifact must be a dict, got {type(data).__name__}")

    entries = data.get("entries")
    if not isinstance(entries, list):
        raise ValueError("Embeddings artifact missing 'entries' list")

    declDim = data.get("dimensions")
    if declDim is not None:
        if isinstance(declDim, bool) or not isinstance(declDim, int) or declDim <= 0:
            raise ValueError(f"Embeddings artifact has invalid dimensions: {declDim}")
        targetDim = expectedDim or declDim
    else:
        targetDim = expectedDim

    seen_ids: set[str] = set()
    for idx, entry in enumerate(entries):
        if not isinstance(entry, dict) or "id" not in entry or "vector" not in entry:
            raise ValueError(f"Embeddings entry at index {idx} missing 'id' or 'vector'")
        eid = entry.get("id")
        if not eid or not isinstance(eid, str) or not eid.strip():
            raise ValueError(f"Embeddings entry at index {idx} missing valid 'id'")
        if eid in seen_ids:
            raise ValueError(f"Duplicate embedding entry id '{eid}' at index {idx}")
        seen_ids.add(eid)
        validateVector(entry["vector"], expectedDim=targetDim, label=f"Skill '{eid}'")

    if expectedModel:
        artifactModel = data.get("model") or (data.get("config", {}) if isinstance(data.get("config"), dict) else {}).get("modelId")
        if artifactModel:
            normExpected = canonicalizeModelId(expectedModel) or expectedModel
            normArtifact = canonicalizeModelId(artifactModel) or artifactModel
            if normArtifact != normExpected:
                raise ValueError(
                    f"Model mismatch: expected '{expectedModel}', found '{artifactModel}'"
                )


validate_embeddings_data = validateEmbeddingsData


def embeddingStatus(
    registryPath: str | Path = ".",
    artifactPath: Optional[str | Path] = None,
    config: Optional[dict[str, Any] | str] = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Check freshness and validity of an embeddings artifact.

    Returns dict with keys:
        status: "fresh" | "stale" | "missing" | "invalid"
        reason: Human-readable explanation of status
        fingerprint: Stored artifact fingerprint or None
        model: Model identifier
        path: Path inspected
        expectedFingerprint: Expected fingerprint (if stale due to mismatch)
        entriesCount: Number of embedding entries found
    """
    regPath = kwargs.get("registry_path", registryPath)
    artPath = kwargs.get("artifact_path", artifactPath)

    if config is None:
        cfg = loadRetrievalConfig(regPath)
    elif isinstance(config, str):
        cfg = loadRetrievalConfig(regPath, modelName=config)
    else:
        cfg = config

    expectedModel = cfg.get("modelId") or cfg.get("model") or cfg.get("defaultModel")

    from gaia_cli.registry import embeddings_path
    if artPath is None:
        standardPath = embeddings_path(regPath)
        if os.path.exists(standardPath):
            artPath = standardPath
        else:
            alt1 = os.path.join(str(regPath), "graph", "embeddings.json")
            alt2 = os.path.join(str(regPath), "docs", "graph", "embeddings.json")
            if os.path.exists(alt1):
                artPath = alt1
            elif os.path.exists(alt2):
                artPath = alt2
            else:
                artPath = standardPath

    resolvedPathStr = str(artPath)

    if not os.path.exists(resolvedPathStr):
        return {
            "status": "missing",
            "reason": f"Embeddings artifact not found at {resolvedPathStr}",
            "fingerprint": None,
            "model": expectedModel,
            "path": resolvedPathStr,
            "entriesCount": 0,
        }

    try:
        with open(resolvedPathStr, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        return {
            "status": "invalid",
            "reason": f"Could not parse embeddings JSON: {exc}",
            "fingerprint": None,
            "model": None,
            "path": resolvedPathStr,
            "entriesCount": None,
        }

    try:
        validateEmbeddingsData(data)
    except ValueError as exc:
        return {
            "status": "invalid",
            "reason": str(exc),
            "fingerprint": None,
            "model": data.get("model") if isinstance(data, dict) else None,
            "path": resolvedPathStr,
            "entriesCount": len(data.get("entries", [])) if isinstance(data, dict) and isinstance(data.get("entries"), list) else None,
        }

    entries = data.get("entries", [])
    artifactModel = data.get("model") or (data.get("config", {}) if isinstance(data.get("config"), dict) else {}).get("modelId")

    # Check model mismatch
    if expectedModel and artifactModel:
        normExpected = canonicalizeModelId(expectedModel, regPath) or expectedModel
        normArtifact = canonicalizeModelId(artifactModel, regPath) or artifactModel
        if normExpected != normArtifact:
            return {
                "status": "stale",
                "reason": f"Model mismatch: artifact has '{artifactModel}', expected '{expectedModel}'",
                "fingerprint": data.get("fingerprint") or data.get("semanticFingerprint"),
                "model": artifactModel,
                "path": resolvedPathStr,
                "entriesCount": len(entries),
            }

    artifactFp = data.get("fingerprint") or data.get("semanticFingerprint")
    artifactContract = data.get("encoderContract")
    if artifactContract != ENCODER_CONTRACT:
        return {
            "status": "stale",
            "reason": (
                f"Encoder contract mismatch: artifact has '{artifactContract}', "
                f"active contract is '{ENCODER_CONTRACT}'"
            ),
            "fingerprint": artifactFp,
            "model": artifactModel or expectedModel,
            "path": resolvedPathStr,
            "entriesCount": len(entries),
        }

    if not artifactFp:
        return {
            "status": "stale",
            "reason": "Legacy artifact missing semantic fingerprint; unverified",
            "fingerprint": None,
            "model": artifactModel or expectedModel,
            "path": resolvedPathStr,
            "entriesCount": len(entries),
        }

    from gaia_cli.embeddings import load_skills
    skills = load_skills(regPath)

    # Reject empty entries when skills exist
    if len(skills) > 0 and len(entries) == 0:
        return {
            "status": "stale",
            "reason": "Embeddings artifact has empty entries for non-empty skill set",
            "fingerprint": artifactFp,
            "model": artifactModel or expectedModel,
            "path": resolvedPathStr,
            "entriesCount": 0,
        }

    skill_ids = [s["id"] for s in skills if s.get("id")]
    entry_ids = [e["id"] for e in entries]

    if len(entry_ids) != len(set(entry_ids)):
        return {
            "status": "invalid",
            "reason": "Embeddings artifact contains duplicate entry IDs",
            "fingerprint": artifactFp,
            "model": artifactModel or expectedModel,
            "path": resolvedPathStr,
            "entriesCount": len(entries),
        }

    missing_ids = set(skill_ids) - set(entry_ids)
    if missing_ids:
        return {
            "status": "stale",
            "reason": f"Embeddings artifact is truncated: missing {len(missing_ids)} skill entries",
            "fingerprint": artifactFp,
            "model": artifactModel or expectedModel,
            "path": resolvedPathStr,
            "entriesCount": len(entries),
        }

    extra_ids = set(entry_ids) - set(skill_ids)
    if extra_ids:
        return {
            "status": "stale",
            "reason": f"Embeddings artifact contains {len(extra_ids)} unknown skill entries",
            "fingerprint": artifactFp,
            "model": artifactModel or expectedModel,
            "path": resolvedPathStr,
            "entriesCount": len(entries),
        }

    # Verify config / fingerprint agreement
    artifactConfig = data.get("config")
    if isinstance(artifactConfig, dict):
        cfg_fp = semanticFingerprint(skills, artifactConfig)
        if cfg_fp != artifactFp:
            return {
                "status": "invalid",
                "reason": "Artifact config does not match stored fingerprint (config/fingerprint disagreement)",
                "fingerprint": artifactFp,
                "model": artifactModel or expectedModel,
                "path": resolvedPathStr,
                "entriesCount": len(entries),
            }

        # Check semantic config differences against expected cfg
        for key in ("modelId", "revision", "dimensions", "normalize", "pooling", "queryPrefix"):
            val_art = artifactConfig.get(key)
            val_cfg = cfg.get(key)
            if key == "dimensions" and val_art is None:
                val_art = data.get("dimensions")
            if val_art is not None and val_cfg is not None:
                if key == "pooling":
                    try:
                        art_p = normalize_pooling_mode(val_art)
                        cfg_p = normalize_pooling_mode(val_cfg)
                    except ValueError:
                        art_p, cfg_p = val_art, val_cfg
                    if art_p != cfg_p:
                        return {
                            "status": "stale",
                            "reason": f"Semantic config mismatch on 'pooling': artifact has {val_art!r}, expected {val_cfg!r}",
                            "fingerprint": artifactFp,
                            "model": artifactModel or expectedModel,
                            "path": resolvedPathStr,
                            "entriesCount": len(entries),
                        }
                elif key == "modelId":
                    art_m = canonicalizeModelId(val_art, regPath) or val_art
                    cfg_m = canonicalizeModelId(val_cfg, regPath) or val_cfg
                    if art_m != cfg_m:
                        return {
                            "status": "stale",
                            "reason": f"Semantic config mismatch on 'modelId': artifact has {val_art!r}, expected {val_cfg!r}",
                            "fingerprint": artifactFp,
                            "model": artifactModel or expectedModel,
                            "path": resolvedPathStr,
                            "entriesCount": len(entries),
                        }
                elif val_art != val_cfg:
                    return {
                        "status": "stale",
                        "reason": f"Semantic config mismatch on '{key}': artifact has {val_art!r}, expected {val_cfg!r}",
                        "fingerprint": artifactFp,
                        "model": artifactModel or expectedModel,
                        "path": resolvedPathStr,
                        "entriesCount": len(entries),
                    }

    expectedFp = semanticFingerprint(skills, cfg)
    if artifactFp == expectedFp:
        return {
            "status": "fresh",
            "reason": "Embeddings artifact is fresh and matches current canonical skills and retrieval config",
            "fingerprint": artifactFp,
            "model": artifactModel or expectedModel,
            "path": resolvedPathStr,
            "entriesCount": len(entries),
        }
    else:
        return {
            "status": "stale",
            "reason": "Semantic fingerprint mismatch: skills or retrieval config have changed",
            "fingerprint": artifactFp,
            "expectedFingerprint": expectedFp,
            "model": artifactModel or expectedModel,
            "path": resolvedPathStr,
            "entriesCount": len(entries),
        }


embedding_status = embeddingStatus


def saveEmbeddingsAtomic(
    entries: list[dict[str, Any]],
    outputPath: str | Path,
    modelName: str,
    dimensions: int,
    fingerprint: Optional[str] = None,
    config: Optional[dict[str, Any]] = None,
) -> None:
    """Atomically write embeddings manifest and vectors to disk.

    Uses an exclusive, randomly named temporary file in the same directory,
    flushes and syncs to disk, then uses os.replace for atomic rename.
    """
    payload: dict[str, Any] = {
        "model": modelName,
        "dimensions": dimensions,
        "generatedAt": str(date.today()),
        "encoderContract": ENCODER_CONTRACT,
        "entries": entries,
    }
    if fingerprint:
        payload["fingerprint"] = fingerprint
    if config:
        payload["config"] = {
            "backend": config.get("backend", "torch"),
            "dimensions": dimensions,
            "modelId": config.get("modelId", modelName),
            "normalize": bool(config.get("normalize", True)),
            "pooling": config.get("pooling", "mean"),
            "queryPrefix": config.get("queryPrefix", ""),
            "revision": config.get("revision"),
            "textTemplate": config.get("textTemplate", "{name}: {description}"),
        }

    outPath = Path(outputPath)
    outPath.parent.mkdir(parents=True, exist_ok=True)
    tmpPath: Optional[Path] = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=outPath.parent,
            prefix=f"{outPath.name}.tmp.",
            suffix=".json",
            delete=False,
            encoding="utf-8",
        ) as f:
            tmpPath = Path(f.name)
            json.dump(payload, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmpPath, outPath)
    except Exception:
        if tmpPath and tmpPath.exists():
            try:
                tmpPath.unlink()
            except OSError:
                pass
        raise


save_embeddings_atomic = saveEmbeddingsAtomic
