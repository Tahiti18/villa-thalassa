"""Tests for Pydantic models."""

from datetime import datetime, timezone

import pytest

from yt_bulk_transcripts.models import (
    AppConfig,
    CaptionSource,
    TranscriptSegment,
    VideoMeta,
    VideoRecord,
    VideoStatus,
)


class TestTranscriptSegment:
    def test_basic(self):
        seg = TranscriptSegment(start=1.0, end=2.5, text="Hello world")
        assert seg.start == 1.0
        assert seg.end == 2.5
        assert seg.text == "Hello world"

    def test_negative_start_rejected(self):
        with pytest.raises(Exception):
            TranscriptSegment(start=-1.0, end=2.5, text="bad")


class TestVideoMeta:
    def test_valid_video_id(self):
        vm = VideoMeta(video_id="dQw4w9WgXcQ")
        assert vm.video_id == "dQw4w9WgXcQ"

    def test_invalid_video_id_too_short(self):
        with pytest.raises(Exception):
            VideoMeta(video_id="abc")

    def test_invalid_video_id_too_long(self):
        with pytest.raises(Exception):
            VideoMeta(video_id="a" * 12)

    def test_invalid_video_id_bad_chars(self):
        with pytest.raises(Exception):
            VideoMeta(video_id="dQw4w9W!XcQ")

    def test_valid_channel_id(self):
        vm = VideoMeta(video_id="dQw4w9WgXcQ", channel_id="UCxxxxxxxxxxxxxxxxxxxxxxx")
        assert vm.channel_id.startswith("UC")

    def test_invalid_channel_id(self):
        with pytest.raises(Exception):
            VideoMeta(video_id="dQw4w9WgXcQ", channel_id="XX_bad_id")


class TestVideoRecord:
    def test_content_hash_computed(self):
        now = datetime.now(timezone.utc)
        rec = VideoRecord(
            video_id="dQw4w9WgXcQ",
            status=VideoStatus.OK,
            last_attempt_at=now,
            text="Hello world test transcript",
        )
        assert rec.content_hash != ""
        assert len(rec.content_hash) == 16  # SHA-256 truncated

    def test_content_hash_empty_text(self):
        now = datetime.now(timezone.utc)
        rec = VideoRecord(
            video_id="dQw4w9WgXcQ",
            status=VideoStatus.NO_CAPTIONS,
            last_attempt_at=now,
            text="",
        )
        assert rec.content_hash == ""

    def test_serialization_roundtrip(self):
        now = datetime.now(timezone.utc)
        rec = VideoRecord(
            video_id="dQw4w9WgXcQ",
            title="Test Video",
            status=VideoStatus.OK,
            last_attempt_at=now,
            language="en",
            caption_source=CaptionSource.HUMAN,
            text="Some text",
            segments=[TranscriptSegment(start=0, end=1, text="seg1")],
        )
        json_str = rec.model_dump_json()
        restored = VideoRecord.model_validate_json(json_str)
        assert restored.video_id == rec.video_id
        assert restored.status == VideoStatus.OK
        assert len(restored.segments) == 1

    def test_status_enum_values(self):
        assert VideoStatus.OK.value == "ok"
        assert VideoStatus.NO_CAPTIONS.value == "no_captions"
        assert VideoStatus.RATE_LIMITED.value == "rate_limited"
        assert VideoStatus.ERROR.value == "error"


class TestAppConfig:
    def test_defaults(self):
        cfg = AppConfig()
        assert cfg.concurrency == 3
        assert cfg.languages == ["en"]
        assert cfg.public_captions_only is True

    def test_language_matches_exact(self):
        cfg = AppConfig(languages=["en"])
        assert cfg.language_matches("en") is True
        assert cfg.language_matches("es") is False

    def test_language_matches_regex(self):
        cfg = AppConfig(languages=["en.*"])
        assert cfg.language_matches("en") is True
        assert cfg.language_matches("en-US") is True
        assert cfg.language_matches("es") is False
