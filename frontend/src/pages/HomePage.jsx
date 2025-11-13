/**
 * Home page for FDA CRL Explorer.
 *
 * Displays:
 * - Overall statistics cards
 * - CRL table (will be implemented in Phase 9)
 * - Filter panel (will be implemented in Phase 9)
 */

import { useStats } from '../services/queries';

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
      {/* Statistics Cards */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Overview</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Total CRLs */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="text-sm font-medium text-gray-600 uppercase tracking-wide">
              Total CRLs
            </div>
            <div className="mt-2 text-3xl font-bold text-gray-900">
              {stats?.total_crls?.toLocaleString() || 0}
            </div>
          </div>

          {/* Approved */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="text-sm font-medium text-gray-600 uppercase tracking-wide">
              Approved
            </div>
            <div className="mt-2 text-3xl font-bold text-green-600">
              {stats?.by_status?.Approved?.toLocaleString() || 0}
            </div>
            <div className="mt-1 text-sm text-gray-500">
              {stats?.total_crls > 0
                ? `${Math.round((stats.by_status.Approved / stats.total_crls) * 100)}%`
                : '0%'}
            </div>
          </div>

          {/* Unapproved */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="text-sm font-medium text-gray-600 uppercase tracking-wide">
              Unapproved
            </div>
            <div className="mt-2 text-3xl font-bold text-amber-600">
              {stats?.by_status?.Unapproved?.toLocaleString() || 0}
            </div>
            <div className="mt-1 text-sm text-gray-500">
              {stats?.total_crls > 0
                ? `${Math.round((stats.by_status.Unapproved / stats.total_crls) * 100)}%`
                : '0%'}
            </div>
          </div>
        </div>
      </div>

      {/* By Year Section */}
      {stats?.by_year && Object.keys(stats.by_year).length > 0 && (
        <div>
          <h3 className="text-xl font-bold text-gray-900 mb-4">CRLs by Year</h3>
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {Object.entries(stats.by_year)
                .sort(([yearA], [yearB]) => yearB.localeCompare(yearA))
                .map(([year, count]) => (
                  <div key={year} className="text-center">
                    <div className="text-2xl font-bold text-gray-900">{count}</div>
                    <div className="text-sm text-gray-600">{year}</div>
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}

      {/* Placeholder for CRL Table */}
      <div>
        <h3 className="text-xl font-bold text-gray-900 mb-4">Complete Response Letters</h3>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
          <p className="text-gray-600">
            CRL table and filters will be implemented in Phase 9
          </p>
        </div>
      </div>
    </div>
  );
}
