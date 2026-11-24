from datetime import date

import httpx
import pytest
import respx

from app.clients import youtube as yt_mod
from app.clients.youtube import YouTubeAuthError, YouTubeClient, YouTubeForbidden


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    # Make tenacity backoff instant.
    monkeypatch.setattr(YouTubeClient._get.retry, "sleep", lambda _s: None)  # type: ignore[attr-defined]


@respx.mock
def test_retries_server_errors_then_succeeds():
    route = respx.get(f"{yt_mod.DATA_API}/channels").mock(
        side_effect=[
            httpx.Response(503, json={"error": {"message": "busy"}}),
            httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": "UC1",
                            "snippet": {"title": "Chan", "thumbnails": {}},
                            "statistics": {"subscriberCount": "42"},
                            "contentDetails": {"relatedPlaylists": {"uploads": "UU1"}},
                        }
                    ]
                },
            ),
        ]
    )
    ch = YouTubeClient("tok").get_my_channel()
    assert ch and ch.uploads_playlist == "UU1" and ch.subscribers == 42
    assert route.call_count == 2


@respx.mock
def test_401_raises_auth_error_without_retry():
    route = respx.get(f"{yt_mod.DATA_API}/channels").mock(return_value=httpx.Response(401, json={}))
    with pytest.raises(YouTubeAuthError):
        YouTubeClient("tok").get_my_channel()
    assert route.call_count == 1


@respx.mock
def test_comments_disabled_is_forbidden_with_reason():
    respx.get(f"{yt_mod.DATA_API}/commentThreads").mock(
        return_value=httpx.Response(403, json={"error": {"errors": [{"reason": "commentsDisabled"}]}})
    )
    with pytest.raises(YouTubeForbidden) as exc:
        list(YouTubeClient("tok").iter_comments("v", 10))
    assert exc.value.reason == "commentsDisabled"


@respx.mock
def test_upload_ids_paginate():
    respx.get(f"{yt_mod.DATA_API}/playlistItems").mock(
        side_effect=[
            httpx.Response(
                200, json={"items": [{"contentDetails": {"videoId": "a"}}], "nextPageToken": "p2"}
            ),
            httpx.Response(200, json={"items": [{"contentDetails": {"videoId": "b"}}]}),
        ]
    )
    assert YouTubeClient("tok").list_upload_ids("UU1", 10) == ["a", "b"]


@respx.mock
def test_video_metrics_falls_back_without_engaged_views():
    respx.get(yt_mod.ANALYTICS_API).mock(
        side_effect=[
            httpx.Response(400, json={"error": {"message": "Unknown identifier (engagedViews)"}}),
            httpx.Response(
                200,
                json={
                    "columnHeaders": [
                        {"name": "video"},
                        {"name": "views"},
                        {"name": "averageViewPercentage"},
                    ],
                    "rows": [["v1", 10, 88.5]],
                },
            ),
        ]
    )
    out = YouTubeClient("tok").video_metrics(date(2025, 1, 1), date(2025, 2, 1))
    assert out["v1"]["averageViewPercentage"] == 88.5
