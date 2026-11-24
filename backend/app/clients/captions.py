"""Caption fetching via youtube-transcript-api.

NOTE: this reads public caption tracks without the official captions API (which costs 200
quota units per download and needs the owner's `youtube.force-ssl` scope). It is fine for an
internal tool on your own channels; before offering the product to third parties, switch to
the official API or to uploading the script yourself. Disable with TRANSCRIPTS_ENABLED=false.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from youtube_transcript_api import (
    IpBlocked,
    NoTranscriptFound,
    RequestBlocked,
    TranscriptsDisabled,
    VideoUnavailable,
    YouTubeTranscriptApi,
)

logger = logging.getLogger(__name__)

PREFERRED_LANGS = ("es", "es-ES", "es-419", "en", "en-US", "en-GB")


@dataclass(frozen=True)
class Snippet:
    start: float
    duration: float
    text: str


@dataclass(frozen=True)
class Captions:
    language: str
    is_generated: bool
    snippets: list[Snippet]


class CaptionsBlocked(RuntimeError):
    """YouTube is rate-limiting/blocking this IP: stop fetching for this run."""


def fetch_captions(video_id: str) -> Captions | None:
    api = YouTubeTranscriptApi()
    try:
        listing = api.list(video_id)
        transcript = None
        try:
            transcript = listing.find_manually_created_transcript(PREFERRED_LANGS)
        except NoTranscriptFound:
            try:
                transcript = listing.find_transcript(PREFERRED_LANGS)
            except NoTranscriptFound:
                transcript = next(iter(listing), None)
        if transcript is None:
            return None
        fetched = transcript.fetch()
    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable):
        return None
    except (IpBlocked, RequestBlocked) as exc:
        raise CaptionsBlocked(str(exc)) from exc

    snippets = [
        Snippet(float(s.start), float(s.duration), s.text.replace("\n", " ").strip())
        for s in fetched
        if s.text and s.text.strip()
    ]
    if not snippets:
        return None
    return Captions(
        language=transcript.language_code, is_generated=transcript.is_generated, snippets=snippets
    )
