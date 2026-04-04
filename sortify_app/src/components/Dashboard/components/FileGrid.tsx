import React, { useState } from 'react';
import { Download, Trash2, Edit2 } from 'lucide-react';
import type { UploadedFile, ViewMode } from '../types';
import { getFileIcon, getCategoryColor } from '../utils/fileUtils';
import { EditCategoryModal } from '../../CategoryEditing/EditCategoryModal';
import type { Category } from '../../CategoryEditing/types';

interface FileGridProps {
  files: UploadedFile[];
  viewMode: ViewMode;
  renamingFileId: string | null;
  newFileName: string;
  categories: Category[];
  onPreviewFile: (file: UploadedFile) => void;
  onDownloadFile: (storagePath: string, fileName: string) => void;
  onDeleteFile: (fileId: string, fileName: string, storagePath?: string) => void;
  onFileNameChange: (name: string) => void;
  onConfirmRename: (fileId: string) => void;
  onCategoryChange: (fileId: string, categoryId: number, categoryName: string) => void;
  onRefreshCategories?: () => void;
}

// --- Helper: Generate Image based on Category ---
const getCategoryImage = (category: string, width: number, height: number): string => {
  // Map categories to search terms
  const keywordMap: Record<string, string> = {
    'Computer Science': 'coding,computer',
    'Biology': 'biology,cell,microscope',
    'Chemistry': 'chemistry,lab,science',
    'Physics': 'physics,astronomy',
    'Mathematics': 'math,geometry,numbers',
    'Engineering': 'engineering,blueprint',
    'Business': 'office,meeting',
    'Assignments': 'writing,notebook,study',
    'Lectures': 'classroom,blackboard',
    'Research': 'library,books',
    'General': 'desk,work'
  };

  let keywords = keywordMap[category];
  if (!keywords) {
    keywords = category.toLowerCase().replace(/\s+/g, ',');
  }

  // Add a lock based on category length to keep images consistent per category
  return `https://loremflickr.com/${width}/${height}/${encodeURIComponent(keywords)}?lock=${category.length}`;
};

export const FileGrid: React.FC<FileGridProps> = ({
  files,
  viewMode,
  renamingFileId,
  newFileName,
  categories,
  onPreviewFile,
  onDownloadFile,
  onDeleteFile,
  onFileNameChange,
  onConfirmRename,
  onCategoryChange,
  onRefreshCategories
}) => {
  const [editingFile, setEditingFile] = useState<UploadedFile | null>(null);
  const [draggedFile, setDraggedFile] = useState<UploadedFile | null>(null);
  const [hoveredFile, setHoveredFile] = useState<string | null>(null);

  const handleDragStart = (e: React.DragEvent, file: UploadedFile) => {
    e.stopPropagation();
    if (file.id.startsWith('demo-')) {
      e.preventDefault();
      return;
    }
    setDraggedFile(file);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('application/x-file-card', JSON.stringify({
      fileId: file.id,
      fileName: file.name
    }));
  };

  const handleDragEnd = () => {
    setDraggedFile(null);
  };

  const handleEditCategory = (file: UploadedFile) => {
    setEditingFile(file);
  };

  const handleSaveCategory = (fileId: string, categoryId: number, categoryName: string) => {
    if (fileId.startsWith('demo-')) {
      console.warn('Cannot change category for demo files');
      setEditingFile(null);
      return;
    }
    onCategoryChange(fileId, categoryId, categoryName);
    setEditingFile(null);
  };

  if (viewMode === 'directory') {
    return null;
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {files.map((file) => {
        const isHovered = hoveredFile === file.id;
        const isDragging = draggedFile?.id === file.id;
        const isDemo = file.id.startsWith('demo-');
        
        return (
          <div 
            key={file.id} 
            draggable={!isDemo}
            onDragStart={(e) => handleDragStart(e, file)}
            onDragEnd={handleDragEnd}
            onMouseEnter={() => setHoveredFile(file.id)}
            onMouseLeave={() => setHoveredFile(null)}
            className={`
              group bg-card rounded-2xl border border-border/50
              transition-all duration-200
              ${isDemo ? 'cursor-default' : 'cursor-grab active:cursor-grabbing'}
              ${isDragging ? 'opacity-30 scale-95' : 'opacity-100'}
              ${isHovered ? 'shadow-xl border-border/80 -translate-y-1' : 'shadow-sm hover:shadow-lg'}
            `}
          >
            
            <div className="relative z-10 p-5">
              <div className="flex items-start justify-between mb-4">
                <div 
                  className="flex items-center gap-3 flex-1 min-w-0 cursor-pointer"
                  onClick={() => onPreviewFile(file)}
                >
                  <div className="w-11 h-11 bg-muted/50 rounded-2xl flex items-center justify-center flex-shrink-0 backdrop-blur-sm">
                    {(() => {
                      const { icon: Icon, className } = getFileIcon(file);
                      return <Icon className={className} />;
                    })()}
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    {renamingFileId === file.id ? (
                      <input
                        type="text"
                        value={newFileName}
                        onChange={(e) => onFileNameChange(e.target.value)}
                        onBlur={() => onConfirmRename(file.id)}
                        onKeyPress={(e) => e.key === 'Enter' && onConfirmRename(file.id)}
                        className="text-sm font-medium w-full bg-background px-2 py-1 rounded-lg border border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                        autoFocus
                      />
                    ) : (
                      <h4 className="text-sm font-medium truncate mb-1.5">
                        {file.name}
                      </h4>
                    )}
                    
                    <span className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-medium text-white ${getCategoryColor(file.category)}`}>
                      {file.category}
                    </span>
                  </div>
                </div>
                
                <div className={`flex items-center gap-1 transition-opacity duration-200 ${isHovered ? 'opacity-100' : 'opacity-0'}`}>
                  {!isDemo && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleEditCategory(file);
                      }}
                      className="p-2 rounded-full hover:bg-muted/80 transition-colors"
                      title="Edit category"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                  )}
                  
                  {file.storage_path && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDownloadFile(file.storage_path!, file.name);
                      }}
                      className="p-2 rounded-full hover:bg-muted/80 transition-colors"
                      title="Download"
                    >
                      <Download className="w-4 h-4" />
                    </button>
                  )}
                  
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteFile(file.id, file.name, file.storage_path);
                    }}
                    className="p-2 rounded-full hover:bg-red-50 dark:hover:bg-red-950/30 text-red-600 dark:text-red-400 transition-colors"
                    title="Delete"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
              
              {/* --- REPLACED: Image Thumbnail based on Category --- */}
              <div 
                className="aspect-video rounded-2xl mb-4 cursor-pointer overflow-hidden relative group/image"
                onClick={() => onPreviewFile(file)}
              >
                 <img 
                    src={getCategoryImage(file.category, 400, 225)} 
                    alt={file.category}
                    className="w-full h-full object-cover transition-transform duration-500 group-hover/image:scale-110"
                 />
                 {/* Color overlay matching the category */}
                 <div className={`absolute inset-0 opacity-20 mix-blend-overlay transition-opacity group-hover/image:opacity-10 ${getCategoryColor(file.category)}`} />
              </div>
              
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>{file.size}</span>
                <span>{file.modified}</span>
              </div>
            </div>
          </div>
        );
      })}
      
      <EditCategoryModal
        file={editingFile}
        categories={categories}
        isOpen={!!editingFile}
        onClose={() => setEditingFile(null)}
        onSave={handleSaveCategory}
        onRefreshCategories={onRefreshCategories}
      />
    </div>
  );
};