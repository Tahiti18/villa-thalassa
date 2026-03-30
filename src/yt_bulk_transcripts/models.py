"""Pydantic models for configuration and transcript data."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class VideoStatus(str, Enum):
    """Processing status for a video."""
    OK = "ok"
    NO_CAPTIONS = "no_captions"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"


class CaptionSource(str, Enum):
    """Where captions came from."""
    HUMAN = "human_subs"
    AUTO = "auto_subs"
    NONE = "none"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class TranscriptSegment(BaseModel):
    """A single timed caption segment."""
    start: float = Field(..., ge=0, description="Start time in seconds")
    end: float = Field(..., ge=0, description="End time in seconds")
    text: str


VideoId = Annotated[str, Field(min_length=11, max_length=11, pattern=r"^[A-Za-z0-9_-]{11}$")]


class VideoMeta(BaseModel):
    """Lightweight video metadata from discovery."""
    video_id: VideoId
    title: str = ""
    channel_title: str = ""
    channel_id: str = ""
    published_at: datetime | None = None

    @field_validator("channel_id")
    @classmethod
    def validate_channel_id(cls, v: str) -> str:
        if v and not v.startswith("UC"):
            raise ValueError("channel_id must start with 'UC'")
        return v


class VideoRecord(BaseModel):
    """Full output record written to JSONL."""
    video_id: VideoId
    title: str = ""
    channel_title: str = ""
    channel_id: str = ""
    published_at: datetime | None = None

    # Processing state
    status: VideoStatus
    attempt_count: int = Field(default=1, ge=1)
    last_attempt_at: datetime

    # Caption data
    language: str = ""
    caption_source: CaptionSource = CaptionSource.NONE
    text: str = ""
    segments: list[TranscriptSegment] = Field(default_factory=list)

    # Integrity
    content_hash: str = ""
    extracted_at: datetime | None = None

    def compute_content_hash(self) -> str:
        """SHA-256 of the plain text for change detection."""
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()[:16]

    def model_post_init(self, __context: object) -> None:
        """Set content_hash after init if text is present."""
        if self.text and not self.content_hash:
            self.content_hash = self.compute_content_hash()


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class AppConfig(BaseModel):
    """Application configuration, loaded from config.yaml."""
    youtube_api_key: str | None = None

    languages: list[str] = Field(default_factory=lambda: ["en"])
    prefer_human_captions: bool = True
    include_auto_captions: bool = True
    subtitle_format: str = "vtt"

    max_videos_per_channel: int = Field(default=500, ge=1)

    concurrency: int = Field(default=3, ge=1)
    min_concurrency: int = Field(default=1, ge=1)
    sleep_between_requests_ms: int = Field(default=250, ge=0)

    user_agent: str = "yt-bulk-transcripts/0.1.0"

    output_dir: str = "out"
    save_text_files: bool = True
    save_json_files: bool = True
    save_raw_subtitles: bool = True

    public_captions_only: bool = True

    def language_matches(self, lang_code: str) -> bool:
        """Check if a language code matches any configured language pattern."""
        for pattern in self.languages:
            if re.fullmatch(pattern, lang_code):
                return True
        return False
