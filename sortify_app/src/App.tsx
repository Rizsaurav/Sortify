import { useState, useEffect } from "react"
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom"
import type { Session } from "@supabase/supabase-js"

import { SignupForm } from "./components/Auth/forms/SignUpForm"
import { LoginForm } from "./components/Auth/forms/LogInForm"
import { DashboardLayout } from "./components/landing_page/dashboard_layout"
import { supabase } from "../../supabase/client"   

function App() {
  const [session, setSession] = useState<Session | null>(null)

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        setSession(session)
      }
    )

    return () => subscription.unsubscribe()
  }, [])

  return (
    <Router>
      <Routes>
        <Route path="/login" element={session ? <Navigate to="/dashboard" /> : <LoginForm />} />
        <Route path="/signup" element={session ? <Navigate to="/dashboard" /> : <SignupForm />} />
        <Route
          path="/dashboard"
          element={
            session ? (
              <DashboardLayout>
                <h1>Welcome to your dashboard</h1>
              </DashboardLayout>
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />
        <Route path="*" element={<Navigate to={session ? "/dashboard" : "/login"} replace />} />
      </Routes>
    </Router>
  )
}

export default App
