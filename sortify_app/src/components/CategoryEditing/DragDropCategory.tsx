import React, { useState, useRef } from 'react';
import { FileText, Folder, Check, X } from 'lucide-react';
import type { Category } from './types';

interface DragDropCategoryProps {
  file: {
    id: string;
    name: string;
    category?: string;
    category_id?: number;
    size?: string;
    created_at?: string;
  };
  categories: Category[];
  onCategoryChange: (fileId: string, categoryId: number, categoryName: string) => void;
  onCancel: () => void;
}

export const DragDropCategory: React.FC<DragDropCategoryProps> = ({
  file,
  categories,
  onCategoryChange,
  onCancel
}) => {
  const [draggedOver, setDraggedOver] = useState<number | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const dragRef = useRef<HTMLDivElement>(null);

  const handleDragStart = (e: React.DragEvent) => {
    setIsDragging(true);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', file.id);
  };

  const handleDragEnd = () => {
    setIsDragging(false);
    setDraggedOver(null);
  };

  const handleDragOver = (e: React.DragEvent, categoryId: number) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setDraggedOver(categoryId);
  };

  const handleDragLeave = () => {
    setDraggedOver(null);
  };

  const handleDrop = (e: React.DragEvent, category: Category) => {
    e.preventDefault();
    const fileId = e.dataTransfer.getData('text/plain');
    
    if (fileId === file.id) {
      onCategoryChange(fileId, category.id, category.label);
    }
    
    setDraggedOver(null);
  };

  const handleCategoryClick = (category: Category) => {
    onCategoryChange(file.id, category.id, category.label);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <FileText className="w-6 h-6 text-blue-600" />
              <div>
                <h3 className="text-lg font-semibold text-gray-900">
                  Move File to Category
                </h3>
                <p className="text-sm text-gray-600">{file.name}</p>
              </div>
            </div>
            <button
              onClick={onCancel}
              className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Instructions */}
        <div className="px-6 py-3 bg-blue-50 border-b border-blue-200">
          <p className="text-sm text-blue-800">
            Drag the file to a category or click on a category to move it
          </p>
        </div>

        {/* File Preview */}
        <div className="px-6 py-4">
          <div
            ref={dragRef}
            draggable
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
            className={`
              flex items-center gap-3 p-3 border-2 border-dashed rounded-lg
              ${isDragging ? 'border-blue-400 bg-blue-50' : 'border-gray-300 bg-gray-50'}
              cursor-move hover:border-blue-400 hover:bg-blue-50 transition-colors
            `}
          >
            <FileText className="w-8 h-8 text-blue-600" />
            <div className="flex-1">
              <p className="font-medium text-gray-900">{file.name}</p>
              <p className="text-sm text-gray-600">
                Current category: {file.category || 'Uncategorized'}
              </p>
            </div>
            <div className="text-xs text-gray-500">
              Drag me
            </div>
          </div>
        </div>

        {/* Categories Grid */}
        <div className="px-6 pb-6">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {categories.map((category) => (
              <div
                key={category.id}
                className={`
                  relative p-4 border-2 border-dashed rounded-lg cursor-pointer
                  transition-all duration-200 hover:scale-105
                  ${draggedOver === category.id 
                    ? 'border-green-400 bg-green-50 scale-105' 
                    : 'border-gray-300 hover:border-blue-400 hover:bg-blue-50'
                  }
                `}
                onDragOver={(e) => handleDragOver(e, category.id)}
                onDragLeave={handleDragLeave}
                onDrop={(e) => handleDrop(e, category)}
                onClick={() => handleCategoryClick(category)}
              >
                {/* Drop Indicator */}
                {draggedOver === category.id && (
                  <div className="absolute inset-0 flex items-center justify-center bg-green-100 bg-opacity-50 rounded-lg">
                    <Check className="w-8 h-8 text-green-600" />
                  </div>
                )}

                <div className="flex flex-col items-center text-center">
                  <div className="mb-2">
                    {category.color ? (
                      <div 
                        className="w-8 h-8 rounded-full flex items-center justify-center"
                        style={{ backgroundColor: category.color }}
                      >
                        <Folder className="w-4 h-4 text-white" />
                      </div>
                    ) : (
                      <div className="w-8 h-8 rounded-full bg-gray-400 flex items-center justify-center">
                        <Folder className="w-4 h-4 text-white" />
                      </div>
                    )}
                  </div>
                  
                  <h4 className="font-medium text-gray-900 text-sm mb-1">
                    {category.label}
                  </h4>
                  
                  {category.user_created && (
                    <span className="text-xs text-blue-600 bg-blue-100 px-2 py-0.5 rounded-full">
                      Custom
                    </span>
                  )}
                </div>

                {/* Drop Zone Overlay */}
                <div className="absolute inset-0 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity">
                  <div className="bg-blue-600 text-white px-3 py-1 rounded-full text-xs font-medium">
                    Drop here
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Empty State */}
          {categories.length === 0 && (
            <div className="text-center py-8">
              <Folder className="w-12 h-12 text-gray-400 mx-auto mb-3" />
              <p className="text-gray-600">No categories available</p>
              <p className="text-sm text-gray-500">Create a category first to organize your files</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-end gap-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
};
