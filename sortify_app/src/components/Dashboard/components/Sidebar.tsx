import React, { useState } from 'react';
import { Folder, Home, FileText, LogOut, User, CheckCircle } from 'lucide-react';
import type{ CategoryCount, FrequentFolder } from '../types';

interface SidebarProps {
  categoryCount: CategoryCount[];
  frequentFolders: FrequentFolder[];
  selectedCategory: string | null;
  onCategoryFilter: (category: string) => void;
  onNavigateToAllFiles: () => void;
  onNavigateToProfile: () => void;
  onSignOut: () => void;
  onDrop?: (fileId: string, categoryId: number, categoryName: string) => void;
  darkMode: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  categoryCount,
  frequentFolders,
  selectedCategory,
  onCategoryFilter,
  onNavigateToAllFiles,
  onNavigateToProfile,
  onSignOut,
  onDrop
}) => {
  const [draggedOverCategory, setDraggedOverCategory] = useState<string | null>(null);

  const handleDragOver = (e: React.DragEvent, categoryName: string) => {
    e.preventDefault();
    e.stopPropagation();
    
    // Only accept our custom file cards, not external files
    const types = e.dataTransfer.types;
    if (types.includes('application/x-file-card')) {
      e.dataTransfer.dropEffect = 'move';
      setDraggedOverCategory(categoryName);
    }
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDraggedOverCategory(null);
  };

  const handleDrop = (e: React.DragEvent, categoryName: string) => {
    e.preventDefault();
    e.stopPropagation();
    
    // Get our custom data
    const data = e.dataTransfer.getData('application/x-file-card');
    if (data) {
      const { fileId } = JSON.parse(data);
      if (onDrop && fileId) {
        // For now, we'll use a placeholder category ID since CategoryCount doesn't have an id
        // In a real implementation, you'd need to map category names to IDs
        const categoryId = 1; // This should be replaced with actual category ID lookup
        onDrop(fileId, categoryId, categoryName);
      }
    }
    setDraggedOverCategory(null);
  };
  return (
    <aside className="w-64 h-screen bg-sidebar border-r border-sidebar-border fixed left-0 top-0 hidden lg:block shadow-xl">
      <div className="flex flex-col h-full">
        <div className="h-16 flex items-center px-6 border-b border-sidebar-border">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center shadow-lg">
              <Folder className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold text-sidebar-foreground">Sortify</span>
          </div>
        </div>

        <nav className="flex-1 px-4 py-6 space-y-6 overflow-y-auto">
          <div>
            <h3 className="text-xs font-semibold text-sidebar-foreground/60 uppercase tracking-wider mb-3 px-3">Navigation</h3>
            <ul className="space-y-1">
              <li>
                <button 
                  onClick={() => onCategoryFilter('')}
                  className="w-full flex items-center gap-3 h-10 px-3 rounded-lg transition-all text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                >
                  <Home className="w-4 h-4" />
                  <span className="text-sm">Dashboard</span>
                </button>
              </li>
              <li>
                <button 
                  onClick={onNavigateToAllFiles}
                  className="w-full flex items-center gap-3 h-10 px-3 rounded-lg transition-all text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                >
                  <FileText className="w-4 h-4" />
                  <span className="text-sm">All Files</span>
                </button>
              </li>
              <li>
                <button 
                  onClick={onNavigateToProfile}
                  className="w-full flex items-center gap-3 h-10 px-3 rounded-lg transition-all text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                >
                  <User className="w-4 h-4" />
                  <span className="text-sm">Profile</span>
                </button>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="text-xs font-semibold text-sidebar-foreground/60 uppercase tracking-wider mb-3 px-3">Frequent Folders</h3>
            <ul className="space-y-1">
              {frequentFolders.length > 0 ? frequentFolders.map((folder) => (
                <li key={folder.name}>
                  <button 
                    onClick={() => onCategoryFilter(folder.name)}
                    className={`w-full flex items-center gap-3 h-10 px-3 rounded-lg transition-all ${
                      selectedCategory === folder.name
                        ? "bg-sidebar-accent text-sidebar-accent-foreground"
                        : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                    }`}
                  >
                    <div className={`w-3 h-3 rounded-full ${folder.color}`} />
                    <span className="flex-1 text-left text-sm">{folder.name}</span>
                    <span className="text-xs px-2 py-0.5 bg-sidebar-accent/50 rounded-full">{folder.count}</span>
                  </button>
                </li>
              )) : (
                <li className="px-3 py-2 text-xs text-sidebar-foreground/60">
                  No folders yet
                </li>
              )}
            </ul>
          </div>

          <div>
            <h3 className="text-xs font-semibold text-sidebar-foreground/60 uppercase tracking-wider mb-3 px-3">Categories</h3>
            <ul className="space-y-1">
              {categoryCount.length > 0 ? categoryCount.map((cat) => (
                <li key={cat.name}>
                  <div
                    onDragOver={(e) => handleDragOver(e, cat.name)}
                    onDragLeave={handleDragLeave}
                    onDrop={(e) => handleDrop(e, cat.name)}
                    className={`
                      relative w-full flex items-center gap-3 h-10 px-3 rounded-lg transition-all duration-200
                      ${draggedOverCategory === cat.name 
                        ? 'bg-gradient-to-r from-blue-50 to-blue-100 border-2 border-blue-400 scale-105 shadow-lg' 
                        : selectedCategory === cat.name
                          ? "bg-sidebar-accent text-sidebar-accent-foreground"
                          : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                      }
                      ${onDrop ? "cursor-pointer" : ""}
                    `}
                    onClick={() => onCategoryFilter(cat.name)}
                  >
                    <div className={`w-3 h-3 rounded-full ${cat.color}`} />
                    <span className="flex-1 text-left text-sm">{cat.name}</span>
                    <span className="text-xs px-2 py-0.5 bg-sidebar-accent/50 rounded-full">{cat.count}</span>
                    
                    {/* Smooth Drop Indicator */}
                    {draggedOverCategory === cat.name && (
                      <div className="absolute inset-0 flex items-center justify-center bg-blue-500 bg-opacity-10 rounded-lg backdrop-blur-sm">
                        <span className="text-blue-600 font-semibold flex items-center gap-2 text-xs">
                          <CheckCircle className="w-4 h-4" />
                          Drop here
                        </span>
                      </div>
                    )}
                  </div>
                </li>
              )) : (
                <li className="px-3 py-2 text-xs text-sidebar-foreground/60">
                  No categories yet
                </li>
              )}
            </ul>
          </div>
        </nav>

        <div className="p-4 border-t border-sidebar-border">
          <button 
            onClick={onSignOut}
            className="w-full flex items-center gap-3 h-10 px-3 rounded-lg transition-all text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
          >
            <LogOut className="w-4 h-4" />
            <span className="text-sm">Sign Out</span>
          </button>
        </div>
      </div>
    </aside>
  );
};