import React, { useState, useEffect } from 'react';
import { X, Plus, Edit2, Trash2, Palette, Save } from 'lucide-react';
import type { Category } from './types';

interface CategoryManagementModalProps {
  isOpen: boolean;
  onClose: () => void;
  categories: Category[];
  onCreateCategory: (name: string, color: string, type?: string) => void;
  onEditCategory: (id: number, name: string, color: string, type?: string) => void;
  onDeleteCategory: (id: number) => void;
}

const PREDEFINED_COLORS = [
  '#3B82F6', // Blue
  '#10B981', // Emerald
  '#F59E0B', // Amber
  '#EF4444', // Red
  '#8B5CF6', // Violet
  '#06B6D4', // Cyan
  '#84CC16', // Lime
  '#F97316', // Orange
  '#EC4899', // Pink
  '#6B7280', // Gray
];

export const CategoryManagementModal: React.FC<CategoryManagementModalProps> = ({
  isOpen,
  onClose,
  categories,
  onCreateCategory,
  onEditCategory,
  onDeleteCategory
}) => {
  const [activeTab, setActiveTab] = useState<'create' | 'manage'>('create');
  const [newCategoryName, setNewCategoryName] = useState('');
  const [selectedColor, setSelectedColor] = useState(PREDEFINED_COLORS[0]);
  const [categoryType, setCategoryType] = useState('');
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);
  const [editName, setEditName] = useState('');
  const [editColor, setEditColor] = useState('');
  const [editType, setEditType] = useState('');

  useEffect(() => {
    if (isOpen) {
      setNewCategoryName('');
      setSelectedColor(PREDEFINED_COLORS[0]);
      setCategoryType('');
      setEditingCategory(null);
      setEditName('');
      setEditColor('');
      setEditType('');
    }
  }, [isOpen]);

  const handleCreateCategory = () => {
    if (newCategoryName.trim()) {
      setTimeout(() => {
        onCreateCategory(newCategoryName.trim(), selectedColor, categoryType.trim());
        setNewCategoryName('');
        setSelectedColor(PREDEFINED_COLORS[0]);
        setCategoryType('');
      }, 0);
    }
  };

  const handleEditCategory = () => {
    if (editingCategory && editName.trim()) {
      onEditCategory(editingCategory.id, editName.trim(), editColor, editType.trim());
      setEditingCategory(null);
      setEditName('');
      setEditColor('');
      setEditType('');
    }
  };

  const handleDeleteCategory = (category: Category) => {
    if (window.confirm(`Are you sure you want to delete "${category.label}"? This will move all files in this category to "General Documents".`)) {
      onDeleteCategory(category.id);
    }
  };

  const startEditing = (category: Category) => {
    setEditingCategory(category);
    setEditName(category.label);
    setEditColor(category.color || PREDEFINED_COLORS[0]);
    setEditType(category.type || '');
  };

  const cancelEditing = () => {
    setEditingCategory(null);
    setEditName('');
    setEditColor('');
    setEditType('');
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900">
              Category Management
            </h2>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="px-6 py-3 border-b border-gray-200">
          <div className="flex gap-1">
            <button
              onClick={() => setActiveTab('create')}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                activeTab === 'create'
                  ? 'bg-blue-100 text-blue-700'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
              }`}
            >
              <Plus className="w-4 h-4 inline mr-2" />
              Create Category
            </button>
            <button
              onClick={() => setActiveTab('manage')}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                activeTab === 'manage'
                  ? 'bg-blue-100 text-blue-700'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
              }`}
            >
              <Edit2 className="w-4 h-4 inline mr-2" />
              Manage Categories
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="px-6 py-4 max-h-96 overflow-y-auto">
          {activeTab === 'create' ? (
            /* Create Category Tab */
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Category Name
                </label>
                <input
                  type="text"
                  value={newCategoryName}
                  onChange={(e) => setNewCategoryName(e.target.value)}
                  placeholder="Enter category name"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      handleCreateCategory();
                    }
                  }}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Color
                </label>
                <div className="grid grid-cols-5 gap-2">
                  {PREDEFINED_COLORS.map((color) => (
                    <button
                      key={color}
                      onClick={() => setSelectedColor(color)}
                      className={`
                        w-8 h-8 rounded-full border-2 transition-all
                        ${selectedColor === color 
                          ? 'border-gray-800 scale-110' 
                          : 'border-gray-300 hover:border-gray-500'
                        }
                      `}
                      style={{ backgroundColor: color }}
                    />
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Type (Optional)
                </label>
                <input
                  type="text"
                  value={categoryType}
                  onChange={(e) => setCategoryType(e.target.value)}
                  placeholder="e.g., Invoice, Contract, Report"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                <div 
                  className="w-6 h-6 rounded-full"
                  style={{ backgroundColor: selectedColor }}
                />
                <span className="text-sm text-gray-600">
                  Preview: {newCategoryName || 'Category Name'}
                  {categoryType && ` (${categoryType})`}
                </span>
              </div>

              <button
                onClick={handleCreateCategory}
                disabled={!newCategoryName.trim()}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <Save className="w-4 h-4" />
                Create Category
              </button>
            </div>
          ) : (
            /* Manage Categories Tab */
            <div className="space-y-3">
              {categories.length === 0 ? (
                <div className="text-center py-8">
                  <Palette className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                  <p className="text-gray-600">No categories available</p>
                  <p className="text-sm text-gray-500">Create your first category to get started</p>
                </div>
              ) : (
                categories.map((category) => (
                  <div key={category.id} className="group">
                    {editingCategory?.id === category.id ? (
                      /* Edit Mode */
                      <div className="p-4 border border-gray-300 rounded-lg bg-gray-50">
                        <div className="space-y-3">
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              Category Name
                            </label>
                            <input
                              type="text"
                              value={editName}
                              onChange={(e) => setEditName(e.target.value)}
                              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                              autoFocus
                            />
                          </div>
                          
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              Color
                            </label>
                            <div className="grid grid-cols-5 gap-2">
                              {PREDEFINED_COLORS.map((color) => (
                                <button
                                  key={color}
                                  onClick={() => setEditColor(color)}
                                  className={`
                                    w-6 h-6 rounded-full border-2 transition-all
                                    ${editColor === color 
                                      ? 'border-gray-800 scale-110' 
                                      : 'border-gray-300 hover:border-gray-500'
                                    }
                                  `}
                                  style={{ backgroundColor: color }}
                                />
                              ))}
                            </div>
                          </div>
                          
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              Type (Optional)
                            </label>
                            <input
                              type="text"
                              value={editType}
                              onChange={(e) => setEditType(e.target.value)}
                              placeholder="e.g., Invoice, Contract, Report"
                              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                            />
                          </div>
                          
                          <div className="flex gap-2">
                            <button
                              onClick={handleEditCategory}
                              className="flex items-center gap-2 px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                            >
                              <Save className="w-4 h-4" />
                              Save
                            </button>
                            <button
                              onClick={cancelEditing}
                              className="px-3 py-2 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400 transition-colors"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      </div>
                    ) : (
                      /* Normal Mode */
                      <div className="flex items-center justify-between p-4 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">
                        <div className="flex items-center gap-3">
                          <div 
                            className="w-6 h-6 rounded-full"
                            style={{ backgroundColor: category.color || '#6B7280' }}
                          />
                          <div>
                            <h3 className="font-medium text-gray-900">{category.label}</h3>
                            {category.user_created && (
                              <span className="text-xs text-blue-600 bg-blue-100 px-2 py-0.5 rounded-full">
                                Custom
                              </span>
                            )}
                          </div>
                        </div>
                        
                        <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button
                            onClick={() => startEditing(category)}
                            className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg"
                            title="Edit category"
                          >
                            <Edit2 className="w-4 h-4" />
                          </button>
                          {category.user_created && (
                            <button
                              onClick={() => handleDeleteCategory(category)}
                              className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg"
                              title="Delete category"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
