import { supabase } from './client'

/**
 * Insert a document + embedding into the database
 * @param {string} content - Raw text/document content
 * @param {Array<number>} embedding - Vector embedding (e.g., from OpenAI)
 */
export async function insertDocument(content, embedding) {
    const { data, error } = await supabase
      .from('documents')
      .insert([{ content, embedding }])
    if (error) throw error
    return data
  }