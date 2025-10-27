import { useState, useEffect, useCallback } from 'react';
import type { Category } from '../../CategoryEditing/types';
import { supabase } from '../../../../../supabase/client';

export const useCategoryManagement = (userId: string) => {
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch categories from API
  const fetchCategories = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Use environment variable for API URL (no hardcoding)
      const API_BASE_URL = import.meta.env.VITE_API_URL;
      
      if (!API_BASE_URL) {
        throw new Error('VITE_API_URL environment variable is not set');
      }
      
      // Send user_id as query parameter for GET request
      const url = new URL(`${API_BASE_URL}/categories`);
      url.searchParams.append('user_id', userId);
      
      console.log('Fetching categories for user:', userId);
      console.log('API URL:', url.toString());
      
      const response = await fetch(url.toString(), {
        method: 'GET'
      });
      
      console.log('Response status:', response.status);
      console.log('Response ok:', response.ok);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Error response:', errorText);
        throw new Error('Failed to fetch categories');
      }
      
      const data = await response.json();
      setCategories(data.categories || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch categories');
      console.error('Error fetching categories:', err);
    } finally {
      setLoading(false);
    }
  }, [userId]);

  // Create new category
  const createCategory = useCallback(async (name: string, color: string, type?: string) => {
    try {
      setLoading(true);
      setError(null);
      
      const API_BASE_URL = import.meta.env.VITE_API_URL;
      
      if (!API_BASE_URL) {
        throw new Error('VITE_API_URL environment variable is not set');
      }
      
      // Send data as form data
      const formData = new FormData();
      formData.append('user_id', userId);
      formData.append('label', name);
      formData.append('color', color);
      formData.append('type', type || '');
      formData.append('user_created', 'true');
      
      const response = await fetch(`${API_BASE_URL}/categories`, {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        throw new Error('Failed to create category');
      }
      
      const newCategory = await response.json();
      setCategories(prev => [...prev, newCategory]);
      return newCategory;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create category');
      console.error('Error creating category:', err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [userId]);

  // Update category
  const updateCategory = useCallback(async (id: number, name: string, color: string, type?: string) => {
    try {
      setLoading(true);
      setError(null);
      
      const API_BASE_URL = import.meta.env.VITE_API_URL;
      
      if (!API_BASE_URL) {
        throw new Error('VITE_API_URL environment variable is not set');
      }
      
      // Send data as form data
      const formData = new FormData();
      formData.append('label', name);
      formData.append('color', color);
      formData.append('type', type || '');
      
      const response = await fetch(`${API_BASE_URL}/categories/${id}`, {
        method: 'PUT',
        body: formData
      });
      
      if (!response.ok) {
        throw new Error('Failed to update category');
      }
      
      const updatedCategory = await response.json();
      setCategories(prev => 
        prev.map(cat => cat.id === id ? updatedCategory : cat)
      );
      return updatedCategory;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update category');
      console.error('Error updating category:', err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  // Delete category
  const deleteCategory = useCallback(async (id: number) => {
    try {
      setLoading(true);
      setError(null);
      
      const API_BASE_URL = import.meta.env.VITE_API_URL;
      
      if (!API_BASE_URL) {
        throw new Error('VITE_API_URL environment variable is not set');
      }
      
      // Send data as form data
      const formData = new FormData();
      formData.append('user_id', userId);
      
      const response = await fetch(`${API_BASE_URL}/categories/${id}`, {
        method: 'DELETE',
        body: formData
      });
      
      if (!response.ok) {
        throw new Error('Failed to delete category');
      }
      
      setCategories(prev => prev.filter(cat => cat.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete category');
      console.error('Error deleting category:', err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [userId]);

  // Change file category
  const changeFileCategory = useCallback(async (
    fileId: string, 
    categoryId: number, 
    categoryName: string, 
    onSuccess?: () => void
  ) => {
    try {
      setLoading(true);
      setError(null);
      
      console.log('Changing file category:', { 
        fileId, 
        categoryId, 
        categoryName
      });
      
      // Get current user
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) {
        throw new Error('User not authenticated');
      }

      // Update the document's cluster_id in Supabase
      const { error: updateError } = await supabase
        .from('documents')
        .update({ 
          cluster_id: categoryId
        })
        .eq('id', fileId)
        .eq('metadata->>user_id', user.id);

      if (updateError) {
        console.error('Supabase error:', updateError);
        throw new Error(`Failed to change file category: ${updateError.message}`);
      }

      console.log('Category changed successfully via Supabase');
      
      // Call success callback to refresh files list
      if (onSuccess) {
        onSuccess();
      }
      
      return { success: true, fileId, categoryId, categoryName };
      
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to change file category';
      setError(errorMessage);
      console.error('Error changing file category:', err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  // Initialize categories on mount
  useEffect(() => {
    if (userId) {
      fetchCategories();
    } else {
      // If no user ID, create some default categories for testing
      const defaultCategories: Category[] = [
        { id: 1, label: 'Academic Work', color: '#3B82F6', user_created: false, type: 'Academic' },
        { id: 2, label: 'Course Materials', color: '#10B981', user_created: false, type: 'Educational' },
        { id: 3, label: 'Research Papers', color: '#8B5CF6', user_created: false, type: 'Research' },
        { id: 4, label: 'Science & Tech', color: '#6366F1', user_created: false, type: 'Technical' },
        { id: 5, label: 'Mathematics', color: '#F59E0B', user_created: false, type: 'Academic' },
        { id: 6, label: 'Business & Finance', color: '#059669', user_created: false, type: 'Business' },
        { id: 7, label: 'Language & Arts', color: '#EC4899', user_created: false, type: 'Creative' },
        { id: 8, label: 'Health & Medicine', color: '#EF4444', user_created: false, type: 'Medical' },
        { id: 9, label: 'Social Sciences', color: '#06B6D4', user_created: false, type: 'Social' },
        { id: 10, label: 'General Documents', color: '#6B7280', user_created: false, type: 'General' }
      ];
      setCategories(defaultCategories);
    }
  }, [userId, fetchCategories]);

  return {
    categories,
    loading,
    error,
    fetchCategories,
    createCategory,
    updateCategory,
    deleteCategory,
    changeFileCategory,
  };
};
