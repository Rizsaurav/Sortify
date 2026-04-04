"use client"

import { Button } from "./UI/ui-core"
import { Avatar, AvatarFallback, AvatarImage } from "./UI/ui-core"
import {
  AlertDialog,
  AlertDialogTrigger,
  AlertDialogContent,
  AlertDialogAction,
  AlertDialogCancel,
} from "./UI/ui-kit"
import { BellIcon, MoonIcon, SunIcon } from "@heroicons/react/24/outline"
import { useState, useEffect } from "react"
import { useProfile } from "../userProfiles/ProfileProviders"
import { supabase } from "../../../../supabase/client"

export function Header() {
  const { profile, loading, refreshProfile } = useProfile()
  const [open, setOpen] = useState(false)
  const [avatarSrc, setAvatarSrc] = useState<string | undefined>()
  const [avatarFailed, setAvatarFailed] = useState(false)

  // Generate an SVG data URL with initials to use as a guaranteed image fallback
  const initialsFrom = (name?: string) => {
    if (!name) return 'U'
    const parts = name.trim().split(/\s+/)
    const initials = parts.length === 1 ? parts[0].slice(0, 2) : (parts[0][0] + parts[parts.length - 1][0])
    return initials.toUpperCase()
  }
  const svgDataUrlForInitials = (label: string) => {
    const initials = initialsFrom(label)
    const bg = '#4f46e5'
    const fg = '#ffffff'
    const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='256' height='256'><rect width='100%' height='100%' fill='${bg}'/><text x='50%' y='50%' dy='.08em' font-family='Inter, Arial, sans-serif' font-size='96' fill='${fg}' text-anchor='middle' dominant-baseline='middle'>${initials}</text></svg>`
    return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`
  }
  useEffect(() => {
    if (open) {
      console.log('Profile popup opened — profile:', profile)
      console.log('Profile avatar_url:', profile?.avatar_url)
    }
  }, [open, profile])

  // Keep a resolved avatar source: prefer profile.avatar_url, then supabase auth metadata, then local fallback
  useEffect(() => {
    let mounted = true
    async function resolveAvatar() {
      if (profile?.avatar_url && !avatarFailed) {
        if (mounted) setAvatarSrc(profile.avatar_url)
        return
      }

      try {
        const { data: { user } } = await supabase.auth.getUser()
        const metaAvatar = user?.user_metadata?.avatar_url
        if (metaAvatar && !avatarFailed) {
          if (mounted) setAvatarSrc(metaAvatar)
          return
        }

        // Prefer a local debug image if present, otherwise the default
        try {
          const resp = await fetch('/debug-avatar.png', { method: 'HEAD' })
          if (resp.ok) {
            if (mounted) setAvatarSrc('/debug-avatar.png')
            return
          }
        } catch (e) {
          // ignore
        }

        // As a final guaranteed fallback, use an initials SVG data URL so an image is always shown
        if (mounted) setAvatarSrc(svgDataUrlForInitials(profile?.full_name || profile?.username || 'U'))
      } catch (err) {
        if (mounted) setAvatarSrc(svgDataUrlForInitials(profile?.full_name || profile?.username || 'U'))
      }
    }
    resolveAvatar()
    return () => { mounted = false }
  }, [profile])

  // Reset avatarFailed when avatarSrc changes to a new candidate
  useEffect(() => {
    setAvatarFailed(false)
  }, [avatarSrc])

  // If popup opens but we don't yet have a profile, try refreshing once
  useEffect(() => {
    if (open && !profile && !loading) {
      try {
        refreshProfile()
      } catch (err) {
        // swallow; refreshProfile handles errors
      }
    }
  }, [open, profile, loading, refreshProfile])
  return (
    <header className="h-16 border-b border-border bg-card">
      <div className="flex h-full items-center justify-between px-6">
        <div className="flex items-center gap-4">{/* Breadcrumb could go here */}</div>

        <div className="flex items-center gap-4">
          {/* Theme Toggle */}
          <Button variant="ghost" size="icon">
            <SunIcon className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
            <MoonIcon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
            <span className="sr-only">Toggle theme</span>
          </Button>

          {/* Notifications */}
          <Button variant="ghost" size="icon" className="relative">
            <BellIcon className="h-5 w-5" />
            <span className="absolute -top-1 -right-1 h-3 w-3 bg-primary rounded-full"></span>
          </Button>

          {/* User Popup */}
          <AlertDialog open={open} onOpenChange={setOpen}>
            <AlertDialogTrigger asChild>
              <Button
                variant="ghost"
                className="relative h-10 w-10 rounded-full"
                type="button"
                onClick={() => setOpen(true)}
              >
                <Avatar className="h-10 w-10">
                  <AvatarImage src="/diverse-student-profiles.png" alt="Alex" />
                  <AvatarFallback>AS</AvatarFallback>
                </Avatar>
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent className="w-64 max-w-[90vw] top-16 right-4 left-auto -translate-x-0 -translate-y-0">
              <div className="p-4">
                <div className="flex justify-center mb-3">
                  <Avatar className="h-16 w-16">
                    <AvatarImage
                      src={avatarSrc || '/diverse-student-profiles.png'}
                      alt={profile?.username || 'User'}
                      onError={(e: any) => {
                        console.warn('AvatarImage failed to load:', e?.target?.src)
                        // avoid infinite retry loops
                        setAvatarFailed(true)
                        setAvatarSrc('/diverse-student-profiles.png')
                      }}
                      onLoad={(e: any) => console.log('AvatarImage loaded:', e?.target?.src)}
                    />
                    <AvatarFallback>{(profile?.username || 'U').slice(0,2).toUpperCase()}</AvatarFallback>
                  </Avatar>
                </div>
                {/* Debug: show plain img and url to verify loading */}
                <div className="flex flex-col items-center gap-2">
                  {avatarSrc && (
                    <>
                      <img
                        src={avatarSrc}
                        alt="debug-avatar"
                        className="h-16 w-16 rounded-full object-cover"
                        onError={(e) => {
                          console.warn('Debug <img> failed to load:', (e.target as HTMLImageElement).src)
                          setAvatarFailed(true)
                          setAvatarSrc('/diverse-student-profiles.png')
                        }}
                        onLoad={(e) => console.log('Debug <img> loaded:', (e.target as HTMLImageElement).src)}
                      />
                      <p className="text-xs text-muted-foreground break-all max-w-[12rem]">{avatarSrc}</p>
                    </>
                  )}
                </div>
                <div className="space-y-2 text-sm">
                  <div>
                    <p className="text-xs text-muted-foreground">Username</p>
                    <p className="text-sm font-medium">{loading ? 'Loading...' : profile?.username ?? 'Not signed in'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Full name</p>
                    <p className="text-sm">{loading ? '' : profile?.full_name ?? ''}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Bio</p>
                    <p className="text-sm">{loading ? '' : profile?.bio ?? ''}</p>
                  </div>
                </div>
                <div className="mt-4 flex gap-2">
                  <AlertDialogCancel asChild>
                    <Button variant="outline" className="flex-1">Close</Button>
                  </AlertDialogCancel>
                  <AlertDialogAction asChild>
                    <a href="/profile" className="w-full">
                      <Button className="w-full">Go to Profile</Button>
                    </a>
                  </AlertDialogAction>
                </div>
              </div>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>
    </header>
  )
}
