import React from 'react';
import { Folder, Home, FileText, Search, Settings, LogOut, User } from 'lucide-react';
import type{ CategoryCount, FrequentFolder } from '../types';

interface SidebarProps {
  categoryCount: CategoryCount[];
  frequentFolders: FrequentFolder[];
  selectedCategory: string | null;
  onCategoryFilter: (category: string) => void;
  onNavigateToAllFiles: () => void;
  onNavigateToProfile: () => void;
  onSignOut: () => void;
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
  darkMode
}) => {
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
                  <button 
                    onClick={() => onCategoryFilter(cat.name)}
                    className={`w-full flex items-center gap-3 h-10 px-3 rounded-lg transition-all ${
                      selectedCategory === cat.name
                        ? "bg-sidebar-accent text-sidebar-accent-foreground"
                        : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                    }`}
                  >
                    <div className={`w-3 h-3 rounded-full ${cat.color}`} />
                    <span className="flex-1 text-left text-sm">{cat.name}</span>
                    <span className="text-xs px-2 py-0.5 bg-sidebar-accent/50 rounded-full">{cat.count}</span>
                  </button>
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