"""Shared safe Jev HTTP client implementation for TypeSafe System One evaluation.

Pinned to model `jev-1.13.0` with conservative budget reservation, atomic local
ledgers, offline-safe operations, and strict validation.
"""

from __future__ import annotations

import datetime
from datetime import timezone
import hashlib
import http.client
import json
import math
import os
from pathlib import Path
import ssl
import time
import urllib.parse
from typing import Any, Callable, Dict, Optional, Tuple, Union

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None

try:
    import msvcrt
except ImportError:  # pragma: no cover
    msvcrt = None


# Contract constants
PINNED_MODEL = "jev-1.13.0"
DEFAULT_ENDPOINT = "https://api.typesafe.ai/v1/systemone"

PRICE_PER_INPUT_TOKEN = 0.042 / 1_000_000  # $0.000000042 per input token
RESERVATION_AMOUNT_USD = 0.003             # Conservative per-attempt envelope

DEFAULT_MONTHLY_LIMIT_USD = 0.5
MAX_MONTHLY_LIMIT_USD = 5.0
DEFAULT_MAX_CALLS = 20
MAX_ALLOWED_CALLS = 20

MAX_REQUEST_BYTES = 12000
MAX_RESPONSE_BYTES = 128 * 1024            # 131,072 bytes
MAX_QUESTIONS = 3
MAX_INPUT_TOKENS = 64000
DEFAULT_TIMEOUT_SECONDS = 10.0

MAX_BUDGET_FILE_BYTES = 1_000_000          # 1 MB bounded read
MAX_CACHE_FILE_BYTES = 5_000_000           # 5 MB bounded read

REQUIRED_BUDGET_KEYS = ("reserved_usd", "spent_usd", "attempts", "successes")


def _current_utc_month() -> str:
    """Return current UTC month string in YYYY-MM format."""
    return datetime.datetime.now(timezone.utc).strftime("%Y-%m")


def _isValidMonthKey(monthKey: Any) -> bool:
    """Return True if monthKey is a valid 'YYYY-MM' string."""
    if not isinstance(monthKey, str) or len(monthKey) != 7:
        return False
    parts = monthKey.split("-")
    if len(parts) != 2:
        return False
    yearPart, monthPart = parts
    if not (yearPart.isdigit() and len(yearPart) == 4 and monthPart.isdigit() and len(monthPart) == 2):
        return False
    monthVal = int(monthPart)
    return 1 <= monthVal <= 12


def _validateBudgetEntry(entry: Any) -> Tuple[bool, Optional[str]]:
    """Validate a single month entry in the budget ledger strictly."""
    if not isinstance(entry, dict):
        return False, "budget entry must be a dictionary"
    if set(entry.keys()) != set(REQUIRED_BUDGET_KEYS):
        return False, f"budget entry keys must match required keys: {REQUIRED_BUDGET_KEYS}"

    reservedUsd = entry["reserved_usd"]
    spentUsd = entry["spent_usd"]
    attempts = entry["attempts"]
    successes = entry["successes"]

    # Finite nonnegative money
    if type(reservedUsd) not in (int, float) or isinstance(reservedUsd, bool):
        return False, "reserved_usd must be a number"
    if type(spentUsd) not in (int, float) or isinstance(spentUsd, bool):
        return False, "spent_usd must be a number"
    reservedUsdFloat = float(reservedUsd)
    spentUsdFloat = float(spentUsd)
    if not math.isfinite(reservedUsdFloat) or not math.isfinite(spentUsdFloat):
        return False, "reserved_usd and spent_usd must be finite numbers"
    if reservedUsdFloat < 0.0 or spentUsdFloat < 0.0:
        return False, "reserved_usd and spent_usd must be non-negative"

    # Exact nonnegative integer counters
    if type(attempts) is not int or isinstance(attempts, bool):
        return False, "attempts must be an exact integer"
    if type(successes) is not int or isinstance(successes, bool):
        return False, "successes must be an exact integer"
    if attempts < 0 or successes < 0:
        return False, "attempts and successes must be non-negative integers"

    # successes <= attempts
    if successes > attempts:
        return False, f"successes ({successes}) cannot exceed attempts ({attempts})"

    # Reserved amounts consistent with attempts
    if attempts == 0:
        if reservedUsdFloat != 0.0:
            return False, f"reserved_usd ({reservedUsdFloat}) must be 0.0 when attempts is 0"
        if spentUsdFloat != 0.0:
            return False, f"spent_usd ({spentUsdFloat}) must be 0.0 when attempts is 0"
    else:
        if reservedUsdFloat <= 0.0:
            return False, "reserved_usd must be positive when attempts > 0"
        if spentUsdFloat > reservedUsdFloat + 1e-9:
            return False, f"spent_usd ({spentUsdFloat}) cannot exceed reserved_usd ({reservedUsdFloat})"

    if successes == 0 and spentUsdFloat != 0.0:
        return False, f"spent_usd ({spentUsdFloat}) must be 0.0 when successes is 0"

    return True, None


def _validateBudgetLedger(data: Any) -> Tuple[bool, Optional[str]]:
    """Validate all entries in the budget ledger dictionary."""
    if not isinstance(data, dict):
        return False, "budget ledger must be a dictionary"
    for mKey, entry in data.items():
        if not _isValidMonthKey(mKey):
            return False, f"invalid month key '{mKey}' in budget ledger"
        validEntry, errMsg = _validateBudgetEntry(entry)
        if not validEntry:
            return False, f"invalid entry for month '{mKey}': {errMsg}"
    return True, None


class _FileLock:
    """Context manager for local interprocess locking via fcntl or msvcrt."""

    def __init__(self, lock_path: Path):
        self.lock_path = lock_path
        self._file = None

    def __enter__(self):
        if fcntl is None and msvcrt is None:
            raise RuntimeError(
                "Exclusive file locking is unavailable on this platform; refusing to run without concurrency protection"
            )
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(self.lock_path, "a+", encoding="utf-8")
        if fcntl is not None:
            fcntl.flock(self._file.fileno(), fcntl.LOCK_EX)
        elif msvcrt is not None:
            self._file.seek(0)
            msvcrt.locking(self._file.fileno(), msvcrt.LK_LOCK, 1)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._file is not None:
            try:
                if fcntl is not None:
                    fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
                elif msvcrt is not None:
                    self._file.seek(0)
                    msvcrt.locking(self._file.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
            finally:
                self._file.close()
                self._file = None


def _atomic_write_json(path: Path, data: Any) -> None:
    """Atomically write JSON data to path using a sibling temporary file and fsync."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.tmp.{os.getpid()}.{time.time_ns()}")
    try:
        content = json.dumps(data, indent=2, sort_keys=True, allow_nan=False)
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, path)
    except Exception:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        raise


def _read_bounded_json(path: Path, max_bytes: int) -> Any:
    """Read a JSON file with strict size bounds. Fail closed if oversized or corrupt."""
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    size = path.stat().st_size
    if size > max_bytes:
        raise ValueError(f"File size {size} exceeds maximum {max_bytes} bytes: {path}")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read(max_bytes + 1)
        if len(content) > max_bytes:
            raise ValueError(f"File content exceeds {max_bytes} bytes: {path}")
        return json.loads(content)


def _compute_cache_key(state: Any, questions: dict) -> str:
    """Compute deterministic SHA-256 hash across contract, model, state, and questions."""
    payload = {
        "contract": "jev-v1",
        "model": PINNED_MODEL,
        "questions": questions,
        "state": state,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _validate_request(state: Any, questions: Any) -> Tuple[bool, Optional[str], Optional[bytes]]:
    """Validate request constraints: non-None state, 1..3 Choice questions, <=12000 UTF-8 bytes."""
    if state is None:
        return False, "state must not be None", None

    if not isinstance(questions, dict):
        return False, "questions must be a dictionary", None

    if len(questions) == 0 or len(questions) > MAX_QUESTIONS:
        return False, f"questions count must be between 1 and {MAX_QUESTIONS}", None

    for qid, q in questions.items():
        if not isinstance(qid, str) or not qid.strip():
            return False, "question id must be a non-empty string", None
        if not isinstance(q, dict):
            return False, f"question '{qid}' must be a dictionary", None
        if q.get("type") != "choice":
            return False, f"question '{qid}' type must be 'choice'", None

        instructions = q.get("instructions")
        if instructions is None:
            return False, f"question '{qid}' missing instructions", None
        if not isinstance(instructions, (str, dict, list)):
            return False, f"question '{qid}' instructions must be string, dict, or list", None
        if isinstance(instructions, (str, dict, list)) and len(instructions) == 0:
            return False, f"question '{qid}' instructions must not be empty", None

        criteria = q.get("criteria")
        if not isinstance(criteria, dict) or len(criteria) == 0 or len(criteria) > 255:
            return False, f"question '{qid}' criteria must be a dict with 1 to 255 options", None

        for opt_key, opt_desc in criteria.items():
            if not isinstance(opt_key, str) or not opt_key.strip():
                return False, f"question '{qid}' criteria option key must be non-empty string", None
            if opt_desc is not None and not isinstance(opt_desc, (str, dict, list)):
                return False, f"question '{qid}' criteria description must be string, dict, list, or None", None

    payload = {
        "model": PINNED_MODEL,
        "state": state,
        "questions": questions,
    }
    try:
        body_bytes = json.dumps(payload, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as e:
        return False, "request payload cannot be serialized to JSON", None

    if len(body_bytes) > MAX_REQUEST_BYTES:
        return False, f"request size {len(body_bytes)} bytes exceeds limit of {MAX_REQUEST_BYTES} bytes", None

    return True, None, body_bytes


def _validate_response(
    resp_obj: Any,
    questions: dict,
) -> Tuple[Optional[dict], Optional[dict], Optional[str]]:
    """Validate API response against pinned model, schema, enums, distributions, finite ranges, and usage."""
    if not isinstance(resp_obj, dict):
        return None, None, "Response must be a JSON object"

    # Pinned model validation
    model = resp_obj.get("model")
    if model != PINNED_MODEL:
        return None, None, f"Response model '{model}' does not match pinned model '{PINNED_MODEL}'"

    # Usage validation
    usage = resp_obj.get("usage")
    if not isinstance(usage, dict):
        return None, None, "Response usage must be an object"
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    if type(input_tokens) is not int or type(output_tokens) is not int:
        return None, None, "Response usage token counts must be integers"
    if isinstance(input_tokens, bool) or isinstance(output_tokens, bool):
        return None, None, "Response usage token counts must be integers"
    if input_tokens < 0 or output_tokens < 0:
        return None, None, "Response usage token counts must be non-negative"
    if input_tokens > MAX_INPUT_TOKENS:
        return None, None, f"Response usage input_tokens {input_tokens} exceeds documented limit of {MAX_INPUT_TOKENS}"

    validated_usage = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }

    # Answers validation
    raw_answers = resp_obj.get("answers")
    if not isinstance(raw_answers, dict):
        return None, None, "Response answers must be an object"

    validated_answers = {}
    for qid, qdata in questions.items():
        if qid not in raw_answers:
            return None, None, f"Missing answer for question '{qid}'"
        ans = raw_answers[qid]
        if not isinstance(ans, dict):
            return None, None, f"Answer for '{qid}' must be an object"
        if ans.get("type") != "choice":
            return None, None, f"Answer for '{qid}' type must be 'choice'"

        criteria_options = set(qdata["criteria"].keys())
        choice = ans.get("choice")
        if not isinstance(choice, str) or not choice.strip():
            return None, None, f"Choice for '{qid}' must be a non-empty string"
        if choice not in criteria_options:
            return None, None, f"Choice '{choice}' for '{qid}' is not in criteria options"

        confidence = ans.get("confidence")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
            return None, None, f"Confidence for '{qid}' must be a float"
        confidence_float = float(confidence)
        if not math.isfinite(confidence_float) or not (0.0 <= confidence_float <= 1.0):
            return None, None, f"Confidence for '{qid}' must be a finite float in [0.0, 1.0]"

        probs = ans.get("probabilities")
        if not isinstance(probs, dict):
            return None, None, f"Probabilities for '{qid}' must be an object"
        if set(probs.keys()) != criteria_options:
            return None, None, f"Probabilities keys for '{qid}' do not match criteria options"

        prob_sum = 0.0
        validated_probs = {}
        for opt, p_val in probs.items():
            if not isinstance(p_val, (int, float)) or isinstance(p_val, bool):
                return None, None, f"Probability for '{qid}:{opt}' must be a float"
            p_float = float(p_val)
            if not math.isfinite(p_float) or not (0.0 <= p_float <= 1.0):
                return None, None, f"Probability for '{qid}:{opt}' must be in [0.0, 1.0]"
            validated_probs[opt] = p_float
            prob_sum += p_float

        if abs(prob_sum - 1.0) > 0.02:
            return None, None, f"Probabilities for '{qid}' must sum to ~1.0, got {prob_sum}"

        # Ensure choice is argmax of probabilities
        max_prob = max(validated_probs.values())
        if validated_probs[choice] < max_prob - 1e-6:
            return None, None, f"Choice '{choice}' for '{qid}' does not have the maximum probability"

        validated_answers[qid] = {
            "type": "choice",
            "choice": choice,
            "confidence": confidence_float,
            "probabilities": validated_probs,
        }

    return validated_answers, validated_usage, None


def _default_transport(url: str, headers: dict[str, str], body: bytes, timeout: float) -> Tuple[int, bytes]:
    """Default HTTPS transport using http.client. Direct connection; never follows redirects."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("Only https URLs are permitted")

    port = parsed.port or 443
    context = ssl.create_default_context()
    conn = http.client.HTTPSConnection(parsed.hostname, port, context=context, timeout=timeout)
    try:
        path = parsed.path
        if parsed.query:
            path += f"?{parsed.query}"
        conn.request("POST", path, body=body, headers=headers)
        resp = conn.getresponse()
        status = resp.status
        if 300 <= status < 400:
            # Prevent credential leakage: NEVER follow redirects
            return status, b""
        resp_body = resp.read(MAX_RESPONSE_BYTES + 1)
        return status, resp_body
    finally:
        conn.close()


def _fallback_result(
    reason: str,
    instruction: str,
    reserved_usd: float = 0.0,
) -> dict:
    """Build standardized fallback response packet with worker-luna handoff."""
    return {
        "status": "fallback",
        "reason": reason,
        "answers": {},
        "model": PINNED_MODEL,
        "cached": False,
        "usage": {},
        "estimatedCostUsd": 0.0,
        "cachedOriginal": None,
        "reservedUsd": reserved_usd,
        "fallback": {
            "agent": "worker-luna",
            "instruction": instruction,
        },
    }


class JevClient:
    """Safe, bounded HTTP client for TypeSafe Jev System One evaluation."""

    def __init__(
        self,
        stateDir: Union[str, Path],
        *,
        live: bool = False,
        maxCalls: int = DEFAULT_MAX_CALLS,
        monthlyLimitUsd: float = DEFAULT_MONTHLY_LIMIT_USD,
        transport: Optional[Any] = None,
    ):
        if not isinstance(stateDir, (str, Path)):
            raise TypeError(f"stateDir must be str or Path, got {type(stateDir).__name__}")
        self.state_dir = Path(stateDir)

        if not isinstance(live, bool):
            raise TypeError(f"live must be boolean, got {type(live).__name__}")
        self.live = live

        if type(maxCalls) is not int or not (0 <= maxCalls <= MAX_ALLOWED_CALLS):
            raise ValueError(f"maxCalls must be an integer between 0 and {MAX_ALLOWED_CALLS}, got {maxCalls!r}")
        self.maxCalls = maxCalls

        if isinstance(monthlyLimitUsd, bool) or not isinstance(monthlyLimitUsd, (int, float)):
            raise ValueError(
                f"monthlyLimitUsd must be a finite number between 0.0 and {MAX_MONTHLY_LIMIT_USD}, got {monthlyLimitUsd!r}"
            )
        monthly_limit_float = float(monthlyLimitUsd)
        if not math.isfinite(monthly_limit_float) or not (0.0 <= monthly_limit_float <= MAX_MONTHLY_LIMIT_USD):
            raise ValueError(
                f"monthlyLimitUsd must be a finite number between 0.0 and {MAX_MONTHLY_LIMIT_USD}, got {monthlyLimitUsd!r}"
            )
        self.monthlyLimitUsd = monthly_limit_float

        if transport is not None and not callable(transport):
            raise TypeError("transport must be callable or None")
        self.transport = transport
        self._process_calls = 0

    def initializeBudget(self) -> dict:
        """Create missing current UTC-month entry ONLY in ledger. Safe offline, never overwrite corrupt ledger."""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        budget_file = self.state_dir / "budget.json"
        lock_file = self.state_dir / "jev.lock"
        month_key = _current_utc_month()

        with _FileLock(lock_file):
            if budget_file.exists():
                try:
                    data = _read_bounded_json(budget_file, MAX_BUDGET_FILE_BYTES)
                except Exception as e:
                    raise ValueError(f"Existing budget ledger is corrupt or invalid: {e}") from e

                valid_ledger, err_msg = _validateBudgetLedger(data)
                if not valid_ledger:
                    raise ValueError(f"Existing budget ledger is corrupt or invalid: {err_msg}")

                if month_key in data:
                    entry = data[month_key]
                    return {
                        "status": "already_exists",
                        "month": month_key,
                        "created": False,
                        "reserved_usd": float(entry["reserved_usd"]),
                        "spent_usd": float(entry["spent_usd"]),
                        "attempts": int(entry["attempts"]),
                        "successes": int(entry["successes"]),
                    }

                entry = {
                    "reserved_usd": 0.0,
                    "spent_usd": 0.0,
                    "attempts": 0,
                    "successes": 0,
                }
                data[month_key] = entry
                _atomic_write_json(budget_file, data)
                return {
                    "status": "created",
                    "month": month_key,
                    "created": True,
                    "reserved_usd": 0.0,
                    "spent_usd": 0.0,
                    "attempts": 0,
                    "successes": 0,
                }
            else:
                entry = {
                    "reserved_usd": 0.0,
                    "spent_usd": 0.0,
                    "attempts": 0,
                    "successes": 0,
                }
                data = {month_key: entry}
                _atomic_write_json(budget_file, data)
                return {
                    "status": "created",
                    "month": month_key,
                    "created": True,
                    "reserved_usd": 0.0,
                    "spent_usd": 0.0,
                    "attempts": 0,
                    "successes": 0,
                }

    def _read_cache(self, cache_key: str, questions: dict) -> Optional[dict]:
        """Read and validate cached answer for this request. Returns None on cache miss or corruption."""
        cache_file = self.state_dir / "cache.json"
        if not cache_file.is_file():
            return None
        try:
            data = _read_bounded_json(cache_file, MAX_CACHE_FILE_BYTES)
            if not isinstance(data, dict):
                return None
            entry = data.get(cache_key)
            if not isinstance(entry, dict):
                return None
            val_answers, val_usage, val_err = _validate_response(entry, questions)
            if val_err is not None:
                return None
            cost = entry.get("estimatedCostUsd", 0.0)
            if type(cost) not in (int, float) or isinstance(cost, bool) or not math.isfinite(float(cost)):
                return None
            return {
                "status": "advisory",
                "reason": "ok",
                "answers": val_answers,
                "model": PINNED_MODEL,
                "cached": True,
                "usage": val_usage,
                "estimatedCostUsd": 0.0,
                "cachedOriginal": {
                    "estimatedCostUsd": float(cost),
                },
                "reservedUsd": 0.0,
                "fallback": None,
            }
        except Exception:
            return None

    def _write_cache(self, cache_key: str, entry: dict) -> None:
        """Atomically persist validated response under SHA-256 hash. Never stores raw prompts or keys."""
        cache_file = self.state_dir / "cache.json"
        lock_file = self.state_dir / "jev.lock"
        try:
            with _FileLock(lock_file):
                data = {}
                if cache_file.is_file():
                    try:
                        loaded = _read_bounded_json(cache_file, MAX_CACHE_FILE_BYTES)
                        if isinstance(loaded, dict):
                            data = loaded
                    except Exception:
                        data = {}
                data[cache_key] = entry
                if len(data) > 1000:
                    keys = list(data.keys())
                    for k in keys[:-1000]:
                        del data[k]
                _atomic_write_json(cache_file, data)
        except Exception:
            pass

    def _execute_transport(
        self,
        url: str,
        headers: dict[str, str],
        body_bytes: bytes,
        timeout: float,
    ) -> Tuple[int, bytes]:
        """Dispatch HTTP call to configured transport or default HTTPS implementation."""
        if self.transport is not None:
            if not callable(self.transport):
                raise TypeError("transport must be callable or None")
            res = self.transport(url, headers, body_bytes, timeout)
            if not isinstance(res, tuple) or len(res) != 2:
                raise ValueError("Transport must return a (status, bytes) tuple")
            status, resp_data = res[0], res[1]
            if isinstance(resp_data, str):
                resp_data = resp_data.encode("utf-8")
            elif not isinstance(resp_data, (bytes, bytearray)):
                raise ValueError("Transport response body must be bytes or str")
            return int(status), bytes(resp_data)

        return _default_transport(url, headers, body_bytes, timeout)

    def evaluate(self, state: Any, questions: dict) -> dict:
        """Evaluate state against Choice questions. Returns typed advisory or safe fallback."""
        valid, err_msg, body_bytes = _validate_request(state, questions)
        if not valid:
            reason = "request_too_large" if (err_msg and "exceeds limit" in err_msg) else "invalid_request"
            return _fallback_result(
                reason=reason,
                instruction=f"Evaluate state with questions using worker-luna reasoning (request validation: {err_msg}).",
                reserved_usd=0.0,
            )

        cache_key = _compute_cache_key(state, questions)
        cached_result = self._read_cache(cache_key, questions)
        if cached_result is not None:
            return cached_result

        if not self.live:
            return _fallback_result(
                reason="dry_run",
                instruction="Evaluate state with questions using worker-luna reasoning (dry run mode active).",
                reserved_usd=0.0,
            )

        api_key = os.environ.get("TYPESAFE_API_KEY", "").strip()
        if not api_key:
            return _fallback_result(
                reason="missing_api_key",
                instruction="Evaluate state with questions using worker-luna reasoning (TYPESAFE_API_KEY not configured).",
                reserved_usd=0.0,
            )

        # Budget verification & atomic reservation BEFORE HTTP call
        budget_file = self.state_dir / "budget.json"
        lock_file = self.state_dir / "jev.lock"
        month_key = _current_utc_month()

        try:
            with _FileLock(lock_file):
                if not budget_file.exists():
                    return _fallback_result(
                        reason="budget_uninitialized",
                        instruction="Evaluate state with questions using worker-luna reasoning (budget ledger uninitialized).",
                        reserved_usd=0.0,
                    )

                try:
                    budget_data = _read_bounded_json(budget_file, MAX_BUDGET_FILE_BYTES)
                except Exception:
                    return _fallback_result(
                        reason="budget_corrupt",
                        instruction="Evaluate state with questions using worker-luna reasoning (budget ledger is corrupt).",
                        reserved_usd=0.0,
                    )

                valid_ledger, _ = _validateBudgetLedger(budget_data)
                if not valid_ledger:
                    return _fallback_result(
                        reason="budget_corrupt",
                        instruction="Evaluate state with questions using worker-luna reasoning (budget ledger is corrupt).",
                        reserved_usd=0.0,
                    )

                if month_key not in budget_data:
                    return _fallback_result(
                        reason="budget_uninitialized",
                        instruction=f"Evaluate state with questions using worker-luna reasoning (budget missing for '{month_key}').",
                        reserved_usd=0.0,
                    )

                entry = budget_data[month_key]
                current_reserved = float(entry["reserved_usd"])
                current_attempts = int(entry["attempts"])

                if current_reserved + RESERVATION_AMOUNT_USD > self.monthlyLimitUsd + 1e-9:
                    return _fallback_result(
                        reason="budget_exceeded",
                        instruction="Evaluate state with questions using worker-luna reasoning (monthly envelope reached).",
                        reserved_usd=0.0,
                    )

                if self._process_calls >= self.maxCalls:
                    return _fallback_result(
                        reason="max_calls_exceeded",
                        instruction=f"Evaluate state with questions using worker-luna reasoning (process call limit of {self.maxCalls} reached).",
                        reserved_usd=0.0,
                    )

                entry["reserved_usd"] = round(current_reserved + RESERVATION_AMOUNT_USD, 6)
                entry["attempts"] = current_attempts + 1

                try:
                    _atomic_write_json(budget_file, budget_data)
                except (OSError, PermissionError):
                    return _fallback_result(
                        reason="budget_write_failed",
                        instruction="Evaluate state with questions using worker-luna reasoning (budget ledger write failed).",
                        reserved_usd=0.0,
                    )
                self._process_calls += 1
        except (OSError, PermissionError, RuntimeError):
            return _fallback_result(
                reason="lock_failed",
                instruction="Evaluate state with questions using worker-luna reasoning (file lock unavailable or failed).",
                reserved_usd=0.0,
            )

        reserved_usd = RESERVATION_AMOUNT_USD

        # Execute HTTP attempt
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": f"gaia-cli/{PINNED_MODEL}",
        }

        try:
            status_code, resp_bytes = self._execute_transport(
                DEFAULT_ENDPOINT,
                headers,
                body_bytes,
                DEFAULT_TIMEOUT_SECONDS,
            )
        except (TimeoutError, http.client.HTTPException):
            return _fallback_result(
                reason="timeout",
                instruction="Evaluate state with questions using worker-luna reasoning (HTTP call timed out).",
                reserved_usd=reserved_usd,
            )
        except ssl.SSLError:
            return _fallback_result(
                reason="ssl_error",
                instruction="Evaluate state with questions using worker-luna reasoning (SSL connection error).",
                reserved_usd=reserved_usd,
            )
        except OSError as exc:
            if "timed out" in str(exc).lower():
                return _fallback_result(
                    reason="timeout",
                    instruction="Evaluate state with questions using worker-luna reasoning (socket timed out).",
                    reserved_usd=reserved_usd,
                )
            return _fallback_result(
                reason="network_error",
                instruction="Evaluate state with questions using worker-luna reasoning (network communication failed).",
                reserved_usd=reserved_usd,
            )
        except Exception:
            return _fallback_result(
                reason="transport_error",
                instruction="Evaluate state with questions using worker-luna reasoning (transport execution failed).",
                reserved_usd=reserved_usd,
            )

        if 300 <= status_code < 400:
            return _fallback_result(
                reason="http_redirect_prohibited",
                instruction="Evaluate state with questions using worker-luna reasoning (HTTP redirect prohibited).",
                reserved_usd=reserved_usd,
            )

        if status_code == 401:
            return _fallback_result(
                reason="http_401",
                instruction="Evaluate state with questions using worker-luna reasoning (authentication failed 401).",
                reserved_usd=reserved_usd,
            )
        if status_code == 422:
            return _fallback_result(
                reason="http_422",
                instruction="Evaluate state with questions using worker-luna reasoning (validation error 422).",
                reserved_usd=reserved_usd,
            )
        if status_code == 429:
            return _fallback_result(
                reason="http_429",
                instruction="Evaluate state with questions using worker-luna reasoning (rate limit 429).",
                reserved_usd=reserved_usd,
            )
        if status_code == 529:
            return _fallback_result(
                reason="http_529",
                instruction="Evaluate state with questions using worker-luna reasoning (service overloaded 529).",
                reserved_usd=reserved_usd,
            )
        if status_code != 200:
            return _fallback_result(
                reason=f"http_{status_code}",
                instruction=f"Evaluate state with questions using worker-luna reasoning (HTTP {status_code}).",
                reserved_usd=reserved_usd,
            )

        if len(resp_bytes) > MAX_RESPONSE_BYTES:
            return _fallback_result(
                reason="response_too_large",
                instruction=f"Evaluate state with questions using worker-luna reasoning (response exceeds {MAX_RESPONSE_BYTES} bytes).",
                reserved_usd=reserved_usd,
            )

        try:
            resp_obj = json.loads(resp_bytes.decode("utf-8"))
        except Exception:
            return _fallback_result(
                reason="invalid_response",
                instruction="Evaluate state with questions using worker-luna reasoning (response is not valid JSON).",
                reserved_usd=reserved_usd,
            )

        val_answers, val_usage, val_err = _validate_response(resp_obj, questions)
        if val_err is not None:
            return _fallback_result(
                reason="invalid_response",
                instruction=f"Evaluate state with questions using worker-luna reasoning (response validation: {val_err}).",
                reserved_usd=reserved_usd,
            )

        estimated_cost = round(val_usage["input_tokens"] * PRICE_PER_INPUT_TOKEN, 6)

        # Update ledger with success and actual spent cost
        try:
            with _FileLock(lock_file):
                if budget_file.exists():
                    budget_data = _read_bounded_json(budget_file, MAX_BUDGET_FILE_BYTES)
                    valid_ledger, _ = _validateBudgetLedger(budget_data)
                    if valid_ledger and month_key in budget_data:
                        entry = budget_data[month_key]
                        entry["spent_usd"] = round(float(entry["spent_usd"]) + estimated_cost, 6)
                        entry["successes"] = int(entry["successes"]) + 1
                        _atomic_write_json(budget_file, budget_data)
        except Exception:
            pass

        # Write to cache
        cache_entry = {
            "model": PINNED_MODEL,
            "answers": val_answers,
            "usage": val_usage,
            "estimatedCostUsd": estimated_cost,
        }
        self._write_cache(cache_key, cache_entry)

        return {
            "status": "advisory",
            "reason": "ok",
            "answers": val_answers,
            "model": PINNED_MODEL,
            "cached": False,
            "usage": val_usage,
            "estimatedCostUsd": estimated_cost,
            "cachedOriginal": None,
            "reservedUsd": reserved_usd,
            "fallback": None,
        }
