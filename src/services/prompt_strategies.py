"""
Prompt Strategy Pattern - Language-specific prompt generation with feedback integration.

Production implementation with FastAPI, Pytest, React, Express, Next.js, TypeScript,
and config file strategies. Integrates with PatternBank for successful pattern examples
and error history for feedback-driven improvement.

Spec Reference: Task Group 3 - Prompt Strategies Implementation
Target Coverage: >90% (TDD approach)
"""

from dataclasses import dataclass
from typing import Optional, List, Any, Dict
from abc import ABC, abstractmethod
import re

from src.services.file_type_detector import (
    FileType,
    FileTypeDetection,
    Framework,
)


@dataclass
class PromptContext:
    """
    Context for prompt generation with comprehensive metadata.

    Contains all information needed to generate optimized prompts:
    - Task details (number, name, description)
    - Complexity assessment
    - File type and framework detection
    - Error feedback (last error + similar errors)
    - Successful patterns for reference
    """
    task_number: int
    task_name: str
    task_description: str
    complexity: str
    file_type_detection: FileTypeDetection
    last_error: Optional[str] = None
    similar_errors: Optional[List[Any]] = None
    successful_patterns: Optional[List[Any]] = None


@dataclass
class GeneratedPrompt:
    """
    Generated prompt with metadata for tracking and optimization.

    Includes prompt text plus metadata about what influenced generation:
    - Base strategy used
    - Pattern examples included
    - Error feedback injected
    - Framework-specific guidance applied
    """
    prompt: str
    strategy_name: str
    pattern_count: int = 0
    error_feedback_included: bool = False
    framework_specific: bool = False


class PromptStrategy(ABC):
    """
    Base strategy for language-specific prompt generation.

    **Design Pattern**: Strategy Pattern for file-type-specific prompts

    **Subclass Responsibilities**:
    - Implement _get_language_guidelines() with best practices
    - Implement _get_framework_specifics() with framework patterns
    - Implement _get_testing_requirements() with test expectations
    - Optionally override _format_pattern_example() for language-specific formatting

    **Shared Functionality**:
    - Error feedback enrichment
    - Similar error retrieval
    - Successful pattern integration
    - Prompt composition and formatting
    """

    def __init__(self) -> None:
        """Initialize base prompt strategy."""
        self.strategy_name = self.__class__.__name__

    def generate_prompt(self, context: PromptContext) -> GeneratedPrompt:
        """
        Generate optimized prompt for task.

        Args:
            context: Prompt context with task details

        Returns:
            GeneratedPrompt with optimized prompt text and metadata

        Example:
            >>> strategy = PythonPromptStrategy()
            >>> result = strategy.generate_prompt(context)
            >>> assert "FastAPI" in result.prompt
            >>> assert result.framework_specific == True
        """
        prompt_parts = []

        # Header
        prompt_parts.append(self._generate_header(context))

        # Language-specific guidelines
        prompt_parts.append(self._get_language_guidelines())

        # Framework-specific guidance
        frameworks = context.file_type_detection.frameworks or []
        if frameworks:
            prompt_parts.append(self._get_framework_specifics(frameworks))

        # Testing requirements
        prompt_parts.append(self._get_testing_requirements())

        # Task description
        prompt_parts.append(self._generate_task_section(context))

        prompt_text = "\n\n".join(prompt_parts)

        return GeneratedPrompt(
            prompt=prompt_text,
            strategy_name=self.strategy_name,
            framework_specific=len(frameworks) > 0
        )

    def generate_prompt_with_feedback(
        self, context: PromptContext
    ) -> GeneratedPrompt:
        """
        Generate prompt enriched with error feedback and successful patterns.

        **Enhancement Strategy**:
        1. Inject error feedback at top (critical context)
        2. Include similar errors with solutions (learning from past)
        3. Add successful patterns as reference examples (quality boost)
        4. Apply base prompt generation

        Args:
            context: Prompt context with feedback data

        Returns:
            GeneratedPrompt with enriched prompt text

        Example:
            >>> strategy = PythonPromptStrategy()
            >>> context.last_error = "TypeError: missing 1 required positional argument"
            >>> result = strategy.generate_prompt_with_feedback(context)
            >>> assert "PREVIOUS ATTEMPT FAILED" in result.prompt
            >>> assert result.error_feedback_included == True
        """
        prompt_parts = []
        pattern_count = 0
        error_feedback = False

        # 1. Error feedback enrichment (if available)
        if context.last_error:
            enriched_error = self._enrich_error_feedback(context.last_error)
            prompt_parts.append(f"## PREVIOUS ATTEMPT FAILED\n\n{enriched_error}")
            error_feedback = True

        # 2. Similar errors with solutions (if available)
        if context.similar_errors:
            similar_section = self._format_similar_errors(
                context.similar_errors[:3]
            )
            prompt_parts.append(similar_section)
            error_feedback = True

        # 3. Successful patterns as reference (if available)
        if context.successful_patterns:
            patterns_section = self._format_successful_patterns(
                context.successful_patterns[:3]
            )
            prompt_parts.append(patterns_section)
            pattern_count = min(len(context.successful_patterns), 3)

        # 4. Base prompt
        base_prompt = self.generate_prompt(context)
        prompt_parts.append(base_prompt.prompt)

        # Combine all sections
        enriched_prompt = "\n\n---\n\n".join(prompt_parts)

        return GeneratedPrompt(
            prompt=enriched_prompt,
            strategy_name=self.strategy_name,
            pattern_count=pattern_count,
            error_feedback_included=error_feedback,
            framework_specific=base_prompt.framework_specific
        )

    def _generate_header(self, context: PromptContext) -> str:
        """Generate task header with metadata."""
        return f"""# Task {context.task_number}: {context.task_name}

**File Type**: {context.file_type_detection.file_type.value}
**Complexity**: {context.complexity}
**Confidence**: {context.file_type_detection.confidence:.0%}"""

    def _generate_task_section(self, context: PromptContext) -> str:
        """Generate task description section."""
        return f"""## Task Requirements

{context.task_description}

Generate complete, production-ready code following all guidelines above."""

    def _enrich_error_feedback(self, error_message: str) -> str:
        """
        Parse and enrich error message for prompt injection.

        Extracts:
        - Error type (e.g., TypeError, SyntaxError)
        - Error location (file, line number)
        - Error context (surrounding information)

        Args:
            error_message: Raw error message

        Returns:
            Enriched error feedback with key information highlighted
        """
        # Extract error type
        error_type_match = re.search(
            r'((?:Syntax|Type|Value|Attribute|Import|Runtime|Assertion)Error)',
            error_message
        )
        error_type = error_type_match.group(1) if error_type_match else "Error"

        # Extract location (file:line)
        location_match = re.search(r'File "([^"]+)", line (\d+)', error_message)
        location = ""
        if location_match:
            file_path, line_num = location_match.groups()
            location = f"\n**Location**: {file_path}:{line_num}"

        # Extract context (the actual error message)
        context_lines = error_message.split('\n')
        # Take last 3 lines (usually most relevant)
        context = '\n'.join(context_lines[-3:]).strip()

        return f"""**Error Type**: {error_type}{location}

**Error Message**:
```
{context}
```

**Required Fix**: Address this error in your implementation."""

    def _format_similar_errors(self, similar_errors: List[Any]) -> str:
        """
        Format similar errors with successful fixes.

        Args:
            similar_errors: List of similar error records

        Returns:
            Formatted section with errors and solutions
        """
        lines = ["## Similar Errors (Learn from Past Fixes)", ""]

        for i, error in enumerate(similar_errors, 1):
            error_msg = getattr(error, 'error_message', str(error))
            solution = getattr(error, 'successful_fix', 'N/A')

            lines.append(f"### Similar Error {i}")
            lines.append(f"```\n{error_msg}\n```")
            if solution != 'N/A':
                lines.append(f"**Solution**: {solution}")
            lines.append("")

        return "\n".join(lines)

    def _format_successful_patterns(
        self, successful_patterns: List[Any]
    ) -> str:
        """
        Format successful patterns as reference examples.

        Args:
            successful_patterns: List of successful pattern records

        Returns:
            Formatted section with pattern examples
        """
        lines = ["## Successful Patterns (Reference Examples)", ""]

        for i, pattern in enumerate(successful_patterns, 1):
            lines.append(self._format_pattern_example(pattern, i))
            lines.append("")

        return "\n".join(lines)

    def _format_pattern_example(self, pattern: Any, index: int) -> str:
        """
        Format single pattern example.

        Can be overridden by subclasses for language-specific formatting.

        Args:
            pattern: Pattern record
            index: Pattern number (1, 2, 3)

        Returns:
            Formatted pattern example
        """
        # Handle both dict and object patterns
        if isinstance(pattern, dict):
            description = pattern.get('task_description', 'N/A')
            code = pattern.get('generated_code', '')
        else:
            description = getattr(pattern, 'task_description', 'N/A')
            code = getattr(pattern, 'generated_code', '')

        return f"""### Reference Pattern {index}
**Task**: {description}

**Code Example**:
```
{code[:500]}{'...' if len(code) > 500 else ''}
```"""

    @abstractmethod
    def _get_language_guidelines(self) -> str:
        """Get language-specific best practices and guidelines."""
        pass

    @abstractmethod
    def _get_framework_specifics(
        self, frameworks: List['FrameworkDetection']
    ) -> str:
        """Get framework-specific guidance and patterns."""
        pass

    @abstractmethod
    def _get_testing_requirements(self) -> str:
        """Get language-specific testing requirements."""
        pass


class PythonPromptStrategy(PromptStrategy):
    """
    Python-specific prompt strategy with FastAPI and Pytest integration.

    **Best Practices**:
    - Type hints everywhere (PEP 484)
    - Docstrings (Google style)
    - PEP 8 compliance
    - Async/await for I/O operations
    - Comprehensive error handling

    **FastAPI Specifics**:
    - Pydantic models for request/response
    - Dependency injection with Depends()
    - HTTPException for errors
    - Async endpoints for performance

    **Pytest Requirements**:
    - >95% code coverage
    - Fixtures for setup/teardown
    - Parametrize for multiple test cases
    - Async tests for async code
    """

    def _get_language_guidelines(self) -> str:
        """Python best practices and style guide."""
        return """## Python Best Practices

**Type Hints** (PEP 484):
- All function parameters must have type hints
- All return types must be annotated
- Use `Optional[T]` for nullable types
- Use `List[T]`, `Dict[K, V]`, `Tuple[T, ...]` for collections

**Docstrings** (Google Style):
- All modules, classes, and functions must have docstrings
- Include Args, Returns, Raises sections
- Provide usage examples for complex functions

**Code Style** (PEP 8):
- 4-space indentation (no tabs)
- Max line length: 88 characters (Black formatter)
- Snake_case for functions and variables
- PascalCase for classes

**Error Handling**:
- Use specific exception types
- Always provide error context in messages
- Clean up resources in `finally` blocks
- Log errors with appropriate severity

**Async/Await**:
- Use `async def` for I/O-bound operations
- Use `await` for async calls
- Don't mix sync and async code incorrectly"""

    def _get_framework_specifics(
        self, frameworks: List['FrameworkDetection']
    ) -> str:
        """FastAPI and Pytest framework-specific guidance."""
        lines = ["## Framework-Specific Guidelines", ""]

        for fw_detection in frameworks:
            fw = fw_detection.framework

            if fw == Framework.FASTAPI:
                lines.append("""### FastAPI Best Practices

**Pydantic Models**:
```python
from pydantic import BaseModel, Field, validator

class UserCreate(BaseModel):
    email: str = Field(..., description="User email")
    username: str = Field(..., min_length=3, max_length=50)

    @validator('email')
    def validate_email(cls, v):
        # Email validation logic
        return v
```

**Dependency Injection**:
```python
from fastapi import Depends, HTTPException

async def get_current_user(token: str = Depends(oauth2_scheme)):
    # Verify token and return user
    pass

@app.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user
```

**Error Handling**:
```python
from fastapi import HTTPException, status

@app.post("/items/")
async def create_item(item: ItemCreate):
    if not item.name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Item name is required"
        )
    return item
```

**Async Endpoints**:
- Use `async def` for all endpoint handlers
- Use `await` for database queries
- Use `asyncio.gather()` for parallel operations""")

            elif fw == Framework.PYTEST:
                lines.append("""### Pytest Best Practices

**Test Structure**:
```python
import pytest
from myapp import calculate_total

def test_calculate_total_basic():
    result = calculate_total(10, 0.2)
    assert result == 12.0

@pytest.mark.parametrize("price,tax,expected", [
    (10, 0.2, 12.0),
    (100, 0.1, 110.0),
    (0, 0.5, 0.0),
])
def test_calculate_total_parametrized(price, tax, expected):
    assert calculate_total(price, tax) == expected
```

**Fixtures**:
```python
@pytest.fixture
def sample_user():
    return User(id=1, name="Test User")

def test_user_update(sample_user):
    sample_user.name = "Updated"
    assert sample_user.name == "Updated"
```

**Async Tests**:
```python
@pytest.mark.asyncio
async def test_async_endpoint():
    result = await fetch_data()
    assert result is not None
```

**Coverage Requirements**:
- Minimum 95% code coverage
- Test all edge cases
- Test error conditions
- Mock external dependencies""")

            elif fw == Framework.FLASK:
                lines.append("""### Flask Best Practices

**Route Handlers**:
```python
from flask import Flask, request, jsonify

@app.route('/api/users', methods=['GET', 'POST'])
def users():
    if request.method == 'POST':
        data = request.get_json()
        # Process data
        return jsonify(data), 201
    return jsonify(users_list)
```

**Error Handling**:
```python
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404
```""")

        return "\n\n".join(lines)

    def _get_testing_requirements(self) -> str:
        """Pytest testing requirements."""
        return """## Testing Requirements

**Test Coverage**: Minimum 95%

**Test Organization**:
- Place tests in `tests/` directory
- Mirror source structure: `src/api/users.py` → `tests/api/test_users.py`
- Use `test_` prefix for all test functions

**Test Quality**:
- Test happy path AND edge cases
- Test error conditions
- Use descriptive test names: `test_user_creation_with_valid_email()`
- One assertion per test (or related assertions)

**Mocking**:
```python
from unittest.mock import Mock, patch

@patch('myapp.external_api.fetch_data')
def test_with_mock(mock_fetch):
    mock_fetch.return_value = {'status': 'ok'}
    result = process_data()
    assert result['status'] == 'ok'
```"""


class JavaScriptPromptStrategy(PromptStrategy):
    """
    JavaScript-specific prompt strategy with React and Express integration.

    **Best Practices**:
    - ES6+ syntax (const/let, arrow functions, destructuring)
    - JSDoc for type documentation
    - Async/await over callbacks
    - Error boundaries for React

    **React Specifics**:
    - Functional components (hooks era)
    - useState/useEffect for state management
    - PropTypes or TypeScript for props
    - Error boundaries for error handling

    **Express Requirements**:
    - Middleware for request processing
    - Async/await for route handlers
    - Validation middleware
    - Centralized error handling
    """

    def _get_language_guidelines(self) -> str:
        """JavaScript best practices and style guide."""
        return """## JavaScript Best Practices (ES6+)

**Modern Syntax**:
- Use `const` for immutable bindings, `let` for mutable
- Arrow functions: `const add = (a, b) => a + b`
- Destructuring: `const { name, email } = user`
- Template literals: `` `Hello ${name}` ``
- Spread operator: `{ ...user, age: 30 }`

**JSDoc Type Documentation**:
```javascript
/**
 * Calculate total with tax
 * @param {number} price - Base price
 * @param {number} taxRate - Tax rate (0.0-1.0)
 * @returns {number} Total price with tax
 */
function calculateTotal(price, taxRate) {
    return price * (1 + taxRate);
}
```

**Async/Await**:
```javascript
async function fetchUser(id) {
    try {
        const response = await fetch(`/api/users/${id}`);
        const user = await response.json();
        return user;
    } catch (error) {
        console.error('Failed to fetch user:', error);
        throw error;
    }
}
```

**Error Handling**:
- Use try/catch for async operations
- Throw descriptive errors
- Handle promise rejections
- Validate inputs early"""

    def _get_framework_specifics(
        self, frameworks: List['FrameworkDetection']
    ) -> str:
        """React and Express framework-specific guidance."""
        lines = ["## Framework-Specific Guidelines", ""]

        for fw_detection in frameworks:
            fw = fw_detection.framework

            if fw == Framework.REACT:
                lines.append("""### React Best Practices (Hooks)

**Functional Components**:
```javascript
import React, { useState, useEffect } from 'react';

function UserProfile({ userId }) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function loadUser() {
            try {
                const data = await fetchUser(userId);
                setUser(data);
            } finally {
                setLoading(false);
            }
        }
        loadUser();
    }, [userId]);

    if (loading) return <div>Loading...</div>;
    return <div>{user.name}</div>;
}
```

**PropTypes**:
```javascript
import PropTypes from 'prop-types';

UserProfile.propTypes = {
    userId: PropTypes.number.isRequired,
    onUpdate: PropTypes.func
};
```

**Custom Hooks**:
```javascript
function useUser(userId) {
    const [user, setUser] = useState(null);

    useEffect(() => {
        fetchUser(userId).then(setUser);
    }, [userId]);

    return user;
}
```

**State Management**:
- Use useState for local state
- Use useContext for global state
- Consider Redux for complex state
- Minimize state, derive when possible""")

            elif fw == Framework.EXPRESS:
                lines.append("""### Express Best Practices

**Route Handlers**:
```javascript
const express = require('express');
const router = express.Router();

router.get('/users/:id', async (req, res, next) => {
    try {
        const user = await User.findById(req.params.id);
        if (!user) {
            return res.status(404).json({ error: 'User not found' });
        }
        res.json(user);
    } catch (error) {
        next(error);
    }
});
```

**Middleware**:
```javascript
function validateUser(req, res, next) {
    const { email, username } = req.body;
    if (!email || !username) {
        return res.status(400).json({
            error: 'Email and username required'
        });
    }
    next();
}

router.post('/users', validateUser, async (req, res, next) => {
    // Handler logic
});
```

**Error Handling**:
```javascript
app.use((err, req, res, next) => {
    console.error(err.stack);
    res.status(err.status || 500).json({
        error: err.message || 'Internal server error'
    });
});
```""")

            elif fw == Framework.VUE:
                lines.append("""### Vue 3 Best Practices

**Composition API**:
```javascript
import { ref, computed, onMounted } from 'vue';

export default {
    setup() {
        const count = ref(0);
        const doubled = computed(() => count.value * 2);

        onMounted(() => {
            console.log('Component mounted');
        });

        return { count, doubled };
    }
}
```""")

        return "\n\n".join(lines)

    def _get_testing_requirements(self) -> str:
        """JavaScript testing requirements."""
        return """## Testing Requirements

**Test Framework**: Jest (or Vitest)

**Test Coverage**: Minimum 80%

**Test Structure**:
```javascript
describe('calculateTotal', () => {
    it('should calculate total with tax', () => {
        const result = calculateTotal(100, 0.1);
        expect(result).toBe(110);
    });

    it('should handle zero price', () => {
        expect(calculateTotal(0, 0.5)).toBe(0);
    });
});
```

**Async Tests**:
```javascript
it('should fetch user data', async () => {
    const user = await fetchUser(1);
    expect(user).toHaveProperty('name');
});
```

**Mocking**:
```javascript
jest.mock('./api');
import { fetchUser } from './api';

it('should handle API errors', async () => {
    fetchUser.mockRejectedValue(new Error('Network error'));
    await expect(loadUser(1)).rejects.toThrow('Network error');
});
```"""


class TypeScriptPromptStrategy(PromptStrategy):
    """
    TypeScript-specific prompt strategy with Next.js and React TypeScript.

    **Best Practices**:
    - Strict typing (no any)
    - Interface definitions for all data structures
    - Type guards for runtime checks
    - Generics for reusable components

    **Next.js Specifics**:
    - Server Components (App Router)
    - Metadata API for SEO
    - API Routes with type safety
    - Data fetching patterns

    **React TypeScript**:
    - Typed Props and State
    - Typed hooks (useState<T>, useRef<T>)
    - Generic components
    - Typed context and reducers
    """

    def _get_language_guidelines(self) -> str:
        """TypeScript best practices and type safety guide."""
        return """## TypeScript Best Practices

**Strict Typing**:
- Enable `strict: true` in tsconfig.json
- Avoid `any` type (use `unknown` if needed)
- Use explicit return types
- Define interfaces for all data structures

**Interface Definitions**:
```typescript
interface User {
    id: number;
    name: string;
    email: string;
    createdAt: Date;
    settings?: UserSettings;  // Optional
}

interface UserSettings {
    theme: 'light' | 'dark';
    notifications: boolean;
}
```

**Type Guards**:
```typescript
function isUser(obj: unknown): obj is User {
    return (
        typeof obj === 'object' &&
        obj !== null &&
        'id' in obj &&
        'name' in obj
    );
}
```

**Generics**:
```typescript
function firstElement<T>(arr: T[]): T | undefined {
    return arr[0];
}

const num = firstElement([1, 2, 3]);  // number | undefined
const str = firstElement(['a', 'b']);  // string | undefined
```

**Utility Types**:
- `Partial<T>`: Make all properties optional
- `Pick<T, K>`: Select specific properties
- `Omit<T, K>`: Exclude specific properties
- `Record<K, V>`: Create object type with specific keys"""

    def _get_framework_specifics(
        self, frameworks: List['FrameworkDetection']
    ) -> str:
        """Next.js and React TypeScript framework-specific guidance."""
        lines = ["## Framework-Specific Guidelines", ""]

        for fw_detection in frameworks:
            fw = fw_detection.framework

            if fw == Framework.NEXTJS:
                lines.append("""### Next.js Best Practices (App Router)

**Server Components**:
```typescript
// app/users/page.tsx
interface User {
    id: number;
    name: string;
}

export default async function UsersPage() {
    const users: User[] = await fetchUsers();

    return (
        <div>
            {users.map(user => (
                <div key={user.id}>{user.name}</div>
            ))}
        </div>
    );
}
```

**Metadata API**:
```typescript
import { Metadata } from 'next';

export const metadata: Metadata = {
    title: 'Users',
    description: 'User management page'
};
```

**API Routes**:
```typescript
// app/api/users/route.ts
import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
    const users = await db.user.findMany();
    return NextResponse.json(users);
}

export async function POST(request: NextRequest) {
    const body = await request.json();
    const user = await db.user.create({ data: body });
    return NextResponse.json(user, { status: 201 });
}
```

**Data Fetching**:
```typescript
async function fetchUsers(): Promise<User[]> {
    const res = await fetch('https://api.example.com/users', {
        next: { revalidate: 60 }  // Revalidate every 60s
    });

    if (!res.ok) {
        throw new Error('Failed to fetch users');
    }

    return res.json();
}
```""")

            elif fw == Framework.REACT:
                lines.append("""### React TypeScript Best Practices

**Typed Props**:
```typescript
interface UserCardProps {
    user: User;
    onUpdate?: (user: User) => void;
    className?: string;
}

const UserCard: React.FC<UserCardProps> = ({
    user,
    onUpdate,
    className
}) => {
    return (
        <div className={className}>
            <h3>{user.name}</h3>
            <button onClick={() => onUpdate?.(user)}>
                Update
            </button>
        </div>
    );
};
```

**Typed Hooks**:
```typescript
function useUsers() {
    const [users, setUsers] = useState<User[]>([]);
    const [loading, setLoading] = useState<boolean>(true);

    useEffect(() => {
        fetchUsers()
            .then(setUsers)
            .finally(() => setLoading(false));
    }, []);

    return { users, loading };
}
```

**Generic Components**:
```typescript
interface ListProps<T> {
    items: T[];
    renderItem: (item: T) => React.ReactNode;
    keyExtractor: (item: T) => string | number;
}

function List<T>({ items, renderItem, keyExtractor }: ListProps<T>) {
    return (
        <ul>
            {items.map(item => (
                <li key={keyExtractor(item)}>
                    {renderItem(item)}
                </li>
            ))}
        </ul>
    );
}
```

**Typed Context**:
```typescript
interface AuthContextType {
    user: User | null;
    login: (email: string, password: string) => Promise<void>;
    logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(
    undefined
);
```""")

        return "\n\n".join(lines)

    def _get_testing_requirements(self) -> str:
        """TypeScript testing requirements."""
        return """## Testing Requirements

**Test Framework**: Jest + TypeScript

**Test Coverage**: Minimum 90%

**Typed Tests**:
```typescript
import { render, screen } from '@testing-library/react';
import UserCard from './UserCard';

const mockUser: User = {
    id: 1,
    name: 'Test User',
    email: 'test@example.com',
    createdAt: new Date()
};

describe('UserCard', () => {
    it('renders user name', () => {
        render(<UserCard user={mockUser} />);
        expect(screen.getByText('Test User')).toBeInTheDocument();
    });
});
```

**Type Safety in Tests**:
- Use proper types for mock data
- Type mock functions correctly
- Ensure type coverage in tests"""


class ConfigFilePromptStrategy(PromptStrategy):
    """
    Config file prompt strategy for JSON, YAML, and Markdown.

    **JSON Requirements**:
    - Valid JSON syntax (no trailing commas)
    - Double quotes only
    - Proper escaping
    - Schema validation

    **YAML Requirements**:
    - Proper indentation (spaces, not tabs)
    - Consistent key-value formatting
    - Anchor/reference support
    - No duplicate keys

    **Markdown Requirements**:
    - Clear structure with headers
    - Code blocks with language tags
    - Lists and tables
    - Links and images
    """

    def _get_language_guidelines(self) -> str:
        """Config file syntax and formatting guidelines."""
        return """## Config File Best Practices

**JSON Syntax**:
- Use double quotes for strings: `"key": "value"`
- NO trailing commas: `{"a": 1}` not `{"a": 1,}`
- Proper escaping: `"path": "C:\\\\Users\\\\Name"`
- Valid types: string, number, boolean, null, object, array

**YAML Syntax**:
- Use spaces for indentation (2 or 4 spaces)
- NO tabs allowed
- Key-value pairs: `key: value`
- Lists: `- item1\\n- item2`
- Comments: `# This is a comment`

**Markdown Syntax**:
- Headers: `# H1`, `## H2`, `### H3`
- Code blocks: ` ```language\\ncode\\n``` `
- Lists: `- item` or `1. item`
- Links: `[text](url)`
- Bold: `**text**`, Italic: `*text*`"""

    def _get_framework_specifics(
        self, frameworks: List['FrameworkDetection']
    ) -> str:
        """Config-specific guidance (minimal framework specifics)."""
        return ""

    def _get_testing_requirements(self) -> str:
        """Config validation requirements."""
        return """## Validation Requirements

**JSON Validation**:
- Must parse without errors
- Must match schema (if provided)
- No syntax errors

**YAML Validation**:
- Must parse without errors
- Proper indentation
- No duplicate keys

**Markdown Validation**:
- Headers form proper hierarchy
- Code blocks have language tags
- Links are properly formatted"""


class PromptStrategyFactory:
    """
    Factory for creating file-type-specific prompt strategies.

    **Strategy Selection**:
    - Python → PythonPromptStrategy
    - JavaScript → JavaScriptPromptStrategy
    - TypeScript → TypeScriptPromptStrategy
    - JSON/YAML/Markdown → ConfigFilePromptStrategy
    - Unknown → PythonPromptStrategy (fallback)

    **Example Usage**:
    ```python
    strategy = PromptStrategyFactory.get_strategy(FileType.PYTHON)
    prompt = strategy.generate_prompt(context)
    ```
    """

    _strategies: Dict[FileType, PromptStrategy] = {}

    @classmethod
    def get_strategy(cls, file_type: FileType) -> PromptStrategy:
        """
        Get appropriate prompt strategy for file type.

        Implements singleton pattern for strategy instances (reuse).

        Args:
            file_type: Detected file type

        Returns:
            PromptStrategy instance for that file type

        Example:
            >>> strategy = PromptStrategyFactory.get_strategy(FileType.PYTHON)
            >>> assert isinstance(strategy, PythonPromptStrategy)
        """
        # Return cached strategy if exists
        if file_type in cls._strategies:
            return cls._strategies[file_type]

        # Create new strategy based on file type
        if file_type == FileType.PYTHON:
            strategy = PythonPromptStrategy()
        elif file_type == FileType.JAVASCRIPT:
            strategy = JavaScriptPromptStrategy()
        elif file_type == FileType.TYPESCRIPT:
            strategy = TypeScriptPromptStrategy()
        elif file_type in [FileType.JSON, FileType.YAML, FileType.MARKDOWN]:
            strategy = ConfigFilePromptStrategy()
        else:
            # Fallback to Python for unknown types
            strategy = PythonPromptStrategy()

        # Cache for reuse
        cls._strategies[file_type] = strategy

        return strategy

    @classmethod
    def clear_cache(cls) -> None:
        """Clear cached strategies (useful for testing)."""
        cls._strategies.clear()
