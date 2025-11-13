/**
 * Statistics Dashboard Component
 *
 * Displays statistics with interactive charts for:
 * - CRLs by Year (Bar Chart)
 * - Approval Status Distribution (Pie Chart)
 */

import { useMemo } from 'react';
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

/**
 * StatCard component for displaying summary statistics
 */
function StatCard({ title, value, subtitle, color = 'blue' }) {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-900 border-blue-200',
    green: 'bg-green-50 text-green-900 border-green-200',
    red: 'bg-red-50 text-red-900 border-red-200',
    gray: 'bg-gray-50 text-gray-900 border-gray-200',
  };

  return (
    <div
      className={`rounded-lg border p-6 ${colorClasses[color] || colorClasses.gray}`}
    >
      <h3 className="text-sm font-medium mb-2">{title}</h3>
      <p className="text-3xl font-bold mb-1">{value}</p>
      {subtitle && <p className="text-sm opacity-75">{subtitle}</p>}
    </div>
  );
}

/**
 * StatsDashboard Component
 */
export default function StatsDashboard({ stats }) {
  // Prepare data for charts
  const yearChartData = useMemo(() => {
    if (!stats?.by_year) return [];

    return Object.entries(stats.by_year)
      .map(([year, count]) => ({
        year,
        count,
      }))
      .sort((a, b) => a.year.localeCompare(b.year));
  }, [stats?.by_year]);

  const statusChartData = useMemo(() => {
    if (!stats?.by_status) return [];

    return Object.entries(stats.by_status).map(([status, count]) => ({
      name: status,
      value: count,
    }));
  }, [stats?.by_status]);

  // Colors for pie chart
  const COLORS = {
    Approved: '#10b981', // green
    Unapproved: '#ef4444', // red
  };

  // Calculate percentages for stat cards
  const approvedCount = stats?.by_status?.Approved || 0;
  const unapprovedCount = stats?.by_status?.Unapproved || 0;
  const total = stats?.total_crls || 0;

  const approvedPercentage = total > 0 ? Math.round((approvedCount / total) * 100) : 0;
  const unapprovedPercentage =
    total > 0 ? Math.round((unapprovedCount / total) * 100) : 0;

  return (
    <div className="space-y-8">
      {/* Summary Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard
          title="Total CRLs"
          value={total.toLocaleString()}
          color="blue"
        />
        <StatCard
          title="Approved"
          value={approvedCount.toLocaleString()}
          subtitle={`${approvedPercentage}% of total`}
          color="green"
        />
        <StatCard
          title="Unapproved"
          value={unapprovedCount.toLocaleString()}
          subtitle={`${unapprovedPercentage}% of total`}
          color="red"
        />
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Bar Chart: CRLs by Year */}
        {yearChartData.length > 0 && (
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h3 className="text-lg font-semibold mb-4 text-gray-900">
              CRLs by Year
            </h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={yearChartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="year"
                  tick={{ fontSize: 12 }}
                  stroke="#6b7280"
                />
                <YAxis tick={{ fontSize: 12 }} stroke="#6b7280" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#ffffff',
                    border: '1px solid #e5e7eb',
                    borderRadius: '6px',
                  }}
                />
                <Legend wrapperStyle={{ fontSize: '14px' }} />
                <Bar dataKey="count" fill="#3b82f6" name="CRL Count" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Pie Chart: Approval Status Distribution */}
        {statusChartData.length > 0 && (
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h3 className="text-lg font-semibold mb-4 text-gray-900">
              Approval Status Distribution
            </h3>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={statusChartData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) =>
                    `${name}: ${(percent * 100).toFixed(0)}%`
                  }
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {statusChartData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={COLORS[entry.name] || '#6b7280'}
                    />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#ffffff',
                    border: '1px solid #e5e7eb',
                    borderRadius: '6px',
                  }}
                />
                <Legend wrapperStyle={{ fontSize: '14px' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
}
