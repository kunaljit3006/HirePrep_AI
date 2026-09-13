import './InterviewerAvatar.css'

export default function InterviewerAvatar({
  name = 'AI Interviewer',
  isSpeaking = false,
  isListening = false,
  subtitle = '',
  onToggleMute,
  isMuted = false,
}) {
  return (
    <div className={`gemini-stage-container ${isSpeaking ? 'is-speaking' : ''} ${isListening ? 'is-listening' : ''}`}>
      {/* ── Google Gemini-Style Fluid Luminous Visualizer ── */}
      <div className="gemini-visualizer-wrapper">
        {/* Ambient Aurora Glow Rays */}
        <div className="gemini-ambient-glow" />

        {/* Dynamic Concentric Breathing Wave Rings */}
        <div className="gemini-wave-ring ring-wave-outer" />
        <div className="gemini-wave-ring ring-wave-mid" />
        <div className="gemini-wave-ring ring-wave-inner" />

        {/* Radiant Gemini Core Orb */}
        <div className="gemini-core-orb">
          <div className="gemini-plasma-fluid" />
          <div className="gemini-inner-light" />
          <div className="gemini-sparkle-center" />
        </div>

        {/* Fluid Gemini Frequency Waves Ribbon */}
        <div className="gemini-waves-strip">
          {[40, 65, 95, 70, 100, 80, 60, 90, 75, 45, 85, 55].map((h, i) => (
            <span
              key={i}
              className={`gemini-bar bar-${i} ${isSpeaking ? 'bar-speaking' : isListening ? 'bar-listening' : ''}`}
              style={{ '--bar-scale': `${h}%`, animationDelay: `${(i * 0.09).toFixed(2)}s` }}
            />
          ))}
        </div>

        {/* Minimal Audio Mute Icon */}
        {onToggleMute && (
          <button
            type="button"
            className={`gemini-mute-toggle ${isMuted ? 'muted' : ''}`}
            onClick={onToggleMute}
            title={isMuted ? 'Unmute voice' : 'Mute voice'}
          >
            {isMuted ? '🔇' : '🔊'}
          </button>
        )}
      </div>

      {/* ── Floating Middle-Down Subtitle Display ── */}
      {subtitle && (
        <div className="gemini-subtitle-container">
          <div className="gemini-subtitle-bubble">
            <p className="gemini-subtitle-text">{subtitle}</p>
          </div>
        </div>
      )}
    </div>
  )
}
