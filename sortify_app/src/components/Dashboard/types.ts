// src/components/Dashboard/types.ts

// Represents an uploaded file in the system
export interface UploadedFile {
  id: string;
  name: string;
  type: string;
  size: string;
  modified: string;
  category: string;
  storage_path?: string;
  view_count?: number;
  metadata?: any;
  content?: string;
  created_at?: string;
  cluster_id?: number;
}

// Represents a file category and its associated metadata
export interface CategoryCount {
  id: number;
  name: string;
  icon: any;
  count: number;
  color: string;
}

// Represents a frequently accessed folder or category
export interface FrequentFolder {
  name: string;
  icon: any;
  color: string;
  count: number;
  lastAccessed?: string;
}

// Enumerates file preview types
export type PreviewType = 'pdf' | 'image' | 'text' | 'video' | 'office' | 'none';

// Enumerates file view modes
export type ViewMode = 'grid' | 'directory';

export interface FilePreviewState {
  file: UploadedFile | null;
  url: string | null;
  content: string | null;
  type: PreviewType;
}

// Represents a user's profile data
export interface UserProfile {
  id: string;
  username: string;
  email: string;
  full_name?: string;
  avatar_url?: string;
  bio?: string;
  created_at?: string;
}
