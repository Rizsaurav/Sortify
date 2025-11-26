import { FileText, Upload, FolderOpen, Trash2, AlertCircle, CheckCircle, Info, ExternalLink } from 'lucide-react';
import type { Notification } from './types';

interface NotificationItemProps {
  notification: Notification;
  onClick: () => void;
  onViewFile?: () => void;
}

export function NotificationItem({ notification, onClick, onViewFile }: NotificationItemProps) {
  const getIcon = () => {
    const iconClass = "w-5 h-5";

    switch (notification.type) {
      case 'success':
        return <CheckCircle className={`${iconClass} text-green-500`} />;
      case 'error':
        return <AlertCircle className={`${iconClass} text-red-500`} />;
      case 'warning':
        return <AlertCircle className={`${iconClass} text-yellow-500`} />;
      case 'info':
      default:
        return <Info className={`${iconClass} text-blue-500`} />;
    }
  };

  const getActionIcon = () => {
    const iconClass = "w-4 h-4";
    const action = notification.metadata?.action;

    switch (action) {
      case 'upload':
        return <Upload className={`${iconClass} text-blue-500`} />;
      case 'delete':
        return <Trash2 className={`${iconClass} text-red-500`} />;
      case 'category_change':
        return <FolderOpen className={`${iconClass} text-purple-500`} />;
      case 'categorize':
        return <FolderOpen className={`${iconClass} text-indigo-500`} />;
      default:
        return <FileText className={`${iconClass} text-gray-500`} />;
    }
  };

  const formatTimeAgo = (dateString: string): string => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  const getBgColor = () => {
    if (notification.is_read) {
      return 'bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800/70';
    }
    return 'bg-blue-50/50 dark:bg-blue-900/10 hover:bg-blue-50 dark:hover:bg-blue-900/20';
  };

  const getTypeColor = () => {
    switch (notification.type) {
      case 'success':
        return 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300';
      case 'error':
        return 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300';
      case 'warning':
        return 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300';
      case 'info':
      default:
        return 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300';
    }
  };

  return (
    <div
      onClick={onClick}
      className={`${getBgColor()} p-4 cursor-pointer transition-all duration-200 border-l-4 ${
        !notification.is_read
          ? 'border-blue-500 dark:border-blue-400'
          : 'border-transparent'
      }`}
    >
      <div className="flex items-start gap-4">
        {/* Icon */}
        <div className="flex-shrink-0 mt-0.5">
          {getIcon()}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Title & Time */}
          <div className="flex items-start justify-between gap-3 mb-1">
            <h4 className={`text-sm font-semibold ${
              notification.is_read
                ? 'text-gray-900 dark:text-gray-100'
                : 'text-gray-900 dark:text-gray-100'
            }`}>
              {notification.title}
            </h4>
            <time className="text-xs text-gray-500 dark:text-gray-400 flex-shrink-0">
              {formatTimeAgo(notification.created_at)}
            </time>
          </div>

          {/* Message */}
          <p className={`text-sm ${
            notification.is_read
              ? 'text-gray-600 dark:text-gray-400'
              : 'text-gray-700 dark:text-gray-300'
          } mb-2`}>
            {notification.message}
          </p>

          {/* Metadata Tags */}
          <div className="flex items-center gap-2 flex-wrap">
            {/* Category Name Tag (for category changes) */}
            {notification.metadata?.category_name && (
              <span className="inline-flex items-center gap-1 px-2 py-1 bg-gradient-to-r from-purple-100 to-indigo-100 dark:from-purple-900/30 dark:to-indigo-900/30 text-purple-700 dark:text-purple-300 text-xs rounded-md font-medium">
                <FolderOpen className="w-3 h-3" />
                {notification.metadata.category_name}
              </span>
            )}

            {/* Action Tag */}
            {notification.metadata?.action && (
              <span className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 text-xs rounded-md font-medium">
                {getActionIcon()}
                <span className="capitalize">{notification.metadata.action.replace('_', ' ')}</span>
              </span>
            )}

            {/* Type Tag */}
            <span className={`inline-flex items-center gap-1 px-2 py-1 text-xs rounded-md font-medium ${getTypeColor()}`}>
              {notification.type}
            </span>

            {/* Filename Tag */}
            {notification.filename && (
              <span className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 text-xs rounded-md font-medium truncate max-w-[200px]">
                <FileText className="w-3 h-3 flex-shrink-0" />
                <span className="truncate">{notification.filename}</span>
              </span>
            )}

            {/* Unread Indicator */}
            {!notification.is_read && (
              <span className="ml-auto w-2 h-2 bg-blue-500 dark:bg-blue-400 rounded-full flex-shrink-0 animate-pulse" />
            )}
          </div>

          {/* View File Button */}
          {onViewFile && (
            <button
              onClick={(e) => {
                e.stopPropagation(); // Prevent triggering the parent onClick
                onViewFile();
              }}
              className="mt-3 w-full px-3 py-2 bg-gradient-to-r from-blue-500 to-indigo-500 hover:from-blue-600 hover:to-indigo-600 text-white text-sm font-medium rounded-lg transition-all duration-200 flex items-center justify-center gap-2 shadow-sm hover:shadow-md"
            >
              <ExternalLink className="w-4 h-4" />
              View File
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
