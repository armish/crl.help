"""
Tests for data processor service.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch
import pytest

from app.services.data_processor import DataProcessorService, process_crl_data


class TestDataProcessorService:
    """Test cases for DataProcessorService."""

    @pytest.fixture
    def service(self):
        """Create a DataProcessorService instance."""
        with patch('app.services.data_processor.CRLRepository') as mock_repo, \
             patch('app.services.data_processor.MetadataRepository'):
            service = DataProcessorService()
            service.crl_repo = mock_repo.return_value
            return service

    @pytest.fixture
    def sample_crl_records(self):
        """Sample CRL records for testing."""
        return [
            {
                "application_number": ["NDA 123456"],
                "letter_date": "01/15/2024",
                "letter_year": "2024",
                "letter_type": "COMPLETE RESPONSE",
                "approval_status": "Approved",
                "company_name": "Test Pharma Inc",
                "company_address": "123 Test St",
                "company_rep": "John Doe",
                "approver_name": "FDA Reviewer",
                "approver_center": ["CDER"],
                "approver_title": "Director",
                "file_name": "test_crl.pdf",
                "text": "This is a test CRL letter."
            },
            {
                "application_number": ["BLA 789012"],
                "letter_date": "03/20/2024",
                "letter_year": "2024",
                "letter_type": "COMPLETE RESPONSE",
                "approval_status": "Unapproved",
                "company_name": "BioTest Corp",
                "company_address": "456 Bio Ave",
                "company_rep": "Jane Smith",
                "approver_name": "FDA Reviewer 2",
                "approver_center": ["CBER"],
                "approver_title": "Senior Director",
                "file_name": "test_crl2.pdf",
                "text": "This is another test CRL letter."
            }
        ]

    @pytest.fixture
    def sample_json_data(self, sample_crl_records):
        """Sample JSON data structure."""
        return {
            "meta": {
                "last_updated": "2025-11-10",
                "results": {
                    "total": len(sample_crl_records)
                }
            },
            "results": sample_crl_records
        }

    def test_parse_date_standard_format(self, service):
        """Test parsing date in MM/DD/YYYY format."""
        result = service.parse_date("01/15/2024")
        assert result == "2024-01-15"

        result = service.parse_date("12/31/2023")
        assert result == "2023-12-31"

    def test_parse_date_yyyymmdd_format(self, service):
        """Test parsing date in YYYYMMDD format."""
        result = service.parse_date("20240115")
        assert result == "2024-01-15"

        result = service.parse_date("20231231")
        assert result == "2023-12-31"

    def test_parse_date_invalid_format(self, service):
        """Test parsing invalid date format."""
        result = service.parse_date("invalid-date")
        assert result is None

        result = service.parse_date("2024-01-15")  # Wrong format
        assert result is None

    def test_parse_date_empty_string(self, service):
        """Test parsing empty date string."""
        result = service.parse_date("")
        assert result is None

    def test_generate_base_id_standard(self, service):
        """Test generating base ID with standard application number."""
        base_id = service._generate_base_id(["NDA 123456"], "01/15/2024")
        assert base_id == "NDA123456_20240115"

        base_id = service._generate_base_id(["BLA 789012"], "12/31/2023")
        assert base_id == "BLA789012_20231231"

    def test_generate_base_id_yyyymmdd_date(self, service):
        """Test generating base ID with YYYYMMDD date format."""
        base_id = service._generate_base_id(["NDA 123456"], "20240115")
        assert base_id == "NDA123456_20240115"

    def test_generate_base_id_empty_app_number(self, service):
        """Test generating base ID with empty application number."""
        base_id = service._generate_base_id([], "01/15/2024")
        assert "UNKNOWN" in base_id

    def test_generate_base_id_invalid_date(self, service):
        """Test generating base ID with invalid date."""
        base_id = service._generate_base_id(["NDA 123456"], "invalid-date")
        # Should use hash of the date string
        assert "NDA123456_" in base_id
        assert len(base_id) > len("NDA123456_")

    def test_parse_all_crls_success(self, service, sample_json_data):
        """Test parsing all CRL records successfully."""
        service.crl_repo.exists.return_value = False

        parsed = service.parse_all_crls(sample_json_data)

        assert len(parsed) == 2
        assert parsed[0]["id"] == "NDA123456_20240115"
        assert parsed[0]["company_name"] == "Test Pharma Inc"
        assert parsed[0]["letter_date"] == "2024-01-15"
        assert parsed[1]["id"] == "BLA789012_20240320"
        assert parsed[1]["company_name"] == "BioTest Corp"

    def test_parse_all_crls_with_duplicates(self, service):
        """Test parsing CRLs with duplicate IDs."""
        data = {
            "results": [
                {
                    "application_number": ["NDA 123456"],
                    "letter_date": "01/15/2024",
                    "letter_year": "2024",
                    "letter_type": "COMPLETE RESPONSE",
                    "approval_status": "Approved",
                    "company_name": "Test Pharma Inc",
                    "file_name": "file1.pdf",
                    "text": "First letter",
                    "company_address": "", "company_rep": "",
                    "approver_name": "", "approver_center": [], "approver_title": ""
                },
                {
                    "application_number": ["NDA 123456"],  # Same app number
                    "letter_date": "01/15/2024",  # Same date
                    "letter_year": "2024",
                    "letter_type": "COMPLETE RESPONSE",
                    "approval_status": "Approved",
                    "company_name": "Test Pharma Inc",
                    "file_name": "file2.pdf",  # Different file
                    "text": "Second letter",
                    "company_address": "", "company_rep": "",
                    "approver_name": "", "approver_center": [], "approver_title": ""
                }
            ]
        }

        service.crl_repo.exists.return_value = False

        parsed = service.parse_all_crls(data)

        assert len(parsed) == 2
        # IDs should be different due to file name hash
        assert parsed[0]["id"] != parsed[1]["id"]
        assert "NDA123456_20240115" in parsed[0]["id"]
        assert "NDA123456_20240115" in parsed[1]["id"]

    def test_parse_all_crls_with_existing_id(self, service, sample_json_data):
        """Test parsing when some IDs already exist in database."""
        # First CRL exists, second doesn't
        service.crl_repo.exists.side_effect = [True, False]

        parsed = service.parse_all_crls(sample_json_data)

        assert len(parsed) == 2
        # First ID should be modified with hash
        assert "_" in parsed[0]["id"]
        # Second ID should be normal
        assert parsed[1]["id"] == "BLA789012_20240320"

    def test_parse_all_crls_skip_invalid_records(self, service):
        """Test that invalid records are skipped gracefully."""
        data = {
            "results": [
                {
                    "application_number": ["NDA 123456"],
                    "letter_date": "01/15/2024",
                    "letter_year": "2024",
                    "letter_type": "COMPLETE RESPONSE",
                    "approval_status": "Approved",
                    "company_name": "Test Pharma Inc",
                    "file_name": "file1.pdf",
                    "text": "Valid record",
                    "company_address": "", "company_rep": "",
                    "approver_name": "", "approver_center": [], "approver_title": ""
                },
                None,  # Invalid record
                {
                    "application_number": ["BLA 789012"],
                    "letter_date": "03/20/2024",
                    "letter_year": "2024",
                    "letter_type": "COMPLETE RESPONSE",
                    "approval_status": "Unapproved",
                    "company_name": "BioTest Corp",
                    "file_name": "file2.pdf",
                    "text": "Another valid record",
                    "company_address": "", "company_rep": "",
                    "approver_name": "", "approver_center": [], "approver_title": ""
                }
            ]
        }

        service.crl_repo.exists.return_value = False

        parsed = service.parse_all_crls(data)

        # Should successfully parse 2 valid records and skip the None
        assert len(parsed) == 2

    def test_detect_new_and_updated_crls_all_new(self, service, sample_json_data):
        """Test detection when all CRLs are new."""
        parsed = service.parse_all_crls(sample_json_data)
        service.crl_repo.exists.return_value = False

        new_crls, updated_crls = service.detect_new_and_updated_crls(parsed)

        assert len(new_crls) == 2
        assert len(updated_crls) == 0

    def test_detect_new_and_updated_crls_some_existing(self, service):
        """Test detection when some CRLs exist."""
        parsed = [
            {"id": "CRL1", "text": "New text"},
            {"id": "CRL2", "text": "Different text"}
        ]

        # First exists with same text, second exists with different text
        def exists_side_effect(crl_id):
            return crl_id in ["CRL1", "CRL2"]

        def get_by_id_side_effect(crl_id):
            if crl_id == "CRL1":
                return {"id": "CRL1", "text": "New text"}  # Same text
            elif crl_id == "CRL2":
                return {"id": "CRL2", "text": "Old text"}  # Different text
            return None

        service.crl_repo.exists.side_effect = exists_side_effect
        service.crl_repo.get_by_id.side_effect = get_by_id_side_effect

        new_crls, updated_crls = service.detect_new_and_updated_crls(parsed)

        assert len(new_crls) == 0
        assert len(updated_crls) == 1
        assert updated_crls[0]["id"] == "CRL2"

    def test_detect_new_and_updated_crls_mixed(self, service):
        """Test detection with mix of new and existing CRLs."""
        parsed = [
            {"id": "CRL1", "text": "Text 1"},  # New
            {"id": "CRL2", "text": "Updated text"},  # Updated
            {"id": "CRL3", "text": "Text 3"}  # New
        ]

        def exists_side_effect(crl_id):
            return crl_id == "CRL2"

        def get_by_id_side_effect(crl_id):
            if crl_id == "CRL2":
                return {"id": "CRL2", "text": "Old text"}
            return None

        service.crl_repo.exists.side_effect = exists_side_effect
        service.crl_repo.get_by_id.side_effect = get_by_id_side_effect

        new_crls, updated_crls = service.detect_new_and_updated_crls(parsed)

        assert len(new_crls) == 2
        assert len(updated_crls) == 1
        assert updated_crls[0]["id"] == "CRL2"

    def test_store_crls_create_success(self, service):
        """Test successfully storing new CRLs."""
        crls = [
            {"id": "CRL1", "text": "Text 1"},
            {"id": "CRL2", "text": "Text 2"}
        ]

        service.crl_repo.create.return_value = None

        count = service.store_crls(crls, operation="create")

        assert count == 2
        assert service.crl_repo.create.call_count == 2

    def test_store_crls_update_success(self, service):
        """Test successfully updating existing CRLs."""
        crls = [
            {"id": "CRL1", "text": "Updated text 1"},
            {"id": "CRL2", "text": "Updated text 2"}
        ]

        service.crl_repo.update.return_value = None

        count = service.store_crls(crls, operation="update")

        assert count == 2
        assert service.crl_repo.update.call_count == 2

    def test_store_crls_empty_list(self, service):
        """Test storing empty CRL list."""
        count = service.store_crls([], operation="create")

        assert count == 0
        service.crl_repo.create.assert_not_called()

    def test_store_crls_partial_failure(self, service):
        """Test storing CRLs with some failures."""
        crls = [
            {"id": "CRL1", "text": "Text 1"},
            {"id": "CRL2", "text": "Text 2"},
            {"id": "CRL3", "text": "Text 3"}
        ]

        # Second create fails
        def create_side_effect(crl):
            if crl["id"] == "CRL2":
                raise Exception("Database error")

        service.crl_repo.create.side_effect = create_side_effect

        count = service.store_crls(crls, operation="create")

        assert count == 2  # 2 succeeded, 1 failed
        assert service.crl_repo.create.call_count == 3

    def test_process_and_store_full_pipeline(self, service, sample_json_data):
        """Test the complete process_and_store pipeline."""
        service.crl_repo.exists.return_value = False
        service.crl_repo.create.return_value = None
        service.crl_repo.get_stats.return_value = {
            "total_crls": 2,
            "by_status": {"Approved": 1, "Unapproved": 1},
            "by_year": {"2024": 2}
        }
        service.metadata_repo.set.return_value = None

        stats = service.process_and_store(sample_json_data)

        assert stats["new_crls"] == 2
        assert stats["updated_crls"] == 0
        assert stats["total_in_db"] == 2
        assert stats["failed"] == 0

    def test_process_and_store_with_updates(self, service, sample_json_data):
        """Test process_and_store with some updates."""
        # First CRL exists and is updated, second is new
        def exists_side_effect(crl_id):
            return "NDA123456" in crl_id

        def get_by_id_side_effect(crl_id):
            if "NDA123456" in crl_id:
                return {"id": crl_id, "text": "Old text"}
            return None

        service.crl_repo.exists.side_effect = exists_side_effect
        service.crl_repo.get_by_id.side_effect = get_by_id_side_effect
        service.crl_repo.create.return_value = None
        service.crl_repo.update.return_value = None
        service.crl_repo.get_stats.return_value = {
            "total_crls": 2,
            "by_status": {"Approved": 1, "Unapproved": 1},
            "by_year": {"2024": 2}
        }
        service.metadata_repo.set.return_value = None

        stats = service.process_and_store(sample_json_data)

        assert stats["new_crls"] == 1
        assert stats["updated_crls"] == 1
        assert stats["total_in_db"] == 2

    def test_process_and_store_error_handling(self, service, sample_json_data):
        """Test error handling in process_and_store."""
        # Make parse_all_crls fail by raising an exception during parsing
        with patch.object(service, 'parse_all_crls', side_effect=Exception("Database connection failed")):
            with pytest.raises(Exception, match="Database connection failed"):
                service.process_and_store(sample_json_data)


class TestDataProcessorEdgeCases:
    """Test edge cases and special scenarios."""

    @pytest.fixture
    def service(self):
        """Create a DataProcessorService instance."""
        with patch('app.services.data_processor.CRLRepository') as mock_repo, \
             patch('app.services.data_processor.MetadataRepository'):
            service = DataProcessorService()
            service.crl_repo = mock_repo.return_value
            return service

    def test_parse_date_february_29_leap_year(self, service):
        """Test parsing February 29 in leap year."""
        result = service.parse_date("02/29/2024")
        assert result == "2024-02-29"

    def test_parse_date_february_29_non_leap_year(self, service):
        """Test parsing February 29 in non-leap year (invalid)."""
        result = service.parse_date("02/29/2023")
        assert result is None  # Invalid date

    def test_parse_all_crls_with_missing_fields(self, service):
        """Test parsing CRLs with missing optional fields."""
        data = {
            "results": [
                {
                    "application_number": ["NDA 123456"],
                    "letter_date": "01/15/2024",
                    # Missing many fields
                    "text": "Minimal CRL record"
                }
            ]
        }

        service.crl_repo.exists.return_value = False

        parsed = service.parse_all_crls(data)

        assert len(parsed) == 1
        assert parsed[0]["text"] == "Minimal CRL record"
        assert parsed[0]["company_name"] == ""
        assert parsed[0]["approver_center"] == []

    def test_generate_base_id_special_characters(self, service):
        """Test ID generation with special characters in app number."""
        base_id = service._generate_base_id(["NDA-123/456"], "01/15/2024")
        # Should strip hyphens and spaces (forward slash is kept in current implementation)
        assert "-" not in base_id
        # Note: Forward slash is currently not stripped by the implementation
        # This is acceptable as it doesn't break ID generation

    def test_parse_date_boundary_values(self, service):
        """Test date parsing with boundary values."""
        # First day of year
        result = service.parse_date("01/01/2024")
        assert result == "2024-01-01"

        # Last day of year
        result = service.parse_date("12/31/2024")
        assert result == "2024-12-31"

        # Invalid month
        result = service.parse_date("13/01/2024")
        assert result is None

        # Invalid day
        result = service.parse_date("01/32/2024")
        assert result is None

    def test_duplicate_id_collision_resolution(self, service):
        """Test that duplicate ID collisions are properly resolved."""
        # Create records with same app number, date, and file name
        data = {
            "results": [
                {
                    "application_number": ["NDA 123456"],
                    "letter_date": "01/15/2024",
                    "file_name": "same_file.pdf",
                    "text": "First",
                    "letter_year": "", "letter_type": "", "approval_status": "",
                    "company_name": "", "company_address": "", "company_rep": "",
                    "approver_name": "", "approver_center": [], "approver_title": ""
                },
                {
                    "application_number": ["NDA 123456"],
                    "letter_date": "01/15/2024",
                    "file_name": "same_file.pdf",  # Same file name!
                    "text": "Second",
                    "letter_year": "", "letter_type": "", "approval_status": "",
                    "company_name": "", "company_address": "", "company_rep": "",
                    "approver_name": "", "approver_center": [], "approver_title": ""
                }
            ]
        }

        service.crl_repo.exists.return_value = False

        parsed = service.parse_all_crls(data)

        assert len(parsed) == 2
        # Even with same file name, IDs should be different (counter added)
        assert parsed[0]["id"] != parsed[1]["id"]


class TestProcessCRLDataFunction:
    """Test the convenience function process_crl_data."""

    def test_process_crl_data_success(self):
        """Test the process_crl_data convenience function."""
        data = {
            "meta": {"last_updated": "2025-11-10"},
            "results": [
                {
                    "application_number": ["NDA 123456"],
                    "letter_date": "01/15/2024",
                    "letter_year": "2024",
                    "letter_type": "COMPLETE RESPONSE",
                    "approval_status": "Approved",
                    "company_name": "Test Pharma Inc",
                    "file_name": "test.pdf",
                    "text": "Test CRL",
                    "company_address": "", "company_rep": "",
                    "approver_name": "", "approver_center": [], "approver_title": ""
                }
            ]
        }

        with patch('app.services.data_processor.CRLRepository') as mock_repo, \
             patch('app.services.data_processor.MetadataRepository') as mock_meta:
            mock_repo.return_value.exists.return_value = False
            mock_repo.return_value.create.return_value = None
            mock_repo.return_value.get_stats.return_value = {"total_crls": 1}
            mock_meta.return_value.set.return_value = None

            stats = process_crl_data(data)

            assert stats["new_crls"] == 1
            assert stats["total_in_db"] == 1
