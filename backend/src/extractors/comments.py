import logging
import requests
from datetime import datetime
from src.models.database import VideoComment, SessionLocal

logger = logging.getLogger(__name__)

MAX_COMMENTS_PER_VIDEO = 200
THREADS_URL = "https://www.googleapis.com/youtube/v3/commentThreads"


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def extract_comments(
    video_id: str, user_email: str, access_token: str
) -> dict:
    """Pull top-level comments + bundled replies. Uses its own DB session."""
    headers = {"Authorization": f"Bearer {access_token}"}
    db = SessionLocal()

    try:
        db.query(VideoComment).filter_by(
            video_id=video_id, user_email=user_email
        ).delete()

        collected: list[VideoComment] = []
        page_token: str | None = None

        while len(collected) < MAX_COMMENTS_PER_VIDEO:
            params = {
                "part": "snippet,replies",
                "videoId": video_id,
                "maxResults": 100,
                "order": "relevance",
                "textFormat": "plainText",
            }
            if page_token:
                params["pageToken"] = page_token

            try:
                res = requests.get(THREADS_URL, headers=headers, params=params, timeout=15)
            except Exception as e:
                logger.error("Comments network error %s: %s", video_id, e)
                break

            if res.status_code == 401:
                return {"status": "token_expired", "video_id": video_id}
            if res.status_code == 403:
                api_reason = ""
                try:
                    api_reason = res.json().get("error", {}).get("errors", [{}])[0].get("reason", "")
                except Exception:
                    pass
                logger.warning("Comments 403 for %s — reason: %s", video_id, api_reason)
                if api_reason == "commentsDisabled":
                    return {"status": "disabled", "video_id": video_id, "api_reason": api_reason}
                return {"status": "no_permission", "video_id": video_id, "api_reason": api_reason}
            if res.status_code != 200:
                logger.warning("Comments API %s for %s", res.status_code, video_id)
                return {"status": "error", "video_id": video_id, "http": res.status_code}

            data = res.json()

            for item in data.get("items", []):
                top_snip = item["snippet"]["topLevelComment"]["snippet"]
                thread_id = item["id"]

                collected.append(
                    VideoComment(
                        comment_id=item["snippet"]["topLevelComment"]["id"],
                        video_id=video_id,
                        user_email=user_email,
                        author=top_snip.get("authorDisplayName", ""),
                        text=top_snip.get("textDisplay", ""),
                        likes=int(top_snip.get("likeCount", 0)),
                        published_at=_parse_dt(top_snip.get("publishedAt")),
                        reply_count=int(item["snippet"].get("totalReplyCount", 0)),
                        is_reply=False,
                        parent_id=None,
                    )
                )

                for reply in item.get("replies", {}).get("comments", []):
                    rs = reply["snippet"]
                    collected.append(
                        VideoComment(
                            comment_id=reply["id"],
                            video_id=video_id,
                            user_email=user_email,
                            author=rs.get("authorDisplayName", ""),
                            text=rs.get("textDisplay", ""),
                            likes=int(rs.get("likeCount", 0)),
                            published_at=_parse_dt(rs.get("publishedAt")),
                            reply_count=0,
                            is_reply=True,
                            parent_id=thread_id,
                        )
                    )

            page_token = data.get("nextPageToken")
            if not page_token:
                break

        if collected:
            db.add_all(collected[:MAX_COMMENTS_PER_VIDEO])
            db.commit()

        return {"status": "ok", "video_id": video_id, "count": len(collected)}

    except Exception as e:
        logger.error("Comments error %s: %s", video_id, e)
        db.rollback()
        return {"status": "error", "video_id": video_id, "error": str(e)}
    finally:
        db.close()
