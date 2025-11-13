/**
 * Tests for React Query hooks.
 *
 * Tests:
 * - useStats hook
 * - useCRLs hook with parameters
 * - useCRL hook
 * - useAskQuestion mutation
 * - Query key functions
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useStats, useCRLs, useCRL, useAskQuestion, queryKeys } from '../queries';
import api from '../api';

// Mock the API client
vi.mock('../api');

// Helper to create wrapper with QueryClient
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
    logger: {
      log: console.log,
      warn: console.warn,
      error: () => {}, // Silence errors in tests
    },
  });

  return ({ children }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe('Query Keys', () => {
  it('generates correct CRLs query key', () => {
    const params = { limit: 10, offset: 0, approval_status: 'Approved' };
    expect(queryKeys.crls(params)).toEqual(['crls', params]);
  });

  it('generates correct CRL query key', () => {
    expect(queryKeys.crl(123)).toEqual(['crl', 123]);
  });

  it('generates correct stats query key', () => {
    expect(queryKeys.stats()).toEqual(['stats']);
  });

  it('generates correct companies query key', () => {
    expect(queryKeys.companies(10)).toEqual(['companies', 10]);
  });
});

describe('useStats', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches statistics successfully', async () => {
    const mockStats = {
      total_crls: 100,
      by_status: {
        Approved: 60,
        Unapproved: 40,
      },
      by_year: {
        '2023': 50,
        '2022': 50,
      },
    };

    api.get.mockResolvedValueOnce({ data: mockStats });

    const { result } = renderHook(() => useStats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(api.get).toHaveBeenCalledWith('/stats/overview');
    expect(result.current.data).toEqual(mockStats);
  });

  it('handles error when fetching statistics', async () => {
    const errorMessage = 'Network error';
    api.get.mockRejectedValueOnce(new Error(errorMessage));

    const { result } = renderHook(() => useStats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBeTruthy();
  });
});

describe('useCRLs', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches CRLs with parameters', async () => {
    const mockCRLs = {
      items: [
        { id: 1, application_number: 'NDA123', company_name: 'Test Co' },
        { id: 2, application_number: 'NDA456', company_name: 'Test Co 2' },
      ],
      total: 2,
      limit: 50,
      offset: 0,
    };

    api.get.mockResolvedValueOnce({ data: mockCRLs });

    const params = { limit: 50, offset: 0, approval_status: 'Approved' };

    const { result } = renderHook(() => useCRLs(params), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(api.get).toHaveBeenCalledWith('/crls', { params });
    expect(result.current.data).toEqual(mockCRLs);
  });

  it('handles empty parameters', async () => {
    const mockCRLs = {
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
    };

    api.get.mockResolvedValueOnce({ data: mockCRLs });

    const { result } = renderHook(() => useCRLs(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(api.get).toHaveBeenCalledWith('/crls', { params: {} });
  });
});

describe('useCRL', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches single CRL by ID', async () => {
    const mockCRL = {
      id: 1,
      application_number: 'NDA123',
      company_name: 'Test Co',
      summary: 'Test summary',
    };

    api.get.mockResolvedValueOnce({ data: mockCRL });

    const { result } = renderHook(() => useCRL(1), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(api.get).toHaveBeenCalledWith('/crls/1');
    expect(result.current.data).toEqual(mockCRL);
  });

  it('does not fetch when ID is null', () => {
    const { result } = renderHook(() => useCRL(null), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe('idle');
    expect(api.get).not.toHaveBeenCalled();
  });
});

describe('useAskQuestion', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('submits question successfully', async () => {
    const mockResponse = {
      question: 'What is the most common deficiency?',
      answer: 'The most common deficiency is...',
      sources: [
        { crl_id: 1, application_number: 'NDA123' },
      ],
    };

    api.post.mockResolvedValueOnce({ data: mockResponse });

    const { result } = renderHook(() => useAskQuestion(), {
      wrapper: createWrapper(),
    });

    const questionData = {
      question: 'What is the most common deficiency?',
      top_k: 5,
    };

    result.current.mutate(questionData);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(api.post).toHaveBeenCalledWith('/qa/ask', questionData);
    expect(result.current.data).toEqual(mockResponse);
  });

  it('handles question submission error', async () => {
    const errorMessage = 'Invalid question';
    api.post.mockRejectedValueOnce(new Error(errorMessage));

    const { result } = renderHook(() => useAskQuestion(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      question: 'What?',
      top_k: 5,
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBeTruthy();
  });
});
