"""Utilities: logging, rate limiting, retry with backoff, text normalization."""

from __future__ import annotations

import html
import logging
import random
import re
import sys
import threading
import time
from functools import wraps
from pathlib import Path
from typing import Any, Callable, TypeVar

T = TypeVar("T")

logger = logging.getLogger("yt_bulk_transcripts")


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging(log_path: str | Path = "out/run.log") -> None:
    """Configure structured logging to console + file."""
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger("yt_bulk_transcripts")
    root.setLevel(logging.DEBUG)

    # Console handler — INFO level
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S"
    ))

    # File handler — DEBUG level
    fh = logging.FileHandler(str(log_path), encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s  %(levelname)-8s  [%(name)s]  %(message)s"
    ))

    root.handlers.clear()
    root.addHandler(console)
    root.addHandler(fh)


# ---------------------------------------------------------------------------
# Rate Limiter with dynamic concurrency
# ---------------------------------------------------------------------------

class RateLimiter:
    """Thread-safe rate limiter with dynamic concurrency reduction.

    When `report_error()` is called, concurrency is halved (floor = min_concurrency).
    When `report_success()` is called, concurrency slowly recovers (+1).
    """

    def __init__(
        self,
        concurrency: int = 3,
        min_concurrency: int = 1,
        sleep_ms: int = 250,
    ) -> None:
        self._max_concurrency = concurrency
        self._min_concurrency = max(1, min_concurrency)
        self._current_concurrency = concurrency
        self._sleep_seconds = sleep_ms / 1000.0
        self._semaphore = threading.Semaphore(concurrency)
        self._lock = threading.Lock()
        self._consecutive_errors = 0

    @property
    def current_concurrency(self) -> int:
        return self._current_concurrency

    def acquire(self) -> None:
        """Acquire a slot, blocking if at capacity."""
        self._semaphore.acquire()
        if self._sleep_seconds > 0:
            time.sleep(self._sleep_seconds)

    def release(self) -> None:
        """Release a slot."""
        self._semaphore.release()

    def report_error(self) -> None:
        """Signal a 429/5xx error — reduce concurrency."""
        with self._lock:
            self._consecutive_errors += 1
            new = max(self._min_concurrency, self._current_concurrency // 2)
            if new < self._current_concurrency:
                logger.warning(
                    "Rate-limit signal: reducing concurrency %d → %d",
                    self._current_concurrency, new,
                )
                self._current_concurrency = new
                # Drain extra permits from semaphore
                self._rebuild_semaphore()

    def report_success(self) -> None:
        """Signal success — slowly recover concurrency."""
        with self._lock:
            self._consecutive_errors = 0
            if self._current_concurrency < self._max_concurrency:
                self._current_concurrency = min(
                    self._max_concurrency,
                    self._current_concurrency + 1,
                )
                self._rebuild_semaphore()

    def _rebuild_semaphore(self) -> None:
        """Replace the semaphore with the current concurrency value."""
        self._semaphore = threading.Semaphore(self._current_concurrency)


# ---------------------------------------------------------------------------
# Retry with exponential backoff + jitter
# ---------------------------------------------------------------------------

_RETRYABLE_PATTERNS = re.compile(
    r"(429|HTTP Error 429|too many requests|rate.?limit|403|HTTP Error 5\d\d)",
    re.IGNORECASE,
)


def is_retryable_error(exc: Exception) -> bool:
    """Check if an exception looks like a transient/rate-limit error."""
    msg = str(exc)
    return bool(_RETRYABLE_PATTERNS.search(msg))


def retry_with_backoff(
    max_retries: int = 4,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    rate_limiter: RateLimiter | None = None,
) -> Callable:
    """Decorator: exponential backoff with jitter for retryable errors."""

    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exc: Exception | None = None
            for attempt in range(max_retries + 1):
                try:
                    result = fn(*args, **kwargs)
                    if rate_limiter:
                        rate_limiter.report_success()
                    return result
                except Exception as exc:
                    last_exc = exc
                    if not is_retryable_error(exc) or attempt >= max_retries:
                        raise
                    if rate_limiter:
                        rate_limiter.report_error()
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    jitter = random.uniform(0, delay * 0.5)
                    total_wait = delay + jitter
                    logger.warning(
                        "Retryable error (attempt %d/%d), waiting %.1fs: %s",
                        attempt + 1, max_retries, total_wait, exc,
                    )
                    time.sleep(total_wait)
            raise last_exc  # type: ignore[misc]

        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Text normalization
# ---------------------------------------------------------------------------

def normalize_text(raw: str) -> str:
    """Clean up caption text: strip HTML, normalize whitespace."""
    # Remove HTML tags first (before unescape, so &lt;b&gt; isn't treated as a tag)
    text = re.sub(r"<[^>]+>", "", raw)
    # Then unescape HTML entities
    text = html.unescape(text)
    # Normalize whitespace (preserving paragraph breaks)
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        stripped = re.sub(r"[ \t]+", " ", line).strip()
        cleaned.append(stripped)
    text = "\n".join(cleaned)
    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
