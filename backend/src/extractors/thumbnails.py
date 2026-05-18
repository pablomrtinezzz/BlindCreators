import logging
import sqlite3
import os
from io import BytesIO

import requests
from PIL import Image

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "data", "database.sqlite")

_THUMB_COLS = [
    ("thumb_width", "INTEGER"),
    ("thumb_height", "INTEGER"),
    ("thumb_brightness", "REAL"),
    ("thumb_aspect_ratio", "REAL"),
    ("thumb_colors", "TEXT"),
]


def _dominant_colors(img: Image.Image, n: int = 5) -> list[str]:
    small = img.resize((80, 80)).convert("RGB")
    counts: dict[tuple, int] = {}
    for px in small.getdata():
        # Quantize to 32-step buckets to group similar shades
        key = (px[0] // 32 * 32, px[1] // 32 * 32, px[2] // 32 * 32)
        counts[key] = counts.get(key, 0) + 1
    top = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:n]
    return [f"#{r:02x}{g:02x}{b:02x}" for (r, g, b), _ in top]


def _ensure_columns(cursor):
    for col, col_type in _THUMB_COLS:
        try:
            cursor.execute(f"ALTER TABLE videos ADD COLUMN {col} {col_type}")
        except Exception:
            pass


def analyze_thumbnail(
    video_id: str, user_email: str, thumbnail_url: str
) -> dict:
    """Download thumbnail and store visual metadata back into the videos table."""
    if not thumbnail_url:
        return {"status": "no_url", "video_id": video_id}

    try:
        resp = requests.get(thumbnail_url, timeout=10)
        resp.raise_for_status()
        img = Image.open(BytesIO(resp.content)).convert("RGB")
    except Exception as e:
        logger.error("Thumbnail download error %s: %s", video_id, e)
        return {"status": "error", "video_id": video_id, "error": str(e)}

    width, height = img.size
    gray = img.convert("L")
    brightness = round(sum(gray.getdata()) / (width * height), 1)
    colors = _dominant_colors(img)

    payload = {
        "thumb_width": width,
        "thumb_height": height,
        "thumb_brightness": brightness,
        "thumb_aspect_ratio": round(width / height, 2),
        "thumb_colors": ",".join(colors),
    }

    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        _ensure_columns(cur)
        cur.execute(
            """UPDATE videos
               SET thumb_width=?, thumb_height=?, thumb_brightness=?,
                   thumb_aspect_ratio=?, thumb_colors=?
               WHERE video_id=? AND user_email=?""",
            (
                payload["thumb_width"],
                payload["thumb_height"],
                payload["thumb_brightness"],
                payload["thumb_aspect_ratio"],
                payload["thumb_colors"],
                video_id,
                user_email,
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error("Thumbnail DB write error %s: %s", video_id, e)

    return {"status": "ok", "video_id": video_id, **payload}
