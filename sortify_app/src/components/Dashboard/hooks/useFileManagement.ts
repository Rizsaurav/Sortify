import { useState, useEffect } from 'react';
import { supabase } from '../../../../../supabase/client';
import type { UploadedFile, CategoryCount, FrequentFolder } from '../types';
import { uploadDocument } from '../../../api/sorter';

export const useFileManagement = () => {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [allFiles, setAllFiles] = useState<UploadedFile[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [totalFilesCount, setTotalFilesCount] = useState(0);
  const [storageUsed, setStorageUsed] = useState(0);
  const [categoryCount, setCategoryCount] = useState<CategoryCount[]>([]);
  const [frequentFolders, setFrequentFolders] = useState<FrequentFolder[]>([]);
  const [notifications, setNotifications] = useState<Array<{id: string, message: string, type: 'success' | 'error' | 'info'}>>([]);
  const [folderCounts] = useState<{[key: string]: number}>({});

  // Notification functions
  const addNotification = (message: string, type: 'success' | 'error' | 'info') => {
    const id = Date.now().toString();
    setNotifications(prev => [...prev, { id, message, type }]);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
      setNotifications(prev => prev.filter(n => n.id !== id));
    }, 5000);
  };

  const removeNotification = (id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  };

  const fetchFiles = async () => {
    try {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) return;

      const { data: files, error } = await supabase
        .from('documents')
        .select(`
          id,
          content,
          metadata,
          created_at,
          clusters!inner(
            id,
            label
          )
        `)
        .eq('metadata->>user_id', user.id)
        .order('created_at', { ascending: false });

      if (error) throw error;

      const processedFiles: UploadedFile[] = files?.map((file: any) => ({
        id: file.id,
        name: file.metadata?.filename || 'Unknown',
        type: file.metadata?.type || 'unknown',
        size: formatFileSize(file.metadata?.size || 0),
        modified: formatDate(file.created_at),
        category: file.clusters?.label || 'General Documents',
        storage_path: file.metadata?.storage_path,
        view_count: file.metadata?.view_count || 0,
        metadata: file.metadata,
        content: file.content,
        created_at: file.created_at,
        cluster_id: file.clusters?.id
      })) || [];

      setAllFiles(processedFiles);
      setUploadedFiles(processedFiles);
      setTotalFilesCount(processedFiles.length);
      
      // Calculate storage used
      const totalSize = processedFiles.reduce((sum, file) => {
        const size = file.metadata?.size || 0;
        return sum + size;
      }, 0);
      setStorageUsed(totalSize);

      // Calculate category counts
      const categoryMap = new Map<string, number>();
      processedFiles.forEach(file => {
        const category = file.category;
        categoryMap.set(category, (categoryMap.get(category) || 0) + 1);
      });

      const categories: CategoryCount[] = Array.from(categoryMap.entries()).map(([name, count]) => ({
        name,
        icon: null, // Will be set by parent component
        count,
        color: getCategoryColor(name)
      }));

      setCategoryCount(categories);

      // Calculate frequent folders (most accessed categories)
      const frequentFoldersData: FrequentFolder[] = categories
        .sort((a, b) => b.count - a.count)
        .slice(0, 4)
        .map(cat => ({
          name: cat.name,
          icon: null, // Will be set by parent component
          color: cat.color,
          count: cat.count
        }));

      setFrequentFolders(frequentFoldersData);

    } catch (error) {
      console.error('Error fetching files:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (files: FileList) => {
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) return;

    addNotification(`Uploading ${files.length} file(s)...`, 'info');

    for (const file of Array.from(files)) {
      try {
        const result = await uploadDocument(file, user.id);
        if (result.status === 'queued' || result.status === 'success') {
          addNotification(`✅ ${file.name} uploaded successfully!`, 'success');
          // Refresh files after upload
          await fetchFiles();
        } else if (result.status === 'duplicate') {
          addNotification(`⚠️ ${file.name} already exists`, 'info');
        } else {
          addNotification(`❌ Failed to upload ${file.name}`, 'error');
        }
      } catch (error) {
        console.error('Upload failed:', error);
        addNotification(`❌ Failed to upload ${file.name}: ${error}`, 'error');
      }
    }
  };

  const deleteFile = async (fileId: string, _fileName: string, storagePath?: string) => {
    try {
      // Delete from database
      const { error: dbError } = await supabase
        .from('documents')
        .delete()
        .eq('id', fileId);

      if (dbError) throw dbError;

      // Delete from storage if path exists
      if (storagePath) {
        const { error: storageError } = await supabase.storage
          .from('documents')
          .remove([storagePath]);

        if (storageError) console.warn('Storage deletion failed:', storageError);
      }

      // Refresh files
      await fetchFiles();
    } catch (error) {
      console.error('Delete failed:', error);
    }
  };

  const renameFile = async (fileId: string, newName: string) => {
    try {
      const { error } = await supabase
        .from('documents')
        .update({
          metadata: { filename: newName }
        })
        .eq('id', fileId);

      if (error) throw error;

      // Refresh files
      await fetchFiles();
    } catch (error) {
      console.error('Rename failed:', error);
    }
  };

  useEffect(() => {
    fetchFiles();
  }, []);

  return {
    uploadedFiles,
    allFiles,
    isLoading,
    totalFilesCount,
    storageUsed,
    categoryCount,
    frequentFolders,
    folderCounts,
    notifications,
    addNotification,
    removeNotification,
    fetchFiles,
    handleFileUpload,
    deleteFile,
    renameFile
  };
};

// Helper functions
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  const now = new Date();
  const diffTime = Math.abs(now.getTime() - date.getTime());
  const diffMinutes = Math.floor(diffTime / (1000 * 60));
  const diffHours = Math.floor(diffTime / (1000 * 60 * 60));
  const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
  
  if (diffMinutes < 1) return 'Just now';
  if (diffMinutes < 60) return `${diffMinutes} minute${diffMinutes > 1 ? 's' : ''} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.ceil(diffDays / 7)} week${Math.ceil(diffDays / 7) > 1 ? 's' : ''} ago`;
  return `${Math.ceil(diffDays / 30)} month${Math.ceil(diffDays / 30) > 1 ? 's' : ''} ago`;
};

const getCategoryColor = (category: string): string => {
  const colors: Record<string, string> = {
    'Academic Work': 'bg-gradient-to-r from-blue-500 to-blue-600',
    'Course Materials': 'bg-gradient-to-r from-green-500 to-green-600', 
    'Research & Papers': 'bg-gradient-to-r from-purple-500 to-purple-600',
    'Science & Tech': 'bg-gradient-to-r from-indigo-500 to-indigo-600',
    'Mathematics': 'bg-gradient-to-r from-orange-500 to-orange-600',
    'Business & Finance': 'bg-gradient-to-r from-emerald-500 to-emerald-600',
    'Language & Arts': 'bg-gradient-to-r from-pink-500 to-pink-600',
    'Health & Medicine': 'bg-gradient-to-r from-red-500 to-red-600',
    'Social Sciences': 'bg-gradient-to-r from-teal-500 to-teal-600',
    'Professional Documents': 'bg-gradient-to-r from-amber-500 to-amber-600',
    'General Documents': 'bg-gradient-to-r from-gray-500 to-gray-600',
    // Fallback for old categories
    Math: "bg-orange-500",
    Science: "bg-green-500",
    History: "bg-blue-500",
    English: "bg-purple-500",
    Physics: "bg-red-500",
    Assignments: "bg-blue-500",
    Lectures: "bg-green-500",
    Research: "bg-purple-500",
    General: "bg-gray-500"
  };
  return colors[category] || "bg-gradient-to-r from-gray-500 to-gray-600";
};
