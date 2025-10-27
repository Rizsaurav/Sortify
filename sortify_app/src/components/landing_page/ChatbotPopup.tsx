import { useState, useRef, useEffect } from 'react';
import { MessageCircle, X, Send, Sparkles, FileText, Loader2 } from 'lucide-react';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
}

interface ChatbotPopupProps {
  isOpen?: boolean;
  onOpenChange?: (isOpen: boolean) => void;
  initialMessage?: string;
}

export default function ChatbotPopup({ isOpen: externalIsOpen, onOpenChange, initialMessage }: ChatbotPopupProps) {
  const [internalIsOpen, setInternalIsOpen] = useState(false);
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
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Use external control if provided, otherwise use internal state
  const isOpen = externalIsOpen !== undefined ? externalIsOpen : internalIsOpen;
  const setIsOpen = onOpenChange || setInternalIsOpen;

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

  // Handle initial message when chatbot opens
  useEffect(() => {
    if (isOpen && initialMessage && initialMessage.trim()) {
      setInputMessage(initialMessage);
    }
  }, [isOpen, initialMessage]);

  const generateBotResponse = (userMessage: string): string => {
    const lowerMessage = userMessage.toLowerCase();

    if (lowerMessage.includes('hello') || lowerMessage.includes('hi')) {
      return "Hello! How can I assist you with your files and studies today?";
    }
    if (lowerMessage.includes('upload') || lowerMessage.includes('file')) {
      return "To upload files, click the 'Upload Files' button at the top of your dashboard or drag and drop files directly onto the page. I can help organize them automatically!";
    }
    if (lowerMessage.includes('search') || lowerMessage.includes('find')) {
      return "You can search for files using the search bar at the top. Try searching by filename, category, or content. The AI Search feature can also help you find documents based on their content!";
    }
    if (lowerMessage.includes('organize') || lowerMessage.includes('category')) {
      return "I automatically organize your files into categories like Assignments, Lectures, Research, Math, and Science based on their names and content. You can also filter by category using the sidebar!";
    }
    if (lowerMessage.includes('help') || lowerMessage.includes('how')) {
      return "I can help you with:\n• Uploading and organizing files\n• Searching through documents\n• Understanding your storage usage\n• Finding specific assignments or notes\n\nWhat would you like to know more about?";
    }
    if (lowerMessage.includes('storage') || lowerMessage.includes('space')) {
      return "You can check your storage usage in the bottom right sidebar. You have 15GB total storage. I can help you manage your files if you're running low on space!";
    }

    return "I'm here to help! You can ask me about uploading files, searching documents, organizing your work, or any other features of Sortify. What would you like to know?";
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputMessage,
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsTyping(true);

    setTimeout(() => {
      const botResponse: Message = {
        id: (Date.now() + 1).toString(),
        text: generateBotResponse(inputMessage),
        sender: 'bot',
        timestamp: new Date()
      };
      
      setMessages(prev => [...prev, botResponse]);
      setIsTyping(false);
    }, 1000);
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
                  <p className="text-sm whitespace-pre-line">{message.text}</p>
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
                    inputRef.current?.focus();
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
            <div className="flex gap-2">
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
                disabled={!inputMessage.trim()}
                className="px-4 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                aria-label="Send message"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}