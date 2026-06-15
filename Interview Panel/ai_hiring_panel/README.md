# 🔁 HireLoop — Multi-Agent Interview System for SDE Hiring

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python" />
  <img src="https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi" />
  <img src="https://img.shields.io/badge/Streamlit-1.40-FF4B4B?style=for-the-badge&logo=streamlit" />
  <img src="https://img.shields.io/badge/Groq-LLaMA%203.3-orange?style=for-the-badge" />
  <img src="https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" />
</p>

> **HireLoop** simulates a complete big-tech style hiring loop — resume analysis, multi-round AI interviews, automated scoring, and a full recruiter report — all powered by Groq's ultra-fast LLaMA 3.3 inference.

---

## What is HireLoop?

HireLoop is a full-stack web application that automates the end-to-end SDE interview pipeline using multiple specialized AI agents. Inspired by the hiring loops at Google, Amazon, and Meta — where candidates go through separate rounds with HR, Engineering, and Management — HireLoop replicates this process digitally.

A candidate uploads their resume. AI agents analyze it, conduct targeted interviews, and produce a structured evaluation report with scores, strengths, weaknesses, and a final hiring recommendation.

---

## Features

- **Resume Parsing** — Supports PDF, DOCX, and TXT formats
- **AI Resume Analysis** — Extracts name, skills, experience, education, and role using LLaMA 3.3
- **3 Specialized Interview Agents:**
- **Sarah (HR Agent)** — Culture fit, soft skills, background, career goals
- **Alex (Technical Agent)** — DSA, system design, domain depth, coding practices
- **Jordan (Manager Agent)** — Leadership, ownership, STAR-based behavioral questions
- **Automated Scoring** — Scores across Overall, Communication, Technical, and Cultural Fit dimensions
- **Hiring Recommendation** — Strong Hire / Hire / Consider / No Hire / Strong No Hire
- **Persistent Storage** — Full candidate history, session transcripts, and reports in SQLite
- **Recruiter Dashboard** — View and compare all interview reports for any candidate
- **Blazing Fast** — Groq's LPU inference means near-instant AI responses

---

## Architecture

```
hireloop/
│
├── agents/
│   ├── base_agent.py          # Abstract base class — conversation loop, transcript management
│   ├── hr_agent.py            # HR Interviewer — Sarah
│   ├── technical_agent.py     # Technical Interviewer — Alex
│   ├── manager_agent.py       # Manager Interviewer — Jordan
│   └── scoring_agent.py       # Scoring engine — evaluates full transcripts
│
├── api/
│   └── routes.py              # FastAPI REST endpoints
│
├── database/
│   ├── db.py                  # SQLAlchemy engine, session factory, DB init
│   └── models.py              # ORM models — Candidate, Session, Message, Report
│
├── llm/
│   └── groq_client.py         # Groq SDK wrapper — single entry point for all LLM calls
│
├── resume/
│   ├── parser.py              # File parser — PDF / DOCX / TXT extraction
│   └── analyzer.py            # LLM-based structured profile extraction
│
├── services/
│   └── interview_service.py   # Business logic layer — orchestrates agents + DB
│
├── main.py                    # FastAPI application entry point
├── streamlit_app.py           # Streamlit frontend
├── config.py                  # Pydantic settings — env var management
├── requirements.txt
└── .env.example
```

### Design Decisions

| Decision              | Reason                                                                           |
| --------------------- | -------------------------------------------------------------------------------- |
| `services/` layer     | Keeps routes thin; business logic is testable independently                      |
| `llm/` module         | Single place to swap LLM providers (Groq → OpenAI → Ollama)                      |
| Agent rebuild from DB | Interviews survive server restarts — transcript is replayed into agent memory    |
| SQLite default        | Zero-config for development; one env var change to switch to PostgreSQL          |
| Pydantic Settings     | Type-safe config, automatic `.env` loading, no `os.environ` scattered everywhere |

---

## Interview Flow

```
Candidate uploads resume
        │
        ▼
  Resume Parser (PDF/DOCX/TXT)
        │
        ▼
  LLM Resume Analyzer
  (name, skills, experience, role)
        │
        ▼
  Select Interviewer Round
  ┌─────┬──────────┬─────────┐
  │ HR  │ Technical│ Manager │
  └─────┴──────────┴─────────┘
        │
        ▼
  Live Chat Interview
  (candidate answers questions)
        │
        ▼
  Scoring Agent
  (analyses full transcript)
        │
        ▼
  Evaluation Report
  (scores + recommendation)
        │
        ▼
  Recruiter Dashboard
```

---

## AGENT PERSONAS

### Sarah — HR Interviewer

Focuses on the human side of hiring. Covers work history verification, cultural fit, communication style, conflict resolution, and career aspirations. Keeps the conversation warm and professional.

### Alex — Technical Interviewer

A principal engineer who adapts question difficulty to the candidate's experience level. Covers data structures, algorithms, system design, coding best practices, and domain-specific technologies listed on the resume.

### Jordan — Manager Interviewer

A senior hiring manager who uses the STAR method (Situation, Task, Action, Result) to probe leadership, ownership, handling ambiguity, cross-functional collaboration, and long-term growth trajectory.

---

## Scoring Rubric

| Score  | Meaning                      |
| ------ | ---------------------------- |
| 9 – 10 | Exceptional, rare talent     |
| 7 – 8  | Strong candidate, clear hire |
| 5 – 6  | Average, needs consideration |
| 3 – 4  | Below expectations           |
| 0 – 2  | Poor fit                     |

Four dimensions are scored independently: **Overall**, **Communication**, **Technical**, **Cultural Fit**

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- A free [Groq API key](https://console.groq.com)

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/hireloop.git
cd hireloop
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
GROQ_API_KEY=gsk_your_key_here
DATABASE_URL=sqlite:///./hireloop.db
SECRET_KEY=your_secret_key_here
```

### 4. Start the backend

```bash
python -m uvicorn main:app --reload --port 8000
```

API docs available at → http://localhost:8000/docs

### 5. Start the frontend

```bash
python -m streamlit run streamlit_app.py
```

Open → **http://localhost:8501**

---

## API Reference

| Method | Endpoint                           | Description                          |
| ------ | ---------------------------------- | ------------------------------------ |
| `POST` | `/api/v1/resume/upload`            | Upload and analyse a resume          |
| `POST` | `/api/v1/sessions`                 | Create an interview session          |
| `POST` | `/api/v1/sessions/{id}/start`      | Start interview, get opening message |
| `POST` | `/api/v1/sessions/{id}/answer`     | Submit candidate answer              |
| `POST` | `/api/v1/sessions/{id}/finish`     | End interview, generate report       |
| `GET`  | `/api/v1/sessions/{id}/transcript` | Fetch full transcript                |
| `GET`  | `/api/v1/candidates/{id}/reports`  | Get all reports for a candidate      |
| `GET`  | `/health`                          | Health check                         |

Full interactive docs at `http://localhost:8000/docs`

---

## Database Schema

```
Candidate
  └── InterviewSession (hr / technical / manager)
        ├── InterviewMessage (agent / candidate turns)
        └── Report (scores, recommendation, feedback)
```

---

## Roadmap

| Phase                   | Status      | Features                                                 |
| ----------------------- | ----------- | -------------------------------------------------------- |
| Phase 1 — MVP           | ✅ Complete | Resume upload, AI analysis, technical interview, scoring |
| Phase 2 — Multi-Agent   | ✅ Complete | HR agent, Manager agent, all three interview types       |
| Phase 3 — Persistence   | ✅ Complete | SQLite DB, candidate history, recruiter dashboard        |
| Phase 4 — Auth & Deploy | 🔜 Planned  | User authentication, analytics, Docker, cloud deployment |

---

## Switching to PostgreSQL

Change one line in `.env`:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/hireloop
```

No other code changes needed.

---

## Tech Stack

| Layer             | Technology                |
| ----------------- | ------------------------- |
| Frontend          | Streamlit                 |
| Backend           | FastAPI                   |
| Database          | SQLite (PostgreSQL-ready) |
| ORM               | SQLAlchemy 2.0            |
| LLM               | LLaMA 3.3 70B via Groq    |
| Resume Parsing    | pdfplumber, python-docx   |
| Config Management | Pydantic Settings         |
| HTTP Client       | Requests, HTTPX           |

---

## License

This project is licensed under the MIT License.

---

## Author

Built by **Vineet Sharma**

> _"Automate the loop. Hire the best."_
