"""
File Type Detector - Multi-signal file type detection for code generation.

Production implementation with keyword detection, framework analysis,
import statement parsing, and confidence scoring for intelligent routing.

Spec Reference: Task Group 2 - File Type Detector Implementation
Target Coverage: >90% (TDD approach)
"""

import re
from enum import Enum
from typing import Optional, List, Dict, Tuple, Set
from dataclasses import dataclass


class FileType(Enum):
    """Supported file types for code generation."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JSON = "json"
    YAML = "yaml"
    MARKDOWN = "markdown"
    UNKNOWN = "unknown"


class Framework(Enum):
    """Detected frameworks with version hints."""
    FASTAPI = "fastapi"
    DJANGO = "django"
    FLASK = "flask"
    PYTEST = "pytest"
    REACT = "react"
    NEXTJS = "nextjs"
    VUE = "vue"
    EXPRESS = "express"
    UNKNOWN = "unknown"


@dataclass
class FrameworkDetection:
    """Result of framework detection."""
    framework: Framework
    confidence: float
    version_hint: Optional[str] = None


@dataclass
class FileTypeDetection:
    """
    Result of file type detection with reasoning.

    Compatible with ClassificationResult for consistency.
    """
    file_type: FileType
    confidence: float
    reasoning: str
    frameworks: Optional[List[FrameworkDetection]] = None
    detected_imports: Optional[List[str]] = None

    def __post_init__(self) -> None:
        if self.frameworks is None:
            self.frameworks = []
        if self.detected_imports is None:
            self.detected_imports = []


class FileTypeDetector:
    """
    Multi-signal file type detector for intelligent code generation routing.

    Detects file types across multiple dimensions:
    1. File extension (highest confidence: 0.95)
    2. Import statements (high confidence: 0.85)
    3. Framework keywords (medium confidence: 0.80)
    4. Generic language keywords (low confidence: 0.60)
    5. Task name/description (lowest confidence: 0.50)

    **Design Principles**:
    - Weighted multi-signal scoring
    - Framework-aware detection
    - Import-based language inference
    - Conflict resolution via extension priority
    - Clear reasoning string generation

    **Example Usage**:
    ```python
    detector = FileTypeDetector()

    result = detector.detect(
        task_name='Create FastAPI endpoint',
        task_description='Build REST endpoint for user validation',
        target_files=['src/api/users.py']
    )

    # result = FileTypeDetection(
    #     file_type=FileType.PYTHON,
    #     confidence=0.95,
    #     reasoning='File extension .py (0.95) + FastAPI keywords (0.80)',
    #     frameworks=[FrameworkDetection(Framework.FASTAPI, 0.90)],
    #     detected_imports=['fastapi', 'pydantic']
    # )
    ```
    """

    # Weight constants for confidence scoring
    WEIGHT_EXTENSION = 0.95
    WEIGHT_IMPORTS = 0.85
    WEIGHT_FRAMEWORK = 0.80
    WEIGHT_KEYWORDS = 0.60
    WEIGHT_TASK_DESC = 0.50

    # File extension mappings
    EXTENSIONS = {
        '.py': FileType.PYTHON,
        '.js': FileType.JAVASCRIPT,
        '.jsx': FileType.JAVASCRIPT,
        '.ts': FileType.TYPESCRIPT,
        '.tsx': FileType.TYPESCRIPT,
        '.json': FileType.JSON,
        '.yaml': FileType.YAML,
        '.yml': FileType.YAML,
        '.md': FileType.MARKDOWN,
        '.markdown': FileType.MARKDOWN,
    }

    # Language keyword patterns
    LANGUAGE_KEYWORDS = {
        FileType.PYTHON: {
            'keywords': [
                'def ', 'class ', 'import ', 'from ', 'async def',
                'pytest', 'pydantic', '__init__', 'self.', 'lambda',
            ],
            'type_hints': ['->', ':', 'Optional', 'List', 'Dict', 'Union'],
        },
        FileType.JAVASCRIPT: {
            'keywords': [
                'function', 'const ', 'let ', 'var ', '=>', 'async ',
                'await ', 'export ', 'require(', 'module.exports',
            ],
            'patterns': ['console.log', 'document.', 'window.'],
        },
        FileType.TYPESCRIPT: {
            'keywords': [
                'interface ', 'type ', 'enum ', ' as ', ': string',
                ': number', ': boolean', 'implements', 'extends',
            ],
            'patterns': ['React.FC', '<>', 'Promise<'],
        },
        FileType.JSON: {
            'patterns': ['{', '}', ':', '[', ']'],
            'anti_patterns': ['//', '/*', 'function', 'const'],
        },
        FileType.YAML: {
            'patterns': [':\n', '- ', 'name:', 'version:'],
            'anti_patterns': ['{', '}', ';', 'function'],
        },
        FileType.MARKDOWN: {
            'patterns': ['# ', '## ', '```', '* ', '- ', '[', ']'],
            'anti_patterns': ['function', 'class ', 'def '],
        },
    }

    # Framework detection patterns
    FRAMEWORK_PATTERNS = {
        Framework.FASTAPI: {
            'imports': ['fastapi', 'APIRouter', 'Depends'],
            'keywords': ['@app.', 'HTTPException', 'FastAPI()', '.get(', '.post('],
            'version_hints': {'async def': '0.65+'},
        },
        Framework.DJANGO: {
            'imports': ['django', 'models.Model', 'views'],
            'keywords': ['urls.py', 'admin.py', 'settings.py', 'Model'],
            'version_hints': {},
        },
        Framework.FLASK: {
            'imports': ['flask', 'Flask'],
            'keywords': ['@app.route', 'render_template', 'request.'],
            'version_hints': {},
        },
        Framework.PYTEST: {
            'imports': ['pytest'],
            'keywords': ['@pytest.', 'fixture', 'parametrize', 'test_'],
            'version_hints': {},
        },
        Framework.REACT: {
            'imports': ['react', 'useState', 'useEffect'],
            'keywords': ['jsx', '<Component', 'React.', 'className='],
            'version_hints': {'useState': '16.8+', 'useEffect': '16.8+'},
        },
        Framework.NEXTJS: {
            'imports': ['next', 'next/'],
            'keywords': ['getServerSideProps', 'getStaticProps', 'pages/', 'app/'],
            'version_hints': {'app/': '13+'},
        },
        Framework.VUE: {
            'imports': ['vue', 'ref(', 'computed('],
            'keywords': ['<template>', '<script setup>', '.vue', 'defineComponent'],
            'version_hints': {'ref(': '3.0+', 'computed(': '3.0+'},
        },
        Framework.EXPRESS: {
            'imports': ['express'],
            'keywords': ['app.get', 'app.post', 'req.', 'res.', 'middleware'],
            'version_hints': {},
        },
    }

    # Import regex patterns
    PYTHON_IMPORT_PATTERN = re.compile(
        r'(?:^|\n)\s*(?:import\s+([a-zA-Z_][a-zA-Z0-9_\.]*)|from\s+([a-zA-Z_][a-zA-Z0-9_\.]*)\s+import)',
        re.MULTILINE
    )
    JS_IMPORT_PATTERN = re.compile(
        r'(?:import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]|require\([\'"]([^\'"]+)[\'"]\))',
        re.MULTILINE | re.DOTALL
    )

    def __init__(self) -> None:
        """Initialize file type detector with language and framework patterns."""
        pass

    def detect(
        self,
        task_name: str,
        task_description: str,
        target_files: Optional[List[str]] = None,
        code_snippet: Optional[str] = None
    ) -> FileTypeDetection:
        """
        Detect file type using multi-signal analysis.

        Analyzes multiple signals with weighted confidence scoring:
        1. File extensions (0.95 weight)
        2. Import statements (0.85 weight)
        3. Framework keywords (0.80 weight)
        4. Generic keywords (0.60 weight)
        5. Task name/description (0.50 weight)

        Args:
            task_name: Name of the task
            task_description: Description of what needs to be done
            target_files: Optional list of target file paths
            code_snippet: Optional code content for analysis

        Returns:
            FileTypeDetection with file type, confidence, reasoning, frameworks

        Example:
            >>> detector = FileTypeDetector()
            >>> result = detector.detect(
            ...     task_name='Create user endpoint',
            ...     task_description='FastAPI endpoint for users',
            ...     target_files=['api/users.py']
            ... )
            >>> result.file_type
            FileType.PYTHON
            >>> result.confidence >= 0.90
            True
        """
        # Collect signals with scores
        signals: Dict[FileType, List[Tuple[str, float]]] = {}

        # Signal 1: File extension (highest priority)
        if target_files:
            ext_signal = self._detect_from_extension(target_files)
            if ext_signal:
                file_type, reasoning = ext_signal
                if file_type not in signals:
                    signals[file_type] = []
                signals[file_type].append((reasoning, self.WEIGHT_EXTENSION))

        # Signal 2: Import statements (if code provided)
        if code_snippet:
            import_signals = self._detect_from_imports(code_snippet)
            for file_type, reasoning in import_signals:
                if file_type not in signals:
                    signals[file_type] = []
                signals[file_type].append((reasoning, self.WEIGHT_IMPORTS))

        # Signal 3: Framework keywords
        combined_text = f"{task_name} {task_description} {code_snippet or ''}"
        framework_signals = self._detect_from_frameworks(combined_text)
        for file_type, reasoning in framework_signals:
            if file_type not in signals:
                signals[file_type] = []
            signals[file_type].append((reasoning, self.WEIGHT_FRAMEWORK))

        # Signal 4: Generic language keywords
        keyword_signals = self._detect_from_keywords(combined_text)
        for file_type, reasoning in keyword_signals:
            if file_type not in signals:
                signals[file_type] = []
            signals[file_type].append((reasoning, self.WEIGHT_KEYWORDS))

        # Signal 5: Task name/description hints
        task_signals = self._detect_from_task(task_name, task_description)
        for file_type, reasoning in task_signals:
            if file_type not in signals:
                signals[file_type] = []
            signals[file_type].append((reasoning, self.WEIGHT_TASK_DESC))

        # Score and select best file type
        if not signals:
            # Fallback to Python
            return FileTypeDetection(
                file_type=FileType.PYTHON,
                confidence=0.50,
                reasoning="No clear signals detected, defaulting to Python",
                frameworks=[],
                detected_imports=[]
            )

        # Calculate composite scores
        file_type_scores = {}
        for file_type, signal_list in signals.items():
            # Take max weight per signal type to avoid double-counting
            max_score = max(weight for _, weight in signal_list)
            file_type_scores[file_type] = max_score

        # Select highest scoring file type
        best_file_type = max(file_type_scores.items(), key=lambda x: x[1])
        detected_type, confidence = best_file_type

        # Build reasoning string
        reasoning_parts = []
        for reason, weight in signals[detected_type]:
            reasoning_parts.append(f"{reason} ({weight:.2f})")
        reasoning = " + ".join(reasoning_parts)

        # Detect frameworks
        frameworks = self._detect_frameworks(combined_text, detected_type)

        # Extract imports
        detected_imports = []
        if code_snippet:
            detected_imports = self._extract_imports(code_snippet, detected_type)

        return FileTypeDetection(
            file_type=detected_type,
            confidence=round(confidence, 2),
            reasoning=reasoning,
            frameworks=frameworks,
            detected_imports=detected_imports
        )

    def _detect_from_extension(
        self,
        target_files: List[str]
    ) -> Optional[Tuple[FileType, str]]:
        """
        Detect file type from file extensions.

        Args:
            target_files: List of file paths

        Returns:
            Tuple of (FileType, reasoning) or None
        """
        for file_path in target_files:
            for ext, file_type in self.EXTENSIONS.items():
                if file_path.endswith(ext):
                    return (file_type, f"File extension {ext}")
        return None

    def _detect_from_imports(
        self,
        code: str
    ) -> List[Tuple[FileType, str]]:
        """
        Detect file type from import statements.

        Args:
            code: Code snippet to analyze

        Returns:
            List of (FileType, reasoning) tuples
        """
        signals = []

        # Python imports
        python_matches = self.PYTHON_IMPORT_PATTERN.findall(code)
        if python_matches:
            signals.append((FileType.PYTHON, "Python import statements"))

        # JavaScript/TypeScript imports
        js_matches = self.JS_IMPORT_PATTERN.findall(code)
        if js_matches:
            # Distinguish TypeScript by type imports
            if 'type ' in code or 'interface ' in code:
                signals.append((FileType.TYPESCRIPT, "TypeScript import statements"))
            else:
                signals.append((FileType.JAVASCRIPT, "JavaScript import statements"))

        return signals

    def _detect_from_frameworks(
        self,
        text: str
    ) -> List[Tuple[FileType, str]]:
        """
        Detect file type based on framework patterns.

        Args:
            text: Combined text to analyze

        Returns:
            List of (FileType, reasoning) tuples
        """
        signals = []
        text_lower = text.lower()

        # Python frameworks
        if any(kw in text_lower for kw in ['fastapi', 'apiRouter', 'httpexception']):
            signals.append((FileType.PYTHON, "FastAPI framework keywords"))
        elif any(kw in text_lower for kw in ['django', 'models.model', 'urls.py']):
            signals.append((FileType.PYTHON, "Django framework keywords"))
        elif any(kw in text_lower for kw in ['flask', '@app.route', 'render_template']):
            signals.append((FileType.PYTHON, "Flask framework keywords"))
        elif any(kw in text_lower for kw in ['pytest', 'fixture', '@pytest']):
            signals.append((FileType.PYTHON, "Pytest framework keywords"))

        # JavaScript/TypeScript frameworks
        if any(kw in text_lower for kw in ['react', 'usestate', 'useeffect', 'jsx']):
            if 'typescript' in text_lower or ': fc' in text_lower:
                signals.append((FileType.TYPESCRIPT, "React TypeScript keywords"))
            else:
                signals.append((FileType.JAVASCRIPT, "React keywords"))
        elif any(kw in text_lower for kw in ['next.js', 'nextjs', 'getserversideprops']):
            signals.append((FileType.TYPESCRIPT, "Next.js keywords"))
        elif any(kw in text_lower for kw in ['vue', 'ref(', 'computed(', '<template>']):
            signals.append((FileType.JAVASCRIPT, "Vue keywords"))
        elif any(kw in text_lower for kw in ['express', 'app.get', 'middleware']):
            signals.append((FileType.JAVASCRIPT, "Express keywords"))

        return signals

    def _detect_from_keywords(
        self,
        text: str
    ) -> List[Tuple[FileType, str]]:
        """
        Detect file type from generic language keywords.

        Args:
            text: Text to analyze

        Returns:
            List of (FileType, reasoning) tuples
        """
        signals = []
        scores: Dict[FileType, int] = {}

        for file_type, patterns in self.LANGUAGE_KEYWORDS.items():
            score = 0

            # Check keywords
            if 'keywords' in patterns:
                for keyword in patterns['keywords']:
                    if keyword in text:
                        score += 1

            # Check type hints/patterns
            if 'type_hints' in patterns:
                for hint in patterns['type_hints']:
                    if hint in text:
                        score += 1
            if 'patterns' in patterns:
                for pattern in patterns['patterns']:
                    if pattern in text:
                        score += 1

            # Check anti-patterns (reduce score)
            if 'anti_patterns' in patterns:
                for anti in patterns['anti_patterns']:
                    if anti in text:
                        score -= 1

            if score > 0:
                scores[file_type] = score

        # Convert top scores to signals
        if scores:
            sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            for file_type, score in sorted_scores[:2]:  # Top 2
                if score >= 2:  # Minimum threshold
                    signals.append((file_type, f"{file_type.value} keywords"))

        return signals

    def _detect_from_task(
        self,
        task_name: str,
        task_description: str
    ) -> List[Tuple[FileType, str]]:
        """
        Detect file type from task name and description.

        Args:
            task_name: Task name
            task_description: Task description

        Returns:
            List of (FileType, reasoning) tuples
        """
        signals = []
        combined = f"{task_name} {task_description}".lower()

        # Language hints in task text
        if 'python' in combined:
            signals.append((FileType.PYTHON, "Task mentions Python"))
        elif 'typescript' in combined or '.ts' in combined:
            signals.append((FileType.TYPESCRIPT, "Task mentions TypeScript"))
        elif 'javascript' in combined or '.js' in combined:
            signals.append((FileType.JAVASCRIPT, "Task mentions JavaScript"))
        elif 'json' in combined:
            signals.append((FileType.JSON, "Task mentions JSON"))
        elif 'yaml' in combined or '.yml' in combined:
            signals.append((FileType.YAML, "Task mentions YAML"))
        elif 'markdown' in combined or '.md' in combined:
            signals.append((FileType.MARKDOWN, "Task mentions Markdown"))

        return signals

    def _detect_frameworks(
        self,
        text: str,
        file_type: FileType
    ) -> List[FrameworkDetection]:
        """
        Detect frameworks present in code/task.

        Args:
            text: Text to analyze
            file_type: Detected file type

        Returns:
            List of FrameworkDetection objects
        """
        detections = []
        text_lower = text.lower()

        for framework, patterns in self.FRAMEWORK_PATTERNS.items():
            score = 0
            version_hint = None

            # Check imports
            if 'imports' in patterns:
                for imp in patterns['imports']:
                    if imp.lower() in text_lower:
                        score += 2  # Imports are strong signal

            # Check keywords
            if 'keywords' in patterns:
                for keyword in patterns['keywords']:
                    if keyword.lower() in text_lower:
                        score += 1

            # Check version hints
            if 'version_hints' in patterns and patterns['version_hints']:
                for hint_keyword, version in patterns['version_hints'].items():
                    if hint_keyword.lower() in text_lower:
                        version_hint = version
                        score += 1

            # If score is high enough, add detection
            if score >= 2:
                confidence = min(0.50 + (score * 0.10), 0.95)
                detections.append(FrameworkDetection(
                    framework=framework,
                    confidence=round(confidence, 2),
                    version_hint=version_hint
                ))

        # Sort by confidence
        detections.sort(key=lambda x: x.confidence, reverse=True)
        return detections

    def _extract_imports(
        self,
        code: str,
        file_type: FileType
    ) -> List[str]:
        """
        Extract import statements from code.

        Args:
            code: Code snippet
            file_type: Detected file type

        Returns:
            List of imported module names
        """
        imports: Set[str] = set()

        if file_type == FileType.PYTHON:
            # Python imports
            matches = self.PYTHON_IMPORT_PATTERN.findall(code)
            for match in matches:
                # match is tuple (import_module, from_module)
                module = match[0] or match[1]
                if module:
                    # Extract root package
                    root = module.split('.')[0]
                    imports.add(root)

        elif file_type in [FileType.JAVASCRIPT, FileType.TYPESCRIPT]:
            # JavaScript/TypeScript imports
            matches = self.JS_IMPORT_PATTERN.findall(code)
            for match in matches:
                # match is tuple (import_path, require_path)
                module = match[0] or match[1]
                if module:
                    # Extract package name (ignore relative imports)
                    if not module.startswith('.'):
                        root = module.split('/')[0]
                        imports.add(root)

        return sorted(list(imports))


# Singleton instance
_detector_instance: Optional[FileTypeDetector] = None


def get_file_type_detector() -> FileTypeDetector:
    """Get singleton file type detector instance."""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = FileTypeDetector()
    return _detector_instance
