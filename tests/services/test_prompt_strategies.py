"""
Tests for Prompt Strategies Implementation

Comprehensive test coverage for:
- Python strategy (FastAPI, Pytest)
- JavaScript strategy (React, Express)
- TypeScript strategy (Next.js, React TypeScript)
- Config file strategy (JSON, YAML, Markdown)
- Feedback loop integration
- Pattern-based enhancements

Target: >90% coverage, 16-24 tests
"""

import pytest
from unittest.mock import Mock, MagicMock

from src.services.prompt_strategies import (
    PromptContext,
    GeneratedPrompt,
    PromptStrategy,
    PythonPromptStrategy,
    JavaScriptPromptStrategy,
    TypeScriptPromptStrategy,
    ConfigFilePromptStrategy,
    PromptStrategyFactory,
)
from src.services.file_type_detector import (
    FileType,
    FileTypeDetection,
    Framework,
    FrameworkDetection,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def basic_file_type_detection():
    """Basic file type detection without frameworks."""
    return FileTypeDetection(
        file_type=FileType.PYTHON,
        confidence=0.95,
        reasoning="File extension .py",
        frameworks=[],
        detected_imports=[]
    )


@pytest.fixture
def fastapi_file_type_detection():
    """File type detection with FastAPI framework."""
    return FileTypeDetection(
        file_type=FileType.PYTHON,
        confidence=0.95,
        reasoning="File extension .py + FastAPI keywords",
        frameworks=[
            FrameworkDetection(
                framework=Framework.FASTAPI,
                confidence=0.90,
                version_hint="0.65+"
            )
        ],
        detected_imports=['fastapi', 'pydantic']
    )


@pytest.fixture
def react_file_type_detection():
    """File type detection with React framework."""
    return FileTypeDetection(
        file_type=FileType.JAVASCRIPT,
        confidence=0.90,
        reasoning="File extension .jsx + React keywords",
        frameworks=[
            FrameworkDetection(
                framework=Framework.REACT,
                confidence=0.85,
                version_hint="16.8+"
            )
        ],
        detected_imports=['react']
    )


@pytest.fixture
def nextjs_file_type_detection():
    """File type detection with Next.js framework."""
    return FileTypeDetection(
        file_type=FileType.TYPESCRIPT,
        confidence=0.95,
        reasoning="File extension .tsx + Next.js keywords",
        frameworks=[
            FrameworkDetection(
                framework=Framework.NEXTJS,
                confidence=0.90,
                version_hint="13+"
            )
        ],
        detected_imports=['next']
    )


@pytest.fixture
def basic_prompt_context(basic_file_type_detection):
    """Basic prompt context without feedback."""
    return PromptContext(
        task_number=1,
        task_name="Create user validation",
        task_description="Implement email validation function",
        complexity="O(1) - Simple validation",
        file_type_detection=basic_file_type_detection
    )


@pytest.fixture
def fastapi_prompt_context(fastapi_file_type_detection):
    """Prompt context for FastAPI endpoint."""
    return PromptContext(
        task_number=2,
        task_name="Create user endpoint",
        task_description="Build FastAPI endpoint for user creation",
        complexity="O(1) - REST endpoint",
        file_type_detection=fastapi_file_type_detection
    )


@pytest.fixture
def error_feedback_context(basic_file_type_detection):
    """Prompt context with error feedback."""
    return PromptContext(
        task_number=3,
        task_name="Fix validation error",
        task_description="Fix TypeError in validation function",
        complexity="O(1) - Bug fix",
        file_type_detection=basic_file_type_detection,
        last_error='File "validators.py", line 42, in validate_email\nTypeError: missing 1 required positional argument: \'email\''
    )


@pytest.fixture
def pattern_feedback_context(basic_file_type_detection):
    """Prompt context with successful patterns."""
    mock_pattern = {
        'task_description': 'Email validation with regex',
        'generated_code': 'def validate_email(email: str) -> bool:\n    return re.match(r"^[\\w.-]+@[\\w.-]+\\.\\w+$", email) is not None'
    }

    return PromptContext(
        task_number=4,
        task_name="Implement validation",
        task_description="Add email validation",
        complexity="O(1) - Validation",
        file_type_detection=basic_file_type_detection,
        successful_patterns=[mock_pattern, mock_pattern, mock_pattern]
    )


# ============================================================================
# Task 3.1: Python Prompt Strategy Tests
# ============================================================================

def test_python_strategy_basic_prompt(basic_prompt_context):
    """Test basic Python prompt generation."""
    strategy = PythonPromptStrategy()
    result = strategy.generate_prompt(basic_prompt_context)

    assert isinstance(result, GeneratedPrompt)
    assert "Python Best Practices" in result.prompt
    assert "Type Hints" in result.prompt
    assert "PEP 8" in result.prompt
    assert result.strategy_name == "PythonPromptStrategy"
    assert result.framework_specific is False


def test_python_strategy_fastapi_specifics(fastapi_prompt_context):
    """Test FastAPI-specific prompt generation."""
    strategy = PythonPromptStrategy()
    result = strategy.generate_prompt(fastapi_prompt_context)

    assert "FastAPI Best Practices" in result.prompt
    assert "Pydantic Models" in result.prompt
    assert "Dependency Injection" in result.prompt
    assert "HTTPException" in result.prompt
    assert result.framework_specific is True


def test_python_strategy_pytest_specifics():
    """Test Pytest-specific prompt generation."""
    pytest_detection = FileTypeDetection(
        file_type=FileType.PYTHON,
        confidence=0.95,
        reasoning="Test file",
        frameworks=[
            FrameworkDetection(Framework.PYTEST, 0.90)
        ],
        detected_imports=['pytest']
    )

    context = PromptContext(
        task_number=1,
        task_name="Write tests",
        task_description="Add test coverage",
        complexity="O(1)",
        file_type_detection=pytest_detection
    )

    strategy = PythonPromptStrategy()
    result = strategy.generate_prompt(context)

    assert "Pytest Best Practices" in result.prompt
    assert "fixtures" in result.prompt.lower()
    assert "parametrize" in result.prompt.lower()
    assert "95%" in result.prompt  # Coverage requirement


def test_python_strategy_pattern_integration(pattern_feedback_context):
    """Test pattern integration in Python prompts."""
    strategy = PythonPromptStrategy()
    result = strategy.generate_prompt_with_feedback(pattern_feedback_context)

    assert "Successful Patterns" in result.prompt
    assert "Reference Pattern 1" in result.prompt
    assert "Email validation" in result.prompt
    assert result.pattern_count == 3
    assert result.error_feedback_included is False


# ============================================================================
# Task 3.2: JavaScript Prompt Strategy Tests
# ============================================================================

def test_javascript_strategy_basic_prompt():
    """Test basic JavaScript prompt generation."""
    js_detection = FileTypeDetection(
        file_type=FileType.JAVASCRIPT,
        confidence=0.90,
        reasoning="JS keywords",
        frameworks=[],
        detected_imports=[]
    )

    context = PromptContext(
        task_number=1,
        task_name="Create utility",
        task_description="Build helper function",
        complexity="O(1)",
        file_type_detection=js_detection
    )

    strategy = JavaScriptPromptStrategy()
    result = strategy.generate_prompt(context)

    assert "JavaScript Best Practices" in result.prompt
    assert "ES6+" in result.prompt
    assert "const" in result.prompt
    assert "Arrow functions" in result.prompt
    assert result.strategy_name == "JavaScriptPromptStrategy"


def test_javascript_strategy_react_specifics(react_file_type_detection):
    """Test React-specific prompt generation."""
    context = PromptContext(
        task_number=1,
        task_name="Create component",
        task_description="Build UserCard component",
        complexity="O(1)",
        file_type_detection=react_file_type_detection
    )

    strategy = JavaScriptPromptStrategy()
    result = strategy.generate_prompt(context)

    assert "React Best Practices" in result.prompt
    assert "Functional Components" in result.prompt
    assert "useState" in result.prompt
    assert "useEffect" in result.prompt
    assert result.framework_specific is True


def test_javascript_strategy_express_specifics():
    """Test Express-specific prompt generation."""
    express_detection = FileTypeDetection(
        file_type=FileType.JAVASCRIPT,
        confidence=0.90,
        reasoning="Express keywords",
        frameworks=[
            FrameworkDetection(Framework.EXPRESS, 0.85)
        ],
        detected_imports=['express']
    )

    context = PromptContext(
        task_number=1,
        task_name="Create API route",
        task_description="Build user endpoint",
        complexity="O(1)",
        file_type_detection=express_detection
    )

    strategy = JavaScriptPromptStrategy()
    result = strategy.generate_prompt(context)

    assert "Express Best Practices" in result.prompt
    assert "Route Handlers" in result.prompt
    assert "Middleware" in result.prompt


# ============================================================================
# Task 3.3: TypeScript Prompt Strategy Tests
# ============================================================================

def test_typescript_strategy_basic_prompt():
    """Test basic TypeScript prompt generation."""
    ts_detection = FileTypeDetection(
        file_type=FileType.TYPESCRIPT,
        confidence=0.95,
        reasoning="TS file extension",
        frameworks=[],
        detected_imports=[]
    )

    context = PromptContext(
        task_number=1,
        task_name="Create type-safe function",
        task_description="Build validation with types",
        complexity="O(1)",
        file_type_detection=ts_detection
    )

    strategy = TypeScriptPromptStrategy()
    result = strategy.generate_prompt(context)

    assert "TypeScript Best Practices" in result.prompt
    assert "Strict Typing" in result.prompt
    assert "Interface Definitions" in result.prompt
    assert "strict: true" in result.prompt
    assert result.strategy_name == "TypeScriptPromptStrategy"


def test_typescript_strategy_nextjs_specifics(nextjs_file_type_detection):
    """Test Next.js-specific prompt generation."""
    context = PromptContext(
        task_number=1,
        task_name="Create page component",
        task_description="Build users page with SSR",
        complexity="O(1)",
        file_type_detection=nextjs_file_type_detection
    )

    strategy = TypeScriptPromptStrategy()
    result = strategy.generate_prompt(context)

    assert "Next.js Best Practices" in result.prompt
    assert "Server Components" in result.prompt
    assert "Metadata API" in result.prompt
    assert "App Router" in result.prompt
    assert result.framework_specific is True


def test_typescript_strategy_react_typescript():
    """Test React TypeScript-specific prompt generation."""
    react_ts_detection = FileTypeDetection(
        file_type=FileType.TYPESCRIPT,
        confidence=0.95,
        reasoning="TSX file",
        frameworks=[
            FrameworkDetection(Framework.REACT, 0.90)
        ],
        detected_imports=['react']
    )

    context = PromptContext(
        task_number=1,
        task_name="Create typed component",
        task_description="Build UserCard with TypeScript",
        complexity="O(1)",
        file_type_detection=react_ts_detection
    )

    strategy = TypeScriptPromptStrategy()
    result = strategy.generate_prompt(context)

    assert "React TypeScript" in result.prompt
    assert "Typed Props" in result.prompt
    assert "React.FC" in result.prompt


# ============================================================================
# Task 3.4: Config File Prompt Strategy Tests
# ============================================================================

def test_config_strategy_json():
    """Test JSON config prompt generation."""
    json_detection = FileTypeDetection(
        file_type=FileType.JSON,
        confidence=0.95,
        reasoning="JSON file extension",
        frameworks=[],
        detected_imports=[]
    )

    context = PromptContext(
        task_number=1,
        task_name="Create config",
        task_description="Build package.json",
        complexity="O(1)",
        file_type_detection=json_detection
    )

    strategy = ConfigFilePromptStrategy()
    result = strategy.generate_prompt(context)

    assert "Config File Best Practices" in result.prompt
    assert "JSON Syntax" in result.prompt
    assert "NO trailing commas" in result.prompt
    assert result.strategy_name == "ConfigFilePromptStrategy"


def test_config_strategy_yaml():
    """Test YAML config prompt generation."""
    yaml_detection = FileTypeDetection(
        file_type=FileType.YAML,
        confidence=0.95,
        reasoning="YAML file",
        frameworks=[],
        detected_imports=[]
    )

    context = PromptContext(
        task_number=1,
        task_name="Create CI config",
        task_description="Build .github/workflows/ci.yml",
        complexity="O(1)",
        file_type_detection=yaml_detection
    )

    strategy = ConfigFilePromptStrategy()
    result = strategy.generate_prompt(context)

    assert "YAML Syntax" in result.prompt
    assert "NO tabs" in result.prompt
    assert "spaces for indentation" in result.prompt


def test_config_strategy_markdown():
    """Test Markdown prompt generation."""
    md_detection = FileTypeDetection(
        file_type=FileType.MARKDOWN,
        confidence=0.95,
        reasoning="Markdown file",
        frameworks=[],
        detected_imports=[]
    )

    context = PromptContext(
        task_number=1,
        task_name="Create documentation",
        task_description="Write README.md",
        complexity="O(1)",
        file_type_detection=md_detection
    )

    strategy = ConfigFilePromptStrategy()
    result = strategy.generate_prompt(context)

    assert "Markdown Syntax" in result.prompt
    assert "Headers:" in result.prompt
    assert "Code blocks:" in result.prompt


# ============================================================================
# Task 3.5: Feedback Loop Integration Tests
# ============================================================================

def test_error_feedback_enrichment(error_feedback_context):
    """Test error message parsing and enrichment."""
    strategy = PythonPromptStrategy()
    result = strategy.generate_prompt_with_feedback(error_feedback_context)

    assert "PREVIOUS ATTEMPT FAILED" in result.prompt
    assert "TypeError" in result.prompt
    assert "validators.py" in result.prompt
    assert "line 42" in result.prompt
    assert result.error_feedback_included is True


def test_similar_error_formatting():
    """Test similar error formatting with solutions."""
    mock_error = Mock()
    mock_error.error_message = "AttributeError: 'NoneType' object has no attribute 'email'"
    mock_error.successful_fix = "Added null check before accessing email"

    context = PromptContext(
        task_number=1,
        task_name="Fix bug",
        task_description="Handle None values",
        complexity="O(1)",
        file_type_detection=FileTypeDetection(
            file_type=FileType.PYTHON,
            confidence=0.95,
            reasoning="Python file",
            frameworks=[],
            detected_imports=[]
        ),
        similar_errors=[mock_error, mock_error]
    )

    strategy = PythonPromptStrategy()
    result = strategy.generate_prompt_with_feedback(context)

    assert "Similar Errors" in result.prompt
    assert "AttributeError" in result.prompt
    assert "Added null check" in result.prompt
    assert result.error_feedback_included is True


def test_successful_pattern_retrieval(pattern_feedback_context):
    """Test successful pattern formatting."""
    strategy = PythonPromptStrategy()
    result = strategy.generate_prompt_with_feedback(pattern_feedback_context)

    assert "Successful Patterns" in result.prompt
    assert "Reference Pattern 1" in result.prompt
    assert "Reference Pattern 2" in result.prompt
    assert "Reference Pattern 3" in result.prompt
    assert "validate_email" in result.prompt
    assert result.pattern_count == 3


def test_prompt_enhancement_strategy():
    """Test complete prompt enhancement with all feedback types."""
    mock_error = Mock()
    mock_error.error_message = "ValueError: invalid email format"
    mock_error.successful_fix = "Added regex validation"

    mock_pattern = {
        'task_description': 'Email validator',
        'generated_code': 'def validate(email): return "@" in email'
    }

    context = PromptContext(
        task_number=1,
        task_name="Implement validation",
        task_description="Add comprehensive email validation",
        complexity="O(1)",
        file_type_detection=FileTypeDetection(
            file_type=FileType.PYTHON,
            confidence=0.95,
            reasoning="Python file",
            frameworks=[],
            detected_imports=[]
        ),
        last_error="ValueError: invalid email format",
        similar_errors=[mock_error],
        successful_patterns=[mock_pattern]
    )

    strategy = PythonPromptStrategy()
    result = strategy.generate_prompt_with_feedback(context)

    # All three feedback types should be present
    assert "PREVIOUS ATTEMPT FAILED" in result.prompt
    assert "Similar Errors" in result.prompt
    assert "Successful Patterns" in result.prompt
    assert result.error_feedback_included is True
    assert result.pattern_count == 1


# ============================================================================
# Task 3.6: Factory and Integration Tests
# ============================================================================

def test_factory_python_strategy():
    """Test factory creates Python strategy."""
    strategy = PromptStrategyFactory.get_strategy(FileType.PYTHON)
    assert isinstance(strategy, PythonPromptStrategy)


def test_factory_javascript_strategy():
    """Test factory creates JavaScript strategy."""
    strategy = PromptStrategyFactory.get_strategy(FileType.JAVASCRIPT)
    assert isinstance(strategy, JavaScriptPromptStrategy)


def test_factory_typescript_strategy():
    """Test factory creates TypeScript strategy."""
    strategy = PromptStrategyFactory.get_strategy(FileType.TYPESCRIPT)
    assert isinstance(strategy, TypeScriptPromptStrategy)


def test_factory_json_strategy():
    """Test factory creates ConfigFilePromptStrategy for JSON."""
    strategy = PromptStrategyFactory.get_strategy(FileType.JSON)
    assert isinstance(strategy, ConfigFilePromptStrategy)


def test_factory_yaml_strategy():
    """Test factory creates ConfigFilePromptStrategy for YAML."""
    strategy = PromptStrategyFactory.get_strategy(FileType.YAML)
    assert isinstance(strategy, ConfigFilePromptStrategy)


def test_factory_markdown_strategy():
    """Test factory creates ConfigFilePromptStrategy for Markdown."""
    strategy = PromptStrategyFactory.get_strategy(FileType.MARKDOWN)
    assert isinstance(strategy, ConfigFilePromptStrategy)


def test_factory_unknown_fallback():
    """Test factory falls back to Python for unknown types."""
    strategy = PromptStrategyFactory.get_strategy(FileType.UNKNOWN)
    assert isinstance(strategy, PythonPromptStrategy)


def test_factory_caching():
    """Test factory caches strategy instances."""
    PromptStrategyFactory.clear_cache()

    strategy1 = PromptStrategyFactory.get_strategy(FileType.PYTHON)
    strategy2 = PromptStrategyFactory.get_strategy(FileType.PYTHON)

    assert strategy1 is strategy2  # Same instance


def test_factory_clear_cache():
    """Test factory cache clearing."""
    strategy1 = PromptStrategyFactory.get_strategy(FileType.PYTHON)
    PromptStrategyFactory.clear_cache()
    strategy2 = PromptStrategyFactory.get_strategy(FileType.PYTHON)

    assert strategy1 is not strategy2  # Different instances after clear
