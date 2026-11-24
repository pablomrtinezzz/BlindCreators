from datetime import datetime

from app.models import Comment, RetentionPoint, TranscriptSegment, User, Video


def seed_user_with_video(
    db, email: str, youtube_id: str = "vid1", *, views: int = 5000, is_short: bool = True
) -> User:
    user = User(email=email, name=email)
    db.add(user)
    db.flush()
    v = Video(
        user_id=user.id,
        youtube_id=youtube_id,
        title=f"Video of {email}",
        published_at=datetime(2026, 3, 2, 18, 0),
        duration_sec=30,
        is_short=is_short,
        views=views,
        likes=100,
        comment_count=1,
        avg_view_pct=85.0,
        subscribers_gained=10,
        retention_views=views,
        transcript_status="ok",
    )
    db.add(v)
    db.flush()
    for i in range(1, 101):
        x = i / 100
        db.add(RetentionPoint(video_id=v.id, elapsed_ratio=x, watch_ratio=1.0 - 0.5 * x))
    db.add(TranscriptSegment(video_id=v.id, idx=0, start_sec=0, end_sec=3, text="Secret hook line"))
    db.add(
        Comment(
            video_id=v.id,
            youtube_comment_id=f"c-{youtube_id}",
            author="viewer",
            text="private comment",
            likes=3,
        )
    )
    db.commit()
    return user
