// src/api/sorter.ts

export type SortResult = {
    success: boolean
    doc_id: string
    category_id?: number
    assignment_type?: string
    processing_time_seconds?: number
    timestamp?: string
  }
  
  export async function sortDocument(doc: { id: string; content: string; user_id: string }): Promise<SortResult> {
    const res = await fetch("http://127.0.0.1:8000/sort", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(doc),
    })
  
    if (!res.ok) throw new Error("Failed to sort document")
    return res.json()
  }
  