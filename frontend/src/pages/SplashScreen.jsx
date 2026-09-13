import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase } from '../lib/supabase'
import DotBackground from '../components/DotBackground'
import gsap from 'gsap'
import './SplashScreen.css'

const SYSTEM_LOGS = [
  'Initializing LangGraph Orchestration Engine...',
  'Connecting AST Python Execution Sandbox...',
  'Calibrating Neural Speech & Telemetry Models...',
  'Systems Armed. Welcome to HirePrep_AI.',
]

export default function SplashScreen({ onComplete }) {
  const navigate = useNavigate()
  const logoRef = useRef(null)
  const containerRef = useRef(null)
  const [mottoText, setMottoText] = useState('')
  const [systemLog, setSystemLog] = useState(SYSTEM_LOGS[0])
  const [progress, setProgress] = useState(0)

  const fullMotto = 'Ace your next tech interview with AI'

  const proceed = async () => {
    gsap.to(containerRef.current, {
      opacity: 0,
      scale: 1.03,
      filter: 'blur(8px)',
      duration: 0.45,
      ease: 'power3.inOut',
      onComplete: async () => {
        if (onComplete) {
          onComplete()
        } else {
          const guest = localStorage.getItem('hireprep_guest_user')
          const { data: { session } } = await supabase.auth.getSession()
          if (session || guest) {
            navigate('/dashboard', { replace: true })
          } else {
            navigate('/auth', { replace: true })
          }
        }
      },
    })
  }

  useEffect(() => {
    // 1. Cinematic Logo Entrance
    const tl = gsap.timeline()

    tl.fromTo(
      logoRef.current,
      { scale: 0.65, opacity: 0, y: 30, filter: 'blur(10px)' },
      { scale: 1, opacity: 1, y: 0, filter: 'blur(0px)', duration: 0.9, ease: 'back.out(1.8)' }
    )

    // 2. Typewriter Motto
    let charIndex = 0
    const typeTimer = setTimeout(() => {
      const typeInterval = setInterval(() => {
        charIndex++
        setMottoText(fullMotto.slice(0, charIndex))
        if (charIndex >= fullMotto.length) {
          clearInterval(typeInterval)
        }
      }, 30)
      return () => clearInterval(typeInterval)
    }, 400)

    // 3. Progress Percentage & System Logs
    let currentProg = 0
    const progInterval = setInterval(() => {
      currentProg += Math.floor(Math.random() * 8) + 4
      if (currentProg >= 100) {
        currentProg = 100
        clearInterval(progInterval)
      }
      setProgress(currentProg)

      if (currentProg > 75) {
        setSystemLog(SYSTEM_LOGS[3])
      } else if (currentProg > 50) {
        setSystemLog(SYSTEM_LOGS[2])
      } else if (currentProg > 25) {
        setSystemLog(SYSTEM_LOGS[1])
      }
    }, 90)

    // 4. Auto-proceed when ready
    const navTimer = setTimeout(() => {
      proceed()
    }, 3200)

    return () => {
      clearTimeout(typeTimer)
      clearInterval(progInterval)
      clearTimeout(navTimer)
    }
  }, [navigate])

  return (
    <div className="splash-container" ref={containerRef}>
      <DotBackground />

      {/* Top action: Quick Skip */}
      <button
        type="button"
        className="splash-skip-btn mono"
        onClick={proceed}
      >
        Skip Intro ➔
      </button>

      <div className="splash-content">
        {/* Dreamy Ambient Pulsing Emerald Glow */}
        <div className="splash-glow-ring" />

        {/* Brand Logo with Glowing Sweep Aura */}
        <div className="splash-logo-wrapper" ref={logoRef}>
          <div className="splash-logo-aura" />
          <img
            src="/hireprep-ai-dark.svg"
            alt="HirePrep_AI"
            className="splash-logo"
          />
        </div>

        {/* Typewriter Motto */}
        <div className="splash-motto-wrapper">
          <p className="splash-motto mono">
            {mottoText}
            <span className="splash-cursor">|</span>
          </p>
        </div>

        {/* Live Audio Equalizer Bars (Representing Voice Telemetry) */}
        <div className="splash-equalizer">
          <span className="eq-bar eq-1" />
          <span className="eq-bar eq-2" />
          <span className="eq-bar eq-3" />
          <span className="eq-bar eq-4" />
          <span className="eq-bar eq-5" />
          <span className="eq-bar eq-6" />
          <span className="eq-bar eq-7" />
        </div>

        {/* System Terminal Status & Micro-Counter */}
        <div className="splash-terminal-footer">
          <div className="splash-log-row">
            <span className="terminal-prompt mono">&gt;</span>
            <span className="splash-log-text mono">{systemLog}</span>
          </div>

          <div className="splash-progress-track">
            <div
              className="splash-progress-fill"
              style={{ width: `${progress}%` }}
            />
          </div>

          <span className="splash-percent mono">{progress}%</span>
        </div>
      </div>
    </div>
  )
}
