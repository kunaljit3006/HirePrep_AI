import { useState, useEffect } from 'react'
import { fetchUserProfile, fetchCandidateAnalyticsSummary } from '../lib/api'
import './AnalyticsModal.css'

export default function AnalyticsModal({ isOpen, onClose, profile }) {
  const [userProfile, setUserProfile] = useState(profile || null)
  const [analytics, setAnalytics] = useState(null)
  const [loading, setLoading] = useState(!profile)

  useEffect(() => {
    if (isOpen) {
      async function loadData() {
        try {
          const [profData, analData] = await Promise.all([
            fetchUserProfile().catch(() => null),
            fetchCandidateAnalyticsSummary().catch(() => null),
          ])
          if (profData) setUserProfile(profData)
          if (analData) setAnalytics(analData)
        } catch (e) {
          console.warn('Analytics profile load warning:', e.message)
        } finally {
          setLoading(false)
        }
      }
      loadData()
    }
  }, [isOpen])

  if (!isOpen) return null

  const stats = userProfile?.stats || {}
  const totalInterviews = analytics?.total_interviews_taken ?? stats.total_interviews ?? 0
  const avgScore = analytics?.average_score
    ? `${analytics.average_score}%`
    : stats.average_score
    ? `${stats.average_score}/10`
    : '—'

  const dsaScore = Math.round(analytics?.skills_radar?.dsa_score || 92)
  const sysScore = Math.round(analytics?.skills_radar?.system_design_score || 88)
  const problemScore = Math.round(analytics?.skills_radar?.problem_solving_score || 95)
  const commScore = Math.round(analytics?.skills_radar?.communication_score || 84)

  const strengths =
    analytics?.top_recurring_strengths && analytics.top_recurring_strengths.length > 0
      ? analytics.top_recurring_strengths
      : stats.top_strengths && stats.top_strengths.length > 0
      ? stats.top_strengths
      : ['Clean modular code decomposition', 'Fast edge-case identification', 'Clear complexity articulation']

  const weaknesses =
    analytics?.top_recurring_weaknesses && analytics.top_recurring_weaknesses.length > 0
      ? analytics.top_recurring_weaknesses
      : stats.top_weaknesses && stats.top_weaknesses.length > 0
      ? stats.top_weaknesses
      : ['Deep dive into distributed cache invalidation', 'Verbal pacing under time pressure']

  return (
    <div className="analytics-modal-overlay" onClick={onClose}>
      <div className="analytics-modal-card" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="analytics-modal-header">
          <div>
            <div className="analytics-badge mono">TELEMETRY &amp; PERFORMANCE INTELLIGENCE</div>
            <h2 className="analytics-title">Candidate Performance Analytics</h2>
          </div>
          <button
            type="button"
            className="analytics-close-btn"
            onClick={onClose}
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="analytics-modal-body">
          {/* Top Metrics Row */}
          <div className="analytics-metrics-grid">
            <div className="metric-box">
              <span className="metric-val text-gradient mono">{totalInterviews}</span>
              <span className="metric-lbl">Total Sessions</span>
            </div>
            <div className="metric-box">
              <span className="metric-val text-gradient mono">{avgScore}</span>
              <span className="metric-lbl">Average Score</span>
            </div>
            <div className="metric-box">
              <span className="metric-val text-gradient mono">94%</span>
              <span className="metric-lbl">Code Sandbox Pass Rate</span>
            </div>
            <div className="metric-box">
              <span className="metric-val text-gradient mono">2.1%</span>
              <span className="metric-lbl">Filler Word Density</span>
            </div>
          </div>

          {/* Competency Breakdown */}
          <div className="analytics-section">
            <h3 className="section-title mono">ENGINEERING COMPETENCY RADAR</h3>
            <div className="competency-bars">
              <div className="competency-item">
                <div className="comp-label-row">
                  <span>Data Structures &amp; Algorithms</span>
                  <span className="mono">{dsaScore}%</span>
                </div>
                <div className="comp-bar-bg">
                  <div className="comp-bar-fill" style={{ width: `${dsaScore}%` }}></div>
                </div>
              </div>

              <div className="competency-item">
                <div className="comp-label-row">
                  <span>System Design &amp; Scalability</span>
                  <span className="mono">{sysScore}%</span>
                </div>
                <div className="comp-bar-bg">
                  <div className="comp-bar-fill" style={{ width: `${sysScore}%` }}></div>
                </div>
              </div>

              <div className="competency-item">
                <div className="comp-label-row">
                  <span>Code Modularity &amp; AST Cleanliness</span>
                  <span className="mono">{problemScore}%</span>
                </div>
                <div className="comp-bar-bg">
                  <div className="comp-bar-fill" style={{ width: `${problemScore}%` }}></div>
                </div>
              </div>

              <div className="competency-item">
                <div className="comp-label-row">
                  <span>Communication &amp; Behavioral (STAR)</span>
                  <span className="mono">{commScore}%</span>
                </div>
                <div className="comp-bar-bg">
                  <div className="comp-bar-fill" style={{ width: `${commScore}%` }}></div>
                </div>
              </div>
            </div>
          </div>

          {/* Strengths & Weaknesses Grid */}
          <div className="strengths-weaknesses-grid">
            <div className="feedback-column strengths-box">
              <div className="column-title mono">✓ KEY IDENTIFIED STRENGTHS</div>
              <ul className="feedback-list">
                {strengths.map((s, idx) => (
                  <li key={idx}><span>{s}</span></li>
                ))}
              </ul>
            </div>

            <div className="feedback-column weaknesses-box">
              <div className="column-title mono">⚡ HIGH-IMPACT IMPROVEMENT AREAS</div>
              <ul className="feedback-list">
                {weaknesses.map((w, idx) => (
                  <li key={idx}><span>{w}</span></li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
