/**
 * Tests for HomePage component.
 *
 * Tests:
 * - Loading state display
 * - Error state display
 * - Statistics display with data
 * - By year section rendering
 * - Placeholder for CRL table
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithClient } from '../../test/utils';
import HomePage from '../HomePage';
import * as queries from '../../services/queries';

// Mock the queries module
vi.mock('../../services/queries', () => ({
  useStats: vi.fn(),
  useCompanies: vi.fn(),
  useCRLs: vi.fn(),
}));

// Mock the filterStore module
vi.mock('../../store/filterStore', () => ({
  default: vi.fn(() => ({
    filters: {
      approval_status: [],
      letter_year: [],
      letter_type: [],
      company_name: [],
      search_text: '',
    },
    sort: {
      sort_by: 'letter_date',
      sort_order: 'DESC',
    },
    pagination: {
      limit: 10,
      offset: 0,
    },
    setFilter: vi.fn(),
    clearFilters: vi.fn(),
    setSort: vi.fn(),
    setPagination: vi.fn(),
  })),
  useQueryParams: vi.fn(() => ({
    sort_by: 'letter_date',
    sort_order: 'DESC',
    limit: 10,
    offset: 0,
  })),
}));

describe('HomePage', () => {
  beforeEach(() => {
    // Default mock for useCompanies
    queries.useCompanies.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    });

    // Default mock for useCRLs
    queries.useCRLs.mockReturnValue({
      data: { items: [], total: 0 },
      isLoading: false,
      error: null,
    });
  });

  it('shows loading state initially', () => {
    queries.useStats.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    renderWithClient(<HomePage />);

    expect(screen.getByText(/loading statistics/i)).toBeInTheDocument();
  });

  it('shows error state when stats fail to load', () => {
    const errorMessage = 'Failed to fetch statistics';
    queries.useStats.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: { message: errorMessage },
    });

    renderWithClient(<HomePage />);

    expect(screen.getByText(/error loading statistics/i)).toBeInTheDocument();
    expect(screen.getByText(errorMessage)).toBeInTheDocument();
  });

  it('displays statistics cards when data is loaded', () => {
    const mockStats = {
      total_crls: 1234,
      by_status: {
        Approved: 800,
        Unapproved: 434,
      },
      by_year: {
        '2023': 150,
        '2022': 200,
        '2021': 180,
      },
    };

    queries.useStats.mockReturnValue({
      data: mockStats,
      isLoading: false,
      error: null,
    });

    renderWithClient(<HomePage />);

    // Check Total CRLs card
    expect(screen.getByText(/total crls/i)).toBeInTheDocument();
    expect(screen.getByText('1,234')).toBeInTheDocument();

    // Check Approved card
    const approvedElements = screen.getAllByText(/approved/i);
    expect(approvedElements.length).toBeGreaterThan(0);
    expect(screen.getByText('800')).toBeInTheDocument();
    expect(screen.getByText('65% of total')).toBeInTheDocument(); // 800/1234 = 65%

    // Check Unapproved card
    const unapprovedElements = screen.getAllByText(/unapproved/i);
    expect(unapprovedElements.length).toBeGreaterThan(0);
    expect(screen.getByText('434')).toBeInTheDocument();
    expect(screen.getByText('35% of total')).toBeInTheDocument(); // 434/1234 = 35%
  });

  it('displays by year section when year data is available', () => {
    const mockStats = {
      total_crls: 530,
      by_status: {
        Approved: 300,
        Unapproved: 230,
      },
      by_year_and_status: {
        '2023': { Approved: 100, Unapproved: 50 },
        '2022': { Approved: 120, Unapproved: 80 },
        '2021': { Approved: 80, Unapproved: 100 },
      },
    };

    queries.useStats.mockReturnValue({
      data: mockStats,
      isLoading: false,
      error: null,
    });

    renderWithClient(<HomePage />);

    // Check section heading for the chart
    expect(screen.getByText(/crls by year/i)).toBeInTheDocument();

    // Year data is now rendered inside Recharts component
    // We can verify the chart container exists
    const chartContainers = document.querySelectorAll('.recharts-responsive-container');
    expect(chartContainers.length).toBeGreaterThan(0);
  });

  it('does not display by year section when no year data', () => {
    const mockStats = {
      total_crls: 100,
      by_status: {
        Approved: 60,
        Unapproved: 40,
      },
      by_year_and_status: {},
    };

    queries.useStats.mockReturnValue({
      data: mockStats,
      isLoading: false,
      error: null,
    });

    renderWithClient(<HomePage />);

    expect(screen.queryByText(/crls by year/i)).not.toBeInTheDocument();
  });

  it('displays CRL table section', () => {
    const mockStats = {
      total_crls: 100,
      by_status: {
        Approved: 60,
        Unapproved: 40,
      },
      by_year: {},
    };

    queries.useStats.mockReturnValue({
      data: mockStats,
      isLoading: false,
      error: null,
    });

    queries.useCRLs.mockReturnValue({
      data: { items: [], total: 0 },
      isLoading: false,
      error: null,
    });

    renderWithClient(<HomePage />);

    expect(screen.getByText(/complete response letters/i)).toBeInTheDocument();
    // Table should render with "No CRLs found" message when data is empty
    expect(screen.getByText(/no crls found/i)).toBeInTheDocument();
  });

  it('handles zero stats gracefully', () => {
    const mockStats = {
      total_crls: 0,
      by_status: {
        Approved: 0,
        Unapproved: 0,
      },
      by_year: {},
    };

    queries.useStats.mockReturnValue({
      data: mockStats,
      isLoading: false,
      error: null,
    });

    renderWithClient(<HomePage />);

    // There are multiple "0" text elements (one for each card)
    const zeroElements = screen.getAllByText('0');
    expect(zeroElements.length).toBeGreaterThan(0);

    // Should have two "0% of total" elements (one for Approved, one for Unapproved)
    expect(screen.getAllByText('0% of total')).toHaveLength(2);
  });
});
