import { useState, useEffect } from 'react';
import { supabase } from '../../../../../supabase/client';
import type { UserProfile } from '../types';

export const useUserProfile = () => {
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const fetchUserProfile = async () => {
    try {
      const { data: { user } } = await supabase.auth.getUser();
      
      if (user) {
        setIsAuthenticated(true);
        
        // Fetch user profile from profiles table
        const { data: profile, error } = await supabase
          .from('profiles')
          .select('*')
          .eq('id', user.id)
          .single();

        if (error && error.code !== 'PGRST116') {
          console.error('Error fetching profile:', error);
        }

        setUserProfile({
          id: user.id,
          username: profile?.username || user.user_metadata?.full_name || 'User',
          email: user.email || '',
          full_name: profile?.full_name || user.user_metadata?.full_name,
          avatar_url: profile?.avatar_url || user.user_metadata?.avatar_url,
          bio: profile?.bio,
          created_at: profile?.created_at || user.created_at
        });
      } else {
        setIsAuthenticated(false);
        setUserProfile(null);
      }
    } catch (error) {
      console.error('Error fetching user profile:', error);
      setIsAuthenticated(false);
      setUserProfile(null);
    } finally {
      setIsLoading(false);
    }
  };

  const updateProfile = async (updates: Partial<UserProfile>) => {
    try {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) throw new Error('User not authenticated');

      const { error } = await supabase
        .from('profiles')
        .upsert({
          id: user.id,
          username: updates.username,
          full_name: updates.full_name,
          avatar_url: updates.avatar_url,
          bio: updates.bio,
          updated_at: new Date().toISOString()
        });

      if (error) throw error;

      // Refresh profile
      await fetchUserProfile();
    } catch (error) {
      console.error('Error updating profile:', error);
      throw error;
    }
  };

  const signOut = async () => {
    try {
      const { error } = await supabase.auth.signOut();
      if (error) throw error;
      
      setIsAuthenticated(false);
      setUserProfile(null);
    } catch (error) {
      console.error('Error signing out:', error);
    }
  };

  useEffect(() => {
    fetchUserProfile();

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event, session) => {
        if (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED') {
          fetchUserProfile();
        } else if (event === 'SIGNED_OUT') {
          setIsAuthenticated(false);
          setUserProfile(null);
        }
      }
    );

    return () => subscription.unsubscribe();
  }, []);

  return {
    userProfile,
    isAuthenticated,
    isLoading,
    updateProfile,
    signOut,
    fetchUserProfile,
    darkMode: false, // You can implement dark mode state here
    onToggleDarkMode: () => {} // You can implement dark mode toggle here
  };
};
