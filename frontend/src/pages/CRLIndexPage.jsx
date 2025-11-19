/**
 * CRL Index Page
 *
 * Lists all CRLs as links for SEO crawlers to discover and index.
 * Each link includes key metadata for search engines.
 */

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { getCRLDetailUrl } from '../utils/urlHelpers';

export default function CRLIndexPage() {
  const [crls, setCRLs] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState({ total: 0, loaded: 0 });

  useEffect(() => {
    const fetchAllCRLs = async () => {
      try {
        setIsLoading(true);
        const allCRLs = [];
        let offset = 0;
        const pageSize = 100;
        let hasMore = true;

        // Fetch all CRLs in batches
        while (hasMore) {
          const response = await fetch(
            `/api/crls?page=${Math.floor(offset / pageSize) + 1}&pageSize=${pageSize}&sortBy=letter_date&sortOrder=DESC`
          );

          if (!response.ok) {
            throw new Error('Failed to fetch CRLs');
          }

          const data = await response.json();

          // Break if no items returned
          if (!data.items || data.items.length === 0) {
            break;
          }

          allCRLs.push(...data.items);
          setStats({ total: data.total, loaded: allCRLs.length });

          // Stop if we've loaded all items or reached the total
          if (allCRLs.length >= data.total || !data.has_more || data.items.length < pageSize) {
            hasMore = false;
          } else {
            offset += pageSize;
            // Add a small delay to avoid overwhelming the server
            await new Promise(resolve => setTimeout(resolve, 50));
          }
        }

        setCRLs(allCRLs);
        setIsLoading(false);
      } catch (err) {
        setError(err.message);
        setIsLoading(false);
      }
    };

    fetchAllCRLs();
  }, []);

  return (
    <>
      <Helmet>
        <title>CRL Index - All Complete Response Letters | FDA CRL Explorer</title>
        <meta name="description" content="Complete index of all FDA Complete Response Letters in our database. Browse by date, company, and therapeutic category." />
        <meta name="robots" content="index, follow" />
      </Helmet>

      <div className="max-w-7xl mx-auto">
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Complete Response Letter Index
          </h1>
          <p className="text-gray-600">
            Browse all {stats.total.toLocaleString()} Complete Response Letters in our database
          </p>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="bg-white rounded-lg border border-gray-200 p-8">
            <div className="flex flex-col items-center justify-center">
              <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"></div>
              <p className="mt-4 text-gray-600">
                Loading CRLs... ({stats.loaded} / {stats.total})
              </p>
              <div className="w-full max-w-md mt-4 bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${stats.total > 0 ? (stats.loaded / stats.total) * 100 : 0}%` }}
                ></div>
              </div>
            </div>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <h2 className="text-red-800 font-semibold text-lg">Error loading CRLs</h2>
            <p className="text-red-600 mt-2">{error}</p>
            <p className="text-sm text-red-500 mt-2">
              Unable to load CRL data. Please try again later.
            </p>
          </div>
        )}

        {/* CRL List */}
        {!isLoading && !error && crls.length > 0 && (
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
            <div className="divide-y divide-gray-200">
              {crls.map((crl) => {
                const crlUrl = getCRLDetailUrl(crl);
                const date = crl.letter_date ? new Date(crl.letter_date).toLocaleDateString() : 'N/A';
                const appNumber = Array.isArray(crl.application_number)
                  ? crl.application_number.join(', ')
                  : crl.application_number || 'N/A';

                return (
                  <Link
                    key={crl.id}
                    to={crlUrl}
                    className="block px-6 py-4 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2">
                      <div className="flex-1">
                        <div className="flex items-start gap-3">
                          <span className="text-sm font-medium text-gray-500 whitespace-nowrap">
                            {date}
                          </span>
                          <div className="flex-1">
                            <h3 className="text-base font-semibold text-blue-600 hover:text-blue-800">
                              {crl.company_name || 'Unknown Company'}
                            </h3>
                            <div className="flex flex-wrap items-center gap-2 mt-1">
                              {crl.therapeutic_category && (
                                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800">
                                  {crl.therapeutic_category}
                                </span>
                              )}
                              {crl.deficiency_reason && (
                                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-orange-100 text-orange-800">
                                  {crl.deficiency_reason}
                                </span>
                              )}
                              {crl.letter_type && (
                                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                                  {crl.letter_type}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                      <div className="text-sm text-gray-500 md:text-right">
                        <div className="font-mono">{appNumber}</div>
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>
          </div>
        )}

        {/* Footer note */}
        {!isLoading && !error && crls.length > 0 && (
          <div className="mt-8 text-center text-sm text-gray-500">
            <p>Total: {crls.length.toLocaleString()} Complete Response Letters</p>
          </div>
        )}

        {/* Back to explorer */}
        <div className="mt-8 text-center">
          <Link
            to="/"
            className="inline-flex items-center text-sm text-blue-600 hover:text-blue-700 transition-colors"
          >
            <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to CRL Explorer
          </Link>
        </div>
      </div>
    </>
  );
}
