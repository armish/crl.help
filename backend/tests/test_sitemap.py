"""
Tests for sitemap generation.
"""

import pytest
from app.utils.sitemap import slugify, generate_crl_url, generate_sitemap_xml


class TestSlugify:
    """Test the slugify function."""

    def test_slugify_simple(self):
        """Test basic slugification."""
        assert slugify("Hello World") == "hello-world"

    def test_slugify_with_special_chars(self):
        """Test slugification with special characters."""
        assert slugify("Hello & World!") == "hello-world"

    def test_slugify_multiple_spaces(self):
        """Test slugification with multiple spaces."""
        assert slugify("Hello    World") == "hello-world"

    def test_slugify_trailing_hyphens(self):
        """Test slugification removes trailing hyphens."""
        assert slugify("Hello-") == "hello"
        assert slugify("-Hello-") == "hello"

    def test_slugify_empty_string(self):
        """Test slugification of empty string."""
        assert slugify("") == ""

    def test_slugify_none(self):
        """Test slugification of None."""
        assert slugify(None) == ""


class TestGenerateCRLUrl:
    """Test CRL URL generation."""

    def test_generate_crl_url_full(self):
        """Test URL generation with all fields."""
        crl = {
            'id': 'BLA125360-2020',
            'letter_type': 'BLA',
            'application_type': 'Original',
            'company_name': 'Pfizer Inc.',
            'therapeutic_category': 'Biologics'
        }
        url = generate_crl_url(crl, "https://crl.help")
        assert url == "https://crl.help/crl/BLA125360-2020/bla-original-pfizer-inc-biologics"

    def test_generate_crl_url_partial(self):
        """Test URL generation with some fields missing."""
        crl = {
            'id': 'NDA123456-2021',
            'letter_type': 'NDA',
            'company_name': 'Test Company'
        }
        url = generate_crl_url(crl, "https://crl.help")
        assert url == "https://crl.help/crl/NDA123456-2021/nda-test-company"

    def test_generate_crl_url_id_only(self):
        """Test URL generation with only ID."""
        crl = {'id': 'TEST-2022'}
        url = generate_crl_url(crl, "https://crl.help")
        assert url == "https://crl.help/crl/TEST-2022"

    def test_generate_crl_url_no_id(self):
        """Test URL generation without ID."""
        crl = {'company_name': 'Test'}
        url = generate_crl_url(crl, "https://crl.help")
        assert url == "https://crl.help/"

    def test_generate_crl_url_empty(self):
        """Test URL generation with empty dict."""
        url = generate_crl_url({}, "https://crl.help")
        assert url == "https://crl.help/"


class TestGenerateSitemapXml:
    """Test sitemap XML generation."""

    def test_generate_sitemap_empty(self):
        """Test sitemap generation with no CRLs."""
        xml = generate_sitemap_xml([], "https://crl.help")

        # Should still have static pages
        assert '<?xml version="1.0" encoding="UTF-8"?>' in xml
        assert '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' in xml
        assert '<loc>https://crl.help/</loc>' in xml
        assert '<loc>https://crl.help/about-crl</loc>' in xml
        assert '<loc>https://crl.help/crl-index</loc>' in xml
        assert '</urlset>' in xml

    def test_generate_sitemap_with_crls(self):
        """Test sitemap generation with CRLs."""
        crls = [
            {
                'id': 'BLA125360-2020',
                'letter_type': 'BLA',
                'application_type': 'Original',
                'company_name': 'Pfizer',
                'therapeutic_category': 'Biologics',
                'updated_at': '2023-01-15T10:00:00'
            },
            {
                'id': 'NDA123456-2021',
                'letter_type': 'NDA',
                'company_name': 'Test Co'
            }
        ]

        xml = generate_sitemap_xml(crls, "https://crl.help")

        # Check static pages
        assert '<loc>https://crl.help/</loc>' in xml
        assert '<loc>https://crl.help/about-crl</loc>' in xml

        # Check CRL URLs
        assert '<loc>https://crl.help/crl/BLA125360-2020/bla-original-pfizer-biologics</loc>' in xml
        assert '<loc>https://crl.help/crl/NDA123456-2021/nda-test-co</loc>' in xml

        # Check lastmod for first CRL
        assert '<lastmod>2023-01-15</lastmod>' in xml

        # Check priorities and changefreq
        assert '<priority>1.0</priority>' in xml  # Homepage
        assert '<priority>0.7</priority>' in xml  # CRL pages
        assert '<changefreq>daily</changefreq>' in xml  # Homepage
        assert '<changefreq>monthly</changefreq>' in xml  # CRL pages

    def test_generate_sitemap_structure(self):
        """Test sitemap XML structure is valid."""
        crls = [{'id': 'TEST-123', 'company_name': 'Test'}]
        xml = generate_sitemap_xml(crls, "https://crl.help")

        # Check XML structure
        lines = xml.split('\n')
        assert lines[0] == '<?xml version="1.0" encoding="UTF-8"?>'
        assert lines[1] == '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        assert lines[-1] == '</urlset>'

        # Check URL blocks are properly formatted
        assert xml.count('<url>') == xml.count('</url>')
        assert xml.count('<loc>') == xml.count('</loc>')

    def test_generate_sitemap_custom_base_url(self):
        """Test sitemap generation with custom base URL."""
        crls = [{'id': 'TEST-123', 'company_name': 'Test'}]
        xml = generate_sitemap_xml(crls, "https://example.com")

        assert '<loc>https://example.com/</loc>' in xml
        assert '<loc>https://example.com/crl/TEST-123/test</loc>' in xml
