<p align="center">
  <img src="./assets/banner.png" alt="HirePrep_AI" width="100%" />
</p>

> Autonomous Multi-Agent AI Mock Interview Platform powered by **FastAPI** and **LangGraph**.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-orange.svg)](https://github.com/langchain-ai/langgraph)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 💡 Overview

HirePrep_AI prepares tech candidates for technical interviews by simulating real 30-minute interviews tailored to their **specific company, role, location, and actual projects**:

1. **Resume Parser Agent**: Extracts skills, projects, and detects coding profiles (GitHub, LeetCode, Codeforces, Kaggle, CodeChef, HackerRank).
2. **Selective Profile Scraper Agent**: Scrapes **ONLY** coding profiles found in the resume, plus inspects repository **codebases (file tree & README)**.
3. **Question Researcher Agent**: Gathers real-world interview intelligence in parallel across **Reddit**, **LeetCode Discuss**, **HackerNews**, **GitHub Repos**, and **GeeksforGeeks Archives**.
4. **Interview Conductor Agent (Real-time WebSocket)**: Delivers questions, evaluates candidate speech-to-text, receives **Camera Body Language Telemetry** (eye contact %, confidence), and monitors **Anti-Cheat Monaco Code Editor** events (tab-switches, copy-paste attempts).
5. **Feedback Generator Agent**: Publishes detailed scoring (0-100, letter grade `A+` to `F`), section scores, body language evaluation, anti-cheat integrity scores, and a personalized 14-day study roadmap.

---

## 🏛️ Repository Structure

```
HirePrep_AI/
├── backend/                     # FastAPI + LangGraph Backend
│   ├── app/
│   │   ├── main.py              # FastAPI app & real-time WebSocket server
│   │   ├── config.py            # Pydantic Settings
│   │   ├── dependencies.py      # Decoupled user context (ready for Auth)
│   │   ├── models/              # Pydantic data schemas
│   │   ├── db/                  # Async SQLAlchemy models & SQLite/PostgreSQL connection
│   │   ├── services/            # LLM router, scrapers, question engine, sandboxed code runner
│   │   ├── graph/               # LangGraph multi-agent supervisor graph & nodes
│   │   └── routes/              # REST endpoints & WebSocket interview streaming
│   ├── tests/                   # Complete test suite (11/11 passing)
│   ├── requirements.txt
│   └── README.md
├── .gitignore
└── README.md
```

---

## 🚀 Quickstart (Backend)

```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
pytest -v tests
uvicorn app.main:app --reload --port 8000
```
Interactive API Swagger Docs: `http://localhost:8000/docs`
