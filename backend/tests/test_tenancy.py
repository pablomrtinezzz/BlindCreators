from app.models import SyncJob
from tests.conftest import auth
from tests.factories import seed_user_with_video


def test_users_only_see_their_own_videos(client, db):
    seed_user_with_video(db, "alice@example.com", "alice_vid")
    seed_user_with_video(db, "bob@example.com", "bob_vid")

    res = client.get("/api/v1/videos", headers=auth("alice@example.com"))
    ids = [v["id"] for v in res.json()["videos"]]
    assert ids == ["alice_vid"]

    assert client.get("/api/v1/videos/bob_vid", headers=auth("alice@example.com")).status_code == 404
    assert client.get("/api/v1/videos/bob_vid/comments", headers=auth("alice@example.com")).status_code == 404


def test_top_comments_are_scoped(client, db):
    seed_user_with_video(db, "alice@example.com", "alice_vid")
    seed_user_with_video(db, "bob@example.com", "bob_vid")
    data = client.get("/api/v1/comments/top", headers=auth("bob@example.com")).json()
    assert {c["video_id"] for c in data["comments"]} == {"bob_vid"}
    assert data["total"] == 1


def test_jobs_are_scoped(client, db):
    alice = seed_user_with_video(db, "alice@example.com", "alice_vid")
    db.add(SyncJob(id="job-alice", user_id=alice.id, status="done"))
    db.commit()
    assert client.get("/api/v1/sync/jobs/job-alice", headers=auth("bob@example.com")).status_code == 404
    assert client.get("/api/v1/sync/jobs/job-alice", headers=auth("alice@example.com")).status_code == 200


def test_delete_my_data_only_touches_me(client, db):
    seed_user_with_video(db, "alice@example.com", "alice_vid")
    seed_user_with_video(db, "bob@example.com", "bob_vid")
    assert client.delete("/api/v1/me/data", headers=auth("alice@example.com")).status_code == 204
    assert client.get("/api/v1/videos", headers=auth("alice@example.com")).json()["videos"] == []
    assert len(client.get("/api/v1/videos", headers=auth("bob@example.com")).json()["videos"]) == 1


def test_video_detail_maps_script_to_curve(client, db):
    seed_user_with_video(db, "alice@example.com", "alice_vid")
    data = client.get("/api/v1/videos/alice_vid", headers=auth("alice@example.com")).json()
    assert len(data["curve"]) == 100
    seg = data["segments"][0]
    assert seg["text"] == "Secret hook line"
    assert seg["delta_pct"] < 0
    assert data["video"]["hook_retention_pct"] == 95.0


def test_dashboard_and_shorts_lab(client, db):
    seed_user_with_video(db, "alice@example.com", "alice_vid")
    dash = client.get("/api/v1/dashboard", headers=auth("alice@example.com")).json()
    assert dash["kpis"]["videos"] == 1
    lab = client.get("/api/v1/shorts/lab", headers=auth("alice@example.com")).json()
    assert lab["shorts"][0]["first_line"] == "Secret hook line"
    assert len(lab["median_curve"]) == 100
