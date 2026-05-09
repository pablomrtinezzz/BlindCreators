# 👁️ BlindCreators: B2B AI-Driven Content Intelligence

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Frontend](https://img.shields.io/badge/Next.js-15-black.svg)](https://nextjs.org/)
[![Backend](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![AI Model](https://img.shields.io/badge/AI-Gemini%201.5%20Flash-orange.svg)](https://deepmind.google/technologies/gemini/)

> **Value Proposition**: A decoupled B2B SaaS ecosystem designed for high-performance content creators. It automates data ingestion from YouTube via OAuth 2.0, performs multi-tenant data modeling, and leverages LLMs to transform raw metrics into actionable growth strategies.

---

## 🏗️ System Architecture & Engineering
BlindCreators is built on a modern **Decoupled Architecture** featuring a real-time **ETL + RAG** (Retrieval-Augmented Generation) pipeline:

* **Frontend Client**: Built with Next.js 15 (App Router) and TailwindCSS, managing secure OAuth 2.0 sessions via NextAuth.js.
* **Backend REST API**: High-performance Python FastAPI server handling data processing, routing, and CORS-secured client communication.
* **Real-Time Extraction Layer**: User-triggered ingestion via YouTube Data API v3 utilizing active session access tokens.
* **AI Strategy Layer**: Implements a RAG pattern using **Gemini 1.5 Flash** to inject historical performance context into generative SEO and content planning tasks.

---

## 🛠️ Key Engineering Features
* **Multi-Tenant Isolation**: Relational SQLite architecture designed to segregate and secure data per user context (`user_email`).
* **Automated Data Pipelines**: Pandas-driven transformations that clean, format, and normalize raw YouTube API JSON dumps into structured SQL records in milliseconds.
* **Executive Dashboarding**: A premium UI/UX built with Recharts and Lucide-React, featuring dynamic, auto-refreshing KPI components.
* **Scalability**: Modular API design allows swapping the persistence layer (e.g., PostgreSQL for cloud deployment) or the LLM provider with minimal refactoring.

---

## 📂 Repository Structure
```text
BlindCreators/
├── backend/
│   ├── data/                 # Processed multi-tenant SQLite storage
│   ├── src/
│   │   ├── api.py            # FastAPI Application & Endpoints
│   │   ├── youtube_sync.py   # Real-time ETL Engine
│   │   └── ai_assistant.py   # Gemini Integration Engine
│   ├── requirements.txt      # Python dependency manifest
│   └── .env.example          # Backend credentials template
├── frontend/
│   ├── src/
│   │   ├── app/              # Next.js Application Router
│   │   └── components/       # Reusable UI & Charting logic
│   ├── package.json          # Node.js dependency manifest
│   └── .env.example          # Frontend credentials template
└── README.md

```

---

## 🚀 Getting Started

### Prerequisites

* Node.js (v18+) and Python (3.10+)
* API Keys for Google Cloud (OAuth Client ID & YouTube Data API v3) and Google AI Studio (Gemini).

### 1. Backend Setup (FastAPI)

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create a .env file and add your credentials
# GEMINI_API_KEY="your_gemini_key"
# YOUTUBE_API_KEY="your_youtube_api_key"

uvicorn src.api:app --reload

```

### 2. Frontend Setup (Next.js)

```bash
cd frontend
npm install

# Create a .env.local file and add your OAuth credentials
# GOOGLE_CLIENT_ID="your_oauth_client_id"
# GOOGLE_CLIENT_SECRET="your_oauth_client_secret"
# NEXTAUTH_SECRET="your_nextauth_secret"
# NEXTAUTH_URL="http://localhost:3000"

npm run dev

```

---

## 🤖 AI Intelligence Capabilities

* **Contextual SEO**: Generates highly clickable titles by analyzing the channel's historical top-performing content dynamically.
* **Audience Sentiment**: (In-development) Processes raw comment data to extract deep audience insights and video concepts.

---

## 🗓️ Strategic Roadmap

| Phase | Focus | Status |
| --- | --- | --- |
| **MVP** | Local ETL Pipeline & Static AI Logic | ✅ |
| **API** | Decoupled API transition (FastAPI) | ✅ |
| **SaaS** | Next.js, OAuth 2.0 & Real-time Multi-tenant Sync | ✅ |
| **Data** | Advanced RAG for Deep Audience Sentiment Analysis | 🗓️ |
| **Cloud** | Production Deployment (Vercel + Railway/Render) | 🗓️ |

---

**Lead Developer**: [Pablo Martínez Suárez](https://github.com/pablomrtinezzz)

```
