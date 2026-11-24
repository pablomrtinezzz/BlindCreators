# BlindCreators

**See the second your viewers leave.** BlindCreators shows retention analytics for YouTube creators, built for Shorts. It lines up every line of your script with the audience retention curve. It also finds weak hooks and digs through your comments for your next video idea.

Right now it is an internal tool, tested on our own channels. The plan is to show that it improves a channel's numbers before offering it to other creators.

---

## What it does

| Screen | Question it answers |
|---|---|
| **Overview** | What should I fix or repeat next? Shows action cards (weakest recent hook, best day to publish, the video with the most comments), median-based KPIs and median views per publish day. |
| **Shorts Lab** | How does each Short's hook compare with how long people keep watching? Has a scatter plot of the hook (retention at 3 s) against % viewed, a looping-Shorts count and a ranked table with each Short's opening line. |
| **Video workspace** | Where exactly do people leave, and on which sentence? Shows the retention curve against the channel median, the script line by line with how many viewers each line lost, the steepest drops, a *Hook doctor* (AI rewrites of your opening) and the comments. |
| **Audience** | What is the audience asking for? Has an AI summary of themes, recurring questions and video ideas (each with a ready-to-film hook), plus a search over your comments. |
| **Ideas** | Gives title suggestions modelled on your own best uploads of the same format. |
| **Ask your channel** | Answers questions about your channel from your own scripts and comments (RAG), with sources. |

### How the analytics work, and their limits
- The **retention curve** comes from the YouTube Analytics API as 100 points (`audienceWatchRatio`). It can go above 100% when viewers replay or loop a Short.
- **Script lines** are built from caption snippets. They are merged into sentence-like segments of up to 6 s. A line is a *leak* when it loses viewers 1.5× faster than the video's average rate.
- The API does not say how many viewers each point of the curve is based on. Curves from videos under `MIN_VIEWS_FOR_RETENTION` views (default 1,000) are marked as noisy and left out of channel medians.
- For a 30 s Short each curve point covers 0.3 s, which is finer than caption timing (±1 s). **Treat line-level deltas as hints for diagnosis, not as proof of cause.**
- Channel KPIs are **medians**, so a single viral outlier cannot skew them.

## Architecture

```
Browser ──► Next.js 16 (frontend/)
              ├─ NextAuth (Google OAuth, read-only scopes)
              └─ /api/backend/* proxy ──► FastAPI (backend/)   [signed 2-min JWT]
                                            ├─ SQLite (SQLAlchemy 2 + Alembic)
                                            ├─ ChromaDB (one collection per user)
                                            ├─ YouTube Data API v3 + Analytics API v2
                                            └─ Gemini (generation + 768-d embeddings)
```

### Security model
- **The browser never talks to the API directly** and never sees a Google token. The Next.js server reads the encrypted NextAuth cookie and signs a 2-minute HS256 JWT (`BACKEND_JWT_SECRET`). The API takes the user's identity **only** from that token.
- The Google access token goes to the API only on `POST /sync`. There the API checks with Google that the token belongs to the same verified email.
- OAuth scopes are read-only: `youtube.readonly` and `yt-analytics.readonly`.
- All data is stored under `users.id` with `ON DELETE CASCADE`, and each user has their own vector collection. Tests check that one user cannot read another user's data.
- `DELETE /api/v1/me/data` (in **Settings**) wipes everything stored for a user.
- AI endpoints are rate-limited per user. Untrusted text (titles, scripts, comments) is wrapped as data in every prompt, so the model does not follow instructions hidden inside it.
- Debug routes are off unless you set `ENABLE_DEBUG_ROUTES=true`. Production refuses to start with them on.

### Sync design
- **Incremental and resumable.** Each phase fetches only what is missing or stale and commits after every video. If a sync is interrupted or the token expires, the job ends as `partial`, and running it again continues where it stopped.
- Phases run in this order: channel → videos (paginated, batched 50 at a time) → analytics → retention (refetched every 7 days) → scripts → comments (refetched when the count changes) → thumbnails → AI index (only changed documents are re-embedded).
- At most one active job per user. A partial unique index in the database enforces this. Jobs left running when the server restarts are marked `interrupted`.
- YouTube API quota is not a practical limit. A full sync costs about 30 units plus comments, out of 10,000 per day.

## Running locally

Requirements: Python 3.12 with [uv](https://docs.astral.sh/uv/), and Node 22.

```bash
# 1. Secrets
cp .env.example .env                         # fill BACKEND_JWT_SECRET and GEMINI_API_KEY
#    frontend/.env.local needs GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, NEXTAUTH_SECRET,
#    NEXTAUTH_URL, BACKEND_URL and the same BACKEND_JWT_SECRET (see .env.example).

# 2. API: runs migrations on startup
cd backend
uv sync
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 3. Web
cd ../frontend
npm install
npm run dev                                  # http://localhost:3000 (port pinned in package.json)
```

In Google Cloud, enable the **YouTube Data API v3** and the **YouTube Analytics API**. Add `http://localhost:3000/api/auth/callback/google` as an authorized redirect URI.

### Quality gates (CI runs these on every push)
```bash
cd backend  && uv run ruff check . && uv run ruff format --check . && uv run pytest
cd frontend && npm run lint && npx tsc --noEmit && npm run build
```

## Project layout
```
backend/
  app/
    main.py            app factory, CORS, error handling, startup migrations
    config.py          all settings (pydantic-settings)
    auth.py            JWT verification → current user
    db.py, models.py   single SQLAlchemy engine/session, ORM schema
    clients/           youtube.py, gemini.py, captions.py, vectors.py
    services/          sync.py, insights.py, retention.py (pure maths), rag.py, ai.py, text.py
    routers/           account.py (me, sync, jobs), analytics.py, ai.py
  alembic/             migrations
  tests/               auth, tenant isolation, retention maths, YouTube client, sync
frontend/src/
  app/(app)/           overview, shorts, videos/[id], audience, ideas, ask, settings
  app/api/backend/     authenticated proxy to the API
  app/login/           sign-in
  components/          shell, UI primitives, charts
  lib/                 auth options, API client, types, formatters
```

## Roadmap
1. **Baseline, then experiment.** Record medians for the last 20–30 Shorts (% viewed, hook at 3 s, subscribers per 1k views). Then change one thing at a time, with about 15 Shorts per variant, and fix the success metric before you start.
2. **Before offering it to other creators:**
   - Replace caption scraping (`youtube-transcript-api`) with the official captions API or with script upload.
   - Review the YouTube API Services data-retention policy.
   - Complete Google OAuth verification for the sensitive scopes.
3. **Postgres and a worker** only when the API runs as more than one instance or has sustained concurrent writers. `DATABASE_URL` and Alembic already make that switch cheap, and pgvector could then replace Chroma.
