"""
Pattern Classifier - Multi-dimensional automatic categorization of code patterns.

Production implementation with domain classification, security inference,
and performance tier analysis for intelligent pattern organization.

Spec Reference: Task Group 1 - Pattern Classifier Implementation
Target Coverage: >90% (TDD approach)
"""

import re
from typing import Dict, Any, List, Tuple, Optional
from enum import Enum
from dataclasses import dataclass


class SecurityLevel(Enum):
    """Security risk classification aligned with OWASP."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PerformanceTier(Enum):
    """Performance complexity tier based on Big-O analysis."""
    LOW = "low"          # O(1), O(log n), simple operations
    MEDIUM = "medium"    # O(n), O(n log n), database queries
    HIGH = "high"        # O(n²)+, recursive, complex data processing


@dataclass
class DomainClassification:
    """Result of domain classification."""
    primary: str
    confidence: float
    secondary: Optional[str] = None
    tags: Optional[List[str]] = None

    def __post_init__(self) -> None:
        if self.tags is None:
            self.tags = []


@dataclass
class SecurityClassification:
    """Result of security level inference."""
    level: SecurityLevel
    confidence: float
    reasoning: str


@dataclass
class PerformanceClassification:
    """Result of performance tier inference."""
    tier: PerformanceTier
    confidence: float
    complexity: str
    suggestions: Optional[List[str]] = None


@dataclass
class ClassificationResult:
    """
    Complete classification result for PatternBank integration.

    This is the object returned by PatternClassifier.classify() and consumed
    by PatternBank for Qdrant/Neo4j storage.
    """
    # Domain classification (primary fields for PatternBank)
    category: str  # Primary domain
    confidence: float  # Primary confidence score

    # Additional domain info
    subcategory: Optional[str] = None  # Secondary domain
    tags: Optional[List[str]] = None  # Domain tags

    # Security classification
    security_level: str = "low"  # SecurityLevel enum value
    security_confidence: float = 0.0
    security_reasoning: str = ""

    # Performance classification
    performance_tier: str = "low"  # PerformanceTier enum value
    performance_confidence: float = 0.0
    complexity: str = "O(1)"
    performance_suggestions: Optional[List[str]] = None

    def __post_init__(self) -> None:
        if self.tags is None:
            self.tags = []
        if self.performance_suggestions is None:
            self.performance_suggestions = []


class PatternClassifier:
    """
    Multi-dimensional pattern classification for automatic categorization.

    Classifies code patterns across three dimensions:
    1. Domain: auth, crud, api, validation, data_transform, etc.
    2. Security: LOW, MEDIUM, HIGH, CRITICAL risk levels
    3. Performance: LOW, MEDIUM, HIGH complexity tiers

    **Design Principles**:
    - Multi-keyword matching with priority scoring
    - Framework-aware domain detection
    - OWASP-aligned security classification
    - Big-O based performance analysis
    - Domain hierarchy support (parent-child relationships)

    **Example Usage**:
    ```python
    classifier = PatternClassifier()

    result = classifier.classify(
        code='async def hash_password(password: str) -> str:\\n    return bcrypt.hash(password)',
        name='hash_password',
        description='Hash user password with bcrypt'
    )

    # result = {
    #     'category': 'auth',
    #     'confidence': 0.95,
    #     'subcategory': 'password_hashing',
    #     'tags': ['security', 'encryption', 'async'],
    #     'security_level': 'CRITICAL',
    #     'security_reasoning': 'Password hashing detected (bcrypt)',
    #     'performance_tier': 'MEDIUM',
    #     'complexity': 'O(n) - cryptographic operation'
    # }
    ```
    """

    # Domain keyword mappings with priority scores
    DOMAIN_KEYWORDS = {
        'auth': {
            'keywords': ['auth', 'login', 'password', 'token', 'jwt', 'oauth',
                        'credential', 'session', 'authenticate', 'bcrypt', 'hash'],
            'priority': 0.95,
            'parent': 'security'
        },
        'crud': {
            'keywords': ['create', 'read', 'update', 'delete', 'insert', 'select',
                        'upsert', 'remove', 'get', 'post', 'put', 'patch'],
            'priority': 0.85,
            'parent': 'api'
        },
        'api': {
            'keywords': ['endpoint', 'route', 'router', 'fastapi', 'apiRouter',
                        'request', 'response', '@app', 'httpexception', 'depends'],
            'priority': 0.90,
            'parent': None
        },
        'validation': {
            'keywords': ['validate', 'validator', 'field', 'basemodel', 'pydantic',
                        'schema', 'check', 'verify', 'sanitize', 'clean'],
            'priority': 0.85,
            'parent': 'data_modeling'
        },
        'data_transform': {
            'keywords': ['transform', 'convert', 'map', 'filter', 'reduce',
                        'serialize', 'deserialize', 'parse', 'format'],
            'priority': 0.80,
            'parent': 'business_logic'
        },
        'business_logic': {
            'keywords': ['calculate', 'compute', 'process', 'analyze', 'evaluate',
                        'business', 'logic', 'rule', 'decision'],
            'priority': 0.75,
            'parent': None
        },
        'testing': {
            'keywords': ['test', 'pytest', 'unittest', 'assert', 'mock', 'fixture',
                        'parametrize', 'coverage', 'spec'],
            'priority': 0.90,
            'parent': None
        },
        'async_operations': {
            'keywords': ['asyncio', 'coroutine', 'future',
                        'concurrent', 'parallel', 'task', 'gather', 'create_task'],
            'priority': 0.75,  # Lower priority - async is common in modern code
            'parent': None
        },
        'data_modeling': {
            'keywords': ['model', 'schema', 'entity', 'dto', 'basemodel', 'field',
                        'relationship', 'foreign', 'primary'],
            'priority': 0.85,
            'parent': None
        }
    }

    # Framework-specific indicators
    FRAMEWORK_INDICATORS = {
        'fastapi': ['@app', 'APIRouter', 'Depends', 'HTTPException', 'fastapi'],
        'pydantic': ['BaseModel', 'Field', 'validator', 'pydantic'],
        'pytest': ['pytest', 'fixture', 'parametrize', 'unittest', 'assert']
    }

    # Security keyword mappings by level
    SECURITY_KEYWORDS = {
        SecurityLevel.CRITICAL: [
            'password', 'token', 'secret', 'key', 'credential', 'encryption',
            'decrypt', 'private', 'jwt', 'oauth', 'bcrypt', 'hash'
        ],
        SecurityLevel.HIGH: [
            'user', 'auth', 'authorization', 'permission', 'session', 'cookie',
            'pii', 'personal', 'sensitive', 'admin'
        ],
        SecurityLevel.MEDIUM: [
            'validate', 'sanitize', 'input', 'output', 'escape', 'filter',
            'check', 'verify'
        ],
        SecurityLevel.LOW: [
            'transform', 'format', 'display', 'render', 'calculate', 'compute'
        ]
    }

    # Performance pattern indicators
    PERFORMANCE_PATTERNS = {
        'async': {'tier': PerformanceTier.MEDIUM, 'complexity': 'O(n) - I/O bound'},
        'loop': {'tier': PerformanceTier.MEDIUM, 'complexity': 'O(n) - iteration'},
        'nested_loop': {'tier': PerformanceTier.HIGH, 'complexity': 'O(n²) - nested iteration'},
        'recursive': {'tier': PerformanceTier.HIGH, 'complexity': 'O(2^n) or O(n log n) - recursion'},
        'database': {'tier': PerformanceTier.MEDIUM, 'complexity': 'O(n) - database query'},
        'simple': {'tier': PerformanceTier.LOW, 'complexity': 'O(1) - constant time'}
    }

    def __init__(self) -> None:
        """Initialize pattern classifier with domain and security mappings."""
        pass

    def classify(self, code: str, name: str, description: str) -> ClassificationResult:
        """
        Classify a pattern based on code, name, and description.

        Performs multi-dimensional classification across:
        - Domain (auth, crud, api, validation, etc.)
        - Security level (LOW, MEDIUM, HIGH, CRITICAL)
        - Performance tier (LOW, MEDIUM, HIGH)

        Args:
            code: The code snippet to classify
            name: Pattern name/purpose
            description: Pattern description/intent

        Returns:
            ClassificationResult object with category, confidence, security, performance

        Example:
            >>> classifier = PatternClassifier()
            >>> result = classifier.classify(
            ...     code='async def hash_password(pwd: str): return bcrypt.hash(pwd)',
            ...     name='hash_password',
            ...     description='Hash user password'
            ... )
            >>> result.category
            'auth'
            >>> result.security_level
            'critical'
        """
        # Combine all text for analysis
        code_lower = code.lower()
        name_lower = name.lower()
        desc_lower = description.lower()
        combined = f"{code_lower} {name_lower} {desc_lower}"

        # Domain classification
        domain = self._classify_domain(code_lower, name_lower, desc_lower)

        # Security level inference
        security = self._infer_security_level(code_lower, name_lower, desc_lower)

        # Performance tier inference
        performance = self._infer_performance_tier(code_lower)

        return ClassificationResult(
            category=domain.primary,
            confidence=domain.confidence,
            subcategory=domain.secondary,
            tags=domain.tags,
            security_level=security.level.value,
            security_confidence=security.confidence,
            security_reasoning=security.reasoning,
            performance_tier=performance.tier.value,
            performance_confidence=performance.confidence,
            complexity=performance.complexity,
            performance_suggestions=performance.suggestions
        )

    def _classify_domain(
        self,
        code: str,
        name: str,
        description: str
    ) -> DomainClassification:
        """
        Classify pattern domain using multi-keyword matching.

        Combines code + name + description analysis with framework detection
        to determine primary domain, secondary domain, and tags.

        Args:
            code: Lowercase code snippet
            name: Lowercase pattern name
            description: Lowercase pattern description

        Returns:
            DomainClassification with primary, secondary, confidence, tags
        """
        combined = f"{code} {name} {description}"

        # Score each domain
        domain_scores = {}
        for domain, config in self.DOMAIN_KEYWORDS.items():
            score = 0.0
            matched_keywords = []

            for keyword in config['keywords']:
                if keyword in combined:
                    score += 1
                    matched_keywords.append(keyword)

            # Normalize score by number of keywords and apply priority
            if score > 0:
                normalized = (score / len(config['keywords'])) * config['priority']
                domain_scores[domain] = {
                    'score': normalized,
                    'keywords': matched_keywords
                }

        # Framework boost
        framework_boost = self._detect_framework_boost(code)
        for domain, boost in framework_boost.items():
            if domain in domain_scores:
                domain_scores[domain]['score'] += boost
            else:
                domain_scores[domain] = {'score': boost, 'keywords': []}

        # Sort by score
        sorted_domains = sorted(
            domain_scores.items(),
            key=lambda x: x[1]['score'],
            reverse=True
        )

        if not sorted_domains:
            # Fallback to general
            return DomainClassification(
                primary='general',
                confidence=0.5,
                secondary=None,
                tags=[]
            )

        # Primary domain
        primary = sorted_domains[0][0]
        primary_score = sorted_domains[0][1]['score']

        # Secondary domain if close
        secondary = None
        if len(sorted_domains) > 1:
            second_score = sorted_domains[1][1]['score']
            if primary_score - second_score < 0.15:
                secondary = sorted_domains[1][0]

        # Generate tags from matched keywords
        tags = []
        for domain, data in sorted_domains[:3]:  # Top 3 domains
            tags.extend(data['keywords'][:2])  # Top 2 keywords per domain
        tags = list(set(tags))[:5]  # Unique, max 5 tags

        # Calculate confidence (0.0-1.0)
        # Boost confidence if we have strong signals
        confidence = min(primary_score, 1.0)

        # Boost for high-priority matches
        if primary in ['auth', 'api', 'testing'] and primary_score >= 0.5:
            confidence = min(confidence + 0.2, 1.0)

        # Boost for framework matches
        if primary in framework_boost:
            confidence = min(confidence + 0.15, 1.0)

        # Ensure minimum confidence
        if confidence < 0.65:
            confidence = 0.65  # Minimum confidence

        return DomainClassification(
            primary=primary,
            confidence=confidence,
            secondary=secondary,
            tags=tags
        )

    def _detect_framework_boost(self, code: str) -> Dict[str, float]:
        """
        Detect frameworks in code and boost relevant domains.

        Args:
            code: Lowercase code snippet

        Returns:
            Dictionary of domain -> boost score
        """
        boosts = {}

        # FastAPI → api domain
        if any(indicator in code for indicator in self.FRAMEWORK_INDICATORS['fastapi']):
            boosts['api'] = 0.2

        # Pydantic → validation/data_modeling
        if any(indicator in code for indicator in self.FRAMEWORK_INDICATORS['pydantic']):
            boosts['validation'] = 0.15
            boosts['data_modeling'] = 0.15

        # Pytest → testing
        if any(indicator in code for indicator in self.FRAMEWORK_INDICATORS['pytest']):
            boosts['testing'] = 0.25

        return boosts

    def _infer_security_level(
        self,
        code: str,
        name: str,
        description: str
    ) -> SecurityClassification:
        """
        Infer security risk level using keyword analysis and code patterns.

        Classifies patterns as LOW, MEDIUM, HIGH, or CRITICAL based on:
        - Security-sensitive keywords (password, token, encryption)
        - Cryptographic operations (bcrypt, hashlib, jwt)
        - Authentication/authorization patterns

        Args:
            code: Lowercase code snippet
            name: Lowercase pattern name
            description: Lowercase pattern description

        Returns:
            SecurityClassification with level, confidence, reasoning
        """
        combined = f"{code} {name} {description}"

        # Check for security keywords by level
        level_matches: Dict[SecurityLevel, List[str]] = {
            SecurityLevel.CRITICAL: [],
            SecurityLevel.HIGH: [],
            SecurityLevel.MEDIUM: [],
            SecurityLevel.LOW: []
        }

        for level, keywords in self.SECURITY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in combined:
                    level_matches[level].append(keyword)

        # Determine highest security level with matches
        if level_matches[SecurityLevel.CRITICAL]:
            level = SecurityLevel.CRITICAL
            confidence = 0.95
            reasoning = f"Critical security operations detected: {', '.join(level_matches[SecurityLevel.CRITICAL][:3])}"
        elif level_matches[SecurityLevel.HIGH]:
            level = SecurityLevel.HIGH
            confidence = 0.85
            reasoning = f"High-security operations detected: {', '.join(level_matches[SecurityLevel.HIGH][:3])}"
        elif level_matches[SecurityLevel.MEDIUM]:
            level = SecurityLevel.MEDIUM
            confidence = 0.75
            reasoning = f"Input validation/sanitization detected: {', '.join(level_matches[SecurityLevel.MEDIUM][:3])}"
        else:
            level = SecurityLevel.LOW
            confidence = 0.70
            reasoning = "General business logic with no apparent security risks"

        # Boost confidence for cryptographic operations
        crypto_patterns = ['bcrypt', 'hashlib', 'jwt', 'encrypt', 'decrypt', 'hmac']
        if any(pattern in code for pattern in crypto_patterns):
            level = SecurityLevel.CRITICAL
            confidence = min(confidence + 0.1, 1.0)
            reasoning = "Cryptographic operations detected (CRITICAL security risk)"

        return SecurityClassification(
            level=level,
            confidence=confidence,
            reasoning=reasoning
        )

    def _infer_performance_tier(self, code: str) -> PerformanceClassification:
        """
        Infer performance tier using complexity analysis and code patterns.

        Analyzes code for:
        - Async/await patterns (I/O bound)
        - Loop structures (O(n) vs O(n²))
        - Recursive patterns
        - Database query patterns

        Args:
            code: Lowercase code snippet

        Returns:
            PerformanceClassification with tier, confidence, complexity, suggestions
        """
        tier = PerformanceTier.LOW
        complexity = "O(1) - constant time"
        suggestions = []
        confidence = 0.80

        # Async/await detection
        if 'async def' in code or 'await' in code:
            tier = PerformanceTier.MEDIUM
            complexity = "O(n) - I/O bound async operation"
            suggestions.append("Already using async/await for I/O optimization")
            confidence = 0.85

        # Database query patterns
        if any(pattern in code for pattern in ['query', 'select', 'filter', 'join']):
            tier = PerformanceTier.MEDIUM
            complexity = "O(n) - database query"
            suggestions.append("Consider adding database indexes for large datasets")
            confidence = 0.80

        # Loop detection
        loop_count = code.count('for ') + code.count('while ')
        if loop_count == 1:
            tier = PerformanceTier.MEDIUM
            complexity = "O(n) - single loop iteration"
            suggestions.append("Single loop is acceptable for most use cases")
            confidence = 0.85
        elif loop_count >= 2:
            # Check for nested loops
            if self._has_nested_loops(code):
                tier = PerformanceTier.HIGH
                complexity = "O(n²) or higher - nested loops detected"
                suggestions.append("Consider algorithm optimization to reduce complexity")
                suggestions.append("Evaluate if set/dict lookups can replace inner loop")
                confidence = 0.90
            else:
                tier = PerformanceTier.MEDIUM
                complexity = "O(n) - sequential loops"

        # Recursive pattern detection
        def_pattern = r'def\s+(\w+)\s*\('
        func_names = re.findall(def_pattern, code)
        for func_name in func_names:
            # Check if function calls itself
            if re.search(rf'{func_name}\s*\(', code.split(f'def {func_name}')[1] if f'def {func_name}' in code else ''):
                tier = PerformanceTier.HIGH
                complexity = "O(2^n) or O(n log n) - recursive algorithm"
                suggestions.append("Consider iterative solution if stack depth is a concern")
                suggestions.append("Add memoization for overlapping subproblems")
                confidence = 0.85
                break

        # Large data structure operations
        if any(op in code for op in ['sort', 'sorted', 'heapq', 'bisect']):
            tier = PerformanceTier.MEDIUM
            complexity = "O(n log n) - sorting operation"
            suggestions.append("Built-in sort is highly optimized (Timsort)")
            confidence = 0.85

        return PerformanceClassification(
            tier=tier,
            confidence=confidence,
            complexity=complexity,
            suggestions=suggestions
        )

    def _has_nested_loops(self, code: str) -> bool:
        """
        Detect nested loop structures in code.

        Args:
            code: Lowercase code snippet

        Returns:
            True if nested loops detected, False otherwise
        """
        # Simple heuristic: if we have 2+ loops, check indentation depth
        loop_count = code.count('for ') + code.count('while ')

        if loop_count < 2:
            return False

        # Split by lines and track indentation levels
        lines = code.split('\n')
        loop_indent_levels = []

        for line in lines:
            if 'for ' in line or 'while ' in line:
                # Count leading whitespace
                indent = len(line) - len(line.lstrip())
                loop_indent_levels.append(indent)

        # If we have loops at different indentation levels, it's nested
        if len(loop_indent_levels) >= 2:
            unique_indents = set(loop_indent_levels)
            if len(unique_indents) >= 2:
                return True

        return False
