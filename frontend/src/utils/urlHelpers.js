/**
 * Utility functions for generating SEO-friendly URLs for CRL pages.
 */

/**
 * Convert a string to a URL-friendly slug
 * @param {string} text - Text to convert to slug
 * @returns {string} URL-friendly slug
 */
const slugify = (text) => {
  if (!text) return '';

  return text
    .toString()
    .toLowerCase()
    .trim()
    .replace(/\s+/g, '-')           // Replace spaces with -
    .replace(/[^\w\-]+/g, '')       // Remove all non-word chars
    .replace(/\-\-+/g, '-')         // Replace multiple - with single -
    .replace(/^-+/, '')             // Trim - from start of text
    .replace(/-+$/, '');            // Trim - from end of text
};

/**
 * Generate a SEO-friendly URL for a CRL detail page
 * @param {Object} crl - CRL object with id, letter_type, application_type, company_name, product_name, therapeutic_category
 * @returns {string} URL path for the CRL detail page
 *
 * URL format: /crl/{id}/{letter-type}-{application-type}-{company-name}-{therapeutic-category}
 * Example: /crl/BLA125360-2020/bla-original-pfizer-biologics
 */
export const getCRLDetailUrl = (crl) => {
  if (!crl || !crl.id) {
    return '/';
  }

  const parts = [];

  // Add letter type if available
  if (crl.letter_type) {
    parts.push(slugify(crl.letter_type));
  }

  // Add application type if available
  if (crl.application_type) {
    parts.push(slugify(crl.application_type));
  }

  // Add company name if available
  if (crl.company_name) {
    parts.push(slugify(crl.company_name));
  }

  // Add therapeutic category if available
  if (crl.therapeutic_category) {
    parts.push(slugify(crl.therapeutic_category));
  }

  // Create the slug portion (the descriptive part after the ID)
  const slug = parts.filter(Boolean).join('-');

  // Return full URL path
  if (slug) {
    return `/crl/${crl.id}/${slug}`;
  }

  // Fallback if no descriptive information is available
  return `/crl/${crl.id}`;
};

/**
 * Parse CRL ID from URL pathname
 * The ID is always the first segment after /crl/
 * @param {string} pathname - URL pathname (e.g., '/crl/BLA125360-2020/bla-pfizer-comirnaty')
 * @returns {string|null} CRL ID or null if invalid
 */
export const parseCRLIdFromUrl = (pathname) => {
  const match = pathname.match(/^\/crl\/([^\/]+)/);
  return match ? match[1] : null;
};
