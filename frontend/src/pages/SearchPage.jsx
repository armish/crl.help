/**
 * SearchPage component - Main search interface.
 *
 * Features:
 * - Keyword search only
 * - URL parameter reading (?q=)
 * - Auto-search on page load if query present
 * - Loading/error/empty states
 * - Result display with SearchResultCard
 * - Pagination support
 * - SEO metadata with Helmet
 */

import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { keywordSearch } from '../services/api';
import SearchResultCard from '../components/SearchResultCard';

export default function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();

  // State
  const [query, setQuery] = useState(searchParams.get('q') || '');
  const [results, setResults] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sortBy, setSortBy] = useState('date-desc'); // 'date-desc', 'date-asc', 'company-asc', 'company-desc', 'relevance-desc', 'relevance-asc'

  // Auto-search on page load if query parameter is present
  useEffect(() => {
    const initialQuery = searchParams.get('q');
    if (initialQuery) {
      setQuery(initialQuery);
      handleSearch(initialQuery);
    }
  }, []); // Only run on mount

  // Handle search
  const handleSearch = async (searchQuery = query) => {
    if (!searchQuery.trim()) {
      setError('Please enter a search query');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const data = await keywordSearch(searchQuery.trim(), 50, 0);
      setResults(data);
    } catch (err) {
      setError(err.message || 'Failed to perform search');
      console.error('Search error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle search form submission
  const handleSubmit = (e) => {
    e.preventDefault();
    // Update URL parameter
    if (query.trim()) {
      setSearchParams({ q: query.trim() });
    }
    handleSearch();
  };

  // Sort results
  const sortResults = (resultsToSort) => {
    if (!resultsToSort || resultsToSort.length === 0) return resultsToSort;

    const sorted = [...resultsToSort];

    switch (sortBy) {
      case 'date-desc':
        // Most recent first
        return sorted.sort((a, b) => new Date(b.letter_date) - new Date(a.letter_date));

      case 'date-asc':
        // Oldest first
        return sorted.sort((a, b) => new Date(a.letter_date) - new Date(b.letter_date));

      case 'company-asc':
        // Alphabetical by company name (A to Z)
        return sorted.sort((a, b) => a.company_name.localeCompare(b.company_name));

      case 'company-desc':
        // Reverse alphabetical by company name (Z to A)
        return sorted.sort((a, b) => b.company_name.localeCompare(a.company_name));

      case 'relevance-desc':
        // By number of matched fields (more matches = more relevant)
        return sorted.sort((a, b) => {
          const aMatches = a.matched_fields?.length || 0;
          const bMatches = b.matched_fields?.length || 0;
          return bMatches - aMatches;
        });

      case 'relevance-asc':
        // By number of matched fields (fewer matches first)
        return sorted.sort((a, b) => {
          const aMatches = a.matched_fields?.length || 0;
          const bMatches = b.matched_fields?.length || 0;
          return aMatches - bMatches;
        });

      default:
        return sorted;
    }
  };

  const resultsArray = sortResults(results?.results || []);

  return (
    <>
      <Helmet>
        <title>{query ? `Search: ${query}` : 'Search CRLs'} - FDA CRL Explorer</title>
        <meta
          name="description"
          content={`Search FDA Complete Response Letters ${query ? `for "${query}"` : 'using keyword search'}`}
        />
      </Helmet>

      <div className="max-w-5xl mx-auto">
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Search CRLs</h1>
          <p className="text-gray-600">
            Search across {' '}
            <span className="font-medium">FDA Complete Response Letters</span>
            {' '} using keyword matching
          </p>
        </div>

        {/* Search Form */}
        <form onSubmit={handleSubmit} className="mb-6">
          <div className="flex gap-2">
            <input
              type="search"
              placeholder="Enter your search query..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <button
              type="submit"
              disabled={isLoading}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
            >
              {isLoading ? 'Searching...' : 'Search'}
            </button>
          </div>
        </form>

        {/* Info Banner */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <div className="flex items-start gap-3">
            <svg className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
            <div className="text-sm text-blue-800">
              <p className="font-medium mb-1">Keyword Search</p>
              <p>Searches across company names, product names, categories, summaries, and full CRL text. Shows context where matches occur.</p>
            </div>
          </div>
        </div>

        {/* Error State */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <div className="flex items-start gap-3">
              <svg className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <div className="text-sm text-red-800">
                <p className="font-medium">Error</p>
                <p>{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Loading State */}
        {isLoading && (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <p className="mt-4 text-gray-600">Searching...</p>
          </div>
        )}

        {/* Results */}
        {!isLoading && results && (
          <>
            {/* Results Header */}
            <div className="mb-6 flex items-center justify-between">
              <p className="text-gray-600">
                Found <span className="font-semibold text-gray-900">{results.total || 0}</span> result(s)
                {query && <> for "<span className="font-medium">{query}</span>"</>}
              </p>

              {/* Sort Dropdown */}
              <div className="flex items-center gap-2">
                <label htmlFor="sort-select" className="text-sm text-gray-600">
                  Sort by:
                </label>
                <select
                  id="sort-select"
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="date-desc">Date (Newest First)</option>
                  <option value="date-asc">Date (Oldest First)</option>
                  <option value="company-asc">Company (A to Z)</option>
                  <option value="company-desc">Company (Z to A)</option>
                  <option value="relevance-desc">Relevance (Most Matches)</option>
                  <option value="relevance-asc">Relevance (Fewest Matches)</option>
                </select>
              </div>
            </div>

            {/* Results List */}
            {resultsArray.length > 0 ? (
              <div className="space-y-4">
                {resultsArray.map((result) => (
                  <SearchResultCard
                    key={result.id}
                    result={result}
                  />
                ))}
              </div>
            ) : (
              // No Results
              <div className="text-center py-12">
                <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <h3 className="mt-4 text-lg font-medium text-gray-900">No results found</h3>
                <p className="mt-2 text-gray-600">
                  Try adjusting your search query or using different keywords.
                </p>
              </div>
            )}
          </>
        )}

        {/* Initial State (no search performed yet) */}
        {!isLoading && !results && !error && (
          <div className="text-center py-12">
            <svg className="mx-auto h-16 w-16 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <h3 className="mt-4 text-lg font-medium text-gray-900">Start Your Search</h3>
            <p className="mt-2 text-gray-600">
              Enter a search query above to find relevant CRLs.
            </p>
          </div>
        )}
      </div>
    </>
  );
}
