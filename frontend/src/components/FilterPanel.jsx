/**
 * Filter Panel Component
 *
 * Provides filtering controls for CRL data:
 * - Search text input
 * - Approval status multi-select dropdown
 * - Year multi-select dropdown
 * - Company name multi-select dropdown
 * - Clear filters button
 */

import useFilterStore from '../store/filterStore';
import { useStats, useCompanies } from '../services/queries';
import MultiSelectDropdown from './MultiSelectDropdown';

export default function FilterPanel() {
  const { filters, setFilter, clearFilters } = useFilterStore();
  // Fetch unfiltered stats to get all available years
  const { data: stats } = useStats({});
  // Fetch companies for multi-select
  const { data: companiesData } = useCompanies(1000);

  // Get available years from stats
  const availableYears = stats?.by_year
    ? Object.keys(stats.by_year).sort((a, b) => b.localeCompare(a))
    : [];

  // Extract company names from the response and sort alphabetically
  const companyNames = companiesData?.companies
    ?.map(c => c.company_name)
    .sort((a, b) => a.localeCompare(b)) || [];

  // Approval status options
  const approvalStatusOptions = ['Approved', 'Unapproved'];

  // Application type options (BLA/NDA/etc. - derived from application_number)
  const applicationTypeOptions = ['BLA', 'NDA', 'BL'];

  // Letter type options (from letter_type field)
  const letterTypeOptions = stats?.by_letter_type
    ? Object.keys(stats.by_letter_type).sort()
    : [];

  // Therapeutic category options
  const therapeuticCategoryOptions = [
    'Small molecules',
    'Biologics - proteins',
    'Vaccines',
    'Blood products',
    'Cellular therapies',
    'Gene therapies',
    'Tissue products',
    'Combination products',
    'Devices/IVDs',
    'Other'
  ];

  // Deficiency reason options
  const deficiencyReasonOptions = [
    'Clinical',
    'CMC / Quality',
    'Facilities / GMP',
    'Combination Product / Device',
    'Regulatory / Labeling / Other'
  ];

  // Check if any filters are active (not "Select All")
  const hasActiveFilters =
    filters.approval_status?.length > 0 ||
    filters.letter_year?.length > 0 ||
    filters.application_type?.length > 0 ||
    filters.letter_type?.length > 0 ||
    filters.therapeutic_category?.length > 0 ||
    filters.deficiency_reason?.length > 0 ||
    filters.company_name?.length > 0 ||
    filters.search_text;

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Filters</h3>
        {hasActiveFilters && (
          <button
            onClick={clearFilters}
            className="text-sm text-blue-600 hover:text-blue-800 font-medium"
          >
            Clear all
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Search Text Input */}
        <div className="lg:col-span-2">
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
        <MultiSelectDropdown
          label="Approval Status"
          options={approvalStatusOptions}
          selectedValues={filters.approval_status || []}
          onChange={(values) => setFilter('approval_status', values)}
          maxHeight="150px"
        />

        {/* Application Type Multi-Select (BLA/NDA/etc.) */}
        <MultiSelectDropdown
          label="Application Type"
          options={applicationTypeOptions}
          selectedValues={filters.application_type || []}
          onChange={(values) => setFilter('application_type', values)}
          maxHeight="150px"
        />

        {/* Letter Type Multi-Select */}
        <MultiSelectDropdown
          label="Letter Type"
          options={letterTypeOptions}
          selectedValues={filters.letter_type || []}
          onChange={(values) => setFilter('letter_type', values)}
          maxHeight="200px"
          enableSearch={true}
        />

        {/* Therapeutic Category Multi-Select */}
        <MultiSelectDropdown
          label="Therapeutic Category"
          options={therapeuticCategoryOptions}
          selectedValues={filters.therapeutic_category || []}
          onChange={(values) => setFilter('therapeutic_category', values)}
          maxHeight="300px"
          enableSearch={true}
        />

        {/* Deficiency Reason Multi-Select */}
        <MultiSelectDropdown
          label="Deficiency Reason"
          options={deficiencyReasonOptions}
          selectedValues={filters.deficiency_reason || []}
          onChange={(values) => setFilter('deficiency_reason', values)}
          maxHeight="200px"
        />

        {/* Year Multi-Select */}
        <MultiSelectDropdown
          label="Year"
          options={availableYears}
          selectedValues={filters.letter_year || []}
          onChange={(values) => setFilter('letter_year', values)}
          maxHeight="300px"
          enableSearch={true}
        />

        {/* Company Name Multi-Select */}
        <MultiSelectDropdown
          label="Company Name"
          options={companyNames}
          selectedValues={filters.company_name || []}
          onChange={(values) => setFilter('company_name', values)}
          maxHeight="300px"
          enableSearch={true}
        />
      </div>

      {/* Active filters indicator */}
      {hasActiveFilters && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <p className="text-sm text-gray-600">
            Active filters:{' '}
            {[
              filters.search_text && `Search: "${filters.search_text}"`,
              filters.approval_status?.length > 0 && `Status: ${filters.approval_status.join(', ')}`,
              filters.application_type?.length > 0 && `App Type: ${filters.application_type.join(', ')}`,
              filters.letter_type?.length > 0 && `Letter Type: ${filters.letter_type.length} selected`,
              filters.therapeutic_category?.length > 0 && `Therapeutic: ${filters.therapeutic_category.length} selected`,
              filters.deficiency_reason?.length > 0 && `Reason: ${filters.deficiency_reason.join(', ')}`,
              filters.letter_year?.length > 0 && `Year: ${filters.letter_year.join(', ')}`,
              filters.company_name?.length > 0 && `Company: ${filters.company_name.length} selected`,
            ]
              .filter(Boolean)
              .join(' | ')}
          </p>
        </div>
      )}
    </div>
  );
}
