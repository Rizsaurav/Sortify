import { useState, useEffect } from "react"
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom"
import type { Session } from "@supabase/supabase-js"
import { supabase } from "../../supabase/client"

import { SignupForm } from "./components/Auth/forms/SignUpForm"
import { LoginForm } from "./components/Auth/forms/LogInForm"
import Dashboard from "./components/landing_page/Dashboard"

function App() {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
      setLoading(false)
    })

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
    })

    return () => subscription.unsubscribe()
  }, [])

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center">Loading...</div>
  }

  return (
    <Router>
      <Routes>
        <Route path="/login" element={session ? <Navigate to="/dashboard" /> : <LoginForm />} />
        <Route path="/signup" element={session ? <Navigate to="/dashboard" /> : <SignupForm />} />
        <Route path="/dashboard" element={session ? <Dashboard /> : <Navigate to="/login" replace />} />
        <Route path="*" element={<Navigate to={session ? "/dashboard" : "/login"} replace />} />
      </Routes>
    </Router>
  )
}

export default App