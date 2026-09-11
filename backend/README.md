# HirePrep_AI Backend

Autonomous Multi-Agent AI Mock Interview Platform Backend powered by **FastAPI** and **LangGraph**.

---

## 🏛️ Architecture Overview

The backend is built around a stateful multi-agent supervisor pattern using **LangGraph**, where each stage of interview preparation and execution is encapsulated into specialized, decoupled agents:

```
[Resume Upload (PDF/DOCX)]
          │
          ▼
   1. Resume Parser Node ────► Extracts skills, projects & coding profiles
          │
          ▼
   2. Profile Scraper Node ───► Scrapes ONLY profiles mentioned in resume (GitHub, LeetCode, Codeforces, Kaggle, CodeChef)
          │
          ▼
   3. Question Researcher ────► Curates company/role/location-specific questions across 5 rounds
          │
          ▼
   4. Interview Conductor ────► Live real-time WebSocket interview streaming & adaptive difficulty
          │
          ▼
   5. Feedback Generator  ────► Multi-dimensional scoring, camera body language & 14-day study roadmap
```

---

## 🔌 Decoupled Auth Integration Contract

Per architectural specifications, **Auth & User Management** will be integrated after core backend features. 

The system has been intentionally designed so that **no endpoint signatures, service layers, or database models need to change** when Auth is added:
1. All endpoints and LangGraph nodes consume user context through `app.dependencies.get_current_user_id`.
2. Currently, `get_current_user_id` returns the caller's `X-User-ID` header, query parameter, or defaults to a mock candidate ID.
3. When NextAuth / OAuth / JWT is connected, only `app/dependencies.py` will be updated to validate the Bearer token / session and return the authenticated `user.id`.
4. The database already contains the `users` table schema (`app/db/models.py`) with primary key `id` matching all foreign keys.

---

## 🚀 Key Features Implemented

### 1. Resume Parser (Agent 1)
- Text extraction from `.pdf` and `.docx` using `PyMuPDF` (`fitz`) and `python-docx`.
- Regex and LLM extraction of skills, education, experience, projects, and contact info.
- Deterministic extraction of coding profile links (GitHub, LeetCode, Codeforces, CodeChef, HackerRank, Kaggle).

### 2. Profile Scraper (Agent 2)
- **Selective Scraping**: Only platforms mentioned in the resume are scraped; unmentioned platforms are skipped.
- **GitHub**: Repositories, top languages, stargazers count, bio.
- **LeetCode**: Solved count (Easy/Medium/Hard), ranking, contest rating.
- **Codeforces**: Rating, max rating, rank, solved count.
- **Kaggle / CodeChef**: Tier and competition statistics.

### 3. Question Researcher (Agent 3)
- Generates tailored question banks covering:
  - Behavioral (STAR technique & company leadership principles)
  - Resume Deep-Dive (specific questions on candidate's own projects)
  - Coding / DSA (problem statement, starter code, test cases, hints)
  - System Design (HLD/LLD tailored to company scale)
  - CS Fundamentals (OS, DBMS, Networking, Concurrency)

### 4. Real-time Interview Engine & WebSocket (Agent 4)
- Bidirectional WebSocket (`/ws/interview/{interview_id}`).
- Streaming AI questions and candidate answers.
- In-browser **Camera Body Language Telemetry** ingestion (Eye contact %, Confidence %, Head stability) via TensorFlow.js Face Mesh.
- **Anti-Cheat Code Editor Telemetry** ingestion (Tab switches, copy-paste attempts, DevTools attempts).
- Safe Python code execution sandbox with AST validation (blocks `os`, `sys`, `subprocess`).
- Adaptive difficulty routing (score < 40 -> easy, 40-70 -> medium, > 70 -> hard).

### 5. Feedback Generator (Agent 5)
- Overall score (0-100) & Letter grade (`A+` to `F`).
- Hire recommendation (`Strong Hire`, `Hire`, `Leaning Hire`, `No Hire`).
- Per-section scores (DSA, System Design, Resume, Behavioral).
- Camera body language evaluation.
- Anti-cheat integrity report.
- Personalized 14-day study roadmap with curated daily topics and resources.

---

## 🛠️ Local Development & Testing

### 1. Activate Environment
```bash
# Windows
backend\venv\Scripts\activate

# Linux / macOS
source backend/venv/bin/activate
```

### 2. Run Test Suite
```bash
pytest -v backend/tests
```

### 3. Start Development Server
```bash
uvicorn app.main:app --reload --port 8000
```
API Documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
