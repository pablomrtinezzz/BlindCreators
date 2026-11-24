"""Pure text helpers: caption -> sentence segments, segments -> RAG chunks."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from app.clients.captions import Snippet

_SENTENCE_END = re.compile(r"[.!?…]['\")\]]*$")
_NOISE = re.compile(r"^\[(?:music|música|applause|aplausos|risas|laughter)\]$", re.IGNORECASE)


@dataclass(frozen=True)
class Segment:
    idx: int
    start: float
    end: float
    text: str


def build_segments(
    snippets: list[Snippet], *, max_seconds: float = 6.0, min_seconds: float = 1.0
) -> list[Segment]:
    """Merges caption snippets into sentence-like segments.

    A segment closes at sentence punctuation (once it lasts `min_seconds`) or when it would
    exceed `max_seconds` (auto-captions often have no punctuation at all).
    """
    segments: list[Segment] = []
    buf: list[str] = []
    seg_start = 0.0
    seg_end = 0.0

    def flush() -> None:
        nonlocal buf
        text = " ".join(buf).strip()
        if text:
            segments.append(Segment(len(segments), round(seg_start, 2), round(seg_end, 2), text))
        buf = []

    for sn in sorted(snippets, key=lambda s: s.start):
        text = re.sub(r"\s+", " ", sn.text).strip()
        if not text or _NOISE.match(text):
            continue
        end = sn.start + max(sn.duration, 0.0)
        if buf and end - seg_start > max_seconds:
            flush()
        if not buf:
            seg_start = sn.start
        buf.append(text)
        seg_end = max(seg_end, end) if buf[:-1] else end
        if _SENTENCE_END.search(text) and seg_end - seg_start >= min_seconds:
            flush()
    flush()

    # Captions overlap: clamp each segment's end to the next start.
    fixed: list[Segment] = []
    for i, s in enumerate(segments):
        end = s.end
        if i + 1 < len(segments):
            end = min(end, segments[i + 1].start) if segments[i + 1].start > s.start else end
        fixed.append(Segment(s.idx, s.start, max(end, s.start + 0.1), s.text))
    return fixed


@dataclass(frozen=True)
class Chunk:
    idx: int
    start: float
    end: float
    text: str


def build_chunks(segments: list[Segment], *, target_words: int = 120, overlap_words: int = 20) -> list[Chunk]:
    """Groups segments into ~target_words chunks with a tail overlap for retrieval."""
    chunks: list[Chunk] = []
    cur: list[Segment] = []
    words = 0
    for seg in segments:
        cur.append(seg)
        words += len(seg.text.split())
        if words >= target_words:
            chunks.append(Chunk(len(chunks), cur[0].start, cur[-1].end, " ".join(s.text for s in cur)))
            tail: list[Segment] = []
            tail_words = 0
            for s in reversed(cur):
                tail_words += len(s.text.split())
                if tail_words > overlap_words:
                    break
                tail.insert(0, s)
            cur, words = tail, sum(len(s.text.split()) for s in tail)
    if cur and (not chunks or cur[-1].end > chunks[-1].end):
        chunks.append(Chunk(len(chunks), cur[0].start, cur[-1].end, " ".join(s.text for s in cur)))
    return chunks


def content_hash(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()[:32]


def clip(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"
