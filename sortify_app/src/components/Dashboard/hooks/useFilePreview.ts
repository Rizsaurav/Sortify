import { useState } from 'react';
import { supabase } from '../../../../../supabase/client';
import type { UploadedFile, FilePreviewState, PreviewType } from '../types';

export const useFilePreview = () => {
  const [previewState, setPreviewState] = useState<FilePreviewState>({
    file: null,
    url: null,
    content: null,
    type: 'none'
  });

  const getFileType = (file: UploadedFile): PreviewType => {
    const type = file.type.toLowerCase();
    const name = file.name.toLowerCase();

    if (type.includes('pdf') || name.endsWith('.pdf')) return 'pdf';
    if (type.includes('image') || name.match(/\.(jpg|jpeg|png|gif|bmp|webp|svg)$/)) return 'image';
    if (type.includes('video') || name.match(/\.(mp4|webm|ogg|mov|avi)$/)) return 'video';
    if (type.includes('text') || name.match(/\.(txt|md|json|csv|log)$/)) return 'text';
    
    // Office documents
    if (type.includes('word') || type.includes('document') || name.match(/\.(doc|docx)$/)) return 'office';
    if (type.includes('excel') || type.includes('spreadsheet') || name.match(/\.(xls|xlsx)$/)) return 'office';
    if (type.includes('powerpoint') || type.includes('presentation') || name.match(/\.(ppt|pptx)$/)) return 'office';
    if (type.includes('openxml') || name.match(/\.(docx|xlsx|pptx)$/)) return 'office';
    
    return 'text';
  };

  const getFileUrl = async (file: UploadedFile): Promise<string | null> => {
    // If file_url is already stored in database, use that first
    if (file.file_url) {
      console.log('Using stored file_url:', file.file_url);
      return file.file_url;
    }

    // Otherwise, generate URL from storage_path
    const storagePath = file.storage_path || file.file_path;
    
    if (!storagePath) {
      console.error('No storage path found for file:', file.name);
      return null;
    }

    try {
      // Use correct bucket name: user-files
      const { data: publicData } = supabase.storage
        .from('user-files')
        .getPublicUrl(storagePath);

      // Test if the public URL works
      try {
        const testResponse = await fetch(publicData.publicUrl, { method: 'HEAD' });
        
        if (testResponse.ok) {
          console.log('Using public URL:', publicData.publicUrl);
          return publicData.publicUrl;
        }
      } catch (fetchError) {
        console.log('Public URL test failed, trying signed URL...');
      }

      // If public URL doesn't work, get a signed URL (for private buckets)
      const { data: signedData, error } = await supabase.storage
        .from('user-files')
        .createSignedUrl(storagePath, 3600); // Valid for 1 hour

      if (error) {
        console.error('Error creating signed URL:', error);
        return null;
      }

      console.log('Using signed URL:', signedData.signedUrl);
      return signedData.signedUrl;

    } catch (error) {
      console.error('Error getting file URL:', error);
      return null;
    }
  };

  const handlePreviewFile = async (file: UploadedFile) => {
    const fileType = getFileType(file);
    
    console.log('Previewing file:', {
      name: file.name,
      type: fileType,
      storage_path: file.storage_path,
      file_path: file.file_path,
      file_url: file.file_url
    });
    
    setPreviewState({
      file,
      url: null,
      content: null,
      type: fileType
    });

    try {
      if (fileType === 'text' && file.content) {
        // For text files, use stored content
        setPreviewState(prev => ({
          ...prev,
          content: file.content ?? null,
        }));
      } else {
        // For all other files, get the URL
        const url = await getFileUrl(file);
        
        if (url) {
          setPreviewState(prev => ({
            ...prev,
            url
          }));
        } else {
          console.error('Failed to get file URL');
        }
      }
    } catch (error) {
      console.error('Error loading preview:', error);
    }
  };

  const closePreview = () => {
    setPreviewState({
      file: null,
      url: null,
      content: null,
      type: 'none'
    });
  };

  const downloadFile = async (storagePath: string, fileName: string) => {
    try {
      console.log('Downloading file:', { storagePath, fileName });
      
      // Use correct bucket name: user-files
      const { data, error } = await supabase.storage
        .from('user-files')
        .download(storagePath);

      if (error) {
        console.error('Download error:', error);
        throw error;
      }

      const url = URL.createObjectURL(data);
      const link = document.createElement('a');
      link.href = url;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      
      console.log('File downloaded successfully');
    } catch (error) {
      console.error('Download failed:', error);
    }
  };

  return {
    previewState,
    handlePreviewFile,
    closePreview,
    downloadFile,
    getFileType
  };
};