import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { uploadResumeFile, startInterviewSession, fetchLatestResume } from '../lib/api'
import './StartInterviewModal.css'

const LOADING_STEPS = [
  { id: 1, label: 'Ingesting resume & parsing skill graphs', icon: '📄' },
  { id: 2, label: 'Mapping company interview rubrics & bar-raiser criteria', icon: '🏢' },
  { id: 3, label: 'Synthesizing tailored algorithmic & behavioral questions', icon: '🧠' },
  { id: 4, label: 'Calibrating AI interviewer persona & voice synthesis', icon: '🎙️' },
  { id: 5, label: 'Initializing real-time AST sandbox & audio pipeline', icon: '⚡' },
]

const INTERVIEW_TIPS = [
  {
    category: 'ALGORITHMS & CODING',
    tip: 'Always state your time and space complexity before implementing code. Interviewers look for trade-off awareness.',
  },
  {
    category: 'SYSTEM DESIGN',
    tip: 'Start with Back-of-the-Envelope calculations: Read vs Write QPS, daily active users, and 5-year storage projections.',
  },
  {
    category: 'BEHAVIORAL (STAR)',
    tip: 'Spend 70% of your answer on Action and Result. Quantify business impact with concrete metrics and milestones.',
  },
  {
    category: 'COMMUNICATION',
    tip: 'Think out loud continuously. A silent candidate gives the interviewer no data to grade your problem-solving depth.',
  },
  {
    category: 'CACHE STRATEGY',
    tip: 'Clarify eviction policy (LRU vs LFU) and cache invalidation mechanics (Cache-Aside, Write-Through, Write-Behind).',
  },
]

export default function StartInterviewModal({ isOpen, onClose, defaultCompany = '', defaultRole = '', defaultLocation = '' }) {
  const navigate = useNavigate()
  const fileInputRef = useRef(null)

  // Form State
  const [resumeFile, setResumeFile] = useState(null)
  const [activeResume, setActiveResume] = useState(null)
  const [activeResumeLoading, setActiveResumeLoading] = useState(false)
  const [company, setCompany] = useState(defaultCompany || 'Google')
  const [role, setRole] = useState(defaultRole || 'Full Stack AI Engineer')
  const [location, setLocation] = useState(defaultLocation || 'India / Hybrid')
  const [durationMin, setDurationMin] = useState(30)
  const [difficulty, setDifficulty] = useState('medium')
  const [dragOver, setDragOver] = useState(false)

  // Auto-fetch candidate's existing active parsed resume on open
  useEffect(() => {
    if (!isOpen) return
    let isMounted = true
    setActiveResumeLoading(true)
    fetchLatestResume()
      .then((res) => {
        if (isMounted && res && res.resume_id) {
          setActiveResume(res)
        }
      })
      .catch((err) => {
        // No previously uploaded resume; silent graceful fallback
        console.log('No prior resume found:', err?.message)
      })
      .finally(() => {
        if (isMounted) setActiveResumeLoading(false)
      })
    return () => {
      isMounted = false
    }
  }, [isOpen])

  // Loading State
  const [isLoading, setIsLoading] = useState(false)
  const [currentStepIdx, setCurrentStepIdx] = useState(0)
  const [tipIdx, setTipIdx] = useState(0)
  const [errorMessage, setErrorMessage] = useState('')

  // Rotate tips while loading
  useEffect(() => {
    if (!isLoading) return
    const tipInterval = setInterval(() => {
      setTipIdx((prev) => (prev + 1) % INTERVIEW_TIPS.length)
    }, 3200)
    return () => clearInterval(tipInterval)
  }, [isLoading])

  // Advance simulated progress steps
  useEffect(() => {
    if (!isLoading) return
    const stepInterval = setInterval(() => {
      setCurrentStepIdx((prev) => {
        if (prev < LOADING_STEPS.length - 1) {
          return prev + 1
        }
        return prev
      })
    }, 2400)
    return () => clearInterval(stepInterval)
  }, [isLoading])

  if (!isOpen) return null

  // File handling
  const handleFileDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0]
      validateAndSetFile(file)
    }
  }

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0])
    }
  }

  const validateAndSetFile = (file) => {
    const validExts = ['.pdf', '.docx', '.doc', '.txt']
    const name = file.name.toLowerCase()
    const isValid = validExts.some((ext) => name.endsWith(ext))
    if (!isValid) {
      setErrorMessage('Please upload a valid PDF, DOCX, or TXT resume.')
      return
    }
    setErrorMessage('')
    setResumeFile(file)
  }

  // Submit and launch
  const handleStartInterview = async (e) => {
    e.preventDefault()
    if (!company.trim()) {
      setErrorMessage('Please specify target company name.')
      return
    }
    if (!role.trim()) {
      setErrorMessage('Please specify target engineering role.')
      return
    }

    setErrorMessage('')
    setIsLoading(true)
    setCurrentStepIdx(0)

    try {
      let resumeId = null

      // Step 1: Upload resume if provided, else use active resume
      if (resumeFile) {
        try {
          const uploadRes = await uploadResumeFile(resumeFile)
          resumeId = uploadRes.resume_id
        } catch (uploadErr) {
          console.warn('Resume upload warning:', uploadErr.message)
          // Continue if resume parsing has fallback
        }
      } else if (activeResume && activeResume.resume_id) {
        resumeId = activeResume.resume_id
      }

      // Step 2: Initialize interview session
      const payload = {
        company: company.trim(),
        role: role.trim(),
        location: location.trim(),
        duration_min: Number(durationMin) || 30,
        difficulty,
        resume_id: resumeId,
      }

      const session = await startInterviewSession(payload)
      
      // Let user enjoy final step briefly before navigation
      setCurrentStepIdx(LOADING_STEPS.length - 1)
      setTimeout(() => {
        setIsLoading(false)
        onClose()
        navigate(`/interview/${session.interview_id}`, { state: { session } })
      }, 1000)
    } catch (err) {
      setIsLoading(false)
      setErrorMessage(err.message || 'Failed to assemble interview session. Please try again.')
    }
  }

  return (
    <div className="start-modal-overlay">
      <div className={`start-modal-card ${isLoading ? 'is-loading-view' : ''}`} onClick={(e) => e.stopPropagation()}>
        {!isLoading ? (
          <>
            {/* Modal Header */}
            <div className="start-modal-header">
              <div className="header-badge-row">
                <div className="badge-pill">
                  <span className="badge-dot"></span>
                  <span className="mono">AI MOCK SESSION SETUP</span>
                </div>
              </div>
              <h2 className="start-modal-title">Launch Your Technical Interview</h2>
              <p className="start-modal-subtitle">
                Upload your resume and choose your target company. Our AI agent will curate live coding and behavioral challenges tailored to you.
              </p>
              <button type="button" className="start-close-btn" onClick={onClose} aria-label="Close">
                ✕
              </button>
            </div>

            {errorMessage && (
              <div className="start-error-banner">
                <span>{errorMessage}</span>
              </div>
            )}

            {/* Modal Body / Form */}
            <form onSubmit={handleStartInterview} className="start-form">
              {/* 1. Resume Upload Dropzone */}
              <div className="form-section">
                <label className="section-label">
                  Candidate Resume <span className="label-opt">(PDF, DOCX, TXT)</span>
                </label>

                {resumeFile ? (
                  <div className="resume-selected-card">
                    <div className="selected-file-info">
                      <span className="file-icon">📄</span>
                      <div className="file-details">
                        <span className="file-name">{resumeFile.name}</span>
                        <span className="file-size mono">
                          {(resumeFile.size / 1024).toFixed(1)} KB • Ready for AI Parsing
                        </span>
                      </div>
                    </div>
                    <button
                      type="button"
                      className="file-remove-btn"
                      onClick={() => setResumeFile(null)}
                      title="Remove file"
                    >
                      ✕
                    </button>
                  </div>
                ) : activeResume ? (
                  <div className="active-resume-card">
                    <div className="active-resume-info">
                      <div className="active-badge-icon">✓</div>
                      <div className="file-details">
                        <span className="file-name">
                          {(activeResume.data?.candidate_name || activeResume.data?.name)
                            ? `${activeResume.data.candidate_name || activeResume.data.name}'s Resume Attached`
                            : 'Active Profile CV Attached'}
                        </span>
                        <span className="file-size mono">
                          {activeResume.data?.projects?.length || 0} Projects • {
                            Array.isArray(activeResume.data?.skills)
                              ? activeResume.data.skills.length
                              : Object.values(activeResume.data?.skills || {}).flat().length
                          } Skills Detected • Auto-Bound
                        </span>
                      </div>
                    </div>
                    <button
                      type="button"
                      className="file-change-btn"
                      onClick={() => fileInputRef.current?.click()}
                    >
                      Change Resume
                    </button>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".pdf,.docx,.doc,.txt"
                      onChange={handleFileSelect}
                      style={{ display: 'none' }}
                    />
                  </div>
                ) : (
                  <div
                    className={`resume-dropzone ${dragOver ? 'drag-active' : ''}`}
                    onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                    onDragLeave={() => setDragOver(false)}
                    onDrop={handleFileDrop}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".pdf,.docx,.doc,.txt"
                      onChange={handleFileSelect}
                      style={{ display: 'none' }}
                    />
                    <div className="dropzone-icon">📁</div>
                    <div className="dropzone-prompt">
                      <span className="dropzone-highlight">Click to upload resume</span> or drag and drop file here
                    </div>
                    <span className="dropzone-sub">
                      Your resume allows the AI to extract your exact projects, tech stack &amp; coding handles
                    </span>
                  </div>
                )}
              </div>

              {/* 2. Company & Role Inputs (Manual entry) */}
              <div className="form-grid">
                {/* Target Company */}
                <div className="form-field">
                  <label className="section-label">Target Company</label>
                  <input
                    type="text"
                    className="modal-input"
                    placeholder="e.g. Google, ZS Associates, Amazon, Goldman Sachs, Startup"
                    value={company}
                    onChange={(e) => setCompany(e.target.value)}
                    required
                  />
                </div>

                {/* Target Role */}
                <div className="form-field">
                  <label className="section-label">Target Engineering Role</label>
                  <input
                    type="text"
                    className="modal-input"
                    placeholder="e.g. SDE II, Full Stack AI Engineer, Frontend Architect, Backend Developer"
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                    required
                  />
                </div>

                {/* Location */}
                <div className="form-field">
                  <label className="section-label">Target Location / Market</label>
                  <input
                    type="text"
                    className="modal-input"
                    placeholder="e.g. India / Hybrid, Remote, San Francisco, London"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                  />
                </div>

                {/* Difficulty & Duration */}
                <div className="form-field-dual">
                  <div className="sub-field">
                    <label className="section-label">Difficulty</label>
                    <select
                      className="modal-input modal-select"
                      value={difficulty}
                      onChange={(e) => setDifficulty(e.target.value)}
                    >
                      <option value="easy">Standard (Entry / Mid)</option>
                      <option value="medium">Rigorous (Senior SDE)</option>
                      <option value="hard">Bar-Raiser (Staff / Lead)</option>
                    </select>
                  </div>
                  <div className="sub-field">
                    <label className="section-label">Duration</label>
                    <select
                      className="modal-input modal-select"
                      value={durationMin}
                      onChange={(e) => setDurationMin(Number(e.target.value))}
                    >
                      <option value={15}>15 Minutes (Sprint)</option>
                      <option value={30}>30 Minutes (Full Round)</option>
                      <option value={45}>45 Minutes (Deep Dive)</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Submit Button */}
              <div className="start-modal-footer">
                <button type="button" className="btn-modal-cancel" onClick={onClose}>
                  Cancel
                </button>
                <button type="submit" className="btn-modal-launch">
                  <span>Synthesize AI Mock Interview</span>
                  <span className="btn-arrow">➔</span>
                </button>
              </div>
            </form>
          </>
        ) : (
          /* ═══════════════════════════════════════════════════
             ENJOYABLE / ENGAGING LOADING EXPERIENCE
             ═══════════════════════════════════════════════════ */
          <div className="loading-chamber">
            {/* Cybernetic AI Radar Ring */}
            <div className="radar-container">
              <div className="radar-ring radar-ring-3"></div>
              <div className="radar-ring radar-ring-2"></div>
              <div className="radar-ring radar-ring-1"></div>
              <div className="radar-sweep"></div>
              <div className="radar-core">
                <span className="core-icon">⚡</span>
              </div>
            </div>

            <div className="loading-header">
              <span className="status-pill mono">ORCHESTRATING INTERVIEW ENGINE</span>
              <h2 className="loading-title">
                Assembling Interview for <span className="text-emerald">{company}</span>
              </h2>
              <p className="loading-subtitle">
                Role: <span className="mono text-light">{role}</span> • Target: {location}
              </p>
            </div>

            {/* Step-by-Step Progress Pipeline */}
            <div className="loading-pipeline">
              {LOADING_STEPS.map((step, idx) => {
                const isDone = idx < currentStepIdx
                const isCurrent = idx === currentStepIdx
                return (
                  <div
                    key={step.id}
                    className={`pipeline-step ${isDone ? 'step-done' : ''} ${isCurrent ? 'step-active' : ''}`}
                  >
                    <div className="step-indicator">
                      {isDone ? '✓' : isCurrent ? <span className="pulse-dot" /> : step.id}
                    </div>
                    <span className="step-label">
                      {step.icon} {step.label}
                    </span>
                  </div>
                )
              })}
            </div>

            {/* Entertainment / Candidate Warm-Up Card */}
            <div className="warmup-card">
              <div className="warmup-header">
                <span className="warmup-badge mono">💡 WARM-UP TIP • {INTERVIEW_TIPS[tipIdx].category}</span>
                <span className="warmup-dots">● ● ●</span>
              </div>
              <p className="warmup-text">
                "{INTERVIEW_TIPS[tipIdx].tip}"
              </p>
            </div>

            <div className="loading-footer-notice mono">
              Hang tight! Deep reasoning models are assembling customized rubrics...
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
