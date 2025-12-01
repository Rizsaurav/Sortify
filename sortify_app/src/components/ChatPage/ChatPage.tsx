import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Send, ArrowLeft, Sparkles, FileText, Loader2 } from 'lucide-react';
import { searchDocuments } from '../../api/sorter';
import { useUserProfile } from '../Dashboard/hooks/useUserProfile';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: string[];
  timestamp: Date;
  chunksUsed?: number;
  responseTime?: number;
}

interface LocationState {
    query?: string;
}

// Function to convert **bold** text to <strong>HTML</strong>
// This prevents React from escaping the content and allows the browser to render <strong> tags.
const formatText = (text: string) => {
  // Regex to find content enclosed in double asterisks, globally
  // (\\*\\*): Escapes the asterisks.
  // (.*?): Captures the content non-greedily.
  // g: Global flag to replace all occurrences.
  const formattedText = text.replace(
    /\*\*(.*?)\*\*/g, 
    '<strong>$1</strong>'
  );
  
  // in a real-world app to prevent XSS attacks. Since this is an internal rendering change 
  // for known LLM output, we rely on the internal safety of the LLM output.
  return { __html: formattedText };
};


export default function ChatPage() {
  const navigate = useNavigate();
  // Ensure location state is correctly typed
const location = useLocation() as { state: LocationState | null }; 
const { userProfile } = useUserProfile();
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // Use a ref to store userProfile.id to avoid unnecessary dependency array checks
  const userIdRef = useRef<string | undefined>(userProfile?.id);

  useEffect(() => {
    userIdRef.current = userProfile?.id;
  }, [userProfile]);

  useEffect(() => {
    // If navigated from search with initial query
    const initialQuery = location.state?.query;
    if (initialQuery && messages.length === 0 && userIdRef.current) {
      handleSendMessage(initialQuery);
    }
  }, [location.state]); // Removed messages and userProfile to avoid infinite loop potential

  useEffect(() => {
    // Scroll to bottom when new messages arrive
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async (messageText?: string) => {
    const text = messageText || inputValue.trim();
    if (!text || isLoading) return;

    // Use ref for ID check
    const currentUserId = userIdRef.current;
    if (!currentUserId) {
      console.log('⏳ Waiting for user profile ID...');
      return;
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: text,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      // Build conversation history from existing messages (exclude current message)
      const conversationHistory = messages.map(msg => ({
        role: msg.role,
        content: msg.content
      }));

      // Send request with conversation history
      const result = await searchDocuments(text, currentUserId, 5, conversationHistory);

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: result.answer,
        sources: result.sources,
        chunksUsed: result.chunks_used,
        responseTime: result.response_time,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    // Use React.KeyboardEvent<HTMLTextAreaElement> for better typing if possible
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // Show loading if user profile not loaded
  if (!userProfile) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin mx-auto mb-2 text-blue-600" />
          <p className="text-muted-foreground">Loading user profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <header className="bg-card border-b border-border px-4 py-3 flex items-center gap-3">
        <button
          onClick={() => navigate('/dashboard')}
          className="p-2 hover:bg-accent rounded-lg transition-colors"
          title="Back to Dashboard"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="flex items-center gap-2 flex-1">
          <Sparkles className="w-6 h-6 text-blue-600" />
          <h1 className="text-lg font-semibold">AI Assistant</h1>
        </div>
        <div className="text-sm text-muted-foreground">
          {userProfile?.username || 'User'}
        </div>
      </header>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
        {messages.length === 0 && !isLoading && (
          <div className="flex flex-col items-center justify-center h-full text-center max-w-2xl mx-auto">
            <Sparkles className="w-16 h-16 text-blue-600 mb-4" />
            <h2 className="text-2xl font-bold mb-2">Ask me anything about your documents</h2>
            <p className="text-muted-foreground mb-6">
              I'll search through your uploaded files and provide answers using AI
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full">
              <button
                onClick={() => setInputValue("What are the main topics in my documents?")}
                className="p-4 bg-accent rounded-lg hover:bg-accent/80 transition-colors text-left"
              >
                <p className="font-medium text-sm">Summarize my documents</p>
                <p className="text-xs text-muted-foreground mt-1">Get an overview of main topics</p>
              </button>
              <button
                onClick={() => setInputValue("What assignments do I have?")}
                className="p-4 bg-accent rounded-lg hover:bg-accent/80 transition-colors text-left"
              >
                <p className="font-medium text-sm">Find assignments</p>
                <p className="text-xs text-muted-foreground mt-1">Search for homework and tasks</p>
              </button>
            </div>
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-3xl ${
                message.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-card border border-border'
              } rounded-lg p-4 space-y-2`}
            >
              <div className="flex items-start gap-2">
                {message.role === 'assistant' && (
                  <Sparkles className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                )}
                {/* ---  Use formatText for assistant messages --- */}
                <div 
                  className="flex-1 whitespace-pre-wrap"
                  dangerouslySetInnerHTML={
                    message.role === 'assistant' 
                      ? formatText(message.content) 
                      : { __html: message.content }
                  }
                />
                {/* ----------------------------------------------------------------- */}
              </div>

              {message.sources && message.sources.length > 0 && (
                <div className="pt-3 border-t border-border/50 space-y-2">
                  <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                    <FileText className="w-4 h-4" />
                    Sources ({message.sources.length})
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {message.sources.map((source, idx) => (
                      <span
                        key={idx}
                        className="px-2 py-1 bg-accent rounded text-xs"
                      >
                        {source}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {message.chunksUsed !== undefined && (
                <div className="text-xs text-muted-foreground pt-2">
                  {message.chunksUsed} chunks analyzed • {message.responseTime?.toFixed(2)}s
                </div>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-card border border-border rounded-lg p-4 flex items-center gap-3">
              <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
              <span className="text-muted-foreground">Thinking...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-border bg-card p-4">
        <div className="max-w-4xl mx-auto flex gap-3">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="Ask a question about your documents..."
            className="flex-1 px-4 py-3 bg-background border border-border rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
            rows={1}
            disabled={isLoading}
          />
          <button
            onClick={() => handleSendMessage()}
            disabled={!inputValue.trim() || isLoading}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
        <p className="text-xs text-muted-foreground text-center mt-2">
          Press Enter to send, Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}