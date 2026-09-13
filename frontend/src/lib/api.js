import { supabase } from './supabase'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/**
 * Sends an authenticated API request to the FastAPI backend.
 * Automatically attaches Supabase JWT or local candidate header.
 */
export async function apiRequest(endpoint, options = {}) {
  const headers = new Headers(options.headers || {})
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  // Check Supabase session
  const { data: { session } } = await supabase.auth.getSession()
  const token = session?.access_token
  const guestUserStr = localStorage.getItem('hireprep_guest_user')

  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  } else if (guestUserStr) {
    try {
      const guest = JSON.parse(guestUserStr)
      headers.set('x-user-id', guest.id || 'candidate-default-001')
    } catch {
      headers.set('x-user-id', 'candidate-default-001')
    }
  }

  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    })

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }))
      let errMsg = `HTTP ${res.status}`
      if (typeof err.detail === 'string') {
        errMsg = err.detail
      } else if (Array.isArray(err.detail)) {
        errMsg = err.detail.map((d) => (d.msg ? `${d.loc ? d.loc.slice(1).join('.') + ': ' : ''}${d.msg}` : JSON.stringify(d))).join('; ')
      } else if (err.detail && typeof err.detail === 'object') {
        errMsg = JSON.stringify(err.detail)
      } else if (err.message) {
        errMsg = err.message
      }
      throw new Error(errMsg)
    }

    return await res.json()
  } catch (err) {
    console.warn(`[Backend API] Error calling ${endpoint}:`, err.message)
    throw err
  }
}

/**
 * Synchronizes user data with the FastAPI backend UserModel
 */
export async function syncUserWithBackend(user) {
  if (!user) return null
  try {
    return await apiRequest('/api/auth/sync', {
      method: 'POST',
      body: JSON.stringify({
        id: user.id,
        email: user.email || '',
        phone: user.phone || '',
        name: user.user_metadata?.full_name || user.email?.split('@')[0] || 'Candidate',
        avatar_url: user.user_metadata?.avatar_url || '',
        github_handle: user.user_metadata?.user_name || '',
        metadata: user.user_metadata || {},
      }),
    })
  } catch (err) {
    console.warn('[Sync] Backend sync note:', err.message)
    return null
  }
}

/**
 * Fetches candidate profile and aggregated interview stats
 */
export async function fetchUserProfile() {
  return await apiRequest('/api/auth/me')
}

/**
 * Updates candidate career preferences and coding profiles in the FastAPI backend
 */
export async function updateUserProfile(profileData) {
  return await apiRequest('/api/auth/profile', {
    method: 'PUT',
    body: JSON.stringify(profileData),
  })
}

/**
 * Permanently deletes the candidate's account and all associated data
 */
export async function deleteUserAccount() {
  return await apiRequest('/api/auth/account', {
    method: 'DELETE',
  })
}

/**
 * Uploads a resume file (PDF/DOCX) to the backend for AI parsing
 */
export async function uploadResumeFile(file) {
  const formData = new FormData()
  formData.append('file', file)
  return await apiRequest('/api/resume/upload', {
    method: 'POST',
    body: formData,
  })
}

/**
 * Fetches the user's latest parsed resume if available
 */
export async function fetchLatestResume() {
  return await apiRequest('/api/resume/latest')
}

/**
 * Initializes an AI mock interview session tailored to the resume and company
 */
export async function startInterviewSession(payload) {
  return await apiRequest('/api/interview/start', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

/**
 * Fetches an ongoing or completed interview session by ID
 */
export async function fetchInterviewSession(interviewId) {
  return await apiRequest(`/api/interview/${interviewId}`)
}

/**
 * Fetches past interview session history for candidate
 */
export async function fetchInterviewHistory() {
  return await apiRequest('/api/interview/history')
}

/**
 * Evaluates candidate code in the AST Python sandbox
 */
export async function submitCodeAnswer(interviewId, questionId, code) {
  return await apiRequest(`/api/interview/${interviewId}/code`, {
    method: 'POST',
    body: JSON.stringify({ question_id: questionId, code }),
  })
}

/**
 * Submits candidate's architecture whiteboard diagram for SPOF and bottleneck evaluation
 */
export async function submitArchitectureDiagram(interviewId, diagramData) {
  return await apiRequest(`/api/interview/${interviewId}/diagram`, {
    method: 'POST',
    body: JSON.stringify({ diagram: diagramData }),
  })
}

/**
 * Retrieves the comprehensive feedback report for an interview session
 */
export async function fetchFeedbackReport(interviewId) {
  return await apiRequest(`/api/feedback/${interviewId}`)
}

/**
 * Manually triggers feedback report generation if not already generated
 */
export async function generateFeedbackReport(interviewId) {
  return await apiRequest(`/api/feedback/${interviewId}/generate`, {
    method: 'POST',
  })
}

/**
 * Retrieves candidate analytics overview (trends, radar, strengths & weaknesses)
 */
export async function fetchCandidateAnalyticsSummary() {
  return await apiRequest('/api/feedback/analytics/summary')
}

/**
 * Helper to construct the WebSocket URL for live interview streaming
 */
export function getInterviewWebSocketUrl(interviewId) {
  const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000'
  const wsBase = apiBase.replace(/^http/, 'ws')
  return `${wsBase}/api/interview/ws/${interviewId}`
}
