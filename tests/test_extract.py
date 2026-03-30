"""Tests for VTT/JSON3 parsers and extract helpers."""

import pytest

from yt_bulk_transcripts.extract import parse_json3, parse_vtt

# ---------------------------------------------------------------------------
# VTT parsing
# ---------------------------------------------------------------------------

SAMPLE_VTT = """\
WEBVTT
Kind: captions
Language: en

00:00:01.000 --> 00:00:04.000
Hello and welcome to this video.

00:00:04.500 --> 00:00:08.200
Today we're going to talk about
something interesting.

00:00:09.000 --> 00:00:12.500
Let's get started with the first topic.
"""

SAMPLE_VTT_WITH_TAGS = """\
WEBVTT

00:00:01.000 --> 00:00:04.000
<b>Hello</b> and <i>welcome</i> to this &amp; video.

00:00:05.000 --> 00:00:08.000
Normal text here.
"""

SAMPLE_VTT_EMPTY = """\
WEBVTT
Kind: captions
Language: en
"""

SAMPLE_VTT_DUPLICATE = """\
WEBVTT

00:00:01.000 --> 00:00:04.000
Hello world

00:00:01.000 --> 00:00:04.000
Hello world

00:00:05.000 --> 00:00:08.000
Next segment
"""


class TestParseVTT:
    def test_basic_parsing(self):
        segments = parse_vtt(SAMPLE_VTT)
        assert len(segments) == 3
        assert segments[0].start == 1.0
        assert segments[0].end == 4.0
        assert "Hello" in segments[0].text
        assert segments[1].start == 4.5
        assert segments[2].end == 12.5

    def test_multiline_cue(self):
        segments = parse_vtt(SAMPLE_VTT)
        # Second cue spans two lines
        assert "something interesting" in segments[1].text

    def test_html_tags_stripped(self):
        segments = parse_vtt(SAMPLE_VTT_WITH_TAGS)
        assert "<b>" not in segments[0].text
        assert "<i>" not in segments[0].text
        assert "Hello" in segments[0].text
        assert "&" in segments[0].text  # HTML entity decoded

    def test_empty_vtt(self):
        segments = parse_vtt(SAMPLE_VTT_EMPTY)
        assert segments == []

    def test_empty_string(self):
        segments = parse_vtt("")
        assert segments == []

    def test_duplicate_dedup(self):
        segments = parse_vtt(SAMPLE_VTT_DUPLICATE)
        # Should deduplicate the repeated "Hello world" at same timestamp
        assert len(segments) == 2
        assert segments[0].text == "Hello world"
        assert segments[1].text == "Next segment"

    def test_timestamp_accuracy(self):
        vtt = "WEBVTT\n\n01:23:45.678 --> 02:34:56.789\nTest"
        segments = parse_vtt(vtt)
        assert len(segments) == 1
        assert segments[0].start == pytest.approx(1 * 3600 + 23 * 60 + 45.678)
        assert segments[0].end == pytest.approx(2 * 3600 + 34 * 60 + 56.789)


# ---------------------------------------------------------------------------
# JSON3 parsing
# ---------------------------------------------------------------------------

SAMPLE_JSON3 = """{
  "events": [
    {
      "tStartMs": 1000,
      "dDurationMs": 3000,
      "segs": [{"utf8": "Hello and welcome."}]
    },
    {
      "tStartMs": 5000,
      "dDurationMs": 4000,
      "segs": [{"utf8": "Today we discuss "}, {"utf8": "something cool."}]
    },
    {
      "tStartMs": 10000,
      "dDurationMs": 2000,
      "segs": [{"utf8": "\\n"}]
    }
  ]
}"""


class TestParseJSON3:
    def test_basic_parsing(self):
        segments = parse_json3(SAMPLE_JSON3)
        assert len(segments) == 2  # newline-only event should be skipped
        assert segments[0].start == 1.0
        assert segments[0].end == 4.0
        assert "Hello" in segments[0].text

    def test_multi_seg_concatenation(self):
        segments = parse_json3(SAMPLE_JSON3)
        assert "something cool" in segments[1].text

    def test_timestamps_converted(self):
        segments = parse_json3(SAMPLE_JSON3)
        assert segments[1].start == 5.0
        assert segments[1].end == 9.0

    def test_invalid_json(self):
        segments = parse_json3("not json at all")
        assert segments == []

    def test_empty_events(self):
        segments = parse_json3('{"events": []}')
        assert segments == []
