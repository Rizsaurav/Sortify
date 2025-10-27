import { useState } from 'react';
import { ArrowLeft, Search, Filter, Grid, List, Download, Trash2, Eye } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

// Hooks
import { useFileManagement } from './hooks/useFileManagement';
import { useFilePreview } from './hooks/useFilePreview';
import { useSearchAndFilter } from './hooks/useSearchAndFilter';
import { useUserProfile } from './hooks/useUserProfile';

// Components
import { FilePreviewModal } from './components/FilePreviewModal';
import { Header } from './components/Header';

// Utils
import { getFileIcon, getCategoryColor } from './utils/fileUtils';

// Types
import type { ViewMode } from './types';

export default function AllFiles() {
  const navigate = useNavigate();
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [selectedFiles, setSelectedFiles] = useState<string[]>([]);
  const [showFilters, setShowFilters] = useState(false);

  // Custom hooks
  const {
    allFiles,
    isLoading,
    categoryCount,
    deleteFile
  } = useFileManagement();

  const {
    previewState,
    handlePreviewFile,
    closePreview,
    downloadFile
  } = useFilePreview();

  const {
    searchQuery,
    setSearchQuery,
    selectedCategory,
    setSelectedCategory,
    activeFilter,
    setActiveFilter,
    filteredFiles,
    clearFilters
  } = useSearchAndFilter(allFiles);

  const {
    userProfile
  } = useUserProfile();

  const handleDeleteFile = async (fileId: string, fileName: string, storagePath?: string) => {
    try {
      await deleteFile(fileId, fileName, storagePath);
    } catch (error) {
      console.error('Delete failed:', error);
    }
  };

  // const handleRenameFile = async (fileId: string, newName: string) => {
  //   try {
  //     await renameFile(fileId, newName);
  //   } catch (error) {
  //     console.error('Rename failed:', error);
  //   }
  // };

  const handleSelectFile = (fileId: string) => {
    setSelectedFiles(prev => 
      prev.includes(fileId) 
        ? prev.filter(id => id !== fileId)
        : [...prev, fileId]
    );
  };

  const handleSelectAll = () => {
    if (selectedFiles.length === filteredFiles.length) {
      setSelectedFiles([]);
    } else {
      setSelectedFiles(filteredFiles.map(file => file.id));
    }
  };

  // const formatStorageUsed = (bytes: number): string => {
  //   if (bytes === 0) return '0 MB';
  //   const mb = bytes / (1024 * 1024);
  //   return `${mb.toFixed(1)} MB`;
  // };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading files...</p>
        </div>
      </div>
    );
  }

  return (
    <>
      {/* File Preview Modal */}
      <FilePreviewModal
        previewState={previewState}
        onClose={closePreview}
        onDownload={downloadFile}
      />

      <div className="min-h-screen bg-background">
        {/* Header */}
        <Header
          userProfile={userProfile}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          darkMode={false}
          onToggleDarkMode={() => {}}
          onNavigateToProfile={() => navigate('/profile')}
        />

        {/* Main Content */}
        <main className="flex-1 p-4 lg:p-6">
          {/* Navigation */}
          <div className="flex items-center gap-4 mb-6">
            <button
              onClick={() => navigate('/dashboard')}
              className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Dashboard
            </button>
            <div className="h-6 w-px bg-border"></div>
            <h1 className="text-2xl font-bold">All Files</h1>
            <span className="text-sm text-muted-foreground">({filteredFiles.length} files)</span>
          </div>

          {/* Controls */}
          <div className="flex flex-col lg:flex-row gap-4 mb-6">
            {/* Search */}
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
                <input
                  type="text"
                  placeholder="Search all files..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            </div>

            {/* Filters and View Toggle */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowFilters(!showFilters)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                  showFilters ? 'bg-blue-600 text-white' : 'bg-secondary hover:bg-secondary/80 text-muted-foreground'
                }`}
              >
                <Filter className="w-4 h-4" />
                Filters
              </button>

              <div className="flex items-center border border-border rounded-lg">
                <button
                  onClick={() => setViewMode('grid')}
                  className={`p-2 rounded-l-lg transition-colors ${
                    viewMode === 'grid' ? 'bg-blue-600 text-white' : 'bg-background hover:bg-accent'
                  }`}
                >
                  <Grid className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setViewMode('directory')}
                  className={`p-2 rounded-r-lg transition-colors ${
                    viewMode === 'directory' ? 'bg-blue-600 text-white' : 'bg-background hover:bg-accent'
                  }`}
                >
                  <List className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>

          {/* Filters Panel */}
          {showFilters && (
            <div className="bg-card border border-border rounded-xl p-4 mb-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Category Filter */}
                <div>
                  <label className="text-sm font-medium mb-2 block">Category</label>
                  <select
                    value={selectedCategory || ''}
                    onChange={(e) => setSelectedCategory(e.target.value || null)}
                    className="w-full p-2 border border-border rounded-lg bg-background"
                  >
                    <option value="">All Categories</option>
                    {categoryCount.map(cat => (
                      <option key={cat.name} value={cat.name}>
                        {cat.name} ({cat.count})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Sort Filter */}
                <div>
                  <label className="text-sm font-medium mb-2 block">Sort By</label>
                  <select
                    value={activeFilter || ''}
                    onChange={(e) => setActiveFilter(e.target.value || null)}
                    className="w-full p-2 border border-border rounded-lg bg-background"
                  >
                    <option value="">Default</option>
                    <option value="recent">Most Recent</option>
                    <option value="oldest">Oldest First</option>
                    <option value="name-asc">Name A-Z</option>
                    <option value="name-desc">Name Z-A</option>
                    <option value="largest">Largest First</option>
                    <option value="smallest">Smallest First</option>
                  </select>
                </div>

                {/* Clear Filters */}
                <div className="flex items-end">
                  <button
                    onClick={clearFilters}
                    className="w-full px-4 py-2 bg-secondary hover:bg-secondary/80 text-muted-foreground rounded-lg transition-colors"
                  >
                    Clear Filters
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Bulk Actions */}
          {selectedFiles.length > 0 && (
            <div className="bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-6">
              <div className="flex items-center justify-between">
                <span className="text-sm text-blue-700 dark:text-blue-300">
                  {selectedFiles.length} file{selectedFiles.length !== 1 ? 's' : ''} selected
                </span>
                <div className="flex items-center gap-2">
                  <button className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors">
                    Download Selected
                  </button>
                  <button className="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700 transition-colors">
                    Delete Selected
                  </button>
                  <button
                    onClick={() => setSelectedFiles([])}
                    className="px-3 py-1 text-sm bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors"
                  >
                    Clear Selection
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Files Grid/List */}
          {filteredFiles.length === 0 ? (
            <div className="bg-card rounded-xl border border-border p-12 text-center">
              <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto mb-4">
                <Search className="w-8 h-8 text-muted-foreground" />
              </div>
              <h3 className="text-lg font-semibold text-foreground mb-2">No files found</h3>
              <p className="text-sm text-muted-foreground mb-6">
                {searchQuery || selectedCategory ? 'Try adjusting your search or filters' : 'Upload your first file to get started'}
              </p>
              {!searchQuery && !selectedCategory && (
                <button
                  onClick={() => navigate('/dashboard')}
                  className="px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg font-medium hover:shadow-lg transition-all"
                >
                  Go to Dashboard
                </button>
              )}
            </div>
          ) : viewMode === 'grid' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {filteredFiles.map((file) => (
                <div
                  key={file.id}
                  className={`group bg-card rounded-xl border border-border hover:shadow-xl transition-all cursor-pointer overflow-hidden ${
                    selectedFiles.includes(file.id) ? 'ring-2 ring-blue-500' : ''
                  }`}
                  onClick={() => handleSelectFile(file.id)}
                >
                  <div className="p-4">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-3 flex-1 min-w-0" onClick={(e) => { e.stopPropagation(); handlePreviewFile(file); }}>
                        <div className="w-10 h-10 bg-muted rounded-lg flex items-center justify-center">
                          {(() => {
                            const { icon: Icon, className } = getFileIcon(file);
                            return <Icon className={className} />;
                          })()}
                        </div>
                        <div className="flex-1 min-w-0">
                          <h4 className="text-sm font-medium truncate">{file.name}</h4>
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
                            handlePreviewFile(file);
                          }}
                          className="p-1.5 rounded-lg hover:bg-muted"
                          title="Preview"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        {file.storage_path && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              downloadFile(file.storage_path!, file.name);
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
                            handleDeleteFile(file.id, file.name, file.storage_path);
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
          ) : (
            <div className="bg-card rounded-xl border border-border overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-muted/50">
                    <tr>
                      <th className="p-4 text-left">
                        <input
                          type="checkbox"
                          checked={selectedFiles.length === filteredFiles.length && filteredFiles.length > 0}
                          onChange={handleSelectAll}
                          className="rounded border-border"
                        />
                      </th>
                      <th className="p-4 text-left text-sm font-medium text-muted-foreground">Name</th>
                      <th className="p-4 text-left text-sm font-medium text-muted-foreground">Category</th>
                      <th className="p-4 text-left text-sm font-medium text-muted-foreground">Size</th>
                      <th className="p-4 text-left text-sm font-medium text-muted-foreground">Modified</th>
                      <th className="p-4 text-left text-sm font-medium text-muted-foreground">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredFiles.map((file) => (
                      <tr key={file.id} className="border-t border-border hover:bg-muted/50">
                        <td className="p-4">
                          <input
                            type="checkbox"
                            checked={selectedFiles.includes(file.id)}
                            onChange={() => handleSelectFile(file.id)}
                            className="rounded border-border"
                          />
                        </td>
                        <td className="p-4">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 bg-muted rounded-lg flex items-center justify-center">
                              {(() => {
                                const { icon: Icon, className } = getFileIcon(file);
                                return <Icon className={className} />;
                              })()}
                            </div>
                            <div>
                              <p className="font-medium">{file.name}</p>
                            </div>
                          </div>
                        </td>
                        <td className="p-4">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium text-white ${getCategoryColor(file.category)}`}>
                            {file.category}
                          </span>
                        </td>
                        <td className="p-4 text-sm text-muted-foreground">{file.size}</td>
                        <td className="p-4 text-sm text-muted-foreground">{file.modified}</td>
                        <td className="p-4">
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => handlePreviewFile(file)}
                              className="p-1.5 rounded-lg hover:bg-muted"
                              title="Preview"
                            >
                              <Eye className="w-4 h-4" />
                            </button>
                            {file.storage_path && (
                              <button
                                onClick={() => downloadFile(file.storage_path!, file.name)}
                                className="p-1.5 rounded-lg hover:bg-muted"
                                title="Download"
                              >
                                <Download className="w-4 h-4" />
                              </button>
                            )}
                            <button
                              onClick={() => handleDeleteFile(file.id, file.name, file.storage_path)}
                              className="p-1.5 rounded-lg hover:bg-red-500/10 text-red-500"
                              title="Delete"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Pagination or Load More */}
          {filteredFiles.length > 20 && (
            <div className="mt-6 text-center">
              <button className="px-6 py-2 bg-secondary hover:bg-secondary/80 text-muted-foreground rounded-lg transition-colors">
                Load More Files
              </button>
            </div>
          )}
        </main>
      </div>
    </>
  );
}
