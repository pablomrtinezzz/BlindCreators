from tests.conftest import auth, make_token


def test_health_is_public(client):
    assert client.get("/api/v1/health").json()["status"] == "ok"


def test_missing_token_is_rejected(client):
    assert client.get("/api/v1/me").status_code == 401


def test_bad_signature_is_rejected(client):
    tok = make_token("a@example.com", secret="another-secret-" + "y" * 40)
    assert client.get("/api/v1/me", headers={"Authorization": f"Bearer {tok}"}).status_code == 401


def test_expired_token_is_rejected(client):
    tok = make_token("a@example.com", exp_in=-120)
    assert client.get("/api/v1/me", headers={"Authorization": f"Bearer {tok}"}).status_code == 401


def test_unverified_email_is_rejected(client):
    tok = make_token("a@example.com", verified=False)
    assert client.get("/api/v1/me", headers={"Authorization": f"Bearer {tok}"}).status_code == 401


def test_wrong_audience_is_rejected(client):
    tok = make_token("a@example.com", aud="someone-else")
    assert client.get("/api/v1/me", headers={"Authorization": f"Bearer {tok}"}).status_code == 401


def test_valid_token_creates_user(client):
    res = client.get("/api/v1/me", headers=auth("New.User@Example.com"))
    assert res.status_code == 200
    assert res.json()["email"] == "new.user@example.com"


def test_user_email_query_param_is_ignored(client):
    res = client.get("/api/v1/me?user_email=victim@example.com", headers=auth("me@example.com"))
    assert res.json()["email"] == "me@example.com"


def test_ai_routes_require_auth(client):
    assert client.post("/api/v1/ai/ask", json={"question": "hola que tal"}).status_code == 401


def test_debug_routes_disabled_by_default(client):
    assert client.get("/api/v1/debug/stats", headers=auth("a@example.com")).status_code == 404
