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
    