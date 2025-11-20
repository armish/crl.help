/**
 * Main layout component for FDA CRL Explorer.
 *
 * Provides:
 * - Header with app title and navigation
 * - Main content area
 * - Footer with credits and links
 */

import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';

export default function Layout({ children }) {
  const location = useLocation();
  const [lastUpdate, setLastUpdate] = useState(null);
  const [isScrolled, setIsScrolled] = useState(false);

  const navItems = [
    { path: '/', label: 'Explore' },
    { path: '/search', label: 'Search' },
    { path: '/about-crl', label: 'What is a CRL?' },
    { path: 'https://github.com/armish/crl.help/issues', label: 'Feedback', external: true },
  ];

  // Handle scroll to shrink header
  useEffect(() => {
    let ticking = false;

    const handleScroll = () => {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          // Use a larger threshold (100px) to avoid jumpiness
          setIsScrolled(window.scrollY > 100);
          ticking = false;
        });
        ticking = true;
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Fetch last data update timestamp
  useEffect(() => {
    const fetchLastUpdate = async () => {
      try {
        const response = await fetch('/health');
        const data = await response.json();
        if (data.last_data_update) {
          // Format date from YYYY-MM-DD to readable format
          const date = new Date(data.last_data_update);
          const formatted = date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
          });
          setLastUpdate(formatted);
        }
      } catch (error) {
        console.error('Failed to fetch last update date:', error);
      }
    };

    fetchLastUpdate();
  }, []);

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* Header - Sticky and shrinks on scroll */}
      <header className={`bg-white shadow-sm border-b border-gray-200 sticky top-0 z-40 transition-all duration-500 ease-in-out ${
        isScrolled ? 'py-2' : 'py-4'
      }`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between gap-4">
            <Link to="/" className="hover:opacity-80 transition-opacity flex-shrink-0">
              <h1 className={`font-bold text-gray-900 transition-all duration-500 ease-in-out ${
                isScrolled ? 'text-xl' : 'text-[2rem]'
              }`}>
                FDA CRL Explorer
              </h1>
              <p className={`text-sm text-gray-600 mt-1 transition-all duration-500 ease-in-out overflow-hidden ${
                isScrolled ? 'max-h-0 opacity-0' : 'max-h-10 opacity-100'
              }`}>
                Complete Response Letter Database with AI-Powered Insights
              </p>
            </Link>

            {/* Navigation */}
            <nav className="hidden md:flex space-x-6 flex-shrink-0">
              {navItems.map((item) => (
                item.external ? (
                  <a
                    key={item.path}
                    href={item.path}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={`font-medium text-gray-600 hover:text-gray-900 transition-all duration-500 ease-in-out ${
                      isScrolled ? 'text-sm' : 'text-base'
                    }`}
                  >
                    {item.label}
                  </a>
                ) : (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`font-medium transition-all duration-500 ease-in-out ${
                      isScrolled ? 'text-sm' : 'text-base'
                    } ${
                      location.pathname === item.path
                        ? 'text-blue-600'
                        : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    {item.label}
                  </Link>
                )
              ))}
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
          <div className="flex flex-col md:flex-row justify-between items-center gap-4 text-sm text-gray-600">
            <div className="flex flex-col items-center md:items-start gap-2">
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
              {lastUpdate && (
                <p className="text-xs text-gray-500">
                  Last updated: {lastUpdate}
                </p>
              )}
              <Link
                to="/crl-index"
                className="text-xs text-blue-600 hover:text-blue-800 font-medium"
              >
                CRL Index
              </Link>
            </div>
            <div className="flex items-center gap-4">
              <a
                href="https://github.com/armish/crl.help"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 text-gray-600 hover:text-gray-900 font-medium transition-colors"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
                </svg>
                <span>GitHub</span>
              </a>
              <span className="hidden md:inline text-gray-400">|</span>
              <p className="hidden md:block">
                Built with React, FastAPI, and OpenAI
              </p>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
