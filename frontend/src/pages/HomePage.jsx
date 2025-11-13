/**
 * Home page for FDA CRL Explorer.
 *
 * Displays:
 * - Statistics dashboard with interactive charts
 * - CRL table with filters and search (Phase 9)
 * - Detail modal with AI summary (Phase 9)
 */

import { useStats } from '../services/queries';
import StatsDashboard from '../components/StatsDashboard';
import FilterPanel from '../components/FilterPanel';

export default function HomePage() {
  const { data: stats, isLoading, error } = useStats();

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
      {/* Statistics Dashboard */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Overview</h2>
        <StatsDashboard stats={stats} />
      </div>

      {/* CRL Table Section */}
      <div>
        <h3 className="text-xl font-bold text-gray-900 mb-4">Complete Response Letters</h3>

        {/* Filter Panel */}
        <FilterPanel />

        {/* Placeholder for CRL Table */}
        <div className="mt-4 bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
          <p className="text-gray-600">
            CRL table will be added next
          </p>
        </div>
      </div>
    </div>
  );
}
