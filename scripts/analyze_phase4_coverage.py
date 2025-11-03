#!/usr/bin/env python
"""
Phase 4 Quality & Coverage Analysis

Comprehensive analysis of the 34 ingested JavaScript/TypeScript examples.
Covers:
- Code quality metrics
- Framework and language coverage
- Pattern diversity
- Complexity distribution
- Query readiness assessment
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
from collections import Counter

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.seed_and_benchmark_phase4 import collect_all_examples
from src.observability import get_logger

logger = get_logger(__name__)


class Phase4CoverageAnalyzer:
    """Analyze Phase 4 coverage and quality."""

    def __init__(self):
        self.examples = collect_all_examples()
        self.stats = {}

    def analyze_all(self) -> Dict[str, Any]:
        """Run all analyses."""
        return {
            "basic_stats": self._analyze_basic_stats(),
            "code_quality": self._analyze_code_quality(),
            "framework_coverage": self._analyze_frameworks(),
            "language_coverage": self._analyze_languages(),
            "pattern_diversity": self._analyze_patterns(),
            "complexity_distribution": self._analyze_complexity(),
            "task_type_coverage": self._analyze_task_types(),
            "metadata_completeness": self._analyze_metadata(),
            "query_readiness": self._analyze_query_readiness(),
        }

    def _analyze_basic_stats(self) -> Dict[str, Any]:
        """Basic statistics."""
        return {
            "total_examples": len(self.examples),
            "total_lines": sum(len(code.strip().split("\n")) for code, _ in self.examples),
            "avg_lines_per_example": sum(len(code.strip().split("\n")) for code, _ in self.examples) // len(self.examples),
        }

    def _analyze_code_quality(self) -> Dict[str, Any]:
        """Code quality metrics."""
        quality_scores = []
        min_lines = []
        max_lines = []

        for code, metadata in self.examples:
            lines = len(code.strip().split("\n"))
            min_lines.append(lines)
            max_lines.append(lines)

            # Quality assessment
            quality_factors = {
                "has_imports": "import" in code.lower() or "require" in code.lower(),
                "has_error_handling": "try" in code.lower() or "catch" in code.lower() or "error" in code.lower(),
                "has_comments": "#" in code or "//" in code or "/*" in code,
                "proper_length": 10 <= lines <= 300,
                "has_function_definition": "function" in code.lower() or "def" in code.lower() or "class" in code.lower(),
            }

            quality_score = sum(quality_factors.values()) / len(quality_factors) * 100
            quality_scores.append(quality_score)

        return {
            "min_lines": min(min_lines),
            "max_lines": max(max_lines),
            "avg_lines": sum(min_lines) / len(min_lines),
            "avg_quality_score": sum(quality_scores) / len(quality_scores),
            "examples_with_error_handling": sum(1 for code, _ in self.examples if "try" in code.lower() or "catch" in code.lower()),
            "examples_with_comments": sum(1 for code, _ in self.examples if "#" in code or "//" in code),
        }

    def _analyze_frameworks(self) -> Dict[str, Any]:
        """Framework coverage analysis."""
        frameworks = Counter(meta.get("framework", "unknown") for _, meta in self.examples)

        return {
            "unique_frameworks": len(frameworks),
            "frameworks": dict(frameworks),
            "primary_framework": frameworks.most_common(1)[0][0],
            "framework_distribution": {
                fw: {"count": count, "percentage": round(count / len(self.examples) * 100, 1)}
                for fw, count in frameworks.items()
            },
        }

    def _analyze_languages(self) -> Dict[str, Any]:
        """Language coverage analysis."""
        languages = Counter(meta.get("language", "unknown") for _, meta in self.examples)

        return {
            "unique_languages": len(languages),
            "languages": dict(languages),
            "language_distribution": {
                lang: {"count": count, "percentage": round(count / len(self.examples) * 100, 1)}
                for lang, count in languages.items()
            },
        }

    def _analyze_patterns(self) -> Dict[str, Any]:
        """Pattern diversity analysis."""
        patterns = Counter(meta.get("pattern", "unknown") for _, meta in self.examples)

        return {
            "unique_patterns": len(patterns),
            "total_patterns": sum(patterns.values()),
            "top_10_patterns": dict(patterns.most_common(10)),
            "pattern_variety_ratio": len(patterns) / len(self.examples),
        }

    def _analyze_complexity(self) -> Dict[str, Any]:
        """Complexity distribution."""
        complexity = Counter(meta.get("complexity", "unknown") for _, meta in self.examples)

        return {
            "distribution": dict(complexity),
            "has_low": "low" in complexity,
            "has_medium": "medium" in complexity,
            "has_high": "high" in complexity,
            "complexity_balance": {
                level: {"count": count, "percentage": round(count / len(self.examples) * 100, 1)}
                for level, count in complexity.items()
            },
        }

    def _analyze_task_types(self) -> Dict[str, Any]:
        """Task type coverage."""
        task_types = Counter(meta.get("task_type", "unknown") for _, meta in self.examples)

        return {
            "unique_task_types": len(task_types),
            "total_task_types": sum(task_types.values()),
            "top_task_types": dict(task_types.most_common(10)),
            "task_type_distribution": {
                task: {"count": count, "percentage": round(count / len(self.examples) * 100, 1)}
                for task, count in task_types.items()
            },
        }

    def _analyze_metadata(self) -> Dict[str, Any]:
        """Metadata completeness."""
        required_fields = {
            "language",
            "framework",
            "pattern",
            "task_type",
            "complexity",
            "tags",
            "source",
        }

        complete_count = 0
        missing_fields_count = {}

        for _, meta in self.examples:
            if required_fields.issubset(meta.keys()):
                complete_count += 1
            else:
                missing = required_fields - set(meta.keys())
                for field in missing:
                    missing_fields_count[field] = missing_fields_count.get(field, 0) + 1

        return {
            "required_fields": len(required_fields),
            "complete_examples": complete_count,
            "completeness_percentage": round(complete_count / len(self.examples) * 100, 1),
            "missing_fields": missing_fields_count if missing_fields_count else "None",
        }

    def _analyze_query_readiness(self) -> Dict[str, Any]:
        """Query readiness assessment."""
        readable_keywords = {
            "express",
            "react",
            "async",
            "function",
            "class",
            "const",
            "typescript",
            "javascript",
            "api",
            "component",
            "hook",
            "middleware",
            "error",
            "fetch",
            "promise",
            "state",
            "props",
            "handle",
        }

        keyword_coverage = Counter()
        examples_with_keywords = set()

        for i, (code, _) in enumerate(self.examples):
            code_lower = code.lower()
            for keyword in readable_keywords:
                if keyword in code_lower:
                    keyword_coverage[keyword] += 1
                    examples_with_keywords.add(i)

        return {
            "searchable_keywords": len(keyword_coverage),
            "total_keyword_matches": sum(keyword_coverage.values()),
            "examples_with_keywords": len(examples_with_keywords),
            "keyword_coverage_percentage": round(len(examples_with_keywords) / len(self.examples) * 100, 1),
            "top_keywords": dict(keyword_coverage.most_common(10)),
            "query_readiness_score": round(len(examples_with_keywords) / len(self.examples) * 100, 1),
        }


def print_analysis(analysis: Dict[str, Any]) -> None:
    """Pretty print analysis results."""
    print("\n" + "=" * 80)
    print("📊 PHASE 4 QUALITY & COVERAGE ANALYSIS")
    print("=" * 80)

    # Basic Stats
    print(f"\n📈 BASIC STATISTICS")
    print(f"   Total examples: {analysis['basic_stats']['total_examples']}")
    print(f"   Total lines of code: {analysis['basic_stats']['total_lines']}")
    print(f"   Avg lines per example: {analysis['basic_stats']['avg_lines_per_example']}")

    # Code Quality
    qual = analysis["code_quality"]
    print(f"\n🔍 CODE QUALITY")
    print(f"   Min lines: {qual['min_lines']}")
    print(f"   Max lines: {qual['max_lines']}")
    print(f"   Avg lines: {qual['avg_lines']:.1f}")
    print(f"   Avg quality score: {qual['avg_quality_score']:.1f}%")
    print(f"   Examples with error handling: {qual['examples_with_error_handling']}/34")
    print(f"   Examples with comments: {qual['examples_with_comments']}/34")

    # Framework Coverage
    fw_cov = analysis["framework_coverage"]
    print(f"\n🏗️  FRAMEWORK COVERAGE")
    print(f"   Unique frameworks: {fw_cov['unique_frameworks']}")
    for fw, dist in fw_cov["framework_distribution"].items():
        print(f"      • {fw}: {dist['count']} ({dist['percentage']}%)")

    # Language Coverage
    lang_cov = analysis["language_coverage"]
    print(f"\n📝 LANGUAGE COVERAGE")
    print(f"   Unique languages: {lang_cov['unique_languages']}")
    for lang, dist in lang_cov["language_distribution"].items():
        print(f"      • {lang}: {dist['count']} ({dist['percentage']}%)")

    # Pattern Diversity
    pat = analysis["pattern_diversity"]
    print(f"\n🎯 PATTERN DIVERSITY")
    print(f"   Unique patterns: {pat['unique_patterns']}")
    print(f"   Pattern variety ratio: {pat['pattern_variety_ratio']:.2f}")
    print(f"   Top patterns:")
    for pattern, count in list(pat["top_10_patterns"].items())[:5]:
        print(f"      • {pattern}: {count}")

    # Complexity
    comp = analysis["complexity_distribution"]
    print(f"\n⚙️  COMPLEXITY DISTRIBUTION")
    for level, dist in comp["complexity_balance"].items():
        print(f"   {level}: {dist['count']} ({dist['percentage']}%)")

    # Task Types
    tasks = analysis["task_type_coverage"]
    print(f"\n🎪 TASK TYPE COVERAGE")
    print(f"   Unique task types: {tasks['unique_task_types']}")

    # Metadata
    meta = analysis["metadata_completeness"]
    print(f"\n📋 METADATA COMPLETENESS")
    print(f"   Complete examples: {meta['complete_examples']}/34")
    print(f"   Completeness: {meta['completeness_percentage']}%")

    # Query Readiness
    query = analysis["query_readiness"]
    print(f"\n🔍 QUERY READINESS")
    print(f"   Searchable keywords: {query['searchable_keywords']}")
    print(f"   Examples with keywords: {query['examples_with_keywords']}/34")
    print(f"   Query readiness score: {query['query_readiness_score']}%")

    # Final Assessment
    print(f"\n✅ OVERALL ASSESSMENT")
    readiness_score = query["query_readiness_score"]
    if readiness_score >= 90:
        status = "🟢 EXCELLENT - Ready for production"
    elif readiness_score >= 75:
        status = "🟡 GOOD - Ready for testing"
    else:
        status = "🔴 NEEDS IMPROVEMENT"

    print(f"   Status: {status}")
    print(f"   Quality score: {qual['avg_quality_score']:.1f}%")
    print(f"   Metadata completeness: {meta['completeness_percentage']}%")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    analyzer = Phase4CoverageAnalyzer()
    analysis = analyzer.analyze_all()
    print_analysis(analysis)
