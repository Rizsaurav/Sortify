import { useState } from 'react';
import { Upload, Search, Clock, Star, Folder, FileText, Film, MoreHorizontal, Filter, Sparkles, Bell, Sun, Moon, Home, File, CloudUpload, BookOpen, GraduationCap, Calculator, BarChart3, Settings, Beaker } from 'lucide-react';

const files = [
  { id: 1, name: "Calculus Assignment 3.pdf", type: "pdf", size: "2.4 MB", modified: "2 hours ago", category: "Math" },
  { id: 2, name: "Biology Lab Report.docx", type: "docx", size: "1.8 MB", modified: "1 day ago", category: "Science" },
  { id: 3, name: "History Presentation.pptx", type: "pptx", size: "5.2 MB", modified: "3 days ago", category: "History" },
  { id: 4, name: "Chemistry Notes.pdf", type: "pdf", size: "3.1 MB", modified: "1 week ago", category: "Science" },
  { id: 5, name: "Literature Essay.docx", type: "docx", size: "892 KB", modified: "1 week ago", category: "English" },
  { id: 6, name: "Physics Lab Video.mp4", type: "mp4", size: "45.2 MB", modified: "2 weeks ago", category: "Physics" }
];

const frequentFolders = [
  { name: "Assignments", count: 89, icon: BookOpen, color: "text-blue-500" },
  { name: "Lecture Notes", count: 156, icon: GraduationCap, color: "text-green-500" },
  { name: "Research Papers", count: 34, icon: Beaker, color: "text-purple-500" },
  { name: "Lab Reports", count: 23, icon: Calculator, color: "text-orange-500" }
];

const categories = [
  { name: "Assignments", icon: BookOpen, count: 89, color: "bg-blue-500" },
  { name: "Lectures", icon: GraduationCap, count: 156, color: "bg-green-500" },
  { name: "Research", icon: Beaker, count: 34, color: "bg-purple-500" },
  { name: "Math", icon: Calculator, count: 67, color: "bg-orange-500" }
];

const getCategoryColor = (category: string): string => {
  const colors: Record<string, string> = {
    Math: "bg-orange-500",
    Science: "bg-green-500",
    History: "bg-blue-500",
    English: "bg-purple-500",
    Physics: "bg-red-500"
  };
  return colors[category] || "bg-gray-500";
};

export default function Dashboard() {
  const [isUploading, setIsUploading] = useState(false);
  const [darkMode, setDarkMode] = useState(false);

  const handleUpload = () => {
    setIsUploading(true);
    setTimeout(() => setIsUploading(false), 2000);
  };

  return (
    <div className={darkMode ? 'dark' : ''}>
      <div className="min-h-screen bg-background">
        <div className="flex">
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
                      { name: "All Files", icon: File, count: 1247 },
                      { name: "Search", icon: Search },
                      { name: "Upload", icon: CloudUpload }
                    ].map((item) => (
                      <li key={item.name}>
                        <button className={`w-full flex items-center gap-3 h-10 px-3 rounded-lg transition-all ${
                          item.current
                            ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg"
                            : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                        }`}>
                          <item.icon className="w-5 h-5" />
                          <span className="flex-1 text-left text-sm font-medium">{item.name}</span>
                          {item.count && <span className={`text-xs px-2 py-0.5 rounded-full ${item.current ? 'bg-white/20' : 'bg-sidebar-accent'}`}>{item.count}</span>}
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>

                <div>
                  <h3 className="text-xs font-semibold text-sidebar-foreground/60 uppercase tracking-wider mb-3 px-3">Categories</h3>
                  <ul className="space-y-1">
                    {categories.map((cat) => (
                      <li key={cat.name}>
                        <button className="w-full flex items-center gap-3 h-10 px-3 rounded-lg text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground transition-all">
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
                      <div className="text-sm font-medium">Zabraks</div>
                      <div className="text-xs text-muted-foreground">Zabraks@university.edu</div>
                    </div>
                    <div className="h-10 w-10 rounded-full bg-gradient-to-br from-blue-600 to-indigo-600 text-white flex items-center justify-center font-semibold shadow-lg">AS</div>
                  </div>
                </div>
              </div>
            </header>

            {/* Main Content */}
            <main className="flex-1 p-4 lg:p-6 space-y-4 lg:space-y-6">
              <div className="space-y-4">
                <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                  <div>
                    <h1 className="text-2xl lg:text-4xl font-bold tracking-tight bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">Welcome back, Zabrak</h1>
                    <p className="text-muted-foreground text-sm lg:text-base mt-1">Your files are organized and ready to search</p>
                  </div>
                  <button onClick={handleUpload} disabled={isUploading} className="w-full lg:w-auto px-6 lg:px-8 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl font-semibold hover:shadow-xl disabled:opacity-50 flex items-center justify-center gap-2 transition-all shadow-lg">
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
                  </button>
                </div>

                <div className="relative">
                  <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
                  <input placeholder="Search through your documents, assignments, and notes..." className="w-full pl-12 pr-32 h-14 rounded-xl bg-card border-2 border-border focus:border-primary outline-none transition-all shadow-sm" />
                  <button className="absolute right-2 top-1/2 -translate-y-1/2 px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg flex items-center gap-2 hover:shadow-lg transition-all font-medium">
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
                    <span key={tag} className="px-3 py-1.5 rounded-lg bg-secondary hover:bg-secondary/80 text-sm cursor-pointer transition-colors">{tag}</span>
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
                            <div className="text-xs text-muted-foreground">{folder.count} files</div>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="bg-card rounded-xl border border-border p-4 lg:p-6 shadow-lg">
                    <h3 className="text-lg font-semibold mb-4">Quick Actions</h3>
                    <div className="space-y-2">
                      {[
                        { name: "Starred Items", icon: Star, desc: "Your favorites" },
                        { name: "Recent Activity", icon: Clock, desc: "Latest changes" }
                      ].map((action) => (
                        <button key={action.name} className="w-full flex items-center gap-3 p-3 rounded-lg border border-border hover:bg-muted/50 transition-colors">
                          <action.icon className="w-5 h-5 text-primary" />
                          <div className="flex-1 text-left">
                            <div className="font-medium">{action.name}</div>
                            <div className="text-xs text-muted-foreground">{action.desc}</div>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                {/* File Grid */}
                <div className="lg:col-span-2">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-2xl font-bold">Recent Files</h2>
                    <button className="px-4 py-2 rounded-lg border border-border hover:bg-accent transition-colors text-sm font-medium">View All</button>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {files.map((file) => (
                      <div key={file.id} className="group bg-card rounded-xl border border-border hover:shadow-xl transition-all cursor-pointer overflow-hidden">
                        <div className="p-4">
                          <div className="flex items-start justify-between mb-3">
                            <div className="flex items-center gap-3 flex-1 min-w-0">
                              <div className="w-10 h-10 bg-muted rounded-lg flex items-center justify-center">
                                {file.type === "mp4" ? <Film className="w-5 h-5 text-muted-foreground" /> : <FileText className="w-5 h-5 text-muted-foreground" />}
                              </div>
                              <div className="flex-1 min-w-0">
                                <h4 className="text-sm font-medium truncate">{file.name}</h4>
                                <div className="flex items-center gap-2 mt-1">
                                  <div className={`w-2 h-2 rounded-full ${getCategoryColor(file.category)}`} />
                                  <span className="text-xs text-muted-foreground">{file.category}</span>
                                </div>
                              </div>
                            </div>
                            <button className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-muted transition-all">
                              <MoreHorizontal className="w-4 h-4" />
                            </button>
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
                </div>

                {/* Recent Files Sidebar */}
                <div className="space-y-4 lg:space-y-6">
                  <div className="bg-card rounded-xl border border-border p-4 lg:p-6 shadow-lg">
                    <h3 className="text-lg font-semibold mb-4">Student Profile</h3>
                    <div className="flex items-center gap-3 mb-4">
                      <div className="h-12 w-12 rounded-full bg-gradient-to-br from-blue-600 to-indigo-600 text-white flex items-center justify-center font-semibold shadow-lg text-lg">AS</div>
                      <div>
                        <h4 className="font-semibold">Alex Smith</h4>
                        <p className="text-sm text-muted-foreground">Computer Science Major</p>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4 pt-4 border-t border-border">
                      <div className="text-center">
                        <div className="text-2xl font-bold text-primary">1,247</div>
                        <div className="text-xs text-muted-foreground">Total Files</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-green-500">89%</div>
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
                      {files.slice(0, 5).map((file) => (
                        <div key={file.id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50 group transition-colors">
                          <div className="w-8 h-8 bg-muted rounded-md flex items-center justify-center">
                            {file.type === "mp4" ? <Film className="w-4 h-4 text-muted-foreground" /> : <FileText className="w-4 h-4 text-muted-foreground" />}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium truncate">{file.name}</p>
                            <div className="flex items-center gap-2 text-xs text-muted-foreground">
                              <span>{file.size}</span>
                              <span>•</span>
                              <span>{file.modified}</span>
                            </div>
                          </div>
                          <button className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-muted transition-all">
                            <MoreHorizontal className="w-4 h-4" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="bg-card rounded-xl border border-border p-4 shadow-lg">
                    <div className="flex items-center justify-between text-sm mb-2">
                      <span className="text-muted-foreground">Storage Used</span>
                      <span className="font-medium">8.4GB / 15GB</span>
                    </div>
                    <div className="h-2 bg-muted rounded-full overflow-hidden">
                      <div className="h-full bg-gradient-to-r from-blue-600 to-indigo-600" style={{ width: '56%' }}></div>
                    </div>
                    <div className="text-xs text-muted-foreground mt-2">6.6GB remaining</div>
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