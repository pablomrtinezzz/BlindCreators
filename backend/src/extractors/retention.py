import logging
import requests
from datetime import datetime, date
from src.models.database import VideoRetention, SessionLocal

logger = logging.getLogger(__name__)

ANALYTICS_URL = "https://youtubeanalytics.googleapis.com/v2/reports"


def extract_retention(
    video_id: str, user_email: str, access_token: str
) -> dict:
    """Fetch audience-retention curve from YouTube Analytics API. Uses its own DB session."""
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "ids": "channel==MINE",
        "metrics": "audienceWatchRatio,relativeRetentionPerformance",
        "dimensions": "elapsedVideoTimeRatio",
        "filters": f"video=={video_id}",
        "startDate": "2020-01-01",
        "endDate": date.today().isoformat(),
    }

    try:
        res = requests.get(ANALYTICS_URL, headers=headers, params=params, timeout=15)
    except Exception as e:
        logger.error("Retention network error %s: %s", video_id, e)
        return {"status": "error", "video_id": video_id, "error": str(e)}

    if res.status_code == 401:
        return {"status": "token_expired", "video_id": video_id}
    if res.status_code in (403, 400):
        try:
            err_body = res.json()
            api_reason = err_body.get("error", {}).get("errors", [{}])[0].get("reason", "")
            api_message = err_body.get("error", {}).get("message", "")
        except Exception:
            api_reason, api_message, err_body = "", "", {}
        logger.warning(
            "Retention %s for %s — reason: %s  message: %s",
            res.status_code, video_id, api_reason, api_message,
        )
        return {
            "status": "no_permission",
            "video_id": video_id,
            "http": res.status_code,
            "api_reason": api_reason,
            "api_message": api_message,
            "raw": err_body,
        }
    if res.status_code != 200:
        logger.warning("Retention API %s for %s: %s", res.status_code, video_id, res.text[:200])
        return {"status": "error", "video_id": video_id, "http": res.status_code, "raw": res.text[:200]}

    body = res.json()
    rows = body.get("rows", [])
    if not rows:
        return {"status": "no_data", "video_id": video_id, "column_headers": body.get("columnHeaders", [])}

    db = SessionLocal()
    try:
        db.query(VideoRetention).filter_by(
            video_id=video_id, user_email=user_email
        ).delete()

        now = datetime.utcnow()
        db.add_all([
            VideoRetention(
                video_id=video_id,
                user_email=user_email,
                elapsed_ratio=float(row[0]),
                watch_ratio=float(row[1]),
                fetched_at=now,
            )
            for row in rows
        ])
        db.commit()
        return {"status": "ok", "video_id": video_id, "points": len(rows)}
    except Exception as e:
        db.rollback()
        logger.error("Retention DB error %s: %s", video_id, e)
        return {"status": "error", "video_id": video_id, "error": str(e)}
    finally:
        db.close()
