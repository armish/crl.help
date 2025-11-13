/**
 * Tests for Layout component.
 *
 * Tests:
 * - Header renders correctly
 * - Navigation links render
 * - Children content renders
 * - Footer renders with credits and links
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import Layout from '../Layout';

describe('Layout', () => {
  it('renders header with app title and tagline', () => {
    render(
      <Layout>
        <div>Test Content</div>
      </Layout>
    );

    expect(screen.getByText('FDA CRL Explorer')).toBeInTheDocument();
    expect(
      screen.getByText(/complete response letter database with ai-powered insights/i)
    ).toBeInTheDocument();
  });

  it('renders navigation links', () => {
    render(
      <Layout>
        <div>Test Content</div>
      </Layout>
    );

    const browseLink = screen.getByRole('link', { name: /browse/i });
    const qaLink = screen.getByRole('link', { name: /q&a/i });
    const aboutLink = screen.getByRole('link', { name: /about/i });

    expect(browseLink).toBeInTheDocument();
    expect(qaLink).toBeInTheDocument();
    expect(aboutLink).toBeInTheDocument();
  });

  it('renders children content in main area', () => {
    const testContent = 'This is test content';

    render(
      <Layout>
        <div>{testContent}</div>
      </Layout>
    );

    expect(screen.getByText(testContent)).toBeInTheDocument();
  });

  it('renders footer with openFDA link', () => {
    render(
      <Layout>
        <div>Test Content</div>
      </Layout>
    );

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
    render(
      <Layout>
        <div>Test Content</div>
      </Layout>
    );

    expect(screen.getByText(/built with react, fastapi, and openai/i)).toBeInTheDocument();
  });

  it('has correct semantic HTML structure', () => {
    const { container } = render(
      <Layout>
        <div>Test Content</div>
      </Layout>
    );

    const header = container.querySelector('header');
    const main = container.querySelector('main');
    const footer = container.querySelector('footer');

    expect(header).toBeInTheDocument();
    expect(main).toBeInTheDocument();
    expect(footer).toBeInTheDocument();
  });

  it('applies correct styling classes', () => {
    const { container } = render(
      <Layout>
        <div>Test Content</div>
      </Layout>
    );

    const rootDiv = container.firstChild;
    expect(rootDiv).toHaveClass('min-h-screen', 'flex', 'flex-col', 'bg-gray-50');
  });
});
