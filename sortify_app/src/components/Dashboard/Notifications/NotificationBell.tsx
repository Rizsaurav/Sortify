import { useState, useRef, useEffect } from 'react';
import { Bell, X, Check, CheckCheck } from 'lucide-react';
import { useNotifications } from './useNotifications';
import { NotificationItem } from './NotificationItem';
import type { UploadedFile } from '../types';

interface NotificationBellProps {
  allFiles: UploadedFile[];
  onPreviewFile: (file: UploadedFile) => void;
  onNavigateToAllFiles: () => void;
}

export function NotificationBell({ allFiles, onPreviewFile, onNavigateToAllFiles }: NotificationBellProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const {
    notifications,
    unreadCount,
    isLoading,
    markAsRead,
    markAllAsRead,
    fetchNotifications
  } = useNotifications();

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const handleBellClick = () => {
    setIsOpen(!isOpen);
    if (!isOpen) {
      fetchNotifications(); // Refresh when opening
    }
  };

  // Handle clicking notification body - opens preview modal
  const handleNotificationClick = async (docId: string, notifId: string) => {
    await markAsRead(docId, notifId);

    // Find the file and open preview
    const file = allFiles.find(f => f.id === docId);
    if (file) {
      onPreviewFile(file);
      setIsOpen(false); // Close dropdown after opening preview
    }
  };

  // Handle clicking "View File" button - navigates to All Files page
  const handleViewFile = async (docId: string, notifId: string) => {
    await markAsRead(docId, notifId);

    // Navigate to All Files page with file highlighted
    onNavigateToAllFiles();
    setIsOpen(false); // Close dropdown

    // Optional: Store the file ID in sessionStorage so All Files page can highlight it
    sessionStorage.setItem('highlightFileId', docId);
  };

  const handleMarkAllRead = async () => {
    await markAllAsRead();
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell Icon Button */}
      <button
        onClick={handleBellClick}
        className="relative p-2.5 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800 transition-all duration-200 group"
        aria-label="Notifications"
      >
        <Bell
          className={`w-5 h-5 transition-all duration-200 ${
            unreadCount > 0
              ? 'text-blue-600 dark:text-blue-400 animate-pulse'
              : 'text-gray-600 dark:text-gray-400 group-hover:text-gray-900 dark:group-hover:text-gray-200'
          }`}
        />

        {/* Unread Badge */}
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 bg-gradient-to-r from-red-500 to-pink-500 text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] flex items-center justify-center px-1 shadow-lg animate-in zoom-in-50">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}

        {/* Pulse Ring Effect for Unread */}
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 w-[18px] h-[18px] bg-red-400 rounded-full animate-ping opacity-40" />
        )}
      </button>

      {/* Dropdown Panel */}
      {isOpen && (
        <div className="absolute right-0 mt-3 w-96 bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700 z-50 overflow-hidden animate-in fade-in slide-in-from-top-5 duration-200">
          {/* Header */}
          <div className="sticky top-0 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 px-5 py-4 flex items-center justify-between backdrop-blur-sm z-10">
            <div className="flex items-center gap-3">
              <Bell className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Notifications
              </h3>
              {unreadCount > 0 && (
                <span className="bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-xs font-medium px-2.5 py-0.5 rounded-full">
                  {unreadCount} new
                </span>
              )}
            </div>

            <div className="flex items-center gap-2">
              {unreadCount > 0 && (
                <button
                  onClick={handleMarkAllRead}
                  className="flex items-center gap-1.5 text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 font-medium transition-colors"
                  title="Mark all as read"
                >
                  <CheckCheck className="w-4 h-4" />
                  Mark all
                </button>
              )}

              <button
                onClick={() => setIsOpen(false)}
                className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
                aria-label="Close"
              >
                <X className="w-4 h-4 text-gray-500 dark:text-gray-400" />
              </button>
            </div>
          </div>

          {/* Notifications List */}
          <div className="max-h-[480px] overflow-y-auto scrollbar-thin scrollbar-thumb-gray-300 dark:scrollbar-thumb-gray-700 scrollbar-track-transparent">
            {isLoading ? (
              <div className="flex flex-col items-center justify-center py-16">
                <div className="animate-spin rounded-full h-10 w-10 border-4 border-blue-200 dark:border-blue-800 border-t-blue-600 dark:border-t-blue-400 mb-4" />
                <p className="text-sm text-gray-500 dark:text-gray-400">Loading notifications...</p>
              </div>
            ) : notifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
                <div className="bg-gray-100 dark:bg-gray-800 rounded-full p-6 mb-4">
                  <Bell className="w-10 h-10 text-gray-400 dark:text-gray-500" />
                </div>
                <h4 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-1">
                  No notifications yet
                </h4>
                <p className="text-sm text-gray-500 dark:text-gray-400 max-w-xs">
                  When you upload, delete, or organize files, you'll see notifications here.
                </p>
              </div>
            ) : (
              <div className="divide-y divide-gray-100 dark:divide-gray-800">
                {notifications.map((notification) => (
                  <NotificationItem
                    key={notification.id}
                    notification={notification}
                    onClick={() => handleNotificationClick(notification.document_id, notification.id)}
                    onViewFile={() => handleViewFile(notification.document_id, notification.id)}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Footer (Optional) */}
          {notifications.length > 0 && (
            <div className="sticky bottom-0 bg-gray-50 dark:bg-gray-800/50 border-t border-gray-200 dark:border-gray-700 px-5 py-3 text-center backdrop-blur-sm">
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Showing {notifications.length} notification{notifications.length !== 1 ? 's' : ''}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
