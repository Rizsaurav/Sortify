import { useState, useEffect, useRef } from 'react';
import { Upload, Search, Clock, Star, Folder, FileText, Film, MoreHorizontal, Filter, Sparkles, Bell, Sun, Moon, Home, File, CloudUpload, BookOpen, GraduationCap, Calculator, BarChart3, Settings, Beaker, X, LogOut, Download, Trash2, Edit2, Image as ImageIcon } from 'lucide-react';
import { supabase } from '../../../../supabase/client';
import { useProfile } from '../userProfiles/ProfileProviders';
import { useNavigate } from 'react-router-dom';

const DEMO_FILES = [
  { id: 'demo-1', name: 'Sample Assignment.pdf', type: 'application/pdf', size: '2.4 MB', modified: '2 hours ago', category: 'Assignments', created_at: new Date().toISOString() },
  { id: 'demo-2', name: 'Lecture Notes.txt', type: 'text/plain', size: '1.2 MB', modified: '1 day ago', category: 'Lectures', created_at: new Date().toISOString() },
  { id: 'demo-3', name: 'Research Paper.pdf', type: 'application/pdf', size: '5.8 MB', modified: '3 days ago', category: 'Research', created_at: new Date().toISOString() },
  { id: 'demo-4', name: 'Math Homework.pdf', type: 'application/pdf', size: '890 KB', modified: '5 days ago', category: 'Math', created_at: new Date().toISOString() },
  { id: 'demo-5', name: 'Biology Lab Report.docx', type: 'application/msword', size: '3.1 MB', modified: '1 week ago', category: 'Science', created_at: new Date().toISOString() },
];


const frequentFolders = [
  { name: "Assignments", icon: BookOpen, color: "text-blue-500" },
  { name: "Lecture Notes", icon: GraduationCap, color: "text-green-500" },
  { name: "Research Papers", icon: Beaker, color: "text-purple-500" },
  { name: "Lab Reports", icon: Calculator, color: "text-orange-500" }
];

const getCategoryColor = (category: string): string => {
  const colors: Record<string, string> = {
    Math: "bg-orange-500",
    Science: "bg-green-500",
    History: "bg-blue-500",
    English: "bg-purple-500",
    Physics: "bg-red-500",
    Assignments: "bg-blue-500",
    Lectures: "bg-green-500",
    Research: "bg-purple-500",
    General: "bg-gray-500"
  };
  return colors[category] || "bg-gray-500";
};

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

interface CategoryCount {
  name: string;
  icon: any;
  count: number;
  color: string;
}

export default function Dashboard() {
  const [isUploading, setIsUploading] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [allFiles, setAllFiles] = useState<UploadedFile[]>([]);
  const [userName, setUserName] = useState('User');
  const [userEmail, setUserEmail] = useState('');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [notification, setNotification] = useState<string | null>(null);
  const [totalFilesCount, setTotalFilesCount] = useState(0);
  const [storageUsed, setStorageUsed] = useState(0);
  const [categoryCount, setCategoryCount] = useState<CategoryCount[]>([]);
  const [folderCounts, setFolderCounts] = useState<{[key: string]: number}>({});
  const [searchQuery, setSearchQuery] = useState('');
  const [filteredFiles, setFilteredFiles] = useState<UploadedFile[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [previewFile, setPreviewFile] = useState<UploadedFile | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewContent, setPreviewContent] = useState<string | null>(null);
  const [previewType, setPreviewType] = useState<'pdf' | 'image' | 'text' | 'video' | 'none'>('none');
  const [renamingFileId, setRenamingFileId] = useState<string | null>(null);
  const [newFileName, setNewFileName] = useState('');
  const [activeFilter, setActiveFilter] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { profile } = useProfile();
  const navigate = useNavigate();

  useEffect(() => {
    checkAuth();
    const savedDarkMode = localStorage.getItem('darkMode');
    if (savedDarkMode) setDarkMode(JSON.parse(savedDarkMode));
  }, []);

  useEffect(() => {
    localStorage.setItem('darkMode', JSON.stringify(darkMode));
  }, [darkMode]);

  useEffect(() => {
    if (isAuthenticated) {
      loadUserInfo();
      loadAllUserDocuments();
    }
  }, [profile, isAuthenticated]);

  useEffect(() => {
    applyFilters();
  }, [searchQuery, allFiles, selectedCategory, activeFilter]);

  const applyFilters = () => {
    let filtered = [...allFiles];
    
    if (searchQuery) {
      filtered = filtered.filter(file => 
        file.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        file.category.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }
    
    if (selectedCategory) {
      filtered = filtered.filter(file => file.category === selectedCategory);
    }

    if (activeFilter) {
      switch (activeFilter) {
        case 'Recent':
          const sevenDaysAgo = new Date();
          sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
          filtered = filtered.filter(file => {
            if (file.created_at) {
              return new Date(file.created_at) >= sevenDaysAgo;
            }
            return false;
          });
          break;
        case 'PDF':
          filtered = filtered.filter(file => 
            file.type.toLowerCase().includes('pdf') || 
            file.name.toLowerCase().endsWith('.pdf')
          );
          break;
        case 'Assignments':
          filtered = filtered.filter(file => file.category === 'Assignments');
          break;
        case 'This Week':
          const oneWeekAgo = new Date();
          oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);
          filtered = filtered.filter(file => {
            if (file.created_at) {
              return new Date(file.created_at) >= oneWeekAgo;
            }
            return false;
          });
          break;
      }
    }
    
    setFilteredFiles(filtered);
  };

  const checkAuth = async () => {
    const isGuestMode = localStorage.getItem('isGuest');
    
    if (isGuestMode === 'true') {
      setIsAuthenticated(true);
      setIsLoading(false); // SET THIS IMMEDIATELY
      setUserName('Guest User');
      setUserEmail('guest@sortify.app');
      
      // ... rest of demo data setup
      
      return; // STOP - don't check session
    }
    
    // Only check session if NOT guest
    try {
      const { data: { session } } = await supabase.auth.getSession();
      
      if (!session) {
        navigate('/login');
        return;
      }
      
      setIsAuthenticated(true);
    } catch (error) {
      console.error('Auth check error:', error);
      navigate('/login');
    } finally {
      setIsLoading(false);
    }
  };
  
  

  const handleLogout = async () => {
    try {
      await supabase.auth.signOut();
      navigate('/login');
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  const loadUserInfo = async () => {
    try {
      const { data: { user } } = await supabase.auth.getUser();
      if (user) {
        setUserEmail(user.email || '');
        if (profile?.username) {
          setUserName(profile.username);
        } else if (user.email) {
          setUserName(user.email.split('@')[0]);
        }
      }
    } catch (error) {
      console.error('Error loading user info:', error);
    }
  };

  const loadAllUserDocuments = async () => {
    try {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) return;

      const { data, error } = await supabase
        .from('documents')
        .select('id, metadata, created_at, content')
        .eq('metadata->>user_id', user.id)
        .order('created_at', { ascending: false });

      if (error) throw error;

      if (data) {
        const formattedFiles = data.map(doc => ({
          id: doc.id,
          name: doc.metadata?.filename || 'Unknown File',
          type: doc.metadata?.type || 'file',
          size: doc.metadata?.size || 'Unknown',
          modified: formatDate(doc.created_at),
          category: doc.metadata?.category || 'General',
          storage_path: doc.metadata?.storage_path,
          view_count: doc.metadata?.view_count || 0,
          metadata: doc.metadata,
          content: doc.content,
          created_at: doc.created_at
        }));

        setAllFiles(formattedFiles);
        setUploadedFiles(formattedFiles.slice(0, 5));
        setTotalFilesCount(formattedFiles.length);

        const totalBytes = data.reduce((acc, doc) => {
          const sizeStr = doc.metadata?.size || '0 B';
          return acc + parseSizeToBytes(sizeStr);
        }, 0);
        setStorageUsed(totalBytes);

        const categoryCounts: {[key: string]: number} = {};
        formattedFiles.forEach(file => {
          categoryCounts[file.category] = (categoryCounts[file.category] || 0) + 1;
        });

        const categories: CategoryCount[] = [
          { name: "Assignments", icon: BookOpen, count: categoryCounts['Assignments'] || 0, color: "bg-blue-500" },
          { name: "Lectures", icon: GraduationCap, count: categoryCounts['Lectures'] || 0, color: "bg-green-500" },
          { name: "Research", icon: Beaker, count: categoryCounts['Research'] || 0, color: "bg-purple-500" },
          { name: "Math", icon: Calculator, count: categoryCounts['Math'] || 0, color: "bg-orange-500" }
        ];
        setCategoryCount(categories);

        setFolderCounts({
          "Assignments": categoryCounts['Assignments'] || 0,
          "Lecture Notes": categoryCounts['Lectures'] || 0,
          "Research Papers": categoryCounts['Research'] || 0,
          "Lab Reports": categoryCounts['Science'] || 0
        });
      }
    } catch (error) {
      console.error('Error loading documents:', error);
    }
  };

  const parseSizeToBytes = (sizeStr: string): number => {
    const match = sizeStr.match(/([\d.]+)\s*(B|KB|MB|GB)/i);
    if (!match) return 0;
    
    const value = parseFloat(match[1]);
    const unit = match[2].toUpperCase();
    
    const multipliers: {[key: string]: number} = {
      'B': 1,
      'KB': 1024,
      'MB': 1024 * 1024,
      'GB': 1024 * 1024 * 1024
    };
    
    return value * (multipliers[unit] || 0);
  };

  const formatStorageSize = (bytes: number) => {
    if (bytes < 1024) return bytes.toFixed(0) + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB';
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} min ago`;
    if (diffHours < 24) return `${diffHours} hr ago`;
    if (diffDays < 7) return `${diffDays} day ago`;
    return date.toLocaleDateString();
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const extractTextFromFile = async (file: File): Promise<string> => {
    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const content = e.target?.result as string;
        if (file.type.startsWith('text/') || file.type === 'application/json') {
          resolve(content);
        } else {
          resolve(`File: ${file.name}\nType: ${file.type}\nSize: ${file.size} bytes`);
        }
      };
      reader.onerror = () => resolve(`File: ${file.name}\nType: ${file.type}\nSize: ${file.size} bytes`);
      
      if (file.type.startsWith('text/') || file.type === 'application/json') {
        reader.readAsText(file);
      } else {
        resolve(`File: ${file.name}\nType: ${file.type}\nSize: ${file.size} bytes`);
      }
    });
  };

  const detectCategory = (filename: string): string => {
    const lower = filename.toLowerCase();
    if (lower.includes('assignment')) return 'Assignments';
    if (lower.includes('lecture') || lower.includes('note')) return 'Lectures';
    if (lower.includes('research') || lower.includes('paper')) return 'Research';
    if (lower.includes('math') || lower.includes('calculus') || lower.includes('algebra')) return 'Math';
    if (lower.includes('bio') || lower.includes('chem') || lower.includes('physics')) return 'Science';
    if (lower.includes('history')) return 'History';
    if (lower.includes('english') || lower.includes('literature') || lower.includes('essay')) return 'English';
    if (lower.includes('lab')) return 'Science';
    return 'General';
  };

  const getFileType = (file: UploadedFile): 'pdf' | 'image' | 'text' | 'video' | 'none' => {
    const type = file.type.toLowerCase();
    const name = file.name.toLowerCase();

    if (type.includes('pdf') || name.endsWith('.pdf')) return 'pdf';
    if (type.includes('image') || name.match(/\.(jpg|jpeg|png|gif|bmp|webp|svg)$/)) return 'image';
    if (type.includes('video') || name.match(/\.(mp4|webm|ogg|mov|avi)$/)) return 'video';
    if (type.includes('text') || name.match(/\.(txt|md|json|csv|log)$/)) return 'text';
    
    return 'text'; // Default to text for doc files
  };

  const handleFileSelect = async (file: File) => {
    setIsUploading(true);

    try {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) {
        setNotification('Please log in to upload files');
        setTimeout(() => setNotification(null), 3000);
        navigate('/login');
        setIsUploading(false);
        return;
      }

      const fileExt = file.name.split('.').pop();
      const fileName = `${user.id}/${Date.now()}-${file.name}`;
      
      const { data: storageData, error: storageError } = await supabase.storage
        .from('user-files')
        .upload(fileName, file);

      if (storageError) throw storageError;

      const content = await extractTextFromFile(file);

      const { data: docData, error: docError } = await supabase
        .from('documents')
        .insert({
          content: content,
          embedding: null,
          metadata: {
            user_id: user.id,
            filename: file.name,
            type: file.type || fileExt,
            size: formatFileSize(file.size),
            category: detectCategory(file.name),
            storage_path: storageData.path,
            view_count: 0
          },
          cluster_id: null
        })
        .select()
        .single();

      if (docError) throw docError;

      setNotification(`✓ ${file.name} uploaded successfully!`);
      setTimeout(() => setNotification(null), 3000);

      await loadAllUserDocuments();

    } catch (error: any) {
      console.error('Upload error:', error);
      setNotification(`✗ Upload failed: ${error.message}`);
      setTimeout(() => setNotification(null), 3000);
    } finally {
      setIsUploading(false);
    }
  };

  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      await handleFileSelect(file);
      event.target.value = '';
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const file = e.dataTransfer.files[0];
    if (file) {
      await handleFileSelect(file);
    }
  };

  const incrementViewCount = async (file: UploadedFile) => {
    try {
      const newViewCount = (file.view_count || 0) + 1;
      
      await supabase
        .from('documents')
        .update({
          metadata: {
            ...file.metadata,
            view_count: newViewCount
          }
        })
        .eq('id', file.id);
    } catch (error) {
      console.error('Error updating view count:', error);
    }
  };

  const handlePreviewFile = async (file: UploadedFile) => {
    setPreviewFile(file);
    setPreviewUrl(null);
    setPreviewContent(null);
    setPreviewType('none');
    
    await incrementViewCount(file);

    if (!file.storage_path) {
      setPreviewContent(file.content || 'No content available');
      setPreviewType('text');
      return;
    }

    try {
      const fileType = getFileType(file);
      setPreviewType(fileType);

      const { data } = await supabase.storage
        .from('user-files')
        .createSignedUrl(file.storage_path, 3600);

      if (!data?.signedUrl) {
        throw new Error('Could not generate preview URL');
      }

      if (fileType === 'pdf' || fileType === 'image' || fileType === 'video') {
        setPreviewUrl(data.signedUrl);
      } else if (fileType === 'text') {
        const { data: fileData, error: downloadError } = await supabase.storage
          .from('user-files')
          .download(file.storage_path);

        if (downloadError) throw downloadError;

        const text = await fileData.text();
        setPreviewContent(text || file.content || 'No content available');
      }
    } catch (error) {
      console.error('Error loading preview:', error);
      setPreviewContent(file.content || 'Error loading file preview. Please try downloading the file.');
      setPreviewType('text');
    }
  };

  const handleDownloadFile = async (storagePath: string, fileName: string) => {
    try {
      const { data, error } = await supabase.storage
        .from('user-files')
        .download(storagePath);

      if (error) throw error;

      const url = URL.createObjectURL(data);
      const a = document.createElement('a');
      a.href = url;
      a.download = fileName;
      document.body.appendChild(a);
      a.click();
      URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      setNotification(`✓ ${fileName} downloaded!`);
      setTimeout(() => setNotification(null), 2000);
    } catch (error: any) {
      console.error('Download error:', error);
      setNotification(`✗ Download failed: ${error.message}`);
      setTimeout(() => setNotification(null), 3000);
    }
  };

  const handleDeleteFile = async (fileId: string, fileName: string, storagePath?: string) => {
    if (!confirm(`Delete "${fileName}"?`)) return;

    try {
      if (storagePath) {
        await supabase.storage.from('user-files').remove([storagePath]);
      }

      const { error } = await supabase
        .from('documents')
        .delete()
        .eq('id', fileId);

      if (error) throw error;

      setNotification(`✓ ${fileName} deleted!`);
      setTimeout(() => setNotification(null), 2000);

      await loadAllUserDocuments();
    } catch (error: any) {
      console.error('Delete error:', error);
      setNotification(`✗ Delete failed: ${error.message}`);
      setTimeout(() => setNotification(null), 3000);
    }
  };

  const handleRenameFile = async (fileId: string) => {
    if (!newFileName.trim()) return;

    try {
      const file = allFiles.find(f => f.id === fileId);
      if (!file) return;

      const { error } = await supabase
        .from('documents')
        .update({
          metadata: {
            ...file.metadata,
            filename: newFileName
          }
        })
        .eq('id', fileId);

      if (error) throw error;

      setNotification(`✓ File renamed to ${newFileName}!`);
      setTimeout(() => setNotification(null), 2000);
      setRenamingFileId(null);
      setNewFileName('');

      await loadAllUserDocuments();
    } catch (error: any) {
      console.error('Rename error:', error);
      setNotification(`✗ Rename failed: ${error.message}`);
      setTimeout(() => setNotification(null), 3000);
    }
  };

  const handleCategoryFilter = (categoryName: string) => {
    setSelectedCategory(selectedCategory === categoryName ? null : categoryName);
  };

  const handleTagFilter = (tag: string) => {
    setActiveFilter(activeFilter === tag ? null : tag);
  };

  const closePreview = () => {
    setPreviewFile(null);
    setPreviewUrl(null);
    setPreviewContent(null);
    setPreviewType('none');
  };

// Check guest mode at render level
const isGuest = localStorage.getItem('isGuest') === 'true';

if (isLoading && !isGuest) {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-600 border-t-transparent"></div>
    </div>
  );
}

if (!isAuthenticated && !isGuest) {
  return null;
}


  const storageLimit = 15 * 1024 * 1024 * 1024;
  const storagePercentage = Math.min((storageUsed / storageLimit) * 100, 100);
  const displayFiles = searchQuery || selectedCategory || activeFilter ? filteredFiles : allFiles;

  return (
    <div className={darkMode ? 'dark' : ''}>
      <div className="min-h-screen bg-background">
        <div className="flex">
          {/* Notification */}
          {notification && (
            <div className="fixed top-4 right-4 z-50 bg-card border border-border rounded-lg shadow-2xl p-4 flex items-center gap-3 animate-in slide-in-from-top-5">
              <div className="flex-1">
                <p className="text-sm font-medium text-foreground">{notification}</p>
              </div>
              <button
                onClick={() => setNotification(null)}
                className="text-muted-foreground hover:text-foreground"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* Preview Modal */}
          {previewFile && (
            <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={closePreview}>
              <div className="bg-card rounded-xl border border-border max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col" onClick={(e) => e.stopPropagation()}>
                <div className="p-6 border-b border-border flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold">{previewFile.name}</h3>
                    <p className="text-sm text-muted-foreground">{previewFile.category} • {previewFile.size}</p>
                  </div>
                  <button onClick={closePreview} className="hover:bg-accent p-2 rounded-lg">
                    <X className="w-5 h-5" />
                  </button>
                </div>
                <div className="flex-1 overflow-auto bg-muted/30">
                  {previewType === 'pdf' && previewUrl ? (
                    <iframe
                      src={`${previewUrl}#toolbar=0`}
                      className="w-full h-full min-h-[600px]"
                      title={previewFile.name}
                    />
                  ) : previewType === 'image' && previewUrl ? (
                    <div className="flex items-center justify-center p-8 min-h-[600px]">
                      <img 
                        src={previewUrl} 
                        alt={previewFile.name}
                        className="max-w-full max-h-full object-contain rounded-lg shadow-lg"
                      />
                    </div>
                  ) : previewType === 'video' && previewUrl ? (
                    <div className="flex items-center justify-center p-8 min-h-[600px]">
                      <video 
                        controls
                        className="max-w-full max-h-full rounded-lg shadow-lg"
                        src={previewUrl}
                      >
                        Your browser does not support video playback.
                      </video>
                    </div>
                  ) : previewType === 'text' && previewContent ? (
                    <div className="p-8 max-w-4xl mx-auto">
                      <div className="bg-background rounded-lg p-6 shadow-sm">
                        <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-foreground overflow-x-auto">{previewContent}</pre>
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
                <div className="p-4 border-t border-border flex items-center justify-end gap-3">
                  {previewFile.storage_path && (
                    <button
                      onClick={() => handleDownloadFile(previewFile.storage_path!, previewFile.name)}
                      className="px-4 py-2 bg-primary text-white rounded-lg hover:opacity-90 flex items-center gap-2"
                    >
                      <Download className="w-4 h-4" />
                      Download
                    </button>
                  )}
                  <button
                    onClick={closePreview}
                    className="px-4 py-2 border border-border rounded-lg hover:bg-accent"
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Sidebar */}
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

              <nav className="flex-1 px-4 py-6 space-y-8 overflow-y-auto">
                <div>
                  <h3 className="text-xs font-semibold text-sidebar-foreground/60 uppercase tracking-wider mb-3 px-3">Navigation</h3>
                  <ul className="space-y-1">
                    {[
                      { name: "Dashboard", icon: Home, current: true },
                      { name: "All Files", icon: File, count: totalFilesCount },
                      { name: "Search", icon: Search },
                      { name: "Upload", icon: CloudUpload, onClick: () => fileInputRef.current?.click() }
                    ].map((item) => (
                      <li key={item.name}>
                        <button 
                          onClick={item.onClick}
                          className={`w-full flex items-center gap-3 h-10 px-3 rounded-lg transition-all ${
                            item.current
                              ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg"
                              : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                          }`}
                        >
                          <item.icon className="w-5 h-5" />
                          <span className="flex-1 text-left text-sm font-medium">{item.name}</span>
                          {item.count !== undefined && <span className={`text-xs px-2 py-0.5 rounded-full ${item.current ? 'bg-white/20' : 'bg-sidebar-accent'}`}>{item.count}</span>}
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>

                <div>
                  <h3 className="text-xs font-semibold text-sidebar-foreground/60 uppercase tracking-wider mb-3 px-3">Categories</h3>
                  <ul className="space-y-1">
                    {categoryCount.map((cat) => (
                      <li key={cat.name}>
                        <button 
                          onClick={() => handleCategoryFilter(cat.name)}
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
                    ))}
                  </ul>
                </div>
              </nav>

              <div className="p-4 border-t border-sidebar-border space-y-1">
                {[
                  { name: "Analytics", icon: BarChart3 },
                  { name: "Settings", icon: Settings }
                ].map((item) => (
                  <button key={item.name} className="w-full flex items-center gap-3 h-10 px-3 rounded-lg text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground transition-all">
                    <item.icon className="w-5 h-5" />
                    <span className="text-sm">{item.name}</span>
                  </button>
                ))}
                <button onClick={handleLogout} className="w-full flex items-center gap-3 h-10 px-3 rounded-lg text-red-500 hover:bg-red-500/10 transition-all">
                  <LogOut className="w-5 h-5" />
                  <span className="text-sm">Logout</span>
                </button>
              </div>
            </div>
          </aside>

          <div className="flex-1 lg:ml-64">
            {/* Header */}
            <header className="h-16 border-b border-border bg-card/80 backdrop-blur-lg sticky top-0 z-40 shadow-sm">
              <div className="h-full flex items-center justify-between px-4 lg:px-6">
                <div className="flex items-center gap-4"></div>
                <div className="flex items-center gap-3">
                  <button onClick={() => setDarkMode(!darkMode)} className="relative h-10 w-10 rounded-lg hover:bg-accent transition-colors">
                    <Sun className="h-5 w-5 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
                    <Moon className="h-5 w-5 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
                  </button>
                  <button className="relative h-10 w-10 rounded-lg hover:bg-accent transition-colors">
                    <Bell className="h-5 w-5" />
                    <span className="absolute top-1.5 right-1.5 h-2 w-2 bg-red-500 rounded-full animate-pulse"></span>
                  </button>
                  <div className="flex items-center gap-3 pl-3 border-l border-border">
                    <div className="text-right hidden sm:block">
                      <div className="text-sm font-medium">{userName}</div>
                      <div className="text-xs text-muted-foreground">{userEmail || 'user@university.edu'}</div>
                    </div>
                    <div className="h-10 w-10 rounded-full bg-gradient-to-br from-blue-600 to-indigo-600 text-white flex items-center justify-center font-semibold shadow-lg">
                      {userName.substring(0, 2).toUpperCase()}
                    </div>
                  </div>
                </div>
              </div>
            </header>

            {/* Main Content */}
            <main 
              className="flex-1 p-4 lg:p-6 space-y-4 lg:space-y-6"
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              {isDragging && (
                <div className="fixed inset-0 z-40 bg-primary/10 border-4 border-dashed border-primary flex items-center justify-center">
                  <div className="bg-card p-8 rounded-xl shadow-2xl">
                    <CloudUpload className="w-16 h-16 text-primary mx-auto mb-4" />
                    <p className="text-xl font-semibold text-foreground">Drop file here to upload</p>
                  </div>
                </div>
              )}

              <div className="space-y-4">
                <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                  <div>
                    <h1 className="text-2xl lg:text-4xl font-bold tracking-tight bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">Welcome back, {userName}</h1>
                    <p className="text-muted-foreground text-sm lg:text-base mt-1">Your files are organized and ready to search</p>
                  </div>
                  <label className="w-full lg:w-auto px-6 lg:px-8 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl font-semibold hover:shadow-xl disabled:opacity-50 flex items-center justify-center gap-2 transition-all shadow-lg cursor-pointer">
                    <input ref={fileInputRef} type="file" onChange={handleUpload} className="hidden" accept="*/*" disabled={isUploading} />
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

                // ... inside <div className="lg:col-span-2">

                {displayFiles.length === 0 ? (
                  <div className="bg-card rounded-xl border border-border p-12 text-center">
                    {searchQuery ? (
                      <>
                        <Search className="w-16 h-16 text-muted-foreground mx-auto mb-4 opacity-50" />
                        <h3 className="text-lg font-semibold text-foreground mb-2">No documents found</h3>
                        <p className="text-sm text-muted-foreground">Try a different search term or check your filters.</p>
                      </>
                    ) : (
                      <>
                        <FileText className="w-16 h-16 text-muted-foreground mx-auto mb-4 opacity-50" />
                        <h3 className="text-lg font-semibold text-foreground mb-2">No files to display</h3>
                        <p className="text-sm text-muted-foreground mb-6">Upload your first file to get started with Sortify</p>
                        <button 
                          onClick={() => fileInputRef.current?.click()}
                          className="px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg font-medium hover:shadow-lg transition-all"
                        >
                          Upload Files
                        </button>
                      </>
                    )}
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* ... file mapping logic remains here ... */}
                  </div>
                )}

                // ...

                <div className="flex items-center gap-2 flex-wrap">
                  <button className="px-4 py-2 rounded-lg border border-border hover:bg-accent flex items-center gap-2 transition-colors">
                    <Filter className="h-4 w-4" />
                    Filters
                  </button>
                  {["Recent", "PDF", "Assignments", "This Week"].map((tag) => (
                    <span 
                      key={tag} 
                      onClick={() => handleTagFilter(tag)}
                      className={`px-3 py-1.5 rounded-lg text-sm cursor-pointer transition-colors ${
                        activeFilter === tag 
                          ? 'bg-primary text-primary-foreground' 
                          : 'bg-secondary hover:bg-secondary/80'
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
                  <div className="bg-card rounded-xl border border-border p-4 lg:p-6 shadow-lg">
                    <h3 className="text-lg font-semibold mb-4">Frequent Folders</h3>
                    <div className="space-y-2">
                      {frequentFolders.map((folder) => (
                        <button key={folder.name} className="w-full flex items-center gap-3 p-3 rounded-lg hover:bg-muted/50 transition-colors">
                          <div className="w-10 h-10 bg-muted rounded-lg flex items-center justify-center">
                            <folder.icon className={`w-5 h-5 ${folder.color}`} />
                          </div>
                          <div className="flex-1 text-left">
                            <div className="font-medium">{folder.name}</div>
                            <div className="text-xs text-muted-foreground">{folderCounts[folder.name] || 0} files</div>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="bg-card rounded-xl border border-border p-4 lg:p-6 shadow-lg">
                    <h3 className="text-lg font-semibold mb-4">Quick Actions</h3>
                    <div className="space-y-2">
                      <button className="w-full flex items-center gap-3 p-3 rounded-lg border border-border hover:bg-muted/50 transition-colors">
                        <Star className="w-5 h-5 text-primary" />
                        <div className="flex-1 text-left">
                          <div className="font-medium">Starred Items</div>
                          <div className="text-xs text-muted-foreground">Your favorites</div>
                        </div>
                      </button>
                      <button className="w-full flex items-center gap-3 p-3 rounded-lg border border-border hover:bg-muted/50 transition-colors">
                        <Clock className="w-5 h-5 text-primary" />
                        <div className="flex-1 text-left">
                          <div className="font-medium">Recent Activity</div>
                          <div className="text-xs text-muted-foreground">Latest changes</div>
                        </div>
                      </button>
                    </div>
                  </div>
                </div>

                {/* File Grid */}
                <div className="lg:col-span-2">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-2xl font-bold">Recent Files</h2>
                    <button className="px-4 py-2 rounded-lg border border-border hover:bg-accent transition-colors text-sm font-medium">View All</button>
                  </div>
                  {displayFiles.length === 0 ? (
                    <div className="bg-card rounded-xl border border-border p-12 text-center">
                      <FileText className="w-16 h-16 text-muted-foreground mx-auto mb-4 opacity-50" />
                      <h3 className="text-lg font-semibold text-foreground mb-2">No files to display</h3>
                      <p className="text-sm text-muted-foreground mb-6">Upload your first file to get started with Sortify</p>
                      <button 
                        onClick={() => fileInputRef.current?.click()}
                        className="px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg font-medium hover:shadow-lg transition-all"
                      >
                        Upload Files
                      </button>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {displayFiles.slice(0, 6).map((file) => (
                        <div key={file.id} className="group bg-card rounded-xl border border-border hover:shadow-xl transition-all cursor-pointer overflow-hidden">
                          <div className="p-4">
                            <div className="flex items-start justify-between mb-3">
                              <div className="flex items-center gap-3 flex-1 min-w-0" onClick={() => handlePreviewFile(file)}>
                                <div className="w-10 h-10 bg-muted rounded-lg flex items-center justify-center">
                                  {file.type.includes("mp4") || file.type.includes("video") ? <Film className="w-5 h-5 text-muted-foreground" /> : <FileText className="w-5 h-5 text-muted-foreground" />}
                                </div>
                                <div className="flex-1 min-w-0">
                                  {renamingFileId === file.id ? (
                                    <input
                                      type="text"
                                      value={newFileName}
                                      onChange={(e) => setNewFileName(e.target.value)}
                                      onBlur={() => handleRenameFile(file.id)}
                                      onKeyPress={(e) => e.key === 'Enter' && handleRenameFile(file.id)}
                                      className="text-sm font-medium w-full bg-background px-2 py-1 rounded"
                                      autoFocus
                                    />
                                  ) : (
                                    <h4 className="text-sm font-medium truncate">{file.name}</h4>
                                  )}
                                  <div className="flex items-center gap-2 mt-1">
                                    <div className={`w-2 h-2 rounded-full ${getCategoryColor(file.category)}`} />
                                    <span className="text-xs text-muted-foreground">{file.category}</span>
                                  </div>
                                </div>
                              </div>
                              <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-all">
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setRenamingFileId(file.id);
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
                                      handleDownloadFile(file.storage_path!, file.name);
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
                  )}
                </div>

                {/* Recent Files Sidebar */}
                <div className="space-y-4 lg:space-y-6">
                  <div className="bg-card rounded-xl border border-border p-4 lg:p-6 shadow-lg">
                    <h3 className="text-lg font-semibold mb-4">Student Profile</h3>
                    <div className="flex items-center gap-3 mb-4">
                      <div className="h-12 w-12 rounded-full bg-gradient-to-br from-blue-600 to-indigo-600 text-white flex items-center justify-center font-semibold shadow-lg text-lg">
                        {userName.substring(0, 2).toUpperCase()}
                      </div>
                      <div>
                        <h4 className="font-semibold">{userName}</h4>
                        <p className="text-sm text-muted-foreground">Computer Science Major</p>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4 pt-4 border-t border-border">
                      <div className="text-center">
                        <div className="text-2xl font-bold text-primary">{totalFilesCount}</div>
                        <div className="text-xs text-muted-foreground">Total Files</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-green-500">
                          {totalFilesCount > 0 ? Math.round((categoryCount.reduce((acc, cat) => acc + cat.count, 0) / totalFilesCount) * 100) : 0}%
                        </div>
                        <div className="text-xs text-muted-foreground">Organized</div>
                      </div>
                    </div>
                  </div>

                  <div className="bg-card rounded-xl border border-border p-4 lg:p-6 shadow-lg">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-semibold">Recently Uploaded</h3>
                      <button className="text-sm text-primary hover:underline font-medium">View All</button>
                    </div>
                    <div className="space-y-2">
                      {uploadedFiles.length > 0 ? (
                        uploadedFiles.map((file) => (
                          <div key={file.id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50 group transition-colors cursor-pointer" onClick={() => handlePreviewFile(file)}>
                            <div className="w-8 h-8 bg-muted rounded-md flex items-center justify-center">
                              {file.type.includes("mp4") || file.type.includes("video") ? <Film className="w-4 h-4 text-muted-foreground" /> : <FileText className="w-4 h-4 text-muted-foreground" />}
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium truncate">{file.name}</p>
                              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                <span>{file.size}</span>
                                <span>•</span>
                                <span>{file.modified}</span>
                              </div>
                            </div>
                            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100">
                              {file.storage_path && (
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleDownloadFile(file.storage_path!, file.name);
                                  }}
                                  className="p-1 rounded hover:bg-muted transition-all"
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
                                className="p-1 rounded hover:bg-red-500/10 text-red-500 transition-all"
                                title="Delete"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          </div>
                        ))
                      ) : (
                        <div className="text-center py-8">
                          <CloudUpload className="w-10 h-10 text-muted-foreground mx-auto mb-3 opacity-50" />
                          <p className="text-sm text-muted-foreground">No files uploaded yet</p>
                          <p className="text-xs text-muted-foreground mt-1">Upload files to see them here</p>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="bg-card rounded-xl border border-border p-4 shadow-lg">
                    <div className="flex items-center justify-between text-sm mb-2">
                      <span className="text-muted-foreground">Storage Used</span>
                      <span className="font-medium">{formatStorageSize(storageUsed)} / 15GB</span>
                    </div>
                    <div className="h-2 bg-muted rounded-full overflow-hidden">
                      <div className="h-full bg-gradient-to-r from-blue-600 to-indigo-600" style={{ width: `${storagePercentage}%` }}></div>
                    </div>
                    <div className="text-xs text-muted-foreground mt-2">{formatStorageSize(storageLimit - storageUsed)} remaining</div>
                  </div>
                </div>
              </div>
            </main>
          </div>
        </div>
      </div>
    </div>
  );
}
