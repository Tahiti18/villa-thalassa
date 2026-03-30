"""Transcript extraction using yt-dlp subprocess + VTT/JSON3 parsing."""

from __future__ import annotations

import json
import logging
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .models import (
    AppConfig,
    CaptionSource,
    TranscriptSegment,
    VideoMeta,
    VideoRecord,
    VideoStatus,
)
from .utils import normalize_text

logger = logging.getLogger("yt_bulk_transcripts.extract")


# ---------------------------------------------------------------------------
# yt-dlp subprocess helpers
# ---------------------------------------------------------------------------

def _run_ytdlp(args: list[str], config: AppConfig) -> subprocess.CompletedProcess:
    """Run a yt-dlp command with the configured user agent."""
    cmd = [
        "yt-dlp",
        "--user-agent", config.user_agent,
        "--no-warnings",
        *args,
    ]
    logger.debug("Running: %s", " ".join(cmd))
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
    )


def list_subtitles(video_id: str, config: AppConfig) -> dict:
    """Run yt-dlp --list-subs and parse available subtitles.

    Returns dict:
        {
            "manual": {"en": [...formats], "es": [...]},
            "auto": {"en": [...formats], ...}
        }
    """
    result = _run_ytdlp(
        ["--list-subs", "--skip-download", f"https://www.youtube.com/watch?v={video_id}"],
        config,
    )

    output = result.stdout + "\n" + result.stderr
    subs: dict[str, dict[str, list[str]]] = {"manual": {}, "auto": {}}

    # Check for rate limiting
    if result.returncode != 0:
        stderr_lower = result.stderr.lower()
        if "429" in stderr_lower or "too many" in stderr_lower or "rate" in stderr_lower:
            raise RuntimeError(f"HTTP Error 429 rate limited for {video_id}")
        if "403" in stderr_lower:
            raise RuntimeError(f"HTTP Error 403 forbidden for {video_id}")

    section = None
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        lower = stripped.lower()

        if "available subtitles" in lower and "auto" not in lower:
            section = "manual"
            continue
        elif "available automatic captions" in lower or "auto-generated" in lower:
            section = "auto"
            continue

        if section and stripped and not stripped.startswith("Language"):
            # Parse language lines like: "en       vtt, ttml, srv3, srv2, srv1, json3"
            parts = stripped.split(None, 1)
            if parts:
                lang_code = parts[0]
                formats = []
                if len(parts) > 1:
                    formats = [f.strip() for f in parts[1].split(",")]
                subs[section][lang_code] = formats

    return subs


def _select_best_subtitle(
    subs: dict, config: AppConfig
) -> tuple[str, CaptionSource, str] | None:
    """Select the best subtitle track based on config preferences.

    Returns (language, source, format) or None.
    """
    # Prefer human captions first if configured
    sources_order = []
    if config.prefer_human_captions:
        sources_order = [("manual", CaptionSource.HUMAN), ("auto", CaptionSource.AUTO)]
    else:
        sources_order = [("auto", CaptionSource.AUTO), ("manual", CaptionSource.HUMAN)]

    if not config.include_auto_captions:
        sources_order = [(k, v) for k, v in sources_order if k != "auto"]

    preferred_format = config.subtitle_format  # "vtt"

    for source_key, source_type in sources_order:
        available = subs.get(source_key, {})
        for lang_code, formats in available.items():
            if config.language_matches(lang_code):
                if preferred_format in formats:
                    fmt = preferred_format
                else:
                    fmt = formats[0] if formats else "vtt"
                return (lang_code, source_type, fmt)

    return None


def download_subtitles(
    video_id: str,
    language: str,
    auto: bool,
    fmt: str,
    output_dir: Path,
    config: AppConfig,
) -> Path | None:
    """Download subtitles for a video using yt-dlp.

    Returns path to the downloaded subtitle file, or None.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(output_dir / "%(id)s.%(ext)s")

    args = [
        "--skip-download",
        "--sub-lang", language,
        "--sub-format", fmt,
        "-o", output_template,
    ]

    if auto:
        args.append("--write-auto-subs")
    else:
        args.append("--write-subs")

    args.append(f"https://www.youtube.com/watch?v={video_id}")

    result = _run_ytdlp(args, config)

    if result.returncode != 0:
        stderr_lower = result.stderr.lower()
        if "429" in stderr_lower or "too many" in stderr_lower:
            raise RuntimeError(f"HTTP Error 429 rate limited for {video_id}")
        logger.warning("yt-dlp download failed for %s: %s", video_id, result.stderr[:200])
        return None

    # Find the downloaded subtitle file
    possible_extensions = [fmt, "vtt", "srt", "json3", "ttml", "srv3"]
    for ext in possible_extensions:
        candidate = output_dir / f"{video_id}.{language}.{ext}"
        if candidate.exists():
            return candidate
        # yt-dlp sometimes uses different naming
        candidate2 = output_dir / f"{video_id}.{ext}"
        if candidate2.exists():
            return candidate2

    # Search for any subtitle file with this video_id
    for f in output_dir.iterdir():
        if f.stem.startswith(video_id) and f.suffix in (".vtt", ".srt", ".json3", ".ttml"):
            return f

    logger.warning("Subtitle file not found after download for %s", video_id)
    return None


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

_VTT_TIMESTAMP_RE = re.compile(
    r"(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})\.(\d{3})"
)


def _ts_to_seconds(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_vtt(content: str) -> list[TranscriptSegment]:
    """Parse a WebVTT file into TranscriptSegment list."""
    segments: list[TranscriptSegment] = []
    lines = content.splitlines()
    i = 0

    while i < len(lines):
        match = _VTT_TIMESTAMP_RE.search(lines[i])
        if match:
            g = match.groups()
            start = _ts_to_seconds(g[0], g[1], g[2], g[3])
            end = _ts_to_seconds(g[4], g[5], g[6], g[7])
            i += 1
            text_lines = []
            while i < len(lines) and lines[i].strip():
                text_lines.append(lines[i].strip())
                i += 1
            text = normalize_text(" ".join(text_lines))
            if text:
                segments.append(TranscriptSegment(start=start, end=end, text=text))
        else:
            i += 1

    # Deduplicate overlapping segments (auto-captions often repeat)
    deduped: list[TranscriptSegment] = []
    for seg in segments:
        if deduped and seg.text == deduped[-1].text and abs(seg.start - deduped[-1].start) < 0.1:
            continue
        deduped.append(seg)

    return deduped


def parse_json3(content: str) -> list[TranscriptSegment]:
    """Parse a YouTube JSON3 subtitle format into TranscriptSegment list."""
    segments: list[TranscriptSegment] = []
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        logger.warning("Invalid JSON3 content")
        return segments

    events = data.get("events", [])
    for event in events:
        start_ms = event.get("tStartMs", 0)
        duration_ms = event.get("dDurationMs", 0)

        segs = event.get("segs", [])
        if not segs:
            continue

        text_parts = [s.get("utf8", "") for s in segs]
        text = normalize_text("".join(text_parts))
        if not text or text == "\n":
            continue

        segments.append(TranscriptSegment(
            start=start_ms / 1000,
            end=(start_ms + duration_ms) / 1000,
            text=text,
        ))

    return segments


def _parse_subtitle_file(path: Path) -> list[TranscriptSegment]:
    """Detect format and parse a subtitle file."""
    content = path.read_text(encoding="utf-8", errors="replace")
    suffix = path.suffix.lower()

    if suffix == ".json3" or suffix == ".json":
        try:
            # Try JSON3 first
            return parse_json3(content)
        except Exception:
            pass

    # Default to VTT parser (handles VTT and similar formats)
    return parse_vtt(content)


# ---------------------------------------------------------------------------
# Main extraction orchestrator
# ---------------------------------------------------------------------------

def extract_transcript(
    video_meta: VideoMeta,
    config: AppConfig,
    output_dir: Path | None = None,
) -> VideoRecord:
    """Extract transcript for a single video.

    1. List available subtitles
    2. Select best match
    3. Download subtitle file
    4. Parse into segments + plain text
    """
    video_id = video_meta.video_id
    now = datetime.now(timezone.utc)
    base_output = output_dir or Path(config.output_dir) / "transcripts"

    # Temporary directory for yt-dlp downloads
    with tempfile.TemporaryDirectory(prefix=f"ytbt_{video_id}_") as tmp:
        tmp_path = Path(tmp)

        try:
            # Step 1: List available subtitles
            subs = list_subtitles(video_id, config)
            logger.debug("Available subs for %s: %s", video_id, subs)

            # Step 2: Select best subtitle
            selection = _select_best_subtitle(subs, config)

            if selection is None:
                logger.info("No captions available for %s", video_id)
                return VideoRecord(
                    video_id=video_id,
                    title=video_meta.title,
                    channel_title=video_meta.channel_title,
                    channel_id=video_meta.channel_id,
                    published_at=video_meta.published_at,
                    status=VideoStatus.NO_CAPTIONS,
                    last_attempt_at=now,
                    caption_source=CaptionSource.NONE,
                )

            language, source, fmt = selection
            is_auto = (source == CaptionSource.AUTO)
            logger.info(
                "Downloading %s %s subs (%s) for %s",
                fmt, source.value, language, video_id,
            )

            # Step 3: Download subtitle file
            sub_file = download_subtitles(
                video_id, language, is_auto, fmt, tmp_path, config,
            )

            if sub_file is None:
                logger.warning("Subtitle download returned nothing for %s", video_id)
                return VideoRecord(
                    video_id=video_id,
                    title=video_meta.title,
                    channel_title=video_meta.channel_title,
                    channel_id=video_meta.channel_id,
                    published_at=video_meta.published_at,
                    status=VideoStatus.NO_CAPTIONS,
                    last_attempt_at=now,
                    caption_source=CaptionSource.NONE,
                )

            # Step 4: Parse segments
            segments = _parse_subtitle_file(sub_file)
            plain_text = "\n".join(seg.text for seg in segments)

            # Copy raw subtitle to output if configured
            if config.save_raw_subtitles:
                raw_dest = base_output / f"{video_id}.{fmt}"
                raw_dest.parent.mkdir(parents=True, exist_ok=True)
                import shutil
                shutil.copy2(str(sub_file), str(raw_dest))

            record = VideoRecord(
                video_id=video_id,
                title=video_meta.title,
                channel_title=video_meta.channel_title,
                channel_id=video_meta.channel_id,
                published_at=video_meta.published_at,
                status=VideoStatus.OK,
                last_attempt_at=now,
                language=language,
                caption_source=source,
                text=plain_text,
                segments=segments,
                extracted_at=now,
            )

            return record

        except RuntimeError as exc:
            if "429" in str(exc) or "rate" in str(exc).lower():
                logger.error("Rate limited extracting %s: %s", video_id, exc)
                return VideoRecord(
                    video_id=video_id,
                    title=video_meta.title,
                    channel_title=video_meta.channel_title,
                    channel_id=video_meta.channel_id,
                    published_at=video_meta.published_at,
                    status=VideoStatus.RATE_LIMITED,
                    last_attempt_at=now,
                    caption_source=CaptionSource.NONE,
                )
            raise

        except Exception as exc:
            logger.error("Error extracting transcript for %s: %s", video_id, exc)
            return VideoRecord(
                video_id=video_id,
                title=video_meta.title,
                channel_title=video_meta.channel_title,
                channel_id=video_meta.channel_id,
                published_at=video_meta.published_at,
                status=VideoStatus.ERROR,
                last_attempt_at=now,
                caption_source=CaptionSource.NONE,
            )
