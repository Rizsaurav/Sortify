import { supabase } from "./client"

// Fetch current user's profile
export async function getCurrentProfile() {
  const { data, error } = await supabase.rpc("current_user_profile")
  if (error) throw error
  //  ensure we return single row
  return Array.isArray(data) ? data[0] : data
}

// Insert or update profile
export async function updateMyProfile(profile: {
  username?: string
  full_name?: string
  avatar_url?: string
  bio?: string
  hobbies?: string[]
  interests?: string[]
  website?: string
  location?: string
  social_links?: Record<string, string>
}) {
  const { data, error } = await supabase.rpc("update_my_profile", {
    p_username: profile.username ?? null,
    p_full_name: profile.full_name ?? null,
    p_avatar_url: profile.avatar_url ?? null,
    p_bio: profile.bio ?? null,
    p_hobbies: profile.hobbies ?? null,
    p_interests: profile.interests ?? null,
    p_website: profile.website ?? null,
    p_location: profile.location ?? null,
    p_social_links: profile.social_links ?? null,
  })
  if (error) throw error
  return data
}
