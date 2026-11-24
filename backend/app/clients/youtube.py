"""Thin, typed client for the YouTube Data API v3 and YouTube Analytics API v2.

Quota (Data API, default 10,000 units/day): channels.list, playlistItems.list, videos.list and
commentThreads.list cost 1 unit each. A full sync of a 500-video channel is ~30 units plus
comments, so quota is not a practical constraint; avoid search.list (100) and captions (200).
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

logger = logging.getLogger(__name__)

DATA_API = "https://www.googleapis.com/youtube/v3"
ANALYTICS_API = "https://youtubeanalytics.googleapis.com/v2/reports"
TOKENINFO = "https://oauth2.googleapis.com/tokeninfo"


class YouTubeError(Exception):
    def __init__(self, message: str, status: int | None = None, reason: str = ""):
        super().__init__(message)
        self.status = status
        self.reason = reason


class YouTubeAuthError(YouTubeError):
    """The access token is invalid or expired."""


class YouTubeForbidden(YouTubeError):
    """403 that is not an auth problem (comments disabled, missing scope, quota...)."""


class _Retryable(YouTubeError):
    pass


@dataclass(frozen=True)
class Channel:
    id: str
    title: str
    thumbnail: str | None
    subscribers: int | None
    uploads_playlist: str


def parse_iso8601_duration(value: str | None) -> int:
    """'PT1H2M3S' -> 3723. Returns 0 for missing/unknown values."""
    if not value:
        return 0
    match = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value)
    if not match:
        return 0
    d, h, m, s = (int(g) if g else 0 for g in match.groups())
    return d * 86400 + h * 3600 + m * 60 + s


def _error_reason(res: httpx.Response) -> tuple[str, str]:
    try:
        err = res.json().get("error", {})
        reason = (err.get("errors") or [{}])[0].get("reason", "")
        return reason, err.get("message", "")
    except Exception:
        return "", res.text[:200]


class YouTubeClient:
    def __init__(self, access_token: str, *, timeout: float = 20.0, http: httpx.Client | None = None):
        self._http = http or httpx.Client(timeout=timeout)
        self._headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        self._token = access_token

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> YouTubeClient:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # ── transport ────────────────────────────────────────────────────────────
    @retry(
        retry=retry_if_exception_type((_Retryable, httpx.TransportError)),
        wait=wait_exponential_jitter(initial=1, max=20),
        stop=stop_after_attempt(4),
        reraise=True,
    )
    def _get(self, url: str, params: dict) -> dict:
        res = self._http.get(url, params=params, headers=self._headers)
        if res.status_code == 200:
            return res.json()
        reason, message = _error_reason(res)
        if res.status_code == 401:
            raise YouTubeAuthError("Google access token expired or invalid", 401, reason)
        if res.status_code == 429 or res.status_code >= 500 or reason in ("rateLimitExceeded",):
            raise _Retryable(message or "retryable error", res.status_code, reason)
        if res.status_code == 403:
            raise YouTubeForbidden(message or "forbidden", 403, reason)
        raise YouTubeError(message or f"HTTP {res.status_code}", res.status_code, reason)

    # ── identity ─────────────────────────────────────────────────────────────
    def token_email(self) -> str | None:
        """Email the access token was issued to (used to bind the token to the session user)."""
        res = self._http.get(TOKENINFO, params={"access_token": self._token})
        if res.status_code != 200:
            raise YouTubeAuthError("Google access token is not valid", res.status_code)
        data = res.json()
        email = data.get("email")
        return email.lower() if email else None

    # ── Data API ─────────────────────────────────────────────────────────────
    def get_my_channel(self) -> Channel | None:
        data = self._get(
            f"{DATA_API}/channels", {"part": "snippet,statistics,contentDetails", "mine": "true"}
        )
        items = data.get("items") or []
        if not items:
            return None
        ch = items[0]
        stats = ch.get("statistics", {})
        thumbs = ch.get("snippet", {}).get("thumbnails", {})
        return Channel(
            id=ch["id"],
            title=ch.get("snippet", {}).get("title", ""),
            thumbnail=(thumbs.get("high") or thumbs.get("default") or {}).get("url"),
            subscribers=None if stats.get("hiddenSubscriberCount") else int(stats.get("subscriberCount", 0)),
            uploads_playlist=ch["contentDetails"]["relatedPlaylists"]["uploads"],
        )

    def list_upload_ids(self, playlist_id: str, limit: int) -> list[str]:
        ids: list[str] = []
        token: str | None = None
        while len(ids) < limit:
            params = {"part": "contentDetails", "playlistId": playlist_id, "maxResults": 50}
            if token:
                params["pageToken"] = token
            data = self._get(f"{DATA_API}/playlistItems", params)
            ids.extend(i["contentDetails"]["videoId"] for i in data.get("items", []))
            token = data.get("nextPageToken")
            if not token:
                break
        return ids[:limit]

    def get_videos(self, ids: list[str]) -> list[dict]:
        out: list[dict] = []
        for i in range(0, len(ids), 50):
            data = self._get(
                f"{DATA_API}/videos",
                {
                    "part": "snippet,contentDetails,statistics",
                    "id": ",".join(ids[i : i + 50]),
                    "maxResults": 50,
                },
            )
            out.extend(data.get("items", []))
        return out

    def iter_comments(self, video_id: str, limit: int) -> Iterator[dict]:
        """Yields normalized top-level comments and their bundled replies."""
        token: str | None = None
        n = 0
        while n < limit:
            params = {
                "part": "snippet,replies",
                "videoId": video_id,
                "maxResults": 100,
                "order": "relevance",
                "textFormat": "plainText",
            }
            if token:
                params["pageToken"] = token
            data = self._get(f"{DATA_API}/commentThreads", params)
            for item in data.get("items", []):
                top = item["snippet"]["topLevelComment"]
                yield _norm_comment(top, parent=None, reply_count=item["snippet"].get("totalReplyCount", 0))
                n += 1
                for reply in item.get("replies", {}).get("comments", []):
                    yield _norm_comment(reply, parent=top["id"], reply_count=0)
                    n += 1
                if n >= limit:
                    return
            token = data.get("nextPageToken")
            if not token:
                return

    # ── Analytics API ────────────────────────────────────────────────────────
    def _report(self, params: dict) -> dict:
        return self._get(ANALYTICS_API, {"ids": "channel==MINE", **params})

    def video_metrics(self, start: date, end: date) -> dict[str, dict]:
        """Lifetime per-video owner metrics. `engagedViews` is optional (not on every account)."""
        base = [
            "views",
            "estimatedMinutesWatched",
            "averageViewDuration",
            "averageViewPercentage",
            "subscribersGained",
        ]
        for metrics in (base + ["engagedViews"], base):
            try:
                body = self._report(
                    {
                        "startDate": start.isoformat(),
                        "endDate": end.isoformat(),
                        "dimensions": "video",
                        "metrics": ",".join(metrics),
                        "sort": "-views",
                        "maxResults": 200,
                    }
                )
            except YouTubeError as exc:
                if isinstance(exc, YouTubeAuthError) or metrics is base:
                    raise
                logger.info("engagedViews unavailable (%s); retrying without it", exc.reason or exc)
                continue
            headers = [h["name"] for h in body.get("columnHeaders", [])]
            return {row[0]: dict(zip(headers, row, strict=False)) for row in body.get("rows", [])}
        return {}

    def short_video_ids(self, start: date, end: date) -> set[str] | None:
        """IDs YouTube itself classifies as Shorts, or None if the filter is unsupported."""
        try:
            body = self._report(
                {
                    "startDate": start.isoformat(),
                    "endDate": end.isoformat(),
                    "dimensions": "video",
                    "metrics": "views",
                    "filters": "creatorContentType==SHORTS",
                    "sort": "-views",
                    "maxResults": 200,
                }
            )
        except YouTubeAuthError:
            raise
        except YouTubeError as exc:
            logger.info("creatorContentType filter unsupported: %s", exc)
            return None
        return {row[0] for row in body.get("rows", [])}

    def retention(self, video_id: str, start: date, end: date) -> list[tuple[float, float, float | None]]:
        """100-point audience retention curve: (elapsed_ratio, watch_ratio, relative_performance)."""
        body = self._report(
            {
                "startDate": start.isoformat(),
                "endDate": end.isoformat(),
                "dimensions": "elapsedVideoTimeRatio",
                "metrics": "audienceWatchRatio,relativeRetentionPerformance",
                "filters": f"video=={video_id}",
            }
        )
        rows = body.get("rows") or []
        return [
            (float(r[0]), float(r[1]), float(r[2]) if len(r) > 2 and r[2] is not None else None) for r in rows
        ]


def _norm_comment(c: dict, parent: str | None, reply_count: int) -> dict:
    s = c.get("snippet", {})
    return {
        "id": c["id"],
        "parent": parent,
        "author": s.get("authorDisplayName", "")[:200],
        "text": s.get("textDisplay", ""),
        "likes": int(s.get("likeCount", 0) or 0),
        "reply_count": int(reply_count or 0),
        "published_at": s.get("publishedAt"),
    }
