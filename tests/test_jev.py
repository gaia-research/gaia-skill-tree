"""Offline unit tests for shared safe Jev HTTP client (src/gaia_cli/jev.py)."""

from __future__ import annotations

import datetime
from datetime import timezone
import json
import math
import os
from pathlib import Path
import pytest

from gaia_cli.jev import (
    DEFAULT_ENDPOINT,
    DEFAULT_MAX_CALLS,
    DEFAULT_MONTHLY_LIMIT_USD,
    MAX_INPUT_TOKENS,
    MAX_QUESTIONS,
    MAX_REQUEST_BYTES,
    MAX_RESPONSE_BYTES,
    PINNED_MODEL,
    PRICE_PER_INPUT_TOKEN,
    RESERVATION_AMOUNT_USD,
    JevClient,
    _compute_cache_key,
    _current_utc_month,
)


@pytest.fixture
def sample_question():
    return {
        "routing": {
            "type": "choice",
            "instructions": "Which capability category best fits this tool?",
            "criteria": {
                "file_management": "Operations modifying or managing local files",
                "network_request": "Operations sending HTTP/network requests",
                "other": "None of the above categories",
            },
        }
    }


@pytest.fixture
def sample_response_payload():
    return {
        "model": "jev-1.13.0",
        "answers": {
            "routing": {
                "type": "choice",
                "choice": "file_management",
                "confidence": 0.95,
                "probabilities": {
                    "file_management": 0.95,
                    "network_request": 0.04,
                    "other": 0.01,
                },
            }
        },
        "usage": {
            "input_tokens": 400,
            "output_tokens": 30,
        },
    }


# =========================================================================
# 1. Initialization and Parameter Validation
# =========================================================================

def test_init_defaults(tmp_path: Path):
    client = JevClient(tmp_path)
    assert client.state_dir == tmp_path
    assert client.live is False
    assert client.maxCalls == DEFAULT_MAX_CALLS
    assert client.monthlyLimitUsd == DEFAULT_MONTHLY_LIMIT_USD
    assert client.transport is None


def test_init_custom_valid(tmp_path: Path):
    client = JevClient(
        tmp_path,
        live=True,
        maxCalls=5,
        monthlyLimitUsd=0.06,
    )
    assert client.live is True
    assert client.maxCalls == 5
    assert client.monthlyLimitUsd == 0.06


def test_init_invalid_state_dir():
    with pytest.raises(TypeError, match="stateDir must be str or Path"):
        JevClient(12345)  # type: ignore


def test_init_invalid_live(tmp_path: Path):
    with pytest.raises(TypeError, match="live must be boolean"):
        JevClient(tmp_path, live="yes")  # type: ignore


def test_init_invalid_max_calls(tmp_path: Path):
    with pytest.raises(ValueError, match="maxCalls must be an integer between 0 and 20"):
        JevClient(tmp_path, maxCalls=-1)

    with pytest.raises(ValueError, match="maxCalls must be an integer between 0 and 20"):
        JevClient(tmp_path, maxCalls=21)

    with pytest.raises(ValueError, match="maxCalls must be an integer between 0 and 20"):
        JevClient(tmp_path, maxCalls=5.5)  # type: ignore

    with pytest.raises(ValueError, match="maxCalls must be an integer between 0 and 20"):
        JevClient(tmp_path, maxCalls=True)  # type: ignore


def test_init_invalid_monthly_limit(tmp_path: Path):
    with pytest.raises(ValueError, match="monthlyLimitUsd must be a finite number between 0.0 and 5.0"):
        JevClient(tmp_path, monthlyLimitUsd=-0.01)

    with pytest.raises(ValueError, match="monthlyLimitUsd must be a finite number between 0.0 and 5.0"):
        JevClient(tmp_path, monthlyLimitUsd=5.01)

    with pytest.raises(ValueError, match="monthlyLimitUsd must be a finite number between 0.0 and 5.0"):
        JevClient(tmp_path, monthlyLimitUsd=float("inf"))

    with pytest.raises(ValueError, match="monthlyLimitUsd must be a finite number between 0.0 and 5.0"):
        JevClient(tmp_path, monthlyLimitUsd=float("nan"))

    with pytest.raises(ValueError, match="monthlyLimitUsd must be a finite number between 0.0 and 5.0"):
        JevClient(tmp_path, monthlyLimitUsd=True)  # type: ignore


def test_init_invalid_transport(tmp_path: Path):
    with pytest.raises(TypeError, match="transport must be callable or None"):
        JevClient(tmp_path, transport="not-callable")  # type: ignore


# =========================================================================
# 2. Budget Ledger Initialization (initializeBudget)
# =========================================================================

def test_initialize_budget_clean_setup(tmp_path: Path):
    client = JevClient(tmp_path)
    res = client.initializeBudget()

    current_month = _current_utc_month()
    assert res["status"] == "created"
    assert res["month"] == current_month
    assert res["created"] is True
    assert res["reserved_usd"] == 0.0
    assert res["spent_usd"] == 0.0
    assert res["attempts"] == 0
    assert res["successes"] == 0

    budget_file = tmp_path / "budget.json"
    assert budget_file.is_file()
    data = json.loads(budget_file.read_text(encoding="utf-8"))
    assert current_month in data
    assert data[current_month]["reserved_usd"] == 0.0


def test_initialize_budget_idempotent_no_overwrite(tmp_path: Path):
    client = JevClient(tmp_path)
    res1 = client.initializeBudget()
    assert res1["created"] is True

    # Mutate ledger to simulate past usage
    budget_file = tmp_path / "budget.json"
    data = json.loads(budget_file.read_text(encoding="utf-8"))
    current_month = _current_utc_month()
    data[current_month]["reserved_usd"] = 0.015
    data[current_month]["spent_usd"] = 0.002
    data[current_month]["attempts"] = 5
    data[current_month]["successes"] = 4
    budget_file.write_text(json.dumps(data), encoding="utf-8")

    # Second initialize call must NOT reset or overwrite existing values
    res2 = client.initializeBudget()
    assert res2["status"] == "already_exists"
    assert res2["created"] is False
    assert res2["reserved_usd"] == 0.015
    assert res2["spent_usd"] == 0.002
    assert res2["attempts"] == 5

    persisted = json.loads(budget_file.read_text(encoding="utf-8"))
    assert persisted[current_month]["reserved_usd"] == 0.015


def test_initialize_budget_preserves_historical_months(tmp_path: Path):
    budget_file = tmp_path / "budget.json"
    historical = {
        "2025-12": {
            "reserved_usd": 0.05,
            "spent_usd": 0.045,
            "attempts": 10,
            "successes": 9,
        }
    }
    budget_file.write_text(json.dumps(historical), encoding="utf-8")

    client = JevClient(tmp_path)
    res = client.initializeBudget()
    assert res["created"] is True

    persisted = json.loads(budget_file.read_text(encoding="utf-8"))
    assert "2025-12" in persisted
    assert persisted["2025-12"]["reserved_usd"] == 0.05
    assert _current_utc_month() in persisted


def test_initialize_budget_corrupt_ledger_fails_closed(tmp_path: Path):
    budget_file = tmp_path / "budget.json"
    budget_file.write_text("{ corrupt json truncated", encoding="utf-8")

    client = JevClient(tmp_path)
    with pytest.raises(ValueError, match="Existing budget ledger is corrupt"):
        client.initializeBudget()

    # Verify corrupt file was NOT overwritten
    assert budget_file.read_text(encoding="utf-8") == "{ corrupt json truncated"


# =========================================================================
# 3. Dry Run and Missing API Key Fallbacks
# =========================================================================

def test_evaluate_dry_run_fallback(tmp_path: Path, sample_question: dict):
    client = JevClient(tmp_path, live=False)
    state = "Test input state"
    result = client.evaluate(state, sample_question)

    assert result["status"] == "fallback"
    assert result["reason"] == "dry_run"
    assert result["answers"] == {}
    assert result["cached"] is False
    assert result["reservedUsd"] == 0.0
    assert result["estimatedCostUsd"] == 0.0
    assert result["fallback"]["agent"] == "worker-luna"
    assert "dry run mode active" in result["fallback"]["instruction"]


def test_evaluate_missing_api_key_fallback(tmp_path: Path, sample_question: dict, monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    client = JevClient(tmp_path, live=True)
    client.initializeBudget()

    result = client.evaluate("state", sample_question)
    assert result["status"] == "fallback"
    assert result["reason"] == "missing_api_key"
    assert result["reservedUsd"] == 0.0
    assert result["fallback"]["agent"] == "worker-luna"


# =========================================================================
# 4. Budget Gates and Failsafe Behavior
# =========================================================================

def test_evaluate_uninitialized_budget_fails_closed(tmp_path: Path, sample_question: dict, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-mock")
    client = JevClient(tmp_path, live=True)
    # budget.json not initialized

    result = client.evaluate("state", sample_question)
    assert result["status"] == "fallback"
    assert result["reason"] == "budget_uninitialized"
    assert result["reservedUsd"] == 0.0


def test_evaluate_missing_current_month_in_budget_fails_closed(tmp_path: Path, sample_question: dict, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-mock")
    budget_file = tmp_path / "budget.json"
    budget_file.write_text(
        json.dumps({"2020-01": {"reserved_usd": 0.0, "spent_usd": 0.0, "attempts": 0, "successes": 0}}),
        encoding="utf-8",
    )

    client = JevClient(tmp_path, live=True)
    result = client.evaluate("state", sample_question)
    assert result["status"] == "fallback"
    assert result["reason"] == "budget_uninitialized"
    assert result["reservedUsd"] == 0.0


def test_evaluate_corrupt_budget_fails_closed(tmp_path: Path, sample_question: dict, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-mock")
    budget_file = tmp_path / "budget.json"
    budget_file.write_text("bad json data", encoding="utf-8")

    client = JevClient(tmp_path, live=True)
    result = client.evaluate("state", sample_question)
    assert result["status"] == "fallback"
    assert result["reason"] == "budget_corrupt"
    assert result["reservedUsd"] == 0.0


def test_evaluate_monthly_limit_exceeded(tmp_path: Path, sample_question: dict, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-mock")
    client = JevClient(tmp_path, live=True, monthlyLimitUsd=0.005)
    client.initializeBudget()

    # Pre-set reserved_usd to 0.003 with 1 attempt
    budget_file = tmp_path / "budget.json"
    data = json.loads(budget_file.read_text(encoding="utf-8"))
    month_key = _current_utc_month()
    data[month_key]["reserved_usd"] = 0.003
    data[month_key]["attempts"] = 1
    budget_file.write_text(json.dumps(data), encoding="utf-8")

    # Attempting another call would require 0.003 + 0.003 = 0.006 > 0.005 limit
    result = client.evaluate("state", sample_question)
    assert result["status"] == "fallback"
    assert result["reason"] == "budget_exceeded"
    assert result["reservedUsd"] == 0.0

    # Ensure ledger was not incremented
    persisted = json.loads(budget_file.read_text(encoding="utf-8"))
    assert persisted[month_key]["reserved_usd"] == 0.003
    assert persisted[month_key]["attempts"] == 1


def test_evaluate_process_max_calls_exceeded(tmp_path: Path, sample_question: dict, sample_response_payload: dict, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-mock")
    mock_calls = 0

    def mock_transport(url, headers, body, timeout):
        nonlocal mock_calls
        mock_calls += 1
        return 200, json.dumps(sample_response_payload).encode("utf-8")

    client = JevClient(tmp_path, live=True, maxCalls=2, transport=mock_transport)
    client.initializeBudget()

    # Call 1: success
    res1 = client.evaluate("state-1", sample_question)
    assert res1["status"] == "advisory"
    assert res1["reservedUsd"] == RESERVATION_AMOUNT_USD

    # Call 2: success
    res2 = client.evaluate("state-2", sample_question)
    assert res2["status"] == "advisory"
    assert res2["reservedUsd"] == RESERVATION_AMOUNT_USD

    # Call 3: exceeds maxCalls=2
    res3 = client.evaluate("state-3", sample_question)
    assert res3["status"] == "fallback"
    assert res3["reason"] == "max_calls_exceeded"
    assert res3["reservedUsd"] == 0.0
    assert mock_calls == 2


# =========================================================================
# 5. Pre-Call Atomic Reservation (No Refunds on Failure)
# =========================================================================

def test_reservation_no_refund_on_http_error(tmp_path: Path, sample_question: dict, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-mock")

    def failing_transport(url, headers, body, timeout):
        return 500, b"Internal Server Error"

    client = JevClient(tmp_path, live=True, transport=failing_transport)
    client.initializeBudget()

    result = client.evaluate("state", sample_question)
    assert result["status"] == "fallback"
    assert result["reason"] == "http_500"
    assert result["reservedUsd"] == RESERVATION_AMOUNT_USD

    # Verify ledger was debited and NOT refunded
    budget_file = tmp_path / "budget.json"
    persisted = json.loads(budget_file.read_text(encoding="utf-8"))
    month_key = _current_utc_month()
    assert persisted[month_key]["reserved_usd"] == RESERVATION_AMOUNT_USD
    assert persisted[month_key]["attempts"] == 1
    assert persisted[month_key]["successes"] == 0
    assert persisted[month_key]["spent_usd"] == 0.0


def test_reservation_no_refund_on_network_exception(tmp_path: Path, sample_question: dict, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-mock")

    def exception_transport(url, headers, body, timeout):
        raise ConnectionResetError("Connection dropped by peer")

    client = JevClient(tmp_path, live=True, transport=exception_transport)
    client.initializeBudget()

    result = client.evaluate("state", sample_question)
    assert result["status"] == "fallback"
    assert result["reason"] == "network_error"
    assert result["reservedUsd"] == RESERVATION_AMOUNT_USD

    budget_file = tmp_path / "budget.json"
    persisted = json.loads(budget_file.read_text(encoding="utf-8"))
    month_key = _current_utc_month()
    assert persisted[month_key]["reserved_usd"] == RESERVATION_AMOUNT_USD
    assert persisted[month_key]["attempts"] == 1


# =========================================================================
# 6. Live Success, Usage Cost Calculation, and Ledger Update
# =========================================================================

def test_evaluate_success_and_ledger_update(
    tmp_path: Path,
    sample_question: dict,
    sample_response_payload: dict,
    monkeypatch,
):
    monkeypatch.setenv("TYPESAFE_API_KEY", "secret-test-key")
    received_headers = {}

    def mock_transport(url, headers, body, timeout):
        nonlocal received_headers
        received_headers = headers
        assert url == DEFAULT_ENDPOINT
        assert json.loads(body.decode("utf-8"))["model"] == PINNED_MODEL
        return 200, json.dumps(sample_response_payload).encode("utf-8")

    client = JevClient(tmp_path, live=True, transport=mock_transport)
    client.initializeBudget()

    result = client.evaluate("My test tool state", sample_question)

    assert result["status"] == "advisory"
    assert result["reason"] == "ok"
    assert result["model"] == PINNED_MODEL
    assert result["cached"] is False
    assert result["reservedUsd"] == RESERVATION_AMOUNT_USD
    assert result["answers"]["routing"]["choice"] == "file_management"
    assert result["answers"]["routing"]["confidence"] == 0.95
    assert result["fallback"] is None

    # Cost calculation: 400 input tokens * $0.042/1M = 0.0000168 -> rounded to 0.000017
    expected_cost = round(400 * PRICE_PER_INPUT_TOKEN, 6)
    assert result["estimatedCostUsd"] == expected_cost
    assert received_headers["Authorization"] == "Bearer secret-test-key"

    # Verify ledger update
    budget_file = tmp_path / "budget.json"
    persisted = json.loads(budget_file.read_text(encoding="utf-8"))
    month_key = _current_utc_month()
    assert persisted[month_key]["reserved_usd"] == RESERVATION_AMOUNT_USD
    assert persisted[month_key]["spent_usd"] == expected_cost
    assert persisted[month_key]["attempts"] == 1
    assert persisted[month_key]["successes"] == 1


# =========================================================================
# 7. Caching Mechanics
# =========================================================================

def test_evaluate_caching_and_offline_replay(
    tmp_path: Path,
    sample_question: dict,
    sample_response_payload: dict,
    monkeypatch,
):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-mock")
    transport_call_count = 0

    def mock_transport(url, headers, body, timeout):
        nonlocal transport_call_count
        transport_call_count += 1
        return 200, json.dumps(sample_response_payload).encode("utf-8")

    client = JevClient(tmp_path, live=True, transport=mock_transport)
    client.initializeBudget()

    state = {"repo": "test/tool", "action": "read_file"}

    # First call: live network
    res1 = client.evaluate(state, sample_question)
    assert res1["status"] == "advisory"
    assert res1["cached"] is False
    assert transport_call_count == 1

    # Second call with same state & questions: served from cache
    res2 = client.evaluate(state, sample_question)
    assert res2["status"] == "advisory"
    assert res2["cached"] is True
    assert res2["reservedUsd"] == 0.0  # Zero reservation on cache hit
    assert res2["estimatedCostUsd"] == 0.0  # Zero per-run incurred cost for cache hit
    assert res2["cachedOriginal"]["estimatedCostUsd"] == res1["estimatedCostUsd"]
    assert res2["answers"] == res1["answers"]
    assert res2["usage"] == res1["usage"]
    assert transport_call_count == 1  # No extra HTTP call!

    # Offline replay: client with live=False also returns cached advisory
    offline_client = JevClient(tmp_path, live=False)
    res_offline = offline_client.evaluate(state, sample_question)
    assert res_offline["status"] == "advisory"
    assert res_offline["cached"] is True
    assert res_offline["estimatedCostUsd"] == 0.0
    assert res_offline["answers"] == res1["answers"]

    # Verify persisted cache does NOT leak state or prompt texts
    cache_file = tmp_path / "cache.json"
    assert cache_file.is_file()
    cache_data = json.loads(cache_file.read_text(encoding="utf-8"))
    expected_cache_key = _compute_cache_key(state, sample_question)
    assert expected_cache_key in cache_data

    # Raw state string must not appear in cache keys
    for k in cache_data.keys():
        assert len(k) == 64  # SHA-256 hex string


def test_corrupt_cache_fails_safely_as_miss(tmp_path: Path, sample_question: dict):
    client = JevClient(tmp_path, live=False)
    cache_file = tmp_path / "cache.json"
    cache_file.write_text("{ corrupt cache content", encoding="utf-8")

    # Corrupt cache does NOT crash; fails safely to cache miss (dry_run fallback)
    result = client.evaluate("state", sample_question)
    assert result["status"] == "fallback"
    assert result["reason"] == "dry_run"


# =========================================================================
# 8. Request Bounds and Schema Validation
# =========================================================================

def test_request_state_none(tmp_path: Path, sample_question: dict):
    client = JevClient(tmp_path)
    res = client.evaluate(None, sample_question)
    assert res["status"] == "fallback"
    assert res["reason"] == "invalid_request"


def test_request_empty_questions(tmp_path: Path):
    client = JevClient(tmp_path)
    res = client.evaluate("state", {})
    assert res["status"] == "fallback"
    assert res["reason"] == "invalid_request"


def test_request_too_many_questions(tmp_path: Path):
    client = JevClient(tmp_path)
    four_questions = {
        f"q{i}": {
            "type": "choice",
            "instructions": f"Instruction {i}",
            "criteria": {"a": "Option A", "b": "Option B"},
        }
        for i in range(4)
    }
    res = client.evaluate("state", four_questions)
    assert res["status"] == "fallback"
    assert res["reason"] == "invalid_request"


def test_request_invalid_question_type(tmp_path: Path):
    client = JevClient(tmp_path)
    bad_type = {
        "q1": {
            "type": "score",  # Only choice questions allowed per contract
            "instructions": "Rate this",
            "criteria": ["Level 0", "Level 1"],
        }
    }
    res = client.evaluate("state", bad_type)
    assert res["status"] == "fallback"
    assert res["reason"] == "invalid_request"


def test_request_too_large_payload(tmp_path: Path, sample_question: dict):
    client = JevClient(tmp_path)
    huge_state = "A" * (MAX_REQUEST_BYTES + 500)
    res = client.evaluate(huge_state, sample_question)
    assert res["status"] == "fallback"
    assert res["reason"] == "request_too_large"


# =========================================================================
# 9. Response Size and Schema Validation
# =========================================================================

def test_response_too_large(tmp_path: Path, sample_question: dict, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-mock")

    def huge_response_transport(url, headers, body, timeout):
        # Oversized response > 128KB
        return 200, b"X" * (MAX_RESPONSE_BYTES + 10)

    client = JevClient(tmp_path, live=True, transport=huge_response_transport)
    client.initializeBudget()

    res = client.evaluate("state", sample_question)
    assert res["status"] == "fallback"
    assert res["reason"] == "response_too_large"
    assert res["reservedUsd"] == RESERVATION_AMOUNT_USD


def test_response_model_mismatch(tmp_path: Path, sample_question: dict, sample_response_payload: dict, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-mock")
    sample_response_payload["model"] = "jev-preview"  # Must match pinned jev-1.13.0

    def bad_model_transport(url, headers, body, timeout):
        return 200, json.dumps(sample_response_payload).encode("utf-8")

    client = JevClient(tmp_path, live=True, transport=bad_model_transport)
    client.initializeBudget()

    res = client.evaluate("state", sample_question)
    assert res["status"] == "fallback"
    assert res["reason"] == "invalid_response"
    assert res["reservedUsd"] == RESERVATION_AMOUNT_USD


def test_response_choice_not_in_criteria(tmp_path: Path, sample_question: dict, sample_response_payload: dict, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-mock")
    sample_response_payload["answers"]["routing"]["choice"] = "unlisted_option"

    def bad_choice_transport(url, headers, body, timeout):
        return 200, json.dumps(sample_response_payload).encode("utf-8")

    client = JevClient(tmp_path, live=True, transport=bad_choice_transport)
    client.initializeBudget()

    res = client.evaluate("state", sample_question)
    assert res["status"] == "fallback"
    assert res["reason"] == "invalid_response"


def test_response_probabilities_distribution_mismatch(tmp_path: Path, sample_question: dict, sample_response_payload: dict, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-mock")
    # Probabilities don't sum to ~1.0
    sample_response_payload["answers"]["routing"]["probabilities"] = {
        "file_management": 0.2,
        "network_request": 0.2,
        "other": 0.1,
    }

    def bad_prob_transport(url, headers, body, timeout):
        return 200, json.dumps(sample_response_payload).encode("utf-8")

    client = JevClient(tmp_path, live=True, transport=bad_prob_transport)
    client.initializeBudget()

    res = client.evaluate("state", sample_question)
    assert res["status"] == "fallback"
    assert res["reason"] == "invalid_response"


def test_response_confidence_out_of_range(tmp_path: Path, sample_question: dict, sample_response_payload: dict, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-mock")
    sample_response_payload["answers"]["routing"]["confidence"] = 1.5

    def bad_conf_transport(url, headers, body, timeout):
        return 200, json.dumps(sample_response_payload).encode("utf-8")

    client = JevClient(tmp_path, live=True, transport=bad_conf_transport)
    client.initializeBudget()

    res = client.evaluate("state", sample_question)
    assert res["status"] == "fallback"
    assert res["reason"] == "invalid_response"


# =========================================================================
# 10. Credential Security: HTTP Redirect Prohibited
# =========================================================================

def test_redirect_prohibited_no_credential_leak(tmp_path: Path, sample_question: dict, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "super-secret-token")

    def redirect_transport(url, headers, body, timeout):
        return 302, b""

    client = JevClient(tmp_path, live=True, transport=redirect_transport)
    client.initializeBudget()

    res = client.evaluate("state", sample_question)
    assert res["status"] == "fallback"
    assert res["reason"] == "http_redirect_prohibited"
    assert res["reservedUsd"] == RESERVATION_AMOUNT_USD


# =========================================================================
# 11. Timeout Handling
# =========================================================================

def test_timeout_fallback(tmp_path: Path, sample_question: dict, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-mock")

    def timeout_transport(url, headers, body, timeout):
        raise TimeoutError("Socket read timed out")

    client = JevClient(tmp_path, live=True, transport=timeout_transport)
    client.initializeBudget()

    res = client.evaluate("state", sample_question)
    assert res["status"] == "fallback"
    assert res["reason"] == "timeout"
    assert res["reservedUsd"] == RESERVATION_AMOUNT_USD


# =========================================================================
# 12. Rate Limit and Service Overload Handlings
# =========================================================================

def test_rate_limit_429(tmp_path: Path, sample_question: dict, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-mock")

    def rate_limit_transport(url, headers, body, timeout):
        return 429, b'{"error": "Too Many Requests"}'

    client = JevClient(tmp_path, live=True, transport=rate_limit_transport)
    client.initializeBudget()

    res = client.evaluate("state", sample_question)
    assert res["status"] == "fallback"
    assert res["reason"] == "http_429"
    assert res["reservedUsd"] == RESERVATION_AMOUNT_USD


def test_overload_529(tmp_path: Path, sample_question: dict, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-mock")

    def overload_transport(url, headers, body, timeout):
        return 529, b'{"error": "Overloaded"}'

    client = JevClient(tmp_path, live=True, transport=overload_transport)
    client.initializeBudget()

    res = client.evaluate("state", sample_question)
    assert res["status"] == "fallback"
    assert res["reason"] == "http_529"
    assert res["reservedUsd"] == RESERVATION_AMOUNT_USD


# =========================================================================
# 13. Multi-Question and Cost Math
# =========================================================================

def test_evaluate_three_questions_success(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-mock")

    three_questions = {
        "cat": {
            "type": "choice",
            "instructions": "Category?",
            "criteria": {"a": "Cat A", "b": "Cat B"},
        },
        "urgency": {
            "type": "choice",
            "instructions": "Urgency?",
            "criteria": {"low": "Not urgent", "high": "Urgent"},
        },
        "domain": {
            "type": "choice",
            "instructions": "Domain?",
            "criteria": {"cli": "CLI tool", "web": "Web app"},
        },
    }

    payload = {
        "model": "jev-1.13.0",
        "answers": {
            "cat": {
                "type": "choice",
                "choice": "a",
                "confidence": 0.88,
                "probabilities": {"a": 0.88, "b": 0.12},
            },
            "urgency": {
                "type": "choice",
                "choice": "low",
                "confidence": 0.99,
                "probabilities": {"low": 0.99, "high": 0.01},
            },
            "domain": {
                "type": "choice",
                "choice": "cli",
                "confidence": 0.75,
                "probabilities": {"cli": 0.75, "web": 0.25},
            },
        },
        "usage": {
            "input_tokens": 1000,
            "output_tokens": 50,
        },
    }

    def mock_transport(url, headers, body, timeout):
        return 200, json.dumps(payload).encode("utf-8")

    client = JevClient(tmp_path, live=True, transport=mock_transport)
    client.initializeBudget()

    res = client.evaluate("Evaluate this triple question state", three_questions)
    assert res["status"] == "advisory"
    assert len(res["answers"]) == 3
    assert res["answers"]["cat"]["choice"] == "a"
    assert res["answers"]["urgency"]["choice"] == "low"
    assert res["answers"]["domain"]["choice"] == "cli"
    # Cost math: 1000 input tokens * $0.042 / 1,000,000 = $0.000042
    assert res["estimatedCostUsd"] == 0.000042


def test_pricing_math_strict_bounds():
    # Input pricing: $0.042 / 1M tokens
    assert math.isclose(1_000_000 * PRICE_PER_INPUT_TOKEN, 0.042, rel_tol=1e-9)
    # 64,000 max context input tokens = $0.002688
    max_context_cost = MAX_INPUT_TOKENS * PRICE_PER_INPUT_TOKEN
    assert max_context_cost <= RESERVATION_AMOUNT_USD  # $0.003 reservation covers full context


# =========================================================================
# 14. Strict Ledger Validation & initializeBudget Protection
# =========================================================================

def test_evaluate_negative_reserved_fails_closed(tmp_path: Path, sample_question: dict, monkeypatch):
    """Reproducible bug: {reserved_usd: -10, attempts: 0} must fail closed and never call HTTP."""
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-mock")
    http_called = False

    def mock_transport(url, headers, body, timeout):
        nonlocal http_called
        http_called = True
        return 200, b"{}"

    budget_file = tmp_path / "budget.json"
    month_key = _current_utc_month()
    budget_file.write_text(
        json.dumps({month_key: {"reserved_usd": -10, "attempts": 0}}),
        encoding="utf-8",
    )

    client = JevClient(tmp_path, live=True, transport=mock_transport)
    result = client.evaluate("state", sample_question)

    assert result["status"] == "fallback"
    assert result["reason"] == "budget_corrupt"
    assert result["reservedUsd"] == 0.0
    assert http_called is False


def test_evaluate_corrupt_ledger_variants_fail_closed(tmp_path: Path, sample_question: dict, monkeypatch):
    """NaN, empty dict {}, missing fields, or inconsistent counters must fail closed without calling HTTP."""
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-mock")
    http_called = False

    def mock_transport(url, headers, body, timeout):
        nonlocal http_called
        http_called = True
        return 200, b"{}"

    month_key = _current_utc_month()
    budget_file = tmp_path / "budget.json"

    bad_entries = [
        {},  # empty dict entry - cannot be treated as $0
        {"reserved_usd": 0.003, "spent_usd": 0.0, "attempts": 0, "successes": 0},  # reserved > 0 but attempts == 0
        {"reserved_usd": 0.0, "spent_usd": 0.0, "attempts": 1, "successes": 0},    # attempts > 0 but reserved == 0
        {"reserved_usd": 0.003, "spent_usd": 0.005, "attempts": 1, "successes": 1},  # spent > reserved
        {"reserved_usd": 0.003, "spent_usd": 0.0, "attempts": 1, "successes": 2},  # successes > attempts
        {"reserved_usd": 0.003, "spent_usd": 0.001, "attempts": 1, "successes": 0},  # successes == 0 but spent > 0
        {"reserved_usd": 0.003, "spent_usd": 0.0, "attempts": 1.5, "successes": 0},  # non-int attempts
        {"reserved_usd": 0.003, "spent_usd": 0.0, "attempts": True, "successes": 0},  # bool attempts
        {"reserved_usd": "0.003", "spent_usd": 0.0, "attempts": 1, "successes": 0},  # string money
    ]

    for bad_entry in bad_entries:
        http_called = False
        budget_file.write_text(json.dumps({month_key: bad_entry}), encoding="utf-8")
        client = JevClient(tmp_path, live=True, transport=mock_transport)
        result = client.evaluate("state", sample_question)
        assert result["status"] == "fallback", f"Expected fallback for {bad_entry}"
        assert result["reason"] == "budget_corrupt", f"Expected budget_corrupt for {bad_entry}"
        assert result["reservedUsd"] == 0.0
        assert http_called is False


def test_initialize_budget_refuses_corrupt_previous_months(tmp_path: Path):
    """initializeBudget must refuse a ledger if ANY entry (including previous months) is corrupt."""
    budget_file = tmp_path / "budget.json"
    corrupt_data = {
        "2025-10": {
            "reserved_usd": -10,
            "attempts": 0,
        }
    }
    budget_file.write_text(json.dumps(corrupt_data), encoding="utf-8")

    client = JevClient(tmp_path)
    with pytest.raises(ValueError, match="Existing budget ledger is corrupt"):
        client.initializeBudget()

    # Verify corrupt file was untouched
    assert json.loads(budget_file.read_text(encoding="utf-8")) == corrupt_data


# =========================================================================
# 15. Lock Failure, Write Permission Failure, and Non-POSIX Failsafe
# =========================================================================

def test_evaluate_lock_failure_fallback(tmp_path: Path, sample_question: dict, monkeypatch):
    """evaluate must return sanitized fallback when file lock cannot be acquired, without throwing or paying."""
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-mock")
    client = JevClient(tmp_path, live=True)
    client.initializeBudget()

    import gaia_cli.jev as jev_mod

    class BrokenLock:
        def __init__(self, path):
            pass

        def __enter__(self):
            raise PermissionError("Permission denied: lock file")

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr(jev_mod, "_FileLock", BrokenLock)

    result = client.evaluate("state", sample_question)
    assert result["status"] == "fallback"
    assert result["reason"] == "lock_failed"
    assert result["reservedUsd"] == 0.0
    assert result["fallback"]["agent"] == "worker-luna"


def test_evaluate_write_failure_fallback(tmp_path: Path, sample_question: dict, monkeypatch):
    """evaluate must return sanitized fallback when budget ledger write fails, without throwing or paying."""
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-mock")
    http_called = False

    def mock_transport(url, headers, body, timeout):
        nonlocal http_called
        http_called = True
        return 200, b"{}"

    client = JevClient(tmp_path, live=True, transport=mock_transport)
    client.initializeBudget()

    import gaia_cli.jev as jev_mod

    def failing_atomic_write(path, data):
        raise PermissionError("Disk is read-only")

    monkeypatch.setattr(jev_mod, "_atomic_write_json", failing_atomic_write)

    result = client.evaluate("state", sample_question)
    assert result["status"] == "fallback"
    assert result["reason"] == "budget_write_failed"
    assert result["reservedUsd"] == 0.0
    assert http_called is False


def test_non_posix_lock_unavailable_fails_closed(tmp_path: Path, sample_question: dict, monkeypatch):
    """When exclusive locking is unavailable (fcntl=None, msvcrt=None), client fails closed on live without paying."""
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-mock")
    import gaia_cli.jev as jev_mod

    monkeypatch.setattr(jev_mod, "fcntl", None)
    monkeypatch.setattr(jev_mod, "msvcrt", None)

    client = JevClient(tmp_path, live=True)
    # Trying to initialize budget without locking raises RuntimeError
    with pytest.raises(RuntimeError, match="Exclusive file locking is unavailable"):
        client.initializeBudget()

    # evaluate on live mode fails closed to fallback without throwing or calling HTTP
    res = client.evaluate("state", sample_question)
    assert res["status"] == "fallback"
    assert res["reason"] == "lock_failed"
    assert res["reservedUsd"] == 0.0


# =========================================================================
# 16. Single Explicit 4-Arg Transport Protocol (No Retries on Error)
# =========================================================================

def test_transport_called_exactly_once_on_error(tmp_path: Path, sample_question: dict, monkeypatch):
    """Transport must be called exactly once; TypeError inside transport must NOT issue a second request."""
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-mock")
    calls = 0

    def bug_transport(url, headers, body, timeout):
        nonlocal calls
        calls += 1
        raise TypeError("Bug inside transport function")

    client = JevClient(tmp_path, live=True, transport=bug_transport)
    client.initializeBudget()

    result = client.evaluate("state", sample_question)
    assert result["status"] == "fallback"
    assert result["reason"] == "transport_error"
    assert calls == 1  # Exactly ONE call, no catch-and-call-again retry!


def test_transport_invalid_return_type_fails_closed(tmp_path: Path, sample_question: dict, monkeypatch):
    """Transport returning something other than a 2-tuple fails closed without retry."""
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-mock")
    calls = 0

    def bad_transport(url, headers, body, timeout):
        nonlocal calls
        calls += 1
        return "not-a-tuple"

    client = JevClient(tmp_path, live=True, transport=bad_transport)
    client.initializeBudget()

    result = client.evaluate("state", sample_question)
    assert result["status"] == "fallback"
    assert result["reason"] == "transport_error"
    assert calls == 1


# =========================================================================
# 17. Response Validation: Choice str Check, Token Cap, and Argmax
# =========================================================================

def test_validate_response_choice_str_check(tmp_path: Path, sample_question: dict, sample_response_payload: dict, monkeypatch):
    """Malformed choice as a dict/list must not crash with TypeError (unhashable type)."""
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-mock")
    sample_response_payload["answers"]["routing"]["choice"] = {"nested": "dict"}

    def mock_transport(url, headers, body, timeout):
        return 200, json.dumps(sample_response_payload).encode("utf-8")

    client = JevClient(tmp_path, live=True, transport=mock_transport)
    client.initializeBudget()

    res = client.evaluate("state", sample_question)
    assert res["status"] == "fallback"
    assert res["reason"] == "invalid_response"


def test_validate_response_input_tokens_cap(tmp_path: Path, sample_question: dict, sample_response_payload: dict, monkeypatch):
    """Response usage with input_tokens > 64,000 must be rejected."""
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-mock")
    sample_response_payload["usage"]["input_tokens"] = 64001

    def mock_transport(url, headers, body, timeout):
        return 200, json.dumps(sample_response_payload).encode("utf-8")

    client = JevClient(tmp_path, live=True, transport=mock_transport)
    client.initializeBudget()

    res = client.evaluate("state", sample_question)
    assert res["status"] == "fallback"
    assert res["reason"] == "invalid_response"


def test_validate_response_choice_not_argmax(tmp_path: Path, sample_question: dict, sample_response_payload: dict, monkeypatch):
    """Choice must be the argmax of probabilities; inconsistent choice must be rejected."""
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-mock")
    # file_management has 0.1, network_request has 0.89, but choice is set to file_management
    sample_response_payload["answers"]["routing"]["choice"] = "file_management"
    sample_response_payload["answers"]["routing"]["probabilities"] = {
        "file_management": 0.10,
        "network_request": 0.89,
        "other": 0.01,
    }

    def mock_transport(url, headers, body, timeout):
        return 200, json.dumps(sample_response_payload).encode("utf-8")

    client = JevClient(tmp_path, live=True, transport=mock_transport)
    client.initializeBudget()

    res = client.evaluate("state", sample_question)
    assert res["status"] == "fallback"
    assert res["reason"] == "invalid_response"


# =========================================================================
# 18. JSON Serialization Rejects NaN & Stable Error Details
# =========================================================================

def test_json_rejects_nan_in_request(tmp_path: Path, sample_question: dict):
    """JSON serialization in request validation must reject NaN."""
    client = JevClient(tmp_path)
    state_with_nan = {"metric": float("nan")}
    res = client.evaluate(state_with_nan, sample_question)
    assert res["status"] == "fallback"
    assert res["reason"] == "invalid_request"


def test_network_exception_details_not_echoed(tmp_path: Path, sample_question: dict, monkeypatch):
    """Network/API exception details must not echo arbitrary server or socket strings."""
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-mock")
    sensitive_info = "Connection to 10.0.0.1:8080 with token XYZ123 failed"

    def leaking_transport(url, headers, body, timeout):
        raise OSError(sensitive_info)

    client = JevClient(tmp_path, live=True, transport=leaking_transport)
    client.initializeBudget()

    result = client.evaluate("state", sample_question)
    assert result["status"] == "fallback"
    assert result["reason"] == "network_error"
    assert sensitive_info not in result["fallback"]["instruction"]
    assert "network communication failed" in result["fallback"]["instruction"]


# =========================================================================
# 19. Cache Hit Reports Incurred estimatedCostUsd as 0
# =========================================================================

def test_cache_hit_reports_zero_incurred_cost(tmp_path: Path, sample_question: dict, sample_response_payload: dict, monkeypatch):
    """Cache hits must report per-run incurred estimatedCostUsd 0.0 and preserve cachedOriginal."""
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-mock")

    def mock_transport(url, headers, body, timeout):
        return 200, json.dumps(sample_response_payload).encode("utf-8")

    client = JevClient(tmp_path, live=True, transport=mock_transport)
    client.initializeBudget()

    # Call 1: Live call incurs cost
    res1 = client.evaluate("state-cache-cost", sample_question)
    assert res1["status"] == "advisory"
    assert res1["cached"] is False
    assert res1["estimatedCostUsd"] > 0.0
    assert res1["cachedOriginal"] is None

    # Call 2: Cache hit incurs 0.0 cost for this run
    res2 = client.evaluate("state-cache-cost", sample_question)
    assert res2["status"] == "advisory"
    assert res2["cached"] is True
    assert res2["estimatedCostUsd"] == 0.0
    assert res2["cachedOriginal"] is not None
    assert res2["cachedOriginal"]["estimatedCostUsd"] == res1["estimatedCostUsd"]
