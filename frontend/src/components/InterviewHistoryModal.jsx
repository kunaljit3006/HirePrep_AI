import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchInterviewHistory } from '../lib/api'
import './InterviewHistoryModal.css'

export default function InterviewHistoryModal({ isOpen, onClose, onLaunchNew }) {
  const navigate = useNavigate()
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (isOpen) {
      async function loadHistory() {
        setLoading(true)
        setError('')
        try {
          const items = await fetchInterviewHistory()
          setHistory(Array.isArray(items) ? items : [])
        } catch (err) {
          console.warn('History fetch note:', err.message)
          setError(err.message || 'Failed to load past sessions')
        } finally {
          setLoading(false)
        }
      }
      loadHistory()
    }
  }, [isOpen])

  if (!isOpen) return null

  return (
    <div className="history-modal-overlay" onClick={onClose}>
      <div className="history-modal-card" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="history-modal-header">
          <div>
            <div className="history-badge mono">INTERVIEW TELEMETRY LOGS</div>
            <h2 className="history-title">Past Interview History</h2>
          </div>
          <button
            type="button"
            className="history-close-btn"
            onClick={onClose}
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="history-modal-body">
          {loading ? (
            <div className="history-loading-box">
              <span className="history-loader-dot" />
              <span className="mono">Loading completed sessions &amp; scoring reports...</span>
            </div>
          ) : error ? (
            <div className="history-error-box">
              <span>{error}</span>
            </div>
          ) : history.length === 0 ? (
            <div className="history-empty-box">
              <div className="history-empty-icon">📁</div>
              <h3 className="history-empty-title">No Past Interviews Yet</h3>
              <p className="history-empty-desc">
                You haven't completed any mock interviews yet. Launch your first session to receive real-time scoring, interviewer rubrics, and AST feedback.
              </p>
              <button
                type="button"
                className="btn-history-start"
                onClick={() => {
                  onClose()
                  if (onLaunchNew) onLaunchNew()
                }}
              >
                Launch First Mock Interview ➔
              </button>
            </div>
          ) : (
            <div className="history-list">
              {history.map((session) => {
                const score = session.overall_score ? `${session.overall_score}/10` : null
                const recommendation = session.hire_recommendation || session.status || 'In Progress'
                const isHire = recommendation.toLowerCase().includes('hire')

                return (
                  <div key={session.id} className="history-item-card">
                    <div className="history-item-left">
                      <div className="history-company-row">
                        <span className="history-company">{session.company || 'Technical Interview'}</span>
                        <span className="history-badge-role mono">{session.role}</span>
                      </div>
                      <div className="history-item-meta mono">
                        <span>{session.relative_time || session.formatted_date || 'Recent'}</span>
                        <span>•</span>
                        <span>{session.difficulty || 'Medium'}</span>
                        <span>•</span>
                        <span>{session.duration_min || 30} mins</span>
                      </div>
                    </div>

                    <div className="history-item-right">
                      {score && (
                        <div className="history-score-tag">
                          <span className="score-num text-gradient mono">{score}</span>
                          {session.letter_grade && (
                            <span className="grade-num mono">({session.letter_grade})</span>
                          )}
                        </div>
                      )}

                      <span className={`status-pill mono ${isHire ? 'pill-hire' : ''}`}>
                        {recommendation}
                      </span>

                      <button
                        type="button"
                        className="btn-review-session"
                        onClick={() => {
                          onClose()
                          if (session.status === 'completed' || session.overall_score || session.feedback_id) {
                            navigate(`/feedback/${session.id}`)
                          } else {
                            navigate(`/interview/${session.id}`)
                          }
                        }}
                      >
                        {session.status === 'completed' || session.overall_score || session.feedback_id
                          ? 'View Feedback Report ➔'
                          : 'Re-open Chamber ➔'}
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
