export interface Notification {
  id: string;
  document_id: string;
  filename: string;
  title: string;
  message: string;
  type: 'success' | 'error' | 'info' | 'warning';
  metadata: {
    action?: 'upload' | 'delete' | 'category_change' | 'categorize' | 'rename';
    filename?: string;
    old_category?: number;
    new_category?: number;
    [key: string]: any;
  };
  is_read: boolean;
  created_at: string;
}

export interface NotificationListResponse {
  notifications: Notification[];
  total: number;
  unread_count: number;
}

export interface UnreadCountResponse {
  unread_count: number;
  user_id: string;
}
