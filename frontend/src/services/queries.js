/**
 * React Query hooks for FDA CRL Explorer API.
 *
 * Provides hooks for:
 * - Fetching CRLs with filters, sorting, pagination
 * - Fetching single CRL details
 * - Fetching statistics
 * - Asking questions (Q&A mutation)
 * - Fetching Q&A history
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from './api';

// Query keys for cache management
export const queryKeys = {
  crls: (params) => ['crls', params],
  crl: (id) => ['crl', id],
  crlText: (id) => ['crlText', id],
  stats: (params) => ['stats', params],
  companies: (limit) => ['companies', limit],
  qa: (id) => ['qa', id],
  qaHistory: (limit) => ['qaHistory', limit],
};

/**
 * Fetch paginated list of CRLs with filtering and sorting.
 *
 * @param {Object} params - Query parameters
 * @param {string} [params.approval_status] - Filter by approval status
 * @param {string} [params.letter_year] - Filter by year
 * @param {string} [params.company_name] - Filter by company name
 * @param {string} [params.search_text] - Full-text search
 * @param {number} [params.limit=50] - Results per page
 * @param {number} [params.offset=0] - Pagination offset
 * @param {string} [params.sort_by='letter_date'] - Sort field
 * @param {string} [params.sort_order='DESC'] - Sort direction
 */
export function useCRLs(params = {}) {
  return useQuery({
    queryKey: queryKeys.crls(params),
    queryFn: async () => {
      const { data } = await api.get('/crls', { params });
      return data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    placeholderData: (previousData) => previousData, // Keep previous page while loading new one
  });
}

/**
 * Fetch single CRL by ID with AI summary.
 *
 * @param {string} id - CRL ID
 */
export function useCRL(id) {
  return useQuery({
    queryKey: queryKeys.crl(id),
    queryFn: async () => {
      const { data } = await api.get('/crls/detail', { params: { crl_id: id } });
      return data;
    },
    enabled: !!id, // Only fetch if ID is provided
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

/**
 * Fetch CRL with full letter text.
 *
 * @param {string} id - CRL ID
 */
export function useCRLText(id) {
  return useQuery({
    queryKey: queryKeys.crlText(id),
    queryFn: async () => {
      const { data } = await api.get('/crls/text', { params: { crl_id: id } });
      return data;
    },
    enabled: !!id,
    staleTime: 10 * 60 * 1000,
  });
}

/**
 * Fetch overall statistics (total CRLs, by status, by year).
 * Supports same filtering parameters as useCRLs.
 *
 * @param {Object} params - Filter parameters
 * @param {string} [params.approval_status] - Filter by approval status
 * @param {string} [params.letter_year] - Filter by year
 * @param {string} [params.company_name] - Filter by company name
 * @param {string} [params.search_text] - Full-text search
 */
export function useStats(params = {}) {
  return useQuery({
    queryKey: queryKeys.stats(params),
    queryFn: async () => {
      const { data } = await api.get('/stats/overview', { params });
      return data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes (shorter since filtered stats can change)
  });
}

/**
 * Fetch company statistics sorted by CRL count.
 *
 * @param {number} [limit=20] - Number of companies to fetch
 */
export function useCompanies(limit = 20) {
  return useQuery({
    queryKey: queryKeys.companies(limit),
    queryFn: async () => {
      const { data } = await api.get('/stats/companies', { params: { limit } });
      return data;
    },
    staleTime: 15 * 60 * 1000,
  });
}

/**
 * Ask a question using RAG-powered Q&A.
 *
 * @returns {Object} Mutation object with mutate function
 */
export function useAskQuestion() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ question, top_k = 5 }) => {
      const { data } = await api.post('/qa/ask', { question, top_k });
      return data;
    },
    onSuccess: () => {
      // Invalidate Q&A history to show new question
      queryClient.invalidateQueries({ queryKey: ['qaHistory'] });
    },
  });
}

/**
 * Fetch Q&A history.
 *
 * @param {number} [limit=10] - Number of Q&A pairs to fetch
 */
export function useQAHistory(limit = 10) {
  return useQuery({
    queryKey: queryKeys.qaHistory(limit),
    queryFn: async () => {
      const { data } = await api.get('/qa/history', { params: { limit } });
      return data;
    },
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

/**
 * Fetch health check status.
 */
export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      const { data } = await api.get('/health');
      return data;
    },
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 60 * 1000, // Refetch every minute
  });
}
