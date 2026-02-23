# 🏥 HealthValidator.ai

**AI-Powered Healthcare Provider Data Validation & Enrichment Platform**

A full-stack application that automates the onboarding, validation, enrichment, and governance of healthcare provider data. It combines real-time NPI Registry verification, LLM-powered analysis (Groq / Llama 3), web-scraping enrichment, and email-based provider verification into a single, cohesive pipeline.

---

## 📑 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Data Flow](#data-flow)
- [Tech Stack & Tools](#tech-stack--tools)
- [Project Structure](#project-structure)
- [Database Schema](#database-schema)
- [AI Agents](#ai-agents)
- [API Endpoints](#api-endpoints)
- [Frontend Pages](#frontend-pages)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)

---

## Overview

Healthcare payers and networks need accurate, up-to-date provider directories. Manual validation is slow, error-prone, and doesn't scale. **HealthValidator.ai** solves this by:

1. **Ingesting** provider data via manual form entry, PDF/image upload (OCR), or CSV batch import.
2. **Validating** every record against the official **NPPES NPI Registry** using deterministic matching algorithms (Levenshtein distance, Jaccard similarity).
3. **Comparing** submitted data to NPI data with an **LLM (Groq — Llama 3)** for semantic field-by-field analysis.
4. **Enriching** incomplete records by scraping the open web (DuckDuckGo + Selenium) and querying the **Hunter.io Email API**.
5. **Scoring** each record with a weighted **confidence score** and flagging anything below threshold for manual review.
6. **Verifying** providers directly via **email verification links** (SMTP).
7. **Auditing** every field-level change in a full **audit trail**.
8. **Analyzing** geographic provider distribution on an interactive **US Map** with AI-driven conversational insights.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React 19)                        │
│  ┌───────────┐ ┌───────────┐ ┌──────────────┐ ┌────────────────┐  │
│  │ Onboarding│ │ Dashboard │ │Provider Detail│ │  US Map +      │  │
│  │   Form    │ │  (List)   │ │  (Drill-down) │ │  Analysis Chat │  │
│  └─────┬─────┘ └─────┬─────┘ └──────┬───────┘ └───────┬────────┘  │
│        │              │              │                 │            │
│        └──────────────┴──────────────┴─────────────────┘            │
│                              │ REST API (port 3000)                 │
└──────────────────────────────┼──────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     BACKEND (FastAPI + Uvicorn)                      │
│                           port 8000                                  │
│  ┌──────────────┐  ┌──────────────────┐  ┌───────────────────────┐  │
│  │  main.py     │  │   services.py    │  │      models.py        │  │
│  │  (Endpoints) │──│  (Business Logic)│──│  (SQLAlchemy ORM)     │  │
│  └──────┬───────┘  └────────┬─────────┘  └───────────┬───────────┘  │
│         │                   │                        │              │
│  ┌──────┴───────────────────┴────────────────────────┘              │
│  │                                                                   │
│  │  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐  │
│  │  │ Extractor Agent │  │ Enrichment Agent  │  │  Email Agent   │  │
│  │  │ (OCR + LLM)     │  │ (Web + LLM)      │  │  (SMTP)        │  │
│  │  └────────┬────────┘  └────────┬─────────┘  └───────┬────────┘  │
│  │           │                    │                     │           │
│  │           ▼                    ▼                     ▼           │
│  │     ┌──────────┐     ┌──────────────┐        ┌────────────┐     │
│  │     │Groq LLM  │     │DuckDuckGo    │        │Gmail SMTP  │     │
│  │     │(Llama 3) │     │+ Selenium    │        │Server      │     │
│  │     └──────────┘     │+ Hunter.io   │        └────────────┘     │
│  │                      └──────────────┘                           │
│  └──────────────────────────────────────────────────────────────────┘
│                               │                                      │
└───────────────────────────────┼──────────────────────────────────────┘
                                ▼
                  ┌──────────────────────────┐
                  │   PostgreSQL Database    │
                  │   (6 tables via asyncpg) │
                  └──────────────────────────┘
                                │
                  ┌─────────────┼─────────────┐
                  ▼             ▼             ▼
           ┌───────────┐ ┌──────────┐ ┌────────────┐
           │ NPI       │ │ Groq API │ │ Hunter.io  │
           │ Registry  │ │ (LLM)    │ │ Email API  │
           │ (NPPES)   │ │          │ │            │
           └───────────┘ └──────────┘ └────────────┘
```

---

## Data Flow

### 1️⃣ Provider Onboarding

```
User Input ──► Extractor Agent (if PDF/Image) ──► Structured JSON
     │                                                  │
     │         Manual Form / CSV Upload ────────────────┤
     │                                                  │
     └──────────────────────────────────────────────────┘
                            │
                            ▼
                  Raw Provider Submission
                  (saved in PostgreSQL)
```

### 2️⃣ Validation Pipeline

```
Raw Submission
      │
      ├──► 1. NPI Lookup (NPPES Registry API)
      │         → Returns official provider data
      │
      ├──► 2. Deterministic Matching
      │         → Levenshtein distance (names)
      │         → Jaccard similarity (addresses)
      │         → Exact match (NPI, taxonomy codes)
      │
      ├──► 3. LLM Comparison (Groq / Llama 3)
      │         → Field-by-field semantic analysis
      │         → Confidence scoring per field
      │         → Issue identification
      │
      ├──► 4. Confidence Score Calculation
      │         → Weighted score across all fields
      │         → Records < 70% flagged for manual review
      │
      └──► 5. Data Governance & Conflict Resolution
                → NPI data = source of truth for core fields
                → Enrichment data fills gaps only
                → Every change logged in audit trail
```

### 3️⃣ Enrichment Pipeline

```
Provider Record (after validation)
      │
      ├──► 1. Web Search (DuckDuckGo via Selenium)
      │         → Scrapes top search results
      │         → Collects practice info, websites, etc.
      │
      ├──► 2. Domain Discovery
      │         → Finds the organization's official website
      │         → Unwraps redirect URLs
      │
      ├──► 3. Hunter.io Email Lookup
      │         → Uses org domain + provider name
      │         → Returns verified email + confidence
      │
      └──► 4. LLM Structuring (Groq / Llama 3)
                → Parses scraped web content
                → Returns structured JSON with:
                     practice_name, website, email,
                     phone, accepting_new_patients,
                     telehealth, languages, confidence
```

### 4️⃣ Email Verification

```
System ──► Generate secure token
       ──► Send verification email (SMTP / simulation)
       ──► Provider clicks link → Verification Portal
       ──► Provider reviews & corrects data
       ──► Data saved as "Verified" with audit log
```

---

## Tech Stack & Tools

### Backend
| Tool | Purpose |
|------|---------|
| **Python 3.10+** | Core language |
| **FastAPI** | REST API framework |
| **Uvicorn** | ASGI server |
| **SQLAlchemy 2.0** | Async ORM (mapped columns) |
| **asyncpg** | Async PostgreSQL driver |
| **Pydantic** | Data validation & schema enforcement |

### AI / LLM
| Tool | Purpose |
|------|---------|
| **Groq Cloud API** | LLM inference (ultra-fast) |
| **Llama 3.3 70B** | Model for comparison, extraction, enrichment, and analysis |
| **LangChain Core** | Prompt templates and output parsers |

### Data Sources & APIs
| Tool | Purpose |
|------|---------|
| **NPPES NPI Registry** | Official US provider validation (CMS) |
| **Hunter.io** | Email discovery from domain + name |
| **DuckDuckGo** | Web search for provider enrichment |

### Web Scraping & Extraction
| Tool | Purpose |
|------|---------|
| **Selenium** | Headless Chrome for web scraping |
| **webdriver-manager** | Auto-manages ChromeDriver |
| **PyPDF** | PDF text extraction |
| **Pytesseract + Pillow** | OCR for image-based documents |

### Frontend
| Tool | Purpose |
|------|---------|
| **React 19** | UI framework |
| **Framer Motion** | Page transitions & animations |
| **Lucide React** | Icon library |
| **react-simple-maps** | Interactive US map visualization |
| **D3 (scale + format)** | Data-driven map coloring & formatting |

### Database
| Tool | Purpose |
|------|---------|
| **PostgreSQL** | Primary relational database |
| **asyncpg** | Non-blocking database I/O |

### Email
| Tool | Purpose |
|------|---------|
| **smtplib (Gmail SMTP)** | Sending verification emails |
| **Simulation mode** | Falls back to console logging if SMTP not configured |

---

## Project Structure

```
EY/
├── .env                        # Environment variables (API keys, DB URL, SMTP)
├── requirements.txt            # Python dependencies
├── README.md                   # This file
│
├── Backend/
│   ├── main.py                 # FastAPI app — all REST endpoints
│   ├── services.py             # Business logic: ValidationService, EnrichmentService
│   ├── models.py               # SQLAlchemy ORM models (6 tables)
│   ├── database.py             # Async engine, session factory, init_db()
│   ├── reset_db.py             # Script to recreate all tables
│   ├── migrate_audit_log.py    # Migration script for audit trail table
│   └── Tables/
│       └── db.sql              # Raw SQL schema for reference
│
├── Agents/
│   ├── extractor_agent.py      # OCR + LLM extraction from PDFs/images
│   ├── enrichment_agent_v0.py  # Web scraping + Hunter.io + LLM enrichment
│   ├── email_agent.py          # SMTP email verification agent
│   ├── network_agent.py        # Network adequacy gap analysis (ReAct agent)
│   ├── healthcare_schema.py    # Pydantic schema for provider profiles
│   └── test_domain_finder.py   # Test script for domain discovery
│
├── Validation/
│   ├── NPI.py                  # NPPES Registry API client
│   ├── groq_client.py          # Groq API wrapper (generate_text)
│   ├── groq_compare.py         # LLM-based field-by-field comparison
│   ├── Validate.py             # Batch CSV validation runner
│   └── gemini_compare.py       # Legacy Gemini comparison (deprecated)
│
├── Data/
│   ├── Healthcare Providers.csv    # Full provider dataset
│   ├── clean_output.csv            # Cleaned CSV for validation
│   ├── sample_.csv                 # Sample data for testing
│   └── *.csv                       # Validation output files
│
└── frontend/
    ├── package.json
    └── src/
        ├── App.js                  # Root component with navigation
        ├── App.css                 # Global styles (dark theme)
        ├── OnboardingForm.js       # Provider onboarding (form + CSV + file upload)
        ├── Dashboard.js            # Provider list with "Needs Review" / "Verified" split
        ├── ProviderDetail.js       # Detailed provider view + audit trail + enrichment
        ├── VerificationPage.js     # External verification portal (token-based)
        ├── USMapAnalysis.js        # Interactive US map with AI analysis chat
        ├── AnalysisPage.js         # Analysis page wrapper
        └── ProcessTracker.js       # Real-time pipeline status tracker
```

---

## Database Schema

The PostgreSQL database uses **6 normalized tables**:

| Table | Purpose |
|-------|---------|
| `providers_master_per` | **Personal info** — NPI (PK), name, phone, email, address |
| `providers_master_prof` | **Professional info** — practice name, specialties, taxonomies, telehealth, languages |
| `providers_master_meta` | **Validation metadata** — confidence scores per field, status, verification tokens, quality flags |
| `raw_provider_submissions` | **Submission log** — raw input payloads, NPI API responses, processing status |
| `market_expansion_opportunities` | **Analytics** — network adequacy, demand index, expansion priority scoring |
| `provider_audit_log` | **Audit trail** — field-level change history with old/new values, source, actor, timestamp |

Each provider record spans 3 linked tables (`per` → `prof` → `meta`) connected by the NPI as a foreign key.

---

## AI Agents

### 🔍 Extractor Agent (`extractor_agent.py`)
Extracts structured provider data from unstructured documents (PDFs, images) using OCR (Pytesseract) and an LLM (Groq / Llama 3) to produce a `HealthcareProviderProfile` Pydantic object.

### 🌐 Enrichment Agent (`enrichment_agent_v0.py`)
A multi-step agent that:
1. Searches DuckDuckGo for the provider/organization.
2. Scrapes top results using headless Selenium.
3. Discovers the organization's official domain.
4. Calls Hunter.io to find the provider's email.
5. Feeds all gathered text to the LLM to produce structured enrichment data.

### ✉️ Email Verification Agent (`email_agent.py`)
Generates secure tokens, constructs verification links, and sends HTML emails via SMTP (or simulates in dev mode).

### 📊 Network Gap Agent (`network_agent.py`)
A ReAct-style agent that analyzes network adequacy by computing geographic coverage gaps for specific specialties using geodesic distance calculations.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/extract` | Upload PDF/image → OCR + LLM extraction |
| `POST` | `/submit` | Submit provider data → starts validation pipeline |
| `GET` | `/status/{id}` | Poll real-time pipeline step statuses |
| `POST` | `/onboard/csv` | Batch CSV upload and processing |
| `GET` | `/providers` | List all providers (paginated) |
| `GET` | `/providers/{id}` | Get provider details by NPI |
| `POST` | `/seed-mock` | Seed database with sample data |
| `POST` | `/reset` | Reset database (danger!) |
| `POST` | `/verify-email/{id}` | Trigger email verification for a provider |
| `GET` | `/verify/{token}` | Retrieve data for verification portal |
| `POST` | `/verify/{token}` | Submit verified/corrected data |
| `POST` | `/enrich/{id}` | Manually trigger enrichment for a provider |
| `POST` | `/enrich/batch` | Batch enrichment for multiple providers |
| `GET` | `/audit/{id}` | Get audit trail for a provider |
| `GET` | `/geo/distribution` | Provider distribution by state |
| `GET` | `/geo/specialties` | List of unique specialties |
| `POST` | `/analyze/map` | AI analysis of geographic data |
| `GET` | `/analyze/context-data` | Fetch filtered context for analysis chat |
| `POST` | `/analyze/chat` | Multi-turn conversational analysis |

---

## Frontend Pages

### 📋 Onboarding Form
- **Manual entry**: Fill in provider details field-by-field.
- **File upload**: Upload a PDF or image for OCR-based extraction.
- **CSV batch import**: Upload a CSV file to process hundreds of providers at once.
- Real-time pipeline status tracking via `ProcessTracker`.

### 📊 Dashboard
- Split view: **"Needs Review"** (confidence < 70%) vs. **"Verified"** providers.
- Provider cards with confidence badges and status indicators.
- Click-through to detailed provider view.

### 🔎 Provider Detail
- Tabbed interface: **Overview** | **Professional** | **History** (Audit Trail).
- Field-level confidence indicators with source attribution.
- One-click **Enrich** button to trigger the enrichment pipeline.
- One-click **Send Verification Email** to initiate provider outreach.

### 🗺️ US Map & Analysis
- Interactive choropleth map of provider distribution by state.
- Specialty-based filtering.
- **AI Chat**: Multi-turn conversational analysis powered by Groq (Llama 3) with full contextual data injection.

### ✅ Verification Portal
- Token-based external page for providers.
- Displays pre-filled data for review and correction.
- Submissions mark the record as "Verified" with full audit trail.

---

## Getting Started

### Prerequisites
- **Python 3.10+**
- **Node.js 18+**
- **PostgreSQL** (running locally or remotely)
- **Google Chrome** (for Selenium headless scraping)
- **Tesseract OCR** (for image extraction — [install guide](https://github.com/tesseract-ocr/tesseract))

### 1. Clone & Install Backend

```bash
# Install Python dependencies
pip install -r requirements.txt
```

### 2. Set Up Database

```bash
# Create the PostgreSQL database
createdb HealthCare

# Or run the SQL schema manually:
psql -d HealthCare -f Backend/Tables/db.sql
```

### 3. Configure Environment

Create a `.env` file in the project root (see [Environment Variables](#environment-variables)).

### 4. Start Backend

```bash
cd Backend
uvicorn main:app --reload
# API available at http://localhost:8000
```

### 5. Install & Start Frontend

```bash
cd frontend
npm install
npm start
# UI available at http://localhost:3000
```

### 6. Seed Sample Data (Optional)

Hit the seed endpoint to populate the database with sample providers:
```bash
curl -X POST http://localhost:8000/seed-mock
```

---

## Environment Variables

Create a `.env` file in the project root with the following:

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/HealthCare

# LLM - Groq Cloud
GROQ_API_KEY=your_groq_api_key

# Email Finder
HUNTER_API=your_hunter_io_api_key

# Email Verification (SMTP)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SENDER_EMAIL=your_email@gmail.com

# Legacy (optional)
GEMINI_API_KEY=your_gemini_key
```

> **Note**: If SMTP credentials are not configured, the Email Agent runs in **simulation mode** and logs verification links to the console instead of sending real emails.

---

<p align="center">
  <em>Built with ❤️ for smarter healthcare data governance</em>
</p>
