# 🏥 HealthValidator.ai

**AI-Powered Healthcare Provider Data Validation, Enrichment & Governance Platform**

A cutting-edge full-stack application designed to automate the onboarding, validation, enrichment, and governance of healthcare provider directory data. It leverages real-time NPI Registry verifications, Large Language Model (LLM) powered semantic analysis (Groq / Llama 3.3 70B), autonomous web scraping algorithms, and multi-modal provider interactions (SMTP Emails, Twilio AI Voice Calls) within a single unified pipeline. 

---

## 📑 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [AI Agents Ecosystem](#ai-agents-ecosystem)
- [Data Validation & Enrichment Flow](#data-validation--enrichment-flow)
- [Database Schema](#database-schema)
- [Technology Stack](#technology-stack)
- [API Reference](#api-reference)
- [Frontend Modules](#frontend-modules)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)

---

## 🎯 Overview

Healthcare payers, networks, and organizations heavily rely on accurate, up-to-date provider directories. The traditional approach—manual credentialing and validation—is painstakingly slow, prone to human error, and completely unscalable. **HealthValidator.ai** disrupts this paradigm by taking a multi-layered, automated approach:

1. **Intelligent Ingestion**: Support for manual entries, CSV bulk uploads, and OCR-based PDF/Image data extraction.
2. **Deterministic & Semantic Validation**: Compares ingested data against the official **NPPES NPI Registry** using classical fuzzy matching (Levenshtein, Jaccard) paired with field-by-field LLM semantic analysis.
3. **Autonomous Enrichment**: Fills missing data gaps by scraping the open web (DuckDuckGo + Selenium headless Chrome) and verifying emails against the **Hunter.io Email API**.
4. **Multi-Modal Verification**: Engages providers directly when data confidence is low through **Twilio AI Voice Calls** (with NPI keypad verification and speech-to-text updates) or **Email Verification Portals**.
5. **Human-in-the-Loop Review**: Intuitive dashboard displaying confidence scores, side-by-side diff table comparisons, and an immutable audit trail for governance.
6. **Geospatial Intelligence**: Visualizes provider distributions on an interactive US map equipped with a native AI chat panel that has contextual awareness of the current view and a ReAct agent mapping network adequacy gaps.

---

## ✨ Key Features

- **Document Parsing via OCR & LLM**: Pytesseract extracts raw text from user-uploaded PDFs/images, and Llama 3 structures it into rigorous JSON schemas.
- **Dynamic Scoring Mechanism**: Calculates an overall trust score based on weighted criteria (e.g., matching NPIs carry more weight than matching phone strings). Profiles falling below a 70% threshold are flagged as "Needs Review."
- **Twilio AI Voice Call Verification**: Deploys an AI voice agent (`CallVerificationAgent`) calling practitioners to verbally confirm/update their details. Captures text via speech recognition, analyzes it using an LLM to build a JSON diff, and live-streams events to the frontend via Server-Sent Events (SSE).
- **Comprehensive Audit Trail**: Every modification—whether coming from the system, the AI Enrichment agent, or a manual review—is appended to `provider_audit_log` detailing old/new values, the exact timestamp, and the actor.
- **LLM-Powered Map Chat**: Users can converse with the AI regarding the current states highlighted on the React map visualizations, providing instant insights regarding geospatial network adequacies.

---

## 🏗 System Architecture

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (React 19)                           │
│  ┌────────────┐ ┌─────────────┐ ┌────────────────┐ ┌─────────────────┐  │
│  │ Onboarding │ │  Dashboard  │ │ Provider Detail│ │ US Map + Chat   │  │
│  │ (CSV/OCR)  │ │ (Analytics) │ │ (Manual Review)│ │ (Geo Analytics) │  │
│  └──────┬─────┘ └──────┬──────┘ └───────┬────────┘ └────────┬────────┘  │
│         │              │                │                   │           │
│         └──────────────┴────────────────┴───────────────────┘           │
│                                │ REST API + WebSockets/SSE              │
└────────────────────────────────┼────────────────────────────────────────┘
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      BACKEND (FastAPI + Uvicorn)                        │
│  ┌───────────────┐ ┌─────────────────┐ ┌─────────────────────────────┐  │
│  │ main.py       │ │ services.py     │ │ models.py (SQLAlchemy ORM)  │  │
│  │ (Routers/SSE) │ │(Business Logic) │ │ database.py (Asyncpg)       │  │
│  └───────┬───────┘ └────────┬────────┘ └──────────────┬──────────────┘  │
│          │                  │                         │                 │
│  ┌───────┴──────────────────┴─────────────────────────┴──────────────┐  │
│  │                        AGENTIC ECOSYSTEM                          │  │
│  │ ┌────────────┐ ┌────────────┐ ┌───────────┐ ┌─────────────────┐   │  │
│  │ │ Extractor  │ │ Enrichment │ │ Email Bot │ │ Twilio Call Bot │   │  │
│  │ └─────┬──────┘ └─────┬──────┘ └─────┬─────┘ └────────┬────────┘   │  │
│  └───────┼──────────────┼──────────────┼────────────────┼────────────┘  │
└──────────┼──────────────┼──────────────┼────────────────┼───────────────┘
           │              │              │                │
┌──────────▼────┐ ┌───────▼──────┐ ┌─────▼──────┐ ┌───────▼───────────┐
│ Groq LLM API  │ │ DuckDuckGo + │ │ Gmail SMTP │ │ Twilio Voice API  │
│ (Llama 3 70B) │ │ Hunter.io    │ │ Server     │ │ (Webhooks/Audio)  │
└───────────────┘ └──────────────┘ └────────────┘ └───────────────────┘
```

---

## 🤖 AI Agents Ecosystem

The system delegates responsibilities to isolated autonomous agents configured to handle robust external data extraction and interfacing:

1. **`extractor_agent.py`**: Operates on unstructured inputs. Bridges OCR libraries to read byte streams and feeds plaintext segments to Llama 3 for structured extraction.
2. **`enrichment_agent_v0.py`**: Navigates the web contextually. For records missing websites or email addresses, this agent conducts sequential DuckDuckGo lookups, deploys headless Chrome to scrape textual context, unravels domains, and feeds them to Hunter.io.
3. **`email_agent.py`**: Handles asynchronous SMTP operations. Formats secure 1-time JWT token verification links directing providers to a dedicated External Portal to self-verify data.
4. **`call_agent.py`**: Integrating Twilio VoiceResponse (TwiML). Conducts interactive phone calls: (a) verifies identity via Keypad NPI entry, (b) asks open-ended questions about practice info, (c) intercepts speech results, (d) structurally extracts variables via the LLM, and (e) applies exact updates to the database!
5. **`network_agent.py`**: A domain-specific ReAct agent dynamically parsing geospatial DB logic and generating insights regarding provider scarcities in rural parameters.

---

## 🔄 Data Validation & Enrichment Flow

### 1️⃣ Ingestion & Normalization
Users submit via JSON forms, CSV batch tools, or upload standard document formats. The API catches raw inputs, caches them in `raw_provider_submissions`.

### 2️⃣ Validation Matrix
- **Registry API Sync**: System fetches NPI API.
- **Fuzzy Math**: Evaluates Levenshtein similarities for Names. Jaccard tokenization for Addresses.
- **Semantic Mapping**: Prompts Llama 3 to analyze nuances (e.g., "M.D." vs "Medical Doctor") and maps individual flags per column attributes.
- **Conclusion**: Data sets graded out of 100 on a confidence metric.

### 3️⃣ Auto-Enrichment (If Applicable)
If the DB detects hollow values (e.g. Missing `email` or `telehealth` bools), the Enrichment node queues the NPI. It explores contextual breadcrumbs online, returning structured schema elements accompanied by origin citations.

### 4️⃣ Verification Modals (Resolving Conflicts)
If System flags `< 70%` accuracy, users prompt AI Calls or Verify Emails. Modals expose Side-by-Side differences between:
- "Submitted Data" vs "NPPES Truth Data" vs "Web Enriched Data".

Once manually approved or verified externally by the provider, the status bumps from `Needs Review` -> `Verified` globally.

---

## 🗄 Database Schema

Leverages **PostgreSQL** via non-blocking `asyncpg` bindings.

| Core Table | Function / Scope |
|---|---|
| `providers_master_per` | Primary Index mapping `NPI` (PK), Names, Phones, Emails, Addresses. |
| `providers_master_prof` | Maps `NPI` (FK) to Practice Name, Specialties, Taxonomy, Telehealth readiness, language traits. |
| `providers_master_meta` | Internal application state. Tracks granular confidence % mapping strings, system `status`, and external verification tokens. |
| `raw_provider_submissions`| Complete unmutated original data inputs mapped against exact NPI API raw responses natively. |
| `provider_audit_log` | High-fidelity append-only ledger tracking `field_name`, `old_value`, `new_value`, `source_type` and Timestamp. |
| `market_expansion` | Analytical caching layers measuring zip-level patient demands mapped to geographic network adequacies. |

---

## 💻 Technology Stack

### Backend Environment
- **Core**: Python 3.10+, FastAPI framework, Uvicorn ASGI Server.
- **Database**: PostgreSQL asynchronously managed natively via SQLAlchemy 2.0 ORM tools.
- **Scraping Toolkit**: Selenium / WebDriver-Manager.
- **Integrations**: Twilio Python SDK, Tesseract OCR binaries, PyPDF.

### LLM Infrastructures
- **Engine**: Groq Cloud accelerated inference. Models typically default to Meta's open weights (`Llama-3-70b-8192` or variant).
- **Tooling**: LangChain core templates / formatting configurations.

### Frontend Application
- **Core**: React 19, custom hook infrastructures, styled completely dynamically.
- **Motion Patterns**: Framer Motion (page transitions, staggering micro-interactions).
- **Mapping**: `react-simple-maps` wrapped with `D3.js` mathematical scales formatting geoJSON topologies.
- **Comms**: Server-Sent Events hooks for streaming Twilio webhooks cleanly into UI banners.

---

## 🔌 API Reference

*(Brief subset of critical system endpoints running on Port 8000)*

- **Core Pipelines**:
  - `POST /submit` - Pushes JSON into validation algorithms.
  - `POST /extract` - Ingests `.pdf`/`.png` yielding extracted structured maps.
  - `POST /onboard/csv` - Fast-track unthrottled batch queues mapping external provider files.
- **Agent Triggers**:
  - `POST /enrich/{npi}` - Dispatches headless instance grabbing DuckDuckGo results for targeted provider.
  - `POST /verify-email/{npi}` - Distributes tokenized SMTP verifier packets.
  - `POST /twilio/call/{npi}` - Bootstraps Twilio agent placing live IVR calls to the designated mobile number via ngrok channels.
- **Data Layers**:
  - `GET /providers` - Global fetched indices.
  - `GET /providers/{npi}` - Drill down returning `_per`, `_prof`, `_meta` mapped JSONs.
  - `GET /audit/{npi}` - Exposes full audit histories.
- **Analysis Engine**:
  - `POST /analyze/chat` - LLM contextual conversational router.

---

## 🎨 Frontend Modules

1. **Dashboard UI** - A high-polish card-driven interface segmenting profiles by risk / review requirements. Auto-refreshes data blocks dynamically avoiding re-renders. 
2. **Onboarding Integration** - Incorporates robust pre-fills bridging raw file byte uploads cleanly toward the ultimate input form. Post upload immediately routes toward the Profile view or Map depending on batch volume.
3. **Manual Review Console** - Optimized for Data Stewards comparing divergent columns (Old vs New vs Canonical). Implements accessible, tight-spaced semantic components mitigating scrolling fatigue.
4. **Geo Charting Views** - Vector mapped state topologies visually delineating provider saturation vs shortage locales interactively. 

---

## 🚀 Getting Started

### Prerequisites
- Node.js 18.x
- Python 3.10 or higher
- PostgreSQL Server 14+
- Tesseract OCR Native Binaries (Crucial for Images)

### 1. Database Sockets
```bash
# Provision root DB natively via PSQL
createdb HealthCare
# Alter schema manually if bypassing declarative base implementations
psql -d HealthCare -f Backend/Tables/db.sql
```

### 2. Backend Orchestration
```bash
# Resolve and map standard python requirements
pip install -r requirements.txt

# Boot the API server in developer reflection mode
cd Backend
uvicorn main:app --reload --port 8000
```

### 3. Frontend Compilation
```bash
# Node module resolutions
cd frontend
npm install
# Ignite the react runtime
npm start
```
*Application lives structurally at `http://localhost:3000`*

---

## 🔒 Environment Variables

Store in root `.env` mapping local machine parameters:

```env
# Essential Paths
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/HealthCare

# Language Model Configurations
GROQ_API_KEY=gsk_my_groq_api_token
GEMINI_API_KEY=legacy_gemini_fallback_optional

# Enrichment APIs
HUNTER_API=hunter.io_secret_node

# Verification SMTP Block
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=app_email@gmail.com
SMTP_PASSWORD=gmail_app_router_password
SENDER_EMAIL=app_email@gmail.com

# Twilio IVR Block
TWILIO_ACCOUNT_SID=ACxyz123abc 
TWILIO_AUTH_TOKEN=secret_twilio_auth
TWILIO_PHONE_NUMBER=+1234567890
WEBHOOK_BASE_URL=https://my-ngrok-tunnel.ngrok.app
```

> **Fallback Notes**: The system gracefully decays if keys are empty. Empty Twilio runs mock print statements, empty SMTP outputs terminal links allowing smooth localized tests.

---

<p align="center">
  <em>Developed to ensure absolute parity within dynamic healthcare credentialing spaces</em>
</p>
