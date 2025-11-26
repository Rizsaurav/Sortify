import { useState, useEffect } from 'react';
import { Upload, Folder, FileText, Sparkles, CloudUpload, BarChart3, Search, Clock, Filter } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import ChatbotPopup from '../landing_page/ChatbotPopup';
import FileDirectory from '../landing_page/FileDirectory';

import { useFileManagement } from './hooks/useFileManagement';
import { useFilePreview } from './hooks/useFilePreview';
import { useSearchAndFilter } from './hooks/useSearchAndFilter';
import { useDragAndDrop } from './hooks/useDragAndDrop';
import { useUserProfile } from './hooks/useUserProfile';
import { useCategoryManagement } from './hooks/useCategoryManagement';

import { FilePreviewModal } from './components/FilePreviewModal';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { FileGrid } from './components/FileGrid';
import { NotificationContainer } from './components/NotificationToast';

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
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [renamingFileId, setRenamingFileId] = useState<string | null>(null);
  const [newFileName, setNewFileName] = useState('');
  const [activeFilter, setActiveFilter] = useState<string | null>(null);
  
  const [isProcessing, setIsProcessing] = useState(false); 
  const [isInitialLoading, setIsInitialLoading] = useState(true); 

  const {
    uploadedFiles,
    totalFilesCount,
    storageUsed,
    categoryCount,
    frequentFolders,
    notifications,
    removeNotification,
    addNotification,
    fetchFiles,
    handleFileUpload,
    deleteFile,
    renameFile
  } = useFileManagement();

  // Fetches initial data on component mount with error handling.
  useEffect(() => {
    const initDashboard = async () => {
      try {
        await fetchFiles();
      } catch (error) {
        console.error("Dashboard initialization failed:", error);
        addNotification("Unable to retrieve files. Please refresh the page.", "error");
      } finally {
        setIsInitialLoading(false);
      }
    };

    initDashboard();
  }, []); 

  // Prevents default browser drag-and-drop interactions to enable custom drop zones.
  useEffect(() => {
    const preventDefault = (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
    };

    window.addEventListener('dragover', preventDefault);
    window.addEventListener('drop', preventDefault);

    return () => {
      window.removeEventListener('dragover', preventDefault);
      window.removeEventListener('drop', preventDefault);
    };
  }, []);

  const { previewState, handlePreviewFile, closePreview, downloadFile } = useFilePreview();
  const { searchQuery, setSearchQuery, selectedCategory, filteredFiles, handleCategoryFilter } = useSearchAndFilter(uploadedFiles);
  const { isDragging, fileInputRef, handleFileInputChange, triggerFileInput } = useDragAndDrop(handleFileUpload);
  const { userProfile, signOut } = useUserProfile();
  const { categories, changeFileCategory, fetchCategories } = useCategoryManagement(userProfile?.id || '');

  const displayFiles = uploadedFiles.length === 0 ? DEMO_FILES : filteredFiles;

  // Handles moving a file to a different category via the edit modal.
  const handleCategoryChange = async (fileId: string, categoryId: number, categoryName: string) => {
    if (isProcessing) return;
    
    if (fileId.startsWith('demo-')) {
      addNotification('Modification of demo files is not permitted.', 'info');
      return;
    }

    setIsProcessing(true);
    try {
      await changeFileCategory(fileId, categoryId, categoryName, async () => {
        await fetchFiles();
      });
      handleCategoryFilter(''); // Reset filter to ensure visibility of moved file.
      addNotification(`File successfully moved to ${categoryName}.`, 'success');
    } catch (error) {
      console.error('Category update operation failed:', error);
      addNotification('Failed to update file category. Please try again.', 'error');
    } finally {
      setIsProcessing(false);
    }
  };

  // Handles dropping a file onto a category sidebar item.
  const handleCategoryDrop = async (fileId: string, categoryId: number, categoryName: string) => {
    if (isProcessing) return;

    if (fileId.startsWith('demo-')) {
      addNotification('Modification of demo files is not permitted.', 'info');
      return;
    }

    setIsProcessing(true);
    try {
      await changeFileCategory(fileId, categoryId, categoryName, async () => {
        await fetchFiles();
      });
      handleCategoryFilter('');
      addNotification(`File successfully moved to ${categoryName}.`, 'success');
    } catch (error) {
      console.error('Category drop operation failed:', error);
      addNotification('Failed to move file. Please try again.', 'error');
    } finally {
      setIsProcessing(false);
    }
  };

  // Handles file deletion with error feedback.
  const handleDeleteFile = async (fileId: string, fileName: string, storagePath?: string) => {
    try {
      await deleteFile(fileId, fileName, storagePath);
      addNotification('File deleted successfully.', 'success');
    } catch (error) {
      console.error('Delete operation failed:', error);
      addNotification('Unable to delete file. Please check your permissions.', 'error');
    }
  };

  // Handles file renaming with error feedback.
  const handleRenameFile = async (fileId: string) => {
    if (!newFileName.trim()) return;

    try {
      await renameFile(fileId, newFileName.trim());
      setRenamingFileId(null);
      setNewFileName('');
      addNotification('File renamed successfully.', 'success');
    } catch (error) {
      console.error('Rename operation failed:', error);
      addNotification('Unable to rename file. Please try again later.', 'error');
    }
  };

  const handleNavigateToAllFiles = () => { navigate('/all-files'); };
  const handleNavigateToProfile = () => { navigate('/profile'); };

  const formatStorageUsed = (bytes: number): string => {
    if (bytes === 0) return '0 MB';
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(1)} MB`;
  };

  // CSS animations for the loading state.
  const globalStyles = `
    @keyframes sortifyHeartbeat {
      0% { transform: scale(1) translateY(9%); opacity: 0.9; }
      50% { transform: scale(1.05) translateY(9%); opacity: 1; }
      100% { transform: scale(1) translateY(9%); opacity: 0.9; }
    }

    @keyframes strokePulse {
       0% { transform: scale(1); }
       50% { transform: scale(1.03); }
       100% { transform: scale(1); }
    }
    
    @keyframes spin-linear {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }
    
    .animate-spin-linear {
      animation: spin-linear 2s linear infinite;
    }

    :root {
      --loading-stroke-gradient: conic-gradient(from 0deg, transparent 0%, transparent 15%, #00c6ff 30%, #0072ff 50%, #ff0080 75%, #ff0000 95%, transparent 100%);
    }
  `;

  // Initial Loading State Render.
  if (isInitialLoading) {
    return (
      <>
        <style>{globalStyles}</style>
        <div className={`min-h-screen flex flex-col items-center justify-center bg-background overflow-hidden ${darkMode ? 'dark' : ''}`}>
          <div 
            className="relative w-24 h-24 flex items-center justify-center"
            style={{ animation: 'strokePulse 2s ease-in-out infinite' }}
          >
            <div 
              className="absolute inset-0 rounded-full animate-spin-linear"
              style={{ 
                background: 'var(--loading-stroke-gradient)', 
                zIndex: 0,
                filter: 'drop-shadow(0 0 4px rgba(0, 114, 255, 0.5)) drop-shadow(0 0 8px rgba(255, 0, 128, 0.4))'
              }}
            ></div>
            <div className="relative z-10 bg-background/95 backdrop-blur-sm w-full h-full rounded-full flex items-center justify-center overflow-hidden m-[3px] p-0.5 shadow-sm">
              <img 
                src="/logo.png" 
                alt="Sortify" 
                className="w-[250%] h-[250%] max-w-none object-center object-cover"
                style={{ animation: 'sortifyHeartbeat 2s ease-in-out infinite' }}
              />
            </div>
          </div>
        </div>
      </>
    );
  }

  return (
    <div className={darkMode ? 'dark' : ''}>
      <div className="min-h-screen bg-background">
        <NotificationContainer 
          notifications={notifications}
          onRemove={removeNotification}
        />

        <FilePreviewModal
          previewState={previewState}
          onClose={closePreview}
          onDownload={downloadFile}
        />

        <Sidebar
          categoryCount={categoryCount}
          frequentFolders={frequentFolders}
          selectedCategory={selectedCategory}
          onCategoryFilter={handleCategoryFilter}
          onNavigateToAllFiles={handleNavigateToAllFiles}
          onNavigateToProfile={handleNavigateToProfile}
          onSignOut={signOut}
          onDrop={handleCategoryDrop}
          darkMode={darkMode}
        />

        <div className="flex-1 lg:ml-64">
          <Header
            userProfile={userProfile}
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            darkMode={darkMode}
            onToggleDarkMode={() => setDarkMode(!darkMode)}
            onNavigateToProfile={handleNavigateToProfile}
            allFiles={uploadedFiles}
            onPreviewFile={handlePreviewFile}
            onNavigateToAllFiles={handleNavigateToAllFiles}
          />

          <main 
            className="flex-1 p-4 lg:p-6 space-y-4 lg:space-y-6"
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => e.preventDefault()}
          >
            {/* Processing Overlay */}
            {isProcessing && (
              <div className="fixed inset-0 z-50 bg-background/60 backdrop-blur-sm flex items-center justify-center">
                <div className="bg-card border border-border rounded-2xl p-8 text-center shadow-2xl">
                  <div className="animate-spin rounded-full h-10 w-10 border-4 border-blue-100 border-t-blue-600 mx-auto mb-4"></div>
                  <p className="text-sm font-medium text-foreground">Updating...</p>
                </div>
              </div>
            )}

            {/* Drag and Drop Overlay */}
            {isDragging && (
              <div className="fixed inset-0 z-40 bg-background/80 backdrop-blur-md flex items-center justify-center transition-all duration-300">
                <div className="bg-card border-2 border-dashed border-blue-500 rounded-2xl p-12 text-center shadow-xl transform scale-105">
                  <div className="bg-blue-50 w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-6">
                    <CloudUpload className="w-10 h-10 text-blue-500" />
                  </div>
                  <h3 className="text-2xl font-bold mb-2 tracking-tight">Drop files here</h3>
                  <p className="text-muted-foreground">Release to upload</p>
                </div>
              </div>
            )}

            <div className="space-y-4">
              <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                <div>
                  <h1 className="text-2xl lg:text-4xl font-bold tracking-tight bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                    Welcome back, {userProfile?.username || 'User'}
                  </h1>
                  <p className="text-muted-foreground text-sm lg:text-base mt-1">Your files are organized and ready to search</p>
                </div>
                <label className="w-full lg:w-auto px-6 lg:px-8 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl font-semibold hover:shadow-xl disabled:opacity-50 flex items-center justify-center gap-2 transition-all shadow-lg cursor-pointer hover:-translate-y-0.5">
                  <input ref={fileInputRef} type="file" onChange={handleFileInputChange} className="hidden" accept="*/*" multiple />
                  <Upload className="h-5 w-5" />
                  Upload Files
                </label>
              </div>

              {/* Search Bar with AI Integration */}
              <div className="relative group">
                <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground group-focus-within:text-blue-500 transition-colors" />
                <input
                  placeholder="Ask a question about your documents..."
                  className="w-full pl-12 pr-32 h-14 rounded-xl bg-card border-2 border-border focus:border-blue-500/50 focus:ring-4 focus:ring-blue-500/10 outline-none transition-all shadow-sm"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
                <button 
                  disabled={!searchQuery.trim()}
                  className="absolute right-2 top-1/2 -translate-y-1/2 px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg flex items-center gap-2 hover:shadow-lg transition-all font-medium disabled:opacity-50 disabled:shadow-none"
                >
                  <Sparkles className="h-4 w-4" />
                  AI Search
                </button>
              </div>

              {/* Filters */}
              <div className="flex items-center gap-2 flex-wrap">
                <button className="px-4 py-2 rounded-lg border border-border hover:bg-accent flex items-center gap-2 transition-colors font-medium text-sm">
                  <Filter className="h-4 w-4" />
                  Filters
                </button>
                {["Recent", "PDF", "Assignments", "This Week"].map((tag) => (
                  <span 
                    key={tag} 
                    onClick={() => setActiveFilter(activeFilter === tag ? null : tag)}
                    className={`px-3 py-1.5 rounded-lg text-sm cursor-pointer transition-all font-medium ${
                      activeFilter === tag 
                        ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300' 
                        : 'bg-secondary/50 hover:bg-secondary text-muted-foreground'
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
                <div className="bg-card rounded-xl border border-border p-4 shadow-sm">
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <Folder className="w-5 h-5 text-blue-500" />
                    Frequent Folders
                  </h3>
                  <div className="space-y-2">
                    {frequentFolders.length > 0 ? frequentFolders.map((folder) => (
                      <button
                        key={folder.name}
                        onClick={() => handleCategoryFilter(folder.name)}
                        className="w-full flex items-center gap-3 p-2 rounded-lg hover:bg-accent transition-colors group"
                      >
                        <div className={`w-3 h-3 rounded-full ${folder.color}`} />
                        <span className="text-sm font-medium group-hover:text-blue-600 transition-colors">{folder.name}</span>
                        <span className="text-xs text-muted-foreground ml-auto bg-muted px-2 py-0.5 rounded-full">{folder.count}</span>
                      </button>
                    )) : (
                      <div className="text-sm text-muted-foreground italic">No folders available</div>
                    )}
                  </div>
                </div>

                {/* Quick Actions */}
                <div className="bg-card rounded-xl border border-border p-4 shadow-sm">
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-purple-500" />
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

                {/* Analytics */}
                <div className="bg-card rounded-xl border border-border p-4 shadow-sm">
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <BarChart3 className="w-5 h-5 text-green-500" />
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
                  <h2 className="text-2xl font-bold tracking-tight">Your Files</h2>
                  <div className="flex items-center p-1 bg-secondary rounded-lg border border-border">
                    <button 
                      onClick={() => setViewMode('directory')}
                      className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all flex items-center gap-2 ${
                        viewMode === 'directory' 
                          ? 'bg-background shadow text-foreground' 
                          : 'text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      <Folder className="w-4 h-4" />
                      Directory
                    </button>
                    <button 
                      onClick={() => setViewMode('grid')}
                      className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all flex items-center gap-2 ${
                        viewMode === 'grid' 
                          ? 'bg-background shadow text-foreground' 
                          : 'text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      <FileText className="w-4 h-4" />
                      Grid
                    </button>
                  </div>
                </div>
                {displayFiles.length === 0 ? (
                  <div className="bg-card rounded-xl border border-border p-12 text-center shadow-sm">
                    <div className="bg-muted/50 w-24 h-24 rounded-full flex items-center justify-center mx-auto mb-6">
                      <FileText className="w-10 h-10 text-muted-foreground opacity-50" />
                    </div>
                    <h3 className="text-lg font-semibold text-foreground mb-2">No files to display</h3>
                    <p className="text-sm text-muted-foreground mb-6 max-w-xs mx-auto">Upload your first file to get started with Sortify and organize your documents.</p>
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
                    categories={categories}
                    onPreviewFile={handlePreviewFile}
                    onDownloadFile={downloadFile}
                    onDeleteFile={handleDeleteFile}
                    onFileNameChange={setNewFileName}
                    onConfirmRename={handleRenameFile}
                    onCategoryChange={handleCategoryChange}
                    onRefreshCategories={fetchCategories}
                  />
                )}
              </div>

              {/* Recent Files Sidebar */}
              <div className="space-y-4 lg:space-y-6">
                <div className="bg-card rounded-xl border border-border p-4 shadow-sm">
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <Clock className="w-5 h-5 text-orange-500" />
                    Recently Uploaded
                  </h3>
                  <div className="space-y-2">
                    {displayFiles.slice(0, 3).map((file) => (
                      <div 
                        key={file.id} 
                        className="flex items-center gap-3 p-2 rounded-lg hover:bg-accent transition-colors cursor-pointer" 
                        onClick={() => handlePreviewFile(file)}
                      >
                        <div className="w-8 h-8 bg-blue-50 dark:bg-blue-900/20 text-blue-600 rounded-lg flex items-center justify-center">
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

                <div className="bg-card rounded-xl border border-border p-4 shadow-sm">
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <CloudUpload className="w-5 h-5 text-indigo-500" />
                    Storage Used
                  </h3>
                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">Used</span>
                      <span className="text-sm font-medium">{formatStorageUsed(storageUsed)}</span>
                    </div>
                    <div className="w-full bg-muted rounded-full h-2 overflow-hidden">
                      <div 
                        className="bg-gradient-to-r from-blue-500 to-indigo-500 h-2 rounded-full transition-all duration-1000"
                        style={{ width: `${Math.min((storageUsed / (100 * 1024 * 1024)) * 100, 100)}%` }}
                      ></div>
                    </div>
                    <p className="text-xs text-muted-foreground text-right">100 MB limit</p>
                  </div>
                </div>
              </div>
            </div>

            <ChatbotPopup />
          </main>
        </div>

        {/* Hidden input for handling file uploads. */}
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