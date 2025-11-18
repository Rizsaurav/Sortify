import { describe, it, expect, beforeAll, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, waitFor, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ChatbotPopup from './ChatbotPopup';
import { supabase } from '../../../../supabase/client';
import { uploadDocument } from '../../api/sorter';

// --- FIX: Manually extend expect for Vitest ---
import * as matchers from '@testing-library/jest-dom/matchers';
expect.extend(matchers);

// --- Mocks ---

// Mock Supabase client
vi.mock('../../../../supabase/client', () => ({
  supabase: {
    auth: {
      getUser: vi.fn(),
    },
  },
}));

// Mock the API uploader function
vi.mock('../../api/sorter', () => ({
  uploadDocument: vi.fn(),
}));

// Mock scrollIntoView since JSDOM doesn't implement it
window.HTMLElement.prototype.scrollIntoView = vi.fn();

// Mock environment variables using vi.stubEnv
vi.stubEnv('VITE_GEMINI_API_KEY', 'test-key');
vi.stubEnv('VITE_API_URL', 'http://localhost:3000');


describe('ChatbotPopup Component', () => {
  const mockFetch = vi.fn();
  
  beforeAll(() => {
    global.fetch = mockFetch;
  });

  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockClear();
    
    // Default Supabase Mock: User is logged in
    (supabase.auth.getUser as any).mockResolvedValue({
      data: { user: { id: 'test-user-id' } },
    });

    // Default Upload Mock
    (uploadDocument as any).mockResolvedValue({ status: 'success' });

    // Default Fetch Mock (Gemini API Success)
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        candidates: [
          {
            content: {
              parts: [{ text: 'This is a mock AI response.' }],
            },
          },
        ],
      }),
    });
  });

  // --- FIX: Clean up DOM after each test ---
  afterEach(() => {
    cleanup();
  });

  it('renders the chat button initially (closed state)', () => {
    render(<ChatbotPopup />);
    const openButton = screen.getByLabelText('Open chat');
    expect(openButton).toBeInTheDocument();
    expect(screen.queryByText('Sortify Assistant')).not.toBeInTheDocument();
  });

  it('opens the chat window when button is clicked', async () => {
    const user = userEvent.setup();
    render(<ChatbotPopup />);
    
    const openButton = screen.getByLabelText('Open chat');
    await user.click(openButton);

    expect(screen.getByText('Sortify Assistant')).toBeInTheDocument();
    expect(screen.getByText(/Hi! I'm your Sortify assistant/i)).toBeInTheDocument();
  });

  it('closes the chat window when close button is clicked', async () => {
    const user = userEvent.setup();
    render(<ChatbotPopup />);

    // Open it first
    await user.click(screen.getByLabelText('Open chat'));
    
    // Find close button and click
    const closeButton = screen.getByLabelText('Close chat');
    await user.click(closeButton);

    expect(screen.queryByText('Sortify Assistant')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Open chat')).toBeInTheDocument();
  });

  it('allows typing and sending a text message', async () => {
    const user = userEvent.setup();
    render(<ChatbotPopup />);
    
    await user.click(screen.getByLabelText('Open chat'));

    const input = screen.getByPlaceholderText('Type your message...');
    const sendButton = screen.getByLabelText('Send message');

    // Type message
    await user.type(input, 'Hello AI');
    expect(input).toHaveValue('Hello AI');

    // Send message
    await user.click(sendButton);

    // Check if user message appears
    expect(screen.getByText('Hello AI')).toBeInTheDocument();
    // Check if input cleared
    expect(input).toHaveValue('');
    
    // Wait for AI response
    await waitFor(() => {
      expect(screen.getByText('This is a mock AI response.')).toBeInTheDocument();
    });
  });

  it('handles file attachment and removal', async () => {
    const user = userEvent.setup();
    render(<ChatbotPopup />);
    await user.click(screen.getByLabelText('Open chat'));

    const file = new File(['dummy content'], 'test-doc.txt', { type: 'text/plain' });
    const fileInput = screen.getByLabelText('Upload file');

    // Upload file
    await user.upload(fileInput, file);

    // Check if file preview is shown
    expect(screen.getByText('test-doc.txt')).toBeInTheDocument();

    // Remove file
    const removeButton = screen.getByLabelText('Remove file');
    await user.click(removeButton);

    expect(screen.queryByText('test-doc.txt')).not.toBeInTheDocument();
  });

  it('uploads file to backend and sends message with file context', async () => {
    const user = userEvent.setup();
    render(<ChatbotPopup />);
    await user.click(screen.getByLabelText('Open chat'));

    const file = new File(['dummy content'], 'notes.txt', { type: 'text/plain' });
    const fileInput = screen.getByLabelText('Upload file');
    
    await user.upload(fileInput, file);
    
    const sendButton = screen.getByLabelText('Send message');
    await user.click(sendButton);

    // Check if uploadDocument was called
    expect(uploadDocument).toHaveBeenCalledWith(expect.any(File), 'test-user-id');

    // Check if Gemini API was called
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('generativelanguage.googleapis.com'),
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining('dummy content') // Verify file content reading
        })
      );
    });
  });

  it('handles API errors gracefully', async () => {
    // --- FIX: Silence console.error for this test to keep output clean ---
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    // Mock API failure
    mockFetch.mockRejectedValueOnce(new Error('API Error'));

    const user = userEvent.setup();
    render(<ChatbotPopup />);
    await user.click(screen.getByLabelText('Open chat'));

    const input = screen.getByPlaceholderText('Type your message...');
    await user.type(input, 'Hello');
    await user.click(screen.getByLabelText('Send message'));

    await waitFor(() => {
      expect(screen.getByText(/Sorry, I'm having trouble connecting/i)).toBeInTheDocument();
    });

    // Restore console.error
    consoleSpy.mockRestore();
  });

  it('displays action buttons when files are processed successfully', async () => {
    // Setup mock to return a message that triggers showActions (requires file upload)
   const user = userEvent.setup();
   render(<ChatbotPopup />);
   await user.click(screen.getByLabelText('Open chat'));

   const file = new File(['content'], 'test.txt', { type: 'text/plain' });
   await user.upload(screen.getByLabelText('Upload file'), file);
   await user.click(screen.getByLabelText('Send message'));

   await waitFor(() => {
     // Check for action buttons
     expect(screen.getByText('Just Summary')).toBeInTheDocument();
     expect(screen.getByText('Create Category')).toBeInTheDocument();
     expect(screen.getByText('Both')).toBeInTheDocument();
   });
 });

 it('creates category when Create Category action is clicked', async () => {
   const user = userEvent.setup();
   render(<ChatbotPopup />);
   await user.click(screen.getByLabelText('Open chat'));

   // 1. Upload File
   const file = new File(['Biology notes content'], 'bio.txt', { type: 'text/plain' });
   await user.upload(screen.getByLabelText('Upload file'), file);
   await user.click(screen.getByLabelText('Send message'));

   // Wait for response and buttons
   await waitFor(() => expect(screen.getByText('Create Category')).toBeInTheDocument());

   // 2. Prepare mocks for the Category Creation flow
   // We need to mock the fetch sequence:
   // Call 1: Gemini Category Suggestion
   // Call 2: Backend Create Category
   mockFetch
     .mockResolvedValueOnce({
       ok: true,
       json: async () => ({ candidates: [{ content: { parts: [{ text: 'Biology 101' }] } }] }),
     })
     .mockResolvedValueOnce({
       ok: true,
       json: async () => ({ id: '123', label: 'Biology 101' }),
     });

   // 3. Click Action
   await user.click(screen.getByText('Create Category'));

   // 4. Verify Success Message
   await waitFor(() => {
     expect(screen.getByText(/Category "Biology 101" created successfully/i)).toBeInTheDocument();
   });
   
   // 5. Verify Backend call
   expect(mockFetch).toHaveBeenCalledWith(
     'http://localhost:3000/categories',
     expect.objectContaining({
       method: 'POST',
       body: expect.any(FormData)
     })
   );
 });
});