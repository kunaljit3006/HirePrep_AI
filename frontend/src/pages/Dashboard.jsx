import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase } from '../lib/supabase'
import { fetchUserProfile } from '../lib/api'
import DotBackground from '../components/DotBackground'
import AccountSettingsModal from '../components/AccountSettingsModal'
import StartInterviewModal from '../components/StartInterviewModal'
import InterviewHistoryModal from '../components/InterviewHistoryModal'
import AnalyticsModal from '../components/AnalyticsModal'
import gsap from 'gsap'
import './Dashboard.css'

export default function Dashboard() {
  const navigate = useNavigate()
  const [user, setUser] = useState(null)
  const [profile, setProfile] = useState(null)
  const [isAccountSettingsOpen, setIsAccountSettingsOpen] = useState(false)
  const [isStartInterviewOpen, setIsStartInterviewOpen] = useState(false)
  const [isHistoryOpen, setIsHistoryOpen] = useState(false)
  const [isAnalyticsOpen, setIsAnalyticsOpen] = useState(false)

  const navRef = useRef(null)
  const heroRef = useRef(null)
  const cardsRef = useRef(null)
  const statsRef = useRef(null)

  useEffect(() => {
    async function loadUserAndProfile() {
      const guest = localStorage.getItem('hireprep_guest_user')
      let currentUser = null

      if (guest) {
        currentUser = JSON.parse(guest)
        setUser(currentUser)
      } else {
        const { data: { user: u } } = await supabase.auth.getUser()
        currentUser = u
        setUser(u)
      }

      // Fetch profile & stats from FastAPI backend
      try {
        const data = await fetchUserProfile()
        if (data) {
          setProfile(data)
        }
      } catch (e) {
        console.warn('Backend profile fetch note:', e.message)
      }
    }

    loadUserAndProfile()
  }, [])

  useEffect(() => {
    if (!user) return

    const tl = gsap.timeline({ defaults: { ease: 'power3.out' } })

    tl.fromTo(
      navRef.current,
      { opacity: 0, y: -16 },
      { opacity: 1, y: 0, duration: 0.45 }
    ).fromTo(
      heroRef.current,
      { opacity: 0, y: 20 },
      { opacity: 1, y: 0, duration: 0.55 },
      '-=0.15'
    )

    const cards = cardsRef.current?.querySelectorAll('.action-card')
    if (cards?.length) {
      tl.fromTo(
        cards,
        { opacity: 0, y: 24 },
        { opacity: 1, y: 0, duration: 0.45, stagger: 0.1 },
        '-=0.25'
      )
    }

    if (statsRef.current) {
      tl.fromTo(
        statsRef.current,
        { opacity: 0, y: 16 },
        { opacity: 1, y: 0, duration: 0.45 },
        '-=0.2'
      )
    }
  }, [user])

  async function handleLogout() {
    localStorage.removeItem('hireprep_guest_user')
    await supabase.auth.signOut()
    navigate('/auth', { replace: true })
  }

  const displayName =
    profile?.name ||
    user?.user_metadata?.full_name ||
    user?.email?.split('@')[0] ||
    'Candidate'

  const isPhoneUser = Boolean(user?.phone || profile?.phone)
  const avatarUrl = profile?.avatar_url || user?.user_metadata?.avatar_url || user?.user_metadata?.picture

  const totalInterviews = profile?.stats?.total_interviews ?? 0
  const avgScore = profile?.stats?.average_score ? `${profile.stats.average_score}/100` : '—'

  // Render circular avatar respecting the rule:
  // "i circle will show the email profile pic if user used email or first letter of his name if phone no"
  const renderNavAvatar = () => {
    if (isPhoneUser) {
      return (
        <div className="nav-avatar">
          {displayName.charAt(0).toUpperCase() || 'C'}
        </div>
      )
    }

    if (avatarUrl) {
      return (
        <div className="nav-avatar nav-avatar-img-wrap">
          <img src={avatarUrl} alt={displayName} className="nav-avatar-img" />
        </div>
      )
    }

    return (
      <div className="nav-avatar">
        {displayName.charAt(0).toUpperCase() || 'E'}
      </div>
    )
  }

  return (
    <div className="dashboard-page">
      <DotBackground />

      {/* Navbar */}
      <nav className="dashboard-nav" ref={navRef}>
        <div className="nav-left">
          <img src="/hireprep-ai-dark.svg" alt="HirePrep_AI" className="nav-logo" />
        </div>
        <div className="nav-right">
          <div className="status-pill mono">
            <span className="status-dot"></span>
            CONNECTED
          </div>

          {/* Account Settings Trigger */}
          <button
            type="button"
            className="nav-user-btn"
            onClick={() => setIsAccountSettingsOpen(true)}
            title="Account Settings"
          >
            {renderNavAvatar()}
            <span className="nav-username">{displayName}</span>
            <span className="nav-settings-tag mono">Settings</span>
          </button>
        </div>
      </nav>

      <main className="dashboard-main">
        {/* Hero Section */}
        <section className="dashboard-hero" ref={heroRef}>
          <div className="hero-greeting">
            <div className="hero-badge-row">
              <span className="status-pill mono">
                <span className="status-dot"></span>
                AI-POWERED TECHNICAL INTERVIEW PLATFORM
              </span>
            </div>
            <h1 className="hero-title">
              Welcome back, <span className="text-gradient">{displayName}</span>
            </h1>
            <p className="hero-subtitle">
              Ready to crush your next interview? Launch your tailored technical session below.
            </p>
          </div>
        </section>

        {/* Quick Action Cards */}
        <section className="dashboard-actions" ref={cardsRef}>
          {/* Card 1: Start Interview */}
          <div className="action-card primary-action-card" id="card-new-interview">
            <div className="action-icon-wrapper">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="5 3 19 12 5 21 5 3" />
              </svg>
            </div>
            <h3 className="action-title">Start Real-Time Mock Interview</h3>
            <p className="action-desc">
              Upload your resume and input target company &amp; role. Our AI curates live algorithmic challenges, AST Python execution, and behavioral questions.
            </p>
            <button
              className="btn btn-primary action-btn"
              onClick={() => setIsStartInterviewOpen(true)}
            >
              Begin Interview
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="5" y1="12" x2="19" y2="12" />
                <polyline points="12 5 19 12 12 19" />
              </svg>
            </button>
          </div>

          {/* Card 2: Past Sessions */}
          <div className="action-card" id="card-past-sessions">
            <div className="action-icon-wrapper">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <polyline points="12 6 12 12 16 14" />
              </svg>
            </div>
            <h3 className="action-title">Past Interview History</h3>
            <p className="action-desc">
              Review completed sessions, interviewer latching logs, speech pace analysis, and detailed scoring reports.
            </p>
            <button
              className="btn btn-ghost action-btn"
              onClick={() => setIsHistoryOpen(true)}
            >
              View Past Sessions
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="5" y1="12" x2="19" y2="12" />
                <polyline points="12 5 19 12 12 19" />
              </svg>
            </button>
          </div>

          {/* Card 3: Telemetry & Analytics */}
          <div className="action-card" id="card-analytics">
            <div className="action-icon-wrapper">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="20" x2="18" y2="10" />
                <line x1="12" y1="20" x2="12" y2="4" />
                <line x1="6" y1="20" x2="6" y2="14" />
              </svg>
            </div>
            <h3 className="action-title">Telemetry &amp; Analytics</h3>
            <p className="action-desc">
              Analyze your filler word density, problem-solving latency, concept recall scores, and growth charts across rounds.
            </p>
            <button
              className="btn btn-ghost action-btn"
              onClick={() => setIsAnalyticsOpen(true)}
            >
              Explore Telemetry
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="5" y1="12" x2="19" y2="12" />
                <polyline points="12 5 19 12 12 19" />
              </svg>
            </button>
          </div>
        </section>

        {/* Dynamic Stats Strip */}
        <section className="dashboard-stats glass-card" ref={statsRef}>
          <div className="stat-item">
            <span className="stat-value text-gradient mono">{totalInterviews}</span>
            <span className="stat-label">Total Interviews</span>
          </div>
          <div className="stat-divider" />
          <div className="stat-item">
            <span className="stat-value text-gradient mono">{avgScore}</span>
            <span className="stat-label">Avg AI Score</span>
          </div>
          <div className="stat-divider" />
          <div className="stat-item">
            <span className="stat-value text-gradient mono">Active</span>
            <span className="stat-label">AI Engine Status</span>
          </div>
          <div className="stat-divider" />
          <div className="stat-item">
            <span className="stat-value text-gradient mono">AST Sandbox</span>
            <span className="stat-label">Code Evaluation</span>
          </div>
        </section>
      </main>

      {/* Account Settings Modal (3 options: Change Name, Log Out, Delete Account) */}
      <AccountSettingsModal
        isOpen={isAccountSettingsOpen}
        onClose={() => setIsAccountSettingsOpen(false)}
        user={user}
        profile={profile}
        onProfileUpdated={(updated) => setProfile(updated)}
        onLogout={handleLogout}
      />

      {/* Start Interview Modal (Resume upload, Company, Role, Location, Enjoyable Loading) */}
      <StartInterviewModal
        isOpen={isStartInterviewOpen}
        onClose={() => setIsStartInterviewOpen(false)}
      />

      {/* Past Interview History Modal */}
      <InterviewHistoryModal
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        onLaunchNew={() => setIsStartInterviewOpen(true)}
      />

      {/* Candidate Telemetry & Analytics Modal */}
      <AnalyticsModal
        isOpen={isAnalyticsOpen}
        onClose={() => setIsAnalyticsOpen(false)}
        profile={profile}
      />
    </div>
  )
}

