// supabase/client.js
import { createClient } from '@supabase/supabase-js'

// Read from environment variables
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY

// Safety check
if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
    throw new Error("Missing Supabase environment variables. Did you set them in .env?")
  }

// Create a single supabase client for the whole app
export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)