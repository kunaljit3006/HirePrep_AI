import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { supabase } from '../lib/supabase'

export default function ProtectedRoute({ children }) {
  const [loading, setLoading] = useState(true)
  const [session, setSession] = useState(null)

  useEffect(() => {
    const guest = localStorage.getItem('hireprep_guest_user')
    if (guest) {
      setSession({ user: JSON.parse(guest) })
      setLoading(false)
      return
    }

    supabase.auth.getSession().then(({ data: { session: s } }) => {
      setSession(s)
      setLoading(false)
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, s) => {
      if (!localStorage.getItem('hireprep_guest_user')) {
        setSession(s)
      }
    })

    return () => subscription.unsubscribe()
  }, [])

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        color: 'var(--text-muted)',
        fontFamily: 'var(--font-body)',
      }}>
        <div className="btn-spinner" style={{
          width: 32,
          height: 32,
          border: '3px solid rgba(0,240,138,0.15)',
          borderTopColor: 'var(--brand-primary)',
          borderRadius: '50%',
          animation: 'spin-slow 0.8s linear infinite',
        }} />
      </div>
    )
  }

  if (!session) {
    return <Navigate to="/auth" replace />
  }

  return children
}
