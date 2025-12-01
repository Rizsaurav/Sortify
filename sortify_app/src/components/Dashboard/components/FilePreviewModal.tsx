import React from 'react';
import { X, Download, FileText, AlertCircle } from 'lucide-react';
import type { FilePreviewState } from '../types';

interface FilePreviewModalProps {
  previewState: FilePreviewState;
  onClose: () => void;
  onDownload: (storagePath: string, fileName: string) => void;
}

export const FilePreviewModal: React.FC<FilePreviewModalProps> = ({
  previewState,
  onClose,
  onDownload
}) => {
  const { file, url, content, type } = previewState;

  if (!file) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="relative bg-card rounded-xl shadow-2xl w-[90vw] h-[90vh] max-w-5xl flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h3 className="text-lg font-semibold truncate">{file.name}</h3>
          <button onClick={onClose} className="hover:bg-accent p-2 rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="flex-1 overflow-auto bg-muted/30">
          {type === 'pdf' && url ? (
            <iframe
              src={`${url}#toolbar=0`}
              className="w-full h-full min-h-[600px]"
              title={file.name}
            />
          ) : type === 'image' && url ? (
            <div className="flex items-center justify-center p-8 min-h-[600px]">
              <img 
                src={url} 
                alt={file.name}
                className="max-w-full max-h-full object-contain rounded-lg shadow-lg"
              />
            </div>
          ) : type === 'video' && url ? (
            <div className="flex items-center justify-center p-8 min-h-[600px]">
              <video 
                controls
                className="max-w-full max-h-full rounded-lg shadow-lg"
                src={url}
              >
                Your browser does not support video playback.
              </video>
            </div>
          ) : type === 'office' && url ? (
            <div className="p-8 max-w-4xl mx-auto">
              <div className="bg-background rounded-lg p-8 shadow-sm text-center">
                <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center mx-auto mb-4">
                  <FileText className="w-8 h-8 text-blue-600 dark:text-blue-400" />
                </div>
                <h3 className="text-xl font-semibold mb-2">{file.name}</h3>
                <p className="text-muted-foreground mb-6">
                  This is an Office document (Word, Excel, or PowerPoint). 
                  Click the download button below to open it with your preferred application.
                </p>
                <div className="flex gap-4 justify-center">
                  <button
                    onClick={() => file.storage_path && onDownload(file.storage_path, file.name)}
                    className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
                  >
                    <Download className="w-4 h-4" />
                    Download File
                  </button>
                  <button
                    onClick={() => window.open(url, '_blank')}
                    className="px-6 py-3 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors flex items-center gap-2"
                  >
                    <FileText className="w-4 h-4" />
                    Open in Browser
                  </button>
                </div>
                {content && (
                  <div className="mt-6 p-4 bg-muted rounded-lg text-left">
                    <pre className="whitespace-pre-wrap text-sm text-muted-foreground">{content}</pre>
                  </div>
                )}
              </div>
            </div>
          ) : type === 'text' && content ? (
            <div className="p-8 max-w-4xl mx-auto">
              <div className="bg-background rounded-lg p-6 shadow-sm">
                <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-foreground overflow-x-auto">{content}</pre>
              </div>
            </div>
          ) : !url && type !== 'text' ? (
            <div className="p-6 flex items-center justify-center min-h-[400px]">
              <div className="text-center max-w-md">
                <AlertCircle className="w-16 h-16 text-amber-500 mx-auto mb-4" />
                <h3 className="text-lg font-semibold mb-2">File Not Available</h3>
                <p className="text-muted-foreground mb-4">
                  This file is listed in the database but could not be found in storage.
                  It may have been deleted or moved.
                </p>
                <p className="text-sm text-muted-foreground">
                  File: <span className="font-mono">{file.name}</span>
                </p>
              </div>
            </div>
          ) : (
            <div className="p-6 flex items-center justify-center min-h-[400px]">
              <div className="text-center">
                <FileText className="w-16 h-16 text-muted-foreground mx-auto mb-4 opacity-50" />
                <p className="text-muted-foreground">Loading preview...</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};