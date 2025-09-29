import { supabase } from './client'


// Sign in with Google OAuth
export async function signInWithGoogle() {
    const { data, error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
    })
    if (error) throw error
    return data
  }

//Sign up with email+password
export async function signUpWithEmail(email, password) {
    const { data, error } = await supabase.auth.signUp({ email, password })
    if (error) throw error
    return data
  }

//Sign in with email and password
export async function signInWithEmail(email, password) {
    const { data, error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) throw error
    return data
  }

//Get the currently logged-in user
export async function getCurrentUser() {
    const { data: { user }, error } = await supabase.auth.getUser()
    if (error) throw error
    return user
  }
  

// Sign out the current user
  export async function signOut() {
    const { error } = await supabase.auth.signOut()
    if (error) throw error
    return true
  }
  