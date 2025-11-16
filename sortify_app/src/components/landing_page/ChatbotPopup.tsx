import { useState, useRef, useEffect } from 'react';
import { MessageCircle, X, Send, Sparkles, FileText, Loader2, Paperclip, XCircle, FolderPlus } from 'lucide-react';
import { supabase } from '../../../../supabase/client';
import { uploadDocument } from '../../api/sorter';

interface AttachedFile {
  id: string;
  file: File;
  name: string;
  size: number;
  type: string;
}

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
  files?: AttachedFile[];
  showActions?: boolean; // Show action buttons for file uploads
  fileContents?: Array<{ name: string; type: string; content: string; mimeType: string }>; // Store file contents for category suggestion
}

export default function ChatbotPopup() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      text: "Hi! I'm your Sortify assistant. I can help you organize files, answer questions about your documents, or assist with your studies. How can I help you today?",
      sender: 'bot',
      timestamp: new Date()
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isCreatingCategory, setIsCreatingCategory] = useState<string | null>(null); // Track which message is creating category
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;

    const newFiles: AttachedFile[] = Array.from(files).map((file) => ({
      id: `${Date.now()}-${Math.random()}`,
      file,
      name: file.name,
      size: file.size,
      type: file.type
    }));

    setAttachedFiles(prev => [...prev, ...newFiles]);
    
    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const removeFile = (fileId: string) => {
    setAttachedFiles(prev => prev.filter(f => f.id !== fileId));
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const readFileAsText = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        resolve(e.target?.result as string);
      };
      reader.onerror = reject;
      reader.readAsText(file);
    });
  };

  const readFileAsBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const result = e.target?.result as string;
        // Remove data URL prefix (e.g., "data:image/png;base64,")
        const base64 = result.split(',')[1] || result;
        resolve(base64);
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  };

  const extractFileContent = async (file: File): Promise<{ type: string; content: string; mimeType: string }> => {
    const fileType = file.type.toLowerCase();
    const fileName = file.name.toLowerCase();

    // Text files
    if (fileType.startsWith('text/') || fileName.match(/\.(txt|md|json|csv|log|js|ts|jsx|tsx|py|java|cpp|c|h|html|css|xml|yaml|yml)$/)) {
      try {
        const text = await readFileAsText(file);
        return { type: 'text', content: text, mimeType: file.type };
      } catch (error) {
        console.error('Error reading text file:', error);
        return { type: 'text', content: `Error reading file: ${file.name}`, mimeType: file.type };
      }
    }

    // PDF files - convert to base64 for Gemini
    if (fileType === 'application/pdf' || fileName.endsWith('.pdf')) {
      try {
        const base64 = await readFileAsBase64(file);
        return { type: 'pdf', content: base64, mimeType: 'application/pdf' };
      } catch (error) {
        console.error('Error reading PDF:', error);
        return { type: 'pdf', content: '', mimeType: 'application/pdf' };
      }
    }

    // Image files - convert to base64 for Gemini vision
    if (fileType.startsWith('image/')) {
      try {
        const base64 = await readFileAsBase64(file);
        return { type: 'image', content: base64, mimeType: file.type };
      } catch (error) {
        console.error('Error reading image:', error);
        return { type: 'image', content: '', mimeType: file.type };
      }
    }

    // For other file types, just return metadata
    return { type: 'unknown', content: `File: ${file.name}\nType: ${file.type}\nSize: ${formatFileSize(file.size)}`, mimeType: file.type };
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim() && attachedFiles.length === 0) return;

    // Upload files to backend if any are attached
    let uploadedFileInfo: string[] = [];
    if (attachedFiles.length > 0) {
      setIsUploading(true);
      try {
        const { data: { user } } = await supabase.auth.getUser();
        if (user) {
          for (const attachedFile of attachedFiles) {
            try {
              const result = await uploadDocument(attachedFile.file, user.id);
              uploadedFileInfo.push(`${attachedFile.name} (${result.status})`);
            } catch (error) {
              console.error(`Error uploading ${attachedFile.name}:`, error);
              uploadedFileInfo.push(`${attachedFile.name} (upload failed)`);
            }
          }
        }
      } catch (error) {
        console.error('Error getting user:', error);
      } finally {
        setIsUploading(false);
      }
    }

    const messageText = inputMessage.trim() || 
      (attachedFiles.length > 0 
        ? `Uploaded ${attachedFiles.length} file(s): ${attachedFiles.map(f => f.name).join(', ')}`
        : '');

    const userMessage: Message = {
      id: Date.now().toString(),
      text: messageText,
      sender: 'user',
      timestamp: new Date(),
      files: attachedFiles.length > 0 ? [...attachedFiles] : undefined
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    const filesToProcess = [...attachedFiles];
    setAttachedFiles([]);
    setIsTyping(true);

    // --- Call Gemini API for a dynamic response ---
    try {
      // This is the system prompt that guides the AI's persona and knowledge
      const systemPrompt = `You are 'Sortify Assistant,' a helpful and friendly chatbot for a student file organization app called 'Sortify.' 
      Your role is to help students with their files, studies, and using the app.
      You have knowledge of the app's features:
      - Uploading files: Users can click 'Upload Files' or drag and drop.
      - Searching: Users can search by filename, category, or content. There is also an 'AI Search' feature.
      - Organization: The app automatically organizes files into categories like Assignments, Lectures, Research, Math, and Science.
      - Storage: Users have 15GB total storage, which they can check in the sidebar.
      
      When a user uploads documents, provide only a brief, concise summary of what's in the document(s). Keep it short and to the point - 2-3 sentences maximum.
      
      Keep your answers concise, friendly, and focused on helping the student.
      Do not make up features that don't exist.`;

      // Extract content from files
      const fileContents: Array<{ name: string; type: string; content: string; mimeType: string }> = [];
      
      if (filesToProcess.length > 0) {
        for (const file of filesToProcess) {
          try {
            const extracted = await extractFileContent(file.file);
            fileContents.push({
              name: file.name,
              type: extracted.type,
              content: extracted.content,
              mimeType: extracted.mimeType
            });
          } catch (error) {
            console.error(`Error extracting content from ${file.name}:`, error);
            fileContents.push({
              name: file.name,
              type: 'error',
              content: `Error reading file: ${file.name}`,
              mimeType: file.type
            });
          }
        }
      }

      // Build the prompt with file contents
      let userPrompt = userMessage.text || '';
      
      // Build parts array for Gemini API (supports multimodal input)
      const parts: Array<{ text?: string; inlineData?: { mimeType: string; data: string } }> = [];

      if (fileContents.length > 0) {
        let fileSummary = `I've uploaded ${fileContents.length} file(s). Please analyze them:\n`;
        let hasProcessableContent = false;
        
        for (const fileContent of fileContents) {
          if (fileContent.type === 'text' && fileContent.content) {
            // For text files, include content directly in the prompt
            fileSummary += `\n--- Content of ${fileContent.name} ---\n${fileContent.content}\n`;
            hasProcessableContent = true;
          } else if (fileContent.type === 'image' && fileContent.content) {
            // For images, add as inline data for Gemini vision
            parts.push({
              inlineData: {
                mimeType: fileContent.mimeType,
                data: fileContent.content
              }
            });
            fileSummary += `\n[Image file: ${fileContent.name} - please analyze this image]\n`;
            hasProcessableContent = true;
          } else if (fileContent.type === 'pdf' && fileContent.content) {
            // For PDFs, try to add as inline data (Gemini 2.5 Flash may support this)
            // If not supported, we'll get an error and can handle it
            try {
              parts.push({
                inlineData: {
                  mimeType: 'application/pdf',
                  data: fileContent.content
                }
              });
              fileSummary += `\n[PDF file: ${fileContent.name} - please analyze this PDF document]\n`;
              hasProcessableContent = true;
            } catch (error) {
              fileSummary += `\n[PDF file: ${fileContent.name} - PDF content extraction may require additional processing]\n`;
            }
          } else {
            fileSummary += `\n${fileContent.name}: ${fileContent.content || 'Unable to read file content'}\n`;
          }
        }

        if (userPrompt) {
          userPrompt += '\n\n' + fileSummary;
        } else {
          userPrompt = fileSummary;
        }

        if (hasProcessableContent) {
          userPrompt += '\n\nPlease provide a brief summary of what\'s in these document(s). Keep it short - 2-3 sentences maximum.';
        } else {
          userPrompt += '\n\nI\'ve uploaded these files. Please provide a brief summary.';
        }
      }

      // Add text prompt as the first part
      if (userPrompt.trim()) {
        parts.unshift({ text: userPrompt });
      }

      const payload = {
        contents: [{ parts }],
        systemInstruction: {
          parts: [{ text: systemPrompt }]
        },
      };

      const apiKey = import.meta.env.VITE_GEMINI_API_KEY;
      const apiUrl = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key=${apiKey}`;

      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('Gemini API error:', errorData);
        
        // Check if it's a file format issue
        if (response.status === 400 && fileContents.length > 0) {
          throw new Error('Some file types may not be supported. Try uploading text files (.txt, .md) or images for best results.');
        }
        throw new Error(`API request failed with status ${response.status}`);
      }

      const result = await response.json();
      const botText = result.candidates?.[0]?.content?.parts?.[0]?.text;

      let botResponseText = "Sorry, I couldn't generate a response. Please try again.";
      if (botText) {
        botResponseText = botText;
      }

      const botResponse: Message = {
        id: (Date.now() + 1).toString(),
        text: botResponseText,
        sender: 'bot',
        timestamp: new Date(),
        showActions: filesToProcess.length > 0, // Show actions if files were uploaded
        fileContents: fileContents.length > 0 ? fileContents : undefined // Store file contents for category suggestion
      };
      
      setMessages(prev => [...prev, botResponse]);

    } catch (error) {
      console.error("Error fetching bot response:", error);
      let errorMessage = "Sorry, I'm having trouble connecting right now. Please try again later.";
      
      if (error instanceof Error) {
        if (error.message.includes('file types may not be supported')) {
          errorMessage = error.message + " PDF files may require text extraction. Try uploading .txt or .md files for immediate analysis.";
        } else if (error.message.includes('API request failed')) {
          errorMessage = "I had trouble processing your request. If you uploaded files, try text files (.txt, .md) or images for best results.";
        }
      }
      
      const errorResponse: Message = {
        id: (Date.now() + 1).toString(),
        text: errorMessage,
        sender: 'bot',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorResponse]);
    } finally {
      setIsTyping(false);
      // Ensure focus is returned to input after sending
      inputRef.current?.focus();
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', { 
      hour: 'numeric', 
      minute: '2-digit',
      hour12: true 
    });
  };

  // Suggest category name using Gemini based on file content
  const suggestCategoryName = async (fileContents: Array<{ name: string; type: string; content: string; mimeType: string }>): Promise<string> => {
    try {
      const systemPrompt = `You are a helpful assistant that suggests category folder names based on document content. 
      Suggest a single, concise category name (2-4 words maximum) that best describes the content of the uploaded document(s).
      Return only the category name, nothing else.`;

      let contentSummary = 'Analyze these files and suggest a category name:\n';
      for (const fileContent of fileContents) {
        if (fileContent.type === 'text' && fileContent.content) {
          // Take first 500 chars for text files
          const preview = fileContent.content.substring(0, 500);
          contentSummary += `\nFile: ${fileContent.name}\nContent preview: ${preview}\n`;
        } else {
          contentSummary += `\nFile: ${fileContent.name} (${fileContent.type})\n`;
        }
      }

      const payload = {
        contents: [{ parts: [{ text: contentSummary }] }],
        systemInstruction: {
          parts: [{ text: systemPrompt }]
        },
      };

      const apiKey = import.meta.env.VITE_GEMINI_API_KEY;
      const apiUrl = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key=${apiKey}`;

      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error('Failed to suggest category name');
      }

      const result = await response.json();
      const suggestedName = result.candidates?.[0]?.content?.parts?.[0]?.text?.trim();
      
      // Clean up the response (remove quotes, extra text)
      const cleanName = suggestedName
        ?.replace(/^["']|["']$/g, '') // Remove surrounding quotes
        .split('\n')[0] // Take first line only
        .trim()
        .substring(0, 30) || 'New Category'; // Limit length

      return cleanName;
    } catch (error) {
      console.error('Error suggesting category name:', error);
      return 'New Category';
    }
  };

  // Create category folder
  const createCategoryFolder = async (categoryName: string, userId: string): Promise<{ success: boolean; message: string }> => {
    try {
      const API_BASE_URL = import.meta.env.VITE_API_URL;
      
      if (!API_BASE_URL) {
        throw new Error('VITE_API_URL environment variable is not set');
      }

      // Generate a random color for the category
      const colors = ['#3B82F6', '#10B981', '#8B5CF6', '#6366F1', '#F59E0B', '#EC4899', '#06B6D4', '#EF4444'];
      const randomColor = colors[Math.floor(Math.random() * colors.length)];

      const formData = new FormData();
      formData.append('user_id', userId);
      formData.append('label', categoryName);
      formData.append('color', randomColor);
      formData.append('type', '');
      formData.append('user_created', 'true');

      const response = await fetch(`${API_BASE_URL}/categories`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        if (response.status === 400 && errorData.detail?.includes('already exists')) {
          return { success: false, message: `Category "${categoryName}" already exists` };
        }
        throw new Error('Failed to create category');
      }

      return { success: true, message: `Category "${categoryName}" created successfully!` };
    } catch (error) {
      console.error('Error creating category:', error);
      return { success: false, message: 'Failed to create category. Please try again.' };
    }
  };

  // Handle action button clicks
  const handleActionClick = async (action: 'summary' | 'category' | 'both', messageId: string) => {
    const message = messages.find(m => m.id === messageId);
    if (!message || !message.fileContents) return;

    setIsCreatingCategory(messageId);

    try {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) {
        throw new Error('User not authenticated');
      }

      if (action === 'category' || action === 'both') {
        // Suggest and create category
        const categoryName = await suggestCategoryName(message.fileContents!);
        const result = await createCategoryFolder(categoryName, user.id);

        // Update the message with the result
        setMessages(prev => prev.map(m => {
          if (m.id === messageId) {
            const actionText = action === 'both' 
              ? `\n\n✅ ${result.message}`
              : `\n\n✅ ${result.message}`;
            return {
              ...m,
              text: m.text + actionText,
              showActions: false // Hide actions after action is taken
            };
          }
          return m;
        }));

        if (!result.success && result.message.includes('already exists')) {
          // Show a message that category already exists
          const errorMessage: Message = {
            id: Date.now().toString(),
            text: result.message,
            sender: 'bot',
            timestamp: new Date()
          };
          setMessages(prev => [...prev, errorMessage]);
        }
      }

      if (action === 'summary' || action === 'both') {
        // Summary is already shown, just hide actions
        setMessages(prev => prev.map(m => {
          if (m.id === messageId) {
            return {
              ...m,
              showActions: false
            };
          }
          return m;
        }));
      }
    } catch (error) {
      console.error('Error handling action:', error);
      const errorMessage: Message = {
        id: Date.now().toString(),
        text: 'Sorry, I encountered an error. Please try again.',
        sender: 'bot',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsCreatingCategory(null);
    }
  };

  return (
    <>
      {/* Chat Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 w-14 h-14 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-full shadow-2xl hover:shadow-3xl transition-all hover:scale-110 flex items-center justify-center z-50 group"
          aria-label="Open chat"
        >
          <MessageCircle className="w-6 h-6" />
          <span className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-white animate-pulse"></span>
        </button>
      )}

      {/* Chat Window */}
      {isOpen && (
        <div className="fixed bottom-6 right-6 w-96 h-[600px] bg-card border border-border rounded-2xl shadow-2xl flex flex-col z-50 overflow-hidden">
          {/* Header */}
          <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-semibold">Sortify Assistant</h3>
                <p className="text-xs text-white/80">Always here to help</p>
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="hover:bg-white/20 p-2 rounded-lg transition-colors"
              aria-label="Close chat"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-muted/30">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                    message.sender === 'user'
                      ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white'
                      : 'bg-card border border-border'
                  }`}
                >
                  {message.files && message.files.length > 0 && (
                    <div className={`mb-2 space-y-1 ${message.sender === 'user' ? 'text-white/90' : ''}`}>
                      {message.files.map((file) => (
                        <div
                          key={file.id}
                          className={`flex items-center gap-2 text-xs p-2 rounded-lg ${
                            message.sender === 'user'
                              ? 'bg-white/20'
                              : 'bg-muted'
                          }`}
                        >
                          <FileText className="w-3 h-3 flex-shrink-0" />
                          <span className="flex-1 truncate">{file.name}</span>
                          <span className="text-xs opacity-70">{formatFileSize(file.size)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {message.text && (
                    <p className="text-sm whitespace-pre-line">{message.text}</p>
                  )}
                  
                  {/* Action Buttons - Show for bot messages with file uploads */}
                  {message.sender === 'bot' && message.showActions && message.fileContents && (
                    <div className="mt-3 pt-3 border-t border-border/50">
                      <p className="text-xs text-muted-foreground mb-2">What would you like to do?</p>
                      <div className="flex flex-wrap gap-2">
                        <button
                          onClick={() => handleActionClick('summary', message.id)}
                          disabled={isCreatingCategory === message.id}
                          className="px-3 py-1.5 text-xs bg-muted hover:bg-muted/80 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
                        >
                          <FileText className="w-3 h-3" />
                          Just Summary
                        </button>
                        <button
                          onClick={() => handleActionClick('category', message.id)}
                          disabled={isCreatingCategory === message.id}
                          className="px-3 py-1.5 text-xs bg-primary/10 hover:bg-primary/20 text-primary rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
                        >
                          {isCreatingCategory === message.id ? (
                            <>
                              <Loader2 className="w-3 h-3 animate-spin" />
                              Creating...
                            </>
                          ) : (
                            <>
                              <FolderPlus className="w-3 h-3" />
                              Create Category
                            </>
                          )}
                        </button>
                        <button
                          onClick={() => handleActionClick('both', message.id)}
                          disabled={isCreatingCategory === message.id}
                          className="px-3 py-1.5 text-xs bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:from-blue-700 hover:to-indigo-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
                        >
                          {isCreatingCategory === message.id ? (
                            <>
                              <Loader2 className="w-3 h-3 animate-spin" />
                              Creating...
                            </>
                          ) : (
                            <>
                              <Sparkles className="w-3 h-3" />
                              Both
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  )}
                  
                  <p
                    className={`text-xs mt-1 ${
                      message.sender === 'user' ? 'text-white/70' : 'text-muted-foreground'
                    }`}
                  >
                    {formatTime(message.timestamp)}
                  </p>
                </div>
              </div>
            ))}
            
            {isTyping && (
              <div className="flex justify-start">
                <div className="bg-card border border-border rounded-2xl px-4 py-3 flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin text-primary" />
                  <span className="text-sm text-muted-foreground">Typing...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Actions */}
          <div className="px-4 py-2 border-t border-border bg-card/50">
            <div className="flex gap-2 overflow-x-auto pb-2">
              {['Upload help', 'Search tips', 'Organize files'].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => {
                    setInputMessage(suggestion);
                    setTimeout(() => inputRef.current?.focus(), 0);
                  }}
                  className="px-3 py-1.5 text-xs bg-muted hover:bg-muted/80 rounded-full whitespace-nowrap transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>

          {/* Input */}
          <div className="p-4 border-t border-border bg-card">
            {/* Attached Files Preview */}
            {attachedFiles.length > 0 && (
              <div className="mb-2 flex flex-wrap gap-2">
                {attachedFiles.map((file) => (
                  <div
                    key={file.id}
                    className="flex items-center gap-2 px-3 py-1.5 bg-muted rounded-lg text-xs"
                  >
                    <FileText className="w-3 h-3 text-primary" />
                    <span className="max-w-[150px] truncate">{file.name}</span>
                    <span className="text-muted-foreground">{formatFileSize(file.size)}</span>
                    <button
                      onClick={() => removeFile(file.id)}
                      className="hover:bg-muted-foreground/20 rounded p-0.5 transition-colors"
                      aria-label="Remove file"
                    >
                      <XCircle className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}
            
            <div className="flex gap-2">
              <input
                ref={fileInputRef}
                type="file"
                multiple
                onChange={handleFileSelect}
                className="hidden"
                aria-label="Upload file"
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                className="px-3 py-3 bg-muted hover:bg-muted/80 border border-border rounded-xl transition-colors flex items-center justify-center"
                aria-label="Attach file"
                title="Attach file"
              >
                <Paperclip className="w-5 h-5 text-muted-foreground" />
              </button>
              <input
                ref={inputRef}
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Type your message..."
                className="flex-1 px-4 py-3 bg-muted border border-border rounded-xl outline-none focus:border-primary transition-colors text-sm"
              />
              <button
                onClick={handleSendMessage}
                disabled={(!inputMessage.trim() && attachedFiles.length === 0) || isTyping || isUploading}
                className="px-4 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                aria-label="Send message"
              >
                {isUploading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}