/**
 * Statistics Dashboard Component
 *
 * Displays statistics with interactive charts for:
 * - CRLs by Year (Bar Chart)
 * - Approval Status Distribution (Pie Chart)
 * - Breakdowns by Application Type, Therapeutic Category, Deficiency Reason
 */

import { useMemo, useState } from 'react';
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
function StatCard({ title, value, subtitle, color = 'blue', unfilteredValue }) {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-900 border-blue-200',
    green: 'bg-green-50 text-green-900 border-green-200',
    orange: 'bg-orange-50 text-orange-900 border-orange-200',
    gray: 'bg-gray-50 text-gray-900 border-gray-200',
  };

  return (
    <div
      className={`rounded-lg border p-6 ${colorClasses[color] || colorClasses.gray}`}
    >
      <h3 className="text-sm font-medium mb-2">{title}</h3>
      <p className="text-3xl font-bold mb-1">
        {value}
        {unfilteredValue && unfilteredValue !== value && (
          <span className="text-lg opacity-60 ml-2">of {unfilteredValue}</span>
        )}
      </p>
      {subtitle && <p className="text-sm opacity-75">{subtitle}</p>}
    </div>
  );
}

/**
 * StatsDashboard Component
 */
export default function StatsDashboard({ stats, unfilteredStats }) {
  // Breakdown selector state
  const [selectedBreakdown, setSelectedBreakdown] = useState('therapeutic_category');

  // Normalization toggle state for year chart
  const [normalizeYearChart, setNormalizeYearChart] = useState(false);

  // Prepare data for stacked bar chart (year + selected breakdown)
  const yearChartData = useMemo(() => {
    let yearData = {};
    let categoriesSet = new Set();

    switch (selectedBreakdown) {
      case 'status':
        yearData = stats?.by_year_and_status || {};
        break;
      case 'application_type':
        yearData = stats?.by_year_and_application_type || {};
        break;
      case 'letter_type':
        yearData = stats?.by_year_and_letter_type || {};
        break;
      case 'therapeutic_category':
        yearData = stats?.by_year_and_therapeutic_category || {};
        break;
      case 'deficiency_reason':
        yearData = stats?.by_year_and_deficiency_reason || {};
        break;
      default:
        yearData = stats?.by_year_and_status || {};
    }

    if (Object.keys(yearData).length === 0) return [];

    // Collect all unique categories across all years
    Object.values(yearData).forEach(yearCounts => {
      Object.keys(yearCounts).forEach(category => categoriesSet.add(category));
    });

    // Build chart data with all categories for each year
    const chartData = Object.entries(yearData)
      .map(([year, categoryCounts]) => {
        const yearEntry = { year };
        let yearTotal = 0;

        // Calculate totals first if normalizing
        if (normalizeYearChart) {
          yearTotal = Object.values(categoryCounts).reduce((sum, count) => sum + count, 0);
        }

        categoriesSet.forEach(category => {
          const count = categoryCounts[category] || 0;
          if (normalizeYearChart && yearTotal > 0) {
            // Convert to percentage
            yearEntry[category] = (count / yearTotal) * 100;
          } else {
            yearEntry[category] = count;
          }
        });
        return yearEntry;
      })
      .sort((a, b) => a.year.localeCompare(b.year));

    return chartData;
  }, [selectedBreakdown, stats, normalizeYearChart]);

  const statusChartData = useMemo(() => {
    if (!stats?.by_status) return [];

    return Object.entries(stats.by_status).map(([status, count]) => ({
      name: status,
      value: count,
    }));
  }, [stats?.by_status]);

  // Prepare data for breakdown chart based on selected breakdown
  const breakdownChartData = useMemo(() => {
    let data = [];

    switch (selectedBreakdown) {
      case 'status':
        if (stats?.by_status) {
          data = Object.entries(stats.by_status).map(([name, value]) => ({ name, value }));
        }
        break;
      case 'application_type':
        if (stats?.by_application_type) {
          data = Object.entries(stats.by_application_type).map(([name, value]) => ({ name, value }));
        }
        break;
      case 'letter_type':
        if (stats?.by_letter_type) {
          data = Object.entries(stats.by_letter_type).map(([name, value]) => ({ name, value }));
        }
        break;
      case 'therapeutic_category':
        if (stats?.by_therapeutic_category) {
          data = Object.entries(stats.by_therapeutic_category).map(([name, value]) => ({ name, value }));
        }
        break;
      case 'deficiency_reason':
        if (stats?.by_deficiency_reason) {
          data = Object.entries(stats.by_deficiency_reason).map(([name, value]) => ({ name, value }));
        }
        break;
      default:
        break;
    }

    return data.sort((a, b) => b.value - a.value);
  }, [selectedBreakdown, stats]);

  // Colors for charts
  const COLORS = {
    Approved: '#10b981', // green
    Unapproved: '#f97316', // orange
  };

  // Color palette for breakdown charts
  const BREAKDOWN_COLORS = [
    '#3b82f6', // blue
    '#10b981', // green
    '#f97316', // orange
    '#8b5cf6', // purple
    '#ec4899', // pink
    '#f59e0b', // amber
    '#14b8a6', // teal
    '#ef4444', // red
    '#6366f1', // indigo
    '#06b6d4', // cyan
  ];

  // Get unique categories from year chart data for stacking
  const yearCategories = useMemo(() => {
    if (yearChartData.length === 0) return [];
    const categories = new Set();
    yearChartData.forEach(yearData => {
      Object.keys(yearData).forEach(key => {
        if (key !== 'year') categories.add(key);
      });
    });
    return Array.from(categories);
  }, [yearChartData]);

  // Get color for a category based on breakdown type
  const getCategoryColor = (category, index) => {
    if (selectedBreakdown === 'status' && COLORS[category]) {
      return COLORS[category];
    }
    return BREAKDOWN_COLORS[index % BREAKDOWN_COLORS.length];
  };

  // Calculate percentages for stat cards
  const approvedCount = stats?.by_status?.Approved || 0;
  const unapprovedCount = stats?.by_status?.Unapproved || 0;
  const total = stats?.total_crls || 0;

  // Get unfiltered values for context
  const unfilteredTotal = unfilteredStats?.total_crls || 0;
  const unfilteredApproved = unfilteredStats?.by_status?.Approved || 0;
  const unfilteredUnapproved = unfilteredStats?.by_status?.Unapproved || 0;

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
          unfilteredValue={unfilteredTotal.toLocaleString()}
          color="blue"
        />
        <StatCard
          title="Approved"
          value={approvedCount.toLocaleString()}
          unfilteredValue={unfilteredApproved.toLocaleString()}
          subtitle={`${approvedPercentage}% of total`}
          color="green"
        />
        <StatCard
          title="Unapproved"
          value={unapprovedCount.toLocaleString()}
          unfilteredValue={unfilteredUnapproved.toLocaleString()}
          subtitle={`${unapprovedPercentage}% of total`}
          color="orange"
        />
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Bar Chart: CRLs by Year (Stacked by Selected Breakdown) */}
        {yearChartData.length > 0 && (
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">
                CRLs by Year {normalizeYearChart && '(%)'}
              </h3>
              <button
                onClick={() => setNormalizeYearChart(!normalizeYearChart)}
                className="px-3 py-1 text-sm border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                {normalizeYearChart ? 'Show Count' : 'Show %'}
              </button>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={yearChartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="year"
                  tick={{ fontSize: 12 }}
                  stroke="#6b7280"
                />
                <YAxis
                  tick={{ fontSize: 12 }}
                  stroke="#6b7280"
                  label={normalizeYearChart ? { value: '%', angle: -90, position: 'insideLeft' } : undefined}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#ffffff',
                    border: '1px solid #e5e7eb',
                    borderRadius: '6px',
                  }}
                  formatter={(value) => normalizeYearChart ? `${value.toFixed(1)}%` : value}
                />
                <Legend wrapperStyle={{ fontSize: '14px' }} />
                {yearCategories.map((category, index) => (
                  <Bar
                    key={category}
                    dataKey={category}
                    stackId="a"
                    fill={getCategoryColor(category, index)}
                    name={category}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Breakdown Bar Chart with Selector */}
        {breakdownChartData.length > 0 && (
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">
                CRL Breakdown
              </h3>
              <select
                value={selectedBreakdown}
                onChange={(e) => setSelectedBreakdown(e.target.value)}
                className="px-3 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="status">Approval Status</option>
                <option value="application_type">Application Type</option>
                <option value="letter_type">Letter Type</option>
                <option value="therapeutic_category">Therapeutic Category</option>
                <option value="deficiency_reason">Deficiency Reason</option>
              </select>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={breakdownChartData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" tick={{ fontSize: 12 }} stroke="#6b7280" />
                <YAxis
                  type="category"
                  dataKey="name"
                  tick={{ fontSize: 11 }}
                  stroke="#6b7280"
                  width={150}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#ffffff',
                    border: '1px solid #e5e7eb',
                    borderRadius: '6px',
                  }}
                />
                <Bar dataKey="value" name="CRLs">
                  {breakdownChartData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={
                        selectedBreakdown === 'status' && COLORS[entry.name]
                          ? COLORS[entry.name]
                          : BREAKDOWN_COLORS[index % BREAKDOWN_COLORS.length]
                      }
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
}
