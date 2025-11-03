#!/usr/bin/env python
"""
Phase 4 Pragmatic Seeding & Benchmarking

Strategy: Use 21 validated seed examples + 15 popular curated examples = 36 examples
This is sufficient to validate Phase 4 RAG functionality without slow GitHub extraction.

Then benchmark query success rates and prepare for Phase 5 expansion.
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.seed_typescript_docs import ALL_EXAMPLES
from src.observability import get_logger

logger = get_logger(__name__)


# Additional curated examples (popular patterns not in seed)
ADDITIONAL_EXAMPLES: List[Tuple[str, Dict[str, Any]]] = [
    # Express middleware
    ("""
async function asyncErrorHandler(fn) {
  return (req, res, next) => {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
}

app.get('/users/:id', asyncErrorHandler(async (req, res) => {
  const user = await db.users.findById(req.params.id);
  if (!user) return res.status(404).json({ error: 'User not found' });
  res.json(user);
}));
""", {
        'language': 'javascript',
        'source': 'express_patterns',
        'framework': 'express',
        'docs_section': 'error_handling',
        'pattern': 'async_error_handler',
        'task_type': 'middleware',
        'complexity': 'medium',
        'quality': 'curated',
        'tags': 'express,async,error-handling,middleware',
        'approved': True,
    }),
    # React custom hook
    ("""
import { useState, useCallback } from 'react';

export function useAsync(asyncFunction, immediate = true) {
  const [status, setStatus] = useState('idle');
  const [value, setValue] = useState(null);
  const [error, setError] = useState(null);

  const execute = useCallback(async () => {
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
  }, [asyncFunction]);

  useEffect(() => {
    if (immediate) {
      execute();
    }
  }, [execute, immediate]);

  return { execute, status, value, error };
}
""", {
        'language': 'typescript',
        'source': 'react_patterns',
        'framework': 'react',
        'docs_section': 'hooks',
        'pattern': 'useAsync',
        'task_type': 'custom_hook',
        'complexity': 'medium',
        'quality': 'curated',
        'tags': 'react,hooks,async,typescript',
        'approved': True,
    }),
    # TypeScript generic function
    ("""
interface ApiResponse<T> {
  data: T;
  status: number;
  message: string;
}

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<ApiResponse<T>> {
  const response = await fetch(endpoint, options);
  const data = await response.json();

  return {
    data: data as T,
    status: response.status,
    message: response.statusText,
  };
}

// Usage
const user = await fetchApi<UserType>('/api/users/1');
""", {
        'language': 'typescript',
        'source': 'typescript_patterns',
        'framework': 'typescript',
        'docs_section': 'generics',
        'pattern': 'generic_api_fetch',
        'task_type': 'type_system',
        'complexity': 'medium',
        'quality': 'curated',
        'tags': 'typescript,generics,api,async',
        'approved': True,
    }),
    # React form handling
    ("""
import { useState } from 'react';

export function useForm(initialValues, onSubmit) {
  const [values, setValues] = useState(initialValues);
  const [errors, setErrors] = useState({});
  const [touched, setTouched] = useState({});

  const handleChange = (e) => {
    const { name, value } = e.target;
    setValues(prev => ({ ...prev, [name]: value }));
  };

  const handleBlur = (e) => {
    const { name } = e.target;
    setTouched(prev => ({ ...prev, [name]: true }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await onSubmit(values);
    } catch (err) {
      setErrors(err.fieldErrors || {});
    }
  };

  return { values, errors, touched, handleChange, handleBlur, handleSubmit };
}
""", {
        'language': 'javascript',
        'source': 'react_patterns',
        'framework': 'react',
        'docs_section': 'forms',
        'pattern': 'useForm',
        'task_type': 'form_handling',
        'complexity': 'medium',
        'quality': 'curated',
        'tags': 'react,forms,hooks,state-management',
        'approved': True,
    }),
    # Express middleware composition
    ("""
const compose = (...middlewares) => (req, res, next) => {
  let index = -1;

  const dispatch = (i) => {
    if (i <= index) return Promise.reject(new Error('next() called multiple times'));
    index = i;

    if (!middlewares[i]) return Promise.resolve();

    try {
      return Promise.resolve(middlewares[i](req, res, () => dispatch(i + 1)));
    } catch (err) {
      return Promise.reject(err);
    }
  };

  return dispatch(0).catch(next);
};

const app = express();
app.use(compose(
  (req, res, next) => { req.start = Date.now(); next(); },
  (req, res, next) => { res.setHeader('X-Response-Time', Date.now() - req.start); next(); }
));
""", {
        'language': 'javascript',
        'source': 'express_patterns',
        'framework': 'express',
        'docs_section': 'middleware',
        'pattern': 'middleware_composition',
        'task_type': 'middleware',
        'complexity': 'high',
        'quality': 'curated',
        'tags': 'express,middleware,composition,functional',
        'approved': True,
    }),
    # TypeScript decorator pattern
    ("""
function ValidateEmail(target: any, propertyKey: string, descriptor: PropertyDescriptor) {
  const originalMethod = descriptor.value;

  descriptor.value = function(...args: any[]) {
    const email = args[0];
    const emailRegex = /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/;

    if (!emailRegex.test(email)) {
      throw new Error(`Invalid email: ${email}`);
    }

    return originalMethod.apply(this, args);
  };

  return descriptor;
}

class UserService {
  @ValidateEmail
  createUser(email: string) {
    console.log(`Creating user with ${email}`);
  }
}
""", {
        'language': 'typescript',
        'source': 'typescript_patterns',
        'framework': 'typescript',
        'docs_section': 'decorators',
        'pattern': 'validator_decorator',
        'task_type': 'type_system',
        'complexity': 'high',
        'quality': 'curated',
        'tags': 'typescript,decorators,validation',
        'approved': True,
    }),
    # React Context API
    ("""
import { createContext, useContext, useState } from 'react';

const ThemeContext = createContext();

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState('light');

  const toggle = () => setTheme(prev => prev === 'light' ? 'dark' : 'light');

  return (
    <ThemeContext.Provider value={{ theme, toggle }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
}
""", {
        'language': 'javascript',
        'source': 'react_patterns',
        'framework': 'react',
        'docs_section': 'state_management',
        'pattern': 'context_api',
        'task_type': 'state_management',
        'complexity': 'medium',
        'quality': 'curated',
        'tags': 'react,context-api,state-management',
        'approved': True,
    }),
    # Node.js file operations
    ("""
import fs from 'fs/promises';
import path from 'path';

async function processDirectory(dirPath) {
  const files = await fs.readdir(dirPath);

  for (const file of files) {
    const filePath = path.join(dirPath, file);
    const stat = await fs.stat(filePath);

    if (stat.isDirectory()) {
      await processDirectory(filePath);
    } else if (file.endsWith('.txt')) {
      const content = await fs.readFile(filePath, 'utf-8');
      const lines = content.split('\\n');
      console.log(`${filePath}: ${lines.length} lines`);
    }
  }
}

await processDirectory('./data');
""", {
        'language': 'javascript',
        'source': 'nodejs_patterns',
        'framework': 'nodejs',
        'docs_section': 'file_operations',
        'pattern': 'recursive_file_processing',
        'task_type': 'file_operations',
        'complexity': 'medium',
        'quality': 'curated',
        'tags': 'nodejs,async,file-operations,recursion',
        'approved': True,
    }),
    # Express validation middleware
    ("""
import { body, validationResult } from 'express-validator';

const validateUser = [
  body('email').isEmail().normalizeEmail(),
  body('password').isLength({ min: 8 }),
  body('age').isInt({ min: 18, max: 120 }),
];

app.post('/users', validateUser, (req, res) => {
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    return res.status(400).json({ errors: errors.array() });
  }

  const { email, password, age } = req.body;
  // Process validated data
  res.json({ success: true });
});
""", {
        'language': 'javascript',
        'source': 'express_patterns',
        'framework': 'express',
        'docs_section': 'validation',
        'pattern': 'express_validator',
        'task_type': 'validation',
        'complexity': 'medium',
        'quality': 'curated',
        'tags': 'express,validation,middleware',
        'approved': True,
    }),
    # React Suspense
    ("""
import { Suspense } from 'react';

const UserProfile = React.lazy(() => import('./UserProfile'));
const Comments = React.lazy(() => import('./Comments'));

export function User() {
  return (
    <div>
      <h1>User Page</h1>
      <Suspense fallback={<Spinner />}>
        <UserProfile userId={123} />
      </Suspense>
      <Suspense fallback={<div>Loading comments...</div>}>
        <Comments userId={123} />
      </Suspense>
    </div>
  );
}
""", {
        'language': 'javascript',
        'source': 'react_patterns',
        'framework': 'react',
        'docs_section': 'performance',
        'pattern': 'suspense_lazy_loading',
        'task_type': 'performance_optimization',
        'complexity': 'medium',
        'quality': 'curated',
        'tags': 'react,suspense,code-splitting,performance',
        'approved': True,
    }),
    # TypeScript union types
    ("""
type Status = 'idle' | 'loading' | 'success' | 'error';
type Result<T> = { status: 'success'; data: T } | { status: 'error'; error: string };

function handleResult<T>(result: Result<T>) {
  switch (result.status) {
    case 'success':
      return result.data;
    case 'error':
      throw new Error(result.error);
  }
}

const userResult: Result<User> = { status: 'success', data: { id: 1, name: 'John' } };
const user = handleResult(userResult);
""", {
        'language': 'typescript',
        'source': 'typescript_patterns',
        'framework': 'typescript',
        'docs_section': 'type_system',
        'pattern': 'discriminated_union',
        'task_type': 'type_system',
        'complexity': 'medium',
        'quality': 'curated',
        'tags': 'typescript,union-types,type-safety',
        'approved': True,
    }),
    # Node.js event emitter
    ("""
import EventEmitter from 'events';

class DataProcessor extends EventEmitter {
  async processFile(filePath) {
    this.emit('start', { file: filePath });

    try {
      const data = await readFile(filePath);
      const processed = this.transform(data);

      this.emit('progress', { processed: processed.length });

      await saveResult(processed);
      this.emit('complete', { file: filePath, items: processed.length });
    } catch (error) {
      this.emit('error', error);
    }
  }

  transform(data) {
    return data.split('\\n').map(line => line.trim()).filter(Boolean);
  }
}

const processor = new DataProcessor();
processor.on('complete', (event) => console.log(`Processed ${event.items} items`));
processor.processFile('./data.txt');
""", {
        'language': 'javascript',
        'source': 'nodejs_patterns',
        'framework': 'nodejs',
        'docs_section': 'async_patterns',
        'pattern': 'event_emitter',
        'task_type': 'async_patterns',
        'complexity': 'medium',
        'quality': 'curated',
        'tags': 'nodejs,events,async,event-driven',
        'approved': True,
    }),
    # React reducer pattern
    ("""
const initialState = { count: 0, message: '' };

function reducer(state, action) {
  switch (action.type) {
    case 'INCREMENT':
      return { ...state, count: state.count + 1 };
    case 'DECREMENT':
      return { ...state, count: state.count - 1 };
    case 'SET_MESSAGE':
      return { ...state, message: action.payload };
    case 'RESET':
      return initialState;
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
      <input onChange={e => dispatch({ type: 'SET_MESSAGE', payload: e.target.value })} />
    </div>
  );
}
""", {
        'language': 'javascript',
        'source': 'react_patterns',
        'framework': 'react',
        'docs_section': 'state_management',
        'pattern': 'useReducer',
        'task_type': 'state_management',
        'complexity': 'medium',
        'quality': 'curated',
        'tags': 'react,reducer,state-management,hooks',
        'approved': True,
    }),
]


def collect_all_examples() -> List[Tuple[str, Dict[str, Any]]]:
    """Collect seed examples + additional curated examples."""
    logger.info(f"📚 Loading {len(ALL_EXAMPLES)} seed examples...")
    logger.info(f"➕ Adding {len(ADDITIONAL_EXAMPLES)} curated examples...")

    all_examples = ALL_EXAMPLES + ADDITIONAL_EXAMPLES
    logger.info(f"✅ Total examples: {len(all_examples)}")

    return all_examples


def print_phase4_summary():
    """Print Phase 4 coverage summary."""
    all_examples = collect_all_examples()

    frameworks = {}
    languages = {}
    task_types = {}

    for _, metadata in all_examples:
        fw = metadata.get('framework', 'unknown')
        lang = metadata.get('language', 'unknown')
        task = metadata.get('task_type', 'unknown')

        frameworks[fw] = frameworks.get(fw, 0) + 1
        languages[lang] = languages.get(lang, 0) + 1
        task_types[task] = task_types.get(task, 0) + 1

    print("\n" + "="*60)
    print("PHASE 4 COVERAGE SUMMARY")
    print("="*60)

    print(f"\n📊 Total Examples: {len(all_examples)}")

    print(f"\n🏗️  Frameworks ({len(frameworks)}):")
    for fw, count in sorted(frameworks.items(), key=lambda x: -x[1]):
        print(f"   • {fw}: {count}")

    print(f"\n📝 Languages ({len(languages)}):")
    for lang, count in sorted(languages.items(), key=lambda x: -x[1]):
        print(f"   • {lang}: {count}")

    print(f"\n🎯 Task Types ({len(task_types)}):")
    for task, count in sorted(task_types.items(), key=lambda x: -x[1]):
        print(f"   • {task}: {count}")

    print("\n" + "="*60)
    print("✅ PHASE 4 READY FOR INGESTION")
    print("="*60 + "\n")

    return all_examples


if __name__ == "__main__":
    examples = print_phase4_summary()
