import React from 'react';
import { Search, Sun, Moon } from 'lucide-react';
import {
  AlertDialog,
  AlertDialogTrigger,
  AlertDialogContent,
  AlertDialogCancel,
  AlertDialogAction,
} from '../../landing_page/UI/ui-kit'
import { NotificationBell } from '../Notifications';
import type { UserProfile, UploadedFile } from '../types';

interface HeaderProps {
  userProfile: UserProfile | null;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  onRAGSearch?: (query: string) => void;
  darkMode: boolean;
  onToggleDarkMode: () => void;
  allFiles: UploadedFile[];
  onPreviewFile: (file: UploadedFile) => void;
  onNavigateToAllFiles: () => void;
  onNavigateToProfile: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  userProfile,
  searchQuery,
  onSearchChange,
  onRAGSearch,
  darkMode,
  onToggleDarkMode,
  onNavigateToProfile,
  allFiles,
  onPreviewFile,
  onNavigateToAllFiles
}) => {
  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(word => word.charAt(0))
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <header className="h-16 bg-card border-b border-border flex items-center justify-between px-4 lg:px-6">
      <div className="flex items-center gap-4 flex-1">
        <div className="relative flex-1 max-w-md flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
            <input
              type="text"
              placeholder="Search files or ask a question..."
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && searchQuery.trim() && onRAGSearch) {
                  onRAGSearch(searchQuery);
                }
              }}
              className="w-full pl-10 pr-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <button
            onClick={(e) => {
              e.preventDefault();
              console.log('🖱️ BUTTON ACTUALLY CLICKED!');
              console.log('onRAGSearch function:', onRAGSearch);
              console.log('searchQuery:', searchQuery);
              if (onRAGSearch) {
                console.log('Calling onRAGSearch...');
                onRAGSearch(searchQuery);
              } else {
                console.error('onRAGSearch is undefined!');
              }
            }}
            disabled={!searchQuery.trim()}
            type="button"
            className="px-4 py-2 bg-gradient-to-r from-purple-500 to-blue-500 text-white rounded-lg hover:from-purple-600 hover:to-blue-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 font-medium"
            title="AI Search"
          >
            <Search className="w-4 h-4" />
            <span className="hidden sm:inline">Search</span>
          </button>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={onToggleDarkMode}
          className="p-2 rounded-lg hover:bg-accent transition-colors"
          title={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {darkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
        </button>

        <NotificationBell
          allFiles={allFiles}
          onPreviewFile={onPreviewFile}
          onNavigateToAllFiles={onNavigateToAllFiles}
        />

        <div className="relative">
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <button className="flex items-center gap-2 p-2 rounded-lg hover:bg-accent transition-colors" type="button">
                {userProfile?.avatar_url ? (
                  <img src={userProfile.avatar_url} alt={userProfile.username} className="w-8 h-8 rounded-full object-cover" />
                ) : (
                  <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-semibold text-sm">
                    {userProfile ? getInitials(userProfile.username) : 'U'}
                  </div>
                )}
                <div className="hidden md:block text-left">
                  <p className="text-sm font-medium">{userProfile?.username || 'User'}</p>
                  <p className="text-xs text-muted-foreground">{userProfile?.email || ''}</p>
                </div>
              </button>
            </AlertDialogTrigger>
            <AlertDialogContent className="w-64 top-16 right-4 left-auto -translate-x-0 -translate-y-0">
              <div className="p-3 text-sm">
                <div>
                  <p className="text-xs text-muted-foreground">Username</p>
                  <p className="text-sm font-medium">{userProfile?.username || 'User'}</p>
                </div>
                <div className="mt-2">
                  <p className="text-xs text-muted-foreground">Full name</p>
                  <p className="text-sm">{userProfile?.full_name || ''}</p>
                </div>
                <div className="mt-2">
                  <p className="text-xs text-muted-foreground">Email</p>
                  <p className="text-sm">{userProfile?.email || ''}</p>
                </div>
                <div className="mt-4 flex gap-2">
                  <AlertDialogCancel asChild>
                    <button className="flex-1 px-3 py-2 border rounded">Close</button>
                  </AlertDialogCancel>
                  <AlertDialogAction asChild>
                    <a href="/profile" className="w-full">
                      <button className="w-full px-3 py-2 bg-primary text-white rounded">Go to Profile</button>
                    </a>
                  </AlertDialogAction>
                </div>
              </div>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>
    </header>
  );
};