"""CLI entrypoint for yt-bulk-transcripts."""

from __future__ import annotations

import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import click
import yaml

from .discover import load_all_inputs
from .extract import extract_transcript
from .models import AppConfig, VideoMeta
from .store import (
    append_record,
    compact_jsonl,
    load_existing_records,
    save_json_file,
    save_text_file,
    should_process,
)
from .utils import RateLimiter, retry_with_backoff, setup_logging

logger = logging.getLogger("yt_bulk_transcripts.cli")


def _load_config(config_path: str) -> AppConfig:
    """Load and validate config.yaml."""
    p = Path(config_path)
    if not p.exists():
        click.echo(f"Config file not found: {p}", err=True)
        sys.exit(1)

    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    if raw is None:
        raw = {}
    return AppConfig.model_validate(raw)


@click.group()
@click.version_option(package_name="yt-bulk-transcripts")
def main() -> None:
    """yt-bulk-transcripts: Bulk YouTube transcript collector (public captions only)."""
    pass


@main.command()
@click.option(
    "--config", "config_path",
    default="config.yaml",
    type=click.Path(),
    help="Path to config.yaml",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Discover videos and show plan without extracting.",
)
@click.option(
    "--limit",
    type=int,
    default=None,
    help="Maximum number of videos to process.",
)
@click.option(
    "--since",
    type=click.DateTime(formats=["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"]),
    default=None,
    help="Only process videos published after this date (YYYY-MM-DD).",
)
@click.option(
    "--refresh-ok",
    is_flag=True,
    default=False,
    help="Re-extract videos with status 'ok' (detect transcript changes).",
)
@click.option(
    "--inputs-dir",
    default="inputs",
    type=click.Path(),
    help="Directory containing input text files.",
)
@click.option(
    "--compact",
    is_flag=True,
    default=False,
    help="Compact the JSONL file after run (deduplicate).",
)
def run(
    config_path: str,
    dry_run: bool,
    limit: int | None,
    since: datetime | None,
    refresh_ok: bool,
    inputs_dir: str,
    compact: bool,
) -> None:
    """Run the bulk transcript collection pipeline."""
    config = _load_config(config_path)

    # Enforce public captions only
    if not config.public_captions_only:
        click.echo("ERROR: public_captions_only must be true.", err=True)
        sys.exit(1)

    output_dir = Path(config.output_dir)
    jsonl_path = output_dir / "transcripts.jsonl"
    transcripts_dir = output_dir / "transcripts"

    setup_logging(output_dir / "run.log")
    logger.info("Starting yt-bulk-transcripts pipeline")
    logger.info("Config: concurrency=%d, languages=%s", config.concurrency, config.languages)

    # --- Discovery -----------------------------------------------------------
    click.echo("📡 Discovering videos...")
    videos = load_all_inputs(config, inputs_dir=inputs_dir, since=since, limit=limit)
    click.echo(f"   Found {len(videos)} videos")

    if not videos:
        click.echo("No videos to process. Check your input files.")
        return

    # --- Resume filter -------------------------------------------------------
    existing = load_existing_records(jsonl_path)
    to_process: list[VideoMeta] = [
        v for v in videos if should_process(v.video_id, existing, refresh_ok=refresh_ok)
    ]
    skipped = len(videos) - len(to_process)
    if skipped:
        click.echo(f"   Skipping {skipped} already-processed videos")
    click.echo(f"   Processing {len(to_process)} videos")

    if dry_run:
        click.echo("\n🔍 Dry run — videos that would be processed:")
        for v in to_process:
            pub = v.published_at.strftime("%Y-%m-%d") if v.published_at else "unknown"
            click.echo(f"   {v.video_id}  {pub}  {v.title[:60]}")
        return

    # --- Extraction ----------------------------------------------------------
    rate_limiter = RateLimiter(
        concurrency=config.concurrency,
        min_concurrency=config.min_concurrency,
        sleep_ms=config.sleep_between_requests_ms,
    )

    stats = {"ok": 0, "no_captions": 0, "rate_limited": 0, "error": 0}

    def _process_one(video_meta: VideoMeta) -> None:
        """Extract transcript for one video with rate limiting."""
        rate_limiter.acquire()
        try:
            # Wrap extraction with retry
            @retry_with_backoff(max_retries=3, rate_limiter=rate_limiter)
            def _extract():
                return extract_transcript(video_meta, config, transcripts_dir)

            record = _extract()

            # Update attempt count if retrying
            if video_meta.video_id in existing:
                prev = existing[video_meta.video_id]
                record.attempt_count = prev.attempt_count + 1

            # Append to JSONL
            append_record(jsonl_path, record)

            # Save auxiliary files
            if record.text and config.save_text_files:
                save_text_file(record.video_id, record.text, transcripts_dir)
            if record.segments and config.save_json_files:
                save_json_file(record.video_id, record, transcripts_dir)

            stats[record.status.value] += 1
            status_icon = {"ok": "✅", "no_captions": "⬜", "rate_limited": "🚫", "error": "❌"}
            click.echo(
                f"   {status_icon.get(record.status.value, '?')} "
                f"{record.video_id} → {record.status.value}"
            )

        except Exception as exc:
            stats["error"] += 1
            logger.error("Unhandled error for %s: %s", video_meta.video_id, exc)
            click.echo(f"   ❌ {video_meta.video_id} → error: {exc}")
        finally:
            rate_limiter.release()

    click.echo(f"\n🚀 Extracting transcripts (concurrency={config.concurrency})...")

    with ThreadPoolExecutor(max_workers=config.concurrency) as executor:
        futures = {
            executor.submit(_process_one, v): v for v in to_process
        }
        for future in as_completed(futures):
            # Exceptions are handled inside _process_one
            future.result()

    # --- Compact if requested -----------------------------------------------
    if compact:
        click.echo("\n🗜️  Compacting JSONL...")
        count = compact_jsonl(jsonl_path)
        click.echo(f"   {count} unique records")

    # --- Summary -------------------------------------------------------------
    click.echo("\n📊 Done!")
    click.echo(f"   ✅ OK:           {stats['ok']}")
    click.echo(f"   ⬜ No captions:  {stats['no_captions']}")
    click.echo(f"   🚫 Rate limited: {stats['rate_limited']}")
    click.echo(f"   ❌ Errors:       {stats['error']}")
    click.echo(f"   📁 Output:       {jsonl_path}")

    logger.info("Pipeline complete: %s", stats)


if __name__ == "__main__":
    main()
