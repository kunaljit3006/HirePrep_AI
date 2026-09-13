import { useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import SplashScreen from './pages/SplashScreen'
import AuthPage from './pages/AuthPage'
import Dashboard from './pages/Dashboard'
import InterviewRoom from './pages/InterviewRoom'
import FeedbackReport from './pages/FeedbackReport'
import ProtectedRoute from './components/ProtectedRoute'

export default function App() {
  // Splash screen displays on every page load/refresh, then dissolves into the target page
  const [showSplash, setShowSplash] = useState(true)

  return (
    <BrowserRouter>
      {showSplash && (
        <SplashScreen onComplete={() => setShowSplash(false)} />
      )}
      <Routes>
        <Route path="/" element={<Navigate to="/auth" replace />} />
        <Route path="/auth" element={<AuthPage />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/interview/:interviewId"
          element={
            <ProtectedRoute>
              <InterviewRoom />
            </ProtectedRoute>
          }
        />
        <Route
          path="/feedback/:interviewId"
          element={
            <ProtectedRoute>
              <FeedbackReport />
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  )
}

