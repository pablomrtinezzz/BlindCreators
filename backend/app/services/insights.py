"""Channel analytics built on stored data: dashboard, Shorts lab, per-video retention."""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import utcnow
from app.models import RetentionPoint, SyncJob, TranscriptSegment, User, Video
from app.services import retention as rt

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _curves(db: Session, video_ids: list[int]) -> dict[int, rt.Curve]:
    if not video_ids:
        return {}
    out: dict[int, rt.Curve] = defaultdict(list)
    rows = db.execute(
        select(RetentionPoint.video_id, RetentionPoint.elapsed_ratio, RetentionPoint.watch_ratio)
        .where(RetentionPoint.video_id.in_(video_ids))
        .order_by(RetentionPoint.video_id, RetentionPoint.elapsed_ratio)
    ).all()
    for vid, x, y in rows:
        out[vid].append((x, y))
    return dict(out)


def _reliable(v: Video, settings: Settings) -> bool:
    return (v.retention_views or v.views or 0) >= settings.min_views_for_retention


def _hook(curve: rt.Curve, v: Video, settings: Settings) -> float | None:
    return rt.retention_at_seconds(curve, v.duration_sec, settings.hook_seconds) if curve else None


def _pct(x: float | None) -> float | None:
    return None if x is None else round(x * 100, 1)


def video_summary(v: Video, curve: rt.Curve, settings: Settings) -> dict:
    hook = _hook(curve, v, settings)
    return {
        "id": v.youtube_id,
        "title": v.title,
        "thumbnail_url": v.thumbnail_url,
        "published_at": v.published_at.isoformat() if v.published_at else None,
        "duration_sec": v.duration_sec,
        "is_short": v.is_short,
        "views": v.views,
        "likes": v.likes,
        "comment_count": v.comment_count,
        "engagement_rate": round(100 * (v.likes + v.comment_count) / v.views, 2) if v.views else None,
        "avg_view_pct": round(v.avg_view_pct, 1) if v.avg_view_pct is not None else None,
        "avg_view_duration_s": v.avg_view_duration_s,
        "subscribers_gained": v.subscribers_gained,
        "subs_per_1k_views": round(1000 * v.subscribers_gained / v.views, 2)
        if v.subscribers_gained and v.views
        else None,
        "engaged_views": v.engaged_views,
        "hook_retention_pct": _pct(hook),
        "looping": rt.is_looping(curve, v.avg_view_pct) if curve or v.avg_view_pct else False,
        "has_retention": bool(curve),
        "reliable": _reliable(v, settings),
        "transcript_status": v.transcript_status,
    }


def list_videos(db: Session, user: User, settings: Settings, kind: str = "all") -> list[dict]:
    q = select(Video).where(Video.user_id == user.id).order_by(Video.published_at.desc())
    if kind == "short":
        q = q.where(Video.is_short.is_(True))
    elif kind == "long":
        q = q.where(Video.is_short.is_(False))
    videos = db.scalars(q).all()
    curves = _curves(db, [v.id for v in videos])
    return [video_summary(v, curves.get(v.id, []), settings) for v in videos]


def channel_medians(rows: list[dict]) -> dict:
    def med(key: str) -> float | None:
        vals = [r[key] for r in rows if r.get(key) is not None and r.get("reliable", True)]
        return round(median(vals), 1) if vals else None

    return {
        "views": med("views"),
        "avg_view_pct": med("avg_view_pct"),
        "hook_retention_pct": med("hook_retention_pct"),
        "subs_per_1k_views": med("subs_per_1k_views"),
        "engagement_rate": med("engagement_rate"),
    }


def dashboard(db: Session, user: User, settings: Settings) -> dict:
    rows = list_videos(db, user, settings)
    videos = db.scalars(select(Video).where(Video.user_id == user.id)).all()
    shorts = [r for r in rows if r["is_short"]]

    by_day: dict[int, list[int]] = defaultdict(list)
    for v in videos:
        if v.published_at:
            by_day[v.published_at.weekday()].append(v.views)
    publish_days = [
        {
            "day": WEEKDAYS[d],
            "median_views": int(median(by_day[d])) if by_day[d] else 0,
            "videos": len(by_day[d]),
        }
        for d in range(7)
    ]

    actions: list[dict] = []
    recent = [r for r in shorts if r["hook_retention_pct"] is not None and r["reliable"]][:15]
    med = channel_medians(shorts)
    if recent and med["hook_retention_pct"] is not None:
        worst = min(recent, key=lambda r: r["hook_retention_pct"])
        if worst["hook_retention_pct"] < med["hook_retention_pct"]:
            actions.append(
                {
                    "kind": "weak_hook",
                    "video_id": worst["id"],
                    "title": worst["title"],
                    "value": worst["hook_retention_pct"],
                    "benchmark": med["hook_retention_pct"],
                    "message": f"Only {worst['hook_retention_pct']}% still watching at {settings.hook_seconds:.0f}s "
                    f"(channel median {med['hook_retention_pct']}%).",
                }
            )
    best_day = max(
        (d for d in publish_days if d["videos"] >= 3), key=lambda d: d["median_views"], default=None
    )
    if best_day:
        actions.append(
            {
                "kind": "best_day",
                "value": best_day["median_views"],
                "title": best_day["day"],
                "message": f"{best_day['day']} uploads get the highest median views "
                f"({best_day['median_views']:,} across {best_day['videos']} videos).",
            }
        )
    top_comment_video = max(videos, key=lambda v: v.comment_count, default=None)
    if top_comment_video and top_comment_video.comment_count:
        actions.append(
            {
                "kind": "conversation",
                "video_id": top_comment_video.youtube_id,
                "title": top_comment_video.title,
                "value": top_comment_video.comment_count,
                "message": f"Most discussed video ({top_comment_video.comment_count:,} comments). "
                "Mine its comments for your next idea.",
            }
        )

    last_job = db.scalar(
        select(SyncJob).where(SyncJob.user_id == user.id).order_by(SyncJob.created_at.desc()).limit(1)
    )
    total_views = sum(v.views for v in videos)
    cutoff = utcnow() - timedelta(days=28)
    return {
        "channel": {
            "title": user.channel_title,
            "thumbnail": user.channel_thumbnail,
            "subscribers": user.subscribers,
            "last_synced_at": user.last_synced_at.isoformat() if user.last_synced_at else None,
        },
        "kpis": {
            "videos": len(videos),
            "shorts": len(shorts),
            "total_views": total_views,
            "median_views": int(median([v.views for v in videos])) if videos else 0,
            "uploads_last_28d": sum(1 for v in videos if v.published_at and v.published_at >= cutoff),
            **{f"median_{k}": val for k, val in channel_medians(rows).items() if k != "views"},
        },
        "publish_days": publish_days,
        "top_videos": sorted(rows, key=lambda r: r["views"], reverse=True)[:5],
        "actions": actions,
        "last_job_status": last_job.status if last_job else None,
    }


def shorts_lab(db: Session, user: User, settings: Settings) -> dict:
    videos = db.scalars(
        select(Video)
        .where(Video.user_id == user.id, Video.is_short.is_(True))
        .order_by(Video.published_at.desc())
    ).all()
    curves = _curves(db, [v.id for v in videos])
    first_lines: dict[int, str] = {}
    if videos:
        for vid, text in db.execute(
            select(TranscriptSegment.video_id, TranscriptSegment.text).where(
                TranscriptSegment.video_id.in_([v.id for v in videos]), TranscriptSegment.idx == 0
            )
        ).all():
            first_lines[vid] = text

    rows = []
    for v in videos:
        curve = curves.get(v.id, [])
        base = video_summary(v, curve, settings)
        drops = rt.detect_drop_offs(curve, v.duration_sec, skip_start_s=settings.hook_seconds, top=1)
        base.update(
            {
                "first_line": first_lines.get(v.id),
                "biggest_drop_sec": drops[0].at_sec if drops else None,
                "biggest_drop_pct": _pct(drops[0].drop) if drops else None,
                "retention_1s_pct": _pct(rt.retention_at_seconds(curve, v.duration_sec, 1.0))
                if curve
                else None,
                "retention_end_pct": _pct(curve[-1][1]) if curve else None,
            }
        )
        rows.append(base)

    reliable_curves = [curves[v.id] for v in videos if v.id in curves and _reliable(v, settings)]
    med = rt.median_curve(reliable_curves)
    return {
        "shorts": rows,
        "medians": channel_medians(rows),
        "median_curve": [{"x": round(x * 100, 1), "y": _pct(y)} for x, y in med],
        "min_views_for_retention": settings.min_views_for_retention,
        "hook_seconds": settings.hook_seconds,
    }


def video_detail(db: Session, user: User, youtube_id: str, settings: Settings) -> dict | None:
    v = db.scalar(select(Video).where(Video.user_id == user.id, Video.youtube_id == youtube_id))
    if v is None:
        return None
    curve = _curves(db, [v.id]).get(v.id, [])
    segs = db.scalars(
        select(TranscriptSegment).where(TranscriptSegment.video_id == v.id).order_by(TranscriptSegment.idx)
    ).all()

    peers = db.scalars(
        select(Video).where(Video.user_id == user.id, Video.is_short.is_(v.is_short), Video.id != v.id)
    ).all()
    peer_curves = _curves(db, [p.id for p in peers if _reliable(p, settings)])
    benchmark = rt.median_curve(list(peer_curves.values()))

    seg_rows = rt.segment_retention(
        curve, v.duration_sec, [(s.idx, s.start_sec, s.end_sec, s.text) for s in segs]
    )
    drops = rt.detect_drop_offs(curve, v.duration_sec, skip_start_s=settings.hook_seconds)

    def seg_at(sec: float) -> str | None:
        for s in segs:
            if s.start_sec <= sec <= s.end_sec:
                return s.text
        return None

    return {
        "video": video_summary(v, curve, settings) | {"description": v.description[:2000]},
        "curve": [
            {
                "x": round(x * 100, 1),
                "sec": round(x * v.duration_sec, 2),
                "y": _pct(y),
                "benchmark": _pct(rt.interpolate(benchmark, x)) if benchmark else None,
            }
            for x, y in curve
        ],
        "drop_offs": [
            {
                "at_sec": d.at_sec,
                "drop_pct": _pct(d.drop),
                "from_pct": _pct(d.retention_before),
                "to_pct": _pct(d.retention_after),
                "line": seg_at(d.at_sec),
            }
            for d in drops
        ],
        "segments": [
            {
                "idx": s.idx,
                "start_sec": s.start_sec,
                "end_sec": s.end_sec,
                "text": s.text,
                "retention_start_pct": _pct(s.retention_start),
                "retention_end_pct": _pct(s.retention_end),
                "delta_pct": _pct(s.delta),
                "severity": s.severity,
            }
            for s in seg_rows
        ]
        if seg_rows
        else [{"idx": s.idx, "start_sec": s.start_sec, "end_sec": s.end_sec, "text": s.text} for s in segs],
        "transcript": {
            "status": v.transcript_status,
            "language": v.transcript_language,
            "auto_generated": v.transcript_is_generated,
        },
        "benchmark_videos": len(peer_curves),
        "min_views_for_retention": settings.min_views_for_retention,
    }
