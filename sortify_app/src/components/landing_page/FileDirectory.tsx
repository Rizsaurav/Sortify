import React, { useState } from 'react';
import { 
  Folder, 
  FileText, 
  ChevronRight, 
  ChevronDown, 
  Download, 
  Trash2, 
  Edit2,
  Film,
  Image as ImageIcon
} from 'lucide-react';

interface UploadedFile {
  id: string;
  name: string;
  type: string;
  size: string;
  modified: string;
  category: string;
  storage_path?: string;
  view_count?: number;
  metadata?: any;
  content?: string;
  created_at?: string;
}

interface FileDirectoryProps {
  files: UploadedFile[];
  onPreviewFile: (file: UploadedFile) => void;
  onDownloadFile: (storagePath: string, fileName: string) => void;
  onDeleteFile: (fileId: string, fileName: string, storagePath?: string) => void;
  onRenameFile: (fileId: string) => void;
  renamingFileId: string | null;
  newFileName: string;
  setNewFileName: (name: string) => void;
}

// --- Helper: Generate Image based on Category ---
// Working properly
const getCategoryImage = (category: string, width: number, height: number): string => {
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
  return `https://loremflickr.com/${width}/${height}/${encodeURIComponent(keywords)}?lock=${category.length}`;
};

const getCategoryColor = (category: string): string => {
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
    'Assignments': 'bg-blue-500',
    'Lecture Notes': 'bg-green-500',
    'Lab Reports': 'bg-purple-500',
    'Research Papers': 'bg-red-500',
    'Study Materials': 'bg-yellow-500',
    'Computer Science': 'bg-indigo-500',
    'Biology': 'bg-emerald-500',
    'Chemistry': 'bg-cyan-500',
    'Physics': 'bg-pink-500',
    'Engineering': 'bg-gray-500',
    'Business': 'bg-amber-500',
    'General': 'bg-slate-500'
  };
  return colors[category] || 'bg-gradient-to-r from-gray-500 to-gray-600';
};

export default function FileDirectory({
  files,
  onPreviewFile,
  onDownloadFile,
  onDeleteFile,
  onRenameFile,
  renamingFileId,
  newFileName,
  setNewFileName
}: FileDirectoryProps) {
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());

  // Group files by category
  const filesByCategory = files.reduce((acc, file) => {
    const category = file.category || 'General';
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(file);
    return acc;
  }, {} as Record<string, UploadedFile[]>);

  const toggleCategory = (category: string) => {
    const newExpanded = new Set(expandedCategories);
    if (newExpanded.has(category)) {
      newExpanded.delete(category);
    } else {
      newExpanded.add(category);
    }
    setExpandedCategories(newExpanded);
  };

  const getFileIcon = (file: UploadedFile) => {
    const type = file.type.toLowerCase();
    const name = file.name.toLowerCase();
    
    if (type.includes('mp4') || type.includes('video') || name.match(/\.(mp4|webm|ogg|mov|avi)$/)) {
      return <Film className="w-4 h-4 text-muted-foreground" />;
    }
    if (type.includes('image') || name.match(/\.(jpg|jpeg|png|gif|bmp|webp|svg)$/)) {
      return <ImageIcon className="w-4 h-4 text-muted-foreground" />;
    }
    if (type.includes('pdf') || name.endsWith('.pdf')) {
      return <FileText className="w-4 h-4 text-red-500" />;
    }
    if (type.includes('word') || type.includes('document') || name.match(/\.(doc|docx)$/)) {
      return <FileText className="w-4 h-4 text-blue-500" />;
    }
    if (type.includes('excel') || type.includes('spreadsheet') || name.match(/\.(xls|xlsx)$/)) {
      return <FileText className="w-4 h-4 text-green-500" />;
    }
    if (type.includes('powerpoint') || type.includes('presentation') || name.match(/\.(ppt|pptx)$/)) {
      return <FileText className="w-4 h-4 text-orange-500" />;
    }
    return <FileText className="w-4 h-4 text-muted-foreground" />;
  };

  return (
    <div className="space-y-4">
      {Object.entries(filesByCategory)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([category, categoryFiles]) => (
          <div key={category} className="bg-card rounded-xl border border-border shadow-lg overflow-hidden">
            {/* Category Header */}
            <button
              onClick={() => toggleCategory(category)}
              className="w-full flex items-center justify-between p-4 lg:p-6 hover:bg-muted/50 transition-colors rounded-xl group relative overflow-hidden"
            >
              <div className="flex items-center gap-3 z-10">
                {/* Category Image */}
                <div className="w-12 h-12 bg-muted rounded-lg flex items-center justify-center overflow-hidden border border-border shadow-sm">
                   <img 
                      src={getCategoryImage(category, 64, 64)} 
                      alt={category}
                      className="w-full h-full object-cover"
                   />
                </div>
                <div className="flex-1 text-left">
                  <div className="font-medium text-lg">{category}</div>
                  <div className="text-xs text-muted-foreground">
                    {categoryFiles.length} file{categoryFiles.length !== 1 ? 's' : ''}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2 z-10">
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium text-white/90 bg-opacity-80 ${getCategoryColor(category)}`}>
                  {categoryFiles.length}
                </span>
                {expandedCategories.has(category) ? (
                  <ChevronDown className="w-4 h-4 text-muted-foreground" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-muted-foreground" />
                )}
              </div>
            </button>

            {/* Category Files */}
            {expandedCategories.has(category) && (
              <div className="border-t border-border">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 lg:p-6">
                  {categoryFiles
                    .sort((a, b) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime())
                    .map((file) => (
                      <div
                        key={file.id}
                        className="group bg-card rounded-xl border border-border hover:shadow-xl transition-all cursor-pointer overflow-hidden"
                      >
                        <div className="p-4">
                          <div className="flex items-start justify-between mb-3">
                            <div className="flex items-center gap-3 flex-1 min-w-0" onClick={() => onPreviewFile(file)}>
                              <div className="w-10 h-10 bg-muted rounded-lg flex items-center justify-center">
                                {getFileIcon(file)}
                              </div>
                              <div className="flex-1 min-w-0">
                                {renamingFileId === file.id ? (
                                  <input
                                    type="text"
                                    value={newFileName}
                                    onChange={(e) => setNewFileName(e.target.value)}
                                    onBlur={() => onRenameFile(file.id)}
                                    onKeyPress={(e) => e.key === 'Enter' && onRenameFile(file.id)}
                                    className="text-sm font-medium w-full bg-background px-2 py-1 rounded"
                                    autoFocus
                                  />
                                ) : (
                                  <h4 className="text-sm font-medium truncate">{file.name}</h4>
                                )}
                                <div className="flex items-center gap-2 mt-1">
                                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium text-white/90 bg-opacity-80 ${getCategoryColor(category)}`}>
                                    {category}
                                  </span>
                                </div>
                              </div>
                            </div>
                            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-all">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onRenameFile(file.id);
                                  setNewFileName(file.name);
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
                        {/* Thumbnail Image */}
                        <div className="aspect-video rounded-lg mb-3 mx-4 overflow-hidden relative group/image">
                           <img 
                              src={getCategoryImage(category, 400, 225)} 
                              alt={category}
                              className="w-full h-full object-cover transition-transform duration-500 group-hover/image:scale-110"
                           />
                           <div className={`absolute inset-0 opacity-20 mix-blend-overlay ${getCategoryColor(category)}`} />
                        </div>

                        <div className="px-4 pb-4 flex items-center justify-between text-xs text-muted-foreground">
                          <span>{file.size}</span>
                          <span>{file.modified}</span>
                        </div>
                      </div>
                    ))}
                </div>
              </div>
            )}
          </div>
        ))}
    </div>
  );
}