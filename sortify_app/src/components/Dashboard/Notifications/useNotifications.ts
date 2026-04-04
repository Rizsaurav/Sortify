import { useState, useEffect, useCallback } from 'react';
import { supabase } from '../../../../../supabase/client';
import type { Notification } from './types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const useNotifications = () => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [userId, setUserId] = useState<string | null>(null);

  // Get user ID
  useEffect(() => {
    const getUserId = async () => {
      const { data: { user } } = await supabase.auth.getUser();
      if (user) {
        setUserId(user.id);
      }
    };
    getUserId();
  }, []);

  // Fetch notifications
  const fetchNotifications = useCallback(async () => {
    if (!userId) return;

    try {
      setIsLoading(true);

      // Fetch notifications
      const response = await fetch(
        `${API_URL}/notifications?user_id=${userId}&limit=50`
      );

      if (!response.ok) {
        throw new Error('Failed to fetch notifications');
      }

      const data = await response.json();

      setNotifications(data.notifications || []);
      setUnreadCount(data.unread_count || 0);
    } catch (error) {
      console.error('Failed to fetch notifications:', error);
    } finally {
      setIsLoading(false);
    }
  }, [userId]);

  // Fetch unread count only
  const fetchUnreadCount = useCallback(async () => {
    if (!userId) return;

    try {
      const response = await fetch(
        `${API_URL}/notifications/unread-count?user_id=${userId}`
      );

      if (!response.ok) {
        throw new Error('Failed to fetch unread count');
      }

      const data = await response.json();
      setUnreadCount(data.unread_count || 0);
    } catch (error) {
      console.error('Failed to fetch unread count:', error);
    }
  }, [userId]);

  // Mark notification as read
  const markAsRead = useCallback(async (documentId: string, notificationId: string) => {
    try {
      const response = await fetch(
        `${API_URL}/notifications/${documentId}/read/${notificationId}`,
        { method: 'PATCH' }
      );

      if (!response.ok) {
        throw new Error('Failed to mark notification as read');
      }

      // Update local state
      setNotifications(prev =>
        prev.map(n =>
          n.id === notificationId ? { ...n, is_read: true } : n
        )
      );

      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (error) {
      console.error('Failed to mark notification as read:', error);
    }
  }, []);

  // Mark all notifications as read
  const markAllAsRead = useCallback(async () => {
    if (!userId) return;

    try {
      // Mark all in local state first for instant UI feedback
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
      setUnreadCount(0);

      // Then update on server
      const updates = notifications
        .filter(n => !n.is_read)
        .map(n => markAsRead(n.document_id, n.id));

      await Promise.all(updates);
    } catch (error) {
      console.error('Failed to mark all as read:', error);
      // Refetch on error to get correct state
      fetchNotifications();
    }
  }, [userId, notifications, markAsRead, fetchNotifications]);

  // Initial fetch
  useEffect(() => {
    if (userId) {
      fetchNotifications();
    }
  }, [userId, fetchNotifications]);

  // Poll for new notifications every 30 seconds
  useEffect(() => {
    if (!userId) return;

    const interval = setInterval(() => {
      fetchUnreadCount();
    }, 30000); // 30 seconds

    return () => clearInterval(interval);
  }, [userId, fetchUnreadCount]);

  // Listen for real-time updates via Supabase Realtime (optional)
  useEffect(() => {
    if (!userId) return;

    // Subscribe to document changes
    const channel = supabase
      .channel('notifications')
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'documents',
          filter: `user_id=eq.${userId}`,
        },
        (payload) => {
          console.log('Document change detected:', payload);
          // Refetch notifications when documents change
          fetchNotifications();
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [userId, fetchNotifications]);

  return {
    notifications,
    unreadCount,
    isLoading,
    fetchNotifications,
    fetchUnreadCount,
    markAsRead,
    markAllAsRead,
  };
};
