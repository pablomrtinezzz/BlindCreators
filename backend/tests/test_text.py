from app.clients.captions import Snippet
from app.clients.youtube import parse_iso8601_duration
from app.services.text import build_chunks, build_segments, content_hash


def test_parse_duration():
    assert parse_iso8601_duration("PT1H2M3S") == 3723
    assert parse_iso8601_duration("PT45S") == 45
    assert parse_iso8601_duration("P1DT1S") == 86401
    assert parse_iso8601_duration(None) == 0
    assert parse_iso8601_duration("garbage") == 0


def test_segments_split_on_punctuation():
    snippets = [
        Snippet(0.0, 1.2, "This boss is"),
        Snippet(1.2, 1.0, "impossible."),
        Snippet(2.2, 1.5, "Unless you do this!"),
        Snippet(3.7, 0.5, "[Music]"),
    ]
    segs = build_segments(snippets)
    assert [s.text for s in segs] == ["This boss is impossible.", "Unless you do this!"]
    assert segs[0].start == 0.0 and segs[0].end <= segs[1].start


def test_segments_cap_duration_without_punctuation():
    snippets = [Snippet(float(i), 1.0, f"word{i}") for i in range(20)]
    segs = build_segments(snippets, max_seconds=6)
    assert len(segs) >= 3
    assert all(s.end - s.start <= 6.01 for s in segs)


def test_chunks_overlap():
    snippets = [Snippet(float(i), 1.0, " ".join(["w"] * 10) + ".") for i in range(30)]
    segs = build_segments(snippets, min_seconds=0.5)
    chunks = build_chunks(segs, target_words=50, overlap_words=10)
    assert len(chunks) > 1
    assert chunks[1].start < chunks[0].end  # overlap


def test_content_hash_is_stable():
    assert content_hash("a", "b") == content_hash("a", "b") != content_hash("ab")
