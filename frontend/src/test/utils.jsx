/**
 * Testing utilities and helpers.
 *
 * Provides wrappers and utilities for testing React components with React Query.
 */

import { render } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

/**
 * Create a new QueryClient for testing with sensible defaults.
 */
export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false, // Don't retry failed queries in tests
        cacheTime: Infinity,
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
}

/**
 * Wrapper component that provides QueryClient to children.
 */
export function Wrapper({ children, queryClient }) {
  const client = queryClient || createTestQueryClient();
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

/**
 * Custom render function that includes QueryClientProvider.
 *
 * @param {React.ReactElement} ui - Component to render
 * @param {Object} options - Options including custom queryClient
 * @returns {Object} - React Testing Library render result
 */
export function renderWithClient(ui, { queryClient, ...options } = {}) {
  const client = queryClient || createTestQueryClient();

  return render(ui, {
    wrapper: ({ children }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    ),
    ...options,
  });
}

/**
 * Wait for a specific amount of time (for async operations).
 */
export const waitFor = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
