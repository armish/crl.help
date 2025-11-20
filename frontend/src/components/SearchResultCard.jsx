/**
 * SearchResultCard component for displaying a single search result.
 *
 * Displays:
 * - CRL metadata (company, date, application number, category)
 * - Match field badges
 * - Context snippets with highlights
 * - "View Details" link to full CRL
 */

import { Link } from 'react-router-dom';
import ContextHighlight from './ContextHighlight';

export default function SearchResultCard({ result }) {
  const {
    id,
    company_name,
    letter_date,
    letter_year,
    application_number,
    application_type,
    therapeutic_category,
    deficiency_reason,
    matched_fields,
    match_snippets,
  } = result;

  // Format date for display
  const formattedDate = new Date(letter_date).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  // Create CRL detail URL
  const detailUrl = `/crl/${id}`;

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
      {/* Header with company and metadata */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <Link
            to={detailUrl}
            className="text-xl font-semibold text-blue-600 hover:text-blue-800 transition-colors"
          >
            {company_name}
          </Link>
          <div className="flex flex-wrap items-center gap-2 mt-2 text-sm text-gray-600">
            <span>{formattedDate}</span>
            <span className="text-gray-400">•</span>
            <span>{application_number && application_number[0]}</span>
            {application_type && (
              <>
                <span className="text-gray-400">•</span>
                <span className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-xs font-medium">
                  {application_type}
                </span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Categories */}
      {(therapeutic_category || deficiency_reason) && (
        <div className="flex flex-wrap gap-2 mb-3">
          {therapeutic_category && (
            <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded text-xs font-medium">
              {therapeutic_category}
            </span>
          )}
          {deficiency_reason && (
            <span className="px-2 py-1 bg-orange-100 text-orange-700 rounded text-xs font-medium">
              {deficiency_reason}
            </span>
          )}
        </div>
      )}

      {/* Matched fields badges */}
      {matched_fields && matched_fields.length > 0 && (
        <div className="mb-3">
          <span className="text-xs text-gray-500 mr-2">Matched in:</span>
          <div className="inline-flex flex-wrap gap-1.5">
            {matched_fields.map((field) => (
              <span
                key={field}
                className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs font-medium"
              >
                {field.replace(/_/g, ' ')}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Context snippets */}
      {match_snippets && Object.keys(match_snippets).length > 0 && (
        <div className="space-y-3 mb-4">
          {Object.entries(match_snippets).slice(0, 3).map(([field, snippet]) => (
            <div key={field} className="pl-4 border-l-2 border-gray-200">
              <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                {field.replace(/_/g, ' ')}
              </span>
              <ContextHighlight snippet={snippet} />
            </div>
          ))}
        </div>
      )}

      {/* View details link */}
      <Link
        to={detailUrl}
        className="inline-flex items-center text-sm text-blue-600 hover:text-blue-800 font-medium transition-colors"
      >
        View Full Details
        <svg className="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </Link>
    </div>
  );
}
