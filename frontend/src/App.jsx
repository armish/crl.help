/**
 * Main App component for FDA CRL Explorer.
 *
 * Sets up:
 * - React Query Provider for data fetching
 * - React Router for navigation
 * - React Helmet Async Provider for SEO metadata
 * - Main layout
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { HelmetProvider } from 'react-helmet-async';
import Layout from './components/Layout';
import HomePage from './pages/HomePage';
import AboutCRL from './pages/AboutCRL';
import CRLDetailPage from './pages/CRLDetailPage';
import CRLIndexPage from './pages/CRLIndexPage';
import SearchPage from './pages/SearchPage';

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1, // Retry failed requests once
      refetchOnWindowFocus: false, // Don't refetch when window regains focus
      staleTime: 5 * 60 * 1000, // Data is fresh for 5 minutes
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <HelmetProvider>
        <BrowserRouter>
          <Layout>
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/search" element={<SearchPage />} />
              <Route path="/about-crl" element={<AboutCRL />} />
              <Route path="/crl-index" element={<CRLIndexPage />} />
              <Route path="/crl/*" element={<CRLDetailPage />} />
            </Routes>
          </Layout>
        </BrowserRouter>
      </HelmetProvider>
    </QueryClientProvider>
  );
}

export default App;
