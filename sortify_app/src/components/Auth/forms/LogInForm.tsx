import React, { useState } from "react"
import { signInWithEmail, signInWithGoogle } from "../../../../.././supabase/auth"


export function LoginForm() {
    const [showPassword, setShowPassword] = useState(false)
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [formData, setFormData] = useState({
      email: "",
      password: "",
    })
  
    const handleSubmit = async (e: React.FormEvent) => {
      e.preventDefault()
      setIsLoading(true)
      setError(null)
  
      try {
        await signInWithEmail(formData.email, formData.password)
        console.log("Signed in with email:", formData.email)
      } catch (err: any) {
        console.error("Login failed:", err.message)
        setError(err.message)
      } finally {
        setIsLoading(false)
      }
    }}