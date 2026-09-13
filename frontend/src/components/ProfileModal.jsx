import { useState, useEffect } from 'react'
import { updateUserProfile } from '../lib/api'
import './ProfileModal.css'

export default function ProfileModal({ isOpen, onClose, profile, onProfileUpdated }) {
  const [name, setName] = useState('')
  const [targetCompany, setTargetCompany] = useState('')
  const [targetRole, setTargetRole] = useState('')
  const [targetLocation, setTargetLocation] = useState('')
  const [experienceLevel, setExperienceLevel] = useState('Mid')
  const [githubHandle, setGithubHandle] = useState('')
  const [leetcodeHandle, setLeetcodeHandle] = useState('')
  const [codeforcesHandle, setCodeforcesHandle] = useState('')
  
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState({ type: '', text: '' })

  useEffect(() => {
    if (profile) {
      setName(profile.name || '')
      setTargetCompany(profile.target_company || 'Google')
      setTargetRole(profile.target_role || 'Full Stack Software Engineer')
      setTargetLocation(profile.target_location || 'India')
      setExperienceLevel(profile.experience_level || 'Mid')
      setGithubHandle(profile.github_handle || '')
      setLeetcodeHandle(profile.leetcode_handle || '')
      setCodeforcesHandle(profile.codeforces_handle || '')
    }
  }, [profile, isOpen])

  if (!isOpen) return null

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    setMessage({ type: '', text: '' })

    try {
      const payload = {
        name: name.trim(),
        target_company: targetCompany.trim(),
        target_role: targetRole.trim(),
        target_location: targetLocation.trim(),
        experience_level: experienceLevel,
        github_handle: githubHandle.trim(),
        leetcode_handle: leetcodeHandle.trim(),
        codeforces_handle: codeforcesHandle.trim(),
      }

      const updated = await updateUserProfile(payload)
      setMessage({ type: 'success', text: 'Candidate profile updated & synced to SQLite database!' })
      if (onProfileUpdated && updated) {
        onProfileUpdated(updated)
      }
      setTimeout(() => {
        onClose()
      }, 1200)
    } catch (err) {
      setMessage({ type: 'error', text: err.message || 'Failed to update profile' })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="profile-modal-overlay" onClick={onClose}>
      <div className="profile-modal-container" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="profile-modal-header">
          <div className="profile-header-left">
            <div className="profile-avatar-pill">
              {name ? name.charAt(0).toUpperCase() : 'C'}
            </div>
            <div>
              <h2 className="profile-modal-title">Candidate Profile &amp; Preferences</h2>
              <p className="profile-modal-subline">Manage your interview target companies and synced coding handles</p>
            </div>
          </div>
          <button type="button" className="profile-close-btn" onClick={onClose} aria-label="Close modal">
            ✕
          </button>
        </div>

        {/* Message Banner */}
        {message.text && (
          <div className={`profile-banner ${message.type === 'success' ? 'banner-success' : 'banner-error'}`}>
            <span>{message.text}</span>
          </div>
        )}

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="profile-form">
          <div className="profile-form-grid">
            {/* Full Name */}
            <div className="profile-field">
              <label className="profile-label">Candidate Full Name</label>
              <input
                type="text"
                className="profile-input"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Kunal Jit"
                required
              />
            </div>

            {/* Experience Level */}
            <div className="profile-field">
              <label className="profile-label">Experience Level</label>
              <select
                className="profile-input profile-select"
                value={experienceLevel}
                onChange={(e) => setExperienceLevel(e.target.value)}
              >
                <option value="Entry">Entry Level (0-2 yrs)</option>
                <option value="Mid">Mid Level (2-5 yrs)</option>
                <option value="Senior">Senior (5-8 yrs)</option>
                <option value="Staff">Staff / Principal (8+ yrs)</option>
              </select>
            </div>

            {/* Target Company */}
            <div className="profile-field">
              <label className="profile-label">Target Dream Company</label>
              <input
                type="text"
                className="profile-input"
                value={targetCompany}
                onChange={(e) => setTargetCompany(e.target.value)}
                placeholder="e.g. Google, Amazon, Meta"
              />
            </div>

            {/* Target Role */}
            <div className="profile-field">
              <label className="profile-label">Target Engineering Role</label>
              <input
                type="text"
                className="profile-input"
                value={targetRole}
                onChange={(e) => setTargetRole(e.target.value)}
                placeholder="e.g. Full Stack AI Engineer, Backend SDE II"
              />
            </div>

            {/* Target Location */}
            <div className="profile-field full-width">
              <label className="profile-label">Preferred Location / Remote</label>
              <input
                type="text"
                className="profile-input"
                value={targetLocation}
                onChange={(e) => setTargetLocation(e.target.value)}
                placeholder="e.g. Bengaluru / Hybrid, Seattle, Remote"
              />
            </div>
          </div>

          <div className="profile-section-divider">
            <span className="profile-divider-text mono">EXTERNAL CODING TELEMETRY HANDLES</span>
          </div>

          <div className="profile-handles-grid">
            {/* LeetCode */}
            <div className="profile-field">
              <label className="profile-label">LeetCode Username</label>
              <input
                type="text"
                className="profile-input mono"
                value={leetcodeHandle}
                onChange={(e) => setLeetcodeHandle(e.target.value)}
                placeholder="e.g. kunal_algo"
              />
            </div>

            {/* GitHub */}
            <div className="profile-field">
              <label className="profile-label">GitHub Username</label>
              <input
                type="text"
                className="profile-input mono"
                value={githubHandle}
                onChange={(e) => setGithubHandle(e.target.value)}
                placeholder="e.g. kunaljit"
              />
            </div>

            {/* Codeforces */}
            <div className="profile-field">
              <label className="profile-label">Codeforces Handle</label>
              <input
                type="text"
                className="profile-input mono"
                value={codeforcesHandle}
                onChange={(e) => setCodeforcesHandle(e.target.value)}
                placeholder="e.g. kunal_tourist"
              />
            </div>
          </div>

          {/* Footer Actions */}
          <div className="profile-modal-footer">
            <button type="button" className="btn-cancel" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-save" disabled={saving}>
              {saving ? 'Synchronizing with Database...' : 'Save Profile Changes ➔'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
