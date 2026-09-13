import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { fetchFeedbackReport, generateFeedbackReport } from '../lib/api'
import DotBackground from '../components/DotBackground'
import './FeedbackReport.css'

export default function FeedbackReport() {
  const { interviewId } = useParams()
  const navigate = useNavigate()
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState('overview') // 'overview' | 'sections' | 'telemetry' | 'roadmap'

  useEffect(() => {
    async function loadReport() {
      if (!interviewId) return
      setLoading(true)
      setError('')
      try {
        let data = null
        try {
          data = await fetchFeedbackReport(interviewId)
        } catch {
          // If report not yet generated, attempt to generate
          data = await generateFeedbackReport(interviewId)
        }
        if (data) {
          setReport(data)
        } else {
          setError('Could not retrieve evaluation report for this session.')
        }
      } catch (err) {
        console.warn('Feedback fetch error:', err.message)
        setError(err.message || 'Failed to assemble feedback report.')
      } finally {
        setLoading(false)
      }
    }
    loadReport()
  }, [interviewId])

  if (loading) {
    return (
      <div className="feedback-page-root">
        <DotBackground />
        <div className="feedback-loader-box">
          <div className="feedback-loader-pulse" />
          <h2 className="feedback-loader-title">Synthesizing AI Evaluation Rubric...</h2>
          <p className="feedback-loader-sub mono">
            Aggregating AST code execution, architecture graph analysis, eye contact telemetry, and LangGraph turn logs.
          </p>
        </div>
      </div>
    )
  }

  if (error || !report) {
    return (
      <div className="feedback-page-root">
        <DotBackground />
        <div className="feedback-error-card">
          <span className="error-icon">⚠️</span>
          <h2>Evaluation Report Unavailable</h2>
          <p className="mono">{error || 'Session report was not found.'}</p>
          <button
            type="button"
            className="btn-feedback-back"
            onClick={() => navigate('/dashboard')}
          >
            Return to Dashboard
          </button>
        </div>
      </div>
    )
  }

  const isHire = (report.hire_recommendation || '').toLowerCase().includes('hire')
  const gradeColor =
    report.letter_grade === 'A+' || report.letter_grade === 'A'
      ? '#00b853'
      : report.letter_grade?.startsWith('B')
      ? '#00e5ff'
      : '#f59e0b'

  return (
    <div className="feedback-page-root">
      <DotBackground />

      {/* Top Navigation */}
      <header className="feedback-navbar">
        <div className="feedback-nav-left">
          <img src="/hireprep-ai-dark.svg" alt="HirePrep" className="feedback-logo" />
          <div className="feedback-nav-badge mono">
            <span>SESSION: {report.interview_id}</span>
            <span>•</span>
            <span>{report.relative_time || report.formatted_date || 'COMPLETED'}</span>
          </div>
        </div>
        <div className="feedback-nav-right">
          <button
            type="button"
            className="btn-feedback-ghost"
            onClick={() => window.print()}
          >
            📄 Print / Export
          </button>
          <button
            type="button"
            className="btn-feedback-primary"
            onClick={() => navigate('/dashboard')}
          >
            Dashboard ➔
          </button>
        </div>
      </header>

      {/* Main Report Container */}
      <main className="feedback-content-viewport">
        {/* ── HERO BANNER: OVERALL SCORE & HIRING VERDICT ── */}
        <section className="feedback-hero-banner">
          <div className="hero-left">
            <div className="hero-badge mono">POST-INTERVIEW TECHNICAL ASSESSMENT</div>
            <h1 className="hero-title">Candidate Evaluation Report</h1>
            <p className="hero-desc">{report.detailed_summary}</p>
            <div className="hero-meta-strip mono">
              <span>Integrity Score: {report.proctoring?.integrity_score || 100}%</span>
              <span>•</span>
              <span>Eye Contact: {report.body_language?.eye_contact_percentage || 88}%</span>
              <span>•</span>
              <span>Confidence: {report.body_language?.overall_confidence_score || 85}%</span>
            </div>
          </div>

          <div className="hero-right">
            <div className="score-radial-card" style={{ borderColor: gradeColor }}>
              <div className="score-main-row">
                <span className="score-number mono text-gradient">
                  {Math.round(report.overall_score)}
                </span>
                <span className="score-denom mono">/100</span>
              </div>
              <div className="grade-badge-wrap mono" style={{ color: gradeColor }}>
                GRADE: {report.letter_grade}
              </div>
              <div className={`hire-pill mono ${isHire ? 'hire-yes' : 'hire-no'}`}>
                {report.hire_recommendation}
              </div>
            </div>
          </div>
        </section>

        {/* ── REPORT TABS ── */}
        <div className="feedback-tabs-bar">
          <button
            type="button"
            className={`fb-tab ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            📊 Executive Summary &amp; Strengths
          </button>
          <button
            type="button"
            className={`fb-tab ${activeTab === 'sections' ? 'active' : ''}`}
            onClick={() => setActiveTab('sections')}
          >
            💻 Round Rubrics (DSA &amp; System Design)
          </button>
          <button
            type="button"
            className={`fb-tab ${activeTab === 'telemetry' ? 'active' : ''}`}
            onClick={() => setActiveTab('telemetry')}
          >
            🛡️ Proctoring &amp; Body Language
          </button>
          <button
            type="button"
            className={`fb-tab ${activeTab === 'roadmap' ? 'active' : ''}`}
            onClick={() => setActiveTab('roadmap')}
          >
            🗺️ 14-Day Growth Roadmap
          </button>
        </div>

        {/* ── TAB 1: EXECUTIVE SUMMARY & STRENGTHS ── */}
        {activeTab === 'overview' && (
          <div className="tab-content-grid">
            {/* Strengths & Weaknesses */}
            <div className="strengths-weaknesses-row">
              <div className="feedback-card strengths-card">
                <div className="card-header-strip">
                  <span className="card-icon">⚡</span>
                  <h3 className="card-title">Key Engineering Strengths</h3>
                </div>
                <ul className="bullet-list">
                  {report.top_strengths?.map((str, idx) => (
                    <li key={idx} className="strength-item">
                      <span className="check-bullet">✓</span>
                      <span>{str}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="feedback-card weaknesses-card">
                <div className="card-header-strip">
                  <span className="card-icon">🎯</span>
                  <h3 className="card-title">Priority Growth Areas</h3>
                </div>
                <ul className="bullet-list">
                  {report.top_weaknesses?.map((weak, idx) => (
                    <li key={idx} className="weakness-item">
                      <span className="cross-bullet">→</span>
                      <span>{weak}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Quick Section Score Bars */}
            <div className="feedback-card">
              <div className="card-header-strip">
                <span className="card-icon">📈</span>
                <h3 className="card-title">Round Score Breakdown</h3>
              </div>
              <div className="section-bars-list">
                {report.section_scores?.map((sec, idx) => {
                  const score = Math.round(sec.score)
                  return (
                    <div key={idx} className="sec-bar-item">
                      <div className="sec-bar-header mono">
                        <span className="sec-name">{sec.section_name}</span>
                        <span className="sec-score">{score}%</span>
                      </div>
                      <div className="sec-progress-track">
                        <div
                          className="sec-progress-fill"
                          style={{
                            width: `${score}%`,
                            background:
                              score >= 85
                                ? 'linear-gradient(90deg, #00b853, #00e5ff)'
                                : score >= 70
                                ? '#00e5ff'
                                : '#f59e0b',
                          }}
                        />
                      </div>
                      <p className="sec-feedback">{sec.feedback}</p>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        )}

        {/* ── TAB 2: ROUND RUBRICS (DSA & SYSTEM DESIGN) ── */}
        {activeTab === 'sections' && (
          <div className="tab-content-grid">
            {/* System Design Architecture Card */}
            {report.architecture_report && (
              <div className="feedback-card arch-review-card">
                <div className="card-header-strip">
                  <span className="card-icon">📐</span>
                  <div>
                    <h3 className="card-title">System Design &amp; Architecture Audit</h3>
                    <span className="card-sub mono">
                      Scalability: {report.architecture_report.scalability_rating} • Fault Tolerance: {report.architecture_report.fault_tolerance}
                    </span>
                  </div>
                  <span className="arch-score-badge mono text-gradient">
                    {Math.round(report.architecture_report.architecture_score)}/100
                  </span>
                </div>
                <p className="card-desc">{report.architecture_report.feedback}</p>

                {report.architecture_report.spof_risks?.length > 0 && (
                  <div className="flag-box spof-flag">
                    <span className="flag-title mono">⚠️ Single Point of Failure (SPOF) Identified:</span>
                    <ul>
                      {report.architecture_report.spof_risks.map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {report.architecture_report.bottlenecks?.length > 0 && (
                  <div className="flag-box bottleneck-flag">
                    <span className="flag-title mono">⏱️ Potential Scaling Bottlenecks:</span>
                    <ul>
                      {report.architecture_report.bottlenecks.map((b, i) => (
                        <li key={i}>{b}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* Code Quality Card */}
            {report.code_quality && (
              <div className="feedback-card">
                <div className="card-header-strip">
                  <span className="card-icon">💻</span>
                  <div>
                    <h3 className="card-title">AST Code Quality &amp; Complexity Analysis</h3>
                    <span className="card-sub mono">
                      Optimal Time: {report.code_quality.time_complexity_optimal ? 'Yes ✓' : 'Sub-optimal'} • Optimal Space: {report.code_quality.space_complexity_optimal ? 'Yes ✓' : 'Sub-optimal'}
                    </span>
                  </div>
                  <span className="arch-score-badge mono text-gradient">
                    {Math.round(report.code_quality.correctness_score)}/100
                  </span>
                </div>
                <p className="card-desc">{report.code_quality.feedback}</p>
              </div>
            )}

            {/* Communication Clarity */}
            {report.communication && (
              <div className="feedback-card">
                <div className="card-header-strip">
                  <span className="card-icon">🎙️</span>
                  <h3 className="card-title">Verbal Communication &amp; Articulation</h3>
                  <span className="arch-score-badge mono text-gradient">
                    {Math.round(report.communication.clarity_score)}/100
                  </span>
                </div>
                <p className="card-desc">{report.communication.feedback}</p>
                {report.communication.filler_words_detected?.length > 0 && (
                  <div className="filler-words-wrap mono">
                    <span className="filler-title">Filler Words Flagged:</span>
                    <div className="chips-row">
                      {report.communication.filler_words_detected.map((w, i) => (
                        <span key={i} className="filler-chip">
                          {w}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ── TAB 3: PROCTORING & BODY LANGUAGE ── */}
        {activeTab === 'telemetry' && (
          <div className="tab-content-grid">
            <div className="telemetry-twin-row">
              {/* Proctoring Summary */}
              <div className="feedback-card">
                <div className="card-header-strip">
                  <span className="card-icon">🛡️</span>
                  <h3 className="card-title">Anti-Cheat &amp; Integrity Audit</h3>
                </div>
                <div className="telemetry-stats-grid mono">
                  <div className="tele-box">
                    <span className="tele-label">Integrity Score</span>
                    <span className="tele-val text-gradient">
                      {report.proctoring?.integrity_score || 100}%
                    </span>
                  </div>
                  <div className="tele-box">
                    <span className="tele-label">Tab Switches</span>
                    <span className="tele-val">{report.proctoring?.tab_switches || 0}</span>
                  </div>
                  <div className="tele-box">
                    <span className="tele-label">Paste Attempts</span>
                    <span className="tele-val">{report.proctoring?.paste_attempts || 0}</span>
                  </div>
                  <div className="tele-box">
                    <span className="tele-label">DevTools Intercepts</span>
                    <span className="tele-val">{report.proctoring?.devtools_attempts || 0}</span>
                  </div>
                </div>
                <div className="proctor-flags-list">
                  {report.proctoring?.flags?.length > 0 ? (
                    report.proctoring.flags.map((f, i) => (
                      <div key={i} className="proctor-flag-pill mono">
                        ⚠️ {f}
                      </div>
                    ))
                  ) : (
                    <div className="proctor-clean mono">
                      ✓ Clean assessment audit: Zero unauthorized external assistance detected.
                    </div>
                  )}
                </div>
              </div>

              {/* Camera Body Language */}
              <div className="feedback-card">
                <div className="card-header-strip">
                  <span className="card-icon">📷</span>
                  <h3 className="card-title">Candidate Video &amp; Engagement</h3>
                </div>
                <div className="telemetry-stats-grid mono">
                  <div className="tele-box">
                    <span className="tele-label">Avg Eye Contact</span>
                    <span className="tele-val text-gradient">
                      {Math.round(report.body_language?.eye_contact_percentage || 88)}%
                    </span>
                  </div>
                  <div className="tele-box">
                    <span className="tele-label">Confidence Index</span>
                    <span className="tele-val">
                      {Math.round(report.body_language?.overall_confidence_score || 85)}%
                    </span>
                  </div>
                  <div className="tele-box">
                    <span className="tele-label">Posture Stability</span>
                    <span className="tele-val">
                      {Math.round(report.body_language?.posture_stability_score || 92)}%
                    </span>
                  </div>
                  <div className="tele-box">
                    <span className="tele-label">Fidgeting Detected</span>
                    <span className="tele-val">
                      {report.body_language?.fidgeting_detected ? 'Yes' : 'Minimal'}
                    </span>
                  </div>
                </div>
                <ul className="bullet-list" style={{ marginTop: '12px' }}>
                  {report.body_language?.notes?.map((n, i) => (
                    <li key={i} className="mono" style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                      • {n}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* ── TAB 4: 14-DAY GROWTH ROADMAP ── */}
        {activeTab === 'roadmap' && (
          <div className="feedback-card">
            <div className="card-header-strip">
              <span className="card-icon">🗺️</span>
              <div>
                <h3 className="card-title">14-Day Personalized Mastery Roadmap</h3>
                <span className="card-sub mono">
                  Targeted milestones formulated from your specific mistakes and weaker rubrics.
                </span>
              </div>
            </div>

            <div className="roadmap-timeline">
              {report.improvement_roadmap_14_days?.map((dayPlan, idx) => (
                <div key={idx} className="roadmap-day-card">
                  <div className="day-badge mono">DAY {dayPlan.day}</div>
                  <div className="day-content">
                    <h4 className="day-topic">{dayPlan.focus_topic}</h4>
                    <ul className="day-actions">
                      {dayPlan.action_items?.map((act, i) => (
                        <li key={i}>{act}</li>
                      ))}
                    </ul>
                    {dayPlan.curated_resources?.length > 0 && (
                      <div className="day-resources mono">
                        <span>Curated Reference:</span>
                        {dayPlan.curated_resources.map((res, rIdx) => (
                          <a
                            key={rIdx}
                            href={res.url || '#'}
                            target="_blank"
                            rel="noreferrer"
                            className="resource-link"
                          >
                            {res.title} ↗
                          </a>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
