import logging
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from src.models.database import VideoTranscript, VideoTranscriptChunk, SessionLocal

logger = logging.getLogger(__name__)

CHUNK_SIZE_WORDS = 150
PREFERRED_LANGS = ["es", "es-ES", "en", "en-US", "en-GB"]


def _build_chunks(
    items: list, video_id: str, user_email: str
) -> tuple[str, list[VideoTranscriptChunk]]:
    full_parts: list[str] = []
    chunks: list[VideoTranscriptChunk] = []

    current_words: list[str] = []
    chunk_start = 0.0
    chunk_idx = 0
    last_end = 0.0

    for item in items:
        txt = item.text.strip() if hasattr(item, "text") else str(item).strip()
        start = float(item.start) if hasattr(item, "start") else 0.0
        duration = float(item.duration) if hasattr(item, "duration") else 0.0
        end = start + duration
        last_end = end

        full_parts.append(txt)
        words = txt.split()

        if not current_words:
            chunk_start = start

        current_words.extend(words)

        if len(current_words) >= CHUNK_SIZE_WORDS:
            chunks.append(
                VideoTranscriptChunk(
                    video_id=video_id,
                    user_email=user_email,
                    chunk_text=" ".join(current_words),
                    start_sec=chunk_start,
                    end_sec=end,
                    chunk_index=chunk_idx,
                )
            )
            current_words = []
            chunk_idx += 1

    if current_words:
        chunks.append(
            VideoTranscriptChunk(
                video_id=video_id,
                user_email=user_email,
                chunk_text=" ".join(current_words),
                start_sec=chunk_start,
                end_sec=last_end,
                chunk_index=chunk_idx,
            )
        )

    return " ".join(full_parts), chunks


def extract_transcript(video_id: str, user_email: str) -> dict:
    """
    Extract and persist transcript for one video.
    Creates its own DB session — fully isolated from the pipeline session.
    Uses youtube-transcript-api v1.x instance-based API.
    """
    # Each call gets its own session so failures don't affect other videos
    db = SessionLocal()
    try:
        db.query(VideoTranscript).filter_by(
            video_id=video_id, user_email=user_email
        ).delete()
        db.query(VideoTranscriptChunk).filter_by(
            video_id=video_id, user_email=user_email
        ).delete()

        # v1.x: must instantiate, then use .fetch() or .list()
        ytt = YouTubeTranscriptApi()
        raw_items = None
        language = "auto"
        is_generated = True

        # Strategy 1: direct fetch with language preference (simplest)
        try:
            fetched = ytt.fetch(video_id, languages=PREFERRED_LANGS)
            raw_items = list(fetched)
            # Detect language from the transcript list
            try:
                tl = ytt.list(video_id)
                for t in tl:
                    if t.language_code in PREFERRED_LANGS:
                        language = t.language_code
                        is_generated = t.is_generated
                        break
            except Exception:
                pass
        except (TranscriptsDisabled, NoTranscriptFound):
            return {"status": "no_transcript", "video_id": video_id}
        except Exception:
            # Strategy 2: try any available language via list
            try:
                tl = ytt.list(video_id)
                all_t = list(tl)
                if not all_t:
                    return {"status": "no_transcript", "video_id": video_id}
                t = all_t[0]
                fetched = t.fetch()
                raw_items = list(fetched)
                language = t.language_code
                is_generated = t.is_generated
            except (TranscriptsDisabled, NoTranscriptFound):
                return {"status": "no_transcript", "video_id": video_id}
            except Exception as e:
                logger.warning("Transcript unavailable %s: %s", video_id, e)
                return {"status": "no_transcript", "video_id": video_id}

        if not raw_items:
            return {"status": "no_transcript", "video_id": video_id}

        full_text, chunks = _build_chunks(raw_items, video_id, user_email)

        db.add(
            VideoTranscript(
                video_id=video_id,
                user_email=user_email,
                language=language,
                is_generated=is_generated,
                full_text=full_text,
                word_count=len(full_text.split()),
            )
        )
        db.add_all(chunks)
        db.commit()

        return {
            "status": "ok",
            "video_id": video_id,
            "chunks": len(chunks),
            "words": len(full_text.split()),
            "lang": language,
        }

    except Exception as e:
        logger.error("Transcript error %s: %s", video_id, e)
        db.rollback()
        return {"status": "error", "video_id": video_id, "error": str(e)}
    finally:
        db.close()
