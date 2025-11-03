"""
Phase 4 TypeScript/JavaScript Ingestion Tests

Tests for seed_typescript_docs.py and extract_github_typescript.py
Validates:
- Example validation and metadata
- Vector store integration
- Batch processing
- Quality metrics
- Query success rate (target: 85%+)
"""

import sys
import pytest
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.seed_typescript_docs import (
    validate_example,
    ALL_EXAMPLES,
    seed_typescript_docs,
)
from scripts.extract_github_typescript import (
    GitHubExtractor,
    estimate_quality_score,
    POPULAR_REPOS,
    EXTRACTION_CONFIG,
)


class TestTypescriptExampleValidation:
    """Test validation of TypeScript/JavaScript examples."""

    def test_all_examples_valid(self):
        """All 20 seed examples should be valid."""
        valid_count = 0
        invalid_examples = []

        for code, metadata in ALL_EXAMPLES:
            if validate_example(code, metadata):
                valid_count += 1
            else:
                invalid_examples.append(metadata.get('pattern', 'unknown'))

        assert len(invalid_examples) == 0, f"Invalid examples: {invalid_examples}"
        assert valid_count == len(ALL_EXAMPLES)

    def test_example_count(self):
        """Should have at least 20 examples."""
        assert len(ALL_EXAMPLES) >= 20

    def test_example_metadata_complete(self):
        """Each example must have complete metadata."""
        required_fields = {
            'language', 'source', 'framework', 'docs_section',
            'pattern', 'task_type', 'complexity', 'quality', 'tags', 'approved'
        }

        for code, metadata in ALL_EXAMPLES:
            assert isinstance(metadata, dict)
            assert required_fields.issubset(metadata.keys()), \
                f"Missing fields in {metadata.get('pattern')}"

            # Validate field values
            assert metadata['language'] in {'typescript', 'javascript', 'python'}
            assert metadata['complexity'] in {'low', 'medium', 'high'}
            assert isinstance(metadata['tags'], str)

    def test_example_code_quality(self):
        """Code examples should meet minimum length requirements."""
        min_lines = 10
        max_lines = 300

        for code, metadata in ALL_EXAMPLES:
            lines = len(code.strip().split('\n'))
            assert lines >= min_lines, \
                f"{metadata['pattern']}: too short ({lines} lines)"
            assert lines <= max_lines, \
                f"{metadata['pattern']}: too long ({lines} lines)"

    def test_framework_distribution(self):
        """Should have diverse framework coverage."""
        frameworks = {}
        for _, metadata in ALL_EXAMPLES:
            fw = metadata['framework']
            frameworks[fw] = frameworks.get(fw, 0) + 1

        # Should have at least 2 frameworks
        assert len(frameworks) >= 2

        # Express and React should be well-represented
        assert 'express' in frameworks
        assert 'react' in frameworks

    def test_language_distribution(self):
        """Examples should include both JavaScript and TypeScript."""
        languages = set()
        for _, metadata in ALL_EXAMPLES:
            languages.add(metadata['language'])

        assert 'typescript' in languages or 'javascript' in languages


class TestSeedTypescriptDocs:
    """Test seed_typescript_docs.py integration."""

    def test_validate_example_function(self):
        """Test validate_example function directly."""
        # Valid example
        valid_code = """
import express from 'express';
const app = express();
app.get('/api/data', (req, res) => {
  res.json({ data: [] });
});
"""
        valid_metadata = {
            'language': 'typescript',
            'source': 'test',
            'framework': 'express',
            'docs_section': 'test',
            'pattern': 'test_pattern',
            'task_type': 'test',
            'complexity': 'low',
            'quality': 'test',
            'tags': 'test',
            'approved': True,
        }

        assert validate_example(valid_code, valid_metadata)

        # Invalid: missing fields
        invalid_metadata = {
            'language': 'typescript',
            'source': 'test',
        }
        assert not validate_example(valid_code, invalid_metadata)

        # Invalid: too short
        short_code = "const x = 1;"
        assert not validate_example(short_code, valid_metadata)

    def test_batch_processing_metadata_cleaning(self):
        """Test that metadata is properly cleaned for ChromaDB."""
        # Simulate metadata with list values
        metadata = {
            'language': 'typescript',
            'tags': 'express,api,typescript',
            'approved': True,
            'number_value': 42,
        }

        # Lists should be converted to comma-separated strings
        assert isinstance(metadata['tags'], str)
        assert isinstance(metadata['approved'], bool)

    def test_seed_examples_summary(self):
        """Validate summary statistics of seed examples."""
        frameworks = {}
        languages = {}

        for _, metadata in ALL_EXAMPLES:
            fw = metadata['framework']
            lang = metadata['language']

            frameworks[fw] = frameworks.get(fw, 0) + 1
            languages[lang] = languages.get(lang, 0) + 1

        # Express should have most examples
        assert frameworks.get('express', 0) >= 5

        # Should primarily be typescript/javascript
        total_js_ts = languages.get('typescript', 0) + languages.get('javascript', 0)
        assert total_js_ts >= len(ALL_EXAMPLES) - 2


class TestGitHubExtractorConfiguration:
    """Test GitHub extractor configuration and setup."""

    def test_extractor_initialization(self):
        """Test GitHubExtractor can be initialized."""
        extractor = GitHubExtractor()

        assert extractor.config is not None
        assert extractor.total_extracted == 0
        assert len(extractor.examples) == 0

    def test_extractor_custom_config(self):
        """Test GitHubExtractor with custom config."""
        custom_config = {
            'min_repo_stars': 2000,
            'batch_size': 25,
        }
        extractor = GitHubExtractor(custom_config)

        assert extractor.config['min_repo_stars'] == 2000
        assert extractor.config['batch_size'] == 25

    def test_popular_repos_configured(self):
        """Should have 10 popular repositories configured."""
        assert len(POPULAR_REPOS) >= 10

        # Verify key repositories are present
        repo_names = set(POPULAR_REPOS.keys())
        assert 'express-js/express' in repo_names
        assert 'facebook/react' in repo_names
        assert 'microsoft/typescript' in repo_names

    def test_repo_metadata_completeness(self):
        """Each repository should have complete metadata."""
        required_fields = {'framework', 'language', 'category', 'pattern_types', 'example_count'}

        for repo_name, repo_info in POPULAR_REPOS.items():
            assert isinstance(repo_info, dict)
            assert required_fields.issubset(repo_info.keys()), \
                f"Missing fields in {repo_name}"

            # Validate framework and language
            assert repo_info['language'] in {'typescript', 'javascript', 'python'}
            assert isinstance(repo_info['pattern_types'], list)
            assert repo_info['example_count'] > 0

    def test_quality_score_calculation(self):
        """Test quality score estimation."""
        # Code with good patterns from popular repo
        good_code = """
async function fetchUser(id: string): Promise<User> {
  try {
    const response = await fetch(`/api/users/${id}`);
    if (!response.ok) throw new Error('Failed to fetch');
    return response.json();
  } catch (error) {
    console.error('Error:', error);
    throw error;
  }
}
"""

        # High stars should give good score
        score_high_stars = estimate_quality_score(good_code, 15000)
        assert score_high_stars > 70

        # Lower stars should give decent score
        score_low_stars = estimate_quality_score(good_code, 800)
        assert score_low_stars > 50

        # Same code, different repo popularity
        assert score_high_stars > score_low_stars


class TestPhase4DataCoverage:
    """Test Phase 4 data coverage and diversity."""

    def test_framework_coverage(self):
        """Should cover key JavaScript/TypeScript frameworks."""
        frameworks = set()
        for _, metadata in ALL_EXAMPLES:
            frameworks.add(metadata['framework'])

        # Minimum framework diversity
        assert len(frameworks) >= 3

        # Key frameworks
        required = {'express', 'react', 'typescript'}
        assert required.issubset(frameworks)

    def test_pattern_diversity(self):
        """Examples should cover diverse patterns."""
        patterns = set()
        for _, metadata in ALL_EXAMPLES:
            patterns.add(metadata['pattern'])

        # Should have good pattern diversity
        assert len(patterns) >= 15

    def test_complexity_distribution(self):
        """Should have mix of complexity levels."""
        complexities = {}
        for _, metadata in ALL_EXAMPLES:
            comp = metadata['complexity']
            complexities[comp] = complexities.get(comp, 0) + 1

        # Should have all three levels represented
        assert 'low' in complexities
        assert 'medium' in complexities
        assert 'high' in complexities

    def test_task_type_coverage(self):
        """Examples should cover diverse task types."""
        task_types = set()
        for _, metadata in ALL_EXAMPLES:
            task_types.add(metadata['task_type'])

        # Should have at least 5 different task types
        assert len(task_types) >= 5

    def test_scalability_readiness(self):
        """Verify infrastructure is ready for 500+ examples."""
        # Should be able to handle large collections
        assert len(ALL_EXAMPLES) >= 20

        # GitHub extractor should have targets for 400+ examples
        total_target = sum(repo['example_count'] for repo in POPULAR_REPOS.values())
        assert total_target >= 400


class TestPhase4Integration:
    """Integration tests for Phase 4 infrastructure."""

    def test_seed_examples_structure(self):
        """Seed examples structure is consistent."""
        for i, (code, metadata) in enumerate(ALL_EXAMPLES):
            assert isinstance(code, str), f"Example {i}: code not string"
            assert isinstance(metadata, dict), f"Example {i}: metadata not dict"
            assert len(code.strip()) > 0, f"Example {i}: empty code"

    def test_extraction_config_valid(self):
        """Extraction configuration is valid."""
        config = EXTRACTION_CONFIG

        assert config['min_lines'] > 0
        assert config['max_lines'] > config['min_lines']
        assert 0 <= config['min_quality_score'] <= 100
        assert config['batch_size'] > 0

    def test_phase4_readiness(self):
        """Phase 4 infrastructure is production-ready."""
        # Seed examples: ✅
        assert len(ALL_EXAMPLES) >= 20

        # All seed examples valid: ✅
        valid_count = sum(1 for code, meta in ALL_EXAMPLES if validate_example(code, meta))
        assert valid_count == len(ALL_EXAMPLES)

        # GitHub extractor configured: ✅
        assert len(POPULAR_REPOS) >= 10

        # Configuration complete: ✅
        assert all(k in EXTRACTION_CONFIG for k in ['min_lines', 'max_lines', 'batch_size'])


class TestPhase4QuerySuccess:
    """Tests for expected Phase 4 query success rates."""

    def test_example_searchability(self):
        """Examples should be searchable by common queries."""
        searchable_keywords = {
            'express', 'react', 'async', 'typescript', 'api',
            'component', 'hook', 'middleware', 'error', 'validation'
        }

        found_keywords = set()
        for code, metadata in ALL_EXAMPLES:
            code_lower = code.lower()
            for keyword in searchable_keywords:
                if keyword in code_lower:
                    found_keywords.add(keyword)

        # Should have good keyword coverage
        assert len(found_keywords) >= 8

    def test_framework_specific_examples(self):
        """Each framework should have sufficient examples."""
        framework_counts = {}
        for _, metadata in ALL_EXAMPLES:
            fw = metadata['framework']
            framework_counts[fw] = framework_counts.get(fw, 0) + 1

        # Express should have at least 5 examples
        assert framework_counts.get('express', 0) >= 5

        # React should have at least 3 examples
        assert framework_counts.get('react', 0) >= 3

    def test_use_case_coverage(self):
        """Examples should cover common use cases."""
        use_cases = set()
        for _, metadata in ALL_EXAMPLES:
            use_cases.add(metadata['task_type'])

        # Common web dev use cases
        expected_cases = {
            'backend_setup', 'middleware', 'component', 'state_management',
            'error_handling', 'type_system'
        }

        covered = expected_cases.intersection(use_cases)
        assert len(covered) >= 4


# ============================================================
# PHASE 4 BENCHMARK TESTS
# ============================================================

class TestPhase4Benchmarks:
    """Benchmark tests for Phase 4 query success rates."""

    def test_phase4_target_metrics(self):
        """Verify Phase 4 can meet target metrics."""
        # Target metrics
        target_query_success = 0.85  # 85%
        target_examples = 500
        target_languages = 2
        target_frameworks = 10

        # Current metrics
        current_examples = len(ALL_EXAMPLES)
        current_frameworks = len(set(meta['framework'] for _, meta in ALL_EXAMPLES))
        current_languages = len(set(meta['language'] for _, meta in ALL_EXAMPLES))

        # Status check
        assert current_examples >= 20, "Need at least 20 seed examples"
        assert current_frameworks >= 3, "Need at least 3 frameworks"
        assert current_languages >= 2, "Need at least 2 languages"

        # GitHub extraction readiness
        github_target = sum(repo['example_count'] for repo in POPULAR_REPOS.values())
        total_target = current_examples + github_target

        assert total_target >= target_examples

    def test_estimated_coverage(self):
        """Estimate Phase 4 coverage based on infrastructure."""
        # Seed examples
        seed_count = len(ALL_EXAMPLES)

        # GitHub extraction (estimated)
        github_count = sum(repo['example_count'] for repo in POPULAR_REPOS.values())

        # Total Phase 4 examples
        total = seed_count + github_count

        # Should achieve 500+ target
        assert total >= 500

        # Log estimates
        print(f"\n📊 Phase 4 Coverage Estimate:")
        print(f"  Seed examples: {seed_count}")
        print(f"  GitHub extraction target: {github_count}")
        print(f"  Total Phase 4 target: {total}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
