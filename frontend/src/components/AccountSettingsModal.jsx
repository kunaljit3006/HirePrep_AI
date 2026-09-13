import { useState, useEffect } from 'react'
import { updateUserProfile, deleteUserAccount } from '../lib/api'
import './AccountSettingsModal.css'

export default function AccountSettingsModal({
  isOpen,
  onClose,
  user,
  profile,
  onProfileUpdated,
  onLogout,
}) {
  const [name, setName] = useState('')
  const [savingName, setSavingName] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [statusMessage, setStatusMessage] = useState({ type: '', text: '' })

  const isPhoneUser = Boolean(user?.phone || profile?.phone)
  const userEmail = user?.email || profile?.email || ''
  const currentDisplayName = profile?.name || user?.user_metadata?.full_name || name || 'Candidate'
  const avatarUrl = profile?.avatar_url || user?.user_metadata?.avatar_url || user?.user_metadata?.picture

  useEffect(() => {
    if (isOpen) {
      setName(profile?.name || user?.user_metadata?.full_name || '')
      setShowDeleteConfirm(false)
      setStatusMessage({ type: '', text: '' })
    }
  }, [isOpen, profile, user])

  if (!isOpen) return null

  // Save / Change Name
  const handleUpdateName = async (e) => {
    e.preventDefault()
    if (!name.trim()) {
      setStatusMessage({ type: 'error', text: 'Name cannot be blank.' })
      return
    }

    setSavingName(true)
    setStatusMessage({ type: '', text: '' })

    try {
      const updated = await updateUserProfile({ name: name.trim() })
      setStatusMessage({ type: 'success', text: 'Name updated successfully!' })
      if (onProfileUpdated && updated) {
        onProfileUpdated(updated)
      }
      // Also update local storage if guest user
      const guest = localStorage.getItem('hireprep_guest_user')
      if (guest) {
        try {
          const parsed = JSON.parse(guest)
          parsed.user_metadata = { ...(parsed.user_metadata || {}), full_name: name.trim() }
          parsed.name = name.trim()
          localStorage.setItem('hireprep_guest_user', JSON.stringify(parsed))
        } catch {
          // ignore
        }
      }
    } catch (err) {
      setStatusMessage({ type: 'error', text: err.message || 'Failed to update name.' })
    } finally {
      setSavingName(false)
    }
  }

  // Delete Account
  const handleDeleteAccount = async () => {
    setDeleting(true)
    setStatusMessage({ type: '', text: '' })
    try {
      await deleteUserAccount()
      localStorage.removeItem('hireprep_guest_user')
      if (onLogout) {
        await onLogout()
      } else {
        window.location.href = '/auth'
      }
    } catch (err) {
      setStatusMessage({ type: 'error', text: err.message || 'Failed to delete account.' })
      setDeleting(false)
    }
  }

  // Render circular avatar
  const renderAvatar = () => {
    if (isPhoneUser) {
      const initial = currentDisplayName.charAt(0).toUpperCase() || 'C'
      return <div className="simple-avatar-letter">{initial}</div>
    }

    if (avatarUrl) {
      return (
        <img
          src={avatarUrl}
          alt={currentDisplayName}
          className="simple-avatar-img"
          onError={(e) => {
            e.target.style.display = 'none'
            if (e.target.nextSibling) e.target.nextSibling.style.display = 'flex'
          }}
        />
      )
    }

    const initial = currentDisplayName.charAt(0).toUpperCase() || 'E'
    return <div className="simple-avatar-letter">{initial}</div>
  }

  return (
    <div className="simple-settings-overlay" onClick={onClose}>
      <div className="simple-settings-card" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="simple-settings-header">
          <div className="simple-user-summary">
            <div className="simple-avatar-circle">
              {renderAvatar()}
            </div>
            <div className="simple-user-meta">
              <h3 className="simple-name">{currentDisplayName}</h3>
              <span className="simple-auth-label mono">
                {isPhoneUser
                  ? `Phone: ${user?.phone || profile?.phone}`
                  : `Email: ${userEmail || 'Account'}`}
              </span>
            </div>
          </div>
          <button
            type="button"
            className="simple-close-btn"
            onClick={onClose}
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        {/* Feedback Banner */}
        {statusMessage.text && (
          <div className={`simple-banner ${statusMessage.type === 'success' ? 'banner-pass' : 'banner-fail'}`}>
            <span>{statusMessage.text}</span>
          </div>
        )}

        {/* Content */}
        <div className="simple-settings-body">
          {/* 1. Change Name */}
          <form onSubmit={handleUpdateName} className="simple-name-group">
            <label className="simple-field-label">Candidate Name</label>
            <div className="simple-input-row">
              <input
                type="text"
                className="simple-input"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Full Name"
                required
              />
              <button
                type="submit"
                className="simple-btn-save"
                disabled={savingName || name.trim() === currentDisplayName}
              >
                {savingName ? 'Saving...' : 'Save'}
              </button>
            </div>
          </form>

          <div className="simple-divider" />

          {/* 2. Log Out */}
          <button
            type="button"
            className="simple-btn-logout"
            onClick={onLogout}
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line x1="21" y1="12" x2="9" y2="12" />
            </svg>
            Sign Out from HirePrep_AI
          </button>

          {/* 3. Delete Account */}
          <div className="simple-delete-area">
            {!showDeleteConfirm ? (
              <button
                type="button"
                className="simple-btn-delete-link"
                onClick={() => setShowDeleteConfirm(true)}
              >
                Delete account permanently
              </button>
            ) : (
              <div className="simple-delete-box">
                <p className="simple-delete-warn">
                  Permanently erase your candidate profile, parsed resumes, and interview history?
                </p>
                <div className="simple-delete-actions">
                  <button
                    type="button"
                    className="simple-btn-cancel-del"
                    onClick={() => setShowDeleteConfirm(false)}
                    disabled={deleting}
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    className="simple-btn-confirm-del"
                    onClick={handleDeleteAccount}
                    disabled={deleting}
                  >
                    {deleting ? 'Deleting...' : 'Yes, Delete Account'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
