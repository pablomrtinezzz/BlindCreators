# BlindCreators — AI-Driven YouTube Content Intelligence

[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15-black.svg)](https://nextjs.org/)
[![Gemini](https://img.shields.io/badge/AI-Gemini%202.5%20Flash-orange.svg)](https://deepmind.google/technologies/gemini/)
[![ChromaDB](https://img.shields.io/badge/Vector%20DB-ChromaDB-7B2FBE.svg)](https://www.trychroma.com/)

> B2B SaaS platform that transforms a YouTube channel into a fully queryable knowledge base. It ingests video metadata, transcripts, viewer comments, and audience retention curves — then makes everything searchable via semantic RAG chat powered by Gemini.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Next.js 15 Frontend                    │
│  Dashboard · Transcripts · Comments · Retention · RAG Chat  │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP / REST
 ┌────────────────────────▼──────────────────────────────────┐
 │                    FastAPI Backend                        │
 │                                                           │
 │  ┌─────────────┐   ┌──────────────────────────────────┐   │
 │  │ Quick Sync  │   │      Extended Pipeline           │   │
 │  │ (sync'd)    │   │   (FastAPI BackgroundTasks)      │   │
 │  └─────────────┘   │                                  │   │
 │                    │  Thumbnails → Transcripts →      │   │
 │                    │  Comments  → Retention →         │   │
 │                    │  Embeddings (ChromaDB)           │   │
 │                    └──────────────────────────────────┘   │
 │                                                           │
 │  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐    │
 │  │  SQLite +    │  │  ChromaDB    │  │  Gemini API   │    │
 │  │  SQLAlchemy  │  │  (local,     │  │  2.5 Flash +  │    │
 │  │  (WAL mode)  │  │  cosine)     │  │  embedding-   │    │
 │  └──────────────┘  └──────────────┘  │  001 (3072d)  │    │
 │                                      └───────────────┘    │
 └───────────────────────────────────────────────────────────┘
                             │
              Google OAuth 2.0 (multi-tenant)
                  YouTube Data API v3
                YouTube Analytics API v2
```

---

## Features

### Data Pipeline (async, per-user)
| Phase | What it does |
|---|---|
| **Thumbnails** | Downloads thumbnail, extracts dominant colours + brightness via PIL |
| **Transcripts** | Fetches subtitles via `youtube-transcript-api`, chunks into 150-word segments with timestamps |
| **Comments** | Mines top-level comments + replies via `commentThreads` API (up to 200 per video) |
| **Retention** | Pulls `audienceWatchRatio` curves from YouTube Analytics API v2 |
| **Embeddings** | Embeds transcript chunks + comment blocks into ChromaDB using `gemini-embedding-001` (3072 dims) |

### Dashboard pages
- **Analytics** — KPIs, views heatmap, hall of fame
- **Transcripts** — Full text with clickable timestamp links to YouTube
- **Comment Mining** — Top comments across the channel sorted by engagement; diagnostic panel for API access issues
- **Audience Retention** — Per-video and channel-average retention curves (Recharts); diagnostic panel for Analytics API
- **RAG Chat** — Gemini 2.5 Flash chat grounded in transcripts + viewer comments; sources panel distinguishes transcript timestamps from comment blocks
- **AI Tools** — SEO title generation, audience insight mining
- **Settings** — Account info, OAuth scope status, re-index button

### Technical highlights
- **Multi-tenant**: every DB row and ChromaDB document is scoped by `user_email`
- **Session isolation**: each extractor creates and closes its own SQLAlchemy session — no cross-video rollback cascades
- **Token auto-refresh**: NextAuth JWT callback refreshes Google OAuth tokens before expiry using `refresh_token`
- **Granular error diagnostics**: debug endpoints hit the YouTube API directly and return the full raw JSON (error reason, HTTP status), surfaced in the UI
- **Job progress**: `SyncJob` table + polling component shows phase-by-phase progress in real time

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15 (App Router), TypeScript, Tailwind CSS, Recharts |
| Backend | FastAPI, SQLAlchemy 2.x, SQLite (WAL), Pydantic |
| AI / Embeddings | Google Gemini 2.5 Flash, `gemini-embedding-001` (3072d) |
| Vector DB | ChromaDB (local persistent, cosine similarity) |
| Auth | NextAuth.js with Google OAuth 2.0 |
| APIs | YouTube Data API v3, YouTube Analytics API v2 |
| Infra | FastAPI BackgroundTasks (no Celery/Redis required) |

---

## Repository Structure

```
BlindCreators/
├── backend/
│   ├── src/
│   │   ├── api.py                  # FastAPI app — 20+ endpoints
│   │   ├── pipeline.py             # Async extended pipeline orchestrator
│   │   ├── ai_assistant.py         # RAG query + Gemini integration
│   │   ├── youtube_sync.py         # Quick video metadata sync
│   │   ├── extractors/
│   │   │   ├── transcripts.py      # youtube-transcript-api v1.x
│   │   │   ├── comments.py         # commentThreads with 403 reason parsing
│   │   │   ├── retention.py        # YouTube Analytics API
│   │   │   └── thumbnails.py       # PIL colour analysis
│   │   ├── models/
│   │   │   └── database.py         # SQLAlchemy models + init_db
│   │   └── rag/
│   │       ├── chroma_client.py    # ChromaDB persistent client
│   │       └── embedder.py         # Gemini embedding-001 batch embedder
│   ├── data/
│   │   ├── database.sqlite         # SQLite database (gitignored)
│   │   └── chroma/                 # ChromaDB storage (gitignored)
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── api/auth/           # NextAuth route (Google OAuth + refresh)
│       │   ├── comments/           # Comment mining page
│       │   ├── transcripts/        # Transcript viewer
│       │   ├── retention/          # Retention curves page
│       │   ├── rag/                # RAG chat page
│       │   ├── settings/           # Account & data tools
│       │   └── ai_tools/           # SEO title generator
│       └── components/
│           ├── Sidebar.tsx
│           ├── TopHeader.tsx       # Full Sync button + job progress
│           └── SyncProgress.tsx    # Phase progress panel (polling)
└── .env.example
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+
- Google Cloud project with these APIs enabled:
  - YouTube Data API v3
  - YouTube Analytics API v2
- Google OAuth 2.0 credentials with scopes:
  - `youtube.readonly`
  - `youtube.force-ssl` (required for reading comments)
  - `yt-analytics.readonly`
- Gemini API key (Google AI Studio)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env    # fill in your keys
uvicorn src.api:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp ../.env.example .env.local   # fill in GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, NEXTAUTH_SECRET
npm run dev
```

Open [http://localhost:3000](http://localhost:3000), sign in with Google, and click **Full Sync**.

---

## Environment Variables

```env
# Google OAuth
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
NEXTAUTH_SECRET=
NEXTAUTH_URL=http://localhost:3000

# Gemini
GEMINI_API_KEY=
```

---

## Roadmap

| Phase | Status |
|---|---|
| Video metadata ETL + analytics dashboard | Done |
| Google OAuth multi-tenant auth + token refresh | Done |
| Transcript extraction + chunked indexing | Done |
| Comment mining + engagement ranking | Done |
| Audience retention curves (Analytics API) | Done |
| ChromaDB vector store + Gemini embeddings | Done |
| RAG Chat (transcripts + comments) | Done |
| Thumbnail visual analysis (PIL) | Done |
| PostgreSQL migration for production | Planned |
| Multi-channel support per user | Planned |
| Scheduled background sync (cron) | Planned |

---

**Lead Developer**: [Pablo Martínez Suárez](https://github.com/pablomrtinezzz)
