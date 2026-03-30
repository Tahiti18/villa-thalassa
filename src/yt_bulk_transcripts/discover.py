"""Video discovery: YouTube Data API v3 + fallback URL parsing."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path

from .models import AppConfig, VideoMeta

logger = logging.getLogger("yt_bulk_transcripts.discover")

# Cache file for discovered videos so discovery is a cached step
DISCOVERY_CACHE = "data/discovery_cache.json"


# ---------------------------------------------------------------------------
# URL / handle parsing helpers
# ---------------------------------------------------------------------------

_VIDEO_ID_RE = re.compile(
    r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/v/)"
    r"([A-Za-z0-9_-]{11})"
)

_CHANNEL_ID_RE = re.compile(r"youtube\.com/channel/(UC[A-Za-z0-9_-]{22})")
_HANDLE_RE = re.compile(r"(?:youtube\.com/)?@([\w.-]+)")
_PLAYLIST_RE = re.compile(r"[?&]list=(PL[A-Za-z0-9_-]+|UU[A-Za-z0-9_-]+)")


def extract_video_id(url: str) -> str | None:
    """Extract an 11-character video ID from a YouTube URL."""
    m = _VIDEO_ID_RE.search(url)
    return m.group(1) if m else None


def extract_channel_id(url: str) -> str | None:
    """Extract a channel ID (UC…) from a URL."""
    m = _CHANNEL_ID_RE.search(url)
    return m.group(1) if m else None


def extract_handle(url: str) -> str | None:
    """Extract a @handle from a URL or raw handle string."""
    m = _HANDLE_RE.search(url)
    return m.group(1) if m else None


def extract_playlist_id(url: str) -> str | None:
    """Extract a playlist ID from a URL."""
    m = _PLAYLIST_RE.search(url)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# File loaders
# ---------------------------------------------------------------------------

def _read_lines(path: str | Path) -> list[str]:
    """Read non-blank, non-comment lines from a text file."""
    p = Path(path)
    if not p.exists():
        return []
    lines = []
    for raw_line in p.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#"):
            lines.append(line)
    return lines


def parse_video_urls(file_path: str | Path) -> list[VideoMeta]:
    """Parse direct video URLs from a text file (fallback mode)."""
    results: list[VideoMeta] = []
    for line in _read_lines(file_path):
        vid = extract_video_id(line)
        if vid:
            results.append(VideoMeta(video_id=vid))
        else:
            logger.warning("Could not extract video ID from line: %s", line)
    return results


# ---------------------------------------------------------------------------
# YouTube Data API v3 discovery
# ---------------------------------------------------------------------------

def _get_youtube_service(api_key: str):  # type: ignore[no-untyped-def]
    """Build a YouTube Data API v3 service object."""
    from googleapiclient.discovery import build
    return build("youtube", "v3", developerKey=api_key)


def resolve_handle_to_channel_id(handle: str, api_key: str) -> str | None:
    """Resolve a @handle to a channel ID via API search."""
    try:
        yt = _get_youtube_service(api_key)
        resp = yt.search().list(
            part="snippet",
            q=f"@{handle}",
            type="channel",
            maxResults=1,
        ).execute()
        items = resp.get("items", [])
        if items:
            return items[0]["snippet"]["channelId"]
    except Exception as exc:
        logger.error("Failed to resolve handle @%s: %s", handle, exc)
    return None


def discover_from_channel(
    channel_id: str, api_key: str, max_videos: int = 500
) -> list[VideoMeta]:
    """List videos from a channel using the YouTube Data API v3."""
    results: list[VideoMeta] = []
    try:
        yt = _get_youtube_service(api_key)
        # Get uploads playlist
        ch_resp = yt.channels().list(
            part="contentDetails,snippet",
            id=channel_id,
        ).execute()
        items = ch_resp.get("items", [])
        if not items:
            logger.warning("Channel not found: %s", channel_id)
            return results

        uploads_playlist = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
        channel_title = items[0]["snippet"]["title"]

        results = _list_playlist_videos(
            yt, uploads_playlist, channel_id, channel_title, max_videos
        )
    except Exception as exc:
        logger.error("API discovery failed for channel %s: %s", channel_id, exc)
    return results


def discover_from_playlist(
    playlist_id: str, api_key: str, max_videos: int = 500
) -> list[VideoMeta]:
    """List videos from a playlist using the YouTube Data API v3."""
    try:
        yt = _get_youtube_service(api_key)
        return _list_playlist_videos(yt, playlist_id, "", "", max_videos)
    except Exception as exc:
        logger.error("API discovery failed for playlist %s: %s", playlist_id, exc)
        return []


def _list_playlist_videos(
    yt,  # type: ignore[no-untyped-def]
    playlist_id: str,
    channel_id: str,
    channel_title: str,
    max_videos: int,
) -> list[VideoMeta]:
    """Paginate through a playlist and return VideoMeta items."""
    results: list[VideoMeta] = []
    page_token: str | None = None

    while len(results) < max_videos:
        request = yt.playlistItems().list(
            part="snippet",
            playlistId=playlist_id,
            maxResults=min(50, max_videos - len(results)),
            pageToken=page_token,
        )
        resp = request.execute()

        for item in resp.get("items", []):
            snippet = item["snippet"]
            vid = snippet["resourceId"]["videoId"]
            published = snippet.get("publishedAt", "")
            pub_dt = None
            if published:
                try:
                    pub_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                except ValueError:
                    pass

            results.append(VideoMeta(
                video_id=vid,
                title=snippet.get("title", ""),
                channel_title=channel_title or snippet.get("channelTitle", ""),
                channel_id=channel_id or snippet.get("channelId", ""),
                published_at=pub_dt,
            ))

        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return results[:max_videos]


# ---------------------------------------------------------------------------
# Discovery cache (local persistence)
# ---------------------------------------------------------------------------

def _load_cache(cache_path: Path) -> dict[str, dict]:
    """Load previously discovered videos from cache."""
    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_cache(cache_path: Path, cache: dict[str, dict]) -> None:
    """Persist discovery cache to disk."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, default=str), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main discovery entry point
# ---------------------------------------------------------------------------

def load_all_inputs(
    config: AppConfig,
    inputs_dir: str = "inputs",
    since: datetime | None = None,
    limit: int | None = None,
) -> list[VideoMeta]:
    """Load videos from all input sources. Cache discovery results locally.

    Args:
        config: Application configuration.
        inputs_dir: Directory containing input text files.
        since: If set, only include videos published after this date.
        limit: Maximum number of videos to return overall.
    """
    cache_path = Path("data/discovery_cache.json")
    cache = _load_cache(cache_path)
    all_videos: dict[str, VideoMeta] = {}

    # -- Direct video URLs (always available) ---------------------------------
    urls_file = Path(inputs_dir) / "video_urls.txt"
    for vm in parse_video_urls(urls_file):
        all_videos[vm.video_id] = vm

    api_key = config.youtube_api_key

    # -- Channels (API-only) --------------------------------------------------
    if api_key:
        channels_file = Path(inputs_dir) / "channels.txt"
        for line in _read_lines(channels_file):
            cid = extract_channel_id(line)
            if not cid:
                handle = extract_handle(line)
                if handle:
                    # Check cache first
                    cache_key = f"handle:{handle}"
                    if cache_key in cache:
                        cid = cache[cache_key].get("channel_id")
                    else:
                        cid = resolve_handle_to_channel_id(handle, api_key)
                        if cid:
                            cache[cache_key] = {"channel_id": cid}

            if cid:
                cache_key = f"channel:{cid}"
                if cache_key in cache:
                    logger.info("Using cached discovery for channel %s", cid)
                    for v_data in cache[cache_key].get("videos", []):
                        try:
                            vm = VideoMeta(**v_data)
                            all_videos[vm.video_id] = vm
                        except Exception:
                            pass
                else:
                    vids = discover_from_channel(cid, api_key, config.max_videos_per_channel)
                    for vm in vids:
                        all_videos[vm.video_id] = vm
                    cache[cache_key] = {
                        "videos": [v.model_dump(mode="json") for v in vids]
                    }
            else:
                logger.warning("Could not resolve channel from: %s", line)

        # -- Playlists (API-only) ------------------------------------------------
        playlists_file = Path(inputs_dir) / "playlists.txt"
        for line in _read_lines(playlists_file):
            pid = extract_playlist_id(line)
            if pid:
                cache_key = f"playlist:{pid}"
                if cache_key in cache:
                    logger.info("Using cached discovery for playlist %s", pid)
                    for v_data in cache[cache_key].get("videos", []):
                        try:
                            vm = VideoMeta(**v_data)
                            all_videos[vm.video_id] = vm
                        except Exception:
                            pass
                else:
                    vids = discover_from_playlist(pid, api_key, config.max_videos_per_channel)
                    for vm in vids:
                        all_videos[vm.video_id] = vm
                    cache[cache_key] = {
                        "videos": [v.model_dump(mode="json") for v in vids]
                    }

    _save_cache(cache_path, cache)

    # -- Apply filters --------------------------------------------------------
    result = list(all_videos.values())

    if since:
        from datetime import timezone
        since_aware = since if since.tzinfo else since.replace(tzinfo=timezone.utc)
        result = [
            v for v in result
            if v.published_at is None or v.published_at >= since_aware
        ]

    if limit:
        result = result[:limit]

    logger.info("Discovered %d videos total", len(result))
    return result
