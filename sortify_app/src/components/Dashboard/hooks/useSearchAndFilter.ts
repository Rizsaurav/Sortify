import { useState, useEffect } from 'react';
import type { UploadedFile } from '../types';

export const useSearchAndFilter = (files: UploadedFile[]) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<string | null>(null);
  const [filteredFiles, setFilteredFiles] = useState<UploadedFile[]>([]);

  useEffect(() => {
    let filtered = [...files];

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(file =>
        file.name.toLowerCase().includes(query) ||
        file.category.toLowerCase().includes(query) ||
        (file.content && file.content.toLowerCase().includes(query))
      );
    }

    // Apply category filter
    if (selectedCategory) {
      filtered = filtered.filter(file => file.category === selectedCategory);
    }

    // Apply additional filters
    if (activeFilter) {
      switch (activeFilter) {
        case 'recent':
          filtered = filtered.sort((a, b) => 
            new Date(b.created_at || '').getTime() - new Date(a.created_at || '').getTime()
          );
          break;
        case 'oldest':
          filtered = filtered.sort((a, b) => 
            new Date(a.created_at || '').getTime() - new Date(b.created_at || '').getTime()
          );
          break;
        case 'largest':
          filtered = filtered.sort((a, b) => {
            const sizeA = parseFileSize(a.size);
            const sizeB = parseFileSize(b.size);
            return sizeB - sizeA;
          });
          break;
        case 'smallest':
          filtered = filtered.sort((a, b) => {
            const sizeA = parseFileSize(a.size);
            const sizeB = parseFileSize(b.size);
            return sizeA - sizeB;
          });
          break;
        case 'name-asc':
          filtered = filtered.sort((a, b) => a.name.localeCompare(b.name));
          break;
        case 'name-desc':
          filtered = filtered.sort((a, b) => b.name.localeCompare(a.name));
          break;
      }
    }

    setFilteredFiles(filtered);
  }, [files, searchQuery, selectedCategory, activeFilter]);

  const handleCategoryFilter = (category: string) => {
    setSelectedCategory(selectedCategory === category ? null : category);
  };

  const clearFilters = () => {
    setSearchQuery('');
    setSelectedCategory(null);
    setActiveFilter(null);
  };

  return {
    searchQuery,
    setSearchQuery,
    selectedCategory,
    setSelectedCategory,
    activeFilter,
    setActiveFilter,
    filteredFiles,
    handleCategoryFilter,
    clearFilters
  };
};

// Helper function to parse file size strings
const parseFileSize = (sizeStr: string): number => {
  const match = sizeStr.match(/(\d+\.?\d*)\s*(KB|MB|GB|Bytes?)/i);
  if (!match) return 0;
  
  const size = parseFloat(match[1]);
  const unit = match[2].toUpperCase();
  
  switch (unit) {
    case 'BYTES':
    case 'BYTE':
      return size;
    case 'KB':
      return size * 1024;
    case 'MB':
      return size * 1024 * 1024;
    case 'GB':
      return size * 1024 * 1024 * 1024;
    default:
      return 0;
  }
};
