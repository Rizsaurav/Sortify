import React, { useState } from 'react';
import { ChevronDown, Plus, Edit2, Trash2 } from 'lucide-react';
import type { Category } from './types';

interface CategoryDropdownProps {
  currentCategory?: string;
  categories: Category[];
  onCategoryChange: (categoryId: number, categoryName: string) => void;
  onCreateCategory: (name: string, color?: string, type?: string) => void;
  onEditCategory?: (categoryId: number, newName: string, color?: string, type?: string) => void;
  onDeleteCategory?: (categoryId: number) => void;
  disabled?: boolean;
  className?: string;
}

export const CategoryDropdown: React.FC<CategoryDropdownProps> = ({
  currentCategory,
  categories,
  onCategoryChange,
  onCreateCategory,
  onEditCategory,
  onDeleteCategory,
  disabled = false,
  className = ""
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newCategoryName, setNewCategoryName] = useState('');
  const [editingCategory, setEditingCategory] = useState<number | null>(null);
  const [editName, setEditName] = useState('');

  const currentCategoryObj = categories.find(cat => cat.label === currentCategory);

  const handleCategorySelect = (category: Category) => {
    onCategoryChange(category.id, category.label);
    setIsOpen(false);
  };

  const handleCreateCategory = () => {
    if (newCategoryName.trim()) {
      onCreateCategory(newCategoryName.trim());
      setNewCategoryName('');
      setShowCreateForm(false);
    }
  };

  const handleEditCategory = (categoryId: number, newName: string) => {
    if (newName.trim() && onEditCategory) {
      onEditCategory(categoryId, newName.trim());
      setEditingCategory(null);
      setEditName('');
    }
  };

  const handleDeleteCategory = (categoryId: number) => {
    if (onDeleteCategory && window.confirm('Are you sure you want to delete this category?')) {
      onDeleteCategory(categoryId);
    }
  };

  const startEditing = (category: Category) => {
    setEditingCategory(category.id);
    setEditName(category.label);
  };

  const cancelEditing = () => {
    setEditingCategory(null);
    setEditName('');
  };

  return (
    <div className={`relative ${className}`}>
      {/* Dropdown Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={disabled}
        className={`
          w-full flex items-center justify-between px-3 py-2 
          bg-white border border-gray-300 rounded-lg
          hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500
          ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        `}
      >
        <div className="flex items-center gap-2">
          {currentCategoryObj?.color && (
            <div 
              className={`w-3 h-3 rounded-full ${currentCategoryObj.color}`}
              style={{ backgroundColor: currentCategoryObj.color }}
            />
          )}
          <span className="text-sm font-medium">
            {currentCategory || 'Select Category'}
          </span>
        </div>
        <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-300 rounded-lg shadow-lg z-50 max-h-64 overflow-y-auto">
          {/* Existing Categories */}
          {categories.map((category) => (
            <div key={category.id} className="group">
              {editingCategory === category.id ? (
                // Edit Mode
                <div className="px-3 py-2 border-b border-gray-100">
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      className="flex-1 px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          handleEditCategory(category.id, editName);
                        } else if (e.key === 'Escape') {
                          cancelEditing();
                        }
                      }}
                    />
                    <button
                      onClick={() => handleEditCategory(category.id, editName)}
                      className="p-1 text-green-600 hover:bg-green-50 rounded"
                    >
                      ✓
                    </button>
                    <button
                      onClick={cancelEditing}
                      className="p-1 text-gray-500 hover:bg-gray-50 rounded"
                    >
                      ✕
                    </button>
                  </div>
                </div>
              ) : (
                // Normal Mode
                <div className="flex items-center justify-between px-3 py-2 hover:bg-gray-50">
                  <button
                    onClick={() => handleCategorySelect(category)}
                    className="flex items-center gap-2 flex-1 text-left"
                  >
                    {category.color && (
                      <div 
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: category.color }}
                      />
                    )}
                    <span className="text-sm">{category.label}</span>
                    {category.user_created && (
                      <span className="text-xs text-blue-600 bg-blue-100 px-1 rounded">
                        Custom
                      </span>
                    )}
                  </button>
                  
                  {/* Action Buttons */}
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    {onEditCategory && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          startEditing(category);
                        }}
                        className="p-1 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded"
                        title="Edit category"
                      >
                        <Edit2 className="w-3 h-3" />
                      </button>
                    )}
                    {onDeleteCategory && category.user_created && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteCategory(category.id);
                        }}
                        className="p-1 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded"
                        title="Delete category"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}

          {/* Create New Category */}
          {showCreateForm ? (
            <div className="px-3 py-2 border-t border-gray-100">
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={newCategoryName}
                  onChange={(e) => setNewCategoryName(e.target.value)}
                  placeholder="Category name"
                  className="flex-1 px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      handleCreateCategory();
                    } else if (e.key === 'Escape') {
                      setShowCreateForm(false);
                      setNewCategoryName('');
                    }
                  }}
                />
                <button
                  onClick={handleCreateCategory}
                  className="p-1 text-green-600 hover:bg-green-50 rounded"
                >
                  ✓
                </button>
                <button
                  onClick={() => {
                    setShowCreateForm(false);
                    setNewCategoryName('');
                  }}
                  className="p-1 text-gray-500 hover:bg-gray-50 rounded"
                >
                  ✕
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={() => setShowCreateForm(true)}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-blue-600 hover:bg-blue-50 border-t border-gray-100"
            >
              <Plus className="w-4 h-4" />
              Create New Category
            </button>
          )}
          
          {/* Category Selector Dropdown */}
          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Or select from existing categories:
            </label>
            <select
              onChange={(e) => {
                const selected = categories.find(cat => cat.id === Number(e.target.value));
                if (selected) handleCategorySelect(selected);
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Choose a category...</option>
              {categories.map(cat => (
                <option key={cat.id} value={cat.id}>
                  {cat.label} {cat.type ? `(${cat.type})` : ''}
                </option>
              ))}
            </select>
          </div>
        </div>
      )}

      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setIsOpen(false)}
        />
      )}
    </div>
  );
};
