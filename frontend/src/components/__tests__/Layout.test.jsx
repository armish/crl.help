/**
 * Tests for Layout component.
 *
 * Tests:
 * - Header renders correctly
 * - Navigation links render
 * - Children content renders
 * - Footer renders with credits and links
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Layout from '../Layout';

// Mock fetch for the health check
global.fetch = vi.fn(() =>
  Promise.resolve({
    json: () => Promise.resolve({ last_data_update: null }),
  })
);

// Helper to render Layout with Router
const renderLayout = (children) => {
  return render(
    <BrowserRouter>
      <Layout>{children}</Layout>
    </BrowserRouter>
  );
};

describe('Layout', () => {
  it('renders header with app title and tagline', () => {
    renderLayout(<div>Test Content</div>);

    expect(screen.getByText('FDA CRL Explorer')).toBeInTheDocument();
    expect(
      screen.getByText(/complete response letter database with ai-powered insights/i)
    ).toBeInTheDocument();
  });

  it('renders navigation links', () => {
    renderLayout(<div>Test Content</div>);

    // Get all links and check that the navigation ones exist
    const allLinks = screen.getAllByRole('link');
    const linkTexts = allLinks.map(link => link.textContent);

    expect(linkTexts).toContain('Explore');
    expect(linkTexts).toContain('What is a CRL?');
    expect(linkTexts).toContain('Feedback');
  });

  it('renders children content in main area', () => {
    const testContent = 'This is test content';

    renderLayout(<div>{testContent}</div>);

    expect(screen.getByText(testContent)).toBeInTheDocument();
  });

  it('renders footer with openFDA link', () => {
    renderLayout(<div>Test Content</div>);

    const openFDALink = screen.getByRole('link', { name: /openfda transparency api/i });

    expect(openFDALink).toBeInTheDocument();
    expect(openFDALink).toHaveAttribute(
      'href',
      'https://open.fda.gov/apis/transparency/crl/'
    );
    expect(openFDALink).toHaveAttribute('target', '_blank');
    expect(openFDALink).toHaveAttribute('rel', 'noopener noreferrer');
  });

  it('renders footer with tech stack credits', () => {
    renderLayout(<div>Test Content</div>);

    expect(screen.getByText(/built with react, fastapi, and openai/i)).toBeInTheDocument();
  });

  it('has correct semantic HTML structure', () => {
    const { container } = renderLayout(<div>Test Content</div>);

    const header = container.querySelector('header');
    const main = container.querySelector('main');
    const footer = container.querySelector('footer');

    expect(header).toBeInTheDocument();
    expect(main).toBeInTheDocument();
    expect(footer).toBeInTheDocument();
  });

  it('applies correct styling classes', () => {
    const { container } = renderLayout(<div>Test Content</div>);

    const rootDiv = container.firstChild;
    expect(rootDiv).toHaveClass('min-h-screen', 'flex', 'flex-col', 'bg-gray-50');
  });
});
