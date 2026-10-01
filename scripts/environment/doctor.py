#!/usr/bin/env python3
"""Gaia Curation Environment Doctor: lightweight diagnostics (never importing torch/ST)."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import platform
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def get_repo_root(registry_path: Optional[str] = None) -> Path:
    return Path(registry_path).resolve() if registry_path else Path(__file__).resolve().parent.parent.parent


def check_source_import(repo_root: Path) -> Dict[str, Any]:
    src_dir = (repo_root / "src").resolve()
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    try:
        import gaia_cli  # type: ignore

        cli_file = getattr(gaia_cli, "__file__", None)
        resolved = str(Path(cli_file).resolve()) if cli_file else ""
        matched = resolved.startswith(str(src_dir))
        ver: Optional[str] = None
        pyproject = repo_root / "pyproject.toml"
        if pyproject.is_file():
            try:
                for line in pyproject.read_text(encoding="utf-8").splitlines():
                    if line.startswith("version = "):
                        ver = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
            except Exception:
                pass
        if not ver:
            for pkg in ("gaia-cli", "gaia_cli"):
                try:
                    ver = str(importlib.metadata.version(pkg))
                    break
                except Exception:
                    pass
        ver = ver or getattr(gaia_cli, "__version__", None) or "0.1.0"
        return {
            "ok": bool(matched),
            "package": "gaia_cli",
            "path": resolved,
            "source_matched": matched,
            "version": str(ver),
        }
    except Exception as exc:
        return {
            "ok": False,
            "package": "gaia_cli",
            "path": None,
            "source_matched": False,
            "version": None,
            "error": str(exc),
        }


def check_dependencies(selected_backend: str = "torch") -> Dict[str, Any]:
    py_ok = sys.version_info >= (3, 10)
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    python_info = {
        "version": platform.python_version(),
        "executable": sys.executable,
        "in_venv": in_venv,
        "version_ok": py_ok,
    }

    def _mod(name: str, pkg: str) -> Dict[str, Any]:
        if importlib.util.find_spec(name) is None:
            return {"available": False, "version": None}
        try:
            ver = importlib.metadata.version(pkg)
        except Exception:
            ver = "installed"
        return {"available": True, "version": str(ver)}

    core = {
        k: _mod(k, p)
        for k, p in {
            "jinja2": "jinja2",
            "jsonschema": "jsonschema",
            "yaml": "PyYAML",
            "questionary": "questionary",
            "pytest": "pytest",
        }.items()
    }
    ml = {
        k: _mod(k, p)
        for k, p in {
            "sentence_transformers": "sentence-transformers",
            "torch": "torch",
            "numpy": "numpy",
            "onnxruntime": "onnxruntime",
        }.items()
    }
    return {
        "python": python_info,
        "core": {"all_core_ok": all(v["available"] for v in core.values()), "modules": core},
        "ml": ml,
    }


def check_retrieval(repo_root: Path) -> Dict[str, Any]:
    src_dir = (repo_root / "src").resolve()
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    try:
        from gaia_cli.curation.retrieval import loadRetrievalConfig  # type: ignore

        cfg = loadRetrievalConfig(registryPath=str(repo_root))
        model = cfg.get("modelId") or cfg.get("model")
        return {
            "ok": bool(model),
            "model": model,
            "revision": cfg.get("revision"),
            "backend": cfg.get("backend", "torch"),
            "dimensions": cfg.get("dimensions", 384),
            "source": "core_api",
            "config": cfg,
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": f"Retrieval config load failed: {exc}",
            "model": None,
            "source": "failed",
        }


def check_artifact_freshness(repo_root: Path, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    src_dir = (repo_root / "src").resolve()
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    try:
        from gaia_cli.curation.retrieval import embeddingStatus  # type: ignore

        st = embeddingStatus(registryPath=str(repo_root), config=config)
        is_fresh = bool(st.get("status") == "fresh")
        is_present = bool(st.get("status") != "missing")
        return {
            "ok": is_fresh,
            "fresh": is_fresh,
            "present": is_present,
            "status": st,
        }
    except Exception as exc:
        return {
            "ok": False,
            "fresh": False,
            "present": False,
            "error": str(exc),
            "status": {"status": "error", "reason": str(exc)},
        }


def check_typesafe_credential() -> Dict[str, Any]:
    return {"configured": bool(os.environ.get("TYPESAFE_API_KEY", "").strip())}


def check_rubric_version(repo_root: Path) -> Dict[str, Any]:
    p = repo_root / "src" / "gaia_cli" / "data" / "curation" / "principles.json"
    if not p.is_file():
        return {
            "present": False,
            "path": "src/gaia_cli/data/curation/principles.json",
            "version": None,
        }
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return {
            "present": True,
            "path": str(p.relative_to(repo_root)),
            "version": str(d.get("version") or d.get("rubricVersion")),
        }
    except Exception as e:
        return {
            "present": True,
            "path": str(p.relative_to(repo_root)),
            "version": None,
            "error": str(e),
        }


def is_curation_eval_receipt(data: Any) -> bool:
    """Identify an evaluation receipt strictly by JSON schema, never filename substrings."""
    if not isinstance(data, dict):
        return False
    return bool(
        "corpus_sha256" in data
        and "catalog_sha256" in data
        and isinstance(data.get("config"), dict)
    )


def check_curation_eval_receipt(repo_root: Path, active_retrieval: Dict[str, Any]) -> Dict[str, Any]:
    corpus_file = repo_root / "tests" / "fixtures" / "curation-oracle.json"
    corpus_sha = hashlib.sha256(corpus_file.read_bytes()).hexdigest() if corpus_file.is_file() else None

    catalog_sha = None
    try:
        from gaia_cli.curation.evaluation import load_catalog  # type: ignore

        catalog = load_catalog(repo_root)
        catalog_sha = hashlib.sha256(
            json.dumps(catalog, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
    except Exception:
        pass

    candidate_dirs = [repo_root / "generated-output" / "curation", repo_root / "generated-output"]
    all_receipts: List[Tuple[Path, Dict[str, Any]]] = []
    for d in candidate_dirs:
        if not d.is_dir():
            continue
        for p in d.glob("*.json"):
            if p.name.endswith("-smoke.json"):
                continue
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if is_curation_eval_receipt(data):
                    all_receipts.append((p, data))
            except Exception:
                continue

    if not all_receipts:
        return {"present": False, "matches_active": False, "reason": "No receipt found"}

    act_cfg = (
        active_retrieval.get("config")
        if isinstance(active_retrieval.get("config"), dict)
        else active_retrieval
    )
    act_model = active_retrieval.get("model") or act_cfg.get("modelId") or act_cfg.get("model")
    act_rev = active_retrieval.get("revision") if "revision" in active_retrieval else act_cfg.get("revision")
    act_b = active_retrieval.get("backend") or act_cfg.get("backend", "torch")
    act_dim = active_retrieval.get("dimensions") or act_cfg.get("dimensions")
    act_norm = act_cfg.get("normalize")
    act_pool = act_cfg.get("pooling")
    act_pfx = act_cfg.get("queryPrefix") if "queryPrefix" in act_cfg else act_cfg.get("query_prefix")

    def _eval_mismatches(d: Dict[str, Any]) -> List[str]:
        r_cfg = d.get("config", {})
        r_corpus = d.get("corpus_sha256")
        r_catalog = d.get("catalog_sha256")
        r_model = r_cfg.get("model") or r_cfg.get("modelId")
        r_rev = r_cfg.get("revision")
        r_b = r_cfg.get("backend", "torch")
        r_dim = r_cfg.get("dimensions")
        r_norm = r_cfg.get("normalize")
        r_pool = r_cfg.get("pooling")
        r_pfx = r_cfg.get("queryPrefix") if "queryPrefix" in r_cfg else r_cfg.get("query_prefix")

        m = []
        if corpus_sha and r_corpus != corpus_sha:
            m.append(f"corpus_sha mismatch ({r_corpus} != {corpus_sha})")
        if catalog_sha and r_catalog != catalog_sha:
            m.append(f"catalog_sha mismatch ({r_catalog} != {catalog_sha})")
        if act_model and r_model != act_model:
            m.append(f"model mismatch ({r_model} != {act_model})")
        if act_rev is not None and r_rev != act_rev:
            m.append(f"revision mismatch ({r_rev} != {act_rev})")
        if act_b and r_b != act_b:
            m.append(f"backend mismatch ({r_b} != {act_b})")
        if act_dim is not None and r_dim is not None and r_dim != act_dim:
            m.append(f"dimensions mismatch ({r_dim} != {act_dim})")
        if act_pool is not None and r_pool is not None and r_pool != act_pool:
            m.append(f"pooling mismatch ({r_pool} != {act_pool})")
        if act_norm is not None and r_norm is not None and r_norm != act_norm:
            m.append(f"normalize mismatch ({r_norm} != {act_norm})")
        if act_pfx is not None and r_pfx != act_pfx:
            m.append(f"queryPrefix mismatch ({r_pfx!r} != {act_pfx!r})")
        return m

    # Score and sort receipts: exact matching active first, then most recently modified
    evaluated_receipts = []
    for path, data in all_receipts:
        mismatches = _eval_mismatches(data)
        evaluated_receipts.append((path, data, mismatches))

    evaluated_receipts.sort(
        key=lambda item: (len(item[2]) == 0, item[0].stat().st_mtime),
        reverse=True,
    )
    chosen_path, chosen_data, chosen_mismatches = evaluated_receipts[0]

    # Explicit baseline search: all-MiniLM-L6-v2 without reranker, matching corpus/catalog
    baseline_data: Optional[Dict[str, Any]] = None
    for _, b_candidate in all_receipts:
        b_cfg = b_candidate.get("config", {})
        b_model = b_cfg.get("model") or b_cfg.get("modelId")
        if (
            b_model == "all-MiniLM-L6-v2"
            and not b_cfg.get("reranker")
            and (not corpus_sha or b_candidate.get("corpus_sha256") == corpus_sha)
            and (not catalog_sha or b_candidate.get("catalog_sha256") == catalog_sha)
        ):
            baseline_data = b_candidate
            break

    # Regression status: report against explicit baseline only, else "unknown"
    chosen_model = chosen_data.get("config", {}).get("model") or chosen_data.get("config", {}).get("modelId")
    is_itself_baseline = bool(
        chosen_model == "all-MiniLM-L6-v2"
        and not chosen_data.get("config", {}).get("reranker")
    )

    if baseline_data and not is_itself_baseline:
        # Metrics comparison against explicit baseline
        c_metrics = chosen_data.get("metrics", {})
        b_metrics = baseline_data.get("metrics", {})
        c_top1 = c_metrics.get("top1")
        b_top1 = b_metrics.get("top1")
        c_mrr = c_metrics.get("mrr")
        b_mrr = b_metrics.get("mrr")

        if c_top1 is not None and b_top1 is not None and c_mrr is not None and b_mrr is not None:
            if c_top1 < b_top1 or c_mrr < b_mrr:
                metrics_status = "regressed"
            elif c_top1 > b_top1 or c_mrr > b_mrr:
                metrics_status = "improved"
            else:
                metrics_status = "neutral"
        else:
            metrics_status = "unknown"

        # Time comparison against explicit baseline
        c_latencies = chosen_data.get("latencies", {})
        b_latencies = baseline_data.get("latencies", {})
        c_time = c_latencies.get("query_seconds") or chosen_data.get("elapsed_seconds")
        b_time = b_latencies.get("query_seconds") or baseline_data.get("elapsed_seconds")

        if c_time is not None and b_time is not None and b_time > 0:
            if c_time > b_time * 1.05:
                time_status = "regressed"
            elif c_time < b_time * 0.95:
                time_status = "improved"
            else:
                time_status = "neutral"
        else:
            time_status = "unknown"
    else:
        time_status = "unknown"
        metrics_status = "unknown"

    return {
        "present": True,
        "path": str(chosen_path.relative_to(repo_root)),
        "matches_active": len(chosen_mismatches) == 0 and bool(
            chosen_data.get("corpus_sha256") and chosen_data.get("catalog_sha256")
        ),
        "mismatches": chosen_mismatches,
        "model": chosen_model,
        "regression_status": {
            "time": time_status,
            "metrics": metrics_status,
            "baseline_present": baseline_data is not None,
        },
    }


def check_smoke_receipt(
    repo_root: Path,
    active_retrieval: Dict[str, Any],
    active_freshness: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    smoke_file = repo_root / "generated-output" / "curation" / "termux-smoke.json"
    if not smoke_file.is_file():
        return {
            "present": False,
            "matches_active": False,
            "actual_android_proof": False,
            "reason": "No smoke receipt found",
        }
    try:
        d = json.loads(smoke_file.read_text(encoding="utf-8"))
        st = d.get("status")
        m_info = d.get("model", {})
        sem_cfg = d.get("semantic_config", {})
        plat = d.get("platform", {})
        is_android = bool(
            plat.get("genuine_termux_aarch64")
            or (plat.get("is_android") and plat.get("arch") in ("aarch64", "arm64", "armv8l"))
        )

        cfg = (
            active_retrieval.get("config")
            if isinstance(active_retrieval.get("config"), dict)
            else active_retrieval
        )
        act_m = active_retrieval.get("model") or cfg.get("modelId") or cfg.get("model")
        act_r = active_retrieval.get("revision") if "revision" in active_retrieval else cfg.get("revision")
        act_b = active_retrieval.get("backend", "torch")
        act_pool = cfg.get("pooling")
        act_norm = cfg.get("normalize")
        act_pfx = cfg.get("queryPrefix") if "queryPrefix" in cfg else cfg.get("query_prefix")

        mismatches: List[str] = [f"status: {st}"] if st != "success" else []

        # Required semantic config values: reject missing values
        rec_m = sem_cfg.get("model") or m_info.get("declared_name")
        if not rec_m:
            mismatches.append("missing model in smoke receipt")
        elif act_m and rec_m != act_m:
            mismatches.append(f"model: {rec_m} != {act_m}")

        rec_b = sem_cfg.get("backend") or m_info.get("backend")
        if not rec_b:
            mismatches.append("missing backend in smoke receipt")
        elif act_b and rec_b != act_b:
            mismatches.append(f"backend: {rec_b} != {act_b}")

        rec_pool = sem_cfg.get("pooling") if "pooling" in sem_cfg else m_info.get("pooling")
        if act_pool is not None and rec_pool != act_pool:
            mismatches.append(f"pooling: {rec_pool} != {act_pool}")

        rec_norm = sem_cfg.get("normalize") if "normalize" in sem_cfg else m_info.get("normalize")
        if act_norm is not None and rec_norm != act_norm:
            mismatches.append(f"normalize: {rec_norm} != {act_norm}")

        rec_pfx = sem_cfg.get("query_prefix") if "query_prefix" in sem_cfg else m_info.get("query_prefix")
        if act_pfx is not None and rec_pfx != act_pfx:
            mismatches.append(f"query_prefix: {rec_pfx} != {act_pfx}")

        rec_rev = sem_cfg.get("revision") if "revision" in sem_cfg else m_info.get("revision")
        if act_r is not None and rec_rev != act_r:
            mismatches.append(f"revision: {rec_rev} != {act_r}")

        # Fingerprint verification: reject missing fingerprints
        rec_fp = sem_cfg.get("fingerprint") or d.get("fingerprint") or m_info.get("fingerprint")
        if active_freshness is not None:
            act_fp = None
            if isinstance(active_freshness, dict):
                st_info = active_freshness.get("status", {})
                act_fp = st_info.get("fingerprint") or st_info.get("expectedFingerprint")
            if not act_fp:
                mismatches.append("missing active artifact fingerprint")
            if not rec_fp:
                mismatches.append("missing fingerprint in smoke receipt")
            elif act_fp and rec_fp != act_fp:
                mismatches.append(f"fingerprint: {rec_fp} != {act_fp}")

        if not is_android:
            mismatches.append("not Android/aarch64")

        matches = len(mismatches) == 0
        return {
            "present": True,
            "path": str(smoke_file.relative_to(repo_root)),
            "status": st,
            "matches_active": matches,
            "actual_android_proof": is_android and (st == "success") and matches,
            "mismatches": mismatches,
        }
    except Exception as exc:
        return {
            "present": True,
            "path": str(smoke_file.relative_to(repo_root)),
            "matches_active": False,
            "actual_android_proof": False,
            "error": str(exc),
        }


def is_real_android() -> bool:
    """Check for real Android runtime via Python API or /system markers, never solely env/uname."""
    # 1. Python Android API (available in standard Python Android/Termux builds)
    if hasattr(sys, "getandroidapilevel"):
        try:
            lvl = sys.getandroidapilevel()
            if isinstance(lvl, int) and lvl > 0:
                return True
        except Exception:
            pass

    # 2. Real /system Android filesystem markers
    for marker in ("/system/build.prop", "/system/bin/getprop", "/system/framework"):
        if os.path.exists(marker):
            return True

    return False


def check_termux_proof(smoke_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    arch = platform.machine().lower()
    is_aarch64 = arch in ("aarch64", "arm64", "armv8l")
    real_android = is_real_android()
    genuine = real_android and is_aarch64

    # Genuine proof requires actual Android/aarch64 hardware proof AND matching smoke receipt
    proof = (
        "proven"
        if (
            genuine
            and smoke_info
            and smoke_info.get("actual_android_proof")
            and smoke_info.get("matches_active")
        )
        else ("provisional" if genuine else "non-termux")
    )
    return {
        "genuine_termux_aarch64": genuine,
        "proof_status": proof,
        "is_android": real_android,
        "arch": arch,
    }


SECRET_PATTERNS = [
    (
        "api_key",
        re.compile(
            r"""(?i)\b(?:typesafe|openai|anthropic|github|aws|api)[a-z0-9_]*(?:key|token|secret)\s*[:=]\s*['"][A-Za-z0-9_\-]{8,}['"]"""
        ),
    ),
    ("github_token", re.compile(r"""\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36}\b""")),
    ("private_key", re.compile(r"""-----BEGIN [A-Z ]*PRIVATE KEY-----""")),
    ("openai_key", re.compile(r"""\bsk-[a-zA-Z0-9]{32,}\b""")),
    ("google_key", re.compile(r"""\bAIza[0-9A-Za-z\-_]{35}\b""")),
]


def scan_file_for_secrets(file_path: Path) -> List[Dict[str, Any]]:
    violations: List[Dict[str, Any]] = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return violations
    seen = set()
    for line in content.splitlines():
        for name, pat in SECRET_PATTERNS:
            if name not in seen and pat.search(line):
                seen.add(name)
                violations.append({"file": str(file_path), "pattern": name, "redacted": True})
    return violations


def scan_changed_tracked_files_for_secrets(
    repo_root: Path,
    baseline: str = "origin/main",
    explicit_files: Optional[List[str]] = None,
) -> Tuple[bool, List[Dict[str, Any]]]:
    if explicit_files:
        targets = [
            Path(f) if Path(f).is_absolute() else repo_root / f
            for f in explicit_files
            if (repo_root / f).is_file()
        ]
    else:
        import subprocess

        changed = set()
        for cmd in [
            ["git", "diff", "--name-only", f"{baseline}...HEAD"],
            ["git", "diff", "--name-only", "main...HEAD"],
            ["git", "diff", "--name-only", "--cached"],
            ["git", "diff", "--name-only"],
        ]:
            try:
                changed.update(
                    subprocess.check_output(
                        cmd, cwd=str(repo_root), text=True, stderr=subprocess.DEVNULL
                    ).splitlines()
                )
            except Exception:
                pass
        skip_exts = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".pyc"}
        targets = [
            repo_root / f.strip()
            for f in changed
            if f.strip() and (repo_root / f.strip()).is_file() and (repo_root / f.strip()).suffix.lower() not in skip_exts
        ]
    violations = [v for t in targets for v in scan_file_for_secrets(t)]
    return len(violations) == 0, violations


def run_doctor(repo_root: Optional[Path] = None) -> Dict[str, Any]:
    root = repo_root or get_repo_root()
    src = check_source_import(root)
    ret = check_retrieval(root)

    backend = ret.get("backend", "torch")
    deps = check_dependencies(selected_backend=backend)

    fresh = check_artifact_freshness(root, ret.get("config"))
    cred = check_typesafe_credential()
    rubric = check_rubric_version(root)
    cur_eval = check_curation_eval_receipt(root, ret)
    smoke = check_smoke_receipt(root, ret, active_freshness=fresh)
    termux = check_termux_proof(smoke)

    # For torch backend, both torch and numpy must be available in addition to sentence_transformers
    ml_mods = deps.get("ml", {})
    if backend == "torch":
        st_ok = ml_mods.get("sentence_transformers", {}).get("available", False)
        torch_ok = ml_mods.get("torch", {}).get("available", True if "torch" not in ml_mods else False)
        numpy_ok = ml_mods.get("numpy", {}).get("available", True if "numpy" not in ml_mods else False)
        ml_ready = bool(st_ok and torch_ok and numpy_ok)
    elif backend in ("onnx", "onnxruntime"):
        onnx_ok = ml_mods.get("onnxruntime", {}).get("available", False)
        numpy_ok = ml_mods.get("numpy", {}).get("available", True if "numpy" not in ml_mods else False)
        ml_ready = bool(onnx_ok and numpy_ok)
    else:
        st_ok = ml_mods.get("sentence_transformers", {}).get("available", False)
        torch_ok = ml_mods.get("torch", {}).get("available", True if "torch" not in ml_mods else False)
        numpy_ok = ml_mods.get("numpy", {}).get("available", True if "numpy" not in ml_mods else False)
        ml_ready = bool(st_ok and torch_ok and numpy_ok)

    deps_ready = bool(
        src.get("ok")
        and deps["python"]["version_ok"]
        and deps["core"]["all_core_ok"]
        and ml_ready
    )
    artifact_ready = bool(fresh.get("fresh"))
    healthy = deps_ready and artifact_ready and ret.get("ok", False)

    return {
        "healthy": healthy,
        "deps_ready": deps_ready,
        "artifact_ready": artifact_ready,
        "readiness": {"deps": deps_ready, "artifact": artifact_ready},
        "source_import": src,
        "deps": deps,
        "retrieval": ret,
        "artifact_freshness": fresh,
        "typesafe_credential": cred,
        "rubric_version": rubric,
        "curation_eval_receipt": cur_eval,
        "smoke_receipt": smoke,
        "termux_proof": termux,
    }


def print_human_report(r: Dict[str, Any]) -> None:
    mark = "[OK]" if r.get("healthy") else "[ACTION REQUIRED]"
    print(f"=== Gaia Curation Environment Doctor {mark} ===")
    print(
        f"Readiness: Dependencies={'[OK]' if r['deps_ready'] else '[FAIL]'} | "
        f"Artifact={'[OK]' if r['artifact_ready'] else '[STALE/MISSING]'}"
    )
    print(
        f"Source: {r['source_import'].get('path')} (matched: {r['source_import'].get('source_matched')}) | "
        f"Version: {r['source_import'].get('version')}"
    )
    print(
        f"Retrieval: Model={r['retrieval'].get('model')} "
        f"(revision={r['retrieval'].get('revision')}, backend={r['retrieval'].get('backend')}) "
        f"[ok={r['retrieval'].get('ok')}]"
    )
    print(
        f"Artifact: Fresh={r['artifact_freshness'].get('fresh')} "
        f"[state={r['artifact_freshness'].get('status', {}).get('status')}]"
    )
    print(f"Typesafe Credential: {'[CONFIGURED]' if r['typesafe_credential'].get('configured') else '[NOT SET]'}")
    print(f"Rubric Principles: v{r['rubric_version'].get('version')} ({r['rubric_version'].get('path')})")
    print(f"Curation Eval Receipt: matches_active={r['curation_eval_receipt'].get('matches_active')}")
    print(
        f"Termux Proof: {r['termux_proof'].get('proof_status').upper()} "
        f"(smoke match={r['smoke_receipt'].get('matches_active')})"
    )


def main() -> int:
    p = argparse.ArgumentParser(description="Gaia Curation Environment Doctor")
    p.add_argument("--json", action="store_true", help="Output JSON")
    p.add_argument("--check", action="store_true", help="Health check (exits 0 if healthy)")
    p.add_argument("--check-deps", action="store_true", help="Check dependencies only")
    p.add_argument("--check-artifact", action="store_true", help="Check artifact freshness only")
    p.add_argument("--scan-secrets", action="store_true", help="Scan changed tracked files for secrets")
    p.add_argument("--files", nargs="*", default=None, help="Explicit files for secret scan")
    p.add_argument("--registry", type=str, default=None, help="Path to repo/registry root")
    a = p.parse_args()

    root = get_repo_root(a.registry)
    if a.scan_secrets:
        clean, violations = scan_changed_tracked_files_for_secrets(root, explicit_files=a.files)
        if clean:
            print("[SECRET SCAN] PASSED: No secrets detected in changed tracked files.")
            return 0
        for v in violations:
            print(f"[SECRET SCAN] VIOLATION: {v['file']} matched pattern '{v['pattern']}' (CONTENT REDACTED)")
        return 1

    report = run_doctor(root)
    if a.json:
        print(json.dumps(report, indent=2))
    elif not (a.check or a.check_deps or a.check_artifact):
        print_human_report(report)

    if a.check_deps:
        if not a.json and not report.get("deps_ready"):
            print("[DEPS] Incomplete dependencies for active retrieval", file=sys.stderr)
        return 0 if report.get("deps_ready") else 1

    if a.check_artifact:
        if not report.get("artifact_ready"):
            if not a.json:
                reason = (
                    report.get("artifact_freshness", {})
                    .get("status", {})
                    .get("reason", "Artifact stale or missing")
                )
                print(f"[ARTIFACT] Stale or missing embeddings artifact: {reason}", file=sys.stderr)
            return 1
        return 0

    if a.check:
        return 0 if report.get("healthy") else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
