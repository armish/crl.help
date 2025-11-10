"""
Data processor service for FDA CRL Explorer.
Handles parsing, transforming, and storing CRL data in the database.
"""

import hashlib
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

from app.database import CRLRepository, MetadataRepository
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class DataProcessorService:
    """
    Service for processing and storing CRL data.

    Handles:
    - Parsing CRL records from JSON
    - Transforming dates and generating IDs
    - Detecting new/updated CRLs
    - Storing CRLs in database
    - Tracking processing metadata
    """

    def __init__(self):
        self.crl_repo = CRLRepository()
        self.metadata_repo = MetadataRepository()

    @staticmethod
    def parse_date(date_str: str) -> Optional[str]:
        """
        Parse date string from MM/DD/YYYY or YYYYMMDD to YYYY-MM-DD format.

        Args:
            date_str: Date in MM/DD/YYYY or YYYYMMDD format

        Returns:
            Optional[str]: Date in YYYY-MM-DD format or None if parsing fails
        """
        try:
            # Try MM/DD/YYYY format first (most common)
            if "/" in date_str:
                dt = datetime.strptime(date_str, "%m/%d/%Y")
            # Try YYYYMMDD format
            elif len(date_str) == 8 and date_str.isdigit():
                dt = datetime.strptime(date_str, "%Y%m%d")
            else:
                logger.warning(f"Unknown date format: '{date_str}'")
                return None

            # Return in ISO format (YYYY-MM-DD)
            return dt.strftime("%Y-%m-%d")
        except (ValueError, AttributeError) as e:
            logger.warning(f"Failed to parse date '{date_str}': {e}")
            return None


    def parse_all_crls(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse all CRL records from JSON data.

        Args:
            data: JSON data with 'results' key containing CRL records

        Returns:
            List[Dict]: List of parsed CRL records
        """
        results = data.get("results", [])
        parsed_crls = []
        used_ids = set()  # Track IDs used in this batch

        logger.info(f"Parsing {len(results)} CRL records...")

        for i, record in enumerate(results):
            try:
                # Generate base ID
                base_id = self._generate_base_id(
                    record.get("application_number", []),
                    record.get("letter_date", "")
                )

                # Check if ID already exists in DB or used in current batch
                final_id = base_id
                if self.crl_repo.exists(base_id) or base_id in used_ids:
                    # Create unique suffix from file name
                    file_name = record.get("file_name", "")
                    file_hash = hashlib.md5(file_name.encode()).hexdigest()[:6]
                    final_id = f"{base_id}_{file_hash}"

                    # If still duplicate (unlikely), add counter
                    counter = 1
                    while final_id in used_ids:
                        final_id = f"{base_id}_{file_hash}_{counter}"
                        counter += 1

                used_ids.add(final_id)

                # Parse the record with the final ID
                crl_data = self._parse_crl_record_with_id(record, final_id)
                parsed_crls.append(crl_data)

                if (i + 1) % 50 == 0:
                    logger.debug(f"Parsed {i + 1}/{len(results)} records")

            except Exception as e:
                logger.error(f"Failed to parse record {i}: {e}")
                # Continue processing other records
                continue

        logger.info(f"Successfully parsed {len(parsed_crls)}/{len(results)} records")

        return parsed_crls

    def _generate_base_id(
        self,
        application_numbers: List[str],
        letter_date: str
    ) -> str:
        """Generate base CRL ID without checking for duplicates."""
        app_num = application_numbers[0] if application_numbers else "UNKNOWN"
        app_num_clean = app_num.replace(" ", "").replace("-", "")

        try:
            if "/" in letter_date:
                dt = datetime.strptime(letter_date, "%m/%d/%Y")
                date_str = dt.strftime("%Y%m%d")
            elif len(letter_date) == 8 and letter_date.isdigit():
                date_str = letter_date
            else:
                date_str = hashlib.md5(letter_date.encode()).hexdigest()[:8]
        except (ValueError, AttributeError):
            date_str = hashlib.md5(letter_date.encode()).hexdigest()[:8]

        return f"{app_num_clean}_{date_str}"

    def _parse_crl_record_with_id(
        self,
        record: Dict[str, Any],
        crl_id: str
    ) -> Dict[str, Any]:
        """Parse CRL record with a pre-determined ID."""
        letter_date_iso = self.parse_date(record.get("letter_date", ""))

        crl_data = {
            "id": crl_id,
            "application_number": record.get("application_number", []),
            "letter_date": letter_date_iso,
            "letter_year": record.get("letter_year", ""),
            "letter_type": record.get("letter_type", ""),
            "approval_status": record.get("approval_status", ""),
            "company_name": record.get("company_name", ""),
            "company_address": record.get("company_address", ""),
            "company_rep": record.get("company_rep", ""),
            "approver_name": record.get("approver_name", ""),
            "approver_center": record.get("approver_center", []),
            "approver_title": record.get("approver_title", ""),
            "file_name": record.get("file_name", ""),
            "text": record.get("text", ""),
            "raw_json": record,
        }

        return crl_data

    def detect_new_and_updated_crls(
        self,
        parsed_crls: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Detect new and updated CRLs by comparing with existing database.

        Args:
            parsed_crls: List of parsed CRL records

        Returns:
            Tuple[List, List]: (new_crls, updated_crls)
        """
        new_crls = []
        updated_crls = []

        logger.info("Detecting new and updated CRLs...")

        for crl in parsed_crls:
            crl_id = crl["id"]

            if self.crl_repo.exists(crl_id):
                # Check if data has changed (compare with existing)
                existing = self.crl_repo.get_by_id(crl_id)

                # Simple comparison: check if text field has changed
                if existing and existing.get("text") != crl.get("text"):
                    updated_crls.append(crl)
            else:
                new_crls.append(crl)

        logger.info(f"Found {len(new_crls)} new CRLs and {len(updated_crls)} updated CRLs")

        return new_crls, updated_crls

    def store_crls(
        self,
        crls: List[Dict[str, Any]],
        operation: str = "create"
    ) -> int:
        """
        Store CRLs in database (create or update).

        Args:
            crls: List of CRL records to store
            operation: 'create' or 'update'

        Returns:
            int: Number of successfully stored CRLs
        """
        if not crls:
            logger.info(f"No CRLs to {operation}")
            return 0

        logger.info(f"Storing {len(crls)} CRLs (operation: {operation})...")

        success_count = 0

        for i, crl in enumerate(crls):
            try:
                if operation == "create":
                    self.crl_repo.create(crl)
                elif operation == "update":
                    self.crl_repo.update(crl["id"], crl)

                success_count += 1

                if (i + 1) % 50 == 0:
                    logger.debug(f"Stored {i + 1}/{len(crls)} CRLs")

            except Exception as e:
                logger.error(f"Failed to store CRL {crl.get('id', 'unknown')}: {e}")
                # Continue processing other records
                continue

        logger.info(f"Successfully stored {success_count}/{len(crls)} CRLs")

        return success_count

    def process_and_store(self, data: Dict[str, Any]) -> Dict[str, int]:
        """
        Process CRL data and store in database.

        This is the main entry point for data processing.

        Args:
            data: JSON data with 'meta' and 'results' keys

        Returns:
            Dict: Statistics about processing (new, updated, failed counts)
        """
        try:
            # Step 1: Parse all CRL records
            parsed_crls = self.parse_all_crls(data)

            # Step 2: Detect new and updated CRLs
            new_crls, updated_crls = self.detect_new_and_updated_crls(parsed_crls)

            # Step 3: Store new CRLs
            new_count = self.store_crls(new_crls, operation="create")

            # Step 4: Update existing CRLs
            updated_count = self.store_crls(updated_crls, operation="update")

            # Step 5: Update metadata
            self.metadata_repo.set("last_processing_date", datetime.now().isoformat())
            self.metadata_repo.set("last_data_update", data["meta"].get("last_updated", ""))
            self.metadata_repo.set("total_crls_processed", str(new_count + updated_count))

            # Get statistics
            stats = self.crl_repo.get_stats()

            logger.info("Data processing completed successfully")
            logger.info(f"Total CRLs in database: {stats['total_crls']}")

            return {
                "new_crls": new_count,
                "updated_crls": updated_count,
                "total_in_db": stats["total_crls"],
                "failed": len(parsed_crls) - new_count - updated_count,
            }

        except Exception as e:
            logger.error(f"Data processing failed: {e}")
            raise


# Convenience function for simple usage
def process_crl_data(data: Dict[str, Any]) -> Dict[str, int]:
    """
    Process and store CRL data.

    Args:
        data: JSON data with CRL records

    Returns:
        Dict: Processing statistics
    """
    processor = DataProcessorService()
    return processor.process_and_store(data)
