# Specification: Stub Modules Complete Implementation

## Goal

Transform 5 minimal stub modules into production-ready implementations to enable full-featured code generation with multi-language support, semantic pattern classification, and automated pattern promotion.

## Executive Summary

**Current State**: 5 stub modules (~313 LOC total) created on 2025-11-20 with minimal functionality
**Problem**: Stubs unblock E2E testing but lack production features needed for quality code generation
**Solution**: Complete implementation of all 5 modules with comprehensive validation, classification, and feedback loops
**Timeline**: 71.5 hours (~9 days) across 3 priority waves
**Expected Impact**: Enable 30%+ pattern reuse, multi-language support, 95%+ validation accuracy

### The Problem: Incomplete Infrastructure

Current stubs enable basic E2E pipeline execution but have critical limitations:

```
pattern_classifier.py: Only keyword-based, no ML classification
file_type_detector.py: Hardcoded Python default, no framework detection
prompt_strategies.py: Single generic strategy, no language-specific optimization
validation_strategies.py: Python-only, no TypeScript/JavaScript support
pattern_feedback_integration.py: Stub registration only, no actual promotion
```

This prevents:
- Multi-language code generation (TypeScript, JavaScript)
- Semantic pattern classification for auto-categorization
- Language-specific prompt optimization
- Accurate syntax validation for non-Python code
- Auto-learning from successful generations (Milestone 4)

### The Solution: Production-Ready Implementations

Implement all 5 modules following Strategy Pattern and cognitive architecture principles:

```
REQUIREMENTS → FILE TYPE DETECTION → LANGUAGE-SPECIFIC PROMPTS →
CODE GENERATION → LANGUAGE-SPECIFIC VALIDATION → QUALITY SCORING →
PATTERN CLASSIFICATION → AUTO-PROMOTION (≥95% success)
```

This enables:
- Multi-language support (Python, TypeScript, JavaScript, JSON, YAML)
- Semantic classification with confidence scores
- Framework-aware prompt generation (FastAPI, Next.js, React)
- Accurate syntax validation per language
- Automated pattern learning and promotion

---

## Compatibility Analysis & Critical Bug Fixes

**Analysis Date**: 2025-11-20
**Status**: ✅ All stubs compatible after fixes

### Critical Bug Fixed: Pattern Classifier Return Type

**Issue**: `pattern_classifier.py` returned `Dict[str, Any]` but `PatternBank` expected object with attributes for Qdrant/Neo4j storage.

**Impact**: CRITICAL - Would cause `AttributeError` in production when storing patterns to Qdrant

**Root Cause**:
```python
# PatternBank line 377-378 expects attribute access:
metadata = {
    "category": classification_result.category,  # ❌ Fails with dict
    "classification_confidence": classification_result.confidence
}

# But classify() returned dict:
return {'category': 'auth', 'confidence': 0.8}  # ❌ Can't access .category
```

**Fix Applied** (2025-11-20):
- Created `ClassificationResult` dataclass with all required fields
- Changed `classify()` return type: `Dict[str, Any]` → `ClassificationResult`
- Updated all 24 tests to use attribute access instead of dict keys
- Verified Qdrant/Neo4j compatibility with integration test

**Files Modified**:
- `src/cognitive/patterns/pattern_classifier.py` - Added ClassificationResult dataclass
- `tests/cognitive/patterns/test_pattern_classifier.py` - Updated to attribute access

**Validation**: ✅ 24/24 tests passing, PatternBank integration verified

### Compatibility Status by Module

| Module | Status | Issues Found | Integration Points |
|--------|--------|--------------|-------------------|
| pattern_classifier.py | ✅ Fixed | ClassificationResult dict→object | PatternBank → Qdrant/Neo4j |
| file_type_detector.py | ✅ Compatible | None | CodeGenerationService, PromptContext |
| prompt_strategies.py | ✅ Compatible | None | CodeGenerationService |
| validation_strategies.py | ⚠️ Enhancement | Python-only validation | CodeGenerationService |
| pattern_feedback_integration.py | ✅ Compatible | None | CodeGenerationService, E2E tests |

### Enhancement Opportunities Identified

**Priority 1** (Next Sprint):
1. **ValidationStrategies**: Implement TypeScript/JavaScript validators (currently Python-only)
2. **PromptStrategies**: Add language-specific strategies (currently generic)
3. **FileTypeDetector**: Add keyword-based detection beyond file extensions

**Priority 2** (Future):
1. **PatternClassifier**: Add semantic embeddings (GraphCodeBERT) beyond keywords
2. **PatternFeedbackIntegration**: Implement actual storage and promotion logic
3. **PromptStrategies**: Add framework-specific optimizations (FastAPI, React, Next.js)

**Impact**: Low for E2E testing (current stubs sufficient), Medium for production quality

### Integration Validation Results

All cross-module dependencies verified compatible:

```
CodeGenerationService
    ├─ FileTypeDetector.detect() → FileTypeDetection ✅
    │   └─ Used by: PromptContext, ValidationStrategyFactory
    ├─ PromptStrategyFactory.get_strategy() → PromptStrategy ✅
    │   └─ Methods: generate_prompt(), generate_prompt_with_feedback()
    ├─ ValidationStrategyFactory.get_strategy() → ValidationStrategy ✅
    │   └─ Method: validate() returns tuple[bool, str]
    └─ PatternFeedbackIntegration.register_successful_generation() ✅
        └─ Returns: str (candidate_id)
```

**Data Flow Integrity**: ✅ All type signatures match, no compatibility issues

### Neo4j/Qdrant Database Compatibility Analysis

**Analysis Date**: 2025-11-20
**Database Schema Source**: Direct queries to production Neo4j + Qdrant
**Status**: ⚠️ **CRITICAL INCOMPATIBILITIES CONFIRMED**

#### Database Architecture Overview

**Existing Production Data** (VERIFIED via direct database queries):
- **Neo4j**: 30,071 Pattern nodes with graph relationships
- **Qdrant devmatrix_patterns**: 21,624 patterns with 768d embeddings
- **Qdrant semantic_patterns**: 30,126 patterns (NOT empty)

**CRITICAL FINDING**: All Qdrant patterns have MINIMAL payload (only 3 fields: `description`, `file_path`, `pattern_id`). This means patterns were populated by legacy seeding scripts, NOT by PatternBank.store_pattern().

#### Critical Incompatibility 1: `complexity` Field Type Conflict

**Issue**: ClassificationResult returns incompatible `complexity` type

| Source | Type | Example Value | VERIFIED |
|--------|------|---------------|----------|
| **Neo4j Pattern.complexity** | `int` | `5` (cyclomatic complexity 1-10+) | ✅ Confirmed in production |
| **Qdrant payload** | N/A | ❌ Field NOT in payload | ✅ Confirmed - only 3 fields exist |
| **ClassificationResult.complexity** | `str` | `"O(n) - iteration"` | ✅ pattern_classifier.py:86 |

**Impact**: ❌ **TYPE MISMATCH** - Cannot store ClassificationResult.complexity (str) in Neo4j.complexity (int)

**Root Cause**:
```python
# pattern_classifier.py returns Big-O notation string:
ClassificationResult(
    complexity="O(n²) or higher - nested loops detected"  # str
)

# But Neo4j/Qdrant expect integer cyclomatic complexity:
{
    "complexity": 5  # int - existing schema
}
```

**Current State**:
- PatternBank does NOT store ClassificationResult.complexity in metadata (line 372-384)
- ✅ No runtime errors because field is not used
- ❌ **Data loss** - complexity analysis discarded

#### Critical Incompatibility 2: Missing Fields in Database Schema

**Issue**: ClassificationResult provides fields that don't exist in current databases

| Field | ClassificationResult | Neo4j (VERIFIED) | Qdrant (VERIFIED) | Status |
|-------|---------------------|------------------|-------------------|--------|
| `security_level` | str (enum) | ❌ NOT in schema | ❌ NOT in payload (only 3 fields) | Future use only |
| `performance_tier` | str (enum) | ❌ NOT in schema | ❌ NOT in payload (only 3 fields) | Future use only |
| `subcategory` | Optional[str] | ❌ NOT in schema | ❌ NOT in payload | Not used |
| `tags` | List[str] | ✅ Separate Tag nodes via [:HAS_TAG] | ❌ NOT in payload | Architecture mismatch |

**Current State**:

- PatternBank only stores `category` and `classification_confidence` (line 377-378)
- `security_level`, `performance_tier`, `complexity` are **DISCARDED**
- ✅ Compatible with existing schema (doesn't break anything)
- ❌ **Data loss** - valuable classification data not persisted

#### Compatible Field: `category` ✅

**Verification**: `category` field is fully compatible with Neo4j

| Source | Type | Example Value | VERIFIED |
|--------|------|---------------|----------|
| **ClassificationResult.category** | str | "auth", "api", "database" | ✅ pattern_classifier.py:71 |
| **Neo4j Pattern.category** | str | "utilities" (actual value) | ✅ Confirmed in production |
| **Neo4j Category node** | str | Relationship [:IN_CATEGORY] | ✅ neo4j_client.py:121 |
| **Qdrant payload** | N/A | ❌ NOT in current payload | ⚠️ Would be stored by PatternBank if used |
| **Neo4j classification_confidence** | float | 0.85 (BONUS field) | ✅ Confirmed - compatible with ClassificationResult.confidence |

**Integration Flow**:
```python
# 1. Pattern classified
result = classifier.classify(code, name, description)
result.category  # "auth"

# 2. Stored in Qdrant metadata
metadata = {"category": result.category}  # ✅ Works

# 3. Neo4j queries use category
MATCH (p:Pattern)-[:IN_CATEGORY]->(c:Category {name: $category})  # ✅ Works
```

#### Architectural Decision Required

**Options for `complexity` Field**:

##### Option A: Separate complexity fields (RECOMMENDED)

```python
@dataclass
class ClassificationResult:
    # ... existing fields ...
    cyclomatic_complexity: Optional[int] = None  # For Neo4j/Qdrant (1-10+)
    algorithmic_complexity: str = "O(1)"         # Big-O analysis (for docs/learning)
```

##### Option B: Keep current (discard complexity)

- Continue not storing complexity in PatternBank
- ClassificationResult.complexity only used for logging/debugging
- Accept data loss as acceptable trade-off

##### Option C: Unified field with conversion

```python
def store_pattern(...):
    # Convert Big-O string to cyclomatic int estimate
    complexity_map = {"O(1)": 1, "O(n)": 5, "O(n²)": 10}
    complexity_int = complexity_map.get(result.complexity[:4], 5)
```

**Options for `security_level` and `performance_tier`**:

##### Option A: Store in semantic_patterns only (RECOMMENDED)

- Use existing `devmatrix_patterns` unchanged (21,624 patterns)
- Store new ClassificationResult data in `semantic_patterns` collection
- Align with planned schema (PATTERN_SCHEMA.md:345-346)

##### Option B: Extend existing schema

- Add `security_level` and `performance_tier` to all Pattern nodes
- Migrate 30,071 Neo4j patterns + 21,624 Qdrant patterns
- High cost, disrupts existing data

##### Option C: Metadata-only storage

- Store additional fields in Qdrant payload only (not Neo4j)
- Accept schema divergence between databases

#### Recommendations

1. **IMMEDIATE** (This Sprint):
   - ✅ Keep `complexity` as-is (Big-O string, not stored in DB)
   - ✅ Store only `category` + `confidence` in PatternBank (current behavior)
   - ✅ Document that `security_level`, `performance_tier` are for future use

2. **SHORT-TERM** (Next Sprint):
   - Update PatternBank to store patterns in `semantic_patterns` collection
   - Use full ClassificationResult schema for new patterns
   - Maintain backward compatibility with `devmatrix_patterns`

3. **LONG-TERM** (Future):
   - Consider adding `cyclomatic_complexity: Optional[int]` field
   - Implement complexity analysis for metric-driven pattern selection

#### Testing Verification

**Current Compatibility**: ✅ VERIFIED
- ClassificationResult fields NOT breaking existing system
- PatternBank selectively uses compatible fields only
- Neo4j queries work with existing Pattern schema
- Qdrant searches compatible with current payload structure

**Risk Level**: 🟡 MEDIUM
- No runtime errors (fields not used = safe)
- Data loss acceptable for MVP (complexity analysis optional)
- Future migration path clear (semantic_patterns ready)

---

## User Stories

- As a developer, I want code generated with language-specific best practices so that output quality matches framework conventions
- As a system admin, I want patterns auto-classified by domain so that pattern bank organization is automated
- As a developer, I want validation to catch syntax errors specific to TypeScript/JavaScript so that generated code compiles correctly
- As a ML engineer, I want successful patterns automatically promoted so that the system learns from each success
- As a developer, I want framework-specific prompts (FastAPI, Next.js) so that generated code follows framework idioms

## Core Requirements

### Pattern Classifier (Auto-Categorization)
- Domain classification using keyword analysis + semantic embeddings
- Security level inference (public, internal, sensitive, critical)
- Performance tier inference (light, medium, heavy, critical)
- Confidence scoring (0.0-1.0) for all classifications
- Multi-label classification support

### File Type Detector (Language/Framework Detection)
- Keyword-based language detection from task descriptions
- Framework detection (FastAPI→Python, Next.js→TypeScript, React→JavaScript)
- File extension inference (.py, .ts, .tsx, .js, .jsx, .json, .yaml)
- Import statement analysis for existing code
- Confidence scoring with reasoning explanation

### Prompt Strategies (Language-Specific Generation)
- Strategy Pattern with base interface + concrete strategies
- PythonPromptStrategy: Type hints, docstrings, Pydantic models, 'code.' imports
- TypeScriptPromptStrategy: Type definitions, interfaces, strict mode
- JavaScriptPromptStrategy: ESLint rules, React patterns, async/await
- ConfigPromptStrategy: JSON Schema validation, YAML syntax
- Feedback loop integration with error patterns and successful patterns

### Validation Strategies (Syntax Validation)
- Strategy Pattern with base interface + concrete strategies
- PythonValidationStrategy: AST parsing, import validation, type hint checking, mypy integration
- TypeScriptValidationStrategy: tsc compilation, type error detection
- JavaScriptValidationStrategy: ESLint integration, JSX syntax validation
- JSONValidationStrategy: JSON.parse + schema validation
- YAMLValidationStrategy: Syntax validation + schema compliance

### Pattern Feedback Integration (Auto-Learning Pipeline)
- Storage layer for successful generations (code + signature + metadata)
- Quality evaluation: complexity analysis, test coverage, security checks
- Similarity detection to prevent duplicates
- Auto-promotion criteria: quality > 0.8, execution success, non-duplicate
- DAG Synchronizer integration for execution metrics
- Pattern lineage tracking in Neo4j
- Dual validation (Claude + GPT-4) for pattern quality

## Visual Design

No UI components - backend services only.

## Reusable Components

### Existing Code to Leverage

**Pattern Bank Integration**:
- `src/cognitive/patterns/pattern_bank.py`: Provides `store_pattern()`, `search_patterns()`, `PatternClassifier` interface
- Qdrant integration already implemented (21,624+ existing patterns)
- Embedding generation with Sentence Transformers

**Semantic Signature System**:
- `src/cognitive/signatures/semantic_signature.py`: Provides `SemanticTaskSignature`, `compute_semantic_hash()`
- Purpose normalization, intent extraction, I/O type inference

**Code Generation Service**:
- `src/services/code_generation_service.py`: Consumer of all 5 stub modules
- Implements retry logic, error pattern tracking, success registration

**DAG Synchronizer** (Milestone 3):
- `src/cognitive/services/dag_synchronizer.py`: Execution metrics tracking
- Neo4j integration for pattern relationships

**Error Pattern Store**:
- `src/services/error_pattern_store.py`: Legacy feedback loop infrastructure
- `ErrorPattern`, `SuccessPattern` dataclasses

### New Components Required

**GraphCodeBERT Integration** (pattern_classifier):
- Semantic code embeddings for classification
- Not present in codebase - need to add transformers dependency

**AST Parsing Utilities** (validation_strategies):
- Python: Use built-in `ast` module
- JavaScript/TypeScript: Need to integrate esprima or similar parser

**External Validators** (validation_strategies):
- TypeScript: Shell execution of `tsc --noEmit`
- ESLint: Shell execution of `eslint`
- mypy: Shell execution of `mypy` for Python type checking

**Quality Scoring Algorithm** (pattern_feedback_integration):
- Complexity metrics (McCabe, Halstead)
- Test coverage integration
- Security pattern detection
- New algorithm needed - not present in codebase

**Dual Validation System** (pattern_feedback_integration):
- Coordinate Claude + GPT-4 for pattern quality validation
- Voting/consensus mechanism
- New component - not present in Task Group 6.3 implementation

## Technical Approach

### Architecture Pattern: Strategy Pattern

All modules except `pattern_classifier` use Strategy Pattern for extensibility:

```python
# Base Strategy Interface
class PromptStrategy(ABC):
    @abstractmethod
    def generate_prompt(self, context: PromptContext) -> str:
        pass

# Concrete Strategies
class PythonPromptStrategy(PromptStrategy):
    def generate_prompt(self, context: PromptContext) -> str:
        # Language-specific implementation
        pass

# Factory Pattern
class PromptStrategyFactory:
    @staticmethod
    def get_strategy(file_type: FileType) -> PromptStrategy:
        return _strategies[file_type]
```

### Classification Approach: Hybrid (Keywords + ML)

pattern_classifier.py uses tiered classification:

1. **Keyword Analysis** (fast, 0.7-0.8 confidence): Pattern matching on code/purpose
2. **Semantic Embeddings** (slower, 0.8-0.95 confidence): GraphCodeBERT embeddings + cosine similarity
3. **Ensemble** (best accuracy): Combine both methods with weighted voting

### Validation Approach: Parser-Based + External Tools

validation_strategies.py uses native parsers + external linters:

1. **Python**: `ast.parse()` for syntax, AST walk for type hints, mypy for advanced checking
2. **TypeScript**: Shell execution of `tsc --noEmit` for compilation validation
3. **JavaScript**: esprima for parsing, ESLint for style/error checking
4. **JSON/YAML**: Native parsers + optional JSON Schema validation

### Pattern Promotion Pipeline (Milestone 4)

pattern_feedback_integration.py implements:

1. **Storage Queue**: Async queue for generation candidates
2. **Quality Evaluation**: Multi-factor scoring (complexity, coverage, security)
3. **Similarity Detection**: Qdrant search to prevent duplicates
4. **Auto-Promotion**: Automatic promotion when quality ≥ 0.8, execution success, non-duplicate
5. **DAG Sync**: Update Neo4j with execution metrics
6. **Dual Validation**: Claude + GPT-4 consensus for pattern quality (Task 6.3.1)

### Integration with CodeGenerationService

All modules integrate into existing code generation flow:

```python
# CodeGenerationService.generate_code()
file_detection = file_type_detector.detect(task_name, task_description, target_files)
prompt_strategy = PromptStrategyFactory.get_strategy(file_detection.file_type)
prompt = prompt_strategy.generate_prompt_with_feedback(context)
code = llm_client.generate(prompt)
validation_strategy = ValidationStrategyFactory.get_strategy(file_detection.file_type)
is_valid, error = validation_strategy.validate(code)

if is_valid and execution_success:
    signature = SemanticTaskSignature.extract_from_task(task)
    category = pattern_classifier.classify(code, task_name, task_description)
    pattern_feedback.register_successful_generation(code, signature, execution_result, metadata)
```

### Dependencies

**Python Packages**:
- `transformers`: GraphCodeBERT for semantic embeddings
- `sentence-transformers`: Pattern Bank embeddings (already present)
- `esprima` or `pyjsparser`: JavaScript AST parsing
- External tools: `tsc` (TypeScript compiler), `eslint`, `mypy`

**Database**:
- Qdrant: Pattern storage (already running, ports 6333/6334)
- Neo4j: Pattern lineage tracking (already running, ports 7474/7687)
- PostgreSQL: Metadata storage (already running, port 5432)

**LLM APIs**:
- Claude Sonnet 4: Strategic reasoning (already configured)
- GPT-4: Dual validation (need API key configuration)
- DeepSeek: Code generation (already configured)

## Out of Scope

### Not in This Spec
- Support for additional languages beyond Python/TypeScript/JavaScript (Go, Rust, Java)
- Machine learning model training for classification (use pre-trained GraphCodeBERT)
- Custom ESLint/TSConfig rule creation
- Web UI for pattern management
- Real-time pattern recommendation API

### Future Enhancements
- Rust/Go/Java validation strategies
- Custom ML model fine-tuning on domain-specific code
- Interactive pattern refinement workflow
- A/B testing framework for prompt strategies
- Automatic framework version detection

## Success Criteria

### Functional Requirements (Must Have)
- All 5 modules implement complete production logic (no stubs)
- Pattern classifier achieves ≥85% domain classification accuracy
- File type detector achieves ≥90% language detection accuracy
- Validation strategies achieve 100% syntax error detection
- Pattern promotion pipeline stores patterns with ≥95% success rate

### Quality Requirements (Must Have)
- Test coverage ≥90% for all modules
- All tests passing (100% pass rate)
- Integration tests with CodeGenerationService
- Type hints on all public APIs
- Docstrings with examples for all public methods

### Performance Requirements (Must Have)
- Pattern classification: <500ms per task
- File type detection: <100ms per task
- Validation: <2s per code generation
- Pattern promotion: Async, non-blocking

### Integration Requirements (Must Have)
- CodeGenerationService integration verified
- Pattern Bank storage working
- DAG Synchronizer metrics tracking
- Error pattern feedback loop functional

### Documentation Requirements (Must Have)
- Inline docstrings with examples
- README with usage examples
- Architecture decision records for key choices

## Implementation Roadmap

### Priority P0 - Critical (14.5 hours)

**Week 1: Foundation**

**pattern_classifier.py** (6.5h):
- STUB-1.1: Keyword-based domain classification (2h)
- STUB-1.2: Security level inference (1.5h)
- STUB-1.3: Performance tier inference (1h)
- STUB-1.4: Unit tests ≥90% coverage (2h)

**file_type_detector.py** (8h):
- STUB-2.1: Language detection from keywords (2.5h)
- STUB-2.2: File extension inference (1h)
- STUB-2.3: Framework detection (2h)
- STUB-2.4: Unit tests ≥90% coverage (2.5h)

### Priority P1 - Important (37 hours)

**Week 2-3: Language-Specific Strategies**

**prompt_strategies.py** (15h):
- STUB-3.1: Base PromptStrategy interface (1.5h)
- STUB-3.2: PythonPromptStrategy (3h)
- STUB-3.3: TypeScriptPromptStrategy (3h)
- STUB-3.4: JavaScriptPromptStrategy (2.5h)
- STUB-3.5: Strategy selector factory (2h)
- STUB-3.6: Unit tests ≥90% coverage (3h)

**validation_strategies.py** (22h):
- STUB-4.1: Base ValidationStrategy interface (2h)
- STUB-4.2: PythonValidationStrategy with AST (4h)
- STUB-4.3: TypeScriptValidationStrategy with tsc (4.5h)
- STUB-4.4: JavaScriptValidationStrategy with ESLint (4h)
- STUB-4.5: JSON/YAML validation strategies (1.5h)
- STUB-4.6: Integration with EnsembleValidator (2h)
- STUB-4.7: Unit tests ≥90% coverage (4h)

### Priority P2 - Milestone 4 (20 hours)

**Week 4: Auto-Learning Pipeline**

**pattern_feedback_integration.py** (20h):
- STUB-5.1: Quality evaluation pipeline (3h)
- STUB-5.2: Promotion workflow with criteria (4h)
- STUB-5.3: Pattern lineage tracking in Neo4j (3h)
- STUB-5.4: Orchestrator integration (2h)
- Task 6.3.1: Dual-validator (Claude + GPT-4) (2h) - EXPLICIT TASK
- Task 6.3.2: Adaptive thresholds by domain (1.5h) - EXPLICIT TASK
- Task 6.3.3: Pattern evolution tracking (1.5h) - EXPLICIT TASK
- STUB-5.5: Unit tests ≥90% coverage (3h)

### Validation Gates

**After P0** (Day 3):
- File type detection working with 3 languages
- Pattern classification with confidence scores
- Integration tests with CodeGenerationService passing

**After P1** (Day 8):
- All language strategies implemented
- Validation working for Python/TypeScript/JavaScript
- Feedback loop collecting error patterns

**After P2** (Day 11):
- Pattern promotion working with real patterns
- DAG Synchronizer metrics tracking active
- Dual validation consensus functional
- Complete E2E test passing (spec → code → validation → promotion)

## Task Breakdown

### Module 1: pattern_classifier.py (6.5h)

**STUB-1.1: Domain Classification** (2h)
- Implement keyword matching for domains: auth, crud, api, validation, data_transform, business_logic
- Add pattern matching rules for common code structures
- Return domain with confidence score (0.7-0.8 for keywords)
- Integration with SemanticTaskSignature

**STUB-1.2: Security Level Inference** (1.5h)
- Analyze code for security patterns (auth, encryption, validation)
- Classify as LOW, MEDIUM, HIGH, CRITICAL
- Consider domain + purpose + code content
- Confidence scoring based on pattern matches

**STUB-1.3: Performance Tier Inference** (1h)
- Analyze code complexity (async operations, database queries, loops)
- Classify as LOW, MEDIUM, HIGH
- Consider computational complexity indicators
- Return tier with reasoning

**STUB-1.4: Unit Tests** (2h)
- Test all classification methods
- Test edge cases (empty code, ambiguous domains)
- Test confidence scoring accuracy
- Target ≥90% coverage

### Module 2: file_type_detector.py (8h)

**STUB-2.1: Language Detection** (2.5h)
- Keyword analysis in task_name and task_description
- Mapping keywords to languages (FastAPI→Python, React→JavaScript/TypeScript)
- Confidence scoring based on keyword matches
- Fallback to Python with low confidence

**STUB-2.2: File Extension Inference** (1h)
- Map language to appropriate extensions
- Handle special cases (TypeScript: .ts vs .tsx, JavaScript: .js vs .jsx)
- Consider task context (API vs component)
- Return extension with reasoning

**STUB-2.3: Framework Detection** (2h)
- Detect frameworks from keywords: FastAPI, Next.js, React, Express, Flask
- Map frameworks to languages and conventions
- Influence prompt generation and validation
- Return framework with confidence

**STUB-2.4: Unit Tests** (2.5h)
- Test language detection accuracy
- Test extension inference logic
- Test framework detection
- Test confidence scoring
- Target ≥90% coverage

### Module 3: prompt_strategies.py (15h)

**STUB-3.1: Base Interface** (1.5h)
- Define PromptStrategy abstract base class
- Define PromptContext dataclass
- Define standard methods: generate_prompt(), generate_prompt_with_feedback()
- Document contract and expectations

**STUB-3.2: PythonPromptStrategy** (3h)
- Implement Python-specific prompt generation
- Emphasize: type hints, docstrings, Pydantic models, 'code.' import prefix
- Include best practices: FastAPI patterns, async/await, error handling
- Add feedback loop integration with error patterns

**STUB-3.3: TypeScriptPromptStrategy** (3h)
- Implement TypeScript-specific prompts
- Emphasize: type definitions, interfaces, strict mode, Next.js patterns
- Include React component patterns, hooks, async/await
- Error pattern integration

**STUB-3.4: JavaScriptPromptStrategy** (2.5h)
- Implement JavaScript-specific prompts
- Emphasize: ESLint rules, JSDoc, modern ES6+ syntax
- React patterns without TypeScript
- Async/await best practices

**STUB-3.5: Strategy Factory** (2h)
- Implement PromptStrategyFactory.get_strategy()
- Map FileType enum to concrete strategies
- Handle ConfigPromptStrategy for JSON/YAML
- Default fallback strategy

**STUB-3.6: Unit Tests** (3h)
- Test each strategy independently
- Test prompt quality and completeness
- Test feedback loop integration
- Test factory pattern
- Target ≥90% coverage

### Module 4: validation_strategies.py (22h)

**STUB-4.1: Base Interface** (2h)
- Define ValidationStrategy abstract base class
- Define standard methods: validate_syntax(), validate_type_hints(), validate_loc()
- Return tuple (is_valid: bool, error_message: Optional[str])
- Document validation contract

**STUB-4.2: PythonValidationStrategy** (4h)
- AST parsing with ast.parse() for syntax validation
- AST walk for type hint verification
- Import statement validation ('code.' prefix requirement)
- LOC counting (≤10 constraint)
- Optional mypy integration for advanced type checking

**STUB-4.3: TypeScriptValidationStrategy** (4.5h)
- Shell execution of tsc --noEmit for compilation
- Parse TypeScript compiler errors
- Validate type definitions presence
- LOC counting
- Handle .ts vs .tsx differences

**STUB-4.4: JavaScriptValidationStrategy** (4h)
- ESLint integration via shell execution
- Parse ESLint output for errors
- JSX syntax validation for .jsx files
- LOC counting
- Error categorization (syntax vs style)

**STUB-4.5: JSON/YAML Strategies** (1.5h)
- JSONValidationStrategy: json.parse() + optional JSON Schema
- YAMLValidationStrategy: yaml.safe_load() + optional schema
- Clear error messages for malformed files

**STUB-4.6: EnsembleValidator Integration** (2h)
- Integrate validation strategies into existing EnsembleValidator
- Ensure strategy selection based on file type
- Test integration with CodeGenerationService
- Verify error reporting pipeline

**STUB-4.7: Unit Tests** (4h)
- Test each validation strategy
- Test edge cases (syntax errors, missing types, LOC violations)
- Test error message clarity
- Test integration with CodeGenerationService
- Target ≥90% coverage

### Module 5: pattern_feedback_integration.py (20h)

**STUB-5.1: Quality Evaluation** (3h)
- Implement quality scoring algorithm
- Metrics: complexity (McCabe), test coverage, security patterns
- Confidence scoring (0.0-1.0)
- Threshold: ≥0.8 for promotion

**STUB-5.2: Promotion Workflow** (4h)
- Implement auto-promotion pipeline
- Criteria: quality > 0.8, execution success, non-duplicate
- Qdrant similarity search for duplicate detection
- Storage to Pattern Bank with metadata
- Success notification/logging

**STUB-5.3: Pattern Lineage Tracking** (3h)
- Neo4j integration for pattern relationships
- Track: parent patterns, derived patterns, evolution history
- Cypher queries for lineage traversal
- Visualization data preparation

**STUB-5.4: Orchestrator Integration** (2h)
- Integrate with OrchestratorMVP
- Execution metrics collection
- Success/failure tracking
- Async pattern promotion queue

**Task 6.3.1: Dual Validator** (2h) - EXPLICIT TASK
- Implement Claude + GPT-4 dual validation
- Voting/consensus mechanism
- Quality score aggregation
- Fallback to single validator on API failure

**Task 6.3.2: Adaptive Thresholds** (1.5h) - EXPLICIT TASK
- Domain-specific quality thresholds
- Metrics: success rate per domain, average quality per domain
- Dynamic threshold adjustment based on performance
- Configuration management

**Task 6.3.3: Pattern Evolution** (1.5h) - EXPLICIT TASK
- Track pattern usage over time
- Version history in Neo4j
- Performance metrics per version
- Automatic deprecation of low-performing patterns

**STUB-5.5: Unit Tests** (3h)
- Test quality evaluation algorithm
- Test promotion criteria
- Test dual validation
- Test adaptive thresholds
- Test pattern evolution tracking
- Target ≥90% coverage

## Testing Strategy

### Unit Tests (Per Module)
- Test all public methods
- Test edge cases and error conditions
- Mock external dependencies (Qdrant, Neo4j, LLM APIs)
- Target ≥90% coverage per module

### Integration Tests
- CodeGenerationService → file_type_detector → prompt_strategies → validation_strategies
- pattern_classifier → Pattern Bank storage
- pattern_feedback_integration → DAG Synchronizer → Neo4j

### E2E Tests
- Full pipeline: spec → file detection → code generation → validation → promotion
- Multi-language scenarios (Python, TypeScript, JavaScript)
- Error recovery and retry scenarios
- Pattern reuse verification

### Performance Tests
- Classification: <500ms per task
- File detection: <100ms per task
- Validation: <2s per code generation
- Pattern search: <300ms for Qdrant lookup

## Metrics & Success Indicators

### Code Quality Metrics
- Test coverage: ≥90% per module
- Type hint coverage: 100% on public APIs
- Linting: Zero errors (flake8, mypy)
- Complexity: McCabe complexity <10 per function

### Functional Metrics
- Pattern classification accuracy: ≥85%
- File type detection accuracy: ≥90%
- Validation accuracy: 100% syntax error detection
- Pattern promotion rate: 30-50% of successful generations

### Performance Metrics
- E2E code generation latency: <10s per task
- Pattern search latency: <300ms
- Validation latency: <2s per code artifact
- System throughput: ≥10 tasks/minute

### Business Metrics
- Pattern reuse rate: ≥30% (baseline: 21K+ existing patterns)
- Code generation success rate: ≥95%
- Multi-language support: 3 languages (Python, TypeScript, JavaScript)
- Auto-learning rate: ≥1 new pattern per 10 successful generations

## Risk Mitigation

### Technical Risks

**Risk**: External tools (tsc, ESLint, mypy) not available in deployment
**Mitigation**: Graceful degradation to syntax-only validation, documentation requirements

**Risk**: GraphCodeBERT model too large for deployment
**Mitigation**: Use lighter sentence-transformers model, adjust embedding dimension

**Risk**: GPT-4 API rate limits in dual validation
**Mitigation**: Fallback to Claude-only validation, implement retry with backoff

**Risk**: Qdrant performance degradation with pattern growth
**Mitigation**: Implement collection sharding, regular optimization, archival strategy

### Timeline Risks

**Risk**: External tool integration takes longer than estimated
**Mitigation**: Implement native parsers first, add external tools as enhancement

**Risk**: Pattern promotion complexity underestimated
**Mitigation**: Implement basic promotion first, add dual validation as P2 enhancement

**Risk**: Testing effort exceeds estimates
**Mitigation**: Prioritize critical path tests, use mocking aggressively

## Dependencies

### External Systems
- Qdrant (vector DB): Already running, ports 6333/6334
- Neo4j (graph DB): Already running, ports 7474/7687
- PostgreSQL: Already running, port 5432
- Redis: Already running, port 6379

### External APIs
- Claude Sonnet 4: Already configured
- GPT-4: Need API key configuration (for dual validation)
- DeepSeek: Already configured

### Python Packages (New)
- `transformers`: GraphCodeBERT embeddings
- `esprima` or `pyjsparser`: JavaScript parsing
- External tools: `tsc`, `eslint`, `mypy` (optional)

### Internal Dependencies
- `src/cognitive/patterns/pattern_bank.py`: Pattern storage
- `src/cognitive/signatures/semantic_signature.py`: Signature extraction
- `src/services/code_generation_service.py`: Consumer of all modules
- `src/cognitive/services/dag_synchronizer.py`: Execution metrics
- `src/services/error_pattern_store.py`: Legacy feedback loop

## Acceptance Criteria

### P0 Completion (Day 3)
- [ ] Pattern classifier classifies domains with ≥85% accuracy
- [ ] File type detector detects 3 languages with ≥90% accuracy
- [ ] All P0 tests passing with ≥90% coverage
- [ ] CodeGenerationService integration verified

### P1 Completion (Day 8)
- [ ] All 4 prompt strategies implemented (Python, TypeScript, JavaScript, Config)
- [ ] All 5 validation strategies implemented (Python, TypeScript, JavaScript, JSON, YAML)
- [ ] Validation catches 100% of syntax errors in test suite
- [ ] All P1 tests passing with ≥90% coverage

### P2 Completion (Day 11)
- [ ] Pattern promotion pipeline auto-promotes patterns with quality ≥0.8
- [ ] Dual validation (Claude + GPT-4) consensus working
- [ ] Adaptive thresholds adjust per domain
- [ ] Pattern evolution tracked in Neo4j
- [ ] All P2 tests passing with ≥90% coverage
- [ ] Complete E2E test passing (spec → code → validation → promotion)

### Production Readiness
- [ ] All tests passing (100% pass rate)
- [ ] Performance benchmarks met (<500ms classification, <100ms detection, <2s validation)
- [ ] Documentation complete (docstrings + README + examples)
- [ ] No stub implementations remaining
- [ ] Integration with CodeGenerationService verified in production-like environment

---

**Total Effort**: 71.5 hours (~9 days)
**Priority Breakdown**: P0 (14.5h) → P1 (37h) → P2 (20h)
**Expected Completion**: Day 11 from start
**Milestone 4 Dependency**: Task Group 6.3 (Phase 2 Week 6) requires pattern_feedback_integration completion
