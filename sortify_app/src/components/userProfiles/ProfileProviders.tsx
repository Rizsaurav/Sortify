import {
    createContext,
    useContext,
    useEffect,
    useState,
  } from "react"
  import type { ReactNode } from "react"

  import {
    getCurrentProfile,
    updateMyProfile,
    createProfileIfNotExists,
  } from "../../../../supabase/profile"
  
  type Profile = {
    id: string
    username?: string
    full_name?: string
    avatar_url?: string
    bio?: string
    hobbies?: string[]
    interests?: string[]
    website?: string
    location?: string
    social_links?: Record<string, string>
  }
  
  type ProfileContextType = {
    profile: Profile | null
    loading: boolean
    error: string | null
    refreshProfile: () => Promise<void>
    updateProfile: (updates: Partial<Profile>) => Promise<void>
  }
  
  const ProfileContext = createContext<ProfileContextType | undefined>(undefined)
  
  export function ProfileProvider({ children }: { children: ReactNode }) {
    const [profile, setProfile] = useState<Profile | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
  
    // Load or create profile on mount
    useEffect(() => {
      async function init() {
        setLoading(true)
        try {
          const p = await createProfileIfNotExists()
          setProfile(p)
          setError(null)
        } catch (err: any) {
          // If no user is logged in, keep profile = null but don’t break UI
          setError(err?.message ?? "Failed to load profile")
          setProfile(null)
        } finally {
          setLoading(false)
        }
      }
      init()
    }, [])

     // Refresh manually
  const refreshProfile = async () => {
    setLoading(true)
    try {
      const p = await getCurrentProfile()
      setProfile(p)
      setError(null)
    } catch (err: any) {
      setError(err?.message ?? "Failed to refresh profile")
    } finally {
      setLoading(false)
    }
  }

  // Update user profile
  const updateProfile = async (updates: Partial<Profile>) => {
    try {
      const p = await updateMyProfile(updates)
      setProfile(p)
      setError(null)
    } catch (err: any) {
      setError(err?.message ?? "Failed to update profile")
    }
  }

  return (
    <ProfileContext.Provider
      value={{ profile, loading, error, refreshProfile, updateProfile }}
    >
      {children}
    </ProfileContext.Provider>
  )
}

// Simple hook for usage
export function useProfile() {
  const ctx = useContext(ProfileContext)
  if (!ctx) throw new Error("useProfile must be used within a ProfileProvider")
  return ctx
}