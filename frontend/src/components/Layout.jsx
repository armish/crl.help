/**
 * Main layout component for FDA CRL Explorer.
 *
 * Provides:
 * - Header with app title and navigation
 * - Main content area
 * - Footer with credits and links
 */

export default function Layout({ children }) {
  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                FDA CRL Explorer
              </h1>
              <p className="text-sm text-gray-600 mt-1">
                Complete Response Letter Database with AI-Powered Insights
              </p>
            </div>

            {/* Navigation (future) */}
            <nav className="hidden md:flex space-x-6">
              <a href="#" className="text-gray-600 hover:text-gray-900 font-medium">
                Browse
              </a>
              <a href="#" className="text-gray-600 hover:text-gray-900 font-medium">
                Q&A
              </a>
              <a href="#" className="text-gray-600 hover:text-gray-900 font-medium">
                About
              </a>
            </nav>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex flex-col md:flex-row justify-between items-center text-sm text-gray-600">
            <p>
              Data from{' '}
              <a
                href="https://open.fda.gov/apis/transparency/crl/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-800 font-medium"
              >
                openFDA Transparency API
              </a>
            </p>
            <p className="mt-2 md:mt-0">
              Built with React, FastAPI, and OpenAI
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
