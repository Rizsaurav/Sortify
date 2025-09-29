import React, { useState } from "react"
import { signInWithEmail, signInWithGoogle } from "../../../../.././supabase/auth"


export function LoginForm() {
    const [showPassword, setShowPassword] = useState(false)
    const [isLoading, setIsLoading] = useState(false)
    const [loginError, setLoginError] = useState<string | null>(null)
    const [loginData, setLoginData] = useState({
      email: "",
      password: "",
    })
  
    const handleSubmit = async (e: React.FormEvent) => {
      e.preventDefault()
      setIsLoading(true)
      setLoginError(null)
  
      try {
        await signInWithEmail(loginData.email, loginData.password)
        console.log("Signed in with email:", loginData.email)
      } catch (err: any) {
        console.error("Login failed:", err.message)
        setLoginError(err.message)
      } finally {
        setIsLoading(false)
      }
    }}

    const handleGoogleLogin = async () => {
        try {
          await signInWithGoogle()
          console.log("Redirecting to Google login...")
        } catch (err: any) {
          console.error(" Google login failed:", err.message)
          setLoginError(err.message)
        }
      }
    
      const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setLoginData((prev) => ({
          ...prev,
          [e.target.name]: e.target.value,
        }))
      }
      
      return (
        <form onSubmit={handleSubmit}>
          <h2>Sign In</h2>
          <p>Enter your credentials to access your account</p>
    
          {/* Email */}
          <div>
            <label htmlFor="email">Email Address</label>
            <input
              id="email"
              name="email"
              type="email"
              value={loginData.email}
              onChange={handleInputChange}
              required
            />
          </div>
    
          {/* Password */}
          <div>
            <label htmlFor="password">Password</label>
            <input
              id="password"
              name="password"
              type={showPassword ? "text" : "password"}
              value={loginData.password}
              onChange={handleInputChange}
              required
            />
            <button type="button" onClick={() => setShowPassword(!showPassword)}>
              {showPassword ? "Hide" : "Show"}
            </button>
          </div>
    