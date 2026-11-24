from datetime import date

import pytest
from sqlalchemy import func, select

from app.clients import captions
from app.clients.youtube import Channel, YouTubeAuthError, YouTubeForbidden
from app.models import Comment, RetentionPoint, SyncJob, TranscriptSegment, User, Video
from app.services import sync
from tests.conftest import auth


def _video_item(vid: str, seconds: int = 30, views: int = 5000, comments: int = 2) -> dict:
    return {
        "id": vid,
        "snippet": {
            "title": f"Title {vid} #shorts",
            "description": "",
            "publishedAt": "2026-03-01T10:00:00Z",
            "thumbnails": {},
        },
        "contentDetails": {"duration": f"PT{seconds}S"},
        "statistics": {"viewCount": str(views), "likeCount": "10", "commentCount": str(comments)},
    }


class FakeYouTube:
    def __init__(self, videos=("v1", "v2"), expire_on_retention_of=None):
        self.videos = list(videos)
        self.expire_on = expire_on_retention_of
        self.retention_calls: list[str] = []
        self.comment_calls: list[str] = []

    def close(self):
        pass

    def get_my_channel(self):
        return Channel(id="UC1", title="My Channel", thumbnail=None, subscribers=1000, uploads_playlist="UU1")

    def list_upload_ids(self, playlist, limit):
        return self.videos[:limit]

    def get_videos(self, ids):
        return [_video_item(i) for i in ids]

    def video_metrics(self, start: date, end: date):
        return {
            v: {"averageViewPercentage": 90.0, "averageViewDuration": 27, "subscribersGained": 3}
            for v in self.videos
        }

    def short_video_ids(self, start, end):
        return set(self.videos)

    def retention(self, vid, start, end):
        if vid == self.expire_on:
            raise YouTubeAuthError("expired", 401)
        self.retention_calls.append(vid)
        return [((i + 1) / 100, 1 - 0.004 * i, 0.5) for i in range(100)]

    def iter_comments(self, vid, limit):
        self.comment_calls.append(vid)
        if vid == "v2":
            raise YouTubeForbidden("disabled", 403, "commentsDisabled")
        yield {
            "id": f"{vid}-c1",
            "parent": None,
            "author": "a",
            "text": "great",
            "likes": 5,
            "reply_count": 1,
            "published_at": None,
        }
        yield {
            "id": f"{vid}-r1",
            "parent": f"{vid}-c1",
            "author": "b",
            "text": "agree",
            "likes": 0,
            "reply_count": 0,
            "published_at": None,
        }


@pytest.fixture(autouse=True)
def fake_captions(monkeypatch):
    monkeypatch.setattr(
        captions,
        "fetch_captions",
        lambda vid: captions.Captions(
            "es", True, [captions.Snippet(0, 2, "Hola."), captions.Snippet(2, 3, "Mira esto.")]
        ),
    )


def _job(db, email="creator@example.com") -> str:
    user = User(email=email, name="c")
    db.add(user)
    db.commit()
    return sync.create_job(db, user).id


def test_full_sync_then_incremental(db):
    job_id = _job(db)
    fake = FakeYouTube()
    sync.run_sync(job_id, "tok", client_factory=lambda _t: fake)
    db.expire_all()

    job = db.get(SyncJob, job_id)
    assert job.status == "done", job.message
    assert db.scalar(select(func.count()).select_from(Video)) == 2
    assert db.scalar(select(func.count()).select_from(RetentionPoint)) == 200
    assert db.scalar(select(func.count()).select_from(TranscriptSegment)) == 4
    assert db.scalar(select(func.count()).select_from(Comment)) == 2  # v2 has comments disabled
    v1 = db.scalar(select(Video).where(Video.youtube_id == "v1"))
    assert v1.is_short and v1.avg_view_pct == 90.0 and v1.retention_views == 5000

    # Second run: nothing stale, so retention/comments are not fetched again.
    fake2 = FakeYouTube()
    job2 = sync.create_job(db, db.get(User, job.user_id)).id
    sync.run_sync(job2, "tok", client_factory=lambda _t: fake2)
    assert fake2.retention_calls == []
    assert fake2.comment_calls == []


def test_expired_token_keeps_progress_and_resumes(db):
    job_id = _job(db)
    sync.run_sync(job_id, "tok", client_factory=lambda _t: FakeYouTube(expire_on_retention_of="v2"))
    db.expire_all()
    job = db.get(SyncJob, job_id)
    assert job.status == "partial"
    assert db.scalar(select(func.count()).select_from(Video)) == 2  # videos kept
    assert db.scalar(select(func.count()).select_from(RetentionPoint)) == 100  # v1 kept

    fake = FakeYouTube()
    job2 = sync.create_job(db, db.get(User, job.user_id)).id
    sync.run_sync(job2, "tok", client_factory=lambda _t: fake)
    assert fake.retention_calls == ["v2"]  # resumed only what was missing


def test_removed_videos_are_deleted(db):
    job_id = _job(db)
    sync.run_sync(job_id, "tok", client_factory=lambda _t: FakeYouTube(videos=("v1", "v2")))
    user_id = db.get(SyncJob, job_id).user_id
    job2 = sync.create_job(db, db.get(User, user_id)).id
    sync.run_sync(job2, "tok", client_factory=lambda _t: FakeYouTube(videos=("v1",)))
    db.expire_all()
    assert [v.youtube_id for v in db.scalars(select(Video))] == ["v1"]


def test_one_active_job_per_user(db):
    _job(db)
    user = db.scalar(select(User))
    with pytest.raises(sync.SyncConflict):
        sync.create_job(db, user)


def test_stale_jobs_are_swept(db):
    _job(db)
    assert sync.sweep_stale_jobs() == 1
    db.expire_all()
    assert db.scalar(select(SyncJob)).status == "interrupted"


def test_sync_endpoint_rejects_token_of_another_account(client, monkeypatch):
    monkeypatch.setattr("app.routers.account.YouTubeClient.token_email", lambda self: "someone@else.com")
    res = client.post("/api/v1/sync", headers={**auth("me@example.com"), "X-Google-Access-Token": "tok"})
    assert res.status_code == 403


def test_sync_endpoint_requires_google_token(client):
    assert client.post("/api/v1/sync", headers=auth("me@example.com")).status_code == 400


def test_thumbnail_analysis():
    from io import BytesIO

    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", (32, 32), (255, 0, 0)).save(buf, format="PNG")
    brightness, colors = sync.analyze_thumbnail_bytes(buf.getvalue())
    assert colors[0] == "#e00000"
    assert brightness > 50
