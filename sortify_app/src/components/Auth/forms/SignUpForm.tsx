// src/components/Auth/forms/SignupForm.tsx
import React, { useState } from "react"
import { signUpWithEmail, signInWithGoogle } from "../../../../../supabase/auth"

export function SignupForm() {
  const [isLoading, setIsLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [signupError, setSignupError] = useState<string | null>(null)
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setSignupError(null)

    if (formData.password !== formData.confirmPassword) {
      setSignupError("Passwords do not match")
      setIsLoading(false)
      return
    }

    try {
      await signUpWithEmail(formData.email, formData.password)
      console.log("Signed up with email:", formData.email)
    } catch (err: any) {
      console.error("Signup failed:", err.message)
      setSignupError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  const handleGoogleSignup = async () => {
    try {
      await signInWithGoogle()
      console.log("Redirecting to Google signup...")
    } catch (err: any) {
      console.error("Google signup failed:", err.message)
      setSignupError(err.message)
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }))
  }

  return (
    <form onSubmit={handleSubmit}>
      <h2>Create Account</h2>
      <p>Sign up to start organizing your files with Sortify</p>

      {/* Full Name */}
      <div>
        <label htmlFor="name">Full Name</label>
        <input
          id="name"
          name="name"
          type="text"
          value={formData.name}
          onChange={handleInputChange}
          required
        />
      </div>

      {/* Email */}
      <div>
        <label htmlFor="email">Email Address</label>
        <input
          id="email"
          name="email"
          type="email"
          value={formData.email}
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
          value={formData.password}
          onChange={handleInputChange}
          required
        />
        <button type="button" onClick={() => setShowPassword(!showPassword)}>
          {showPassword ? "Hide" : "Show"}
        </button>
      </div>

      {/* Confirm Password */}
      <div>
        <label htmlFor="confirmPassword">Confirm Password</label>
        <input
          id="confirmPassword"
          name="confirmPassword"
          type={showConfirmPassword ? "text" : "password"}
          value={formData.confirmPassword}
          onChange={handleInputChange}
          required
        />
        <button type="button" onClick={() => setShowConfirmPassword(!showConfirmPassword)}>
          {showConfirmPassword ? "Hide" : "Show"}
        </button>
      </div>

      {/* Error */}
      {signupError && <p style={{ color: "red" }}>{signupError}</p>}

      {/* Submit */}
      <button type="submit" disabled={isLoading}>
        {isLoading ? "Creating Account..." : "Create Account"}
      </button>

      {/* Google signup */}
      <button type="button" onClick={handleGoogleSignup}>
        Sign up with Google
      </button>

      {/* Links */}
      <p>
        Already have an account? <a href="/login">Sign in</a>
      </p>
    </form>
  )
}
