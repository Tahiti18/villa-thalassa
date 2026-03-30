"""Tests for discovery module: URL parsing helpers."""


from yt_bulk_transcripts.discover import (
    extract_channel_id,
    extract_handle,
    extract_playlist_id,
    extract_video_id,
)


class TestExtractVideoId:
    def test_standard_url(self):
        assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_short_url(self):
        assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_embed_url(self):
        assert extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_url_with_params(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120s&list=PLxyz"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_invalid_url(self):
        assert extract_video_id("https://example.com") is None

    def test_plain_text(self):
        assert extract_video_id("not a url at all") is None


class TestExtractChannelId:
    def test_channel_url(self):
        url = "https://www.youtube.com/channel/UCxxxxxxxxxxxxxxxxxxxxxx"
        assert extract_channel_id(url) == "UCxxxxxxxxxxxxxxxxxxxxxx"

    def test_no_channel(self):
        assert extract_channel_id("https://www.youtube.com/watch?v=abc") is None


class TestExtractHandle:
    def test_handle_url(self):
        assert extract_handle("https://www.youtube.com/@TestChannel") == "TestChannel"

    def test_bare_handle(self):
        assert extract_handle("@TestChannel") == "TestChannel"

    def test_no_handle(self):
        assert extract_handle("https://www.youtube.com/watch?v=abc") is None


class TestExtractPlaylistId:
    def test_playlist_url(self):
        url = "https://www.youtube.com/playlist?list=PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        assert extract_playlist_id(url) is not None

    def test_no_playlist(self):
        assert extract_playlist_id("https://www.youtube.com/watch?v=abc") is None
