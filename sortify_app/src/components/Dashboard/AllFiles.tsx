import { useState } from 'react';
import { ArrowLeft, Search, Filter, Grid, List, Download, Trash2, Eye, X, CheckSquare } from 'lucide-react';
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

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
          <p className="text-sm font-medium text-gray-500 animate-pulse">Loading your workspace...</p>
        </div>
      </div>
    );
  }

  return (
    <>
      <FilePreviewModal
        previewState={previewState}
        onClose={closePreview}
        onDownload={downloadFile}
      />

      <div className="min-h-screen bg-[#F9FAFB] text-gray-900 font-sans selection:bg-blue-100 selection:text-blue-900">
        {/* Header Component Wrapper */}
        <div className="sticky top-0 z-40 bg-[#F9FAFB]/80 backdrop-blur-md border-b border-gray-200/50">
            <Header
            userProfile={userProfile}
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            darkMode={false}
            onToggleDarkMode={() => {}}
            onNavigateToProfile={() => navigate('/profile')}
            />
        </div>

        <main className="max-w-7xl mx-auto p-6 lg:p-8">
          {/* Top Navigation Bar */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-10">
            <div>
                <button
                onClick={() => navigate('/dashboard')}
                className="group flex items-center gap-2 text-sm font-medium text-gray-500 hover:text-gray-900 transition-colors mb-3"
                >
                <ArrowLeft className="w-4 h-4 transition-transform group-hover:-translate-x-1" />
                Back
                </button>
                <div className="flex items-baseline gap-3">
                    <h1 className="text-3xl font-bold tracking-tight text-gray-900">All Files</h1>
                    <span className="text-sm font-medium text-gray-400 bg-gray-100 px-2.5 py-0.5 rounded-full">
                        {filteredFiles.length}
                    </span>
                </div>
            </div>

  {/* Global Controls */}
            <div className="flex flex-col sm:flex-row gap-3 w-full md:w-auto">
                {/* Search Bar */}
                <div className="relative group flex-1 sm:min-w-[280px]">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4 group-focus-within:text-blue-500 transition-colors" />
                    <input
                    type="text"
                    placeholder="Search files..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-10 pr-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all placeholder:text-gray-400"
                    />
                </div>

                {/* View Toggle & Filter */}
                <div className="flex items-center gap-2">
                    <button
                    onClick={() => setShowFilters(!showFilters)}
                    className={`p-2.5 rounded-xl border transition-all duration-200 ${
                        showFilters 
                        ? 'bg-blue-50 border-blue-200 text-blue-600' 
                        : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300 hover:bg-gray-50'
                    }`}
                    title="Toggle Filters"
                    >
                    <Filter className="w-4 h-4" />
                    </button>

                    <div className="flex p-1 bg-gray-100 rounded-xl border border-gray-200/50">
                        <button
                            onClick={() => setViewMode('grid')}
                            className={`p-1.5 rounded-lg transition-all duration-200 ${
                            viewMode === 'grid' 
                                ? 'bg-white text-gray-900 shadow-sm' 
                                : 'text-gray-400 hover:text-gray-600'
                            }`}
                        >
                            <Grid className="w-4 h-4" />
                        </button>
                        <button
                            onClick={() => setViewMode('directory')}
                            className={`p-1.5 rounded-lg transition-all duration-200 ${
                            viewMode === 'directory' 
                                ? 'bg-white text-gray-900 shadow-sm' 
                                : 'text-gray-400 hover:text-gray-600'
                            }`}
                        >
                            <List className="w-4 h-4" />
                        </button>
                    </div>
                </div>
            </div>
          </div>
      {/* Animated Filter Panel */}
          <div className={`overflow-hidden transition-all duration-300 ease-in-out ${showFilters ? 'max-h-96 opacity-100 mb-8' : 'max-h-0 opacity-0'}`}>
            <div className="bg-white border border-gray-100 rounded-2xl p-6 shadow-lg shadow-gray-100/50">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-gray-900">Filter Options</h3>
                <button onClick={clearFilters} className="text-xs font-medium text-blue-600 hover:text-blue-700 hover:underline">
                    Reset all
                </button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-gray-500 ml-1">File Type</label>
                  <select
                    value={selectedCategory || ''}
                    onChange={(e) => setSelectedCategory(e.target.value || null)}
                    className="w-full p-2.5 bg-gray-50 border-none rounded-xl text-sm text-gray-700 focus:ring-2 focus:ring-blue-500/20 cursor-pointer hover:bg-gray-100 transition-colors"
                  >
                    <option value="">All Types</option>
                    {categoryCount.map(cat => (
                      <option key={cat.name} value={cat.name}>{cat.name} ({cat.count})</option>
                    ))}
                  </select>
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-gray-500 ml-1">Sort Order</label>
                  <select
                    value={activeFilter || ''}
                    onChange={(e) => setActiveFilter(e.target.value || null)}
                    className="w-full p-2.5 bg-gray-50 border-none rounded-xl text-sm text-gray-700 focus:ring-2 focus:ring-blue-500/20 cursor-pointer hover:bg-gray-100 transition-colors"
                  >
                    <option value="">Default</option>
                    <option value="recent">Date: Newest</option>
                    <option value="oldest">Date: Oldest</option>
                    <option value="name-asc">Name: A-Z</option>
                    <option value="name-desc">Name: Z-A</option>
                    <option value="largest">Size: Largest</option>
                    <option value="smallest">Size: Smallest</option>
                  </select>
                </div>
              </div>
            </div>
          </div>

          {/* Selection Floating Dock */}
          {selectedFiles.length > 0 && (
            <div className="fixed bottom-8 left-1/2 transform -translate-x-1/2 z-50 animate-in slide-in-from-bottom-10 fade-in duration-300">
                <div className="bg-gray-900/90 backdrop-blur-md text-white rounded-full px-6 py-3 shadow-2xl flex items-center gap-6 border border-white/10">
                    <span className="text-sm font-medium pl-2 border-r border-white/20 pr-6">
                        {selectedFiles.length} selected
                    </span>
                    <div className="flex items-center gap-2">
                        <button className="p-2 rounded-full hover:bg-white/20 transition-colors tooltip-trigger" title="Download">
                            <Download className="w-4 h-4" />
                        </button>
                        <button className="p-2 rounded-full hover:bg-red-500/80 transition-colors text-red-300 hover:text-white" title="Delete">
                            <Trash2 className="w-4 h-4" />
                        </button>
                        <button 
                            onClick={() => setSelectedFiles([])}
                            className="p-2 rounded-full hover:bg-white/20 transition-colors ml-2" 
                            title="Cancel"
                        >
                            <X className="w-4 h-4" />
                        </button>
                    </div>
                </div>
            </div>
          )}

          {/* Content Area */}
          {filteredFiles.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-24 px-4 text-center bg-white rounded-3xl border border-dashed border-gray-200">
              <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mb-4">
                <Search className="w-6 h-6 text-gray-400" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">No files found</h3>
              <p className="text-gray-500 max-w-sm mt-2 text-sm">
                {searchQuery || selectedCategory ? 'We couldn\'t find anything matching your criteria.' : 'Your drive is empty. Upload a file to get started.'}
              </p>
              {(searchQuery || selectedCategory) && (
                  <button 
                    onClick={clearFilters}
                    className="mt-6 text-blue-600 text-sm font-medium hover:underline"
                  >
                      Clear all filters
                  </button>
              )}
            </div>
          ) : viewMode === 'grid' ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {filteredFiles.map((file) => (
                <div
                  key={file.id}
                  className={`group relative bg-white rounded-2xl transition-all duration-300 cursor-pointer overflow-hidden
                    ${selectedFiles.includes(file.id) 
                        ? 'ring-2 ring-blue-500 shadow-lg shadow-blue-500/10 transform scale-[1.02]' 
                        : 'border border-gray-100 hover:border-gray-200 shadow-[0_2px_8px_rgba(0,0,0,0.04)] hover:shadow-[0_12px_24px_rgba(0,0,0,0.06)] hover:-translate-y-1'
                    }`}
                  onClick={() => handleSelectFile(file.id)}
                >
                  {/* Selection Checkbox (Visible on Hover or Selected) */}
                  <div className={`absolute top-3 left-3 z-10 transition-all duration-200 ${selectedFiles.includes(file.id) ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}`}>
                      <div className={`w-5 h-5 rounded-md flex items-center justify-center border ${selectedFiles.includes(file.id) ? 'bg-blue-500 border-blue-500 text-white' : 'bg-white border-gray-300'}`}>
                        {selectedFiles.includes(file.id) && <CheckSquare className="w-3 h-3" />}
                      </div>
                  </div>

                  <div className="p-5">
                    <div className="flex items-start justify-between mb-4">
                        {/* Icon Container */}
                        <div className="w-12 h-12 bg-gray-50 rounded-xl flex items-center justify-center text-gray-600 group-hover:scale-110 transition-transform duration-300">
                            {(() => {
                            const { icon: Icon, className } = getFileIcon(file);
                            return <Icon className={className} strokeWidth={1.5} />;
                            })()}
                        </div>
                        
                        {/* Floating Actions */}
                        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-all duration-200 translate-x-2 group-hover:translate-x-0">
                            <button
                                onClick={(e) => { e.stopPropagation(); handlePreviewFile(file); }}
                                className="p-2 rounded-lg hover:bg-gray-100 text-gray-500 hover:text-blue-600 transition-colors"
                            >
                                <Eye className="w-4 h-4" />
                            </button>
                            <button
                                onClick={(e) => { e.stopPropagation(); handleDeleteFile(file.id, file.name, file.storage_path); }}
                                className="p-2 rounded-lg hover:bg-red-50 text-gray-400 hover:text-red-500 transition-colors"
                            >
                                <Trash2 className="w-4 h-4" />
                            </button>
                        </div>
                    </div>

                    <div>
                        <h4 className="text-sm font-semibold text-gray-900 truncate mb-1" title={file.name}>{file.name}</h4>
                        <div className="flex items-center gap-2">
                            <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium tracking-wide uppercase ${getCategoryColor(file.category)} bg-opacity-90 text-white`}>

                                {file.category}
                            </span>
                        </div>
                    </div>
                  </div>

                  {/* Footer Meta */}
                  <div className="px-5 py-3 bg-gray-50/50 border-t border-gray-100 flex items-center justify-between text-xs text-gray-400 font-medium">
                    <span>{file.size}</span>
                    <span>{file.modified}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50/80 border-b border-gray-100">
                    <tr>
                      <th className="p-4 w-12">
                        <input
                          type="checkbox"
                          checked={selectedFiles.length === filteredFiles.length && filteredFiles.length > 0}
                          onChange={handleSelectAll}
                          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500/20 cursor-pointer"
                        />
                      </th>
                      <th className="p-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Name</th>
                      <th className="p-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Type</th>
                      <th className="p-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Size</th>
                      <th className="p-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Modified</th>
                      <th className="p-4 w-24"></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {filteredFiles.map((file) => (
                      <tr 
                        key={file.id} 
                        onClick={() => handleSelectFile(file.id)}
                        className={`group hover:bg-gray-50 transition-colors cursor-pointer ${selectedFiles.includes(file.id) ? 'bg-blue-50/30' : ''}`}
                      >
                        <td className="p-4">
                          <input
                            type="checkbox"
                            checked={selectedFiles.includes(file.id)}
                            onChange={() => handleSelectFile(file.id)}
                            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500/20 cursor-pointer"
                          />
                        </td>
                        <td className="p-4">
                          <div className="flex items-center gap-4">
                            <div className="w-8 h-8 bg-gray-100 rounded-lg flex items-center justify-center text-gray-500">
                              {(() => {
                                const { icon: Icon } = getFileIcon(file);
                                return <Icon className="w-4 h-4" />;
                              })()}
                            </div>
                            <p className="text-sm font-medium text-gray-900">{file.name}</p>
                          </div>
                        </td>
                        <td className="p-4">
                            <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-600">
                                {file.category}
                            </span>
                        </td>
                        <td className="p-4 text-sm text-gray-500">{file.size}</td>
                        <td className="p-4 text-sm text-gray-500">{file.modified}</td>
                        <td className="p-4">
                          <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button
                                onClick={(e) => { e.stopPropagation(); handlePreviewFile(file); }}
                                className="p-1.5 text-gray-400 hover:text-blue-600 transition-colors"
                            >
                              <Eye className="w-4 h-4" />
                            </button>
                            {file.storage_path && (
                              <button
                                onClick={(e) => { e.stopPropagation(); downloadFile(file.storage_path!, file.name); }}
                                className="p-1.5 text-gray-400 hover:text-gray-900 transition-colors"
                              >
                                <Download className="w-4 h-4" />
                              </button>
                            )}
                             <button
                                onClick={(e) => { e.stopPropagation(); handleDeleteFile(file.id, file.name, file.storage_path); }}
                                className="p-1.5 text-gray-400 hover:text-red-600 transition-colors"
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

          {filteredFiles.length > 20 && (
            <div className="mt-12 text-center">
              <button className="px-8 py-3 bg-white border border-gray-200 text-sm font-medium text-gray-600 rounded-xl hover:bg-gray-50 hover:border-gray-300 transition-all shadow-sm">
                Load More
              </button>
            </div>
          )}
        </main>
      </div>
    </>
  );
}