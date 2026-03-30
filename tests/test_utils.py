"""Tests for utility functions: normalization, retry, rate limiter."""


import pytest

from yt_bulk_transcripts.utils import (
    RateLimiter,
    is_retryable_error,
    normalize_text,
    retry_with_backoff,
)

# ---------------------------------------------------------------------------
# Text normalization
# ---------------------------------------------------------------------------

class TestNormalizeText:
    def test_strips_html_tags(self):
        assert normalize_text("<b>Hello</b> <i>world</i>") == "Hello world"

    def test_decodes_html_entities(self):
        assert normalize_text("rock &amp; roll") == "rock & roll"
        assert normalize_text("a &lt; b &gt; c") == "a < b > c"

    def test_normalizes_whitespace(self):
        assert normalize_text("  hello   world  ") == "hello world"

    def test_preserves_paragraphs(self):
        result = normalize_text("para one\n\npara two")
        assert "para one" in result
        assert "para two" in result
        assert "\n\n" in result

    def test_collapses_multiple_blanks(self):
        result = normalize_text("a\n\n\n\n\nb")
        assert result == "a\n\nb"

    def test_empty_string(self):
        assert normalize_text("") == ""

    def test_complex_html(self):
        raw = '<font color="#FFFFFF">Hello</font> <c.colorCCCCCC>world</c>'
        result = normalize_text(raw)
        assert "<font" not in result
        assert "Hello" in result
        assert "world" in result


# ---------------------------------------------------------------------------
# Retryable error detection
# ---------------------------------------------------------------------------

class TestIsRetryableError:
    def test_429_detected(self):
        assert is_retryable_error(RuntimeError("HTTP Error 429")) is True

    def test_rate_limit_detected(self):
        assert is_retryable_error(RuntimeError("rate limited by server")) is True

    def test_403_detected(self):
        assert is_retryable_error(RuntimeError("HTTP Error 403 Forbidden")) is True

    def test_500_detected(self):
        assert is_retryable_error(RuntimeError("HTTP Error 500")) is True

    def test_normal_error_not_retryable(self):
        assert is_retryable_error(ValueError("invalid input")) is False


# ---------------------------------------------------------------------------
# Retry decorator
# ---------------------------------------------------------------------------

class TestRetryWithBackoff:
    def test_succeeds_immediately(self):
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def succeeds():
            nonlocal call_count
            call_count += 1
            return "ok"

        assert succeeds() == "ok"
        assert call_count == 1

    def test_retries_on_retryable_error(self):
        call_count = 0

        @retry_with_backoff(max_retries=2, base_delay=0.01, max_delay=0.05)
        def fails_then_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("HTTP Error 429 too many requests")
            return "ok"

        assert fails_then_succeeds() == "ok"
        assert call_count == 3

    def test_raises_non_retryable_immediately(self):
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("bad input")

        with pytest.raises(ValueError):
            always_fails()
        assert call_count == 1  # no retries

    def test_exhausts_retries(self):
        call_count = 0

        @retry_with_backoff(max_retries=2, base_delay=0.01, max_delay=0.05)
        def always_rate_limited():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("HTTP Error 429")

        with pytest.raises(RuntimeError):
            always_rate_limited()
        assert call_count == 3  # initial + 2 retries


# ---------------------------------------------------------------------------
# Rate Limiter
# ---------------------------------------------------------------------------

class TestRateLimiter:
    def test_initial_concurrency(self):
        rl = RateLimiter(concurrency=5, min_concurrency=1, sleep_ms=0)
        assert rl.current_concurrency == 5

    def test_error_reduces_concurrency(self):
        rl = RateLimiter(concurrency=6, min_concurrency=1, sleep_ms=0)
        rl.report_error()
        assert rl.current_concurrency == 3

    def test_error_respects_minimum(self):
        rl = RateLimiter(concurrency=2, min_concurrency=1, sleep_ms=0)
        rl.report_error()  # 2 -> 1
        rl.report_error()  # stays 1
        assert rl.current_concurrency == 1

    def test_success_recovers_concurrency(self):
        rl = RateLimiter(concurrency=4, min_concurrency=1, sleep_ms=0)
        rl.report_error()  # 4 -> 2
        assert rl.current_concurrency == 2
        rl.report_success()  # 2 -> 3
        assert rl.current_concurrency == 3
        rl.report_success()  # 3 -> 4
        assert rl.current_concurrency == 4
        rl.report_success()  # stays 4 (max)
        assert rl.current_concurrency == 4

    def test_acquire_release(self):
        rl = RateLimiter(concurrency=2, min_concurrency=1, sleep_ms=0)
        rl.acquire()
        rl.release()  # should not raise
