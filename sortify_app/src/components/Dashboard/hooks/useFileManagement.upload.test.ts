import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useFileManagement } from './useFileManagement';

// Mock the SAME module path the hook imports
vi.mock('../../../../../supabase/client', () => ({
  supabase: {
    auth: {
      // always return a user object
      getUser: vi.fn().mockResolvedValue({ data: { user: { id: 'u1' } } }),
    },
  },
}));

// Mock uploader API
vi.mock('../../../api/sorter', () => ({
  uploadDocument: vi.fn(),
  getTaskStatus: vi.fn(), // unused here (no polling in this test)
}));

import { uploadDocument } from '../../../api/sorter';

const flush = () => new Promise((r) => setTimeout(r, 0));

describe('useFileManagement uploader (simple happy path)', () => {
  beforeEach(() => {
    // Do NOT reset all mocks (would wipe implementations). Just clear call history.
    vi.clearAllMocks();

    // Mock the backend fetches called by fetchFiles():
    // 1) initial mount: documents (empty), categories (empty)
    // 2) after upload refresh: documents (one file), categories (Assignments)
    global.fetch = vi
      .fn()
      // initial documents
      .mockResolvedValueOnce({
        ok: true,
        json: vi.fn().mockResolvedValue({ documents: [] }),
      } as any)
      // initial categories
      .mockResolvedValueOnce({
        ok: true,
        json: vi.fn().mockResolvedValue({ categories: [] }),
      } as any)
      // refresh documents
      .mockResolvedValueOnce({
        ok: true,
        json: vi.fn().mockResolvedValue({
          documents: [
            {
              id: 'd1',
              created_at: new Date().toISOString(),
              cluster_id: 1,
              content: 'x',
              metadata: { filename: 'a.pdf', type: 'application/pdf', size: 1024 },
            },
          ],
        }),
      } as any)
      // refresh categories
      .mockResolvedValueOnce({
        ok: true,
        json: vi.fn().mockResolvedValue({
          categories: [{ id: 1, label: 'Assignments' }],
        }),
      } as any);

    // Make upload succeed immediately (no polling)
    (uploadDocument as any).mockResolvedValue({
      status: 'success',
      doc_id: 'd1',
    });

  });

  it('uploads a file, shows success toast, and refreshes file list', async () => {
    const { result } = renderHook(() => useFileManagement());
    await flush(); // let initial fetchFiles settle

    const file = new File(['hi'], 'a.pdf', { type: 'application/pdf' });

    await act(async () => {
      const list = { 0: file, length: 1, item: () => file } as unknown as FileList;
      await result.current.handleFileUpload(list);
      await flush(); // allow post-upload refresh to complete
    });

    // Uploader called with the file and user id
    expect(uploadDocument).toHaveBeenCalledWith(file, 'u1');

    // Success toast was emitted
    const messages = result.current.notifications.map((n) => n.message).join(' | ');
    expect(messages).toMatch(/uploaded successfully/i);

    // State refreshed from backend (now shows one file)
    expect(result.current.totalFilesCount).toBe(1);
    expect(result.current.uploadedFiles[0].name).toBe('a.pdf');
    expect(result.current.uploadedFiles[0].category).toBe('Assignments');
  });
});
