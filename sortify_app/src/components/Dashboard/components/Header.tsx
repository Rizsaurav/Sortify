import React from 'react';
import { Search, Bell, Sun, Moon } from 'lucide-react';
import type { UserProfile } from '../types';

interface HeaderProps {
  userProfile: UserProfile | null;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  darkMode: boolean;
  onToggleDarkMode: () => void;
  onNavigateToProfile: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  userProfile,
  searchQuery,
  onSearchChange,
  darkMode,
  onToggleDarkMode,
  onNavigateToProfile
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
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
          <input
            type="text"
            placeholder="Search files..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
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

        <button className="p-2 rounded-lg hover:bg-accent transition-colors relative">
          <Bell className="w-5 h-5" />
          <span className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full"></span>
        </button>

        <div className="relative">
          <button
            onClick={onNavigateToProfile}
            className="flex items-center gap-2 p-2 rounded-lg hover:bg-accent transition-colors"
          >
            {userProfile?.avatar_url ? (
              <img
                src={userProfile.avatar_url}
                alt={userProfile.username}
                className="w-8 h-8 rounded-full object-cover"
              />
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
        </div>
      </div>
    </header>
  );
};