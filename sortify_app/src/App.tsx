import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom"

import { SignupForm } from "./components/Auth/forms/SignUpForm"
import { LoginForm } from "./components/Auth/forms/LogInForm"
import './App.css'

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<LoginForm />} />
        <Route path="/signup" element={<SignupForm />} />
        <Route path="/dashboard" element={<h2>Dashboard (coming soon)</h2>} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </Router>
  )
}


export default App
