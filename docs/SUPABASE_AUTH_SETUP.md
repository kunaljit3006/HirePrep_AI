# 🔐 HirePrep_AI — Supabase Authentication & User Management Guide

This guide explains how Supabase Authentication is integrated into **HirePrep_AI** across both Frontend and Backend.

---

## 1. Supabase Project Setup

1. Go to [https://supabase.com](https://supabase.com) and create a free project (e.g. `hireprep-ai`).
2. Go to **Project Settings > API**:
   - Copy **Project URL** (e.g., `https://xyzproject.supabase.co`)
   - Copy **Anon / Public Key** (`eyJhbGciOiJIUzI1NiIsIn...`)
   - Copy **JWT Secret** (under JWT Settings)
3. Under **Authentication > Providers**:
   - Enable **Email / Password**
   - Enable **GitHub OAuth** (recommended for developer interview candidates)
   - Enable **Google OAuth**

---

## 2. Backend Configuration (`backend/.env`)

Add your Supabase credentials to `backend/.env`:

```bash
# Supabase Authentication
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_KEY=your-supabase-anon-key
SUPABASE_JWT_SECRET=your-supabase-jwt-secret
AUTH_ENABLED=true
```

> **Note**: In local development or automated tests, if `SUPABASE_JWT_SECRET` is left empty, the backend automatically operates in development bypass mode, allowing unverified/mock tokens to work seamlessly without crashing.

---

## 3. Frontend Integration (`@supabase/supabase-js`)

### Step 1: Install Supabase Client in Frontend
```bash
npm install @supabase/supabase-js
```

### Step 2: Initialize Supabase Client (`lib/supabase.ts`)
```typescript
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://your-project.supabase.co';
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'your-anon-key';

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
```

### Step 3: Sign In with GitHub or Email
```typescript
// Sign In with GitHub OAuth
export async function signInWithGitHub() {
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: 'github',
    options: {
      redirectTo: `${window.location.origin}/dashboard`
    }
  });
  if (error) console.error("GitHub Login Error:", error.message);
  return data;
}

// Sign In with Email & Password
export async function signInWithEmail(email: string, password: string) {
  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password
  });
  if (error) throw error;
  return data;
}
```

### Step 4: Attaching the Supabase Token to Backend Requests
Every request to HirePrep_AI FastAPI backend should attach the user's Supabase JWT access token in the `Authorization` header:

```typescript
// Helper function to call HirePrep_AI Backend APIs
export async function apiRequest(endpoint: string, options: RequestInit = {}) {
  // Get active Supabase session
  const { data: { session } } = await supabase.auth.getSession();
  const token = session?.access_token;

  const headers = new Headers(options.headers || {});
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(`http://localhost:8000${endpoint}`, {
    ...options,
    headers
  });

  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.detail || 'API request failed');
  }

  return response.json();
}
```

### Step 5: Syncing Candidate Profile After Login
Immediately after a successful login in React/Next.js:
```typescript
supabase.auth.onAuthStateChange(async (event, session) => {
  if (session?.user) {
    // Sync candidate metadata with HirePrep_AI backend
    await apiRequest('/api/auth/sync', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id: session.user.id,
        email: session.user.email,
        name: session.user.user_metadata.full_name || session.user.email?.split('@')[0],
        avatar_url: session.user.user_metadata.avatar_url,
        github_handle: session.user.user_metadata.user_name,
        metadata: session.user.user_metadata
      })
    });
  }
});
```

---

## 4. Backend Authentication & User API Endpoints

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/auth/me` | `GET` | Returns authenticated candidate's profile, synced coding handles, and aggregate interview stats. |
| `/api/auth/sync` | `POST` | Explicitly syncs candidate metadata upon Supabase login. Auto-provisions record in `UserModel`. |
| `/api/auth/profile` | `PUT` | Updates target role, company, location, experience level, and coding handles. |

---

## 5. WebSocket Authentication for Live Interviews
When connecting the live interview room via WebSocket (`ws://localhost:8000/api/interview/{interview_id}/live`):
Pass the user token or user ID via query parameter:
```typescript
const { data: { session } } = await supabase.auth.getSession();
const ws = new WebSocket(
  `ws://localhost:8000/api/interview/${interviewId}/live?user_id=${session?.user.id}`
);
```
HirePrep_AI's WebSocket connection manager verifies the candidate's identity against the session before permitting live speech and vision telemetry.
