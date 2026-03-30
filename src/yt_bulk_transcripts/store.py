"""JSONL store: append-only writer, deduplication, resume policy."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from .models import VideoRecord, VideoStatus

logger = logging.getLogger("yt_bulk_transcripts.store")


# ---------------------------------------------------------------------------
# JSONL read/write
# ---------------------------------------------------------------------------

def load_existing_records(jsonl_path: str | Path) -> dict[str, VideoRecord]:
    """Load existing JSONL records keyed by video_id.

    Returns a dict so we can check status for resume decisions.
    """
    p = Path(jsonl_path)
    records: dict[str, VideoRecord] = {}
    if not p.exists():
        return records

    for line_num, raw_line in enumerate(
        p.read_text(encoding="utf-8").splitlines(), start=1
    ):
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            data = json.loads(raw_line)
            rec = VideoRecord.model_validate(data)
            # Keep latest record per video_id (last write wins)
            records[rec.video_id] = rec
        except Exception as exc:
            logger.warning("Skipping malformed JSONL line %d: %s", line_num, exc)

    logger.info("Loaded %d existing records from %s", len(records), p)
    return records


def load_existing_ids(jsonl_path: str | Path) -> set[str]:
    """Quick set of video_ids already in the JSONL (for dedup checks)."""
    return set(load_existing_records(jsonl_path).keys())


def should_process(
    video_id: str,
    existing: dict[str, VideoRecord],
    refresh_ok: bool = False,
) -> bool:
    """Decide whether to (re-)process a video based on resume policy.

    - Not in existing → process
    - Status rate_limited / error → always retry
    - Status ok → skip unless refresh_ok is True
    - Status no_captions → skip (captions don't appear retroactively often)
    """
    if video_id not in existing:
        return True

    rec = existing[video_id]

    if rec.status in (VideoStatus.RATE_LIMITED, VideoStatus.ERROR):
        return True

    if rec.status == VideoStatus.OK and refresh_ok:
        return True

    return False


def append_record(jsonl_path: str | Path, record: VideoRecord) -> None:
    """Append a single VideoRecord as one JSON line."""
    p = Path(jsonl_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    line = record.model_dump_json() + "\n"
    with open(p, "a", encoding="utf-8") as f:
        f.write(line)

    logger.debug("Appended record for %s (status=%s)", record.video_id, record.status.value)


def compact_jsonl(jsonl_path: str | Path) -> int:
    """Compact the JSONL file: keep only the latest record per video_id.

    Returns number of records after compaction.
    """
    records = load_existing_records(jsonl_path)
    p = Path(jsonl_path)

    # Rewrite with deduplicated records
    with open(p, "w", encoding="utf-8") as f:
        for rec in records.values():
            f.write(rec.model_dump_json() + "\n")

    logger.info("Compacted %s: %d unique records", p, len(records))
    return len(records)


# ---------------------------------------------------------------------------
# Auxiliary file outputs
# ---------------------------------------------------------------------------

def save_text_file(video_id: str, text: str, output_dir: str | Path) -> Path:
    """Save plain text transcript to {output_dir}/{video_id}.txt."""
    p = Path(output_dir) / f"{video_id}.txt"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    logger.debug("Saved text file: %s", p)
    return p


def save_json_file(video_id: str, record: VideoRecord, output_dir: str | Path) -> Path:
    """Save full record with timestamps to {output_dir}/{video_id}.json."""
    p = Path(output_dir) / f"{video_id}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(record.model_dump_json(indent=2), encoding="utf-8")
    logger.debug("Saved JSON file: %s", p)
    return p
