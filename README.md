
# 👁️ BlindCreators: B2B AI-Driven Content Intelligence

[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![AI Model](https://img.shields.io/badge/AI-Gemini%203%20Flash-orange.svg)](https://deepmind.google/technologies/gemini/)
[![Framework](https://img.shields.io/badge/Framework-Streamlit-FF4B4B.svg)](https://streamlit.io/)

> **Value Proposition**: A modular business intelligence ecosystem designed for high-performance content creators. It automates data ingestion from YouTube, performs statistical outlier-filtering, and leverages LLMs to transform raw metrics into actionable growth strategies.

---

## 🏗️ System Architecture & Engineering
BlindCreators is built on a robust **ETL + RAG** (Retrieval-Augmented Generation) pipeline:

*   **Extraction Layer**: High-concurrency ingestion via YouTuabe Data API v3.
*   **Analytics Engine**: Beyond raw views—it calculates **"True Performance"** by applying statistical normalization and filtering viral outliers using Median Percentiles.
*   **NLP Audience Mining**: Vector-based analysis (simulated via NLP clustering) of top-level comments to identify high-intent audience segments.
*   **AI Strategy Layer**: Implements a RAG pattern using **Gemini 3 Flash** to inject historical performance context into generative SEO and content planning tasks.

---

## 🛠️ Key Engineering Features
*   **Data Integrity**: Relational persistence using SQLite to track performance history and avoid API quota exhaustion.
*   **Statistical Cleansing**: Custom logic in `transform.py` to isolate organic growth from algorithmic anomalies.
*   **B2B Dashboarding**: A premium UI/UX built in Streamlit with custom branding for data-driven storytelling.
*   **Scalability**: Modular design allows swapping the persistence layer (e.g., PostgreSQL) or the LLM provider with minimal refactoring.

---

## 📂 Repository Structure
```text
BlindCreators/
├── data/
│   ├── raw/                # Non-structured JSON (API dumps)
│   └── database.sqlite     # Processed relational storage
├── src/
│   ├── extract.py          # Ingestion engine
│   ├── transform.py        # Feature Engineering & Normalization
│   ├── ai_assistant.py     # Gemini Integration (RAG Pattern)
│   └── app.py              # Analytical Dashboard
├── .streamlit/             # UI/UX Custom Branding
├── requirements.txt        # Dependency Manifest
└── .env.example            # Template for secure credentials

```

---

## 🚀 Getting Started

### Prerequisites

* Python 3.12+
* API Keys for Google Cloud (YouTube) and Google AI Studio (Gemini).

### Installation

1. **Clone & Setup**:
```bash
git clone [https://github.com/pablomrtinezzz/BlindCreators.git](https://github.com/pablomrtinezzz/BlindCreators.git)
cd BlindCreators
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt


```
2. **Environment**:
   Copy `.env.example` to `.env` and fill in your API keys.

---

## 🤖 AI Intelligence Capabilities
*   **Contextual SEO**: Generates titles by analyzing the top 10% of historically successful content.
*   **Gap Analysis**: Identifies "Audience Pain Points" by processing raw comment data through a multi-shot prompting strategy.

---

## 🗓️ Strategic Roadmap
| Phase | Focus | Status |
| :--- | :--- | :--- |
| **MVP** | ETL Pipeline & Core Analytics | ✅ |
| **Beta** | RAG Integration & Audience Mining | ✅ |
| **Scale** | FastAPI Backend + React Dashboard | 🗓️ |
| **Enterprise**| Multi-channel OAuth 2.0 Integration | 🗓️ |

---
**Lead Developer**: [Pablo Martínez Suárez](https://github.com/pablomrtinezzz)

