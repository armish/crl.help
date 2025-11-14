/**
 * Tests for FilterPanel component.
 *
 * Tests:
 * - Renders all filter inputs
 * - Search text input updates filter
 * - Clear filters button works
 * - Active filters indicator displays correctly
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { renderWithClient } from '../../test/utils';
import FilterPanel from '../FilterPanel';
import * as queries from '../../services/queries';
import useFilterStore from '../../store/filterStore';

// Mock the queries module
vi.mock('../../services/queries', () => ({
  useStats: vi.fn(),
  useCompanies: vi.fn(),
}));

describe('FilterPanel', () => {
  beforeEach(() => {
    // Reset filter store before each test
    useFilterStore.getState().clearFilters();

    // Default mock implementations
    queries.useStats.mockReturnValue({
      data: {
        by_year: {
          '2023': 150,
          '2022': 200,
          '2021': 180,
        },
      },
      isLoading: false,
      error: null,
    });

    queries.useCompanies.mockReturnValue({
      data: {
        companies: [
          { company_name: 'Pfizer Inc', crl_count: 10 },
          { company_name: 'Moderna Inc', crl_count: 8 },
          { company_name: 'Johnson & Johnson', crl_count: 7 },
          { company_name: 'AstraZeneca', crl_count: 5 },
        ],
      },
      isLoading: false,
      error: null,
    });
  });

  it('renders filter heading', () => {
    renderWithClient(<FilterPanel />);

    expect(screen.getByText('Filters')).toBeInTheDocument();
  });

  it('renders all new filter dropdowns', () => {
    renderWithClient(<FilterPanel />);

    // Check for new filter dropdowns
    expect(screen.getByText(/therapeutic category/i)).toBeInTheDocument();
    expect(screen.getByText(/deficiency reason/i)).toBeInTheDocument();
  });

  it('renders multi-select dropdowns for filters', () => {
    renderWithClient(<FilterPanel />);

    // Multi-select dropdowns render as buttons with the label
    expect(screen.getByText(/approval status/i)).toBeInTheDocument();
    expect(screen.getByText(/application type/i)).toBeInTheDocument();
    expect(screen.getByText(/year/i)).toBeInTheDocument();
    expect(screen.getByText(/company name/i)).toBeInTheDocument();
  });

  it('clear filters button appears when filters are active', () => {
    // Set a filter programmatically before rendering
    act(() => {
      useFilterStore.getState().setFilter('approval_status', ['Approved']);
    });

    renderWithClient(<FilterPanel />);

    expect(screen.getByText('Clear all')).toBeInTheDocument();
  });

  it('clear filters button does not appear when no filters active', () => {
    renderWithClient(<FilterPanel />);

    expect(screen.queryByText('Clear all')).not.toBeInTheDocument();
  });

  it('clear filters button clears all filters', () => {
    // Set filters programmatically
    act(() => {
      useFilterStore.getState().setFilter('approval_status', ['Approved']);
      useFilterStore.getState().setFilter('letter_year', ['2023']);
    });

    renderWithClient(<FilterPanel />);

    const clearButton = screen.getByText('Clear all');
    fireEvent.click(clearButton);

    const state = useFilterStore.getState();
    expect(state.filters.search_text).toBe('');
    expect(state.filters.approval_status).toEqual([]);
    expect(state.filters.letter_year).toEqual([]);
    expect(state.filters.application_type).toEqual([]);
    expect(state.filters.letter_type).toEqual([]);
    expect(state.filters.therapeutic_category).toEqual([]);
    expect(state.filters.deficiency_reason).toEqual([]);
    expect(state.filters.company_name).toEqual([]);
  });

  it('handles empty stats data gracefully', () => {
    queries.useStats.mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
    });

    renderWithClient(<FilterPanel />);

    // Should still render without errors
    expect(screen.getByText('Filters')).toBeInTheDocument();
  });

  it('handles empty companies data gracefully', () => {
    queries.useCompanies.mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
    });

    renderWithClient(<FilterPanel />);

    // Should still render without errors
    expect(screen.getByText('Filters')).toBeInTheDocument();
  });
});
