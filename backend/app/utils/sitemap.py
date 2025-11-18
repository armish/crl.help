"""
Sitemap generation utilities for SEO.

Generates XML sitemaps for search engine crawlers to discover and index
all CRL pages and static pages.
"""

from datetime import datetime
from typing import List, Dict
import re


def slugify(text: str) -> str:
    """
    Convert text to URL-friendly slug.

    Args:
        text: Text to convert

    Returns:
        URL-friendly slug
    """
    if not text:
        return ""

    # Convert to lowercase and strip
    slug = text.lower().strip()

    # Replace spaces with hyphens
    slug = re.sub(r'\s+', '-', slug)

    # Remove non-word characters (keep hyphens)
    slug = re.sub(r'[^\w\-]', '', slug)

    # Replace multiple hyphens with single hyphen
    slug = re.sub(r'\-+', '-', slug)

    # Trim hyphens from start and end
    slug = slug.strip('-')

    return slug


def generate_crl_url(crl: Dict, base_url: str) -> str:
    """
    Generate SEO-friendly URL for a CRL.

    Args:
        crl: CRL data dictionary with id, letter_type, application_type,
             company_name, therapeutic_category
        base_url: Base URL of the site (e.g., 'https://crl.help')

    Returns:
        Complete URL for the CRL detail page
    """
    if not crl or not crl.get('id'):
        return f"{base_url}/"

    parts = []

    # Add letter type if available
    if crl.get('letter_type'):
        parts.append(slugify(crl['letter_type']))

    # Add application type if available
    if crl.get('application_type'):
        parts.append(slugify(crl['application_type']))

    # Add company name if available
    if crl.get('company_name'):
        parts.append(slugify(crl['company_name']))

    # Add therapeutic category if available
    if crl.get('therapeutic_category'):
        parts.append(slugify(crl['therapeutic_category']))

    # Create the slug portion
    slug = '-'.join([p for p in parts if p])

    # Return full URL
    if slug:
        return f"{base_url}/crl/{crl['id']}/{slug}"

    return f"{base_url}/crl/{crl['id']}"


def generate_sitemap_xml(crls: List[Dict], base_url: str = "https://crl.help") -> str:
    """
    Generate XML sitemap for all pages.

    Args:
        crls: List of CRL dictionaries
        base_url: Base URL of the site

    Returns:
        XML sitemap string
    """
    # Start XML
    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]

    # Add static pages
    static_pages = [
        {'loc': f"{base_url}/", 'priority': '1.0', 'changefreq': 'daily'},
        {'loc': f"{base_url}/about-crl", 'priority': '0.8', 'changefreq': 'monthly'},
        {'loc': f"{base_url}/crl-index", 'priority': '0.9', 'changefreq': 'weekly'},
    ]

    for page in static_pages:
        xml_lines.append('  <url>')
        xml_lines.append(f'    <loc>{page["loc"]}</loc>')
        xml_lines.append(f'    <changefreq>{page["changefreq"]}</changefreq>')
        xml_lines.append(f'    <priority>{page["priority"]}</priority>')
        xml_lines.append('  </url>')

    # Add CRL pages
    for crl in crls:
        url = generate_crl_url(crl, base_url)

        # Get last modified date if available
        lastmod = None
        if crl.get('updated_at'):
            try:
                if isinstance(crl['updated_at'], str):
                    # Parse ISO format
                    lastmod = datetime.fromisoformat(crl['updated_at'].replace('Z', '+00:00'))
                else:
                    lastmod = crl['updated_at']
            except (ValueError, TypeError):
                pass

        xml_lines.append('  <url>')
        xml_lines.append(f'    <loc>{url}</loc>')
        if lastmod:
            xml_lines.append(f'    <lastmod>{lastmod.strftime("%Y-%m-%d")}</lastmod>')
        xml_lines.append('    <changefreq>monthly</changefreq>')
        xml_lines.append('    <priority>0.7</priority>')
        xml_lines.append('  </url>')

    # Close XML
    xml_lines.append('</urlset>')

    return '\n'.join(xml_lines)
