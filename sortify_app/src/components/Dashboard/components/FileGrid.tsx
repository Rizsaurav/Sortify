import React from 'react';
import { FileText, Download, Trash2, Edit2 } from 'lucide-react';
import type { UploadedFile, ViewMode } from '../types';
import { getFileIcon, getCategoryColor } from '../utils/fileUtils';

interface FileGridProps {
  files: UploadedFile[];
  viewMode: ViewMode;
  renamingFileId: string | null;
  newFileName: string;
  onPreviewFile: (file: UploadedFile) => void;
  onDownloadFile: (storagePath: string, fileName: string) => void;
  onDeleteFile: (fileId: string, fileName: string, storagePath?: string) => void;
  onRenameFile: (fileId: string) => void;
  onFileNameChange: (name: string) => void;
  onConfirmRename: (fileId: string) => void;
}

export const FileGrid: React.FC<FileGridProps> = ({
  files,
  viewMode,
  renamingFileId,
  newFileName,
  onPreviewFile,
  onDownloadFile,
  onDeleteFile,
  onRenameFile,
  onFileNameChange,
  onConfirmRename
}) => {
  if (viewMode === 'directory') {
    // This would be handled by FileDirectory component
    return null;
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {files.slice(0, 6).map((file) => (
        <div key={file.id} className="group bg-card rounded-xl border border-border hover:shadow-xl transition-all cursor-pointer overflow-hidden">
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
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onRenameFile(file.id);
                  }}
                  className="p-1.5 rounded-lg hover:bg-muted"
                  title="Rename"
                >
                  <Edit2 className="w-4 h-4" />
                </button>
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
    </div>
  );
};