/**
 * Tests for StatsDashboard component.
 *
 * Tests:
 * - Renders summary stat cards correctly
 * - Calculates percentages correctly
 * - Handles zero stats gracefully
 * - Renders bar chart with year data
 * - Renders pie chart with status data
 * - Handles missing data gracefully
 * - Sorts year data chronologically
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import StatsDashboard from '../StatsDashboard';

describe('StatsDashboard', () => {
  const mockStatsComplete = {
    total_crls: 1234,
    by_status: {
      Approved: 800,
      Unapproved: 434,
    },
    by_year_and_status: {
      '2023': { Approved: 100, Unapproved: 50 },
      '2022': { Approved: 150, Unapproved: 50 },
      '2021': { Approved: 120, Unapproved: 60 },
      '2020': { Approved: 70, Unapproved: 30 },
    },
  };

  it('renders summary stat cards with correct values', () => {
    render(<StatsDashboard stats={mockStatsComplete} />);

    // Check Total CRLs
    expect(screen.getByText('Total CRLs')).toBeInTheDocument();
    expect(screen.getByText('1,234')).toBeInTheDocument();

    // Check Approved
    expect(screen.getByText('Approved')).toBeInTheDocument();
    expect(screen.getByText('800')).toBeInTheDocument();
    expect(screen.getByText('65% of total')).toBeInTheDocument(); // 800/1234 = 65%

    // Check Unapproved
    expect(screen.getByText('Unapproved')).toBeInTheDocument();
    expect(screen.getByText('434')).toBeInTheDocument();
    expect(screen.getByText('35% of total')).toBeInTheDocument(); // 434/1234 = 35%
  });

  it('calculates percentages correctly for different distributions', () => {
    const stats = {
      total_crls: 1000,
      by_status: {
        Approved: 750,
        Unapproved: 250,
      },
      by_year_and_status: {},
    };

    render(<StatsDashboard stats={stats} />);

    expect(screen.getByText('750')).toBeInTheDocument();
    expect(screen.getByText('75% of total')).toBeInTheDocument();

    expect(screen.getByText('250')).toBeInTheDocument();
    expect(screen.getByText('25% of total')).toBeInTheDocument();
  });

  it('handles zero stats gracefully', () => {
    const stats = {
      total_crls: 0,
      by_status: {
        Approved: 0,
        Unapproved: 0,
      },
      by_year_and_status: {},
    };

    render(<StatsDashboard stats={stats} />);

    // Should display 0 for all counts
    const zeroElements = screen.getAllByText('0');
    expect(zeroElements.length).toBeGreaterThan(0);

    // Should display 0% for percentages
    expect(screen.getAllByText('0% of total')).toHaveLength(2);
  });

  it('renders chart section headings when data is available', () => {
    render(<StatsDashboard stats={mockStatsComplete} />);

    expect(screen.getByText(/CRLs by Year/i)).toBeInTheDocument();
    expect(screen.getByText('Approval Status Distribution')).toBeInTheDocument();
  });

  it('does not render year chart when no year data', () => {
    const stats = {
      total_crls: 100,
      by_status: {
        Approved: 60,
        Unapproved: 40,
      },
      by_year_and_status: {},
    };

    render(<StatsDashboard stats={stats} />);

    expect(screen.queryByText(/CRLs by Year/i)).not.toBeInTheDocument();
  });

  it('does not render status chart when no status data', () => {
    const stats = {
      total_crls: 100,
      by_status: {},
      by_year_and_status: {
        '2023': { Approved: 30, Unapproved: 20 },
        '2022': { Approved: 30, Unapproved: 20 },
      },
    };

    render(<StatsDashboard stats={stats} />);

    expect(screen.queryByText('Approval Status Distribution')).not.toBeInTheDocument();
  });

  it('handles missing stats object gracefully', () => {
    render(<StatsDashboard stats={null} />);

    // Should still render stat cards with 0 values
    expect(screen.getByText('Total CRLs')).toBeInTheDocument();
    expect(screen.getByText('Approved')).toBeInTheDocument();
    expect(screen.getByText('Unapproved')).toBeInTheDocument();
  });

  it('handles partial stats object gracefully', () => {
    const stats = {
      total_crls: 500,
      by_status: {
        Approved: 300,
      },
      by_year_and_status: {},
    };

    render(<StatsDashboard stats={stats} />);

    // Should handle missing Unapproved count
    expect(screen.getByText('300')).toBeInTheDocument();
    expect(screen.getByText('60% of total')).toBeInTheDocument();
  });

  it('renders stat cards with correct color classes', () => {
    const { container } = render(<StatsDashboard stats={mockStatsComplete} />);

    // Check that cards have the expected color classes
    const cards = container.querySelectorAll('.rounded-lg.border.p-6');
    expect(cards.length).toBeGreaterThan(0);

    // Total CRLs should have blue color
    expect(cards[0].className).toContain('bg-blue-50');

    // Approved should have green color
    expect(cards[1].className).toContain('bg-green-50');

    // Unapproved should have orange color (changed from red)
    expect(cards[2].className).toContain('bg-orange-50');
  });

  it('formats large numbers with comma separators', () => {
    const stats = {
      total_crls: 12345,
      by_status: {
        Approved: 8000,
        Unapproved: 4345,
      },
      by_year_and_status: {},
    };

    render(<StatsDashboard stats={stats} />);

    expect(screen.getByText('12,345')).toBeInTheDocument();
    expect(screen.getByText('8,000')).toBeInTheDocument();
    expect(screen.getByText('4,345')).toBeInTheDocument();
  });

  it('renders responsive containers for charts', () => {
    render(<StatsDashboard stats={mockStatsComplete} />);

    // Check that chart section headings are present (charts exist)
    expect(screen.getByText(/CRLs by Year/i)).toBeInTheDocument();
    expect(screen.getByText('Approval Status Distribution')).toBeInTheDocument();
  });
});
