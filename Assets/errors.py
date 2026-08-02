"""
errors.py — Centralised error handling utilities for Job Search Assistant.

Provides:
  - Custom exception hierarchy
  - retry_with_backoff() — exponential back-off with jitter
  - handle_http_status() — maps HTTP status codes to typed exceptions
  - get_logger() — file + console logger
  - require_env_vars() — fail-fast credential validation
"""

import logging
import os
import time
import random
import functools
from typing import Callable, Any, Optional

# ── Logger setup ───────────────────────────────────────────────────────────────

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "api_errors.log")


def get_logger(name: str) -> logging.Logger:
    """Return a logger that writes to both console (WARNING+) and logs/api_errors.log (DEBUG+)."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # already configured

    logger.setLevel(logging.DEBUG)

    # File handler — full detail
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))

    # Console handler — warnings and above only
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    ch.setFormatter(logging.Formatter("%(levelname)s [%(name)s]: %(message)s"))

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


# ── Custom exceptions ──────────────────────────────────────────────────────────

class JobAssistantError(Exception):
    """Base class for all project exceptions."""


class AuthError(JobAssistantError):
    """Raised when API credentials are missing or invalid (401 / 403)."""
    def __init__(self, service: str, detail: str = ""):
        self.service = service
        super().__init__(f"[{service}] Authentication failed. {detail}".strip())


class RateLimitError(JobAssistantError):
    """Raised when an API returns HTTP 429 Too Many Requests."""
    def __init__(self, service: str, retry_after: Optional[float] = None):
        self.service = service
        self.retry_after = retry_after  # seconds to wait, if provided by API
        wait_msg = f" Retry after {retry_after:.0f}s." if retry_after else ""
        super().__init__(f"[{service}] Rate limit exceeded.{wait_msg}")


class APIError(JobAssistantError):
    """Raised for unexpected non-2xx API responses."""
    def __init__(self, service: str, status_code: int, detail: str = ""):
        self.service = service
        self.status_code = status_code
        super().__init__(f"[{service}] API error {status_code}. {detail}".strip())


class NetworkError(JobAssistantError):
    """Raised for connectivity / timeout issues."""
    def __init__(self, service: str, detail: str = ""):
        self.service = service
        super().__init__(f"[{service}] Network error. {detail}".strip())


class DatabaseError(JobAssistantError):
    """Raised for PostgreSQL connection / query failures."""
    def __init__(self, detail: str = ""):
        super().__init__(f"[PostgreSQL] {detail}".strip())


# ── HTTP status mapper ─────────────────────────────────────────────────────────

def handle_http_status(response, service: str) -> None:
    """
    Inspect an HTTP response and raise a typed exception for any non-2xx status.
    Call this after every requests.get() / requests.post().

    Args:
        response: A requests.Response object.
        service:  Human-readable service name (e.g. 'Adzuna').

    Raises:
        AuthError       on 401 / 403
        RateLimitError  on 429  (parses Retry-After header when present)
        APIError        on any other non-2xx status
    """
    code = response.status_code
    if 200 <= code < 300:
        return  # success — nothing to do

    if code in (401, 403):
        raise AuthError(service, f"HTTP {code}: {response.text[:200]}")

    if code == 429:
        retry_after: Optional[float] = None
        raw = response.headers.get("Retry-After") or response.headers.get("X-RateLimit-Reset")
        if raw:
            try:
                retry_after = float(raw)
            except ValueError:
                pass
        raise RateLimitError(service, retry_after=retry_after)

    raise APIError(service, code, response.text[:200])


# ── Retry helper ───────────────────────────────────────────────────────────────

def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_exceptions: tuple = (NetworkError, APIError),
    logger: Optional[logging.Logger] = None,
):
    """
    Decorator factory — retries the wrapped function on retryable exceptions
    using exponential back-off with full jitter.

    Usage:
        @retry_with_backoff(max_retries=3, retryable_exceptions=(NetworkError,))
        def my_api_call(): ...

    Args:
        max_retries:           Maximum number of retry attempts (not counting the first try).
        base_delay:            Initial wait time in seconds.
        max_delay:             Cap on the computed wait time.
        retryable_exceptions:  Tuple of exception types that trigger a retry.
        logger:                Optional logger; falls back to module-level logger.
    """
    _log = logger or get_logger("retry")

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exc: Optional[Exception] = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except RateLimitError as exc:
                    # Honour the Retry-After from the server when present
                    wait = exc.retry_after if exc.retry_after else base_delay * (2 ** attempt)
                    wait = min(wait, max_delay)
                    _log.warning(
                        "Rate limit hit on %s (attempt %d/%d). Waiting %.1fs...",
                        exc.service, attempt + 1, max_retries + 1, wait,
                    )
                    last_exc = exc
                    if attempt < max_retries:
                        time.sleep(wait)
                except retryable_exceptions as exc:
                    wait = min(
                        base_delay * (2 ** attempt) + random.uniform(0, 1),
                        max_delay,
                    )
                    _log.warning(
                        "Retryable error on attempt %d/%d: %s. Waiting %.1fs...",
                        attempt + 1, max_retries + 1, exc, wait,
                    )
                    last_exc = exc
                    if attempt < max_retries:
                        time.sleep(wait)
            raise last_exc  # exhausted all retries

        return wrapper
    return decorator


# ── Convenience: validate required env vars ────────────────────────────────────

def require_env_vars(service: str, *var_names: str) -> dict:
    """
    Check that all required environment variables are set and non-empty.
    Raises AuthError immediately with a clear message if any are missing.

    Returns a dict of {var_name: value} for easy unpacking.
    """
    missing = [v for v in var_names if not os.getenv(v)]
    if missing:
        raise AuthError(
            service,
            f"Missing environment variables: {', '.join(missing)}. "
            "Check your .env file.",
        )
    return {v: os.getenv(v) for v in var_names}
