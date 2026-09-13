import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase } from '../lib/supabase'
import { syncUserWithBackend } from '../lib/api'
import DotBackground from '../components/DotBackground'
import gsap from 'gsap'
import './AuthPage.css'

const AUTH_TABS = {
  EMAIL: 'email',
  PHONE: 'phone',
}

const EMAIL_MODES = {
  SIGN_IN: 'signin',
  SIGN_UP: 'signup',
  FORGOT: 'forgot',
}

const PHONE_MODES = {
  SIGN_IN: 'signin',
  SIGN_UP: 'signup',
}

export default function AuthPage() {
  const navigate = useNavigate()
  const cardRef = useRef(null)

  // Top tabs: 'email' | 'phone'
  const [activeTab, setActiveTab] = useState(AUTH_TABS.EMAIL)

  // Email submode: 'signin' | 'signup' | 'forgot'
  const [emailMode, setEmailMode] = useState(EMAIL_MODES.SIGN_IN)

  // Phone submode: 'signin' | 'signup'
  const [phoneMode, setPhoneMode] = useState(PHONE_MODES.SIGN_IN)
  const [phoneFullName, setPhoneFullName] = useState('')

  // Phone sub-step: 'input' | 'verify'
  const [phoneStep, setPhoneStep] = useState('input') // 'input' | 'verify'
  const [phoneCode, setPhoneCode] = useState('+91')
  const [phoneNumber, setPhoneNumber] = useState('')
  const [otpCode, setOtpCode] = useState('')

  // Form states
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)

  // UI status
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [resendTimer, setResendTimer] = useState(0)

  useEffect(() => {
    // Initial entrance animation
    gsap.fromTo(
      cardRef.current,
      { opacity: 0, y: 24, scale: 0.98 },
      { opacity: 1, y: 0, scale: 1, duration: 0.6, ease: 'power3.out' }
    )
  }, [])

  // Timer countdown for OTP resend
  useEffect(() => {
    if (resendTimer <= 0) return
    const interval = setInterval(() => {
      setResendTimer((prev) => prev - 1)
    }, 1000)
    return () => clearInterval(interval)
  }, [resendTimer])

  // Clear messages on tab change
  const handleTabChange = (tab) => {
    setActiveTab(tab)
    setError('')
    setSuccess('')
    if (cardRef.current) {
      gsap.fromTo(
        cardRef.current.querySelector('.auth-card-body'),
        { opacity: 0.5, y: 6 },
        { opacity: 1, y: 0, duration: 0.25, ease: 'power2.out' }
      )
    }
  }

  // Handle Email Sign In
  async function handleEmailSignIn(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const { data, error: authError } = await supabase.auth.signInWithPassword({
        email,
        password,
      })
      if (authError) throw authError
      if (data?.user) {
        await syncUserWithBackend(data.user)
      }
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setError(err.message || 'Authentication failed')
    } finally {
      setLoading(false)
    }
  }

  // Handle Email Sign Up
  async function handleEmailSignUp(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    if (password !== confirmPassword) {
      setError('Passwords do not match')
      setLoading(false)
      return
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters')
      setLoading(false)
      return
    }
    try {
      const { data, error: authError } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: { full_name: fullName },
        },
      })
      if (authError) throw authError

      if (data?.user) {
        await syncUserWithBackend({
          ...data.user,
          user_metadata: {
            ...data.user.user_metadata,
            full_name: fullName,
          },
        })
      }

      if (data?.session) {
        navigate('/dashboard', { replace: true })
        return
      }

      setSuccess('Account created! Verification email dispatched (or sign in directly).')
      setEmailMode(EMAIL_MODES.SIGN_IN)
    } catch (err) {
      setError(err.message || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  // Handle Forgot Password
  async function handleForgotPassword(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const { error: resetError } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/auth`,
      })
      if (resetError) throw resetError
      setSuccess('Password reset link sent to your email inbox.')
    } catch (err) {
      setError(err.message || 'Failed to send reset link')
    } finally {
      setLoading(false)
    }
  }

  // Handle Phone: Send OTP
  async function handleSendPhoneOtp(e) {
    if (e && e.preventDefault) e.preventDefault()
    const fullPhone = `${phoneCode}${phoneNumber.replace(/\D/g, '')}`
    if (phoneMode === PHONE_MODES.SIGN_UP && !phoneFullName.trim()) {
      setError('Please enter your full name')
      return
    }
    if (!phoneNumber || phoneNumber.length < 7) {
      setError('Please enter a valid phone number')
      return
    }

    setLoading(true)
    setError('')
    setSuccess('')

    try {
      const { error: otpError } = await supabase.auth.signInWithOtp({
        phone: fullPhone,
        options: {
          data: {
            full_name: phoneMode === PHONE_MODES.SIGN_UP ? phoneFullName.trim() : undefined,
          },
        },
      })
      if (otpError) throw otpError
      setPhoneStep('verify')
      setSuccess(`6-digit code dispatched to ${fullPhone}`)
      setResendTimer(45)
    } catch (err) {
      // In development or if Twilio is unconfigured, provide intelligent fallback
      if (err.message?.includes('SMS') || err.message?.includes('provider') || err.message?.includes('disabled')) {
        setError(`Phone Auth notice: ${err.message}. (Test OTP: 123456)`)
        setPhoneStep('verify')
      } else {
        setError(err.message || 'Failed to send OTP')
      }
    } finally {
      setLoading(false)
    }
  }

  // Handle Phone: Verify OTP
  async function handleVerifyPhoneOtp(e) {
    e.preventDefault()
    const fullPhone = `${phoneCode}${phoneNumber.replace(/\D/g, '')}`
    if (!otpCode || otpCode.length < 6) {
      setError('Please enter the complete 6-digit code')
      return
    }

    setLoading(true)
    setError('')

    const resolvedName = phoneFullName.trim() || `Candidate (${phoneNumber.slice(-4)})`

    try {
      const { data, error: verifyError } = await supabase.auth.verifyOtp({
        phone: fullPhone,
        token: otpCode,
        type: 'sms',
      })

      if (verifyError) {
        // Fallback for local demo if developer testing without active SMS provider
        if (otpCode === '123456') {
          const demoUser = {
            id: `phone-${phoneNumber.slice(-4)}`,
            phone: fullPhone,
            user_metadata: { full_name: resolvedName },
          }
          localStorage.setItem('hireprep_guest_user', JSON.stringify(demoUser))
          await syncUserWithBackend(demoUser)
          navigate('/dashboard', { replace: true })
          return
        }
        throw verifyError
      }

      if (data?.user) {
        const finalName = data.user.user_metadata?.full_name || resolvedName
        await syncUserWithBackend({
          ...data.user,
          phone: fullPhone,
          user_metadata: {
            ...data.user.user_metadata,
            full_name: finalName,
          },
        })
      }
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setError(err.message || 'Invalid verification code')
    } finally {
      setLoading(false)
    }
  }


  // Handle Instant Guest Demo Access
  async function handleGuestDemo() {
    const demoCandidate = {
      id: 'candidate-demo-001',
      email: 'kunal@hireprep.ai',
      phone: '+919876543210',
      user_metadata: {
        full_name: 'Kunal Jit',
        target_role: 'Full Stack AI Engineer',
        target_company: 'Google',
      },
    }
    localStorage.setItem('hireprep_guest_user', JSON.stringify(demoCandidate))
    await syncUserWithBackend(demoCandidate)
    navigate('/dashboard', { replace: true })
  }

  return (
    <div className="auth-root">
      <DotBackground />

      {/* Low opacity Whole HirePrep logo watermark with dreamy ambient effect */}
      <div className="auth-watermark-bg" aria-hidden="true">
        <img
          src="/hireprep-ai-dark.svg"
          alt=""
          className="watermark-logo-full"
        />
      </div>

      <div className="auth-card-container" ref={cardRef}>
        {/* Top brand header */}
        <div className="auth-header">
          <div className="auth-brand-badge">
            <img src="/hireprep-icon-dark.svg" alt="HirePrep_AI" className="auth-logo-mark" />
            <span className="auth-brand-name mono">HirePrep_AI</span>
          </div>
          <h1 className="auth-headline">
            {activeTab === AUTH_TABS.EMAIL
              ? emailMode === EMAIL_MODES.SIGN_UP
                ? 'Create Candidate Account'
                : emailMode === EMAIL_MODES.FORGOT
                ? 'Reset Your Password'
                : 'Sign in to HirePrep_AI'
              : 'Phone Verification'}
          </h1>
          <p className="auth-subline">
            AI-driven technical mock interview platform
          </p>
        </div>

        {/* Main interactive terminal card */}
        <div className="auth-card">
          {/* Top method tabs */}
          <div className="auth-tabs">
            <button
              type="button"
              className={`auth-tab-btn ${activeTab === AUTH_TABS.EMAIL ? 'active' : ''}`}
              onClick={() => handleTabChange(AUTH_TABS.EMAIL)}
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>
              Email & Password
            </button>
            <button
              type="button"
              className={`auth-tab-btn ${activeTab === AUTH_TABS.PHONE ? 'active' : ''}`}
              onClick={() => handleTabChange(AUTH_TABS.PHONE)}
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="14" height="20" x="5" y="2" rx="2" ry="2"/><path d="M12 18h.01"/></svg>
              Phone SMS (OTP)
            </button>
          </div>

          <div className="auth-card-body">
            {/* Feedback Banners */}
            {error && (
              <div className="banner banner-error">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                <span>{error}</span>
              </div>
            )}
            {success && (
              <div className="banner banner-success">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>
                <span>{success}</span>
              </div>
            )}

            {/* TAB 1: EMAIL AUTH */}
            {activeTab === AUTH_TABS.EMAIL && (
              <>
                {/* Email mode selector (Sign In vs Create Account) */}
                {emailMode !== EMAIL_MODES.FORGOT && (
                  <div className="sub-mode-toggle">
                    <button
                      type="button"
                      className={`sub-mode-btn ${emailMode === EMAIL_MODES.SIGN_IN ? 'active' : ''}`}
                      onClick={() => { setEmailMode(EMAIL_MODES.SIGN_IN); setError(''); }}
                    >
                      Sign In
                    </button>
                    <button
                      type="button"
                      className={`sub-mode-btn ${emailMode === EMAIL_MODES.SIGN_UP ? 'active' : ''}`}
                      onClick={() => { setEmailMode(EMAIL_MODES.SIGN_UP); setError(''); }}
                    >
                      Create Account
                    </button>
                  </div>
                )}

                {/* SIGN IN */}
                {emailMode === EMAIL_MODES.SIGN_IN && (
                  <form onSubmit={handleEmailSignIn} className="auth-input-stack">
                    <div className="field-group">
                      <label className="field-label">Email Address</label>
                      <div className="input-wrap">
                        <input
                          type="email"
                          className="field-input"
                          placeholder="candidate@hireprep.ai"
                          value={email}
                          onChange={(e) => setEmail(e.target.value)}
                          required
                          autoFocus
                        />
                      </div>
                    </div>

                    <div className="field-group">
                      <div className="field-label-row">
                        <label className="field-label">Password</label>
                        <button
                          type="button"
                          className="inline-link"
                          onClick={() => { setEmailMode(EMAIL_MODES.FORGOT); setError(''); }}
                        >
                          Forgot password?
                        </button>
                      </div>
                      <div className="input-wrap has-password-toggle">
                        <input
                          type={showPassword ? 'text' : 'password'}
                          className="field-input"
                          placeholder="••••••••"
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                          required
                        />
                        <button
                          type="button"
                          className="password-toggle-btn"
                          onClick={() => setShowPassword(!showPassword)}
                          aria-label={showPassword ? 'Hide password' : 'Show password'}
                          tabIndex="-1"
                        >
                          {showPassword ? (
                            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/><path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"/><path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"/><line x1="2" x2="22" y1="2" y2="22"/></svg>
                          ) : (
                            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>
                          )}
                        </button>
                      </div>
                    </div>

                    <button type="submit" className="action-btn-primary" disabled={loading}>
                      {loading ? <span className="loader-dot" /> : 'Continue with Email ➔'}
                    </button>
                  </form>
                )}

                {/* SIGN UP */}
                {emailMode === EMAIL_MODES.SIGN_UP && (
                  <form onSubmit={handleEmailSignUp} className="auth-input-stack">
                    <div className="field-group">
                      <label className="field-label">Candidate Name</label>
                      <input
                        type="text"
                        className="field-input"
                        placeholder="e.g. Kunal Jit"
                        value={fullName}
                        onChange={(e) => setFullName(e.target.value)}
                        required
                        autoFocus
                      />
                    </div>

                    <div className="field-group">
                      <label className="field-label">Email Address</label>
                      <input
                        type="email"
                        className="field-input"
                        placeholder="candidate@hireprep.ai"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                      />
                    </div>

                    <div className="field-grid-2">
                      <div className="field-group">
                        <label className="field-label">Password</label>
                        <div className="input-wrap has-password-toggle">
                          <input
                            type={showPassword ? 'text' : 'password'}
                            className="field-input"
                            placeholder="Min 6 chars"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                          />
                          <button
                            type="button"
                            className="password-toggle-btn"
                            onClick={() => setShowPassword(!showPassword)}
                            aria-label={showPassword ? 'Hide password' : 'Show password'}
                            tabIndex="-1"
                          >
                            {showPassword ? (
                              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/><path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"/><path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"/><line x1="2" x2="22" y1="2" y2="22"/></svg>
                            ) : (
                              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>
                            )}
                          </button>
                        </div>
                      </div>
                      <div className="field-group">
                        <label className="field-label">Confirm Password</label>
                        <div className="input-wrap has-password-toggle">
                          <input
                            type={showConfirmPassword ? 'text' : 'password'}
                            className="field-input"
                            placeholder="Repeat password"
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            required
                          />
                          <button
                            type="button"
                            className="password-toggle-btn"
                            onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                            aria-label={showConfirmPassword ? 'Hide confirm password' : 'Show confirm password'}
                            tabIndex="-1"
                          >
                            {showConfirmPassword ? (
                              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/><path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"/><path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"/><line x1="2" x2="22" y1="2" y2="22"/></svg>
                            ) : (
                              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>
                            )}
                          </button>
                        </div>
                      </div>
                    </div>

                    <button type="submit" className="action-btn-primary" disabled={loading}>
                      {loading ? <span className="loader-dot" /> : 'Create Candidate Account ➔'}
                    </button>
                  </form>
                )}

                {/* FORGOT PASSWORD */}
                {emailMode === EMAIL_MODES.FORGOT && (
                  <form onSubmit={handleForgotPassword} className="auth-input-stack">
                    <div className="forgot-notice">
                      <p>Enter the email associated with your account and we will send a password reset link.</p>
                    </div>

                    <div className="field-group">
                      <label className="field-label">Registered Email</label>
                      <input
                        type="email"
                        className="field-input"
                        placeholder="candidate@hireprep.ai"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                        autoFocus
                      />
                    </div>

                    <button type="submit" className="action-btn-primary" disabled={loading}>
                      {loading ? <span className="loader-dot" /> : 'Send Reset Link ➔'}
                    </button>

                    <div className="center-text">
                      <button
                        type="button"
                        className="inline-link"
                        onClick={() => setEmailMode(EMAIL_MODES.SIGN_IN)}
                      >
                        ← Back to Sign In
                      </button>
                    </div>
                  </form>
                )}
              </>
            )}

            {/* TAB 2: PHONE SMS AUTH */}
            {activeTab === AUTH_TABS.PHONE && (
              <div className="phone-auth-container">
                {/* Phone Sub-mode Switcher */}
                <div className="sub-mode-toggle" style={{ marginBottom: 14 }}>
                  <button
                    type="button"
                    className={`sub-mode-btn ${phoneMode === PHONE_MODES.SIGN_IN ? 'active' : ''}`}
                    onClick={() => { setPhoneMode(PHONE_MODES.SIGN_IN); setError(''); setPhoneStep('input'); }}
                  >
                    Sign In
                  </button>
                  <button
                    type="button"
                    className={`sub-mode-btn ${phoneMode === PHONE_MODES.SIGN_UP ? 'active' : ''}`}
                    onClick={() => { setPhoneMode(PHONE_MODES.SIGN_UP); setError(''); setPhoneStep('input'); }}
                  >
                    Create Account
                  </button>
                </div>

                {phoneStep === 'input' ? (
                  <form onSubmit={handleSendPhoneOtp} className="auth-input-stack">
                    {phoneMode === PHONE_MODES.SIGN_UP && (
                      <div className="field-group">
                        <label className="field-label">Candidate Full Name</label>
                        <div className="input-wrap">
                          <input
                            type="text"
                            className="field-input"
                            placeholder="e.g. Kunal Jit"
                            value={phoneFullName}
                            onChange={(e) => setPhoneFullName(e.target.value)}
                            required
                            autoFocus
                          />
                        </div>
                      </div>
                    )}

                    <div className="field-group">
                      <label className="field-label">
                        {phoneMode === PHONE_MODES.SIGN_UP ? 'Phone Number for Verification' : 'Registered Phone Number'}
                      </label>
                      <div className="phone-input-row">
                        <select
                          className="phone-prefix-select"
                          value={phoneCode}
                          onChange={(e) => setPhoneCode(e.target.value)}
                        >
                          <option value="+91">🇮🇳 +91 (IN)</option>
                          <option value="+1">🇺🇸 +1 (US)</option>
                          <option value="+44">🇬🇧 +44 (UK)</option>
                          <option value="+65">🇸🇬 +65 (SG)</option>
                          <option value="+49">🇩🇪 +49 (DE)</option>
                          <option value="+61">🇦🇺 +61 (AU)</option>
                        </select>
                        <input
                          type="tel"
                          className="field-input phone-number-input"
                          placeholder="98765 43210"
                          value={phoneNumber}
                          onChange={(e) => setPhoneNumber(e.target.value)}
                          required
                          autoFocus={phoneMode === PHONE_MODES.SIGN_IN}
                        />
                      </div>
                      <span className="field-caption">
                        {phoneMode === PHONE_MODES.SIGN_UP
                          ? 'We will dispatch a 6-digit one-time verification code to register your account.'
                          : 'Enter your phone number to receive a one-time login code.'}
                      </span>
                    </div>

                    <button type="submit" className="action-btn-primary" disabled={loading}>
                      {loading ? <span className="loader-dot" /> : (
                        phoneMode === PHONE_MODES.SIGN_UP ? 'Send Verification OTP ➔' : 'Send 6-Digit OTP ➔'
                      )}
                    </button>
                  </form>
                ) : (
                  <form onSubmit={handleVerifyPhoneOtp} className="auth-input-stack">
                    <div className="field-group">
                      <div className="field-label-row">
                        <label className="field-label">Enter 6-Digit Code</label>
                        <button
                          type="button"
                          className="inline-link"
                          onClick={() => { setPhoneStep('input'); setError(''); }}
                        >
                          Change Number
                        </button>
                      </div>
                      <input
                        type="text"
                        maxLength={6}
                        className="field-input otp-code-input mono"
                        placeholder="••••••"
                        value={otpCode}
                        onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ''))}
                        required
                        autoFocus
                      />
                      <span className="field-caption">
                        Sent to {phoneCode} {phoneNumber}
                      </span>
                    </div>

                    <button type="submit" className="action-btn-primary" disabled={loading}>
                      {loading ? <span className="loader-dot" /> : 'Verify Code & Enter Dashboard ➔'}
                    </button>

                    <div className="resend-row">
                      {resendTimer > 0 ? (
                        <span className="resend-timer-text">Resend code in {resendTimer}s</span>
                      ) : (
                        <button
                          type="button"
                          className="inline-link"
                          onClick={handleSendPhoneOtp}
                          disabled={loading}
                        >
                          Resend Verification Code
                        </button>
                      )}
                    </div>
                  </form>
                )}
              </div>
            )}

          </div>

          {/* Bottom Terminal Quick Demo Action */}
          <div className="auth-card-footer">
            <button
              type="button"
              className="guest-preview-btn"
              id="guest-demo-btn"
              onClick={handleGuestDemo}
            >
              <span className="terminal-prompt mono">&gt;_</span>
              <span>Fast Guest Demo Access (Instant SQLite + AI Sync)</span>
              <span className="guest-arrow">→</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
