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

  const handleDragStart = (e: React.DragEvent, file: UploadedFile) => {
    e.stopPropagation(); // Prevent parent handlers
    
    // Don't allow dragging demo files
    if (file.id.startsWith('demo-')) {
      e.preventDefault();
      return;
    }
    
    setDraggedFile(file);
    
    // Use custom data format to distinguish from file uploads
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
    // Check if it's a demo file
    if (fileId.startsWith('demo-')) {
      console.warn('Cannot change category for demo files');
      setEditingFile(null);
      return;
    }
    
    onCategoryChange(fileId, categoryId, categoryName);
    setEditingFile(null);
  };
  if (viewMode === 'directory') {
    // This would be handled by FileDirectory component
    return null;
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {files.slice(0, 6).map((file) => (
        <div 
          key={file.id} 
          draggable={!file.id.startsWith('demo-')}
          onDragStart={(e) => handleDragStart(e, file)}
          onDragEnd={handleDragEnd}
          className={`
            group bg-card rounded-xl border border-border hover:shadow-xl transition-all overflow-hidden
            ${file.id.startsWith('demo-') ? 'cursor-default' : 'cursor-grab active:cursor-grabbing'}
            ${draggedFile?.id === file.id ? 'opacity-30 scale-95' : 'opacity-100'}
            hover:border-blue-300
            transition-all duration-200
          `}
        >
          <div className="p-4">
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-3 flex-1 min-w-0" onClick={() => onPreviewFile(file)}>
                <div className="w-10 h-10 bg-muted rounded-lg flex items-center justify-center">
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
                      className="text-sm font-medium w-full bg-background px-2 py-1 rounded"
                      autoFocus
                    />
                  ) : (
                    <h4 className="text-sm font-medium truncate">{file.name}</h4>
                  )}
                  <div className="flex items-center gap-2 mt-1">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium text-white/90 bg-opacity-80 ${getCategoryColor(file.category)}`}>
                      {file.category}
                    </span>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-all">
                {!file.id.startsWith('demo-') && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleEditCategory(file);
                    }}
                    className="p-1.5 rounded-lg hover:bg-muted"
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
                    className="p-1.5 rounded-lg hover:bg-muted"
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
                  className="p-1.5 rounded-lg hover:bg-red-500/10 text-red-500"
                  title="Delete"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
          <div className="aspect-video bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-950 dark:to-indigo-950 mx-4 rounded-lg mb-3"></div>
          <div className="px-4 pb-4 flex items-center justify-between text-xs text-muted-foreground">
            <span>{file.size}</span>
            <span>{file.modified}</span>
          </div>
        </div>
      ))}
      
      {/* Edit Category Modal */}
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