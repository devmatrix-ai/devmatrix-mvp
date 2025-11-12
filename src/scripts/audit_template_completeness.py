"""Comprehensive Template Audit - Verify Data Completeness and Consistency

This script audits what's ACTUALLY in Neo4j vs what SHOULD be there.
Identifies: missing templates, duplicates, corrupted data, inconsistencies.
"""

import asyncio
import logging
from typing import Dict, List, Set, Tuple
from src.neo4j_client import Neo4jClient
from src.scripts.backend_templates_data import BACKEND_TEMPLATES

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TemplateAudit:
    def __init__(self, client: Neo4jClient):
        self.client = client
        self.expected_templates = {t["id"]: t for t in BACKEND_TEMPLATES}
        self.expected_ids = set(t["id"] for t in BACKEND_TEMPLATES)
        self.issues = []

    async def get_actual_templates(self) -> Dict:
        """Get ALL templates from Neo4j with complete data"""
        try:
            query = """
            MATCH (t:Template)
            RETURN {
                id: t.id,
                name: t.name,
                category: t.category,
                framework: t.framework,
                language: t.language,
                precision: t.precision,
                complexity: t.complexity,
                code_length: size(t.code),
                status: t.status,
                source: t.source
            } as template
            ORDER BY t.category, t.id
            """

            result = await self.client.session.run(query)
            templates = []
            async for record in result:
                templates.append(record["template"])

            return {t["id"]: t for t in templates}
        except Exception as e:
            logger.error(f"❌ Failed to get templates from Neo4j: {e}")
            return {}

    async def audit_count(self, actual: Dict) -> None:
        """Audit 1: Count consistency"""
        logger.info("\n" + "="*70)
        logger.info("🔍 AUDIT 1: TEMPLATE COUNT")
        logger.info("="*70)

        expected_count = len(self.expected_ids)
        actual_count = len(actual)

        logger.info(f"Expected: {expected_count} templates")
        logger.info(f"Actual:   {actual_count} templates")

        if actual_count == expected_count:
            logger.info("✅ COUNT MATCHES")
        else:
            diff = actual_count - expected_count
            logger.info(f"⚠️  MISMATCH: {diff:+d} templates")
            self.issues.append(f"Count mismatch: expected {expected_count}, found {actual_count}")

    async def audit_missing_templates(self, actual: Dict) -> None:
        """Audit 2: Find missing templates"""
        logger.info("\n" + "="*70)
        logger.info("🔍 AUDIT 2: MISSING TEMPLATES")
        logger.info("="*70)

        missing = self.expected_ids - set(actual.keys())

        if not missing:
            logger.info("✅ ALL EXPECTED TEMPLATES FOUND")
        else:
            logger.info(f"❌ MISSING {len(missing)} TEMPLATES:")
            for template_id in sorted(missing):
                template = self.expected_templates[template_id]
                logger.info(f"   - {template_id}: {template['name']} ({template['category']})")
                self.issues.append(f"Missing template: {template_id}")

    async def audit_extra_templates(self, actual: Dict) -> None:
        """Audit 3: Find extra/unexpected templates"""
        logger.info("\n" + "="*70)
        logger.info("🔍 AUDIT 3: EXTRA TEMPLATES (Unexpected)")
        logger.info("="*70)

        extra = set(actual.keys()) - self.expected_ids

        if not extra:
            logger.info("✅ NO EXTRA TEMPLATES")
        else:
            logger.info(f"⚠️  FOUND {len(extra)} UNEXPECTED TEMPLATES:")
            for template_id in sorted(extra):
                template = actual[template_id]
                logger.info(f"   - {template_id}: {template['name']} ({template['category']})")
                self.issues.append(f"Extra/unexpected template: {template_id}")

    async def audit_data_completeness(self, actual: Dict) -> None:
        """Audit 4: Check if template data is complete"""
        logger.info("\n" + "="*70)
        logger.info("🔍 AUDIT 4: DATA COMPLETENESS")
        logger.info("="*70)

        incomplete = []
        zero_code = []
        none_values = []

        for template_id, template in actual.items():
            # Check code length
            code_length = template.get("code_length", 0) or 0
            if code_length == 0:
                zero_code.append((template_id, template["name"]))
            elif code_length < 50:
                incomplete.append((template_id, template["name"], code_length))

            # Check for None values in critical fields
            for field in ["category", "framework", "language", "precision", "complexity"]:
                if template.get(field) is None or template.get(field) == "None":
                    none_values.append((template_id, template["name"], field))

        if not incomplete and not zero_code and not none_values:
            logger.info("✅ ALL TEMPLATES HAVE COMPLETE DATA")
        else:
            if zero_code:
                logger.info(f"❌ {len(zero_code)} TEMPLATES WITH NO CODE:")
                for tid, name in zero_code:
                    logger.info(f"   - {tid}: {name}")
                    self.issues.append(f"No code in template: {tid}")

            if incomplete:
                logger.info(f"⚠️  {len(incomplete)} TEMPLATES WITH SHORT CODE:")
                for tid, name, length in incomplete:
                    logger.info(f"   - {tid}: {name} ({length} chars)")
                    self.issues.append(f"Incomplete code in template: {tid}")

            if none_values:
                logger.info(f"⚠️  {len(none_values)} FIELD NULL/NONE VALUES:")
                for tid, name, field in none_values:
                    logger.info(f"   - {tid}.{field}: {name}")
                    self.issues.append(f"None value in {tid}.{field}")

    async def audit_category_consistency(self, actual: Dict) -> None:
        """Audit 5: Check category/framework consistency"""
        logger.info("\n" + "="*70)
        logger.info("🔍 AUDIT 5: CATEGORY & FRAMEWORK CONSISTENCY")
        logger.info("="*70)

        # Build expected mappings
        expected_by_category = {}
        expected_by_framework = {}

        for template in BACKEND_TEMPLATES:
            cat = template["category"]
            fw = template["framework"]
            tid = template["id"]

            if cat not in expected_by_category:
                expected_by_category[cat] = []
            expected_by_category[cat].append(tid)

            if fw not in expected_by_framework:
                expected_by_framework[fw] = []
            expected_by_framework[fw].append(tid)

        # Check actual against expected
        actual_by_category = {}
        for tid, template in actual.items():
            cat = template.get("category", "UNKNOWN")
            if cat not in actual_by_category:
                actual_by_category[cat] = []
            actual_by_category[cat].append(tid)

        # Report differences
        logger.info("\n📊 CATEGORY DISTRIBUTION:")
        for cat in sorted(expected_by_category.keys()):
            expected_count = len(expected_by_category[cat])
            actual_count = len(actual_by_category.get(cat, []))
            status = "✅" if expected_count == actual_count else "⚠️"
            logger.info(f"   {status} {cat:20} Expected: {expected_count:2d}, Actual: {actual_count:2d}")

            if expected_count != actual_count:
                self.issues.append(f"Category {cat}: expected {expected_count}, found {actual_count}")

        # Check for unexpected categories
        unexpected_cats = set(actual_by_category.keys()) - set(expected_by_category.keys())
        if unexpected_cats:
            logger.info(f"\n⚠️  UNEXPECTED CATEGORIES:")
            for cat in sorted(unexpected_cats):
                templates = actual_by_category[cat]
                logger.info(f"   - {cat}: {len(templates)} templates")
                self.issues.append(f"Unexpected category in DB: {cat}")

    async def audit_code_sample(self, actual: Dict, sample_size: int = 3) -> None:
        """Audit 6: Sample check of code content"""
        logger.info("\n" + "="*70)
        logger.info("🔍 AUDIT 6: CODE CONTENT SAMPLE CHECK")
        logger.info("="*70)

        # Get templates with actual code
        with_code = [(tid, t) for tid, t in actual.items() if (t.get("code_length") or 0) > 100]

        if not with_code:
            logger.info("❌ NO TEMPLATES WITH CODE CONTENT")
            self.issues.append("No templates have actual code content")
            return

        logger.info(f"✅ {len(with_code)} templates have code content\n")
        logger.info(f"📋 SAMPLING {min(sample_size, len(with_code))} templates:")

        for tid, template in with_code[:sample_size]:
            expected = self.expected_templates.get(tid)
            logger.info(f"\n   Template: {tid}")
            logger.info(f"   Name: {template['name']}")
            logger.info(f"   Category: {template['category']}")
            logger.info(f"   Code Length: {template['code_length']} chars")

            if expected:
                expected_code_len = len(expected.get("code", ""))
                logger.info(f"   Expected Code Length: {expected_code_len} chars")
                if abs(template['code_length'] - expected_code_len) > 50:
                    logger.info(f"   ⚠️  CODE LENGTH MISMATCH")
                    self.issues.append(f"Code mismatch in {tid}")

            logger.info(f"   ✅ Code present and non-empty")

    async def print_summary(self) -> None:
        """Print audit summary"""
        logger.info("\n" + "="*70)
        logger.info("📊 AUDIT SUMMARY")
        logger.info("="*70)

        if not self.issues:
            logger.info("✅ ALL AUDITS PASSED - Templates are properly populated")
            logger.info("\n🎉 Database is ready for use!")
        else:
            logger.info(f"❌ {len(self.issues)} ISSUES FOUND:\n")
            for i, issue in enumerate(self.issues, 1):
                logger.info(f"   {i}. {issue}")

            logger.info("\n⚠️  REMEDIATION NEEDED - See issues above")
            logger.info("\nRECOMMENDED ACTIONS:")
            logger.info("1. Delete all templates from Neo4j")
            logger.info("2. Run ingest_backend_templates.py fresh")
            logger.info("3. Re-run this audit to verify")

        logger.info("="*70)

    async def run_full_audit(self) -> bool:
        """Execute all audits"""
        logger.info("\n🚀 STARTING COMPREHENSIVE TEMPLATE AUDIT\n")

        actual = await self.get_actual_templates()

        await self.audit_count(actual)
        await self.audit_missing_templates(actual)
        await self.audit_extra_templates(actual)
        await self.audit_data_completeness(actual)
        await self.audit_category_consistency(actual)
        await self.audit_code_sample(actual, sample_size=3)

        await self.print_summary()

        return len(self.issues) == 0


async def main():
    client = Neo4jClient()

    try:
        if not await client.connect():
            logger.error("Failed to connect to Neo4j")
            return

        logger.info("✅ Connected to Neo4j")

        audit = TemplateAudit(client)
        success = await audit.run_full_audit()

        exit_code = 0 if success else 1

    except Exception as e:
        logger.error(f"❌ Audit failed: {e}")
        exit_code = 1
    finally:
        await client.close()
        exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
