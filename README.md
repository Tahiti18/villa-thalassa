# yt-bulk-transcripts

**Production-grade bulk YouTube transcript collector** — extracts publicly available captions/transcripts from YouTube videos in bulk using `yt-dlp`.

> ⚠️ This tool only accesses **public videos** and **existing public captions**. It does not bypass any access controls.

## Features

- **Bulk extraction** of YouTube transcripts from channels, playlists, or video URL lists
- **Two discovery modes**: YouTube Data API v3 (channels/playlists) or direct video URLs
- **Public captions only** — `--public-captions-only` is always enforced
- **yt-dlp powered** — robust subtitle download using proven infrastructure
- **Idempotent & restartable** — safe to re-run; skips already-processed videos, retries failures
- **Dynamic rate limiting** — concurrency auto-reduces on 429/403/5xx errors
- **Deterministic outputs**: JSONL, plain text, JSON with timestamps, raw VTT files
- **Content hashing** — detect transcript changes across runs

## Quick Start

### 1. Install

```bash
pip install -e ".[dev]"
```

### 2. Configure

Edit `config.yaml`:

```yaml
youtube_api_key: null          # Set for channel/playlist discovery
languages: ["en"]              # Regex supported (e.g. "en.*")
concurrency: 3
sleep_between_requests_ms: 250
```

### 3. Add Inputs

Add video URLs to `inputs/video_urls.txt`:

```
https://www.youtube.com/watch?v=dQw4w9WgXcQ
https://www.youtube.com/watch?v=9bZkp7q19f0
```

Or channels to `inputs/channels.txt` (requires API key):

```
@ChannelHandle
https://www.youtube.com/channel/UCxxxxxxxxxxxxxxxxxxxxxxx
```

### 4. Run

```bash
# Full run
yt-bulk-transcripts run

# Dry run (discover videos, don't extract)
yt-bulk-transcripts run --dry-run

# Limit to 10 videos
yt-bulk-transcripts run --limit 10

# Only videos published after a date
yt-bulk-transcripts run --since 2024-01-01

# Re-extract previously successful videos
yt-bulk-transcripts run --refresh-ok

# Compact JSONL after run (remove duplicate entries)
yt-bulk-transcripts run --compact
```

## Output Structure

```
out/
├── transcripts.jsonl          # One JSON record per video (append-only)
├── run.log                    # Structured debug log
└── transcripts/
    ├── {video_id}.txt         # Plain text transcript
    ├── {video_id}.json        # Full record with timestamps
    └── {video_id}.vtt         # Raw subtitle file
```

### JSONL Record Schema

```json
{
  "video_id": "dQw4w9WgXcQ",
  "title": "Video Title",
  "channel_title": "Channel Name",
  "channel_id": "UCxxxxxxxxxxxxxxxxxxxxxxx",
  "published_at": "2024-01-15T10:30:00+00:00",
  "status": "ok",
  "attempt_count": 1,
  "last_attempt_at": "2025-02-23T18:00:00+00:00",
  "language": "en",
  "caption_source": "human_subs",
  "text": "Full transcript text...",
  "segments": [
    {"start": 0.0, "end": 4.0, "text": "Hello and welcome."}
  ],
  "content_hash": "a1b2c3d4e5f6g7h8",
  "extracted_at": "2025-02-23T18:00:00+00:00"
}
```

**Status values**: `ok`, `no_captions`, `rate_limited`, `error`

**Caption source**: `human_subs`, `auto_subs`, `none`

## Resume / Restart Behavior

| Previous status | Default behavior | With `--refresh-ok` |
|----------------|-----------------|-------------------|
| (new video) | Process | Process |
| `ok` | Skip | Re-process |
| `no_captions` | Skip | Skip |
| `rate_limited` | Retry | Retry |
| `error` | Retry | Retry |

## Configuration Reference

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `youtube_api_key` | string? | null | YouTube Data API v3 key |
| `languages` | list[str] | ["en"] | Language patterns (regex) |
| `prefer_human_captions` | bool | true | Prefer human over auto captions |
| `include_auto_captions` | bool | true | Fall back to auto-generated |
| `subtitle_format` | string | "vtt" | Preferred format |
| `max_videos_per_channel` | int | 500 | Max videos per channel |
| `concurrency` | int | 3 | Initial thread pool size |
| `min_concurrency` | int | 1 | Floor for dynamic reduction |
| `sleep_between_requests_ms` | int | 250 | Delay between requests |
| `user_agent` | string | "yt-bulk-transcripts/0.1.0" | User-Agent header |
| `save_text_files` | bool | true | Save .txt files |
| `save_json_files` | bool | true | Save .json files |
| `save_raw_subtitles` | bool | true | Save raw .vtt files |

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint
ruff check src/ tests/
```

## Implementation Notes

### Why yt-dlp via subprocess?

`yt-dlp` is the most robust tool for accessing public YouTube subtitles. It supports subtitle listing (`--list-subs`), downloading (`--write-subs`, `--write-auto-subs`), format selection (`--sub-format vtt`), and works without authentication for public content.

- **yt-dlp subtitle flags**: [yt-dlp manual](https://manpages.debian.org/testing/yt-dlp/yt-dlp.1.en.html) documents all subtitle-related options
- **YouTube captions API is OAuth-constrained**: The official YouTube Data API v3 `captions.download` endpoint requires OAuth 2.0 and channel owner authorization — it cannot be used to download captions from third-party channels ([Stack Overflow reference](https://stackoverflow.com/questions/tagged/youtube-data-api))

### Subtitle Format Strategy

1. **VTT preferred** — easy to parse into timed segments
2. **Fallback** — if VTT not available, uses best available format
3. **JSON3** — YouTube's native JSON subtitle format, also supported

### Dynamic Concurrency

When 429/403/5xx responses are detected, concurrency is automatically halved (floor: `min_concurrency`). On success, it recovers by +1 per successful request until reaching the configured maximum.

## License

MIT
