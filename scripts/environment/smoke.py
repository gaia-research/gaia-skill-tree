#!/usr/bin/env python3
"""Gaia Curation Environment Smoke & Model Warmup Helper.

Supports:
1. --warmup: Bounded source-local prefill smoke for setup.sh.
   Loads declared retrieval model via shared getSentenceTransformer (with full
   config and revision applied), encodes direct query, creates a local temporary
   registry with 2 synthetic nodes and graph, encodes synthetic docs with embed_skills,
   invokes buildPrefillPacket with real encoder (precomputedVector=None), validates
   packet with selfValidatePacket, profiles latencies, and creates zero real registry mutations.
2. --termux: Genuine Termux / Android aarch64 runtime verification.
   Detects actual Android platform signals (MUST return nonzero on non-Android/aarch64),
   evaluates torch/sentence-transformers, requires fresh embeddings artifact (error +
   remediation gaia dev embed; no silent fallback), validates via load_embeddings,
   invokes buildPrefillPacket without precomputedVector with candidateId smoke/termux,
   validates packet via selfValidatePacket, profiles latency and RSS, generates structured
   receipt with full semantic config and fingerprint, and sanitizes all outputs.
3. Optional --model and --embeddings overrides for candidate smoke evaluation.
"""

from __future__ import annotations

import argparse
import datetime
import importlib.metadata
import importlib.util
import json
import os
import platform
import re
import resource
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import doctor


def sanitize_secrets(text: str) -> str:
    """Sanitize any API key or token patterns from diagnostic strings."""
    redacted = re.sub(r"""(?i)(?:key|token|secret)\s*[:=]\s*['"]?[A-Za-z0-9_\-]{8,}['"]?""", "[REDACTED]", text)
    redacted = re.sub(r"""\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b""", "[REDACTED_GH_TOKEN]", redacted)
    redacted = re.sub(r"""\bsk-[a-zA-Z0-9]{20,}\b""", "[REDACTED_SK_KEY]", redacted)
    redacted = re.sub(r"""\bAIza[0-9A-Za-z\-_]{25,}\b""", "[REDACTED_AIZA_KEY]", redacted)
    return redacted


def get_approx_rss_mb() -> float:
    """Return peak process RSS in megabytes."""
    try:
        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if platform.system().lower() == "darwin":
            return round(usage / (1024 * 1024), 2)
        return round(usage / 1024, 2)
    except Exception:
        try:
            with open("/proc/self/status", "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        return round(float(line.split()[1]) / 1024, 2)
        except Exception:
            pass
        return 0.0


def run_warmup(repo_root: Path, model_override: Optional[str] = None) -> int:
    """Bounded source-local prefill warmup with temporary synthetic registry."""
    src_dir = (repo_root / "src").resolve()
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    if model_override:
        try:
            from gaia_cli.curation.retrieval import loadRetrievalConfig  # type: ignore

            cfg_data = loadRetrievalConfig(registryPath=str(repo_root), modelName=model_override)
            model_name = model_override
            revision = cfg_data.get("revision")
            backend = cfg_data.get("backend", "torch")
            expected_dim = cfg_data.get("dimensions", 384)
        except Exception as exc:
            print(f"[SMOKE WARMUP] ERROR: Failed loading retrieval config for {model_override}: {sanitize_secrets(str(exc))}", file=sys.stderr)
            return 1
    else:
        ret_info = doctor.check_retrieval(repo_root)
        if not ret_info.get("ok"):
            print(f"[SMOKE WARMUP] ERROR: Failed loading retrieval config: {ret_info.get('error')}", file=sys.stderr)
            return 1
        model_name = ret_info.get("model", "all-MiniLM-L6-v2")
        revision = ret_info.get("revision")
        backend = ret_info.get("backend", "torch")
        expected_dim = ret_info.get("dimensions", 384)
        cfg_data = ret_info.get("config", {})

    cache_dir = os.environ.get("GAIA_MODEL_CACHE") or str(repo_root / ".gaia" / "models")
    os.environ["GAIA_MODEL_CACHE"] = cache_dir
    os.environ["HF_HOME"] = cache_dir
    os.environ["SENTENCE_TRANSFORMERS_HOME"] = cache_dir
    Path(cache_dir).mkdir(parents=True, exist_ok=True)

    print(f"[SMOKE WARMUP] Initializing model warmup: {model_name} (revision: {revision}, backend: {backend})")

    # 1. Shared getSentenceTransformer with full config and revision applied
    t0 = time.perf_counter()
    try:
        from gaia_cli.curation.retrieval import getSentenceTransformer  # type: ignore

        model = getSentenceTransformer(model_name, revision=revision, backend=backend, pooling=cfg_data.get("pooling"))
    except Exception as exc:
        clean_err = sanitize_secrets(str(exc))
        print(f"[SMOKE WARMUP] ERROR: Failed loading model '{model_name}': {clean_err}", file=sys.stderr)
        return 1
    load_time_ms = round((time.perf_counter() - t0) * 1000, 2)

    # 2. Direct model query
    warmup_name = "Browser Session Controller"
    warmup_desc = "low-level browser DOM/cookie/navigation operations"
    warmup_query = f"{warmup_name}: {warmup_desc}"

    t1 = time.perf_counter()
    try:
        from gaia_cli.semantic_search import embed_query  # type: ignore

        direct_vec = embed_query(
            warmup_query,
            model_name=model_name,
            config=cfg_data,
        )
    except Exception as exc:
        clean_err = sanitize_secrets(str(exc))
        print(f"[SMOKE WARMUP] ERROR: Direct query encoding failed: {clean_err}", file=sys.stderr)
        return 1
    direct_time_ms = round((time.perf_counter() - t1) * 1000, 2)
    dim_ok = len(direct_vec) == expected_dim
    if not dim_ok:
        print(f"[SMOKE WARMUP] ERROR: Direct vector dimension mismatch ({len(direct_vec)} != {expected_dim})", file=sys.stderr)
        return 1

    # 3. Valid local temporary registry containing 2 synthetic nodes and graph (zero real registry mutation)
    t2 = time.perf_counter()
    try:
        from gaia_cli.embeddings import embed_skills  # type: ignore
        from gaia_cli.prefill import buildPrefillPacket, selfValidatePacket  # type: ignore

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            reg_dir = tmp_root / "registry"
            reg_dir.mkdir(parents=True, exist_ok=True)
            nodes_dir = reg_dir / "nodes"
            nodes_dir.mkdir(parents=True, exist_ok=True)

            synthetic_skills = [
                {
                    "id": "browser-control",
                    "name": "Browser Control",
                    "description": "Directly controls a web browser via low-level protocols to manipulate DOM, cookies, and navigation",
                },
                {
                    "id": "test-generation",
                    "name": "Test Generation",
                    "description": "Automated unit test generation",
                },
            ]
            (reg_dir / "gaia.json").write_text(json.dumps({"skills": synthetic_skills}, indent=2), encoding="utf-8")
            for s in synthetic_skills:
                (nodes_dir / f"{s['id']}.json").write_text(json.dumps(s, indent=2), encoding="utf-8")

            # Encode synthetic docs with embed_skills (NOT embed_query!)
            entries, dim = embed_skills(
                synthetic_skills,
                model_name=model_name,
                revision=revision,
                config=cfg_data,
            )
            synthetic_embeddings = {
                "entries": entries,
                "dimensions": dim,
                "model": model_name,
                "fingerprint": "synthetic-warmup-fingerprint",
            }

            fixture_bytes = (
                f"---\n"
                f"name: {warmup_name}\n"
                f"description: {warmup_desc}\n"
                f"---\n"
                f"# {warmup_name}\n\n"
                f"Bounded warmup fixture for {warmup_desc}.\n"
            ).encode("utf-8")

            def warmup_fixture_fetcher(_url: str) -> bytes:
                return fixture_bytes

            packet = buildPrefillPacket(
                candidateId="smoke/warmup-candidate",
                name=warmup_name,
                description=warmup_desc,
                canonicalUrl="https://github.com/gaia-research/smoke-warmup/blob/main/SKILL.md",
                sourceLane="source-repository",
                embeddings=synthetic_embeddings,
                thresholds={"strongMap": 0.72, "weakMap": 0.45, "topK": 3},
                registryPath=tmp_root,
                precomputedVector=None,
                modelName=model_name,
                config=cfg_data,
                fetcher=warmup_fixture_fetcher,
            )

            packet_errors = selfValidatePacket(packet)
            if packet_errors:
                print(f"[SMOKE WARMUP] ERROR: selfValidatePacket failed: {packet_errors}", file=sys.stderr)
                return 1

            options = packet.get("mappingOptions", [])
            if not options:
                print("[SMOKE WARMUP] Notice: Prefill query produced empty recall (0 mapping options above threshold).", file=sys.stderr)

            if "l4Resolution" in packet:
                print("[SMOKE WARMUP] ERROR: Illegal l4Resolution present in prefill packet", file=sys.stderr)
                return 1

    except Exception as exc:
        clean_err = sanitize_secrets(str(exc))
        print(f"[SMOKE WARMUP] ERROR: Warmup prefill failed: {clean_err}", file=sys.stderr)
        return 1

    prefill_time_ms = round((time.perf_counter() - t2) * 1000, 2)
    rss_mb = get_approx_rss_mb()

    print(f"[SMOKE WARMUP] Load latency: {load_time_ms} ms")
    print(f"[SMOKE WARMUP] Direct vector latency: {direct_time_ms} ms (dim: {len(direct_vec)}, expected: {expected_dim})")
    print(f"[SMOKE WARMUP] Prefill packet latency: {prefill_time_ms} ms (mapping options: {len(options)})")
    print(f"[SMOKE WARMUP] Approximate peak RSS: {rss_mb} MB")
    print("[SMOKE WARMUP] Result: OK (zero registry/intake artifacts created)")
    return 0


def run_termux_smoke(
    repo_root: Path,
    output_path: Optional[str] = None,
    model_override: Optional[str] = None,
    embeddings_override: Optional[str] = None,
) -> int:
    """Genuine Termux/aarch64 smoke test and receipt generator.

    MUST return nonzero on non-Android/non-aarch64 platform.
    Requires fresh embeddings artifact matching active config (no silent fallback).
    Executes buildPrefillPacket without precomputedVector, validates via selfValidatePacket.
    """
    src_dir = (repo_root / "src").resolve()
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    receipt_path = Path(output_path).resolve() if output_path else (repo_root / "generated-output" / "curation" / "termux-smoke.json")
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    rss_start = get_approx_rss_mb()

    termux_proof = doctor.check_termux_proof()

    # Query dependency versions via metadata (safe)
    deps_versions: Dict[str, Optional[str]] = {}
    for mod, pkg in [("torch", "torch"), ("sentence_transformers", "sentence-transformers"), ("numpy", "numpy"), ("onnxruntime", "onnxruntime")]:
        if importlib.util.find_spec(mod) is not None:
            try:
                deps_versions[mod] = str(importlib.metadata.version(pkg))
            except Exception:
                deps_versions[mod] = "installed"
        else:
            deps_versions[mod] = None

    limitations: List[str] = []
    install_steps: List[str] = []
    recommendations: List[str] = []

    # 1. Genuine Platform Gate: MUST return nonzero on non-Android / non-aarch64!
    if not termux_proof.get("genuine_termux_aarch64"):
        limitations.append(f"Host platform ({platform.system()}/{platform.machine()}) is not genuine Termux Android/aarch64.")
        receipt = {
            "status": "unsupported_platform",
            "timestamp": timestamp,
            "platform": termux_proof,
            "error": "Non-Termux / non-Android platform: Termux smoke verification requires genuine Android/aarch64 hardware.",
            "limitations": limitations,
            "install_steps": ["Execute termux-smoke on an Android aarch64 device within Termux."],
            "recommendations": ["Platform verification requires native Android device."],
        }
        receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        print(f"[TERMUX SMOKE] FAILED: Host is not genuine Termux Android/aarch64. Receipt: {receipt_path}", file=sys.stderr)
        return 1

    # 2. Dependency Readiness Gate
    if not deps_versions.get("sentence_transformers") or not deps_versions.get("torch"):
        if not deps_versions.get("torch"):
            limitations.append("Missing native torch runtime on Termux.")
            install_steps.append("pkg install python-torch")
        if not deps_versions.get("sentence_transformers"):
            limitations.append("Missing sentence-transformers in active virtualenv.")
            install_steps.append("pip install sentence-transformers")

        receipt = {
            "status": "failed",
            "timestamp": timestamp,
            "platform": termux_proof,
            "dependencies": deps_versions,
            "error": "Required ML dependencies missing on Termux environment.",
            "limitations": limitations,
            "install_steps": install_steps,
            "recommendations": ["Install missing runtime dependencies using exact install steps."],
        }
        receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        print(f"[TERMUX SMOKE] FAILED: Missing ML dependencies. Receipt: {receipt_path}", file=sys.stderr)
        return 1

    # 3. Retrieval configuration resolution
    if model_override:
        try:
            from gaia_cli.curation.retrieval import loadRetrievalConfig  # type: ignore

            cfg_data = loadRetrievalConfig(registryPath=str(repo_root), modelName=model_override)
            model_name = model_override
            revision = cfg_data.get("revision")
            backend = cfg_data.get("backend", "torch")
            expected_dim = cfg_data.get("dimensions", 384)
            cfg_source = "cli_override"
        except Exception as exc:
            clean_err = sanitize_secrets(str(exc))
            receipt = {"status": "failed", "timestamp": timestamp, "platform": termux_proof, "error": f"Failed retrieval config: {clean_err}"}
            receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
            print(f"[TERMUX SMOKE] FAILED: Retrieval config error: {clean_err}", file=sys.stderr)
            return 1
    else:
        ret_info = doctor.check_retrieval(repo_root)
        if not ret_info.get("ok"):
            clean_err = sanitize_secrets(str(ret_info.get("error")))
            receipt = {"status": "failed", "timestamp": timestamp, "platform": termux_proof, "error": f"Failed retrieval config: {clean_err}"}
            receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
            print(f"[TERMUX SMOKE] FAILED: Retrieval config error: {clean_err}", file=sys.stderr)
            return 1
        model_name = ret_info.get("model", "all-MiniLM-L6-v2")
        revision = ret_info.get("revision")
        backend = ret_info.get("backend", "torch")
        expected_dim = ret_info.get("dimensions", 384)
        cfg_data = ret_info.get("config", {})
        cfg_source = ret_info.get("source", "core_api")

    pooling = cfg_data.get("pooling")
    normalize = cfg_data.get("normalize", True)
    query_prefix = cfg_data.get("queryPrefix") or cfg_data.get("query_prefix")

    cache_dir = os.environ.get("GAIA_MODEL_CACHE") or str(repo_root / ".gaia" / "models")
    os.environ["GAIA_MODEL_CACHE"] = cache_dir
    os.environ["HF_HOME"] = cache_dir
    os.environ["SENTENCE_TRANSFORMERS_HOME"] = cache_dir
    Path(cache_dir).mkdir(parents=True, exist_ok=True)

    # 4. Strict Embedding Freshness Check (No silent fallback or catalog[:25] fallback!)
    art_path = Path(embeddings_override).resolve() if embeddings_override else (repo_root / "registry" / "embeddings.json")
    from gaia_cli.curation.retrieval import embeddingStatus  # type: ignore
    from gaia_cli.semantic_search import load_embeddings  # type: ignore

    emb_status = embeddingStatus(registryPath=str(repo_root), artifactPath=str(art_path), config=cfg_data)
    if emb_status.get("status") != "fresh":
        st_reason = emb_status.get("reason", "Artifact not fresh")
        err_msg = (
            f"Embeddings artifact at '{art_path}' is {emb_status.get('status')} ({st_reason}). "
            "Remediation: run 'gaia dev embed' to generate fresh embeddings matching the active registry."
        )
        recommendations.append("Run 'gaia dev embed' to generate fresh embeddings matching active registry.")
        receipt = {
            "status": "stale_embeddings",
            "timestamp": timestamp,
            "platform": termux_proof,
            "dependencies": deps_versions,
            "error": err_msg,
            "artifact_status": emb_status,
            "recommendations": recommendations,
        }
        receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        print(f"[TERMUX SMOKE] FAILED: {err_msg}", file=sys.stderr)
        return 1

    try:
        repo_embeddings = load_embeddings(str(art_path), validate=True)
    except Exception as exc:
        clean_err = sanitize_secrets(str(exc))
        receipt = {
            "status": "invalid_embeddings",
            "timestamp": timestamp,
            "platform": termux_proof,
            "dependencies": deps_versions,
            "error": f"Failed loading embeddings artifact: {clean_err}",
            "recommendations": ["Run 'gaia dev embed' to regenerate valid embeddings."],
        }
        receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        print(f"[TERMUX SMOKE] FAILED: {clean_err}", file=sys.stderr)
        return 1

    # 5. Model Load via shared getSentenceTransformer with full revision/backend/pooling
    t0 = time.perf_counter()
    try:
        from gaia_cli.curation.retrieval import getSentenceTransformer  # type: ignore

        model = getSentenceTransformer(model_name, revision=revision, backend=backend, pooling=pooling)
    except Exception as exc:
        clean_err = sanitize_secrets(str(exc))
        receipt = {
            "status": "failed",
            "timestamp": timestamp,
            "platform": termux_proof,
            "error": f"Model load failure: {clean_err}",
            "limitations": [clean_err],
        }
        receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        print(f"[TERMUX SMOKE] FAILED: Model load error: {clean_err}", file=sys.stderr)
        return 1
    load_duration_ms = round((time.perf_counter() - t0) * 1000, 2)

    # 6. Direct vector extraction
    candidate_name = "Browser Session Controller"
    candidate_desc = "low-level browser DOM/cookie/navigation operations"
    query_text = f"{candidate_name}: {candidate_desc}"

    t_direct = time.perf_counter()
    try:
        from gaia_cli.semantic_search import embed_query  # type: ignore

        direct_vec = embed_query(
            query_text,
            model_name=model_name,
            config=cfg_data,
        )
    except Exception as exc:
        clean_err = sanitize_secrets(str(exc))
        receipt = {
            "status": "failed",
            "timestamp": timestamp,
            "platform": termux_proof,
            "error": f"Direct vector failure: {clean_err}",
        }
        receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        print(f"[TERMUX SMOKE] FAILED: Direct vector error: {clean_err}", file=sys.stderr)
        return 1
    direct_duration_ms = round((time.perf_counter() - t_direct) * 1000, 2)
    direct_dim = len(direct_vec)
    if direct_dim != expected_dim:
        err_msg = f"Direct vector dimension mismatch ({direct_dim} != {expected_dim})"
        receipt = {"status": "dimension_mismatch", "timestamp": timestamp, "platform": termux_proof, "error": err_msg}
        receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        print(f"[TERMUX SMOKE] FAILED: {err_msg}", file=sys.stderr)
        return 1

    # 7. Real Gaia prefill query WITHOUT precomputedVector using transparent recorded fixture
    t_prefill = time.perf_counter()
    try:
        from gaia_cli.prefill import buildPrefillPacket, selfValidatePacket  # type: ignore

        fixture_bytes = (
            f"---\n"
            f"name: {candidate_name}\n"
            f"description: {candidate_desc}\n"
            f"---\n"
            f"# {candidate_name}\n\n"
            f"Synthetic recorded fixture for {candidate_desc}.\n"
        ).encode("utf-8")

        def transparent_fixture_fetcher(_url: str) -> bytes:
            return fixture_bytes

        packet = buildPrefillPacket(
            candidateId="smoke/termux",
            name=candidate_name,
            description=candidate_desc,
            canonicalUrl="https://github.com/gaia-research/termux-smoke/blob/main/SKILL.md",
            sourceLane="source-repository",
            embeddings=repo_embeddings,
            thresholds={"strongMap": 0.72, "weakMap": 0.45, "topK": 3},
            registryPath=repo_root,
            precomputedVector=None,
            modelName=model_name,
            config=cfg_data,
            fetcher=transparent_fixture_fetcher,
        )

        packet_errors = selfValidatePacket(packet)
        if packet_errors:
            err_msg = f"selfValidatePacket failed on generated packet: {packet_errors}"
            receipt = {
                "status": "invalid_packet",
                "timestamp": timestamp,
                "platform": termux_proof,
                "error": err_msg,
                "packet_errors": packet_errors,
            }
            receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
            print(f"[TERMUX SMOKE] FAILED: {err_msg}", file=sys.stderr)
            return 1

        actual_options = packet.get("mappingOptions", [])
        if not actual_options:
            # A valid empty recall is a legitimate retrieval result, not an encoder failure
            print("[TERMUX SMOKE] Notice: Prefill query produced empty recall (0 mapping options above threshold).", file=sys.stderr)

        if "l4Resolution" in packet:
            err_msg = "Illegal l4Resolution present in discovery prefill packet"
            receipt = {"status": "invalid_l4_present", "timestamp": timestamp, "platform": termux_proof, "error": err_msg}
            receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
            print(f"[TERMUX SMOKE] FAILED: {err_msg}", file=sys.stderr)
            return 1

    except Exception as exc:
        clean_err = sanitize_secrets(str(exc))
        receipt = {
            "status": "failed",
            "timestamp": timestamp,
            "platform": termux_proof,
            "error": f"Prefill query error: {clean_err}",
        }
        receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        print(f"[TERMUX SMOKE] FAILED: Real prefill query error: {clean_err}", file=sys.stderr)
        return 1

    prefill_duration_ms = round((time.perf_counter() - t_prefill) * 1000, 2)
    rss_peak = get_approx_rss_mb()
    artifact_fp = repo_embeddings.get("fingerprint") or emb_status.get("fingerprint")

    # 8. Full Semantic Configuration & Receipt
    semantic_config = {
        "model": model_name,
        "declared_name": model_name,
        "revision": revision,
        "backend": backend,
        "dimensions": expected_dim,
        "pooling": pooling,
        "normalize": normalize,
        "query_prefix": query_prefix,
        "fingerprint": artifact_fp,
        "config_source": cfg_source,
        "artifact_path": str(art_path),
    }

    receipt = {
        "status": "success",
        "timestamp": timestamp,
        "platform": termux_proof,
        "python": {"version": platform.python_version(), "executable": sys.executable},
        "dependencies": deps_versions,
        "semantic_config": semantic_config,
        "model": {
            "declared_name": model_name,
            "revision": revision,
            "backend": backend,
            "dimensions": expected_dim,
            "pooling": pooling,
            "normalize": normalize,
            "query_prefix": query_prefix,
            "config_source": cfg_source,
            "cache_dir": cache_dir,
            "fingerprint": artifact_fp,
        },
        "fingerprint": artifact_fp,
        "source": {
            "candidate_id": "smoke/termux",
            "candidate_name": candidate_name,
            "source_lane": "source-repository",
            "recorded_fixture_fetcher": True,
            "transparent_fixture": True,
            "synthetic_candidate": True,
            "note": "Transparent recorded fixture fetcher for synthetic capability Browser Session Controller; not live upstream proof",
        },
        "metrics": {
            "load_duration_ms": load_duration_ms,
            "direct_duration_ms": direct_duration_ms,
            "direct_vector_dim": direct_dim,
            "prefill_duration_ms": prefill_duration_ms,
            "actual_mapping_options": actual_options,
            "rss_initial_mb": rss_start,
            "rss_peak_mb": rss_peak,
        },
        "limitations": limitations,
        "install_steps": install_steps,
        "recommendations": recommendations,
    }

    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")

    print(f"=== Gaia Termux Curation Smoke [OK] ===")
    print(f"Status: success")
    print(f"Model: {model_name} (revision={revision}, backend={backend}, pooling={pooling})")
    print(f"Direct latency: {direct_duration_ms} ms | Prefill latency: {prefill_duration_ms} ms")
    print(f"Actual mapping options count: {len(actual_options)}")
    print(f"Peak RSS: {rss_peak} MB")
    print(f"Receipt written: {receipt_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Gaia Curation Environment Smoke Helper")
    parser.add_argument("--warmup", action="store_true", help="Run bounded source-local warmup only")
    parser.add_argument("--termux", action="store_true", help="Run genuine Termux aarch64 smoke test")
    parser.add_argument("--output", type=str, default=None, help="Receipt output path for --termux")
    parser.add_argument("--registry", type=str, default=None, help="Path to repo/registry root")
    parser.add_argument("--model", type=str, default=None, help="Model override for candidate smoke")
    parser.add_argument("--embeddings", type=str, default=None, help="Embeddings artifact override for candidate smoke")
    args = parser.parse_args()

    repo_root = doctor.get_repo_root(args.registry)
    if args.warmup:
        return run_warmup(repo_root, model_override=args.model)
    if args.termux:
        return run_termux_smoke(
            repo_root,
            output_path=args.output,
            model_override=args.model,
            embeddings_override=args.embeddings,
        )

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
