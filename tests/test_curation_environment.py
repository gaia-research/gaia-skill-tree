"""Tests for portable curation environment tooling.

Tests scripts/environment/setup.sh, doctor.py, maintenance.sh, termux-smoke.sh,
smoke.py, and env.sh. Uses mocks and executable shell stubs to prove call patterns,
error aggregation, and contract behaviors without real pip installs, package builds,
or remote model downloads.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_DIR = REPO_ROOT / "scripts" / "environment"
if str(ENV_DIR) not in sys.path:
    sys.path.insert(0, str(ENV_DIR))

import doctor  # type: ignore
import smoke  # type: ignore
from gaia_cli.curation.retrieval import ENCODER_CONTRACT

doctor.ENCODER_CONTRACT = ENCODER_CONTRACT
smoke.ENCODER_CONTRACT = ENCODER_CONTRACT


class TestDoctor:
    """Tests for doctor.py."""

    def test_doctor_check_mode_healthy_keys(self):
        """doctor report contains all required schema keys."""
        report = doctor.run_doctor(REPO_ROOT)
        required_keys = [
            "healthy",
            "deps_ready",
            "artifact_ready",
            "readiness",
            "source_import",
            "deps",
            "retrieval",
            "artifact_freshness",
            "typesafe_credential",
            "rubric_version",
            "curation_eval_receipt",
            "smoke_receipt",
            "termux_proof",
        ]
        for key in required_keys:
            assert key in report, f"Missing key in doctor report: {key}"

    def test_doctor_no_torch_st_imported(self):
        """Lightweight check: doctor deps inspection must use find_spec/metadata without importing torch/ST."""
        sys.modules.pop("torch", None)
        sys.modules.pop("sentence_transformers", None)

        res = doctor.check_dependencies()
        assert "core" in res
        assert "ml" in res
        assert "torch" not in sys.modules, "doctor.check_dependencies() illegally imported torch!"
        assert "sentence_transformers" not in sys.modules, "doctor.check_dependencies() illegally imported sentence_transformers!"

    def test_retrieval_core_api_required_fail_not_fallback(self):
        """Retrieval config must fail visibly via core API; no silent default fallback to MiniLM."""
        with patch.dict(sys.modules, {"gaia_cli.curation.retrieval": None}):
            res = doctor.check_retrieval(Path("/nonexistent/path"))
            assert res["ok"] is False
            assert res["model"] is None
            assert res["source"] == "failed"
            assert "error" in res

    def test_typesafe_credential_boolean_only(self, monkeypatch):
        """Typesafe credential must be boolean only; JEV_API_KEY is unsupported; secrets never printed."""
        secret_value = "typesafe-secret-key-12345678"
        monkeypatch.setenv("TYPESAFE_API_KEY", secret_value)
        monkeypatch.delenv("JEV_API_KEY", raising=False)

        res = doctor.check_typesafe_credential()
        assert res["configured"] is True

        report = doctor.run_doctor(REPO_ROOT)
        dumped = json.dumps(report)
        assert secret_value not in dumped

        # Test JEV_API_KEY unsupported: setting JEV_API_KEY alone does NOT configure Typesafe
        monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
        monkeypatch.setenv("JEV_API_KEY", "jev-unsupported-key")
        res_jev = doctor.check_typesafe_credential()
        assert res_jev["configured"] is False

    def test_rubric_version_detection(self, tmp_path):
        """Rubric version correctly parses version from principles.json."""
        principles = tmp_path / "src" / "gaia_cli" / "data" / "curation" / "principles.json"
        principles.parent.mkdir(parents=True, exist_ok=True)
        principles.write_text(json.dumps({"version": "4.0.0", "title": "Curation Principles"}), encoding="utf-8")

        res = doctor.check_rubric_version(tmp_path)
        assert res["present"] is True
        assert res["version"] == "4.0.0"

        empty_root = tmp_path / "empty"
        empty_root.mkdir()
        res_missing = doctor.check_rubric_version(empty_root)
        assert res_missing["present"] is False
        assert res_missing["version"] is None

    def test_termux_proof_platform_presence_alone_not_proven(self):
        """Platform presence alone on Android/aarch64 is NOT proven without matching successful smoke receipt."""
        with patch("platform.machine", return_value="aarch64"), \
             patch("platform.system", return_value="Android"), \
             patch("os.path.exists", return_value=True), \
             patch.dict(os.environ, {"TERMUX_VERSION": "0.118.0", "PREFIX": "/data/data/com.termux/files/usr"}):
            res = doctor.check_termux_proof(smoke_info=None)
            assert res["genuine_termux_aarch64"] is True
            assert res["proof_status"] == "provisional", "Platform presence alone must be provisional, not proven!"

            smoke_matching = {"matches_active": True, "actual_android_proof": True}
            res_proven = doctor.check_termux_proof(smoke_info=smoke_matching)
            assert res_proven["proof_status"] == "proven"

    def test_termux_proof_non_termux(self):
        """Generic x86_64 Linux is classified as non-termux."""
        with patch("platform.machine", return_value="x86_64"), \
             patch("platform.system", return_value="Linux"), \
             patch("os.path.exists", return_value=False), \
             patch.dict(os.environ, {}, clear=True):
            res = doctor.check_termux_proof()
            assert res["genuine_termux_aarch64"] is False
            assert res["proof_status"] == "non-termux"

    def test_readiness_deps_vs_artifact_separated(self, tmp_path):
        """Readiness separates dependencies from artifact freshness so setup doesn't reinstall on stale embeddings."""
        mock_src = {"ok": True, "source_matched": True}
        mock_deps = {
            "python": {"version_ok": True},
            "core": {"all_core_ok": True},
            "ml": {"sentence_transformers": {"available": True}},
        }
        mock_retrieval = {"ok": True, "model": "all-MiniLM-L6-v2", "config": {}}
        mock_freshness = {"fresh": False, "present": True}

        with patch("doctor.check_source_import", return_value=mock_src), \
             patch("doctor.check_dependencies", return_value=mock_deps), \
             patch("doctor.check_retrieval", return_value=mock_retrieval), \
             patch("doctor.check_artifact_freshness", return_value=mock_freshness):
            report = doctor.run_doctor(tmp_path)
            assert report["deps_ready"] is True
            assert report["artifact_ready"] is False
            assert report["healthy"] is False
            assert report["readiness"] == {"deps": True, "artifact": False}

    def test_curation_eval_receipt_matching(self, tmp_path):
        """Curation eval receipt verifies matching active config, corpus_sha256, and catalog_sha256."""
        out_dir = tmp_path / "generated-output" / "curation"
        out_dir.mkdir(parents=True, exist_ok=True)
        eval_receipt = out_dir / "eval-receipt.json"

        eval_receipt.write_text(
            json.dumps({
                "corpus_sha256": "expected_corpus_sha",
                "catalog_sha256": "expected_catalog_sha",
                "encoder_contract": ENCODER_CONTRACT,
                "config": {"model": "all-MiniLM-L6-v2"},
            }),
            encoding="utf-8",
        )

        with patch("doctor.hashlib.sha256") as mock_sha:
            mock_hash = MagicMock()
            mock_hash.hexdigest.side_effect = ["expected_corpus_sha", "expected_catalog_sha"]
            mock_sha.return_value = mock_hash

            res = doctor.check_curation_eval_receipt(tmp_path, active_retrieval={"model": "all-MiniLM-L6-v2"})
            assert res["present"] is True
            assert res["matches_active"] is True

    def test_doctor_healthy_requires_both_matching_eval_and_smoke_receipts(self, tmp_path):
        """run_doctor() healthy requires deps_ready, artifact_ready, ret.ok, cur_eval matching, AND smoke matching."""
        cur_dir = tmp_path / "generated-output" / "curation"
        cur_dir.mkdir(parents=True, exist_ok=True)

        mock_src = {"ok": True, "source_matched": True}
        mock_deps = {
            "python": {"version_ok": True},
            "core": {"all_core_ok": True},
            "ml": {
                "sentence_transformers": {"available": True},
                "torch": {"available": True},
                "numpy": {"available": True},
            },
        }
        mock_retrieval = {
            "ok": True,
            "model": "all-MiniLM-L6-v2",
            "revision": "main",
            "backend": "torch",
            "dimensions": 384,
            "config": {"pooling": "mean", "normalize": True, "queryPrefix": None},
        }
        mock_freshness = {"fresh": True, "present": True, "status": {"fingerprint": "fresh-fp-1"}}

        eval_file = cur_dir / "curation-eval.json"
        smoke_file = cur_dir / "termux-smoke.json"

        eval_data_matching = {
            "schema_version": 1,
            "encoder_contract": ENCODER_CONTRACT,
            "status": "completed",
            "corpus_sha256": "c_sha",
            "catalog_sha256": "cat_sha",
            "config": {
                "model": "all-MiniLM-L6-v2",
                "revision": "main",
                "backend": "torch",
                "dimensions": 384,
                "pooling": "mean",
                "normalize": True,
                "queryPrefix": None,
                "threads": 1,
            },
            "metrics": {"top1": 1.0, "mrr": 1.0},
        }

        smoke_data_matching = {
            "status": "success",
            "encoder_contract": ENCODER_CONTRACT,
            "platform": {
                "genuine_termux_aarch64": True,
                "is_android": True,
                "arch": "aarch64",
            },
            "semantic_config": {
                "model": "all-MiniLM-L6-v2",
                "revision": "main",
                "backend": "torch",
                "dimensions": 384,
                "pooling": "mean",
                "normalize": True,
                "query_prefix": None,
                "fingerprint": "fresh-fp-1",
            },
            "metrics": {"repeat_cosine": 1.0},
        }

        with patch("doctor.check_source_import", return_value=mock_src), \
             patch("doctor.check_dependencies", return_value=mock_deps), \
             patch("doctor.check_retrieval", return_value=mock_retrieval), \
             patch("doctor.check_artifact_freshness", return_value=mock_freshness), \
             patch("doctor.hashlib.sha256") as mock_sha:
            mock_hash = MagicMock()
            mock_hash.hexdigest.side_effect = ["c_sha", "cat_sha"] * 20
            mock_sha.return_value = mock_hash

            # 1. Neither receipt exists -> healthy is False
            rep = doctor.run_doctor(tmp_path)
            assert rep["healthy"] is False

            # 2. Only eval receipt exists -> healthy is False
            eval_file.write_text(json.dumps(eval_data_matching), encoding="utf-8")
            rep = doctor.run_doctor(tmp_path)
            assert rep["healthy"] is False

            # 3. Only smoke receipt exists (eval deleted) -> healthy is False
            eval_file.unlink()
            smoke_file.write_text(json.dumps(smoke_data_matching), encoding="utf-8")
            rep = doctor.run_doctor(tmp_path)
            assert rep["healthy"] is False

            # 4. Eval receipt matching + smoke receipt PRE-FIX (missing encoder_contract) -> healthy is False
            eval_file.write_text(json.dumps(eval_data_matching), encoding="utf-8")
            smoke_prefix = dict(smoke_data_matching)
            del smoke_prefix["encoder_contract"]
            smoke_file.write_text(json.dumps(smoke_prefix), encoding="utf-8")
            rep = doctor.run_doctor(tmp_path)
            assert rep["healthy"] is False
            assert rep["smoke_receipt"]["matches_active"] is False

            # 5. Smoke receipt matching + eval receipt PRE-FIX (missing encoder_contract) -> healthy is False
            smoke_file.write_text(json.dumps(smoke_data_matching), encoding="utf-8")
            eval_prefix = dict(eval_data_matching)
            del eval_prefix["encoder_contract"]
            eval_file.write_text(json.dumps(eval_prefix), encoding="utf-8")
            rep = doctor.run_doctor(tmp_path)
            assert rep["healthy"] is False
            assert rep["curation_eval_receipt"]["matches_active"] is False

            # 6. BOTH matching eval receipt AND matching smoke receipt exist -> healthy is True!
            eval_file.write_text(json.dumps(eval_data_matching), encoding="utf-8")
            rep = doctor.run_doctor(tmp_path)
            assert rep["healthy"] is True

    def test_smoke_receipt_matching(self, tmp_path):
        """Smoke receipt verifies matching active model, revision, backend, and Android platform proof."""
        smoke_file = tmp_path / "generated-output" / "curation" / "termux-smoke.json"
        smoke_file.parent.mkdir(parents=True, exist_ok=True)

        smoke_file.write_text(
            json.dumps({
                "status": "success",
                "model": {"declared_name": "all-MiniLM-L6-v2", "revision": "main", "backend": "torch"},
                "platform": {"genuine_termux_aarch64": True, "is_android": True, "arch": "aarch64"},
                "encoder_contract": ENCODER_CONTRACT,
                "metrics": {"repeat_cosine": 1.0},
            }),
            encoding="utf-8",
        )

        active_cfg = {"model": "all-MiniLM-L6-v2", "revision": "main", "backend": "torch"}
        res = doctor.check_smoke_receipt(tmp_path, active_cfg)
        assert res["present"] is True
        assert res["status"] == "success"
        assert res["matches_active"] is True
        assert res["actual_android_proof"] is True

    def test_doctor_smoke_receipt_semantic_config_matching(self, tmp_path):
        """Smoke receipt matches only if full config (pooling, normalize, prefix, fingerprint) matches."""
        smoke_file = tmp_path / "generated-output" / "curation" / "termux-smoke.json"
        smoke_file.parent.mkdir(parents=True, exist_ok=True)

        base_receipt = {
            "status": "success",
            "semantic_config": {
                "model": "all-MiniLM-L6-v2",
                "revision": "main",
                "backend": "torch",
                "pooling": "mean",
                "normalize": True,
                "query_prefix": None,
                "fingerprint": "fresh-fp-1",
            },
            "platform": {"genuine_termux_aarch64": True, "is_android": True, "arch": "aarch64"},
            "encoder_contract": ENCODER_CONTRACT,
            "metrics": {"repeat_cosine": 1.0},
        }
        smoke_file.write_text(json.dumps(base_receipt), encoding="utf-8")

        active_cfg = {
            "model": "all-MiniLM-L6-v2",
            "revision": "main",
            "backend": "torch",
            "config": {"pooling": "mean", "normalize": True, "queryPrefix": None},
        }
        active_fresh = {"status": {"fingerprint": "fresh-fp-1"}}

        # Matching receipt -> matches_active = True, actual_android_proof = True
        res = doctor.check_smoke_receipt(tmp_path, active_cfg, active_freshness=active_fresh)
        assert res["matches_active"] is True
        assert res["actual_android_proof"] is True

        # Mismatched pooling -> matches_active = False, proof fails
        active_cfg_cls = dict(active_cfg, config={"pooling": "cls", "normalize": True, "queryPrefix": None})
        res_pool = doctor.check_smoke_receipt(tmp_path, active_cfg_cls, active_freshness=active_fresh)
        assert res_pool["matches_active"] is False
        assert any("pooling" in m for m in res_pool["mismatches"])

        # Mismatched fingerprint (stale smoke) -> matches_active = False
        active_fresh_stale = {"status": {"fingerprint": "new-fp-2"}}
        res_fp = doctor.check_smoke_receipt(tmp_path, active_cfg, active_freshness=active_fresh_stale)
        assert res_fp["matches_active"] is False
        assert any("fingerprint" in m for m in res_fp["mismatches"])

    def test_doctor_refuses_prefix_curation_eval_receipt(self, tmp_path):
        """Doctor refuses pre-fix curation eval receipts missing or outdated encoder_contract."""
        out_dir = tmp_path / "generated-output" / "curation"
        out_dir.mkdir(parents=True, exist_ok=True)
        eval_receipt = out_dir / "eval-receipt.json"

        # Case 1: Receipt completely missing encoder_contract (pre-fix)
        eval_receipt.write_text(
            json.dumps({
                "corpus_sha256": "expected_c",
                "catalog_sha256": "expected_cat",
                "config": {"model": "all-MiniLM-L6-v2"},
            }),
            encoding="utf-8",
        )
        with patch("doctor.hashlib.sha256") as mock_sha:
            mock_hash = MagicMock()
            mock_hash.hexdigest.side_effect = ["expected_c", "expected_cat"]
            mock_sha.return_value = mock_hash

            res = doctor.check_curation_eval_receipt(tmp_path, active_retrieval={"model": "all-MiniLM-L6-v2"})
            assert res["matches_active"] is False
            assert any("encoder contract mismatch" in m for m in res["mismatches"])

        # Case 2: Receipt with stale / outdated encoder_contract
        eval_receipt.write_text(
            json.dumps({
                "corpus_sha256": "expected_c",
                "catalog_sha256": "expected_cat",
                "encoder_contract": "sentence-transformers-legacy-v0",
                "config": {"model": "all-MiniLM-L6-v2"},
            }),
            encoding="utf-8",
        )
        with patch("doctor.hashlib.sha256") as mock_sha:
            mock_hash = MagicMock()
            mock_hash.hexdigest.side_effect = ["expected_c", "expected_cat"]
            mock_sha.return_value = mock_hash

            res = doctor.check_curation_eval_receipt(tmp_path, active_retrieval={"model": "all-MiniLM-L6-v2"})
            assert res["matches_active"] is False
            assert any("encoder contract mismatch" in m for m in res["mismatches"])

    def test_doctor_refuses_prefix_smoke_receipt_without_repeatability(self, tmp_path):
        """Doctor refuses pre-fix smoke receipts missing repeat_cosine or with repeat_cosine < 0.999999."""
        smoke_file = tmp_path / "generated-output" / "curation" / "termux-smoke.json"
        smoke_file.parent.mkdir(parents=True, exist_ok=True)
        active_cfg = {"model": "all-MiniLM-L6-v2", "revision": "main", "backend": "torch"}

        # Case 1: Receipt without metrics block (pre-fix receipt)
        smoke_file.write_text(
            json.dumps({
                "status": "success",
                "model": {"declared_name": "all-MiniLM-L6-v2", "revision": "main", "backend": "torch"},
                "platform": {"genuine_termux_aarch64": True, "is_android": True, "arch": "aarch64"},
            }),
            encoding="utf-8",
        )
        res_no_metrics = doctor.check_smoke_receipt(tmp_path, active_cfg)
        assert res_no_metrics["matches_active"] is False
        assert any("repeatability proof" in m for m in res_no_metrics["mismatches"])

        # Case 2: Receipt with non-deterministic drift (e.g. repeat_cosine=0.53 from train mode dropout)
        smoke_file.write_text(
            json.dumps({
                "status": "success",
                "model": {"declared_name": "all-MiniLM-L6-v2", "revision": "main", "backend": "torch"},
                "platform": {"genuine_termux_aarch64": True, "is_android": True, "arch": "aarch64"},
                "metrics": {"repeat_cosine": 0.53},
            }),
            encoding="utf-8",
        )
        res_drift = doctor.check_smoke_receipt(tmp_path, active_cfg)
        assert res_drift["matches_active"] is False
        assert any("repeatability proof" in m for m in res_drift["mismatches"])

    def test_doctor_core_modules_includes_pytest(self):
        """doctor core modules must include pytest dev requirement."""
        deps = doctor.check_dependencies()
        assert "pytest" in deps["core"]["modules"]
        assert deps["core"]["modules"]["pytest"]["available"] is True

    def test_doctor_prefers_project_metadata_version_over_stale(self, tmp_path):
        """doctor.check_source_import prefers pyproject.toml version over stale __version__ 0.1.0."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "gaia-cli"\nversion = "8.17.1"\n', encoding="utf-8")
        src = tmp_path / "src" / "gaia_cli"
        src.mkdir(parents=True)
        (src / "__init__.py").write_text('__version__ = "0.1.0"\n', encoding="utf-8")

        res = doctor.check_source_import(tmp_path)
        assert res["version"] == "8.17.1"

    def test_secret_scanner_reports_path_not_line(self, tmp_path):
        """Secret scanner detects patterns and reports file path, NOT line number or content."""
        leak_file = tmp_path / "leak.py"
        key_name = "TYPESAFE_" + "API_KEY"
        key_val = "sk-live-" + "0123456789abcdef0123456789"
        leak_file.write_text(
            f'# Line 1: header\n'
            f'{key_name} = "{key_val}"\n'
            f'# Line 3: footer\n',
            encoding="utf-8",
        )

        violations = doctor.scan_file_for_secrets(leak_file)
        assert len(violations) == 1
        v = violations[0]
        assert v["file"] == str(leak_file)
        assert v["path"] == str(leak_file)
        assert v["pattern"] == "api_key"
        assert v["category"] == "api_key"
        assert v["report"] is True
        assert v["redacted"] is True
        assert "line" not in v
        assert "sk-live" not in json.dumps(v)

    def test_secret_scanner_canary_injected_source_line_never_leaks(self, tmp_path, capsys, monkeypatch):
        """Canary API token injected into source lines is never emitted in reports or stdout/stderr."""
        monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        canary_token = "ghp_" + "CanaryTokenInjectedSourceSecret12345"
        leak_file = tmp_path / "leaky_module.py"
        leak_file.write_text(
            f'# Configuration\nGITHUB_SECRET_TOKEN = "{canary_token}"\nACTIVE = True\n',
            encoding="utf-8",
        )

        findings = doctor.scan_path_rule_findings(leak_file)
        assert len(findings) >= 1
        assert canary_token not in json.dumps(findings)
        assert findings[0]["path"] == str(leak_file)
        assert findings[0]["report"] is True

        is_clean, changed_findings = doctor.scan_changed_tracked_paths(tmp_path, explicit_files=[str(leak_file)])
        assert is_clean is False
        assert canary_token not in json.dumps(changed_findings)

        with patch("sys.argv", ["doctor.py", "--scan-secrets", "--registry", str(tmp_path), "--files", str(leak_file)]):
            exit_code = doctor.main()
            assert exit_code == 1

        out, err = capsys.readouterr()
        assert canary_token not in out
        assert canary_token not in err
        assert "VIOLATION" in out

    def test_canary_injected_token_in_doctor_retrieval_exception_never_leaks(self, tmp_path, monkeypatch):
        """Doctor retrieval config exception never reflects raw exception string or injected secrets."""
        monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
        canary_token = "AIza_CANARY_DOCTOR_RETRIEVAL_TOKEN_12345"

        with patch("gaia_cli.curation.retrieval.loadRetrievalConfig", side_effect=RuntimeError(f"HTTP auth failed key={canary_token}")):
            res = doctor.check_retrieval(tmp_path)
            assert res["ok"] is False
            dumped = json.dumps(res)
            assert canary_token not in dumped
            assert "RETRIEVAL_CONFIG_LOAD_FAILED" in res["error"]


class TestSmoke:
    """Tests for smoke.py."""

    def test_smoke_warmup_calls_prefill_and_no_registry_mutation(self, tmp_path):
        """--warmup executes getSentenceTransformer, direct query, embed_skills, and buildPrefillPacket without registry mutation."""
        registry_dir = tmp_path / "registry"
        registry_dir.mkdir(parents=True, exist_ok=True)

        mock_st = MagicMock()
        mock_instance = MagicMock()
        mock_instance.encode.return_value = [[0.1] * 384, [0.1] * 384]
        mock_st.return_value = mock_instance

        mock_prefill = MagicMock()
        mock_prefill.return_value = {
            "contractVersion": "discovery-packet-v2",
            "candidateId": "smoke/warmup-candidate",
            "mappingOptions": [{"genericId": "code-review", "similarity": 0.85}],
        }

        with patch("doctor.check_retrieval", return_value={"ok": True, "model": "all-MiniLM-L6-v2", "revision": "main", "backend": "torch", "dimensions": 384, "config": {}}), \
             patch("gaia_cli.curation.retrieval.getSentenceTransformer", mock_st), \
             patch("gaia_cli.embeddings.getSentenceTransformer", mock_st), \
             patch("gaia_cli.semantic_search.embed_query", return_value=[0.1] * 384), \
             patch("gaia_cli.prefill.buildPrefillPacket", mock_prefill), \
             patch("gaia_cli.prefill.selfValidatePacket", return_value=[]):
            code = smoke.run_warmup(tmp_path)
            assert code == 0
            assert mock_st.called
            assert mock_prefill.called
            # Ensure buildPrefillPacket was called with precomputedVector=None and candidateId="smoke/warmup-candidate"
            call_kwargs = mock_prefill.call_args[1]
            assert call_kwargs.get("precomputedVector") is None
            assert call_kwargs.get("candidateId") == "smoke/warmup-candidate"
            assert call_kwargs.get("sourceLane") == "source-repository"
            # Ensure real repo registry directory is untouched
            assert list(registry_dir.iterdir()) == []

    def test_smoke_warmup_invalid_packet_means_fail(self, tmp_path):
        """Warmup fails when selfValidatePacket reports validation errors."""
        mock_st = MagicMock()
        mock_instance = MagicMock()
        mock_instance.encode.return_value = [[0.1] * 384, [0.1] * 384]
        mock_st.return_value = mock_instance

        mock_prefill = MagicMock()
        mock_prefill.return_value = {"mappingOptions": [{"genericId": "code-review"}]}

        with patch("doctor.check_retrieval", return_value={"ok": True, "model": "all-MiniLM-L6-v2", "revision": "main", "backend": "torch", "dimensions": 384, "config": {}}), \
             patch("gaia_cli.curation.retrieval.getSentenceTransformer", mock_st), \
             patch("gaia_cli.embeddings.getSentenceTransformer", mock_st), \
             patch("gaia_cli.semantic_search.embed_query", return_value=[0.1] * 384), \
             patch("gaia_cli.prefill.buildPrefillPacket", mock_prefill), \
             patch("gaia_cli.prefill.selfValidatePacket", return_value=["INVALID_CANDIDATE_ID"]):
            code = smoke.run_warmup(tmp_path)
            assert code == 1

    def test_smoke_termux_must_return_nonzero_on_non_android(self, tmp_path):
        """--termux MUST return nonzero on non-Android/non-aarch64 platform."""
        receipt_path = tmp_path / "generated-output" / "curation" / "termux-smoke.json"

        with patch("doctor.check_termux_proof", return_value={"genuine_termux_aarch64": False, "is_android": False, "arch": "x86_64"}):
            code = smoke.run_termux_smoke(tmp_path, output_path=str(receipt_path))
            assert code == 1, "--termux must return nonzero on non-Android/non-aarch64 platform!"
            assert receipt_path.is_file()
            data = json.loads(receipt_path.read_text(encoding="utf-8"))
            assert data["status"] == "unsupported_platform"

    def test_smoke_termux_requires_fresh_embeddings_and_fails_on_stale(self, tmp_path):
        """--termux MUST require embeddingStatus fresh; stale artifact must fail with remediation (no silent fallback)."""
        receipt_path = tmp_path / "termux-receipt.json"

        with patch("doctor.check_termux_proof", return_value={"genuine_termux_aarch64": True, "is_android": True, "arch": "aarch64"}), \
             patch("doctor.check_retrieval", return_value={"ok": True, "model": "all-MiniLM-L6-v2", "revision": "main", "backend": "torch", "dimensions": 384, "config": {}}), \
             patch("importlib.util.find_spec", return_value=MagicMock()), \
             patch("importlib.metadata.version", return_value="2.0.0"), \
             patch("gaia_cli.curation.retrieval.embeddingStatus", return_value={"status": "stale", "reason": "Model mismatch: artifact has BAAI/bge, expected all-MiniLM"}):
            code = smoke.run_termux_smoke(tmp_path, output_path=str(receipt_path))
            assert code == 1, "Termux smoke must fail on stale embeddings!"
            assert receipt_path.is_file()
            data = json.loads(receipt_path.read_text(encoding="utf-8"))
            assert data["status"] == "stale_embeddings"
            assert "remediation" in data["error"].lower() or "gaia dev embed" in data["error"]

    def test_smoke_termux_android_success_with_actual_generics(self, tmp_path):
        """--termux on Android executes with fresh artifact, real prefill without precomputedVector, and records receipt."""
        receipt_path = tmp_path / "termux-receipt.json"

        mock_st = MagicMock()
        mock_packet = {
            "contractVersion": "discovery-packet-v2",
            "candidateId": "smoke/termux",
            "mappingOptions": [
                {"genericId": "code-review", "similarity": 0.88, "matchTier": "strong"}
            ]
        }

        fresh_status = {"status": "fresh", "fingerprint": "fp-12345", "reason": "Artifact is fresh"}
        mock_embs = {"entries": [{"id": "code-review", "vector": [0.1] * 384}], "dimensions": 384, "model": "all-MiniLM-L6-v2", "fingerprint": "fp-12345"}

        with patch("doctor.check_termux_proof", return_value={"genuine_termux_aarch64": True, "is_android": True, "arch": "aarch64"}), \
             patch("doctor.check_retrieval", return_value={"ok": True, "model": "all-MiniLM-L6-v2", "revision": "v1.2", "backend": "torch", "dimensions": 384, "config": {"pooling": "mean", "normalize": True}, "source": "core_api"}), \
             patch("importlib.util.find_spec", return_value=MagicMock()), \
             patch("importlib.metadata.version", return_value="2.0.0"), \
             patch("gaia_cli.curation.retrieval.embeddingStatus", return_value=fresh_status), \
             patch("gaia_cli.semantic_search.load_embeddings", return_value=mock_embs), \
             patch("gaia_cli.curation.retrieval.getSentenceTransformer", return_value=mock_st) as mock_get_st, \
             patch("gaia_cli.semantic_search.embed_query", return_value=[0.05] * 384), \
             patch("gaia_cli.prefill.buildPrefillPacket", return_value=mock_packet) as mock_prefill, \
             patch("gaia_cli.prefill.selfValidatePacket", return_value=[]):
            code = smoke.run_termux_smoke(tmp_path, output_path=str(receipt_path))
            assert code == 0
            assert mock_get_st.called
            mock_get_st.assert_called_with("all-MiniLM-L6-v2", revision="v1.2", backend="torch", pooling="mean")

            # Verify buildPrefillPacket called without precomputedVector and with candidateId smoke/termux
            assert mock_prefill.called
            call_kwargs = mock_prefill.call_args[1]
            assert call_kwargs.get("precomputedVector") is None
            assert call_kwargs.get("candidateId") == "smoke/termux"
            assert call_kwargs.get("sourceLane") == "source-repository"

            assert receipt_path.is_file()
            data = json.loads(receipt_path.read_text(encoding="utf-8"))
            assert data["status"] == "success"
            assert data["metrics"]["direct_vector_dim"] == 384
            assert len(data["metrics"]["actual_mapping_options"]) == 1
            assert data["source"]["recorded_fixture_fetcher"] is True
            assert data["semantic_config"]["fingerprint"] == "fp-12345"
            assert data["semantic_config"]["pooling"] == "mean"
            assert data["semantic_config"]["normalize"] is True

    def test_smoke_termux_invalid_packet_means_fail(self, tmp_path):
        """--termux fails when selfValidatePacket returns errors."""
        receipt_path = tmp_path / "termux-receipt.json"

        mock_st = MagicMock()
        mock_packet = {
            "contractVersion": "discovery-packet-v2",
            "candidateId": "smoke/termux",
            "mappingOptions": [{"genericId": "code-review", "similarity": 0.88}],
        }
        fresh_status = {"status": "fresh", "fingerprint": "fp-12345"}
        mock_embs = {"entries": [{"id": "code-review", "vector": [0.1] * 384}], "dimensions": 384, "model": "all-MiniLM-L6-v2", "fingerprint": "fp-12345"}

        with patch("doctor.check_termux_proof", return_value={"genuine_termux_aarch64": True, "is_android": True, "arch": "aarch64"}), \
             patch("doctor.check_retrieval", return_value={"ok": True, "model": "all-MiniLM-L6-v2", "revision": "v1.2", "backend": "torch", "dimensions": 384, "config": {}}), \
             patch("importlib.util.find_spec", return_value=MagicMock()), \
             patch("importlib.metadata.version", return_value="2.0.0"), \
             patch("gaia_cli.curation.retrieval.embeddingStatus", return_value=fresh_status), \
             patch("gaia_cli.semantic_search.load_embeddings", return_value=mock_embs), \
             patch("gaia_cli.curation.retrieval.getSentenceTransformer", return_value=mock_st), \
             patch("gaia_cli.semantic_search.embed_query", return_value=[0.05] * 384), \
             patch("gaia_cli.prefill.buildPrefillPacket", return_value=mock_packet), \
             patch("gaia_cli.prefill.selfValidatePacket", return_value=["INVALID_GENERIC_SNAPSHOT"]):
            code = smoke.run_termux_smoke(tmp_path, output_path=str(receipt_path))
            assert code == 1
            data = json.loads(receipt_path.read_text(encoding="utf-8"))
            assert data["status"] == "invalid_packet"
            assert "INVALID_GENERIC_SNAPSHOT" in str(data["packet_errors"])

    def test_smoke_termux_candidate_overrides(self, tmp_path):
        """--termux supports --model and --embeddings overrides."""
        receipt_path = tmp_path / "termux-bge-receipt.json"
        custom_emb_file = tmp_path / "custom-bge.json"
        custom_emb_file.write_text("{}", encoding="utf-8")

        mock_st = MagicMock()
        mock_packet = {
            "contractVersion": "discovery-packet-v2",
            "candidateId": "smoke/termux",
            "mappingOptions": [{"genericId": "code-review", "similarity": 0.91}],
        }
        fresh_status = {"status": "fresh", "fingerprint": "bge-fp-999"}
        mock_embs = {"entries": [{"id": "code-review", "vector": [0.1] * 512}], "dimensions": 512, "model": "BAAI/bge-small-en-v1.5", "fingerprint": "bge-fp-999"}

        with patch("doctor.check_termux_proof", return_value={"genuine_termux_aarch64": True, "is_android": True, "arch": "aarch64"}), \
             patch("gaia_cli.curation.retrieval.loadRetrievalConfig", return_value={"modelId": "BAAI/bge-small-en-v1.5", "dimensions": 512, "pooling": "cls", "normalize": True, "queryPrefix": "Represent this sentence for searching relevant passages: "}), \
             patch("importlib.util.find_spec", return_value=MagicMock()), \
             patch("importlib.metadata.version", return_value="2.0.0"), \
             patch("gaia_cli.curation.retrieval.embeddingStatus", return_value=fresh_status), \
             patch("gaia_cli.semantic_search.load_embeddings", return_value=mock_embs), \
             patch("gaia_cli.curation.retrieval.getSentenceTransformer", return_value=mock_st), \
             patch("gaia_cli.semantic_search.embed_query", return_value=[0.05] * 512), \
             patch("gaia_cli.prefill.buildPrefillPacket", return_value=mock_packet), \
             patch("gaia_cli.prefill.selfValidatePacket", return_value=[]):
            code = smoke.run_termux_smoke(
                tmp_path,
                output_path=str(receipt_path),
                model_override="BAAI/bge-small-en-v1.5",
                embeddings_override=str(custom_emb_file),
            )
            assert code == 0
            data = json.loads(receipt_path.read_text(encoding="utf-8"))
            assert data["status"] == "success"
            assert data["semantic_config"]["model"] == "BAAI/bge-small-en-v1.5"
            assert data["semantic_config"]["pooling"] == "cls"
            assert data["semantic_config"]["fingerprint"] == "bge-fp-999"

    def test_smoke_termux_rejects_drift_vectors(self, tmp_path):
        """smoke run_termux_smoke rejects non-deterministic encoders when repeated query drifts."""
        receipt_path = tmp_path / "termux-drift-receipt.json"

        mock_st = MagicMock()
        fresh_status = {"status": "fresh", "fingerprint": "fp-12345", "reason": "Artifact is fresh"}
        mock_embs = {
            "entries": [{"id": "code-review", "vector": [0.1] * 384}],
            "dimensions": 384,
            "model": "all-MiniLM-L6-v2",
            "fingerprint": "fp-12345",
        }

        # Simulate non-deterministic dropout/drift: first query vector is orthogonal to second query vector
        vec_initial = [1.0] + [0.0] * 383
        vec_drifted = [0.0, 1.0] + [0.0] * 382

        with patch("doctor.check_termux_proof", return_value={"genuine_termux_aarch64": True, "is_android": True, "arch": "aarch64"}), \
             patch("doctor.check_retrieval", return_value={"ok": True, "model": "all-MiniLM-L6-v2", "revision": "v1.2", "backend": "torch", "dimensions": 384, "config": {"pooling": "mean", "normalize": True}, "source": "core_api"}), \
             patch("importlib.util.find_spec", return_value=MagicMock()), \
             patch("importlib.metadata.version", return_value="2.0.0"), \
             patch("gaia_cli.curation.retrieval.embeddingStatus", return_value=fresh_status), \
             patch("gaia_cli.semantic_search.load_embeddings", return_value=mock_embs), \
             patch("gaia_cli.curation.retrieval.getSentenceTransformer", return_value=mock_st), \
             patch("gaia_cli.semantic_search.embed_query", side_effect=[vec_initial, vec_drifted]):
            code = smoke.run_termux_smoke(tmp_path, output_path=str(receipt_path))
            assert code == 1, "Termux smoke must exit 1 when identical-query vectors drift"
            assert receipt_path.is_file()
            data = json.loads(receipt_path.read_text(encoding="utf-8"))
            assert data["status"] == "failed"
            assert data["error"] == "NONDETERMINISTIC_ENCODER"
            assert data["repeat_cosine"] < 0.999999
            assert abs(data["repeat_cosine"] - 0.0) < 1e-6

    def test_smoke_sanitizes_errors(self):
        """Diagnostic string errors must sanitize secret tokens."""
        fake_gh = "ghp_" + "123456789012345678901234567890123456"
        fake_sk = "sk-" + "abcdef12345678901234567890"
        raw_error = f"Authentication failed with token: {fake_gh} and key {fake_sk}"
        sanitized = smoke.sanitize_secrets(raw_error)
        assert "ghp_1234567890" not in sanitized
        assert "sk-abcdef" not in sanitized
        assert "[REDACTED" in sanitized

    def test_failure_code_safe_opaque_status(self):
        """failureCode returns safe opaque status codes without reflecting exception message contents."""
        assert smoke.failureCode(None, "DEFAULT_ERR") == "DEFAULT_ERR"
        canary = "sk-live-CANARY-SECRET-KEY-123456789"
        exc = ValueError(f"Secret leakage attempt: {canary}")
        res = smoke.failureCode(exc, "CONFIG_FAILED")
        assert canary not in res
        assert res == "ValueError [CONFIG_FAILED]"
        assert smoke.failure_code(exc, "CONFIG_FAILED") == "ValueError [CONFIG_FAILED]"

    def test_canary_injected_token_in_failing_model_exception_never_leaks(self, tmp_path, capsys, monkeypatch):
        """Canary API token in failing model exception is never emitted in stdout, stderr, or receipts."""
        monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("HF_TOKEN", raising=False)

        canary_token = "sk-live-CANARY_FAILING_MODEL_EXCEPTION_TOKEN_12345"
        failing_exc = RuntimeError(f"Connection failed to endpoint with Authorization: Bearer {canary_token}")

        # 1. Warmup failure
        with patch("doctor.check_retrieval", return_value={"ok": True, "model": "all-MiniLM-L6-v2", "revision": "main", "backend": "torch", "dimensions": 384, "config": {}}), \
             patch("gaia_cli.curation.retrieval.getSentenceTransformer", side_effect=failing_exc):
            code = smoke.run_warmup(tmp_path)
            assert code == 1

        out, err = capsys.readouterr()
        assert canary_token not in out
        assert canary_token not in err
        assert "MODEL_LOAD_FAILED" in err
        assert "RuntimeError" in err

        # 2. Termux smoke failure & receipt
        receipt_path = tmp_path / "termux-receipt.json"
        fresh_status = {"status": "fresh", "fingerprint": "fp-12345"}
        mock_embs = {"entries": [{"id": "code-review", "vector": [0.1] * 384}], "dimensions": 384, "model": "all-MiniLM-L6-v2", "fingerprint": "fp-12345"}

        with patch("doctor.check_termux_proof", return_value={"genuine_termux_aarch64": True, "is_android": True, "arch": "aarch64"}), \
             patch("doctor.check_retrieval", return_value={"ok": True, "model": "all-MiniLM-L6-v2", "revision": "v1.2", "backend": "torch", "dimensions": 384, "config": {}}), \
             patch("importlib.util.find_spec", return_value=MagicMock()), \
             patch("importlib.metadata.version", return_value="2.0.0"), \
             patch("gaia_cli.curation.retrieval.embeddingStatus", return_value=fresh_status), \
             patch("gaia_cli.semantic_search.load_embeddings", return_value=mock_embs), \
             patch("gaia_cli.curation.retrieval.getSentenceTransformer", side_effect=failing_exc):
            code = smoke.run_termux_smoke(tmp_path, output_path=str(receipt_path))
            assert code == 1

        out, err = capsys.readouterr()
        assert canary_token not in out
        assert canary_token not in err
        assert receipt_path.is_file()
        receipt_text = receipt_path.read_text(encoding="utf-8")
        assert canary_token not in receipt_text
        assert "MODEL_LOAD_FAILED" in receipt_text
        assert "RuntimeError" in receipt_text

    def test_canary_injected_token_in_invalid_config_never_leaks(self, tmp_path, capsys, monkeypatch):
        """Canary API token in invalid config exception is never emitted in stdout, stderr, or receipts."""
        monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
        canary_token = "typesafe-CANARY_INVALID_CONFIG_SECRET_TOKEN_67890"
        cfg_exc = ValueError(f"Malformed config: invalid credential key={canary_token} at https://internal.gaia.org")

        # 1. Warmup with model_override
        with patch("gaia_cli.curation.retrieval.loadRetrievalConfig", side_effect=cfg_exc):
            code = smoke.run_warmup(tmp_path, model_override="canary-model")
            assert code == 1

        out, err = capsys.readouterr()
        assert canary_token not in out
        assert canary_token not in err
        assert "RETRIEVAL_CONFIG_LOAD_FAILED" in err

        # 2. Termux smoke with model_override
        receipt_path = tmp_path / "termux-cfg-receipt.json"
        with patch("doctor.check_termux_proof", return_value={"genuine_termux_aarch64": True, "is_android": True, "arch": "aarch64"}), \
             patch("importlib.util.find_spec", return_value=MagicMock()), \
             patch("importlib.metadata.version", return_value="2.0.0"), \
             patch("gaia_cli.curation.retrieval.loadRetrievalConfig", side_effect=cfg_exc):
            code = smoke.run_termux_smoke(tmp_path, output_path=str(receipt_path), model_override="canary-model")
            assert code == 1

        out, err = capsys.readouterr()
        assert canary_token not in out
        assert canary_token not in err
        assert receipt_path.is_file()
        receipt_text = receipt_path.read_text(encoding="utf-8")
        assert canary_token not in receipt_text
        assert "RETRIEVAL_CONFIG_LOAD_FAILED" in receipt_text
        assert "ValueError" in receipt_text


class TestShellScriptsWithStubs:
    """Executable shell stub tests proving calls, arguments, and error aggregation."""

    def test_env_sh_sourcing_and_isolation(self, tmp_path):
        """env.sh centralizes cache dirs, active branch PYTHONPATH, and venv interpreter without global mutation."""
        test_script = tmp_path / "test_env.sh"
        test_script.write_text(
            f'#!/usr/bin/env bash\n'
            f'set -euo pipefail\n'
            f'source "{ENV_DIR}/env.sh"\n'
            f'echo "CACHE=${{GAIA_MODEL_CACHE}}"\n'
            f'echo "HF=${{HF_HOME}}"\n'
            f'echo "PYTHONPATH=${{PYTHONPATH}}"\n'
            f'echo "PY=${{PY}}"\n',
            encoding="utf-8",
        )
        test_script.chmod(0o755)

        proc = subprocess.run(["bash", str(test_script)], capture_output=True, text=True, check=True)
        out = proc.stdout
        assert "CACHE=" in out
        assert "HF=" in out
        assert "src" in out

    def test_setup_sh_skips_reinstall_when_deps_healthy(self, tmp_path):
        """setup.sh skips pip install when doctor --check-deps reports healthy and .venv exists."""
        fake_venv = tmp_path / ".venv"
        fake_venv_bin = fake_venv / "bin"
        fake_venv_bin.mkdir(parents=True)
        fake_py = fake_venv_bin / "python"
        fake_py.write_text("#!/bin/sh\nexit 0\n")
        fake_py.chmod(0o755)
        fake_pip = fake_venv_bin / "pip"
        canary = tmp_path / "pip_was_called.flag"
        fake_pip.write_text(f"#!/bin/sh\ntouch '{canary}'\nexit 0\n")
        fake_pip.chmod(0o755)

        mock_py = tmp_path / "mock_py.sh"
        mock_py.write_text(
            '#!/bin/sh\n'
            'for arg in "$@"; do\n'
            '  if [ "$arg" = "--check-deps" ]; then\n'
            '    exit 0\n'
            '  fi\n'
            'done\n'
            'echo "=== Doctor Report [OK] ==="\n'
            'exit 0\n'
        )
        mock_py.chmod(0o755)

        run_script = tmp_path / "run_setup.sh"
        run_script.write_text(
            f'#!/usr/bin/env bash\n'
            f'set -euo pipefail\n'
            f'export REPO_ROOT="{tmp_path}"\n'
            f'export PY="{mock_py}"\n'
            f'bash "{ENV_DIR}/setup.sh"\n',
            encoding="utf-8",
        )
        run_script.chmod(0o755)

        proc = subprocess.run(["bash", str(run_script)], capture_output=True, text=True)
        assert proc.returncode == 0
        assert "Environment dependencies are already healthy" in proc.stdout
        assert not canary.is_file(), "setup.sh illegally called pip when dependencies were already healthy!"

    def test_maintenance_sh_aggregates_errors_and_calls_real_gaia_cli(self, tmp_path):
        """maintenance.sh executes real python -m gaia_cli, aggregates all errors across steps, and exits with count."""
        log_file = tmp_path / "commands.log"

        test_script = tmp_path / "test_maint.sh"
        test_script.write_text(
            f'#!/usr/bin/env bash\n'
            f'set -euo pipefail\n'
            f'export REPO_ROOT="{tmp_path}"\n'
            f'export PY="{tmp_path}/mock_py.sh"\n'
            f'cat << \'EOF\' > "{tmp_path}/mock_py.sh"\n'
            f'#!/bin/sh\n'
            f'echo "PY_CALL: $*" >> "{log_file}"\n'
            f'# Intentionally fail dev validate to prove error aggregation\n'
            f'if [ "$1" = "-m" ] && [ "$2" = "gaia_cli" ] && [ "$3" = "dev" ] && [ "$4" = "validate" ]; then\n'
            f'  exit 1\n'
            f'fi\n'
            f'exit 0\n'
            f'EOF\n'
            f'chmod +x "{tmp_path}/mock_py.sh"\n'
            f'bash "{ENV_DIR}/maintenance.sh" --offline\n',
            encoding="utf-8",
        )
        test_script.chmod(0o755)

        proc = subprocess.run(["bash", str(test_script)], capture_output=True, text=True)
        assert proc.returncode == 1
        assert "FAILED with 1 error(s)" in proc.stdout or "FAILED with 1 error(s)" in proc.stderr

        commands_logged = log_file.read_text(encoding="utf-8")
        assert "PY_CALL: -m gaia_cli --version" in commands_logged
        assert "PY_CALL: -m gaia_cli steward scan" in commands_logged
        assert "PY_CALL: -m gaia_cli dev validate" in commands_logged
        assert "PY_CALL: -m pytest" in commands_logged
        assert "[OFFLINE] Explicitly skipping network git fetch" in proc.stdout

    def test_maintenance_sh_benchmark_invokes_real_evaluation(self, tmp_path):
        """maintenance.sh --benchmark runs scripts/curation_benchmark.py, NOT smoke warmup."""
        log_file = tmp_path / "benchmark.log"

        test_script = tmp_path / "test_bench.sh"
        test_script.write_text(
            f'#!/usr/bin/env bash\n'
            f'set -euo pipefail\n'
            f'export REPO_ROOT="{tmp_path}"\n'
            f'export PY="{tmp_path}/mock_py.sh"\n'
            f'cat << \'EOF\' > "{tmp_path}/mock_py.sh"\n'
            f'#!/bin/sh\n'
            f'echo "PY_CALL: $*" >> "{log_file}"\n'
            f'exit 0\n'
            f'EOF\n'
            f'chmod +x "{tmp_path}/mock_py.sh"\n'
            f'bash "{ENV_DIR}/maintenance.sh" --offline --benchmark\n',
            encoding="utf-8",
        )
        test_script.chmod(0o755)

        proc = subprocess.run(["bash", str(test_script)], capture_output=True, text=True)
        assert proc.returncode == 0
        commands_logged = log_file.read_text(encoding="utf-8")
        assert "scripts/curation_benchmark.py" in commands_logged
        assert "smoke.py --warmup" not in commands_logged, "maintenance.sh --benchmark must run real evaluation benchmark, not smoke warmup!"

    def test_maintenance_sh_refresh_and_recheck(self, tmp_path):
        """maintenance.sh --refresh generates embeddings and rechecks artifact freshness."""
        log_file = tmp_path / "refresh.log"

        test_script = tmp_path / "test_ref.sh"
        test_script.write_text(
            f'#!/usr/bin/env bash\n'
            f'set -euo pipefail\n'
            f'export REPO_ROOT="{tmp_path}"\n'
            f'export PY="{tmp_path}/mock_py.sh"\n'
            f'cat << \'EOF\' > "{tmp_path}/mock_py.sh"\n'
            f'#!/bin/sh\n'
            f'echo "PY_CALL: $*" >> "{log_file}"\n'
            f'if [ "$2" = "--check-artifact" ]; then\n'
            f'  if [ -f "{tmp_path}/rechecked.flag" ]; then\n'
            f'    exit 0\n'
            f'  else\n'
            f'    touch "{tmp_path}/rechecked.flag"\n'
            f'    exit 1\n'
            f'  fi\n'
            f'fi\n'
            f'exit 0\n'
            f'EOF\n'
            f'chmod +x "{tmp_path}/mock_py.sh"\n'
            f'bash "{ENV_DIR}/maintenance.sh" --offline --refresh\n',
            encoding="utf-8",
        )
        test_script.chmod(0o755)

        proc = subprocess.run(["bash", str(test_script)], capture_output=True, text=True)
        assert proc.returncode == 0
        commands_logged = log_file.read_text(encoding="utf-8")
        assert "generate_embeddings" in commands_logged
        assert "Rechecking artifact freshness after generation" in proc.stdout
        assert "Embeddings successfully regenerated and verified fresh" in proc.stdout

    def test_setup_sh_healthy_avoids_reinstall_and_generation(self, tmp_path):
        """setup.sh skips BOTH pip install AND gaia dev embed when deps are healthy and artifact is fresh."""
        fake_venv = tmp_path / ".venv"
        fake_venv_bin = fake_venv / "bin"
        fake_venv_bin.mkdir(parents=True)
        fake_py = fake_venv_bin / "python"
        fake_py.write_text("#!/bin/sh\nexit 0\n")
        fake_py.chmod(0o755)
        fake_pip = fake_venv_bin / "pip"
        pip_canary = tmp_path / "pip_was_called.flag"
        fake_pip.write_text(f"#!/bin/sh\ntouch '{pip_canary}'\nexit 0\n")
        fake_pip.chmod(0o755)

        embed_log = tmp_path / "embed_called.log"
        mock_py = tmp_path / "mock_py.sh"
        mock_py.write_text(
            f'#!/bin/sh\n'
            f'for arg in "$@"; do\n'
            f'  if [ "$arg" = "--check-deps" ]; then exit 0; fi\n'
            f'  if [ "$arg" = "--check-artifact" ]; then exit 0; fi\n'
            f'  if [ "$arg" = "embed" ]; then echo "EMBED" >> "{embed_log}"; exit 0; fi\n'
            f'done\n'
            f'exit 0\n'
        )
        mock_py.chmod(0o755)

        run_script = tmp_path / "run_setup.sh"
        run_script.write_text(
            f'#!/usr/bin/env bash\n'
            f'set -euo pipefail\n'
            f'export REPO_ROOT="{tmp_path}"\n'
            f'export PY="{mock_py}"\n'
            f'bash "{ENV_DIR}/setup.sh"\n',
            encoding="utf-8",
        )
        run_script.chmod(0o755)

        proc = subprocess.run(["bash", str(run_script)], capture_output=True, text=True)
        assert proc.returncode == 0
        assert "Environment dependencies are already healthy" in proc.stdout
        assert "Embeddings artifact is already fresh. Skipping generation" in proc.stdout
        assert not pip_canary.is_file(), "setup.sh illegally called pip!"
        assert not embed_log.is_file(), "setup.sh illegally called dev embed when embeddings were already fresh!"

    def test_setup_sh_stale_embeddings_triggers_generation_without_pip_reinstall(self, tmp_path):
        """setup.sh skips pip install when deps are healthy, but triggers gaia dev embed when artifact is stale."""
        fake_venv = tmp_path / ".venv"
        fake_venv_bin = fake_venv / "bin"
        fake_venv_bin.mkdir(parents=True)
        fake_py = fake_venv_bin / "python"
        fake_py.write_text("#!/bin/sh\nexit 0\n")
        fake_py.chmod(0o755)
        fake_pip = fake_venv_bin / "pip"
        pip_canary = tmp_path / "pip_was_called.flag"
        fake_pip.write_text(f"#!/bin/sh\ntouch '{pip_canary}'\nexit 0\n")
        fake_pip.chmod(0o755)

        embed_log = tmp_path / "embed_called.log"
        mock_py = tmp_path / "mock_py.sh"
        mock_py.write_text(
            f'#!/bin/sh\n'
            f'for arg in "$@"; do\n'
            f'  if [ "$arg" = "--check-deps" ]; then exit 0; fi\n'
            f'  if [ "$arg" = "--check-artifact" ]; then exit 1; fi\n'
            f'  if [ "$arg" = "embed" ]; then echo "EMBED" >> "{embed_log}"; exit 0; fi\n'
            f'done\n'
            f'exit 0\n'
        )
        mock_py.chmod(0o755)

        run_script = tmp_path / "run_setup.sh"
        run_script.write_text(
            f'#!/usr/bin/env bash\n'
            f'set -euo pipefail\n'
            f'export REPO_ROOT="{tmp_path}"\n'
            f'export PY="{mock_py}"\n'
            f'bash "{ENV_DIR}/setup.sh"\n',
            encoding="utf-8",
        )
        run_script.chmod(0o755)

        proc = subprocess.run(["bash", str(run_script)], capture_output=True, text=True)
        assert proc.returncode == 0
        assert "Environment dependencies are already healthy" in proc.stdout
        assert "generating fresh embeddings via gaia dev embed" in proc.stdout
        assert not pip_canary.is_file(), "setup.sh illegally called pip when dependencies were healthy!"
        assert embed_log.is_file(), "setup.sh failed to call gaia dev embed on stale artifact!"

    def test_setup_sh_benchmark_flag_runs_benchmark(self, tmp_path):
        """setup.sh --benchmark runs curation_benchmark.py."""
        bench_log = tmp_path / "bench.log"
        fake_venv = tmp_path / ".venv"
        fake_venv_bin = fake_venv / "bin"
        fake_venv_bin.mkdir(parents=True)
        fake_py = fake_venv_bin / "python"
        fake_py.write_text("#!/bin/sh\nexit 0\n")
        fake_py.chmod(0o755)

        mock_py = tmp_path / "mock_py.sh"
        mock_py.write_text(
            f'#!/bin/sh\n'
            f'if echo "$*" | grep -q "curation_benchmark.py"; then\n'
            f'  echo "BENCH_CALLED" >> "{bench_log}"\n'
            f'fi\n'
            f'exit 0\n'
        )
        mock_py.chmod(0o755)

        run_script = tmp_path / "run_setup.sh"
        run_script.write_text(
            f'#!/usr/bin/env bash\n'
            f'set -euo pipefail\n'
            f'export REPO_ROOT="{tmp_path}"\n'
            f'export PY="{mock_py}"\n'
            f'bash "{ENV_DIR}/setup.sh" --benchmark\n',
            encoding="utf-8",
        )
        run_script.chmod(0o755)

        proc = subprocess.run(["bash", str(run_script)], capture_output=True, text=True)
        assert proc.returncode == 0
        assert bench_log.is_file()

    def test_doctor_finds_receipt_by_schema_without_filename_substrings(self, tmp_path):
        """doctor must discover evaluation receipts by schema, not requiring filename substrings."""
        cur_dir = tmp_path / "generated-output" / "curation"
        cur_dir.mkdir(parents=True, exist_ok=True)

        # File named without 'eval', 'benchmark', or 'receipt'
        rep_file = cur_dir / "minilm-report.json"
        rep_file.write_text(
            json.dumps({
                "schema_version": 1,
                "encoder_contract": ENCODER_CONTRACT,
                "status": "completed",
                "corpus_sha256": "c_sha",
                "catalog_sha256": "cat_sha",
                "config": {"model": "all-MiniLM-L6-v2", "backend": "torch"},
                "metrics": {"top1": 1.0, "mrr": 1.0},
            }),
            encoding="utf-8",
        )

        # Another file that does NOT match receipt schema
        (cur_dir / "notes.json").write_text(json.dumps({"notes": "some notes"}), encoding="utf-8")

        with patch("doctor.hashlib.sha256") as mock_sha:
            mock_hash = MagicMock()
            mock_hash.hexdigest.side_effect = ["c_sha", "cat_sha"]
            mock_sha.return_value = mock_hash

            res = doctor.check_curation_eval_receipt(tmp_path, active_retrieval={"model": "all-MiniLM-L6-v2"})
            assert res["present"] is True
            assert res["path"] == "generated-output/curation/minilm-report.json"
            assert res["matches_active"] is True

    def test_doctor_receipt_regression_status_against_explicit_baseline(self, tmp_path):
        """doctor reports regression status against explicit baseline only, else unknown."""
        cur_dir = tmp_path / "generated-output" / "curation"
        cur_dir.mkdir(parents=True, exist_ok=True)

        # Baseline: all-MiniLM-L6-v2
        (cur_dir / "minilm-report.json").write_text(
            json.dumps({
                "schema_version": 1,
                "encoder_contract": ENCODER_CONTRACT,
                "status": "completed",
                "corpus_sha256": "c_sha",
                "catalog_sha256": "cat_sha",
                "config": {"model": "all-MiniLM-L6-v2", "backend": "torch"},
                "latencies": {"query_seconds": 1.0},
                "metrics": {"top1": 1.0, "mrr": 1.0},
            }),
            encoding="utf-8",
        )

        # Challenger: BGE
        (cur_dir / "bge-report.json").write_text(
            json.dumps({
                "schema_version": 1,
                "encoder_contract": ENCODER_CONTRACT,
                "status": "completed",
                "corpus_sha256": "c_sha",
                "catalog_sha256": "cat_sha",
                "config": {"model": "BAAI/bge-small-en-v1.5", "backend": "torch"},
                "latencies": {"query_seconds": 2.5},
                "metrics": {"top1": 0.8, "mrr": 0.85},
            }),
            encoding="utf-8",
        )

        with patch("doctor.hashlib.sha256") as mock_sha:
            mock_hash = MagicMock()
            mock_hash.hexdigest.side_effect = ["c_sha", "cat_sha"]
            mock_sha.return_value = mock_hash

            # When evaluating challenger with baseline present:
            res_challenger = doctor.check_curation_eval_receipt(
                tmp_path,
                active_retrieval={"model": "BAAI/bge-small-en-v1.5"},
            )
            assert res_challenger["regression_status"]["baseline_present"] is True
            assert res_challenger["regression_status"]["metrics"] == "regressed"
            assert res_challenger["regression_status"]["time"] == "regressed"

    def test_doctor_eval_baseline_selection_rejects_prefix_receipt(self, tmp_path):
        """eval baseline selection rejects pre-fix receipts missing encoder_contract via _eval_mismatches."""
        cur_dir = tmp_path / "generated-output" / "curation"
        cur_dir.mkdir(parents=True, exist_ok=True)

        # Baseline missing encoder_contract (pre-fix)
        (cur_dir / "minilm-report.json").write_text(
            json.dumps({
                "schema_version": 1,
                "status": "completed",
                "corpus_sha256": "c_sha",
                "catalog_sha256": "cat_sha",
                "config": {"model": "all-MiniLM-L6-v2", "backend": "torch"},
                "latencies": {"query_seconds": 1.0},
                "metrics": {"top1": 1.0, "mrr": 1.0},
            }),
            encoding="utf-8",
        )

        with patch("doctor.hashlib.sha256") as mock_sha:
            mock_hash = MagicMock()
            mock_hash.hexdigest.side_effect = ["c_sha", "cat_sha"] * 5
            mock_sha.return_value = mock_hash

            res = doctor.check_curation_eval_receipt(
                tmp_path,
                active_retrieval={"model": "all-MiniLM-L6-v2"},
            )
            # Pre-fix receipt must NOT be selected as baseline
            assert res["regression_status"]["baseline_present"] is False

    def test_termux_proof_rejects_fake_env_without_android_markers(self):
        """Termux proof must reject fake env markers on non-Android platforms."""
        with patch("platform.machine", return_value="aarch64"), \
             patch("doctor.is_real_android", return_value=False), \
             patch.dict(os.environ, {"TERMUX_VERSION": "0.118.0", "PREFIX": "/data/data/com.termux/files/usr"}):
            res = doctor.check_termux_proof(smoke_info=None)
            assert res["genuine_termux_aarch64"] is False
            assert res["proof_status"] == "non-termux"

    def test_smoke_receipt_rejects_missing_fingerprint_and_config(self, tmp_path):
        """Smoke receipt must report mismatches when required fingerprints or configs are missing."""
        smoke_file = tmp_path / "generated-output" / "curation" / "termux-smoke.json"
        smoke_file.parent.mkdir(parents=True, exist_ok=True)

        # Receipt missing model, backend, and fingerprint
        smoke_file.write_text(
            json.dumps({
                "status": "success",
                "platform": {"genuine_termux_aarch64": True, "is_android": True, "arch": "aarch64"},
            }),
            encoding="utf-8",
        )

        active_cfg = {"model": "all-MiniLM-L6-v2", "backend": "torch"}
        active_fresh = {"status": {"fingerprint": "valid-fp"}}

        res = doctor.check_smoke_receipt(tmp_path, active_cfg, active_freshness=active_fresh)
        assert res["matches_active"] is False
        assert any("missing model" in m for m in res["mismatches"])
        assert any("missing backend" in m for m in res["mismatches"])
        assert any("missing fingerprint" in m for m in res["mismatches"])

    def test_deps_requires_torch_and_numpy_for_torch_backend(self, tmp_path):
        """Doctor deps_ready requires torch and numpy when backend is torch."""
        mock_src = {"ok": True, "source_matched": True}
        mock_retrieval = {"ok": True, "model": "all-MiniLM-L6-v2", "backend": "torch", "config": {}}
        mock_freshness = {"fresh": True, "present": True}

        # Case A: ST available, but torch missing -> deps_ready must be False
        mock_deps_no_torch = {
            "python": {"version_ok": True},
            "core": {"all_core_ok": True},
            "ml": {
                "sentence_transformers": {"available": True},
                "torch": {"available": False},
                "numpy": {"available": True},
            },
        }

        with patch("doctor.check_source_import", return_value=mock_src), \
             patch("doctor.check_dependencies", return_value=mock_deps_no_torch), \
             patch("doctor.check_retrieval", return_value=mock_retrieval), \
             patch("doctor.check_artifact_freshness", return_value=mock_freshness):
            report = doctor.run_doctor(tmp_path)
            assert report["deps_ready"] is False
            assert report["healthy"] is False

    def test_check_artifact_stale_returns_one(self, tmp_path, monkeypatch, capsys):
        """doctor --check-artifact returns 1 and outputs error when artifact is stale."""
        mock_report = {
            "healthy": False,
            "artifact_ready": False,
            "deps_ready": True,
            "artifact_freshness": {
                "fresh": False,
                "status": {"status": "stale", "reason": "Fingerprint mismatch"},
            },
        }
        monkeypatch.setattr("doctor.run_doctor", lambda root: mock_report)
        monkeypatch.setattr("sys.argv", ["doctor.py", "--check-artifact"])

        ret = doctor.main()
        assert ret == 1
        captured = capsys.readouterr()
        assert "Stale or missing embeddings artifact" in captured.err

    def test_maintenance_sh_stale_exits_two_and_summary_needs_refresh(self, tmp_path):
        """maintenance.sh without --refresh increments warnings, outputs NEEDS REFRESH, and exits 2 when artifact is stale."""
        test_script = tmp_path / "test_stale.sh"
        test_script.write_text(
            f'#!/usr/bin/env bash\n'
            f'set -euo pipefail\n'
            f'export REPO_ROOT="{tmp_path}"\n'
            f'export PY="{tmp_path}/mock_py.sh"\n'
            f'cat << \'EOF\' > "{tmp_path}/mock_py.sh"\n'
            f'#!/bin/sh\n'
            f'if [ "$2" = "--check-artifact" ]; then\n'
            f'  exit 1\n'
            f'fi\n'
            f'exit 0\n'
            f'EOF\n'
            f'chmod +x "{tmp_path}/mock_py.sh"\n'
            f'bash "{ENV_DIR}/maintenance.sh" --offline\n',
            encoding="utf-8",
        )
        test_script.chmod(0o755)

        proc = subprocess.run(["bash", str(test_script)], capture_output=True, text=True)
        assert proc.returncode == 2
        assert "Warnings: 1" in proc.stdout
        assert "NEEDS REFRESH" in proc.stdout
        assert "NEEDS REFRESH" in proc.stderr

    def test_setup_sh_pip_install_failure_fails_actionable(self, tmp_path):
        """setup.sh fails actionably (exit 1) without silent fallback when pip install fails."""
        mock_py = tmp_path / "mock_py.sh"
        mock_py.write_text(
            f'#!/bin/sh\n'
            f'if [ "$1" = "{ENV_DIR}/doctor.py" ] && [ "$2" = "--check-deps" ]; then\n'
            f'  exit 1\n'
            f'fi\n'
            f'exit 0\n'
        )
        mock_py.chmod(0o755)

        fake_venv = tmp_path / ".venv"
        fake_venv_bin = fake_venv / "bin"
        fake_venv_bin.mkdir(parents=True)
        fake_py = fake_venv_bin / "python"
        fake_py.write_text("#!/bin/sh\nexit 0\n")
        fake_py.chmod(0o755)
        fake_pip = fake_venv_bin / "pip"
        fake_pip.write_text(
            '#!/bin/sh\n'
            'if echo "$*" | grep -q "dev,embeddings"; then\n'
            '  exit 1\n'
            'fi\n'
            'exit 0\n'
        )
        fake_pip.chmod(0o755)

        run_script = tmp_path / "run_setup_fail.sh"
        run_script.write_text(
            f'#!/usr/bin/env bash\n'
            f'set -euo pipefail\n'
            f'export REPO_ROOT="{tmp_path}"\n'
            f'export PY="{mock_py}"\n'
            f'bash "{ENV_DIR}/setup.sh"\n',
            encoding="utf-8",
        )
        run_script.chmod(0o755)

        proc = subprocess.run(["bash", str(run_script)], capture_output=True, text=True)
        assert proc.returncode == 1
        assert "Failed installing package" in proc.stderr
        assert "falling back" not in proc.stdout, "setup.sh must not silently fall back on pip failure!"

    def test_env_sh_precedence_stale_python3_updated_to_venv(self, tmp_path):
        """env.sh updates PY from stale initial python3 to .venv interpreter once .venv exists."""
        fake_venv = tmp_path / ".venv"
        fake_venv_bin = fake_venv / "bin"
        fake_venv_bin.mkdir(parents=True)
        fake_py = fake_venv_bin / "python"
        fake_py.write_text("#!/bin/sh\nexit 0\n")
        fake_py.chmod(0o755)

        test_script = tmp_path / "test_env_prec.sh"
        test_script.write_text(
            f'#!/usr/bin/env bash\n'
            f'set -euo pipefail\n'
            f'export REPO_ROOT="{tmp_path}"\n'
            f'export PY="python3"\n'
            f'source "{ENV_DIR}/env.sh"\n'
            f'echo "RESOLVED_PY=$PY"\n'
            f'echo "VENV_PY=$VENV_PY"\n',
            encoding="utf-8",
        )
        test_script.chmod(0o755)

        proc = subprocess.run(["bash", str(test_script)], capture_output=True, text=True)
        assert proc.returncode == 0
        assert f"RESOLVED_PY={fake_py}" in proc.stdout
        assert f"VENV_PY={fake_py}" in proc.stdout


