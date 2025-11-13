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

import { describe, it, expect, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithClient } from '../../test/utils';
import HomePage from '../HomePage';
import * as queries from '../../services/queries';

// Mock the queries module
vi.mock('../../services/queries', () => ({
  useStats: vi.fn(),
}));

describe('HomePage', () => {
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
    expect(screen.getByText('65%')).toBeInTheDocument(); // 800/1234 = 65%

    // Check Unapproved card
    expect(screen.getByText(/unapproved/i)).toBeInTheDocument();
    expect(screen.getByText('434')).toBeInTheDocument();
    expect(screen.getByText('35%')).toBeInTheDocument(); // 434/1234 = 35%
  });

  it('displays by year section when year data is available', () => {
    const mockStats = {
      total_crls: 530,
      by_status: {
        Approved: 300,
        Unapproved: 230,
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

    // Check section heading
    expect(screen.getByText(/crls by year/i)).toBeInTheDocument();

    // Check individual years (sorted in descending order)
    expect(screen.getByText('2023')).toBeInTheDocument();
    expect(screen.getByText('2022')).toBeInTheDocument();
    expect(screen.getByText('2021')).toBeInTheDocument();

    // Check counts
    expect(screen.getByText('150')).toBeInTheDocument();
    expect(screen.getByText('200')).toBeInTheDocument();
    expect(screen.getByText('180')).toBeInTheDocument();
  });

  it('does not display by year section when no year data', () => {
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

    renderWithClient(<HomePage />);

    expect(screen.queryByText(/crls by year/i)).not.toBeInTheDocument();
  });

  it('displays placeholder for CRL table', () => {
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

    renderWithClient(<HomePage />);

    expect(screen.getByText(/complete response letters/i)).toBeInTheDocument();
    expect(
      screen.getByText(/crl table and filters will be implemented in phase 9/i)
    ).toBeInTheDocument();
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

    // Should have two "0%" elements (one for Approved, one for Unapproved)
    expect(screen.getAllByText('0%')).toHaveLength(2);
  });
});
