#!/usr/bin/env python3
"""
Audit and clean pattern database.

Cleanup operations:
- Remove patterns with empty purpose
- Filter patterns by framework (keep fastapi, remove nextjs, etc.)
- Validate embedding quality

Spec Reference: Task Group 3.2 (spec.md lines 216-270)

Usage:
    python scripts/audit_patterns.py --framework fastapi --dry-run
    python scripts/audit_patterns.py --framework fastapi  # Execute cleanup
"""

import logging
import argparse
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.cognitive.patterns.pattern_bank import PatternBank
from src.cognitive.config.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PatternDatabaseAuditor:
    """
    Pattern database auditor for cleanup and validation.

    Operations:
    - Identify patterns with empty/invalid purpose
    - Filter by framework
    - Backup before cleanup
    - Generate cleanup report
    """

    def __init__(self, framework_filter: str = "fastapi", dry_run: bool = True):
        """
        Initialize auditor.

        Args:
            framework_filter: Only keep patterns for this framework
            dry_run: If True, only report statistics without making changes
        """
        self.framework_filter = framework_filter
        self.dry_run = dry_run
        self.pattern_bank = PatternBank()

        # Statistics
        self.total_patterns = 0
        self.removed_empty = 0
        self.removed_framework = 0
        self.cleaned_patterns = []
        self.removed_patterns = []

    def connect(self) -> None:
        """Connect to Qdrant pattern database."""
        logger.info("Connecting to Qdrant pattern database...")
        self.pattern_bank.connect()
        logger.info("✅ Connected successfully")

    def audit(self) -> Dict[str, Any]:
        """
        Audit pattern database and return statistics.

        Returns:
            Statistics dictionary with counts and removed pattern IDs
        """
        logger.info(f"Starting pattern audit (framework={self.framework_filter}, dry_run={self.dry_run})")

        # Get all patterns from Qdrant
        collection_name = self.pattern_bank.collection_name
        logger.info(f"Reading patterns from collection: {collection_name}")

        try:
            # Scroll through all patterns
            scroll_result = self.pattern_bank.client.scroll(
                collection_name=collection_name,
                limit=10000,  # Get all patterns
                with_payload=True,
                with_vectors=False  # Don't need vectors for audit
            )

            points = scroll_result[0]
            self.total_patterns = len(points)
            logger.info(f"📊 Total patterns in database: {self.total_patterns}")

            # Audit each pattern
            for point in points:
                payload = point.payload
                pattern_id = payload.get("pattern_id", str(point.id))

                # Extract framework from pattern_id (used for all filtering)
                framework = self._extract_framework(pattern_id)

                # Check for empty purpose
                purpose = payload.get("purpose", "").strip()
                if not purpose:
                    self.removed_empty += 1
                    self.removed_patterns.append({
                        "pattern_id": pattern_id,
                        "reason": "empty_purpose",
                        "framework": framework,
                        "domain": payload.get("domain", "unknown")
                    })
                    logger.warning(f"❌ Pattern {pattern_id}: empty purpose (framework={framework}, domain={payload.get('domain')})")
                    continue

                # Check framework filter
                # Pattern IDs follow format: {framework}_{type}_{name}_{hash}
                # Examples: fastapi_function_..., next.js_component_..., supabase_function_...

                if self.framework_filter and framework != self.framework_filter.lower():
                    self.removed_framework += 1
                    self.removed_patterns.append({
                        "pattern_id": pattern_id,
                        "reason": "wrong_framework",
                        "framework": framework,
                        "purpose": purpose[:50]
                    })
                    logger.debug(f"Skipping pattern {pattern_id}: framework={framework} (filter={self.framework_filter})")
                    continue

                # Pattern is valid
                self.cleaned_patterns.append({
                    "pattern_id": pattern_id,
                    "purpose": purpose[:50],
                    "framework": framework,
                    "domain": payload.get("domain", "unknown")
                })

            # Generate statistics
            stats = {
                "total_before": self.total_patterns,
                "removed_empty": self.removed_empty,
                "removed_framework": self.removed_framework,
                "total_after": len(self.cleaned_patterns),
                "timestamp": datetime.utcnow().isoformat(),
                "framework_filter": self.framework_filter,
                "dry_run": self.dry_run,
                "removed_patterns": self.removed_patterns[:10]  # First 10 for report
            }

            self._print_statistics(stats)

            return stats

        except Exception as e:
            logger.error(f"❌ Failed to audit patterns: {e}")
            raise

    def execute_cleanup(self) -> None:
        """
        Execute cleanup by removing invalid patterns from Qdrant.

        WARNING: This modifies the database. Always run with dry_run=True first.
        """
        if self.dry_run:
            logger.info("🔍 DRY RUN MODE - No changes will be made")
            logger.info(f"Would remove {len(self.removed_patterns)} patterns")
            return

        logger.warning(f"⚠️  EXECUTING CLEANUP: Removing {len(self.removed_patterns)} patterns")

        try:
            collection_name = self.pattern_bank.collection_name

            # Extract pattern IDs to remove
            pattern_ids_to_remove = [p["pattern_id"] for p in self.removed_patterns]

            if pattern_ids_to_remove:
                # Delete patterns from Qdrant
                logger.info(f"Deleting {len(pattern_ids_to_remove)} patterns...")

                # Qdrant delete expects point IDs (integers or UUIDs)
                # Convert pattern_id to point ID if needed
                point_ids = []
                for pattern_id in pattern_ids_to_remove:
                    try:
                        # Try to use pattern_id as-is (if it's a UUID string)
                        point_ids.append(pattern_id)
                    except Exception:
                        # Otherwise use hash (as done in store_pattern)
                        point_ids.append(hash(pattern_id) % (2**63))

                # Delete points
                self.pattern_bank.client.delete(
                    collection_name=collection_name,
                    points_selector=point_ids
                )

                logger.info(f"✅ Successfully deleted {len(pattern_ids_to_remove)} patterns")
            else:
                logger.info("✅ No patterns to remove - database is clean")

        except Exception as e:
            logger.error(f"❌ Failed to execute cleanup: {e}")
            raise

    def backup_database(self, backup_path: Path) -> None:
        """
        Create backup of pattern database before cleanup.

        Args:
            backup_path: Path to save backup JSON file
        """
        logger.info(f"Creating database backup at: {backup_path}")

        try:
            collection_name = self.pattern_bank.collection_name

            # Get all patterns with full payload
            scroll_result = self.pattern_bank.client.scroll(
                collection_name=collection_name,
                limit=10000,
                with_payload=True,
                with_vectors=False  # Vectors are large, skip for backup
            )

            points = scroll_result[0]

            # Serialize patterns to JSON
            backup_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "collection_name": collection_name,
                "total_patterns": len(points),
                "patterns": [
                    {
                        "point_id": str(point.id),
                        "payload": point.payload
                    }
                    for point in points
                ]
            }

            # Write backup file
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            with open(backup_path, 'w') as f:
                json.dump(backup_data, f, indent=2)

            logger.info(f"✅ Backup created: {len(points)} patterns saved to {backup_path}")

        except Exception as e:
            logger.error(f"❌ Failed to create backup: {e}")
            raise

    def _extract_framework(self, pattern_id: str) -> str:
        """
        Extract framework from pattern ID.

        Pattern IDs follow format: {framework}_{type}_{name}_{hash}
        Examples:
        - fastapi_function_read_items_1094ab25edc4a9e7 → fastapi
        - next.js_component_button_abc123 → next.js
        - supabase_function_createclient_xyz789 → supabase

        Returns:
            Framework name or "unknown"
        """
        if "_" in pattern_id:
            parts = pattern_id.split("_")
            # Handle frameworks with dots (e.g., next.js)
            if len(parts) >= 2:
                framework_part = parts[0]
                # Check if next token is a continuation (e.g., "next" + "js")
                if len(parts) > 1 and parts[0] == "next" and parts[1] == "js":
                    return "next.js"
                return framework_part.lower()

        return "unknown"

    def _print_statistics(self, stats: Dict[str, Any]) -> None:
        """Print cleanup statistics in readable format."""
        print("\n" + "=" * 60)
        print("📊 PATTERN DATABASE AUDIT REPORT")
        print("=" * 60)
        print(f"Timestamp: {stats['timestamp']}")
        print(f"Framework filter: {stats['framework_filter']}")
        print(f"Dry run: {stats['dry_run']}")
        print()
        print(f"Total patterns (before):  {stats['total_before']}")
        print(f"  ❌ Removed (empty purpose):    {stats['removed_empty']}")
        print(f"  ❌ Removed (wrong framework):  {stats['removed_framework']}")
        print(f"Total patterns (after):   {stats['total_after']}")
        print()

        if stats['removed_patterns']:
            print("Sample removed patterns:")
            for i, pattern in enumerate(stats['removed_patterns'][:5], 1):
                reason = pattern['reason'].replace('_', ' ').title()
                print(f"  {i}. [{reason}] {pattern.get('purpose', 'N/A')[:40]} (framework={pattern.get('framework', 'unknown')})")

        print("=" * 60)
        print()


def main():
    """Main entry point for pattern audit script."""
    parser = argparse.ArgumentParser(
        description="Audit and clean pattern database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (no changes)
  python scripts/audit_patterns.py --framework fastapi --dry-run

  # Execute cleanup (WARNING: modifies database)
  python scripts/audit_patterns.py --framework fastapi

  # Create backup first
  python scripts/audit_patterns.py --framework fastapi --backup backups/patterns_backup.json
        """
    )

    parser.add_argument(
        "--framework",
        type=str,
        default="fastapi",
        help="Framework filter (only keep patterns for this framework)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Dry run mode (report only, no changes)"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute cleanup (WARNING: modifies database)"
    )
    parser.add_argument(
        "--backup",
        type=Path,
        help="Path to backup file (recommended before executing cleanup)"
    )

    args = parser.parse_args()

    # Initialize auditor
    dry_run = not args.execute  # If --execute is set, dry_run=False
    auditor = PatternDatabaseAuditor(
        framework_filter=args.framework,
        dry_run=dry_run
    )

    try:
        # Connect to database
        auditor.connect()

        # Create backup if requested
        if args.backup:
            auditor.backup_database(args.backup)

        # Run audit
        stats = auditor.audit()

        # Execute cleanup if not dry run
        if not dry_run:
            confirmation = input("\n⚠️  Are you sure you want to execute cleanup? (yes/no): ")
            if confirmation.lower() == "yes":
                auditor.execute_cleanup()
                logger.info("✅ Cleanup completed successfully")
            else:
                logger.info("❌ Cleanup cancelled by user")
        else:
            logger.info("ℹ️  Dry run completed. Use --execute to apply changes.")

        # Save statistics to file
        stats_path = project_root / "claudedocs" / "pattern_audit_stats.json"
        stats_path.parent.mkdir(parents=True, exist_ok=True)
        with open(stats_path, 'w') as f:
            json.dump(stats, f, indent=2)
        logger.info(f"📊 Statistics saved to: {stats_path}")

    except Exception as e:
        logger.error(f"❌ Audit failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
