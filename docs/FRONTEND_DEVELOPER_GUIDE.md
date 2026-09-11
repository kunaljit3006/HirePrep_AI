# 💻 HirePrep_AI — Comprehensive Frontend Feature Guide & Architecture

> **Purpose**: This document provides a complete conceptual, behavioral, and architectural description of every feature the frontend developer needs to build for **HirePrep_AI**.
>
> **Core Philosophy**: HirePrep_AI is not a simple form or a generic chatbot. It is an **immersive, high-stakes technical interview simulator** that mirrors the pressure, proctoring, and depth of real interviews at companies like Google, Amazon, Microsoft, and Uber.

---

## 📑 Table of Contents
1. [System Architecture: Frontend vs Backend Division of Labor](#1-system-architecture-frontend-vs-backend-division-of-labor)
2. [Feature 1: The Camera Vision & Body Language Engine](#feature-1-the-camera-vision--body-language-engine)
3. [Feature 2: The Proctored Anti-Cheat Code Editor](#feature-2-the-proctored-anti-cheat-code-editor)
4. [Feature 3: The Voice & Speech Processing Engine](#feature-3-the-voice--speech-processing-engine)
5. [Feature 4: The 3-Panel Live Interview Room](#feature-4-the-3-panel-live-interview-room)
6. [Feature 5: Resume Parsing & Job Targeting Onboarding](#feature-5-resume-parsing--job-targeting-onboarding)
7. [Feature 6: Candidate Analytics Dashboard](#feature-6-candidate-analytics-dashboard)
8. [Feature 7: Holistic Feedback Report & 14-Day Study Roadmap](#feature-7-holistic-feedback-report--14-day-study-roadmap)
9. [Feature 8: Real-Time WebSocket Communication Protocol](#feature-8-real-time-websocket-communication-protocol)
10. [Design System & Aesthetic Standards](#design-system--aesthetic-standards)

---

## 1. System Architecture: Frontend vs Backend Division of Labor

To achieve **sub-second latency**, **100% candidate privacy**, and **zero server GPU costs ($0)**, the application uses an intelligent hybrid design:

```
+-----------------------------------------------------------------------------------+
| FRONTEND (Runs in Candidate's Browser)                                             |
|                                                                                   |
|  [Webcam Feed] ──► [TensorFlow.js Face Mesh] ──► Computes Eye Contact & Confidence |
|  [Microphone]  ──► [Web Speech API]          ──► Speech-to-Text Transcriptions    |
|  [Keyboard]    ──► [Monaco Editor Listener]  ──► Blocks Paste & Logs Tab Switches |
|                                                                                   |
|  All heavy computer vision & audio runs locally on the candidate's GPU/CPU.       |
|  Video and audio streams are NEVER uploaded to any server.                         |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼ (Lightweight JSON telemetry via WebSocket)
+-----------------------------------------------------------------------------------+
| BACKEND (FastAPI + LangGraph)                                                     |
|                                                                                   |
|  - Agent 1: Parses Resumes & Detects Profiles                                     |
|  - Agent 2: Scrapes GitHub Codebases & LeetCode Stats                             |
|  - Agent 3: Researches Questions from Reddit, LeetCode Discuss, & HackerNews      |
|  - Agent 4: Orchestrates Interview Turns & Adaptive Difficulty Routing            |
|  - Agent 5: Correlates Camera Telemetry with Transcript to Generate Reports       |
+-----------------------------------------------------------------------------------+
```

---

## Feature 1: The Camera Vision & Body Language Engine

### What is this feature?
In a real technical interview, hiring managers evaluate more than just code syntax—they assess **eye contact, confidence under pressure, nervous fidgeting, and overall poise**. 

The camera is **MANDATORY** in HirePrep_AI. The interview will not begin unless camera access is granted.

### Is this Frontend or Backend?
* **Video Capture & Neural Network Inference**: **100% FRONTEND**.
* **Scoring & Correlation**: **BACKEND**.

### How does it work scientifically?
Using **MediaPipe Face Mesh (via TensorFlow.js)** running inside the browser, the frontend maps **468 3D geometric facial landmarks** across every video frame:

1. **Eye Contact Analysis**:
   - The model tracks the 3D iris center landmarks (`468`, `473`) relative to the inner and outer eye corners (`33`, `133`, `362`, `263`).
   - If the candidate looks directly at the interviewer on screen or into the webcam, the gaze ratio is centered (score: **90% - 100%**).
   - If the candidate looks down at cheat notes or glances sideways at a second monitor, the ratio deviates significantly (score drops to **30% - 50%**).
2. **Confidence & Composure Score**:
   - **Brow Furrowing**: Tracks the distance between eyebrow landmarks (`70` and `300`). Furrowed brows indicate stress or uncertainty.
   - **Mouth Tension**: Distinguishes relaxed speech from nervous lip-compression or jaw-clenching.
   - **Blink Rate**: Measures blinks per minute (normal speech: 15–20/min; rapid blinking >40/min indicates anxiety spikes).
3. **Head Stability & Poise**:
   - Calculates 3D head pitch, yaw, and roll using the vector between the nose tip (`1`) and chin (`152`).
   - Distinguishes confident, upright posture from nervous head-swaying or slouching.
4. **Anti-Cheat Presence Detection**:
   - Confirms that **exactly one person** is in the frame. If the candidate ducks away, or if a second face appears, a violation is recorded.

### The Real-Time HUD (Heads-Up Display)
During the interview, the candidate sees their own webcam feed in a sleek glassmorphic overlay displaying a live **Eye Contact Meter (e.g. 92%)** and a **Confidence Pulse Indicator** that turns green when composed and amber when looking away for prolonged periods.

---

## Feature 2: The Proctored Anti-Cheat Code Editor

### What is this feature?
Top tech interviews do not allow candidates to copy-paste solutions from ChatGPT, StackOverflow, or external IDEs. When the coding round begins, an integrated **Monaco Editor** (the engine behind VS Code) opens with built-in proctoring restrictions.

### How does it behave?
1. **Copy-Paste Disabled**:
   - Intercepts `Ctrl+C`, `Ctrl+V`, `Ctrl+X` (and `Cmd` variants on Mac).
   - Right-click context menus are completely disabled within the editor.
   - Attempting to paste triggers an immediate, polite warning banner: *"Clipboard paste is disabled during proctored coding rounds."*
2. **Tab-Switch & Blur Detection**:
   - Listens to `document.visibilitychange` and `window.onblur`.
   - If the candidate switches tabs or minimizes the browser to check an answer, the frontend instantly logs a `tab_switch` violation with a precise timestamp.
3. **DevTools Blocking**:
   - Intercepts `F12`, `Ctrl+Shift+I`, and `Ctrl+Shift+J` to prevent inspecting web elements or network requests.
4. **In-Browser Code Execution**:
   - The candidate can run code in **Python** or **JavaScript**.
   - Clicking `[Run Code]` submits the code to the backend sandbox (`/api/interview/{id}/code`), which executes test cases (both visible and hidden) and returns output, execution time (in ms), and test assertions without system imports.

---

## Feature 3: The Voice & Speech Processing Engine

### What is this feature?
To make mock interviews feel real, candidates can speak their answers naturally rather than typing everything into a chat box.

### How does it behave?
1. **Speech-to-Text (STT)**:
   - Uses the browser-native `SpeechRecognition` API.
   - While the candidate speaks, live interim text appears in their input bubble.
   - When the candidate pauses or clicks `[Done Answering]`, the final transcript is sent to the backend.
2. **Text-to-Speech (TTS)**:
   - When the AI interviewer asks a question or follow-up, `window.speechSynthesis` speaks the question aloud using a natural, professional tone.
   - An interactive **Audio Waveform Visualizer** animates on the AI interviewer's avatar while the AI is speaking.
3. **Mute & Push-to-Talk Controls**:
   - Candidates can mute their microphone or switch to text chat at any time if they are in a noisy environment.

---

## Feature 4: The 3-Panel Live Interview Room

### What is this feature?
The main interview workspace where the candidate spends the 30-minute session.

### The 3-Panel Layout:
* **Panel 1 (Top Navigation Bar)**:
  - Shows Target Company logo, Candidate Role (e.g. `Google — SDE-2`), Current Round indicator (`Coding`, `Behavioral`, or `System Design`), and a countdown timer (`28:45`).
* **Panel 2 (Left Column — Interviewer & Video HUD)**:
  - **AI Interviewer Card**: Avatar with animated speech waveform, showing the current question text.
  - **Candidate Video Card**: Live webcam feed showing the eye-contact meter and confidence badge.
  - **Live Transcript Card**: Scrollable chronological dialogue history between interviewer and candidate.
* **Panel 3 (Right Column — Interactive Workspace)**:
  - **Monaco Code Editor**: Opens during coding rounds with syntax highlighting, line numbers, and theme toggling.
  - **Test Case Runner**: Renders test case inputs, expected outputs, and actual results with green/red status tags.
  - **Architecture Whiteboard (Optional Tab)**: For system design rounds, provides a simple canvas to sketch components.

---

## Feature 5: Resume Parsing & Job Targeting Onboarding

### What is this feature?
The setup flow where candidates configure their interview before entering the room.

### How does it behave?
1. **Interactive File Uploader**:
   - Drag-and-drop zone for `.pdf` and `.docx` resumes.
   - Instantly uploads to `POST /api/resume/upload`.
   - Renders a real-time extraction preview showing candidate name, extracted skills pills (Languages, Frameworks, Cloud), and detected coding profiles (GitHub, LeetCode, Codeforces, Kaggle).
2. **Interview Customizer**:
   - **Company**: Searchable dropdown (e.g., Google, Amazon, Microsoft, Meta, Netflix, Uber, or Custom Startup).
   - **Role**: SDE-1, SDE-2, Fullstack, Frontend, Backend, Machine Learning.
   - **Location**: India, US, Europe, Remote.
   - **Difficulty**: Easy, Medium, Hard.
3. **Hardware Readiness Check (Gatekeeper)**:
   - Verifies webcam stream and microphone input levels.
   - Displays a green checkmark when both devices are operational. The `[Enter Interview Room]` button remains disabled until hardware is validated.

---

## Feature 6: Candidate Analytics Dashboard

### What is this feature?
The candidate's personal preparation command center (`/dashboard`).

### Key Elements:
* **Readiness Radar Chart**: Visualizes performance across 5 key competencies:
  - *Data Structures & Algorithms*
  - *System Design & Scalability*
  - *Behavioral & Leadership*
  - *Communication Quality*
  - *Body Language & Eye Contact*
* **Interview History Feed**:
  - Cards for every past interview showing company logo, score (`88 / 100`), grade (`A`), date, and a direct `[View Feedback]` link.
* **Preparation Streaks & Stats**:
  - Total interview hours logged, questions answered, and integrity score average.

---

## Feature 7: Holistic Feedback Report & 14-Day Study Roadmap

### What is this feature?
After completing an interview, the candidate is routed to `/feedback/[id]`. This is not just a score—it is an actionable, comprehensive diagnostic report.

### Key Elements:
1. **Overall Grade & Hire Recommendation**:
   - Score circular gauge (0 to 100).
   - Big Letter Grade badge (`A+`, `A`, `B+`, `B`, `C`, `D`, `F`).
   - Official hiring committee status: **"Strong Hire"**, **"Hire"**, **"Leaning Hire"**, or **"No Hire"**.
2. **Per-Section Score Breakdown**:
   - Individual score bars for Coding, System Design, Resume Deep-Dive, and Behavioral.
   - Expandable accordions detailing specific strengths and weaknesses for each round.
3. **Camera & Body Language Report**:
   - Average Eye Contact percentage.
   - Confidence score and posture stability rating.
   - Behavioral notes (e.g. *"Maintained steady eye contact; composure remained solid under tough follow-up questions"*).
4. **Proctoring Integrity Report**:
   - Integrity score starting at 100 with clear accounting of any tab-switches or paste attempts.
5. **Personalized 14-Day Interactive Study Roadmap**:
   - A day-by-day interactive study guide (Day 1 through Day 14).
   - Tailored specifically to the candidate's weak areas identified during the interview.
   - Each day contains actionable goals and direct links to NeetCode, LeetCode, and ByteByteGo guides.

---

## Feature 8: Real-Time WebSocket Communication Protocol

### Connection:
`ws://localhost:8000/ws/interview/{interview_id}`

### Message Flows:
1. **Interview Start**:
   - Server immediately pushes the first AI greeting and question:
     ```json
     {
       "type": "ai_question",
       "round_type": "behavioral",
       "question_idx": 0,
       "content": "Welcome to your Google mock interview! Let's begin...",
       "difficulty": "medium",
       "question": { "title": "...", "description": "..." }
     }
     ```
2. **Candidate Answers & Clarifying Cross-Questions**:
   - Client sends speech-to-text transcript or typed text:
     ```json
     { "type": "candidate_answer", "content": "I approached this by using multithreading..." }
     ```
   - **Cross-Questioning / Clarification Questions**: Candidates can ask clarifying questions at any time (e.g. *"Do we have to write the brute force first or direct optimal solution?"*, or *"Are duplicates allowed in the input?"*):
     ```json
     { "type": "candidate_clarification", "content": "Should I start with brute force or jump straight to the optimal approach?" }
     ```
   - **AI Interviewer Clarification Response**: The AI interviewer answers supportively, does NOT penalize or score, and keeps the question active:
     ```json
     {
       "type": "ai_clarification",
       "content": "Good question! Feel free to outline the brute force intuition briefly in 30 seconds so we are aligned on the baseline, but please implement the optimal solution directly in code. Go ahead whenever you are ready!",
       "is_clarification": true,
       "round_type": "coding",
       "question_idx": 0
     }
     ```
   - **Progressive Hint Request & Response**: Candidates can request hints (or trigger via an `[Ask for a Hint]` button):
     ```json
     { "type": "candidate_hint_request", "content": "Can I get a hint on optimizing space?" }
     ```
     Server delivers graduated hints (Tier 1: Intuition nudge -> Tier 2: Structural pointer -> Tier 3: Concrete approach):
     ```json
     {
       "type": "ai_hint",
       "content": "Sure! Here is a quick pointer: Consider using a Hash Map or Two Pointers to trade a small amount of memory for instant O(1) lookups.",
       "is_hint": true,
       "hint_tier": 1,
       "round_type": "coding",
       "question_idx": 0,
       "speech_clarity": {
         "total_words": 142,
         "filler_words": { "um": 2, "uh": 1, "like": 3, "basically": 1, "you know": 0, "actually": 0 }
       }
     }
     ```
   - **AI Interviewer Concept Probing (Active Listening)**: When candidate drops a concept (Redis, multithreading, Kafka):
     ```json
     {
       "type": "ai_follow_up",
       "content": "Got it. You brought up multithreading there—how did you prevent race conditions or handle synchronization when multiple threads write to shared memory?",
       "is_follow_up": true,
       "probed_topic": "multithreading synchronization and race conditions"
     }
     ```
   - **Live Approach Verification & "Right Track" Affirmations**:
     When a candidate thinks out loud, asks *"Am I on the right track?"*, or clicks an `[Am I on the Right Track?]` co-pilot button:
     ```json
     { "type": "candidate_approach_check", "content": "I am thinking of using a two-pointer approach starting from both ends to find the pair. Am I on the right track?" }
     ```
     The AI interviewer responds immediately as an attentive co-pilot, validating their direction:
     ```json
     {
       "type": "ai_affirmation",
       "content": "Yes, exactly! You are on the right track with that approach. That will give you optimal time and space efficiency. Go ahead and start implementing it!",
       "is_approach_check": true,
       "track_status": "on_track",
       "round_type": "coding",
       "question_idx": 0
     }
     ```
     *(Frontend displays a positive green "On Track" badge, plays interviewer voice encouragement, and allows candidate to proceed without question disruption).*
3. **Body Language Stream (Every 1 Second)**:
   - Client sends in-browser face mesh metrics:
     ```json
     {
       "type": "body_language_sample",
       "eye_contact_score": 89.2,
       "confidence_score": 84.0,
       "head_stability_score": 92.5,
       "face_in_frame": true
     }
     ```
4. **Anti-Cheat Alerts**:
   - Client detects paste attempt or tab switch and sends:
     ```json
     { "type": "proctoring_violation", "violation_type": "tab_switch" }
     ```
   - Server returns instant warning notification to candidate:
     ```json
     { "type": "proctoring_warning", "message": "Tab switch recorded in proctoring report." }
     ```
5. **Session Finished**:
   - When all rounds conclude, server emits:
     ```json
     { "type": "interview_completed", "message": "Generating your diagnostic report..." }
     ```
   - Client automatically redirects to `/feedback/[id]`.

---

## Design System & Aesthetic Standards

* **Dark Theme Default**: Deep space black (`#0a0d14`) with dark slate cards (`#121824`).
* **Accents**: High-visibility HirePrep green (`#00ea88`) for positive actions and scores; electric purple (`#7928ca`) for AI activity; neon pink (`#ff0080`) for proctoring violations.
* **Micro-Animations**:
  - Smooth scale transitions on card hovers.
  - Fluid audio visualizer ripples.
  - Pulsing status dots (`Live Recording`, `AI Speaking`, `Evaluating Answer`).
* **Typography**: Modern geometric typography (`Outfit` or `Inter` for headings and body; `JetBrains Mono` for code).
