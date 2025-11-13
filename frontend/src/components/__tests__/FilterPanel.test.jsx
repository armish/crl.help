/**
 * Tests for FilterPanel component.
 *
 * Tests:
 * - Renders all filter inputs
 * - Search text input updates filter
 * - Approval status dropdown updates filter
 * - Year dropdown populates from stats
 * - Company autocomplete shows suggestions
 * - Company autocomplete selects value
 * - Clear filters button works
 * - Active filters indicator displays correctly
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
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
      data: ['Pfizer Inc', 'Moderna Inc', 'Johnson & Johnson', 'AstraZeneca'],
      isLoading: false,
      error: null,
    });
  });

  it('renders all filter inputs', () => {
    renderWithClient(<FilterPanel />);

    expect(screen.getByLabelText(/search/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/approval status/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/year/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/company name/i)).toBeInTheDocument();
  });

  it('renders filter heading', () => {
    renderWithClient(<FilterPanel />);

    expect(screen.getByText('Filters')).toBeInTheDocument();
  });

  it('search text input updates filter', () => {
    renderWithClient(<FilterPanel />);

    const searchInput = screen.getByLabelText(/search/i);
    fireEvent.change(searchInput, { target: { value: 'test search' } });

    expect(useFilterStore.getState().filters.search_text).toBe('test search');
  });

  it('approval status dropdown updates filter', () => {
    renderWithClient(<FilterPanel />);

    const statusSelect = screen.getByLabelText(/approval status/i);
    fireEvent.change(statusSelect, { target: { value: 'Approved' } });

    expect(useFilterStore.getState().filters.approval_status).toBe('Approved');
  });

  it('approval status dropdown has correct options', () => {
    renderWithClient(<FilterPanel />);

    const statusSelect = screen.getByLabelText(/approval status/i);
    const options = statusSelect.querySelectorAll('option');

    expect(options).toHaveLength(3);
    expect(options[0].value).toBe('');
    expect(options[1].value).toBe('Approved');
    expect(options[2].value).toBe('Unapproved');
  });

  it('year dropdown populates from stats', () => {
    renderWithClient(<FilterPanel />);

    const yearSelect = screen.getByLabelText(/year/i);
    const options = yearSelect.querySelectorAll('option');

    // Should have "All Years" + 3 years from mock data
    expect(options).toHaveLength(4);
    expect(options[0].value).toBe(''); // All Years
    expect(options[1].value).toBe('2023');
    expect(options[2].value).toBe('2022');
    expect(options[3].value).toBe('2021');
  });

  it('year dropdown updates filter', () => {
    renderWithClient(<FilterPanel />);

    const yearSelect = screen.getByLabelText(/year/i);
    fireEvent.change(yearSelect, { target: { value: '2023' } });

    expect(useFilterStore.getState().filters.letter_year).toBe('2023');
  });

  it('company name input accepts text', () => {
    renderWithClient(<FilterPanel />);

    const companyInput = screen.getByLabelText(/company name/i);
    fireEvent.change(companyInput, { target: { value: 'Pf' } });

    expect(companyInput.value).toBe('Pf');
  });

  it('company autocomplete shows suggestions when typing 2+ characters', async () => {
    renderWithClient(<FilterPanel />);

    const companyInput = screen.getByLabelText(/company name/i);
    fireEvent.change(companyInput, { target: { value: 'Pf' } });
    fireEvent.focus(companyInput);

    await waitFor(() => {
      expect(screen.getByText('Pfizer Inc')).toBeInTheDocument();
    });
  });

  it('company autocomplete filters suggestions based on input', async () => {
    renderWithClient(<FilterPanel />);

    const companyInput = screen.getByLabelText(/company name/i);
    fireEvent.change(companyInput, { target: { value: 'mod' } });
    fireEvent.focus(companyInput);

    await waitFor(() => {
      expect(screen.getByText('Moderna Inc')).toBeInTheDocument();
      expect(screen.queryByText('Pfizer Inc')).not.toBeInTheDocument();
    });
  });

  it('company autocomplete does not show for single character', () => {
    renderWithClient(<FilterPanel />);

    const companyInput = screen.getByLabelText(/company name/i);
    fireEvent.change(companyInput, { target: { value: 'P' } });
    fireEvent.focus(companyInput);

    expect(screen.queryByText('Pfizer Inc')).not.toBeInTheDocument();
  });

  it('company autocomplete selects value on click', async () => {
    renderWithClient(<FilterPanel />);

    const companyInput = screen.getByLabelText(/company name/i);
    fireEvent.change(companyInput, { target: { value: 'Pf' } });
    fireEvent.focus(companyInput);

    await waitFor(() => {
      const suggestion = screen.getByText('Pfizer Inc');
      fireEvent.click(suggestion);
    });

    await waitFor(() => {
      expect(useFilterStore.getState().filters.company_name).toBe('Pfizer Inc');
    });
  });

  it('shows "no companies found" message when no matches', async () => {
    renderWithClient(<FilterPanel />);

    const companyInput = screen.getByLabelText(/company name/i);
    fireEvent.change(companyInput, { target: { value: 'xyz123' } });
    fireEvent.focus(companyInput);

    await waitFor(() => {
      expect(screen.getByText(/no companies found/i)).toBeInTheDocument();
    });
  });

  it('clear filters button appears when filters are active', () => {
    renderWithClient(<FilterPanel />);

    // Set a filter
    const searchInput = screen.getByLabelText(/search/i);
    fireEvent.change(searchInput, { target: { value: 'test' } });

    expect(screen.getByText('Clear all')).toBeInTheDocument();
  });

  it('clear filters button does not appear when no filters active', () => {
    renderWithClient(<FilterPanel />);

    expect(screen.queryByText('Clear all')).not.toBeInTheDocument();
  });

  it('clear filters button clears all filters', () => {
    renderWithClient(<FilterPanel />);

    // Set multiple filters
    const searchInput = screen.getByLabelText(/search/i);
    const statusSelect = screen.getByLabelText(/approval status/i);

    fireEvent.change(searchInput, { target: { value: 'test' } });
    fireEvent.change(statusSelect, { target: { value: 'Approved' } });

    const clearButton = screen.getByText('Clear all');
    fireEvent.click(clearButton);

    const state = useFilterStore.getState();
    expect(state.filters.search_text).toBe('');
    expect(state.filters.approval_status).toBe('');
    expect(state.filters.letter_year).toBe('');
    expect(state.filters.company_name).toBe('');
  });

  it('shows active filters indicator with correct text', () => {
    renderWithClient(<FilterPanel />);

    const searchInput = screen.getByLabelText(/search/i);
    const statusSelect = screen.getByLabelText(/approval status/i);

    fireEvent.change(searchInput, { target: { value: 'aspirin' } });
    fireEvent.change(statusSelect, { target: { value: 'Approved' } });

    expect(screen.getByText(/active filters:/i)).toBeInTheDocument();
    expect(screen.getByText(/Search: "aspirin"/)).toBeInTheDocument();
    expect(screen.getByText(/Status: Approved/)).toBeInTheDocument();
  });

  it('handles empty stats data gracefully', () => {
    queries.useStats.mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
    });

    renderWithClient(<FilterPanel />);

    const yearSelect = screen.getByLabelText(/year/i);
    const options = yearSelect.querySelectorAll('option');

    // Should only have "All Years" option
    expect(options).toHaveLength(1);
    expect(options[0].value).toBe('');
  });

  it('handles empty companies data gracefully', () => {
    queries.useCompanies.mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
    });

    renderWithClient(<FilterPanel />);

    const companyInput = screen.getByLabelText(/company name/i);
    fireEvent.change(companyInput, { target: { value: 'test' } });
    fireEvent.focus(companyInput);

    // Should show "no companies found"
    expect(screen.queryByText('Pfizer Inc')).not.toBeInTheDocument();
  });

  it('resets pagination when filter changes', () => {
    renderWithClient(<FilterPanel />);

    // Set pagination to page 2
    useFilterStore.getState().nextPage();
    expect(useFilterStore.getState().pagination.offset).toBe(50);

    // Change a filter
    const searchInput = screen.getByLabelText(/search/i);
    fireEvent.change(searchInput, { target: { value: 'test' } });

    // Pagination should reset
    expect(useFilterStore.getState().pagination.offset).toBe(0);
  });
});
