import { useState, useEffect } from 'react';
import { supabase } from '../../../../../supabase/client';
import type { UploadedFile, CategoryCount, FrequentFolder } from '../types';
import { uploadDocument, getTaskStatus } from '../../../api/sorter';

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

  // Notification counter to ensure unique IDs
  let notificationIdCounter = 0;
  
  /**
   * Add a notification to the notification stack
   * Auto-removes after 5 seconds
   */
  const addNotification = (message: string, type: 'success' | 'error' | 'info') => {
    notificationIdCounter++;
    const id = `${Date.now()}-${notificationIdCounter}`;
    setNotifications(prev => [...prev, { id, message, type }]);
    
    setTimeout(() => {
      setNotifications(prev => prev.filter(n => n.id !== id));
    }, 5000);
  };

  /**
   * Manually remove a notification by ID
   */
  const removeNotification = (id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  };

  /**
   * Fetch all files and categories from the backend
   * Processes files and calculates category counts
   */
  const fetchFiles = async () => {
    try {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) return;

      // Fetch documents from backend API
      let documents: any[] = [];
      try {
        const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/upload/documents?user_id=${user.id}`);
        if (response.ok) {
          const data = await response.json();
          documents = data.documents || [];
          console.log('Documents fetched from backend:', documents.length);
        } else {
          console.error('Error fetching documents from backend:', response.status);
        }
      } catch (error) {
        console.error('Error fetching document metadata:', error);
      }

      // Fetch categories from backend API and create ID-to-name mapping
      let categoriesMap = new Map<number, string>();
      let categoriesArray: any[] = [];
      try {
        const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/categories?user_id=${user.id}`);
        if (response.ok) {
          const data = await response.json();
          console.log('Categories fetched from backend:', data);
          if (data.categories) {
            categoriesArray = data.categories;
            data.categories.forEach((cat: any) => {
              categoriesMap.set(cat.id, cat.label);
            });
            console.log('Categories map created:', categoriesMap);
          }
        } else {
          console.error('Error fetching categories from backend:', response.status);
        }
      } catch (error) {
        console.error('Error fetching categories:', error);
      }

      // Process documents and map cluster_id to category names
      const processedFiles: UploadedFile[] = documents.map((doc: any) => {
        const categoryId = doc.cluster_id;
        const categoryName = categoryId ? categoriesMap.get(categoryId) : 'General Documents';
        
        return {
          id: doc.id,
          name: doc.metadata?.filename || 'Unknown',
          type: doc.metadata?.type || 'unknown',
          size: formatFileSize(doc.metadata?.size || 0),
          modified: formatDate(doc.created_at),
          category: categoryName || 'General Documents',
          storage_path: doc.storage_path || `${user.id}/${doc.metadata?.filename || 'unknown'}`,
          file_path: doc.file_path,
          file_url: doc.file_url,
          view_count: 0,
          metadata: {
            ...doc.metadata,
            filename: doc.metadata?.filename || 'Unknown'
          },
          content: doc.content || '',
          created_at: doc.created_at,
          cluster_id: categoryId
        };
      });

      console.log('Processed files:', processedFiles.length);
      setAllFiles(processedFiles);
      setUploadedFiles(processedFiles);
      setTotalFilesCount(processedFiles.length);
      
      // Calculate total storage used
      const totalSize = processedFiles.reduce((sum, file) => {
        const size = file.metadata?.size || 0;
        return sum + size;
      }, 0);
      setStorageUsed(totalSize);

      // Calculate category counts with proper ID mapping
      // This map stores both the count and the actual database ID for each category
      const categoryDataMap = new Map<string, { count: number; id: number }>();
      
      processedFiles.forEach(file => {
        const categoryName = file.category;
        const existingData = categoryDataMap.get(categoryName);
        
        if (existingData) {
          // Increment count for existing category
          existingData.count++;
        } else {
          // Find the category ID from the backend categories array
          const categoryEntry = categoriesArray.find((cat: any) => cat.label === categoryName);
          const categoryId = categoryEntry?.id || 0;
          
          console.log(`Mapping category "${categoryName}" to ID: ${categoryId}`);
          
          // Initialize new category with count and ID
          categoryDataMap.set(categoryName, { 
            count: 1, 
            id: categoryId 
          });
        }
      });

      // Convert map to CategoryCount array with proper IDs
      const categories: CategoryCount[] = Array.from(categoryDataMap.entries()).map(([name, data]) => ({
        id: data.id,
        name,
        icon: null,
        count: data.count,
        color: getCategoryColor(name)
      }));

      console.log('Categories with IDs for sidebar:', categories);
      setCategoryCount(categories);

      // Calculate frequent folders (top 4 most used categories)
      const frequentFoldersData: FrequentFolder[] = categories
        .sort((a, b) => b.count - a.count)
        .slice(0, 4)
        .map(cat => ({
          name: cat.name,
          icon: null,
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

  /**
   * Handle file upload with processing status tracking
   * Polls for completion before refreshing file list
   */
  const handleFileUpload = async (files: FileList) => {
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) return;

    addNotification(`Uploading ${files.length} file(s)...`, 'info');

    for (const file of Array.from(files)) {
      try {
        const result = await uploadDocument(file, user.id);
        if (result.status === 'queued' || result.status === 'success') {
          addNotification(`${file.name} uploaded successfully`, 'success');
          
          // Wait for processing to complete if there's a task_id
          if (result.task_id) {
            addNotification(`Processing ${file.name}...`, 'info');
            
            let attempts = 0;
            const maxAttempts = 30;
            
            while (attempts < maxAttempts) {
              await new Promise(resolve => setTimeout(resolve, 1000));
              
              try {
                const taskStatus = await getTaskStatus(result.task_id);
                
                if (taskStatus.status === 'completed') {
                  addNotification(`${file.name} processed successfully`, 'success');
                  break;
                } else if (taskStatus.status === 'failed') {
                  addNotification(`Failed to process ${file.name}: ${taskStatus.error}`, 'error');
                  break;
                }
                
                attempts++;
              } catch (error) {
                console.error('Error checking task status:', error);
                attempts++;
              }
            }
            
            if (attempts >= maxAttempts) {
              addNotification(`${file.name} processing is taking longer than expected`, 'info');
            }
          }
          
          // Delay to ensure processing is complete
          await new Promise(resolve => setTimeout(resolve, 500));
          
          // Refresh files after upload and processing
          await fetchFiles();
        } else if (result.status === 'duplicate') {
          addNotification(`${file.name} already exists`, 'info');
        } else {
          addNotification(`Failed to upload ${file.name}`, 'error');
        }
      } catch (error) {
        console.error('Upload failed:', error);
        addNotification(`Failed to upload ${file.name}: ${error}`, 'error');
      }
    }
  };

  /**
   * Delete a file from both database and storage
   */
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

  /**
   * Rename a file by updating its metadata
   */
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

  // Initialize by fetching files on mount
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

/**
 * Helper Functions
 */

/**
 * Format bytes to human-readable file size
 */
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

/**
 * Format date string to relative time (e.g., "2 hours ago")
 */
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

/**
 * Get Tailwind CSS gradient class for a given category
 */
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
    'Occupational Safety Health': 'bg-gradient-to-r from-yellow-500 to-yellow-600',
    // Fallback for legacy categories
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