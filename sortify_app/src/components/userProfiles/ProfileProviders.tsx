import {
    createContext,
    useContext,
    useEffect,
    useState,
    ReactNode,
  } from "react"
  import {
    getCurrentProfile,
    updateMyProfile,
    createProfileIfNotExists,
  } from "../../../supabase/profile"
  
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