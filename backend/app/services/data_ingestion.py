"""
Data ingestion service for FDA CRL Explorer.
Handles downloading and extracting CRL data from FDA API.
"""

import json
import zipfile
from pathlib import Path
from typing import Dict, Any, Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class DataIngestionService:
    """
    Service for downloading and extracting FDA CRL data.

    Handles:
    - Downloading JSON ZIP file from FDA
    - Extracting and validating JSON data
    - Retry logic with exponential backoff
    - Progress tracking
    """

    def __init__(self):
        self.raw_dir = Path(settings.data_raw_dir)
        self.processed_dir = Path(settings.data_processed_dir)

        # Ensure directories exist
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True
    )
    async def download_crl_json(self) -> Path:
        """
        Download CRL JSON ZIP file from FDA.

        Returns:
            Path: Path to downloaded ZIP file

        Raises:
            httpx.HTTPError: If download fails after retries
        """
        url = settings.fda_json_url
        zip_filename = url.split("/")[-1]
        zip_path = self.raw_dir / zip_filename

        logger.info(f"Downloading CRL data from {url}")

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()

                # Write to file
                zip_path.write_bytes(response.content)

                file_size_mb = len(response.content) / (1024 * 1024)
                logger.info(f"Downloaded {zip_filename} ({file_size_mb:.2f} MB)")

                return zip_path

            except httpx.HTTPError as e:
                logger.error(f"Failed to download CRL data: {e}")
                raise

    def extract_json_from_zip(self, zip_path: Path) -> Path:
        """
        Extract JSON file from ZIP archive.

        Args:
            zip_path: Path to ZIP file

        Returns:
            Path: Path to extracted JSON file

        Raises:
            zipfile.BadZipFile: If ZIP file is corrupted
            FileNotFoundError: If JSON file not found in ZIP
        """
        logger.info(f"Extracting {zip_path.name}")

        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Get list of files in ZIP
                file_list = zip_ref.namelist()
                logger.debug(f"Files in ZIP: {file_list}")

                # Find JSON file (should be only one)
                json_files = [f for f in file_list if f.endswith('.json')]

                if not json_files:
                    raise FileNotFoundError("No JSON file found in ZIP archive")

                if len(json_files) > 1:
                    logger.warning(f"Multiple JSON files found, using first: {json_files[0]}")

                json_filename = json_files[0]

                # Extract to raw directory
                zip_ref.extract(json_filename, self.raw_dir)
                json_path = self.raw_dir / json_filename

                file_size_mb = json_path.stat().st_size / (1024 * 1024)
                logger.info(f"Extracted {json_filename} ({file_size_mb:.2f} MB)")

                return json_path

        except zipfile.BadZipFile as e:
            logger.error(f"Corrupted ZIP file: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to extract JSON: {e}")
            raise

    def load_json_data(self, json_path: Path) -> Dict[str, Any]:
        """
        Load and parse JSON data from file.

        Args:
            json_path: Path to JSON file

        Returns:
            Dict: Parsed JSON data with 'meta' and 'results' keys

        Raises:
            json.JSONDecodeError: If JSON is malformed
        """
        logger.info(f"Loading JSON data from {json_path.name}")

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Validate structure
            if 'meta' not in data or 'results' not in data:
                raise ValueError("Invalid JSON structure: missing 'meta' or 'results' keys")

            num_results = len(data['results'])
            last_updated = data['meta'].get('last_updated', 'Unknown')

            logger.info(f"Loaded {num_results} CRL records (last updated: {last_updated})")

            return data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load JSON data: {e}")
            raise

    async def download_and_extract(self) -> Dict[str, Any]:
        """
        Download, extract, and load CRL JSON data.

        This is the main entry point for data ingestion.

        Returns:
            Dict: Parsed JSON data with CRL records

        Raises:
            Exception: If any step fails
        """
        try:
            # Step 1: Download ZIP file
            zip_path = await self.download_crl_json()

            # Step 2: Extract JSON file
            json_path = self.extract_json_from_zip(zip_path)

            # Step 3: Load JSON data
            data = self.load_json_data(json_path)

            logger.info("Data ingestion completed successfully")

            return data

        except Exception as e:
            logger.error(f"Data ingestion failed: {e}")
            raise

    def get_cached_json(self) -> Optional[Dict[str, Any]]:
        """
        Get cached JSON data if available (avoids re-downloading).

        Returns:
            Optional[Dict]: Cached JSON data or None if not available
        """
        # Look for any JSON files in raw directory
        json_files = list(self.raw_dir.glob("*.json"))

        if not json_files:
            logger.info("No cached JSON data found")
            return None

        # Use the most recent file
        json_path = max(json_files, key=lambda p: p.stat().st_mtime)

        logger.info(f"Found cached JSON data: {json_path.name}")

        try:
            return self.load_json_data(json_path)
        except Exception as e:
            logger.warning(f"Failed to load cached data: {e}")
            return None


# Convenience function for simple usage
async def fetch_crl_data(use_cache: bool = True) -> Dict[str, Any]:
    """
    Fetch CRL data from FDA (or use cached data if available).

    Args:
        use_cache: If True, use cached data if available

    Returns:
        Dict: CRL data with 'meta' and 'results' keys
    """
    service = DataIngestionService()

    if use_cache:
        cached_data = service.get_cached_json()
        if cached_data:
            return cached_data

    return await service.download_and_extract()
