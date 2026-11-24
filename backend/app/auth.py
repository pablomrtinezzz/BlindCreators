"""Request authentication.

The browser never talks to this API directly. The Next.js server (which owns the NextAuth
session) proxies every call and attaches a short-lived HS256 JWT signed with
BACKEND_JWT_SECRET. The user identity is derived *only* from that token.
"""

from __future__ import annotations

import logging
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db, utcnow
from app.models import User

logger = logging.getLogger(__name__)

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


def decode_token(token: str, settings: Settings) -> dict:
    try:
        claims = jwt.decode(
            token,
            settings.backend_jwt_secret,
            algorithms=["HS256"],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iat", "sub", "email"]},
            leeway=10,
        )
    except jwt.PyJWTError as exc:
        logger.info("Rejected token: %s", type(exc).__name__)
        raise _UNAUTHORIZED from exc
    if claims.get("email_verified") is not True:
        raise _UNAUTHORIZED
    return claims


def current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise _UNAUTHORIZED
    claims = decode_token(authorization.split(" ", 1)[1].strip(), settings)

    email = str(claims["email"]).strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email)
        db.add(user)
    user.name = str(claims.get("name") or user.name or email.split("@")[0])[:200]
    user.image = claims.get("picture") or user.image
    user.last_seen_at = utcnow()
    db.commit()
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def google_access_token(
    x_google_access_token: Annotated[str | None, Header()] = None,
) -> str:
    if not x_google_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google access token missing. Sign out and sign in again.",
        )
    return x_google_access_token
