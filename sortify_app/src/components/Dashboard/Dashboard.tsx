import { useState, useRef } from 'react';
import { Upload, Folder, FileText, Sparkles, CloudUpload, BarChart3, X, Search, Clock, Filter } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import ChatbotPopup from '../landing_page/ChatbotPopup';
import FileDirectory from '../landing_page/FileDirectory';

// Hooks
import { useFileManagement } from './hooks/useFileManagement';
import { useFilePreview } from './hooks/useFilePreview';
import { useSearchAndFilter } from './hooks/useSearchAndFilter';
import { useDragAndDrop } from './hooks/useDragAndDrop';
import { useUserProfile } from './hooks/useUserProfile';

// Components
import { FilePreviewModal } from './components/FilePreviewModal';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { FileGrid } from './components/FileGrid';
import { NotificationContainer } from './components/NotificationToast';

// Types
import type { ViewMode } from './types';

const DEMO_FILES = [
  { id: 'demo-1', name: 'Sample Assignment.pdf', type: 'application/pdf', size: '2.4 MB', modified: '2 hours ago', category: 'Assignments', created_at: new Date().toISOString() },
  { id: 'demo-2', name: 'Lecture Notes.txt', type: 'text/plain', size: '1.2 MB', modified: '1 day ago', category: 'Lectures', created_at: new Date().toISOString() },
  { id: 'demo-3', name: 'Research Paper.pdf', type: 'application/pdf', size: '5.8 MB', modified: '3 days ago', category: 'Research', created_at: new Date().toISOString() },
  { id: 'demo-4', name: 'Math Homework.pdf', type: 'application/pdf', size: '890 KB', modified: '5 days ago', category: 'Math', created_at: new Date().toISOString() },
  { id: 'demo-5', name: 'Biology Lab Report.docx', type: 'application/msword', size: '3.1 MB', modified: '1 week ago', category: 'Science', created_at: new Date().toISOString() },
];

export default function Dashboard() {
  const navigate = useNavigate();
  const [darkMode, setDarkMode] = useState(false);
  const [notification, setNotification] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [renamingFileId, setRenamingFileId] = useState<string | null>(null);
  const [newFileName, setNewFileName] = useState('');
  const [activeFilter, setActiveFilter] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  // Custom hooks
  const {
    uploadedFiles,
    totalFilesCount,
    storageUsed,
    categoryCount,
    frequentFolders,
    notifications,
    removeNotification,
    handleFileUpload,
    deleteFile,
    renameFile
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
    filteredFiles,
    handleCategoryFilter
  } = useSearchAndFilter(uploadedFiles);

  const {
    isDragging,
    fileInputRef,
    handleDragOver,
    handleDragLeave,
    handleDrop,
    handleFileInputChange,
    triggerFileInput
  } = useDragAndDrop(handleFileUpload);

  const {
    userProfile,
    signOut
  } = useUserProfile();

  // Use demo files if no real files
  const displayFiles = filteredFiles.length > 0 ? filteredFiles : DEMO_FILES;



  const handleDeleteFile = async (fileId: string, fileName: string, storagePath?: string) => {
    try {
      await deleteFile(fileId, fileName, storagePath);
      setNotification('File deleted successfully!');
      setTimeout(() => setNotification(null), 3000);
    } catch (error) {
      setNotification('Delete failed. Please try again.');
      setTimeout(() => setNotification(null), 3000);
    }
  };

  const handleRenameFile = async (fileId: string) => {
    if (newFileName.trim()) {
      try {
        await renameFile(fileId, newFileName.trim());
        setRenamingFileId(null);
        setNewFileName('');
        setNotification('File renamed successfully!');
        setTimeout(() => setNotification(null), 3000);
      } catch (error) {
        setNotification('Rename failed. Please try again.');
        setTimeout(() => setNotification(null), 3000);
      }
    }
  };

  const handleNavigateToAllFiles = () => {
    navigate('/all-files');
  };

  const handleNavigateToProfile = () => {
    navigate('/profile');
  };

  const handleSignOut = async () => {
    try {
      await signOut();
      navigate('/login');
    } catch (error) {
      console.error('Sign out failed:', error);
    }
  };

  const formatStorageUsed = (bytes: number): string => {
    if (bytes === 0) return '0 MB';
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(1)} MB`;
  };

  return (
    <div className={darkMode ? 'dark' : ''}>
      <div className="min-h-screen bg-background">
        {/* Notifications */}
        <NotificationContainer 
          notifications={notifications}
          onRemove={removeNotification}
        />

        {/* File Preview Modal */}
        <FilePreviewModal
          previewState={previewState}
          onClose={closePreview}
          onDownload={downloadFile}
        />

        {/* Sidebar */}
        <Sidebar
          categoryCount={categoryCount}
          frequentFolders={frequentFolders}
          selectedCategory={selectedCategory}
          onCategoryFilter={handleCategoryFilter}
          onNavigateToAllFiles={handleNavigateToAllFiles}
          onNavigateToProfile={handleNavigateToProfile}
          onSignOut={handleSignOut}
          darkMode={darkMode}
        />

        <div className="flex-1 lg:ml-64">
          {/* Header */}
          <Header
            userProfile={userProfile}
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            darkMode={darkMode}
            onToggleDarkMode={() => setDarkMode(!darkMode)}
            onNavigateToProfile={handleNavigateToProfile}
          />

          {/* Main Content */}
          <main 
            className="flex-1 p-4 lg:p-6 space-y-4 lg:space-y-6"
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            {/* Drag and Drop Overlay */}
            {isDragging && (
              <div className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm flex items-center justify-center">
                <div className="bg-card border-2 border-dashed border-blue-500 rounded-xl p-12 text-center">
                  <CloudUpload className="w-16 h-16 text-blue-500 mx-auto mb-4" />
                  <h3 className="text-xl font-semibold mb-2">Drop files here</h3>
                  <p className="text-muted-foreground">Release to upload your files</p>
                </div>
              </div>
            )}

            <div className="space-y-4">
              <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                <div>
                  <h1 className="text-2xl lg:text-4xl font-bold tracking-tight bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">Welcome back, {userProfile?.username || 'User'}</h1>
                  <p className="text-muted-foreground text-sm lg:text-base mt-1">Your files are organized and ready to search</p>
                </div>
                <label className="w-full lg:w-auto px-6 lg:px-8 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl font-semibold hover:shadow-xl disabled:opacity-50 flex items-center justify-center gap-2 transition-all shadow-lg cursor-pointer">
                  <input ref={fileInputRef} type="file" onChange={handleFileInputChange} className="hidden" accept="*/*" multiple disabled={isUploading} />
                  {isUploading ? (
                    <>
                      <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent" />
                      Uploading...
                    </>
                  ) : (
                    <>
                      <Upload className="h-5 w-5" />
                      Upload Files
                    </>
                  )}
                </label>
              </div>

              {/* Search Bar with RAG */}
              <div className="relative">
                <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
                <input
                  placeholder="Ask a question about your documents..."
                  className="w-full pl-12 pr-32 h-14 rounded-xl bg-card border-2 border-border focus:border-primary outline-none transition-all shadow-sm"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      // Handle RAG search
                    }
                  }}
                />
                <button 
                  onClick={() => {
                    // Handle RAG search
                  }}
                  disabled={!searchQuery.trim()}
                  className="absolute right-2 top-1/2 -translate-y-1/2 px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg flex items-center gap-2 hover:shadow-lg transition-all font-medium disabled:opacity-50"
                >
                  <Sparkles className="h-4 w-4" />
                  AI Search
                </button>
              </div>

              <div className="flex items-center gap-2 flex-wrap">
                <button className="px-4 py-2 rounded-lg border border-border hover:bg-accent flex items-center gap-2 transition-colors">
                  <Filter className="h-4 w-4" />
                  Filters
                </button>
                {["Recent", "PDF", "Assignments", "This Week"].map((tag) => (
                  <span 
                    key={tag} 
                    onClick={() => setActiveFilter(activeFilter === tag ? null : tag)}
                    className={`px-3 py-1.5 rounded-lg text-sm cursor-pointer transition-colors ${
                      activeFilter === tag 
                        ? 'bg-primary text-primary-foreground' 
                        : 'bg-secondary/50 hover:bg-secondary/80 text-muted-foreground backdrop-blur-sm'
                    }`}
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 lg:gap-6">
              {/* Quick Access */}
              <div className="space-y-4 lg:space-y-6">
                {/* Frequent Folders */}
                <div className="bg-card rounded-xl border border-border p-4">
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <Folder className="w-5 h-5" />
                    Frequent Folders
                  </h3>
                  <div className="space-y-2">
                    {frequentFolders.length > 0 ? frequentFolders.map((folder) => (
                      <button
                        key={folder.name}
                        onClick={() => handleCategoryFilter(folder.name)}
                        className="w-full flex items-center gap-3 p-2 rounded-lg hover:bg-accent transition-colors"
                      >
                        <div className={`w-3 h-3 rounded-full ${folder.color}`} />
                        <span className="text-sm">{folder.name}</span>
                        <span className="text-xs text-muted-foreground ml-auto">{folder.count}</span>
                      </button>
                    )) : (
                      <div className="text-sm text-muted-foreground">No folders yet</div>
                    )}
                  </div>
                </div>

                {/* Quick Actions */}
                <div className="bg-card rounded-xl border border-border p-4">
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <Sparkles className="w-5 h-5" />
                    Quick Actions
                  </h3>
                  <div className="space-y-2">
                    <button
                      onClick={triggerFileInput}
                      className="w-full flex items-center gap-3 p-2 rounded-lg hover:bg-accent transition-colors"
                    >
                      <Upload className="w-4 h-4" />
                      <span className="text-sm">Upload Files</span>
                    </button>
                    <button
                      onClick={handleNavigateToAllFiles}
                      className="w-full flex items-center gap-3 p-2 rounded-lg hover:bg-accent transition-colors"
                    >
                      <FileText className="w-4 h-4" />
                      <span className="text-sm">View All Files</span>
                    </button>
                  </div>
                </div>

                {/* Student Profile */}
                <div className="bg-card rounded-xl border border-border p-4">
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <BarChart3 className="w-5 h-5" />
                    Analytics
                  </h3>
                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">Files Uploaded</span>
                      <span className="text-sm font-medium">{totalFilesCount}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">Storage Used</span>
                      <span className="text-sm font-medium">{formatStorageUsed(storageUsed)}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">Categories</span>
                      <span className="text-sm font-medium">{categoryCount.length}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* File Display */}
              <div className="lg:col-span-2">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-2xl font-bold">Your Files</h2>
                  <div className="flex items-center gap-2">
                    <button 
                      onClick={() => setViewMode('directory')}
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                        viewMode === 'directory' 
                          ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg' 
                          : 'bg-secondary hover:bg-secondary/80 text-muted-foreground'
                      }`}
                    >
                      <Folder className="w-4 h-4" />
                      Directory
                    </button>
                    <button 
                      onClick={() => setViewMode('grid')}
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                        viewMode === 'grid' 
                          ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg' 
                          : 'bg-secondary hover:bg-secondary/80 text-muted-foreground'
                      }`}
                    >
                      <FileText className="w-4 h-4" />
                      Grid
                    </button>
                  </div>
                </div>
                {displayFiles.length === 0 ? (
                  <div className="bg-card rounded-xl border border-border p-12 text-center">
                    <FileText className="w-16 h-16 text-muted-foreground mx-auto mb-4 opacity-50" />
                    <h3 className="text-lg font-semibold text-foreground mb-2">No files to display</h3>
                    <p className="text-sm text-muted-foreground mb-6">Upload your first file to get started with Sortify</p>
                    <button 
                      onClick={triggerFileInput}
                      className="px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg font-medium hover:shadow-lg transition-all"
                    >
                      Upload Files
                    </button>
                  </div>
                ) : viewMode === 'directory' ? (
                  <FileDirectory
                    files={displayFiles}
                    onPreviewFile={handlePreviewFile}
                    onDownloadFile={downloadFile}
                    onDeleteFile={handleDeleteFile}
                    onRenameFile={(fileId) => {
                      setRenamingFileId(fileId);
                      const file = displayFiles.find(f => f.id === fileId);
                      if (file) setNewFileName(file.name);
                    }}
                    renamingFileId={renamingFileId}
                    newFileName={newFileName}
                    setNewFileName={setNewFileName}
                  />
                ) : (
                  <FileGrid
                    files={displayFiles}
                    viewMode={viewMode}
                    renamingFileId={renamingFileId}
                    newFileName={newFileName}
                    onPreviewFile={handlePreviewFile}
                    onDownloadFile={downloadFile}
                    onDeleteFile={handleDeleteFile}
                    onRenameFile={(fileId) => {
                      setRenamingFileId(fileId);
                      const file = displayFiles.find(f => f.id === fileId);
                      if (file) setNewFileName(file.name);
                    }}
                    onFileNameChange={setNewFileName}
                    onConfirmRename={handleRenameFile}
                  />
                )}
              </div>

              {/* Recent Files Sidebar */}
              <div className="space-y-4 lg:space-y-6">
                {/* Recently Uploaded */}
                <div className="bg-card rounded-xl border border-border p-4">
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <Clock className="w-5 h-5" />
                    Recently Uploaded
                  </h3>
                  <div className="space-y-2">
                    {displayFiles.slice(0, 3).map((file) => (
                      <div key={file.id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-accent transition-colors cursor-pointer" onClick={() => handlePreviewFile(file)}>
                        <div className="w-8 h-8 bg-muted rounded-lg flex items-center justify-center">
                          <FileText className="w-4 h-4" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate">{file.name}</p>
                          <p className="text-xs text-muted-foreground">{file.modified}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Storage Used */}
                <div className="bg-card rounded-xl border border-border p-4">
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <CloudUpload className="w-5 h-5" />
                    Storage Used
                  </h3>
                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">Used</span>
                      <span className="text-sm font-medium">{formatStorageUsed(storageUsed)}</span>
                    </div>
                    <div className="w-full bg-muted rounded-full h-2">
                      <div 
                        className="bg-gradient-to-r from-blue-500 to-indigo-500 h-2 rounded-full transition-all"
                        style={{ width: `${Math.min((storageUsed / (100 * 1024 * 1024)) * 100, 100)}%` }}
                      ></div>
                    </div>
                    <p className="text-xs text-muted-foreground">100 MB limit</p>
                  </div>
                </div>
              </div>
            </div>

            {/* ChatbotPopup */}
            <ChatbotPopup />
          </main>
        </div>

        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          onChange={handleFileInputChange}
          className="hidden"
          accept=".pdf,.doc,.docx,.txt,.md,.jpg,.jpeg,.png,.gif,.mp4,.webm,.ogg,.mov,.avi"
        />
      </div>
    </div>
  );
}
