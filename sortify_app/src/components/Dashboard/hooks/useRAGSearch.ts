import { useState, useCallback } from 'react';
import { searchDocuments, type SearchResult } from '../../../api/sorter';
import { useUserProfile } from './useUserProfile';

interface RAGSearchState {
  isSearching: boolean;
  searchResult: SearchResult | null;
  error: string | null;
}

export const useRAGSearch = () => {
  const { userProfile } = useUserProfile();
  const [state, setState] = useState<RAGSearchState>({
    isSearching: false,
    searchResult: null,
    error: null
  });

  const performRAGSearch = useCallback(async (query: string, topK: number = 5) => {
    console.log('🔍 RAG Search triggered with query:', query);
    console.log('👤 User profile:', userProfile);

    if (!query.trim()) {
      console.log('❌ Empty query, aborting');
      setState({ isSearching: false, searchResult: null, error: null });
      return;
    }

    if (!userProfile?.id) {
      console.log('❌ User not authenticated');
      setState({
        isSearching: false,
        searchResult: null,
        error: 'User not authenticated'
      });
      return;
    }

    console.log('⏳ Starting RAG search...');
    setState({ isSearching: true, searchResult: null, error: null });

    try {
      console.log('📡 Calling searchDocuments API...');
      const result = await searchDocuments(query, userProfile.id, topK);
      console.log('✅ RAG search successful:', result);
      setState({
        isSearching: false,
        searchResult: result,
        error: null
      });
    } catch (err) {
      console.error('❌ RAG search failed:', err);
      setState({
        isSearching: false,
        searchResult: null,
        error: err instanceof Error ? err.message : 'Search failed'
      });
    }
  }, [userProfile]);

  const clearSearch = useCallback(() => {
    setState({ isSearching: false, searchResult: null, error: null });
  }, []);

  return {
    isSearching: state.isSearching,
    searchResult: state.searchResult,
    searchError: state.error,
    performRAGSearch,
    clearSearch
  };
};
