"""
Tests for data ingestion service.
"""

import json
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import httpx

from app.services.data_ingestion import DataIngestionService, fetch_crl_data


class TestDataIngestionService:
    """Test cases for DataIngestionService."""

    @pytest.fixture
    def service(self, tmp_path):
        """Create a DataIngestionService with temporary directories."""
        with patch('app.services.data_ingestion.settings') as mock_settings:
            mock_settings.data_raw_dir = str(tmp_path / "raw")
            mock_settings.data_processed_dir = str(tmp_path / "processed")
            mock_settings.fda_json_url = "https://example.com/data.json.zip"

            service = DataIngestionService()
            return service

    @pytest.fixture
    def sample_crl_data(self):
        """Create sample CRL data for testing."""
        return {
            "meta": {
                "disclaimer": "Test disclaimer",
                "last_updated": "2025-11-10",
                "results": {
                    "total": 2
                }
            },
            "results": [
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
                    "text": "This is another test CRL letter with deficiencies."
                }
            ]
        }

    @pytest.fixture
    def create_test_zip(self, tmp_path, sample_crl_data):
        """Create a test ZIP file containing JSON data."""
        def _create_zip(filename="test_data.json.zip"):
            zip_path = tmp_path / filename
            json_path = tmp_path / "test_data.json"

            # Write JSON file
            with open(json_path, 'w') as f:
                json.dump(sample_crl_data, f)

            # Create ZIP file
            with zipfile.ZipFile(zip_path, 'w') as zf:
                zf.write(json_path, "test_data.json")

            # Clean up temporary JSON
            json_path.unlink()

            return zip_path

        return _create_zip

    @pytest.mark.asyncio
    async def test_download_crl_json_success(self, service, tmp_path, create_test_zip):
        """Test successful download of CRL JSON ZIP file."""
        zip_path = create_test_zip()

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.content = zip_path.read_bytes()
            mock_response.raise_for_status = MagicMock()

            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_context

            result = await service.download_crl_json()

            assert result.exists()
            assert result.name.endswith(".zip")

    @pytest.mark.asyncio
    async def test_download_crl_json_http_error(self, service):
        """Test download with HTTP error."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.HTTPError("Connection failed")
            )
            mock_client.return_value = mock_context

            with pytest.raises(httpx.HTTPError):
                await service.download_crl_json()

    @pytest.mark.asyncio
    async def test_download_retry_logic(self, service):
        """Test that retry logic works with exponential backoff."""
        with patch('httpx.AsyncClient') as mock_client:
            # Simulate 2 failures then success
            mock_response = MagicMock()
            mock_response.content = b"test data"
            mock_response.raise_for_status = MagicMock()

            mock_context = AsyncMock()
            mock_get = AsyncMock(
                side_effect=[
                    httpx.HTTPError("First failure"),
                    httpx.HTTPError("Second failure"),
                    mock_response
                ]
            )
            mock_context.__aenter__.return_value.get = mock_get
            mock_client.return_value = mock_context

            result = await service.download_crl_json()

            # Should succeed after retries
            assert result.exists()
            assert mock_get.call_count == 3

    def test_extract_json_from_zip_success(self, service, create_test_zip):
        """Test successful extraction of JSON from ZIP."""
        zip_path = create_test_zip()

        json_path = service.extract_json_from_zip(zip_path)

        assert json_path.exists()
        assert json_path.suffix == ".json"
        assert json_path.stat().st_size > 0

    def test_extract_json_from_zip_bad_zip(self, service, tmp_path):
        """Test extraction with corrupted ZIP file."""
        bad_zip = tmp_path / "bad.zip"
        bad_zip.write_text("This is not a valid ZIP file")

        with pytest.raises(zipfile.BadZipFile):
            service.extract_json_from_zip(bad_zip)

    def test_extract_json_from_zip_no_json(self, service, tmp_path):
        """Test extraction when ZIP contains no JSON files."""
        zip_path = tmp_path / "no_json.zip"

        # Create ZIP with no JSON files
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("readme.txt", "No JSON here")

        with pytest.raises(FileNotFoundError):
            service.extract_json_from_zip(zip_path)

    def test_load_json_data_success(self, service, tmp_path, sample_crl_data):
        """Test successful loading and parsing of JSON data."""
        json_path = tmp_path / "test.json"
        json_path.write_text(json.dumps(sample_crl_data))

        data = service.load_json_data(json_path)

        assert "meta" in data
        assert "results" in data
        assert len(data["results"]) == 2
        assert data["meta"]["last_updated"] == "2025-11-10"

    def test_load_json_data_invalid_structure(self, service, tmp_path):
        """Test loading JSON with invalid structure."""
        json_path = tmp_path / "invalid.json"
        json_path.write_text(json.dumps({"invalid": "structure"}))

        with pytest.raises(ValueError, match="Invalid JSON structure"):
            service.load_json_data(json_path)

    def test_load_json_data_malformed(self, service, tmp_path):
        """Test loading malformed JSON."""
        json_path = tmp_path / "malformed.json"
        json_path.write_text("{ invalid json }")

        with pytest.raises(json.JSONDecodeError):
            service.load_json_data(json_path)

    @pytest.mark.asyncio
    async def test_download_and_extract_full_pipeline(self, service, create_test_zip, sample_crl_data):
        """Test the complete download and extract pipeline."""
        zip_path = create_test_zip()

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.content = zip_path.read_bytes()
            mock_response.raise_for_status = MagicMock()

            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_context

            data = await service.download_and_extract()

            assert "meta" in data
            assert "results" in data
            assert len(data["results"]) == 2
            assert data["results"][0]["company_name"] == "Test Pharma Inc"

    def test_get_cached_json_exists(self, service, tmp_path, sample_crl_data):
        """Test getting cached JSON data."""
        # Create a cached JSON file in raw directory
        json_path = service.raw_dir / "cached.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(sample_crl_data))

        data = service.get_cached_json()

        assert data is not None
        assert len(data["results"]) == 2

    def test_get_cached_json_not_exists(self, service):
        """Test getting cached JSON when none exists."""
        data = service.get_cached_json()

        assert data is None

    def test_get_cached_json_corrupted(self, service):
        """Test getting cached JSON when file is corrupted."""
        # Create corrupted JSON file
        json_path = service.raw_dir / "corrupted.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text("{ corrupted json }")

        data = service.get_cached_json()

        assert data is None  # Should return None and log warning

    @pytest.mark.asyncio
    async def test_fetch_crl_data_with_cache(self, tmp_path, sample_crl_data):
        """Test fetch_crl_data function with cache."""
        with patch('app.services.data_ingestion.settings') as mock_settings:
            mock_settings.data_raw_dir = str(tmp_path / "raw")
            mock_settings.data_processed_dir = str(tmp_path / "processed")

            # Create cached data
            raw_dir = Path(tmp_path / "raw")
            raw_dir.mkdir(parents=True, exist_ok=True)
            cached_file = raw_dir / "cached.json"
            cached_file.write_text(json.dumps(sample_crl_data))

            data = await fetch_crl_data(use_cache=True)

            assert data is not None
            assert len(data["results"]) == 2

    @pytest.mark.asyncio
    async def test_fetch_crl_data_no_cache(self, tmp_path, sample_crl_data, create_test_zip):
        """Test fetch_crl_data function forcing download."""
        with patch('app.services.data_ingestion.settings') as mock_settings:
            mock_settings.data_raw_dir = str(tmp_path / "raw")
            mock_settings.data_processed_dir = str(tmp_path / "processed")
            mock_settings.fda_json_url = "https://example.com/data.json.zip"

            zip_path = create_test_zip()

            with patch('httpx.AsyncClient') as mock_client:
                mock_response = MagicMock()
                mock_response.content = zip_path.read_bytes()
                mock_response.raise_for_status = MagicMock()

                mock_context = AsyncMock()
                mock_context.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
                mock_client.return_value = mock_context

                data = await fetch_crl_data(use_cache=False)

                assert data is not None
                assert len(data["results"]) == 2


class TestDataIngestionEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_network_timeout(self):
        """Test handling of network timeout."""
        with patch('app.services.data_ingestion.settings') as mock_settings:
            mock_settings.data_raw_dir = "/tmp/test_raw"
            mock_settings.data_processed_dir = "/tmp/test_processed"
            mock_settings.fda_json_url = "https://example.com/data.json.zip"

            service = DataIngestionService()

            with patch('httpx.AsyncClient') as mock_client:
                mock_context = AsyncMock()
                mock_context.__aenter__.return_value.get = AsyncMock(
                    side_effect=httpx.TimeoutException("Request timed out")
                )
                mock_client.return_value = mock_context

                with pytest.raises(httpx.TimeoutException):
                    await service.download_crl_json()

    def test_disk_space_error(self, tmp_path):
        """Test handling of disk space error during extraction."""
        with patch('app.services.data_ingestion.settings') as mock_settings:
            mock_settings.data_raw_dir = str(tmp_path)
            mock_settings.data_processed_dir = str(tmp_path)

            service = DataIngestionService()

            # Create a minimal ZIP file
            zip_path = tmp_path / "test.zip"
            with zipfile.ZipFile(zip_path, 'w') as zf:
                zf.writestr("test.json", '{"test": "data"}')

            # Mock the extract method to raise an error
            with patch.object(zipfile.ZipFile, 'extract', side_effect=OSError("No space left on device")):
                with pytest.raises(OSError):
                    service.extract_json_from_zip(zip_path)

    def test_multiple_json_files_in_zip(self, tmp_path):
        """Test handling of ZIP with multiple JSON files."""
        with patch('app.services.data_ingestion.settings') as mock_settings:
            mock_settings.data_raw_dir = str(tmp_path)
            mock_settings.data_processed_dir = str(tmp_path)

            service = DataIngestionService()

            # Create ZIP with multiple JSON files
            zip_path = tmp_path / "multi.zip"
            with zipfile.ZipFile(zip_path, 'w') as zf:
                zf.writestr("file1.json", '{"meta": {}, "results": []}')
                zf.writestr("file2.json", '{"meta": {}, "results": []}')

            # Should extract first JSON file and log warning
            result = service.extract_json_from_zip(zip_path)

            assert result.exists()
            assert result.name.endswith(".json")
