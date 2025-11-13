/**
 * Filter Panel Component
 *
 * Provides filtering controls for CRL data:
 * - Search text input
 * - Approval status dropdown
 * - Year dropdown
 * - Company name autocomplete
 * - Clear filters button
 */

import { useState, useEffect } from 'react';
import useFilterStore from '../store/filterStore';
import { useStats, useCompanies } from '../services/queries';

export default function FilterPanel() {
  const { filters, setFilter, clearFilters } = useFilterStore();
  // Fetch unfiltered stats to get all available years for the dropdown
  const { data: stats } = useStats({});
  // Fetch more companies for better autocomplete (increase limit to 500)
  const { data: companiesData } = useCompanies(500);

  // Local state for company autocomplete
  const [companyInput, setCompanyInput] = useState('');
  const [showCompanySuggestions, setShowCompanySuggestions] = useState(false);

  // Initialize company input from store
  useEffect(() => {
    setCompanyInput(filters.company_name || '');
  }, [filters.company_name]);

  // Get available years from stats
  const availableYears = stats?.by_year
    ? Object.keys(stats.by_year).sort((a, b) => b.localeCompare(a))
    : [];

  // Extract company names from the response and filter based on input
  const companyNames = companiesData?.companies?.map(c => c.company_name) || [];
  const filteredCompanies = companyInput.length >= 2
    ? companyNames.filter((company) =>
        company.toLowerCase().includes(companyInput.toLowerCase())
      ).slice(0, 10) // Limit to 10 suggestions
    : [];

  const handleCompanySelect = (company) => {
    setCompanyInput(company);
    setFilter('company_name', company);
    setShowCompanySuggestions(false);
  };

  const handleCompanyInputChange = (e) => {
    const value = e.target.value;
    setCompanyInput(value);
    setShowCompanySuggestions(value.length >= 2);

    // Update filter immediately for search-as-you-type
    if (value.length === 0) {
      setFilter('company_name', '');
    }
  };

  const handleClearFilters = () => {
    clearFilters();
    setCompanyInput('');
    setShowCompanySuggestions(false);
  };

  const handleApprovalStatusToggle = (status) => {
    const currentStatuses = filters.approval_status || [];
    const newStatuses = currentStatuses.includes(status)
      ? currentStatuses.filter(s => s !== status)
      : [...currentStatuses, status];
    setFilter('approval_status', newStatuses);
  };

  const handleYearToggle = (year) => {
    const currentYears = filters.letter_year || [];
    const newYears = currentYears.includes(year)
      ? currentYears.filter(y => y !== year)
      : [...currentYears, year];
    setFilter('letter_year', newYears);
  };

  // Check if any filters are active
  const hasActiveFilters =
    filters.approval_status?.length > 0 ||
    filters.letter_year?.length > 0 ||
    filters.company_name ||
    filters.search_text;

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Filters</h3>
        {hasActiveFilters && (
          <button
            onClick={handleClearFilters}
            className="text-sm text-blue-600 hover:text-blue-800 font-medium"
          >
            Clear all
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Search Text Input */}
        <div>
          <label
            htmlFor="search_text"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Search
          </label>
          <input
            id="search_text"
            type="text"
            value={filters.search_text}
            onChange={(e) => setFilter('search_text', e.target.value)}
            placeholder="Search CRLs..."
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        {/* Approval Status Multi-Select */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Approval Status
          </label>
          <div className="space-y-2">
            {['Approved', 'Unapproved'].map((status) => (
              <label key={status} className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.approval_status?.includes(status)}
                  onChange={() => handleApprovalStatusToggle(status)}
                  className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">{status}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Year Multi-Select */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Year
          </label>
          <div className="border border-gray-300 rounded-md shadow-sm max-h-24 overflow-y-auto p-2 space-y-1">
            {availableYears.length > 0 ? (
              availableYears.map((year) => (
                <label key={year} className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={filters.letter_year?.includes(year)}
                    onChange={() => handleYearToggle(year)}
                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <span className="text-sm text-gray-700">{year}</span>
                </label>
              ))
            ) : (
              <p className="text-sm text-gray-500 text-center py-2">No years available</p>
            )}
          </div>
        </div>

        {/* Company Name Autocomplete */}
        <div className="relative">
          <label
            htmlFor="company_name"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Company Name
          </label>
          <input
            id="company_name"
            type="text"
            value={companyInput}
            onChange={handleCompanyInputChange}
            onFocus={() => companyInput.length >= 2 && setShowCompanySuggestions(true)}
            onBlur={() => {
              // Delay to allow clicking on suggestions
              setTimeout(() => setShowCompanySuggestions(false), 200);
            }}
            placeholder="Type to search..."
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />

          {/* Autocomplete Suggestions */}
          {showCompanySuggestions && filteredCompanies.length > 0 && (
            <div className="absolute z-10 mt-1 w-full bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-auto">
              {filteredCompanies.map((company, index) => (
                <button
                  key={index}
                  type="button"
                  onClick={() => handleCompanySelect(company)}
                  className="w-full text-left px-3 py-2 hover:bg-blue-50 text-sm text-gray-900"
                >
                  {company}
                </button>
              ))}
            </div>
          )}

          {/* No results message */}
          {showCompanySuggestions && companyInput.length >= 2 && filteredCompanies.length === 0 && (
            <div className="absolute z-10 mt-1 w-full bg-white border border-gray-300 rounded-md shadow-lg p-3">
              <p className="text-sm text-gray-500">No companies found</p>
            </div>
          )}
        </div>
      </div>

      {/* Active filters indicator */}
      {hasActiveFilters && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <p className="text-sm text-gray-600">
            Active filters:{' '}
            {[
              filters.search_text && `Search: "${filters.search_text}"`,
              filters.approval_status?.length > 0 && `Status: ${filters.approval_status.join(', ')}`,
              filters.letter_year?.length > 0 && `Year: ${filters.letter_year.join(', ')}`,
              filters.company_name && `Company: ${filters.company_name}`,
            ]
              .filter(Boolean)
              .join(', ')}
          </p>
        </div>
      )}
    </div>
  );
}
