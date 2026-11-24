import os
import tempfile
import time
from pathlib import Path

import jwt
import pytest

_TMP = Path(tempfile.mkdtemp(prefix="blindcreators-tests-"))
os.environ.update(
    {
        "ENVIRONMENT": "test",
        "DATABASE_URL": f"sqlite:///{_TMP / 'test.sqlite'}",
        "CHROMA_PATH": str(_TMP / "chroma"),
        "BACKEND_JWT_SECRET": "test-secret-" + "x" * 40,
        "GEMINI_API_KEY": "",
        "TRANSCRIPTS_ENABLED": "true",
        "MIN_VIEWS_FOR_RETENTION": "100",
    }
)

from fastapi.testclient import TestClient  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import SyncJob, User, Video  # noqa: E402


def make_token(
    email: str, *, secret: str | None = None, exp_in: int = 300, verified: bool = True, **extra
) -> str:
    s = get_settings()
    now = int(time.time())
    claims = {
        "sub": email,
        "email": email,
        "email_verified": verified,
        "name": email.split("@")[0],
        "iss": s.jwt_issuer,
        "aud": s.jwt_audience,
        "iat": now,
        "exp": now + exp_in,
        **extra,
    }
    return jwt.encode(claims, secret or s.backend_jwt_secret, algorithm="HS256")


def auth(email: str) -> dict:
    return {"Authorization": f"Bearer {make_token(email)}"}


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _clean_db(client):
    yield
    with SessionLocal() as db:
        db.query(SyncJob).delete()
        db.query(Video).delete()
        db.query(User).delete()
        db.commit()
    from app import ratelimit

    ratelimit.reset()


@pytest.fixture
def db():
    with SessionLocal() as s:
        yield s
