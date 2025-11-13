/**
 * Home page for FDA CRL Explorer.
 *
 * Displays:
 * - Statistics dashboard with interactive charts
 * - CRL table with filters and search (Phase 9)
 * - Detail modal with AI summary (Phase 9)
 */

import { useState } from 'react';
import { useStats } from '../services/queries';
import StatsDashboard from '../components/StatsDashboard';
import FilterPanel from '../components/FilterPanel';
import CRLTable from '../components/CRLTable';
import { useQueryParams } from '../store/filterStore';

export default function HomePage() {
  // Show/hide state for Overview section
  const [showOverview, setShowOverview] = useState(true);

  // Get filter parameters from Zustand store
  const filterParams = useQueryParams();

  // Extract only filter params (exclude pagination and sort) for stats
  const { limit, offset, sort_by, sort_order, ...filterOnlyParams } = filterParams;

  // Fetch filtered stats with current filters applied (no pagination/sort)
  const { data: stats, isLoading, error } = useStats(filterOnlyParams);

  // Fetch unfiltered stats for showing original totals
  const { data: unfilteredStats } = useStats({});

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-600">Loading statistics...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <h3 className="text-red-800 font-semibold">Error loading statistics</h3>
        <p className="text-red-600 text-sm mt-1">{error.message}</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Filter Panel - at the top */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Filter CRLs</h2>
        <FilterPanel />
      </div>

      {/* Statistics Dashboard - updates based on filters */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold text-gray-900">Overview</h2>
          <button
            onClick={() => setShowOverview(!showOverview)}
            className="text-sm text-blue-600 hover:text-blue-800 font-medium flex items-center space-x-1"
          >
            <span>{showOverview ? 'Hide' : 'Show'}</span>
            <svg
              className={`w-4 h-4 transition-transform ${showOverview ? '' : 'rotate-180'}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
            </svg>
          </button>
        </div>
        {showOverview && <StatsDashboard stats={stats} unfilteredStats={unfilteredStats} />}
      </div>

      {/* CRL Table Section */}
      <div>
        <h3 className="text-xl font-bold text-gray-900 mb-4">Complete Response Letters</h3>
        <CRLTable />
      </div>
    </div>
  );
}
