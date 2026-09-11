# 💻 HirePrep_AI — Complete Frontend Developer Guide & Specifications

> **Audience**: Frontend Engineers building the Next.js client application for **HirePrep_AI**.  
> **Backend Base URL**: `http://localhost:8000` (Local) / `https://api.hireprep.ai` (Production)  
> **WebSocket URL**: `ws://localhost:8000/ws/interview/{interview_id}`

---

## 📑 Table of Contents
1. [Tech Stack & Architecture](#-tech-stack--architecture)
2. [Design System & Aesthetic Guidelines](#-design-system--aesthetic-guidelines)
3. [Complete Page Directory & Routes](#-complete-page-directory--routes)
4. [Detailed Page Specifications & Wireframes](#-detailed-page-specifications--wireframes)
   - [Page 1: Landing Page (`/`)](#1-landing-page-)
   - [Page 2: Candidate Dashboard (`/dashboard`)](#2-candidate-dashboard-dashboard)
   - [Page 3: Interview Setup & Resume Upload (`/setup`)](#3-interview-setup--resume-upload-setup)
   - [Page 4: Live 30-Min Interview Room (`/interview/[id]`)](#4-live-30-min-interview-room-interviewid)
   - [Page 5: Holistic Feedback & Roadmap Report (`/feedback/[id]`)](#5-holistic-feedback--roadmap-report-feedbackid)
   - [Page 6: Community Leaderboard (`/leaderboard`)](#6-community-leaderboard-leaderboard)
5. [Core Client-Side Engine Specifications](#-core-client-side-engine-specifications)
   - [Engine A: Mandatory Camera & TensorFlow.js Face Mesh](#engine-a-mandatory-camera--tensorflowjs-face-mesh)
   - [Engine B: Monaco Code Editor with Anti-Cheat System](#engine-b-monaco-code-editor-with-anti-cheat-system)
   - [Engine C: Web Speech API (Voice STT & TTS)](#engine-c-web-speech-api-voice-stt--tts)
   - [Engine D: Real-Time WebSocket Protocol](#engine-d-real-time-websocket-protocol)
6. [Backend API Integration Contract](#-backend-api-integration-contract)

---

## 🛠️ Tech Stack & Architecture

| Layer | Technology | Details |
|---|---|---|
| **Framework** | **Next.js 15+ (App Router)** | Modern React Server Components + Client Components where interactive |
| **Styling** | **Vanilla CSS + Custom Properties** | Design tokens, glassmorphism, dynamic gradients, smooth micro-animations |
| **Code Editor** | **`@monaco-editor/react`** | Proctored VS Code editor with disabled shortcuts & paste listeners |
| **Computer Vision** | **`@tensorflow/tfjs` & `@tensorflow-models/face-landmarks-detection`** | 468 facial mesh landmarks running 100% in-browser on client GPU |
| **Voice Processing** | **Web Speech API** | `SpeechRecognition` (voice input) + `SpeechSynthesis` (AI interviewer voice) |
| **Real-time Comms** | **Native WebSocket API** | Bidirectional event streaming for transcript, audio, code & telemetry |

---

## 🎨 Design System & Aesthetic Guidelines

### Color Palette (Tokens)
```css
:root {
  --bg-primary: #0a0d14;         /* Deep void black */
  --bg-secondary: #121824;       /* Card background */
  --bg-elevated: #1a2233;        /* Dropdowns, modals */
  --border-subtle: rgba(255, 255, 255, 0.08);
  --border-glow: rgba(16, 185, 129, 0.3);

  /* Brand Colors */
  --brand-green: #00ea88;        /* HirePrep bright green accent */
  --brand-green-glow: rgba(0, 234, 136, 0.15);
  --accent-purple: #7928ca;      /* AI / reasoning highlights */
  --accent-blue: #0070f3;        /* System highlights */
  --accent-amber: #f5a623;       /* Warning / timer */
  --accent-red: #ff0080;         /* Violations / alerts */

  /* Typography */
  --font-display: 'Outfit', 'Inter', -apple-system, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
}
```

### Aesthetic Standards
* **Visual Wow-Factor**: Deep dark theme with glassmorphic cards (`backdrop-filter: blur(12px)`), subtle neon borders, and smooth hover micro-interactions.
* **Zero Jitter**: Video feeds, audio visualizers, and code editor must maintain consistent layout dimensions without jumping during dynamic text updates.

---

## 📂 Complete Page Directory & Routes

```
frontend/
├── app/
│   ├── layout.js                 # Global HTML, Navbar, Footer, Providers
│   ├── page.js                   # Landing Page (/)
│   ├── dashboard/page.js         # Candidate Dashboard (/dashboard)
│   ├── setup/page.js             # Resume Upload & Job Targeting (/setup)
│   ├── interview/[id]/page.js    # Live Proctored Interview Room (/interview/[id])
│   ├── feedback/[id]/page.js     # Comprehensive Feedback Report (/feedback/[id])
│   └── leaderboard/page.js       # Opt-in Global Leaderboard (/leaderboard)
├── components/
│   ├── ui/                       # Buttons, Cards, Badges, Modals, Sliders
│   ├── interview/                # CameraStream, AudioWaveform, MonacoAntiCheat, TranscriptFeed
│   ├── feedback/                 # ScoreGauge, RadarChart, RoadmapTimeline, IntegrityCard
│   └── layout/                   # Header, Sidebar, Footer
├── hooks/
│   ├── useFaceMesh.js            # TensorFlow.js camera body language tracker
│   ├── useSpeechEngine.js        # SpeechRecognition (STT) + SpeechSynthesis (TTS)
│   ├── useAntiCheat.js           # Monaco anti-paste, blur, devtools blocker
│   └── useInterviewSocket.js     # WebSocket connection manager
└── styles/
    └── globals.css               # Global tokens, typography, utilities
```

---

## 📄 Detailed Page Specifications & Wireframes

### 1. Landing Page (`/`)
* **Hero Section**:
  - Catchy title with gradient typography: *"Master Your Next Technical Interview with Autonomous AI"*.
  - Dual action buttons: `[Start Free Mock Interview]` (primary green glow) and `[View Sample Report]`.
  - Live animated preview of the 3-panel interview room (Face mesh tracking + Voice waveform + Monaco editor).
* **Company Badges Ribbon**: Google, Amazon, Microsoft, Uber, Meta, Netflix.
* **Core Value Pillars**:
  1. *Resume-Tailored Deep Dives* — Questions on your actual projects & codebase decisions.
  2. *Live Computer Vision Telemetry* — In-browser eye contact & confidence feedback.
  3. *Proctored Anti-Cheat Editor* — Simulates real coding screen restrictions.
  4. *Targeted Question Intelligence* — Scrapes Reddit & LeetCode Discuss for your exact target company.
* **Interactive Demo**: Try a 60-second AI interviewer voice question directly on the landing page.

---

### 2. Candidate Dashboard (`/dashboard`)
* **Welcome Header**: Candidate profile summary, total interviews taken, current average score.
* **Readiness Radar Chart**: DSA, System Design, Behavioral, Communication, Body Language.
* **Past Interviews Table**:
  - Columns: Target Company, Role, Date, Score & Grade (`A+`, `B`), Status, Action `[View Detailed Feedback]`.
* **Action Card**: `[Schedule / Start New Mock Interview]` (prominent CTA button leading to `/setup`).

---

### 3. Interview Setup & Resume Upload (`/setup`)
* **Step 1: Resume Upload**:
  - Drag-and-drop zone accepting `.pdf` and `.docx`.
  - Client sends file to `POST /api/resume/upload`.
  - Displays instant extracted breakdown:
    - Candidate Name & Title
    - Categorized Skills pills
    - Detected Profile Badges (GitHub, LeetCode, Codeforces, Kaggle)
* **Step 2: Target Interview Configuration**:
  - **Company**: Auto-complete input (Google, Amazon, Microsoft, Startup, etc.).
  - **Role**: SDE-1, SDE-2, Fullstack, Frontend, Backend, Machine Learning Engineer.
  - **Location**: Default "India" (or dropdown for US, Europe, Remote).
  - **Difficulty**: Easy, Medium, Hard.
  - **Duration**: 30 Minutes.
* **Step 3: Device & Camera Verification (MANDATORY)**:
  - Video preview verifying camera permission.
  - Microphone test bar with animated audio level visualizer.
  - Start button remains **disabled** until both camera and mic are granted!

---

### 4. Live 30-Min Interview Room (`/interview/[id]`)

This is the central experience. The page layout is a **3-panel responsive workspace**:

```
+------------------------------------------------------------------------------------+
| TOP BAR: Target: Google (SDE-2) | Round: CODING | Timer: 24:18 | [End Interview]   |
+----------------------------------+-------------------------------------------------+
| LEFT PANEL (40% width)           | RIGHT PANEL (60% width)                         |
|                                  |                                                 |
| 1. AI Interviewer Avatar         | [Tab: Monaco Code Editor]  [Tab: Whiteboard]    |
|    - Animated speech wave        |                                                 |
|    - Audio TTS speech active     | // Anti-Cheat Active: Copy/Paste Blocked        |
|                                  | class Solution:                                 |
| 2. Candidate Video Stream (HUD)  |     def lengthOfLongestSubstring(s: str):       |
|    - Live Eye Contact Meter: 91% |         # Write solution here                   |
|    - Confidence Gauge: 84%       |                                                 |
|    - Posture indicator           |                                                 |
|                                  |                                                 |
| 3. Live Dialogue Transcript      |                                                 |
|    - AI: "Can you explain O(N)?" | ----------------------------------------------- |
|    - Candidate: (Live STT text)  | Test Cases Panel: [Test 1: PASSED] [Test 2: ...] |
|    - [Mute Mic] [Push to Talk]   | Buttons: [Run Code]  [Submit Final Solution]    |
+----------------------------------+-------------------------------------------------+
```

#### Key Interactions:
1. **Camera Feed**:
   - Camera **must remain on**. If user covers or turns off camera, an alert displays: *"Camera is mandatory for interview proctoring"*.
   - TensorFlow.js computes face landmarks every 1 second and sends `body_language_sample` via WebSocket.
2. **Anti-Cheat Monaco Editor**:
   - `Ctrl+C`, `Ctrl+V`, `Ctrl+X`, and right-click paste are intercepted, blocked, and logged.
   - When candidate leaves the browser tab (`document.visibilitychange`), a warning banner pops up and a violation event is transmitted.
   - Clicking `[Run Code]` calls `POST /api/interview/{id}/code` and renders test assertions below.
3. **Voice Dialogue**:
   - Web Speech API listens continuously when mic is on.
   - Finished phrases are sent as `candidate_answer` via WebSocket.
   - When AI interviewer streams text, `window.speechSynthesis` speaks the question naturally.

---

### 5. Holistic Feedback & Roadmap Report (`/feedback/[id]`)
* **Hero Score Badge**:
  - Circular animated progress ring: Overall Score (e.g. `86 / 100`).
  - Letter Grade pill (`A`), Hire Recommendation badge (`Strong Hire` - green).
* **Multi-Tab Breakdown**:
  - **Tab 1: Section Scores**: Bar breakdown for DSA (85%), System Design (82%), Resume Projects (90%), Behavioral (84%).
  - **Tab 2: Camera & Body Language**: Average eye contact percentage, confidence score, posture stability, fidgeting analysis.
  - **Tab 3: Anti-Cheat & Integrity**: Proctoring score (100% minus deductions), list of any tab-switch or paste events.
  - **Tab 4: Technical Transcript**: Full dialogue annotated with AI interviewer evaluations and follow-up rationales.
* **14-Day Personalized Roadmap**:
  - Day-by-day interactive timeline (Day 1 to Day 14).
  - Target topics, specific actionable exercises, and direct link cards to NeetCode / LeetCode / ByteByteGo resources.
* **Export Action**: `[Download PDF Report]` and `[Share Feedback Link]`.

---

### 6. Community Leaderboard (`/leaderboard`)
* Candidate opt-in ranking based on mock interview scores.
* Filter by target company (Google, Amazon, Microsoft) and role (SDE-1, SDE-2).
* Shows user handle/avatar, target company, overall score, and badge.

---

## 🧠 Core Client-Side Engine Specifications

### Engine A: Mandatory Camera & TensorFlow.js Face Mesh
* **Packages**:
  ```bash
  npm install @tensorflow/tfjs @tensorflow-models/face-landmarks-detection
  ```
* **Hook Implementation (`hooks/useFaceMesh.js`)**:
  - Load model: `faceLandmarksDetection.createDetector(faceLandmarksDetection.SupportedModels.MediaPipeFaceMesh)`
  - Periodically analyze webcam frame:
    - **Eye Contact %**: Calculate horizontal and vertical gaze ratio between iris landmarks (468, 473) and eye corner landmarks (33, 133). If centered within threshold -> 100%, if looking away -> < 50%.
    - **Confidence Score**: Computed from smile/neutral mouth landmark ratio and brow tension.
    - **Head Stability**: Track variance of nose tip landmark (landmark 1) over time.
  - Emit JSON sample every 1000ms:
    ```json
    {
      "type": "body_language_sample",
      "eye_contact_score": 88.5,
      "confidence_score": 82.0,
      "head_stability_score": 91.0,
      "face_in_frame": true,
      "timestamp": 1726071800.12
    }
    ```

---

### Engine B: Monaco Code Editor with Anti-Cheat System
* **Package**: `@monaco-editor/react`
* **Anti-Cheat Rules (`hooks/useAntiCheat.js`)**:
  ```javascript
  // 1. Intercept Copy / Paste in Monaco Editor
  editor.onKeyDown((e) => {
    // Intercept Ctrl+V, Ctrl+C, Ctrl+X, Cmd+V, Cmd+C
    if ((e.ctrlKey || e.metaKey) && ['KeyV', 'KeyC', 'KeyX'].includes(e.code)) {
      e.preventDefault();
      e.stopPropagation();
      logAndSendViolation("copy_paste_attempt", "Blocked clipboard shortcut inside code editor");
    }
  });

  // 2. Intercept context menu (right click)
  editor.onContextMenu((e) => {
    e.event.preventDefault();
  });

  // 3. Tab-switch / Window Blur Detection
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      logAndSendViolation("tab_switch", "Candidate left interview browser tab");
    }
  });

  window.addEventListener("blur", () => {
    logAndSendViolation("window_blur", "Candidate switched focus away from interview window");
  });

  // 4. Block DevTools Shortcuts
  window.addEventListener("keydown", (e) => {
    if (e.key === "F12" || ((e.ctrlKey || e.metaKey) && e.shiftKey && ['I', 'J', 'C'].includes(e.key.toUpperCase()))) {
      e.preventDefault();
      logAndSendViolation("devtools_attempt", "Attempted to inspect browser elements");
    }
  });
  ```

---

### Engine C: Web Speech API (Voice STT & TTS)
* **Speech-to-Text (`SpeechRecognition`)**:
  - Initializes `window.SpeechRecognition || window.webkitSpeechRecognition`.
  - Sets `continuous = true` and `interimResults = true`.
  - On final result, appends to transcript and sends `{ type: "candidate_answer", content: text }`.
* **Text-to-Speech (`SpeechSynthesis`)**:
  - When `{ type: "ai_question" }` arrives over WebSocket, call:
    ```javascript
    const utterance = new SpeechSynthesisUtterance(data.content);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    window.speechSynthesis.speak(utterance);
    ```

---

### Engine D: Real-Time WebSocket Protocol
* **Connect**: `ws://localhost:8000/ws/interview/{interview_id}`
* **Messages Sent by Client to Server**:
  1. `candidate_answer`: `{"type": "candidate_answer", "content": "..."}`
  2. `body_language_sample`: `{"type": "body_language_sample", "eye_contact_score": 85.0, ...}`
  3. `proctoring_violation`: `{"type": "proctoring_violation", "violation_type": "tab_switch", ...}`
* **Messages Received by Client from Server**:
  1. `ai_question`:
     ```json
     {
       "type": "ai_question",
       "round_type": "coding",
       "question_idx": 1,
       "content": "Given a string s, find the longest substring...",
       "difficulty": "medium",
       "question": { "title": "...", "starter_code": { "python": "..." }, "test_cases": [...] }
     }
     ```
  2. `proctoring_warning`: `{"type": "proctoring_warning", "message": "Integrity alert: tab_switch recorded."}`
  3. `interview_completed`: `{"type": "interview_completed", "message": "Interview finished! Generating report..."}`

---

## 🔗 Backend API Integration Contract

| Method | Endpoint | Description | Request Body / Form | Response |
|---|---|---|---|---|
| `POST` | `/api/resume/upload` | Upload PDF/DOCX resume | `multipart/form-data` (`file`) | `ResumeParseResponse` |
| `GET` | `/api/resume/{id}` | Get parsed resume details | None | `ResumeParseResponse` |
| `POST` | `/api/profile/scrape-from-resume/{id}` | Scrapes mentioned profiles | None | `ScrapedProfilesData` |
| `POST` | `/api/question/generate` | Generate targeted question bank | `QuestionBankRequest` | `QuestionBankResponse` |
| `POST` | `/api/interview/start` | Start 30-min interview session | `CreateInterviewRequest` | `InterviewSessionResponse` |
| `GET` | `/api/interview/{id}` | Fetch session & question bank | None | `InterviewSessionResponse` |
| `POST` | `/api/interview/{id}/code` | Safe AST code runner | `CodeSubmissionRequest` | `CodeSubmissionResult` |
| `GET` | `/api/feedback/{id}` | Get finalized feedback report | None | `FeedbackReportResponse` |
| `GET` | `/api/feedback/user/history` | Get past interviews for user | None | `List[FeedbackReportResponse]` |

---

## 🎯 Verification Checklist for the Frontend Developer
- [ ] Next.js 15 App Router structure configured.
- [ ] Camera stream renders with active eye-contact & confidence HUD via TensorFlow.js.
- [ ] Monaco Code Editor disables copy/paste and detects tab switches.
- [ ] Web Speech API enables hands-free voice interviews with audio waveform animation.
- [ ] WebSocket streams questions, answers, and telemetry in real time.
- [ ] Feedback page visualizes all scores, proctoring metrics, and the 14-day study roadmap.
