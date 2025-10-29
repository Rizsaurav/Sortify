import { FileText, Image as ImageIcon, Film } from 'lucide-react';
import type { UploadedFile } from '../types';

export const getCategoryColor = (category: string): string => {
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

export const getFileIcon = (file: UploadedFile) => {
  const type = file.type.toLowerCase();
  const name = file.name.toLowerCase();
  
  if (type.includes('mp4') || type.includes('video') || name.match(/\.(mp4|webm|ogg|mov|avi)$/)) {
    return { icon: Film, className: "w-5 h-5 text-muted-foreground" };
  }
  if (type.includes('image') || name.match(/\.(jpg|jpeg|png|gif|bmp|webp|svg)$/)) {
    return { icon: ImageIcon, className: "w-5 h-5 text-muted-foreground" };
  }
  if (type.includes('pdf') || name.endsWith('.pdf')) {
    return { icon: FileText, className: "w-5 h-5 text-red-500" };
  }
  if (type.includes('word') || type.includes('document') || name.match(/\.(doc|docx)$/)) {
    return { icon: FileText, className: "w-5 h-5 text-blue-500" };
  }
  if (type.includes('excel') || type.includes('spreadsheet') || name.match(/\.(xls|xlsx)$/)) {
    return { icon: FileText, className: "w-5 h-5 text-green-500" };
  }
  if (type.includes('powerpoint') || type.includes('presentation') || name.match(/\.(ppt|pptx)$/)) {
    return { icon: FileText, className: "w-5 h-5 text-orange-500" };
  }
  return { icon: FileText, className: "w-5 h-5 text-muted-foreground" };
};

export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

export const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  const now = new Date();
  const diffTime = Math.abs(now.getTime() - date.getTime());
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  
  if (diffDays === 1) return '1 day ago';
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.ceil(diffDays / 7)} weeks ago`;
  return `${Math.ceil(diffDays / 30)} months ago`;
};
