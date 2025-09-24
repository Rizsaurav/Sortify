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

/**
 * Search for similar documents using pgvector similarity
 * @param {Array<number>} queryEmbedding - Embedding of the query
 * @param {number} matchCount - How many results to return (default: 5)
 */
export async function searchDocuments(queryEmbedding, matchCount = 5) {
    const { data, error } = await supabase.rpc('match_documents', {
      query_embedding: queryEmbedding,
      match_count: matchCount,
    })
    if (error) throw error
    return data
  }

/**
 * Update an existing document (content + embedding)
 */
export async function updateDocument(id, content, embedding) {
    const { data, error } = await supabase
      .from('documents')
      .update({ content, embedding })
      .eq('id', id)
    if (error) throw error
    return data
  }

  /**
 * Fetch a single document by ID
 */
export async function getDocumentById(id) {
    const { data, error } = await supabase
      .from('documents')
      .select('*')
      .eq('id', id)
      .single()
    if (error) throw error
    return data
  }