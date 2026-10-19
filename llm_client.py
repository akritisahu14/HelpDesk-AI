"""
LLM Client for HelpDesk AI.
Supports:
1. NVIDIA NIM Cloud API using NVIDIA_API_KEY from environment variable.
   Default best model: nvidia/nemotron-3-super-120b-a12b (120B MoE flagship).
2. Strict Rate Limiting: 40 RPM (Requests Per Minute) sliding window enforcement.
3. Automatic Exponential Backoff & Retry on HTTP 429 / 503.
4. Robust JSON extraction across standard content and reasoning outputs.
5. Multi-tier Fallback: NVIDIA NIM -> Local Ollama (llama3.2:1b) -> Deterministic ITIL Engine.
"""

import os
import json
import re
import time
import threading
from collections import deque
from typing import Dict, Any, Optional, Deque
import urllib.request
import urllib.error

# NVIDIA NIM Configuration
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_NVIDIA_MODEL = "nvidia/nemotron-3-super-120b-a12b"
NVIDIA_TIMEOUT_SECONDS = 25

# Rate Limit Configuration
MAX_RPM = 40
RATE_LIMIT_WINDOW_SECONDS = 60.0

# Local Ollama Fallback Configuration
OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "llama3.2:1b"
OLLAMA_TIMEOUT_SECONDS = 15

# Legacy default model identifier
DEFAULT_MODEL = DEFAULT_NVIDIA_MODEL


class SlidingWindowRateLimiter:
    """
    Thread-safe sliding window rate limiter enforcing a strict Requests-Per-Minute (RPM) ceiling.
    Maintains a rolling 60-second window of invocation timestamps.
    Automatically throttles/pauses when approaching or reaching the RPM quota.
    """

    def __init__(self, max_rpm: int = MAX_RPM, window_seconds: float = RATE_LIMIT_WINDOW_SECONDS):
        self.max_rpm = max_rpm
        self.window_seconds = window_seconds
        self.timestamps: Deque[float] = deque()
        self.lock = threading.Lock()
        self.total_requests = 0
        self.throttled_count = 0
        self.last_request_time = 0.0

    def acquire(self) -> float:
        """
        Blocks until an API call can be safely dispatched without exceeding max_rpm.
        Returns the duration waited in seconds.
        """
        waited = 0.0
        with self.lock:
            while True:
                now = time.time()
                # Purge timestamps outside the rolling window
                while self.timestamps and (now - self.timestamps[0]) >= self.window_seconds:
                    self.timestamps.popleft()

                # If quota available in the rolling window
                if len(self.timestamps) < self.max_rpm:
                    # Optional smoothing: avoid 40 concurrent bursts by enforcing small spacing (e.g. 50ms)
                    min_spacing = 0.05
                    time_since_last = now - self.last_request_time
                    if time_since_last < min_spacing:
                        sleep_space = min_spacing - time_since_last
                        time.sleep(sleep_space)
                        now = time.time()

                    self.timestamps.append(now)
                    self.last_request_time = now
                    self.total_requests += 1
                    return waited

                # Rolling quota exhausted: compute necessary sleep duration
                sleep_needed = (self.timestamps[0] + self.window_seconds) - now + 0.05
                if sleep_needed > 0:
                    self.throttled_count += 1
                    # Release lock during sleep to prevent blocking other threads
                    self.lock.release()
                    time.sleep(sleep_needed)
                    waited += sleep_needed
                    self.lock.acquire()

    def get_stats(self) -> Dict[str, Any]:
        """Returns live telemetry of the rate limiter."""
        now = time.time()
        with self.lock:
            while self.timestamps and (now - self.timestamps[0]) >= self.window_seconds:
                self.timestamps.popleft()
            active_count = len(self.timestamps)
            return {
                "max_rpm": self.max_rpm,
                "current_rpm_used": active_count,
                "available_slots": max(0, self.max_rpm - active_count),
                "utilization_pct": round((active_count / self.max_rpm) * 100.0, 1),
                "total_requests": self.total_requests,
                "throttled_count": self.throttled_count
            }


# Global rate limiter singleton
_global_rate_limiter = SlidingWindowRateLimiter(max_rpm=MAX_RPM, window_seconds=RATE_LIMIT_WINDOW_SECONDS)


def get_rate_limiter_stats() -> Dict[str, Any]:
    """Exposes real-time rate limiter metrics for UI dashboards and telemetry."""
    return _global_rate_limiter.get_stats()


def get_nvidia_api_key() -> str:
    """Retrieves NVIDIA API key from environment variable."""
    return os.environ.get("NVIDIA_API_KEY", "").strip()


def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Safely extracts a JSON object from text that may contain markdown code blocks,
    chain-of-thought commentary, or reasoning tags.
    """
    if not text:
        return None
    try:
        return json.loads(text.strip())
    except Exception:
        pass

    # Try searching for markdown code block ```json ... ``` or ``` ... ```
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except Exception:
            pass

    # Try searching for outermost curly braces { ... }
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except Exception:
            pass

    return None


def call_nvidia(
    prompt: str,
    system_prompt: str = "",
    json_mode: bool = True,
    model: str = DEFAULT_NVIDIA_MODEL,
    temperature: float = 0.1,
    max_tokens: int = 1024
) -> Dict[str, Any]:
    """
    Sends a chat completion request to the NVIDIA NIM Cloud API.
    Enforces the 40 RPM rate limit and handles HTTP 429/503 retries with exponential backoff.
    """
    api_key = get_nvidia_api_key()
    if not api_key:
        return {
            "success": False,
            "raw_text": "",
            "parsed_json": None,
            "error": "NVIDIA_API_KEY environment variable not set.",
            "source": "fallback"
        }

    url = f"{NVIDIA_BASE_URL}/chat/completions"
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json"
    }

    max_retries = 3
    backoff_delay = 2.0

    for attempt in range(max_retries):
        # 1. Enforce 40 RPM sliding-window rate limit
        throttle_wait = _global_rate_limiter.acquire()

        t0 = time.time()
        try:
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=NVIDIA_TIMEOUT_SECONDS) as response:
                latency = time.time() - t0
                resp_data = json.loads(response.read().decode("utf-8"))
                choice = resp_data.get("choices", [{}])[0]
                message = choice.get("message", {})
                
                raw_text = message.get("content") or ""
                reasoning = message.get("reasoning_content") or ""

                parsed = None
                if json_mode:
                    parsed = extract_json_from_text(raw_text)
                    if not parsed and reasoning:
                        parsed = extract_json_from_text(reasoning)

                return {
                    "success": True,
                    "raw_text": raw_text,
                    "parsed_json": parsed,
                    "reasoning_content": reasoning,
                    "source": "nvidia",
                    "model": model,
                    "latency_seconds": round(latency, 2),
                    "throttle_wait_seconds": round(throttle_wait, 2)
                }

        except urllib.error.HTTPError as http_err:
            status_code = http_err.code
            err_body = http_err.read().decode("utf-8", errors="replace")

            # Handle 429 (Rate Limit) or 503 (Service Unavailable)
            if status_code in (429, 503) and attempt < max_retries - 1:
                # Respect Retry-After header if provided
                retry_after_hdr = http_err.headers.get("Retry-After")
                sleep_time = float(retry_after_hdr) if retry_after_hdr and retry_after_hdr.isdigit() else backoff_delay
                time.sleep(sleep_time)
                backoff_delay *= 2
                continue

            return {
                "success": False,
                "raw_text": "",
                "parsed_json": None,
                "error": f"NVIDIA API HTTP {status_code}: {err_body[:200]}",
                "source": "fallback",
                "model": model
            }

        except Exception as exc:
            if attempt < max_retries - 1:
                time.sleep(backoff_delay)
                backoff_delay *= 2
                continue

            return {
                "success": False,
                "raw_text": "",
                "parsed_json": None,
                "error": f"NVIDIA API Connection Error: {str(exc)}",
                "source": "fallback",
                "model": model
            }

    return {
        "success": False,
        "raw_text": "",
        "parsed_json": None,
        "error": "Max retries exceeded for NVIDIA NIM API.",
        "source": "fallback"
    }


def call_local_ollama(
    prompt: str,
    system_prompt: str = "",
    json_mode: bool = True,
    model: str = DEFAULT_OLLAMA_MODEL,
    temperature: float = 0.1
) -> Dict[str, Any]:
    """
    Sends a generation request to the local Ollama API (fallback engine).
    """
    payload: Dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": 512
        }
    }
    if system_prompt:
        payload["system"] = system_prompt
    if json_mode:
        payload["format"] = "json"

    try:
        t0 = time.time()
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{OLLAMA_BASE_URL}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT_SECONDS) as response:
            latency = time.time() - t0
            result = json.loads(response.read().decode("utf-8"))
            raw_text = result.get("response", "").strip()

            parsed = None
            if json_mode:
                parsed = extract_json_from_text(raw_text)

            return {
                "success": True,
                "raw_text": raw_text,
                "parsed_json": parsed,
                "source": "ollama",
                "model": model,
                "latency_seconds": round(latency, 2)
            }
    except Exception as exc:
        return {
            "success": False,
            "raw_text": "",
            "parsed_json": None,
            "error": str(exc),
            "source": "fallback"
        }


def call_llm(
    prompt: str,
    system_prompt: str = "",
    json_mode: bool = True,
    model: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: int = 1024
) -> Dict[str, Any]:
    """
    Unified multi-tier LLM generation dispatch:
    1. Tries NVIDIA NIM Cloud API if NVIDIA_API_KEY is present (Enforces 40 RPM rate limit).
    2. Falls back to Local Ollama if NVIDIA fails or is unavailable.
    3. Falls back to deterministic rule-based output if both are offline.
    """
    # 1. Try NVIDIA NIM API
    if get_nvidia_api_key():
        target_model = model or DEFAULT_NVIDIA_MODEL
        res = call_nvidia(
            prompt=prompt,
            system_prompt=system_prompt,
            json_mode=json_mode,
            model=target_model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        if res.get("success") and (not json_mode or res.get("parsed_json") is not None):
            return res

    # 2. Try Local Ollama Fallback
    ollama_res = call_local_ollama(
        prompt=prompt,
        system_prompt=system_prompt,
        json_mode=json_mode,
        model=DEFAULT_OLLAMA_MODEL,
        temperature=temperature
    )
    if ollama_res.get("success") and (not json_mode or ollama_res.get("parsed_json") is not None):
        return ollama_res

    # 3. Deterministic Fallback
    return {
        "success": False,
        "raw_text": "",
        "parsed_json": None,
        "source": "deterministic_fallback",
        "error": "All LLM backends (NVIDIA NIM and Ollama) failed or unavailable. Safely engaged deterministic rule-based engine."
    }


# Backwards compatibility alias: existing agent code calling `call_ollama` will use `call_llm`
call_ollama = call_llm


def check_model_status() -> Dict[str, Any]:
    """
    Checks the status of all available LLM backends:
    - NVIDIA NIM Cloud API (Key present, rate limit capacity, active model, privacy notice)
    - Local Ollama status
    Transparently reveals cloud vs local processing so privacy claims remain accurate.
    """
    api_key = get_nvidia_api_key()
    has_nvidia_key = bool(api_key)
    masked_key = f"{api_key[:6]}...{api_key[-4:]}" if len(api_key) > 10 else ("Configured" if has_nvidia_key else "Missing")

    # Rate limiter stats
    rl_stats = get_rate_limiter_stats()

    # Ollama status check
    ollama_available = False
    ollama_models = []
    try:
        req = urllib.request.Request(f"{OLLAMA_BASE_URL}/api/tags", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            ollama_models = [m.get("name") for m in data.get("models", [])]
            ollama_available = True
    except Exception:
        pass

    active_provider = "NVIDIA NIM" if has_nvidia_key else ("Ollama" if ollama_available else "Deterministic Fallback")

    # Clear privacy transparency disclosure
    if has_nvidia_key:
        privacy_notice = "Cloud Processing (NVIDIA NIM): Queries are sent to integrate.api.nvidia.com. Cloud API calls are enabled."
        data_residency = "External Cloud (NVIDIA NIM)"
        is_cloud = True
    elif ollama_available:
        privacy_notice = "Local Processing (Ollama): Queries processed on localhost. Data remains strictly on-premise."
        data_residency = "Localhost On-Premise"
        is_cloud = False
    else:
        privacy_notice = "Offline Deterministic Mode: Rule-based heuristics active. No external API transmissions."
        data_residency = "Local Host (No LLM)"
        is_cloud = False

    return {
        "available": has_nvidia_key or ollama_available,
        "active_provider": active_provider,
        "is_cloud": is_cloud,
        "data_residency": data_residency,
        "privacy_notice": privacy_notice,
        "nvidia": {
            "available": has_nvidia_key,
            "model": DEFAULT_NVIDIA_MODEL,
            "api_key_configured": has_nvidia_key,
            "api_key_masked": masked_key,
            "max_rpm": MAX_RPM,
            "current_rpm_used": rl_stats["current_rpm_used"],
            "available_slots": rl_stats["available_slots"],
            "total_requests": rl_stats["total_requests"],
            "throttled_count": rl_stats["throttled_count"]
        },
        "ollama": {
            "available": ollama_available,
            "model": DEFAULT_OLLAMA_MODEL,
            "models": ollama_models
        },
        # Backwards compatible fields for legacy app.py
        "target_model_present": has_nvidia_key or any(DEFAULT_OLLAMA_MODEL in m for m in ollama_models),
        "models": [DEFAULT_NVIDIA_MODEL] if has_nvidia_key else ollama_models,
        "message": (
            f"NVIDIA NIM Cloud is online (Cloud API enabled). Best Model: '{DEFAULT_NVIDIA_MODEL}' (Rate Limit: {MAX_RPM} RPM)."
            if has_nvidia_key
            else ("Ollama is online (100% on-premise)." if ollama_available else "Running in deterministic fallback mode.")
        )
    }


def check_ollama_status() -> Dict[str, Any]:
    """Backwards compatibility wrapper for app.py."""
    return check_model_status()
