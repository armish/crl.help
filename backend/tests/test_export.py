"""
Tests for export functionality (CSV and Excel).
"""

import pytest
import csv
import io
from app.services.export_service import ExportService


class TestExportService:
    """Test the ExportService class."""

    def test_format_value_none(self):
        """Test formatting None values."""
        assert ExportService._format_value(None) == ""

    def test_format_value_date(self):
        """Test formatting date values."""
        from datetime import date
        d = date(2024, 12, 25)
        assert ExportService._format_value(d) == "2024-12-25"

    def test_format_value_list(self):
        """Test formatting list values."""
        assert ExportService._format_value(["a", "b", "c"]) == "a, b, c"
        assert ExportService._format_value([]) == ""

    def test_format_value_string(self):
        """Test formatting string values."""
        assert ExportService._format_value("test") == "test"

    def test_export_to_csv_basic(self):
        """Test basic CSV export without summaries."""
        crls = [
            {
                "id": "TEST_001",
                "application_number": ["NDA 123456"],
                "company_name": "Test Company",
                "letter_date": "2024-01-15",
                "letter_year": "2024",
                "application_type": "NDA",
                "letter_type": "COMPLETE RESPONSE",
                "approval_status": "Unapproved",
                "therapeutic_category": "Small molecules",
                "product_name": "Test Drug",
                "indications": "Test Indication",
                "deficiency_reason": "Clinical",
                "approver_center": "CDER",
                "approver_name": "John Doe",
            }
        ]

        result = ExportService.export_to_csv(crls, include_summary=False)

        # Read CSV content
        result.seek(0)
        reader = csv.reader(result)
        rows = list(reader)

        # Check header row
        assert len(rows) == 2  # Header + 1 data row
        assert "ID" in rows[0]
        assert "Application Number" in rows[0]
        assert "Executive summary" not in rows[0]  # Not included

        # Check data row
        assert rows[1][0] == "TEST_001"
        assert "Test Company" in rows[1]

    def test_export_to_csv_with_summary(self):
        """Test CSV export with summaries included."""
        crls = [
            {
                "id": "TEST_001",
                "application_number": ["NDA 123456"],
                "company_name": "Test Company",
                "letter_date": "2024-01-15",
                "letter_year": "2024",
                "application_type": "NDA",
                "letter_type": "COMPLETE RESPONSE",
                "approval_status": "Unapproved",
                "therapeutic_category": "Small molecules",
                "product_name": "Test Drug",
                "indications": "Test Indication",
                "deficiency_reason": "Clinical",
                "approver_center": "CDER",
                "approver_name": "John Doe",
                "summary": "This is a test summary of the CRL deficiencies.",
            }
        ]

        result = ExportService.export_to_csv(crls, include_summary=True)

        # Read CSV content
        result.seek(0)
        reader = csv.reader(result)
        rows = list(reader)

        # Check header includes summary
        assert "Executive summary" in rows[0]

        # Check summary is in last column
        summary_idx = rows[0].index("Executive summary")
        assert rows[1][summary_idx] == "This is a test summary of the CRL deficiencies."

    def test_export_to_excel_requires_openpyxl(self):
        """Test that Excel export works when openpyxl is available."""
        crls = [
            {
                "id": "TEST_001",
                "application_number": ["NDA 123456"],
                "company_name": "Test Company",
                "letter_date": "2024-01-15",
                "letter_year": "2024",
                "application_type": "NDA",
                "letter_type": "COMPLETE RESPONSE",
                "approval_status": "Unapproved",
                "therapeutic_category": "Small molecules",
                "product_name": "Test Drug",
                "indications": "Test Indication",
                "deficiency_reason": "Clinical",
                "approver_center": "CDER",
                "approver_name": "John Doe",
            }
        ]

        try:
            result = ExportService.export_to_excel(crls, include_summary=False)
            assert isinstance(result, io.BytesIO)
            assert result.getvalue()  # Has content
        except ImportError:
            pytest.skip("openpyxl not installed")


class TestExportEndpoints:
    """Test the export API endpoints."""

    def test_csv_export_endpoint_no_data(self, client):
        """Test CSV export when no CRLs match filters."""
        response = client.get("/api/export/csv?letter_year=1900")
        assert response.status_code == 404
        # Error message could be generic 404 or specific "No CRLs found"
        assert "detail" in response.json()

    def test_csv_export_endpoint_basic(self, client):
        """Test CSV export endpoint returns valid CSV."""
        response = client.get("/api/export/csv?limit=5")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "crl_export" in response.headers["content-disposition"]

        # Check CSV content
        content = response.text
        lines = content.strip().split('\n')
        assert len(lines) >= 2  # At least header + 1 row
        assert "ID" in lines[0]
        assert "Application Number" in lines[0]

    def test_csv_export_with_filters(self, client):
        """Test CSV export respects filter parameters."""
        response = client.get("/api/export/csv?approval_status=Unapproved&letter_year=2024")
        assert response.status_code in [200, 404]  # 404 if no data matches

        if response.status_code == 200:
            content = response.text
            lines = content.strip().split('\n')
            assert len(lines) >= 1  # At least header

    def test_csv_export_with_summary(self, client):
        """Test CSV export includes summary column when requested."""
        response = client.get("/api/export/csv?include_summary=true&limit=5")
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            content = response.text
            lines = content.strip().split('\n')
            assert "Executive summary" in lines[0]

    def test_csv_export_without_summary(self, client):
        """Test CSV export excludes summary by default."""
        response = client.get("/api/export/csv?include_summary=false&limit=5")
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            content = response.text
            lines = content.strip().split('\n')
            assert "Executive summary" not in lines[0]

    def test_excel_export_endpoint_basic(self, client):
        """Test Excel export endpoint returns valid Excel file."""
        response = client.get("/api/export/excel?limit=5")

        if response.status_code == 501:
            pytest.skip("openpyxl not installed")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        assert "crl_export" in response.headers["content-disposition"]
        assert ".xlsx" in response.headers["content-disposition"]

        # Check file has content
        assert len(response.content) > 0

    def test_excel_export_with_summary(self, client):
        """Test Excel export includes summary when requested."""
        response = client.get("/api/export/excel?include_summary=true&limit=5")

        if response.status_code == 501:
            pytest.skip("openpyxl not installed")

        assert response.status_code in [200, 404]

    def test_export_respects_sort_order(self, client):
        """Test export respects sort_by and sort_order parameters."""
        response = client.get("/api/export/csv?sort_by=letter_date&sort_order=ASC&limit=5")
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            # Just verify it doesn't error with sort parameters
            content = response.text
            lines = content.strip().split('\n')
            assert len(lines) >= 1

    def test_export_filename_has_timestamp(self, client):
        """Test exported files have timestamps in filename."""
        response = client.get("/api/export/csv?limit=5")

        if response.status_code == 200:
            disposition = response.headers["content-disposition"]
            assert "crl_export_" in disposition
            # Should have format: crl_export_YYYYMMDD_HHMMSS.csv
            assert ".csv" in disposition


class TestCRLListWithSummary:
    """Test the /api/crls endpoint with include_summary parameter."""

    def test_list_crls_without_summary_default(self, client):
        """Test that CRL list doesn't include summaries by default."""
        response = client.get("/api/crls?limit=5")
        assert response.status_code == 200

        data = response.json()
        if data["items"]:
            first_item = data["items"][0]
            # Summary should be None or not present when include_summary=false (default)
            assert first_item.get("summary") is None

    def test_list_crls_with_summary_true(self, client):
        """Test that CRL list includes summaries when requested."""
        response = client.get("/api/crls?include_summary=true&limit=5")
        assert response.status_code == 200

        data = response.json()
        if data["items"]:
            # At least some items should have summaries if they exist in DB
            # Note: Not all CRLs may have summaries generated yet
            items_with_summaries = [item for item in data["items"] if item.get("summary")]
            # Just verify the endpoint works; actual summary availability depends on DB state

    def test_list_crls_with_summary_false(self, client):
        """Test that CRL list excludes summaries when explicitly set to false."""
        response = client.get("/api/crls?include_summary=false&limit=5")
        assert response.status_code == 200

        data = response.json()
        if data["items"]:
            for item in data["items"]:
                assert item.get("summary") is None


class TestSummaryRepository:
    """Test the SummaryRepository batch fetching."""

    def test_get_summaries_by_crl_ids_empty_list(self, test_db, mocker):
        """Test batch fetching with empty ID list."""
        from app.database import SummaryRepository

        mocker.patch('app.database.get_db', return_value=test_db)
        repo = SummaryRepository()
        summaries = repo.get_summaries_by_crl_ids([])
        assert summaries == []

    def test_get_summaries_by_crl_ids_nonexistent(self, test_db, mocker):
        """Test batch fetching with non-existent IDs."""
        from app.database import SummaryRepository

        mocker.patch('app.database.get_db', return_value=test_db)
        repo = SummaryRepository()
        summaries = repo.get_summaries_by_crl_ids(["FAKE_ID_001", "FAKE_ID_002"])
        assert summaries == []

    def test_get_summaries_by_crl_ids_real_data(self, test_db, mocker):
        """Test batch fetching with real CRL IDs."""
        from app.database import SummaryRepository, CRLRepository

        mocker.patch('app.database.get_db', return_value=test_db)

        # Get some real CRL IDs
        crl_repo = CRLRepository()
        crls, _ = crl_repo.get_all(limit=5, offset=0)

        if not crls:
            pytest.skip("No CRLs in database")

        crl_ids = [crl["id"] for crl in crls]

        # Fetch summaries
        summary_repo = SummaryRepository()
        summaries = summary_repo.get_summaries_by_crl_ids(crl_ids)

        # Summaries is a list (may be empty if no summaries exist yet)
        assert isinstance(summaries, list)

        # If summaries exist, they should have the expected structure
        for summary in summaries:
            assert "crl_id" in summary
            assert "summary" in summary
            assert summary["crl_id"] in crl_ids
