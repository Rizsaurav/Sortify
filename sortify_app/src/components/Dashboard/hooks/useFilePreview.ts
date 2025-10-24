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
    
    return 'text'; // Default fallback
  };

  const handlePreviewFile = async (file: UploadedFile) => {
    const fileType = getFileType(file);
    
    setPreviewState({
      file,
      url: null,
      content: null,
      type: fileType
    });

    try {
      if (fileType === 'pdf' && file.storage_path) {
        // Get PDF URL from storage
        const { data } = supabase.storage
          .from('documents')
          .getPublicUrl(file.storage_path);
        
        setPreviewState(prev => ({
          ...prev,
          url: data.publicUrl
        }));
      } else if (fileType === 'image' && file.storage_path) {
        // Get image URL from storage
        const { data } = supabase.storage
          .from('documents')
          .getPublicUrl(file.storage_path);
        
        setPreviewState(prev => ({
          ...prev,
          url: data.publicUrl
        }));
      } else if (fileType === 'video' && file.storage_path) {
        // Get video URL from storage
        const { data } = supabase.storage
          .from('documents')
          .getPublicUrl(file.storage_path);
        
        setPreviewState(prev => ({
          ...prev,
          url: data.publicUrl
        }));
      } else if (fileType === 'office' && file.storage_path) {
        // Get office document URL from storage
        const { data } = supabase.storage
          .from('documents')
          .getPublicUrl(file.storage_path);
        
        setPreviewState(prev => ({
          ...prev,
          url: data.publicUrl
        }));
      } else if (fileType === 'text' && file.content) {
        setPreviewState(prev => ({
          ...prev,
          content: file.content ?? null,  // <--- fixed
        }));
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
      const { data, error } = await supabase.storage
        .from('documents')
        .download(storagePath);

      if (error) throw error;

      const url = URL.createObjectURL(data);
      const link = document.createElement('a');
      link.href = url;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
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
