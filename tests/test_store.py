"""Tests for JSONL store: append, dedup, resume policy."""

import json
from datetime import datetime, timezone
from pathlib import Path

from yt_bulk_transcripts.models import (
    CaptionSource,
    TranscriptSegment,
    VideoRecord,
    VideoStatus,
)
from yt_bulk_transcripts.store import (
    append_record,
    compact_jsonl,
    load_existing_ids,
    load_existing_records,
    save_json_file,
    save_text_file,
    should_process,
)


def _make_record(
    video_id: str = "dQw4w9WgXcQ",
    status: VideoStatus = VideoStatus.OK,
    text: str = "test transcript",
) -> VideoRecord:
    return VideoRecord(
        video_id=video_id,
        title="Test",
        status=status,
        last_attempt_at=datetime.now(timezone.utc),
        text=text,
        caption_source=CaptionSource.HUMAN if status == VideoStatus.OK else CaptionSource.NONE,
    )


class TestAppendAndLoad:
    def test_append_creates_file(self, tmp_path: Path):
        jsonl = tmp_path / "test.jsonl"
        rec = _make_record()
        append_record(jsonl, rec)

        assert jsonl.exists()
        lines = jsonl.read_text().strip().splitlines()
        assert len(lines) == 1

        data = json.loads(lines[0])
        assert data["video_id"] == "dQw4w9WgXcQ"

    def test_append_multiple(self, tmp_path: Path):
        jsonl = tmp_path / "test.jsonl"
        append_record(jsonl, _make_record("dQw4w9WgXcQ"))
        append_record(jsonl, _make_record("abc12345678"))

        records = load_existing_records(jsonl)
        assert len(records) == 2
        assert "dQw4w9WgXcQ" in records
        assert "abc12345678" in records

    def test_load_existing_ids(self, tmp_path: Path):
        jsonl = tmp_path / "test.jsonl"
        append_record(jsonl, _make_record("dQw4w9WgXcQ"))
        append_record(jsonl, _make_record("abc12345678"))

        ids = load_existing_ids(jsonl)
        assert ids == {"dQw4w9WgXcQ", "abc12345678"}

    def test_load_nonexistent_file(self, tmp_path: Path):
        jsonl = tmp_path / "missing.jsonl"
        records = load_existing_records(jsonl)
        assert records == {}


class TestIdempotency:
    def test_duplicate_append_last_wins(self, tmp_path: Path):
        jsonl = tmp_path / "test.jsonl"
        rec1 = _make_record(text="original")
        rec2 = _make_record(text="updated")

        append_record(jsonl, rec1)
        append_record(jsonl, rec2)

        # After load, last record wins for same video_id
        records = load_existing_records(jsonl)
        assert len(records) == 1
        assert records["dQw4w9WgXcQ"].text == "updated"

    def test_compact_deduplicates(self, tmp_path: Path):
        jsonl = tmp_path / "test.jsonl"
        append_record(jsonl, _make_record(text="v1"))
        append_record(jsonl, _make_record(text="v2"))
        append_record(jsonl, _make_record("abc12345678"))

        count = compact_jsonl(jsonl)
        assert count == 2  # only 2 unique video_ids

        # Verify file has exactly 2 lines
        lines = jsonl.read_text().strip().splitlines()
        assert len(lines) == 2


class TestResumePolicy:
    def test_new_video_should_process(self):
        assert should_process("dQw4w9WgXcQ", {}) is True

    def test_ok_video_skipped(self):
        existing = {"dQw4w9WgXcQ": _make_record(status=VideoStatus.OK)}
        assert should_process("dQw4w9WgXcQ", existing) is False

    def test_ok_video_processed_with_refresh(self):
        existing = {"dQw4w9WgXcQ": _make_record(status=VideoStatus.OK)}
        assert should_process("dQw4w9WgXcQ", existing, refresh_ok=True) is True

    def test_rate_limited_retried(self):
        existing = {
            "dQw4w9WgXcQ": _make_record(status=VideoStatus.RATE_LIMITED, text="")
        }
        assert should_process("dQw4w9WgXcQ", existing) is True

    def test_error_retried(self):
        existing = {"dQw4w9WgXcQ": _make_record(status=VideoStatus.ERROR, text="")}
        assert should_process("dQw4w9WgXcQ", existing) is True

    def test_no_captions_skipped(self):
        existing = {
            "dQw4w9WgXcQ": _make_record(status=VideoStatus.NO_CAPTIONS, text="")
        }
        assert should_process("dQw4w9WgXcQ", existing) is False


class TestAuxiliaryFiles:
    def test_save_text_file(self, tmp_path: Path):
        p = save_text_file("dQw4w9WgXcQ", "Hello world", tmp_path)
        assert p.exists()
        assert p.read_text() == "Hello world"
        assert p.name == "dQw4w9WgXcQ.txt"

    def test_save_json_file(self, tmp_path: Path):
        rec = _make_record()
        rec.segments = [TranscriptSegment(start=0, end=1, text="seg")]
        p = save_json_file("dQw4w9WgXcQ", rec, tmp_path)
        assert p.exists()
        data = json.loads(p.read_text())
        assert data["video_id"] == "dQw4w9WgXcQ"
        assert len(data["segments"]) == 1
