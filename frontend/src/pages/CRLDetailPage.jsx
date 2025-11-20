/**
 * CRL Detail Page
 *
 * Dedicated page for displaying Complete Response Letter details.
 * This page is SEO-friendly with a descriptive URL structure.
 *
 * URL format: /crl/{id}/{letter-type}-{company-name}-{product-name}
 * Example: /crl/BLA125360-2020/bla-pfizer-comirnaty
 */

import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { useCRL } from '../services/queries';
import CRLDetailContent from '../components/CRLDetailContent';
import PDFViewer from '../components/PDFViewer';
import { parseCRLIdFromUrl } from '../utils/urlHelpers';

export default function CRLDetailPage() {
  const { '*': pathname } = useParams();
  const crlId = parseCRLIdFromUrl(`/crl/${pathname}`);
  const [activeTab, setActiveTab] = useState('summary');

  // Fetch CRL for SEO metadata
  const { data: crl } = useCRL(crlId);

  // Generate SEO-friendly title and description
  const pageTitle = crl
    ? `${crl.company_name || 'Unknown'} - ${crl.product_name || crl.therapeutic_category || 'CRL'} | FDA CRL Explorer`
    : 'Complete Response Letter | FDA CRL Explorer';

  const pageDescription = crl
    ? `Complete Response Letter for ${crl.company_name || 'Unknown Company'}'s ${crl.product_name || crl.therapeutic_category || 'application'} (${crl.letter_type || 'Letter'} - ${crl.letter_year || 'N/A'}). ${crl.summary?.substring(0, 150) || 'View detailed information about this FDA Complete Response Letter.'}`
    : 'View detailed information about this FDA Complete Response Letter.';

  if (!crlId) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-4xl mx-auto px-4 py-12">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <h2 className="text-red-800 font-semibold text-lg">Invalid CRL URL</h2>
            <p className="text-red-600 mt-2">
              The URL you've entered doesn't contain a valid CRL identifier.
            </p>
            <Link
              to="/"
              className="inline-block mt-4 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors"
            >
              Back to Explorer
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <Helmet>
        <title>{pageTitle}</title>
        <meta name="description" content={pageDescription} />

        {/* Open Graph tags for social media */}
        <meta property="og:title" content={pageTitle} />
        <meta property="og:description" content={pageDescription} />
        <meta property="og:type" content="article" />

        {/* Additional metadata */}
        {crl && (
          <>
            <meta name="keywords" content={`FDA, CRL, Complete Response Letter, ${crl.company_name}, ${crl.product_name || crl.therapeutic_category}, ${crl.letter_type}`} />
            {crl.letter_date && <meta property="article:published_time" content={crl.letter_date} />}
          </>
        )}
      </Helmet>

      <div className="min-h-screen bg-gray-50">
        <div className="max-w-4xl mx-auto px-4 py-8">
          {/* Breadcrumb navigation */}
          <nav className="mb-6">
            <ol className="flex items-center space-x-2 text-sm text-gray-600">
              <li>
                <Link to="/" className="hover:text-blue-600 transition-colors">
                  Home
                </Link>
              </li>
              <li>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </li>
              <li className="text-gray-900 font-medium">
                {crl ? (
                  <>
                    {crl.company_name || 'CRL'} - {crl.product_name || crl.therapeutic_category || crl.id}
                  </>
                ) : (
                  'Loading...'
                )}
              </li>
            </ol>
          </nav>

          {/* Page header */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Complete Response Letter
            </h1>
            {crl && (
              <p className="text-gray-600">
                {crl.company_name && <span className="font-medium">{crl.company_name}</span>}
                {crl.product_name && <span> - {crl.product_name}</span>}
                {crl.letter_date && (
                  <span className="ml-2 text-sm text-gray-500">
                    ({new Date(crl.letter_date).toLocaleDateString()})
                  </span>
                )}
              </p>
            )}
          </div>

          {/* Tabs */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            {/* Tab Navigation */}
            <div className="border-b border-gray-200">
              <nav className="flex -mb-px">
                <button
                  onClick={() => setActiveTab('summary')}
                  className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === 'summary'
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-600 hover:text-gray-800 hover:border-gray-300'
                  }`}
                >
                  Summary
                </button>
                <button
                  onClick={() => setActiveTab('pdf')}
                  className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === 'pdf'
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-600 hover:text-gray-800 hover:border-gray-300'
                  }`}
                >
                  PDF Document
                </button>
              </nav>
            </div>

            {/* Tab Content */}
            <div className="p-6">
              {activeTab === 'summary' && <CRLDetailContent crlId={crlId} />}
              {activeTab === 'pdf' && crl?.file_name && (
                <div className="h-[800px]">
                  <PDFViewer
                    pdfUrl={`https://download.open.fda.gov/crl/${crl.file_name}`}
                  />
                </div>
              )}
              {activeTab === 'pdf' && !crl?.file_name && (
                <div className="flex flex-col items-center justify-center p-12 text-gray-500">
                  <svg className="w-16 h-16 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <p className="text-lg font-medium">PDF Not Available</p>
                  <p className="text-sm mt-2">The PDF document for this CRL is not available.</p>
                </div>
              )}
            </div>
          </div>

          {/* Back to explorer link */}
          <div className="mt-6 text-center">
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
      </div>
    </>
  );
}
