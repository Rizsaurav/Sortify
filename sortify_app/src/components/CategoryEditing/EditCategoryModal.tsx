import React, { useState, useEffect } from 'react';
import { X, FileText } from 'lucide-react';
import type { Category } from './types';

interface EditCategoryModalProps {
  file: {
    id: string;
    name: string;
    category?: string;
    category_id?: number;
    size?: string;
    created_at?: string;
  } | null;
  categories: Category[];
  isOpen: boolean;
  onClose: () => void;
  onSave: (fileId: string, categoryId: number, categoryName: string) => void;
  onRefreshCategories?: () => void;
}

export const EditCategoryModal: React.FC<EditCategoryModalProps> = ({
  file,
  categories,
  isOpen,
  onClose,
  onSave,
  onRefreshCategories
}) => {
  const [selectedCategoryId, setSelectedCategoryId] = useState<number | null>(null);
  const [categoryName, setCategoryName] = useState('');

  useEffect(() => {
    if (file) {
      setSelectedCategoryId(file.category_id || null);
      setCategoryName(file.category || '');
    }
  }, [file]);

  if (!isOpen || !file) return null;

  const handleSave = () => {
    if (selectedCategoryId !== null) {
      onSave(file.id, selectedCategoryId, categoryName);
      onClose();
    }
  };

  const handleCategoryChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const catId = Number(e.target.value);
    setSelectedCategoryId(catId);
    const cat = categories.find(c => c.id === catId);
    setCategoryName(cat?.label || '');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Glassmorphism Backdrop */}
      <div 
        className="absolute inset-0 bg-gradient-to-br from-blue-500/10 via-purple-500/10 to-pink-500/10 backdrop-blur-md"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative bg-white/90 backdrop-blur-xl rounded-2xl shadow-2xl max-w-md w-full border border-white/20 animate-fadeIn">
        {/* Header with gradient */}
        <div className="relative px-6 py-4 border-b border-gray-200/50 bg-gradient-to-r from-blue-50/50 to-purple-50/50 rounded-t-2xl">
          <h3 className="text-lg font-semibold text-gray-800">Edit Category</h3>
          <button 
            onClick={onClose}
            className="absolute top-4 right-4 p-2 text-gray-400 hover:text-gray-600 hover:bg-white/50 rounded-lg transition-all"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          {/* File Info */}
          <div className="flex items-center gap-3 p-3 bg-gradient-to-r from-gray-50 to-blue-50 rounded-lg border border-gray-200/50">
            <FileText className="w-8 h-8 text-blue-500" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-700 truncate">{file.name}</p>
              <p className="text-xs text-gray-500">{file.size} • {file.created_at}</p>
            </div>
          </div>

          {/* Category Selector */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select Category
            </label>
            <select
              value={selectedCategoryId || ''}
              onChange={handleCategoryChange}
              className="w-full px-4 py-3 bg-white border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
            >
              <option value="">Choose a category...</option>
              {categories.length > 0 ? (
                categories.map(cat => (
                  <option key={cat.id} value={cat.id}>
                    {cat.label} {cat.type ? `(${cat.type})` : ''}
                  </option>
                ))
              ) : (
                <option value="" disabled>Loading categories...</option>
              )}
            </select>
            {categories.length === 0 && (
              <div className="flex items-center justify-between">
                <p className="text-xs text-gray-500">No categories available.</p>
                {onRefreshCategories && (
                  <button
                    onClick={onRefreshCategories}
                    className="text-xs text-blue-600 hover:text-blue-800 underline"
                  >
                    Refresh
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Preview */}
          <div className="flex items-center gap-3 p-3 bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg border border-blue-200/50">
            <div 
              className="w-4 h-4 rounded-full"
              style={{ backgroundColor: categories.find(c => c.id === selectedCategoryId)?.color || '#6B7280' }}
            />
            <span className="text-sm text-gray-700">
              Preview: <span className="font-medium">{categoryName || 'No category selected'}</span>
            </span>
          </div>
        </div>

        {/* Actions */}
        <div className="px-6 py-4 bg-gray-50/50 border-t border-gray-200/50 rounded-b-2xl flex gap-3">
          <button
            onClick={handleSave}
            disabled={selectedCategoryId === null}
            className="flex-1 px-4 py-2.5 bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-xl hover:from-blue-600 hover:to-blue-700 font-medium shadow-lg shadow-blue-500/30 transition-all hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
          >
            Save Changes
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2.5 bg-white border border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 font-medium transition-all"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
};
