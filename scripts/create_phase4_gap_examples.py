#!/usr/bin/env python
"""
Phase 4 Gap-Filling Curation

Create 50-100 targeted examples for identified failure patterns:
- React hooks (hooks for state management)
- Promise patterns (promise chains, async/await)
- Component composition
- Type validation
- Form submission handling
- Middleware patterns
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.observability import get_logger

logger = get_logger(__name__)


def get_gap_examples():
    """Get 50-100 curated examples targeting identified failure patterns."""

    # ========================================
    # REACT HOOKS EXAMPLES (6 queries failed)
    # ========================================

    react_hooks = [
        # useState examples
        {
            "code": """
import React, { useState } from 'react';

export function Counter() {
  const [count, setCount] = useState(0);

  return (
    <div>
      <p>Count: {count}</p>
      <button onClick={() => setCount(count + 1)}>Increment</button>
    </div>
  );
}
""",
            "language": "javascript",
            "framework": "react",
            "pattern": "useState hook",
            "task_type": "state management",
            "complexity": "low",
            "tags": ["hooks", "state", "useState", "react"],
            "source": "curation"
        },
        # useReducer examples
        {
            "code": """
import React, { useReducer } from 'react';

const initialState = { count: 0 };

function reducer(state, action) {
  switch(action.type) {
    case 'INCREMENT':
      return { count: state.count + 1 };
    case 'DECREMENT':
      return { count: state.count - 1 };
    default:
      return state;
  }
}

export function Counter() {
  const [state, dispatch] = useReducer(reducer, initialState);

  return (
    <div>
      <p>Count: {state.count}</p>
      <button onClick={() => dispatch({ type: 'INCREMENT' })}>+</button>
      <button onClick={() => dispatch({ type: 'DECREMENT' })}>-</button>
    </div>
  );
}
""",
            "language": "javascript",
            "framework": "react",
            "pattern": "useReducer hook",
            "task_type": "state management",
            "complexity": "medium",
            "tags": ["hooks", "useReducer", "reducer", "state", "react"],
            "source": "curation"
        },
        # useEffect examples
        {
            "code": """
import React, { useState, useEffect } from 'react';

export function DataFetcher() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const response = await fetch('/api/data');
        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, []);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return <div>{JSON.stringify(data)}</div>;
}
""",
            "language": "javascript",
            "framework": "react",
            "pattern": "useEffect hook with data fetching",
            "task_type": "data fetching",
            "complexity": "medium",
            "tags": ["hooks", "useEffect", "fetch", "async", "react"],
            "source": "curation"
        },
        # useContext examples
        {
            "code": """
import React, { createContext, useContext, useState } from 'react';

const ThemeContext = createContext();

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState('light');

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}

export function ThemedComponent() {
  const { theme, setTheme } = useTheme();

  return (
    <div style={{ background: theme === 'light' ? '#fff' : '#333' }}>
      Current theme: {theme}
      <button onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}>
        Toggle
      </button>
    </div>
  );
}
""",
            "language": "javascript",
            "framework": "react",
            "pattern": "useContext and createContext",
            "task_type": "context management",
            "complexity": "medium",
            "tags": ["hooks", "useContext", "context", "provider", "react"],
            "source": "curation"
        },
        # Custom useAsync hook
        {
            "code": """
import { useState, useEffect } from 'react';

export function useAsync(asyncFunction, immediate = true) {
  const [status, setStatus] = useState('idle');
  const [value, setValue] = useState(null);
  const [error, setError] = useState(null);

  const execute = async () => {
    setStatus('pending');
    setValue(null);
    setError(null);
    try {
      const response = await asyncFunction();
      setValue(response);
      setStatus('success');
      return response;
    } catch (error) {
      setError(error);
      setStatus('error');
    }
  };

  useEffect(() => {
    if (immediate) execute();
  }, [immediate]);

  return { execute, status, value, error };
}
""",
            "language": "javascript",
            "framework": "react",
            "pattern": "custom useAsync hook",
            "task_type": "async operations",
            "complexity": "high",
            "tags": ["hooks", "custom hook", "async", "react"],
            "source": "curation"
        },
        # useMemo example
        {
            "code": """
import React, { useMemo } from 'react';

export function ExpensiveCalculation({ items }) {
  const total = useMemo(() => {
    return items.reduce((sum, item) => sum + item.price, 0);
  }, [items]);

  return <div>Total: ${total}</div>;
}
""",
            "language": "javascript",
            "framework": "react",
            "pattern": "useMemo hook",
            "task_type": "performance optimization",
            "complexity": "medium",
            "tags": ["hooks", "useMemo", "memoization", "react"],
            "source": "curation"
        },
    ]

    # ========================================
    # PROMISE AND ASYNC PATTERNS (3 queries failed)
    # ========================================

    promise_patterns = [
        {
            "code": """
function fetchUserData(userId) {
  return fetch(`/api/users/${userId}`)
    .then(response => response.json())
    .then(data => {
      console.log('User:', data);
      return data;
    })
    .catch(error => {
      console.error('Failed to fetch:', error);
      throw error;
    });
}

// Or with async/await
async function fetchUserDataAsync(userId) {
  try {
    const response = await fetch(`/api/users/${userId}`);
    const data = await response.json();
    console.log('User:', data);
    return data;
  } catch (error) {
    console.error('Failed to fetch:', error);
    throw error;
  }
}
""",
            "language": "javascript",
            "framework": "javascript",
            "pattern": "Promise chains and async/await",
            "task_type": "async operations",
            "complexity": "medium",
            "tags": ["promise", "async", "await", "fetch"],
            "source": "curation"
        },
        {
            "code": """
// Promise.all for parallel requests
async function fetchMultipleUsers(userIds) {
  try {
    const promises = userIds.map(id =>
      fetch(`/api/users/${id}`).then(r => r.json())
    );
    const users = await Promise.all(promises);
    return users;
  } catch (error) {
    console.error('Failed:', error);
    throw error;
  }
}

// Promise.race for timeout
async function fetchWithTimeout(url, timeoutMs) {
  const fetchPromise = fetch(url);
  const timeoutPromise = new Promise((_, reject) =>
    setTimeout(() => reject(new Error('Timeout')), timeoutMs)
  );

  return Promise.race([fetchPromise, timeoutPromise]);
}
""",
            "language": "javascript",
            "framework": "javascript",
            "pattern": "Promise.all and Promise.race",
            "task_type": "async operations",
            "complexity": "high",
            "tags": ["promise", "Promise.all", "Promise.race", "parallel"],
            "source": "curation"
        },
        {
            "code": """
// Promise error handling patterns
function chainedPromises() {
  return fetch('/api/data')
    .then(response => {
      if (!response.ok) throw new Error('Not found');
      return response.json();
    })
    .then(data => processData(data))
    .catch(error => {
      console.error('Error:', error);
      return null;  // fallback
    })
    .finally(() => {
      console.log('Cleanup complete');
    });
}

// Retry pattern
async function fetchWithRetry(url, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fetch(url).then(r => r.json());
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
    }
  }
}
""",
            "language": "javascript",
            "framework": "javascript",
            "pattern": "Promise error handling and retry",
            "task_type": "error handling",
            "complexity": "high",
            "tags": ["promise", "error handling", "retry", "async"],
            "source": "curation"
        },
    ]

    # ========================================
    # COMPONENT COMPOSITION (2 queries failed)
    # ========================================

    component_composition = [
        {
            "code": """
import React from 'react';

// Render props pattern
function DataFetcher({ render }) {
  const [data, setData] = React.useState(null);

  React.useEffect(() => {
    fetch('/api/data')
      .then(r => r.json())
      .then(data => setData(data));
  }, []);

  return render(data);
}

// Usage
<DataFetcher
  render={(data) => data ? <div>{data}</div> : <div>Loading</div>}
/>
""",
            "language": "javascript",
            "framework": "react",
            "pattern": "render props pattern",
            "task_type": "component composition",
            "complexity": "medium",
            "tags": ["composition", "render props", "react"],
            "source": "curation"
        },
        {
            "code": """
import React from 'react';

// Higher-order component pattern
function withDataFetching(WrappedComponent) {
  return function DataFetchingComponent(props) {
    const [data, setData] = React.useState(null);
    const [loading, setLoading] = React.useState(true);

    React.useEffect(() => {
      fetch('/api/data')
        .then(r => r.json())
        .then(data => {
          setData(data);
          setLoading(false);
        });
    }, []);

    return <WrappedComponent data={data} loading={loading} {...props} />;
  };
}

// Usage
const EnhancedComponent = withDataFetching(MyComponent);
""",
            "language": "javascript",
            "framework": "react",
            "pattern": "higher-order component (HOC)",
            "task_type": "component composition",
            "complexity": "high",
            "tags": ["composition", "HOC", "higher-order", "react"],
            "source": "curation"
        },
        {
            "code": """
import React from 'react';

// Component composition with children
function Card({ title, children, footer }) {
  return (
    <div className="card">
      <div className="card-header">
        <h2>{title}</h2>
      </div>
      <div className="card-body">
        {children}
      </div>
      {footer && <div className="card-footer">{footer}</div>}
    </div>
  );
}

// Usage
<Card title="User Info" footer={<button>Close</button>}>
  <p>User details here</p>
</Card>
""",
            "language": "javascript",
            "framework": "react",
            "pattern": "component composition with children",
            "task_type": "component composition",
            "complexity": "low",
            "tags": ["composition", "children", "react"],
            "source": "curation"
        },
    ]

    # ========================================
    # TYPE VALIDATION (1 query failed - "Type validation")
    # ========================================

    type_validation = [
        {
            "code": """
import { z } from 'zod';

// Schema definition
const UserSchema = z.object({
  id: z.number(),
  name: z.string().min(1),
  email: z.string().email(),
  age: z.number().int().positive().optional(),
});

// Validation
function validateUser(data) {
  try {
    return UserSchema.parse(data);
  } catch (error) {
    console.error('Validation error:', error);
    return null;
  }
}

// Type inference
type User = z.infer<typeof UserSchema>;
""",
            "language": "typescript",
            "framework": "typescript",
            "pattern": "Zod schema validation",
            "task_type": "validation",
            "complexity": "medium",
            "tags": ["validation", "schema", "zod", "typescript"],
            "source": "curation"
        },
        {
            "code": """
// TypeScript type guards
function isUser(value: unknown): value is User {
  return (
    typeof value === 'object' &&
    value !== null &&
    'id' in value &&
    'name' in value &&
    typeof value.id === 'number' &&
    typeof value.name === 'string'
  );
}

// Runtime validation with TypeScript
function processUser(data: unknown) {
  if (isUser(data)) {
    console.log('Valid user:', data);
    return data;
  }
  throw new Error('Invalid user data');
}
""",
            "language": "typescript",
            "framework": "typescript",
            "pattern": "TypeScript type guards",
            "task_type": "type validation",
            "complexity": "high",
            "tags": ["validation", "type guards", "typescript"],
            "source": "curation"
        },
    ]

    # ========================================
    # FORM SUBMISSION (1 query failed - "Form submission handling")
    # ========================================

    form_patterns = [
        {
            "code": """
import React, { useState } from 'react';

export function LoginForm() {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
  });
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);

  function handleChange(e) {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);

    try {
      const response = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        const error = await response.json();
        setErrors(error.fields || {});
        return;
      }

      const result = await response.json();
      localStorage.setItem('token', result.token);
      window.location.href = '/dashboard';
    } catch (error) {
      setErrors({ general: error.message });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="email"
        name="email"
        value={formData.email}
        onChange={handleChange}
        placeholder="Email"
      />
      <input
        type="password"
        name="password"
        value={formData.password}
        onChange={handleChange}
        placeholder="Password"
      />
      <button type="submit" disabled={submitting}>
        {submitting ? 'Logging in...' : 'Login'}
      </button>
      {errors.general && <div className="error">{errors.general}</div>}
    </form>
  );
}
""",
            "language": "javascript",
            "framework": "react",
            "pattern": "form submission with validation",
            "task_type": "form handling",
            "complexity": "medium",
            "tags": ["form", "submission", "validation", "react"],
            "source": "curation"
        },
    ]

    # ========================================
    # MIDDLEWARE PATTERNS (1 query failed)
    # ========================================

    middleware_patterns = [
        {
            "code": """
import Express from 'express';

const app = Express();

// Authentication middleware
function authMiddleware(req, res, next) {
  const token = req.headers.authorization?.split(' ')[1];

  if (!token) {
    return res.status(401).json({ error: 'No token' });
  }

  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    req.user = decoded;
    next();
  } catch (error) {
    res.status(401).json({ error: 'Invalid token' });
  }
}

// Logging middleware
function loggingMiddleware(req, res, next) {
  console.log(`${req.method} ${req.path}`);
  next();
}

// Error handling middleware (must be last)
function errorHandler(err, req, res, next) {
  console.error(err.stack);
  res.status(500).json({ error: 'Internal server error' });
}

app.use(loggingMiddleware);
app.use('/api', authMiddleware);

app.get('/api/user', (req, res) => {
  res.json({ user: req.user });
});

app.use(errorHandler);
""",
            "language": "javascript",
            "framework": "express",
            "pattern": "middleware patterns",
            "task_type": "middleware",
            "complexity": "medium",
            "tags": ["middleware", "express", "auth", "logging"],
            "source": "curation"
        },
    ]

    # ========================================
    # TYPESCRIPT ADVANCED PATTERNS
    # ========================================

    typescript_advanced = [
        {
            "code": """
// Discriminated unions in TypeScript
type Result<T> =
  | { status: 'success'; data: T }
  | { status: 'error'; error: Error }
  | { status: 'loading' };

function handleResult<T>(result: Result<T>) {
  switch (result.status) {
    case 'success':
      console.log('Data:', result.data);
      return result.data;
    case 'error':
      console.error('Error:', result.error);
      return null;
    case 'loading':
      console.log('Still loading...');
      return undefined;
  }
}
""",
            "language": "typescript",
            "framework": "typescript",
            "pattern": "discriminated unions",
            "task_type": "type system",
            "complexity": "high",
            "tags": ["discriminated unions", "typescript", "types"],
            "source": "curation"
        },
        {
            "code": """
// TypeScript generics for API calls
async function apiCall<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(endpoint, options);

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

// Usage
interface User {
  id: number;
  name: string;
}

const user = await apiCall<User>('/api/users/1');
""",
            "language": "typescript",
            "framework": "typescript",
            "pattern": "generic API calls",
            "task_type": "api integration",
            "complexity": "medium",
            "tags": ["generics", "api", "typescript"],
            "source": "curation"
        },
    ]

    # Combine all examples
    all_examples = (
        react_hooks +
        promise_patterns +
        component_composition +
        type_validation +
        form_patterns +
        middleware_patterns +
        typescript_advanced
    )

    return all_examples


def main():
    logger.info("=" * 80)
    logger.info("🎯 PHASE 4 GAP-FILLING CURATION")
    logger.info("=" * 80)

    examples = get_gap_examples()

    logger.info(f"\n📊 Created {len(examples)} targeted examples:")

    # Group by pattern
    patterns = {}
    for ex in examples:
        pattern = ex.get("pattern", "unknown")
        if pattern not in patterns:
            patterns[pattern] = 0
        patterns[pattern] += 1

    logger.info("\nBy pattern:")
    for pattern, count in sorted(patterns.items(), key=lambda x: -x[1]):
        logger.info(f"  • {pattern}: {count}")

    # Group by framework
    frameworks = {}
    for ex in examples:
        fw = ex.get("framework", "unknown")
        if fw not in frameworks:
            frameworks[fw] = 0
        frameworks[fw] += 1

    logger.info("\nBy framework:")
    for fw, count in sorted(frameworks.items(), key=lambda x: -x[1]):
        logger.info(f"  • {fw}: {count}")

    # Group by task type
    tasks = {}
    for ex in examples:
        task = ex.get("task_type", "unknown")
        if task not in tasks:
            tasks[task] = 0
        tasks[task] += 1

    logger.info("\nBy task type:")
    for task, count in sorted(tasks.items(), key=lambda x: -x[1]):
        logger.info(f"  • {task}: {count}")

    logger.info("\n" + "=" * 80)
    logger.info(f"✅ Generated {len(examples)} gap-filling examples")
    logger.info("=" * 80)

    return examples


if __name__ == "__main__":
    examples = main()

    # Return in format compatible with ingest script
    print(f"\n# Total examples: {len(examples)}")
    print("# Ready for ingestion")
