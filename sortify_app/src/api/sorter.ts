// src/api/sorter.ts

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export type SortResult = {
    success: boolean
    doc_id: string
    category_id?: number
    assignment_type?: string
    processing_time_seconds?: number
    timestamp?: string
}

export type UploadResult = {
    filename: string
    status: string
    message: string
    doc_id?: string
    task_id?: string
    timestamp: string
}

export type SearchResult = {
    answer: string
    sources: string[]
    chunks_used: number
    response_time: number
}

export type TaskStatus = {
    task_id: string
    doc_id: string
    status: string
    created_at: string
    category_id?: number
    category_name?: string
    completed_at?: string
    error?: string
}

export async function uploadDocument(file: File, userId: string): Promise<UploadResult> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_id', userId);

    const response = await fetch(`${API_BASE_URL}/upload`, {
        method: 'POST',
        body: formData,
    });

    if (!response.ok) {
        throw new Error('Failed to upload file');
    }

    return response.json();
}

export async function searchDocuments(question: string, userId: string, topK: number = 5): Promise<SearchResult> {
    const formData = new FormData();
    formData.append('question', question);
    formData.append('user_id', userId);
    formData.append('top_k', topK.toString());

    const response = await fetch(`${API_BASE_URL}/ask_supabase`, {
        method: 'POST',
        body: formData,
    });

    if (!response.ok) {
        throw new Error('Failed to search documents');
    }

    return response.json();
}

export async function getTaskStatus(taskId: string): Promise<TaskStatus> {
    const response = await fetch(`${API_BASE_URL}/upload/task-status/${taskId}`);
    
    if (!response.ok) {
        throw new Error('Failed to get task status');
    }

    return response.json();
}

export async function getFileCategory(docId: string) {
    const response = await fetch(`${API_BASE_URL}/upload/file-category/${docId}`);
    
    if (!response.ok) {
        throw new Error('Failed to get file category');
    }

    return response.json();
}

// Legacy function for backward compatibility
export async function sortDocument(doc: { id: string; content: string; user_id: string }): Promise<SortResult> {
    const res = await fetch(`${API_BASE_URL}/sort`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(doc),
    })

    if (!res.ok) throw new Error("Failed to sort document")
    return res.json()
}
  