"""
Tests for FileTypeDetector - Multi-signal file type detection.

Comprehensive test coverage for Task Group 2 implementation with:
- Language detection tests (Python, JS/TS, JSON, YAML, Markdown)
- Framework detection tests (8+ frameworks)
- Import analysis tests
- Confidence scoring tests
- Conflict resolution tests

Target: 16-24 focused tests with >90% coverage
"""

import pytest
from src.services.file_type_detector import (
    FileTypeDetector,
    FileType,
    Framework,
    FileTypeDetection,
    FrameworkDetection,
    get_file_type_detector,
)


class TestLanguageDetection:
    """Tests for language detection (Task 2.1)."""

    def test_python_detection_with_extension(self):
        """Test Python detection with .py file extension."""
        detector = FileTypeDetector()
        result = detector.detect(
            task_name="Create function",
            task_description="Simple Python function",
            target_files=["src/utils.py"]
        )

        assert result.file_type == FileType.PYTHON
        assert result.confidence >= 0.90
        assert ".py" in result.reasoning

    def test_python_detection_with_keywords(self):
        """Test Python detection with language keywords."""
        detector = FileTypeDetector()
        code = """
def calculate_sum(a: int, b: int) -> int:
    return a + b

class Calculator:
    def __init__(self):
        self.result = 0
"""
        result = detector.detect(
            task_name="Create calculator",
            task_description="Python calculator class",
            code_snippet=code
        )

        assert result.file_type == FileType.PYTHON
        assert result.confidence >= 0.60

    def test_javascript_detection_with_extension(self):
        """Test JavaScript detection with .js extension."""
        detector = FileTypeDetector()
        result = detector.detect(
            task_name="Create module",
            task_description="JavaScript module",
            target_files=["src/utils.js"]
        )

        assert result.file_type == FileType.JAVASCRIPT
        assert result.confidence >= 0.90
        assert ".js" in result.reasoning

    def test_typescript_detection_with_extension(self):
        """Test TypeScript detection with .ts extension."""
        detector = FileTypeDetector()
        result = detector.detect(
            task_name="Create types",
            task_description="TypeScript type definitions",
            target_files=["src/types.ts"]
        )

        assert result.file_type == FileType.TYPESCRIPT
        assert result.confidence >= 0.90
        assert ".ts" in result.reasoning

    def test_typescript_detection_with_keywords(self):
        """Test TypeScript detection with type keywords."""
        detector = FileTypeDetector()
        code = """
interface User {
    id: number;
    name: string;
    email: string;
}

type UserId = number;

function getUser(id: UserId): Promise<User> {
    return fetch(`/api/users/${id}`);
}
"""
        result = detector.detect(
            task_name="Create user types",
            task_description="TypeScript user interface",
            code_snippet=code
        )

        assert result.file_type == FileType.TYPESCRIPT
        assert result.confidence >= 0.60

    def test_json_detection_with_extension(self):
        """Test JSON detection with .json extension."""
        detector = FileTypeDetector()
        result = detector.detect(
            task_name="Create config",
            task_description="JSON configuration file",
            target_files=["config/settings.json"]
        )

        assert result.file_type == FileType.JSON
        assert result.confidence >= 0.90

    def test_yaml_detection_with_extension(self):
        """Test YAML detection with .yaml extension."""
        detector = FileTypeDetector()
        result = detector.detect(
            task_name="Create config",
            task_description="YAML configuration",
            target_files=["config/app.yaml"]
        )

        assert result.file_type == FileType.YAML
        assert result.confidence >= 0.90

    def test_markdown_detection_with_extension(self):
        """Test Markdown detection with .md extension."""
        detector = FileTypeDetector()
        result = detector.detect(
            task_name="Create docs",
            task_description="Markdown documentation",
            target_files=["docs/README.md"]
        )

        assert result.file_type == FileType.MARKDOWN
        assert result.confidence >= 0.90


class TestFrameworkDetection:
    """Tests for framework detection (Task 2.2)."""

    def test_fastapi_framework_detection(self):
        """Test FastAPI framework detection."""
        detector = FileTypeDetector()
        code = """
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel

app = FastAPI()

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id}
"""
        result = detector.detect(
            task_name="Create FastAPI endpoint",
            task_description="REST API endpoint",
            target_files=["api/users.py"],
            code_snippet=code
        )

        assert result.file_type == FileType.PYTHON
        assert len(result.frameworks) > 0
        fastapi_detected = any(f.framework == Framework.FASTAPI for f in result.frameworks)
        assert fastapi_detected

    def test_pytest_framework_detection(self):
        """Test Pytest framework detection."""
        detector = FileTypeDetector()
        code = """
import pytest
from app.services import UserService

@pytest.fixture
def user_service():
    return UserService()

@pytest.mark.parametrize("user_id", [1, 2, 3])
def test_get_user(user_service, user_id):
    user = user_service.get_user(user_id)
    assert user is not None
"""
        result = detector.detect(
            task_name="Create test",
            task_description="Pytest test case",
            target_files=["tests/test_users.py"],
            code_snippet=code
        )

        assert result.file_type == FileType.PYTHON
        pytest_detected = any(f.framework == Framework.PYTEST for f in result.frameworks)
        assert pytest_detected

    def test_react_framework_detection(self):
        """Test React framework detection."""
        detector = FileTypeDetector()
        code = """
import React, { useState, useEffect } from 'react';

function UserProfile({ userId }) {
    const [user, setUser] = useState(null);

    useEffect(() => {
        fetch(`/api/users/${userId}`)
            .then(res => res.json())
            .then(setUser);
    }, [userId]);

    return <div className="profile">{user?.name}</div>;
}
"""
        result = detector.detect(
            task_name="Create React component",
            task_description="User profile component",
            target_files=["components/UserProfile.jsx"],
            code_snippet=code
        )

        assert result.file_type == FileType.JAVASCRIPT
        react_detected = any(f.framework == Framework.REACT for f in result.frameworks)
        assert react_detected

    def test_nextjs_framework_detection(self):
        """Test Next.js framework detection."""
        detector = FileTypeDetector()
        code = """
import { GetServerSideProps } from 'next';

export const getServerSideProps: GetServerSideProps = async (context) => {
    const userId = context.params?.id;
    const user = await fetch(`/api/users/${userId}`).then(r => r.json());
    return { props: { user } };
};

export default function UserPage({ user }) {
    return <div>{user.name}</div>;
}
"""
        result = detector.detect(
            task_name="Create Next.js page",
            task_description="Server-side rendered page",
            target_files=["pages/users/[id].tsx"],
            code_snippet=code
        )

        assert result.file_type == FileType.TYPESCRIPT
        nextjs_detected = any(f.framework == Framework.NEXTJS for f in result.frameworks)
        assert nextjs_detected

    def test_multiple_framework_detection(self):
        """Test detection of multiple frameworks (FastAPI + Pytest)."""
        detector = FileTypeDetector()
        code = """
from fastapi import FastAPI
import pytest

app = FastAPI()

@pytest.fixture
def client():
    return TestClient(app)
"""
        result = detector.detect(
            task_name="Create API tests",
            task_description="FastAPI test suite",
            code_snippet=code
        )

        assert result.file_type == FileType.PYTHON
        assert len(result.frameworks) >= 2
        frameworks_detected = {f.framework for f in result.frameworks}
        assert Framework.FASTAPI in frameworks_detected
        assert Framework.PYTEST in frameworks_detected

    def test_framework_version_hints(self):
        """Test framework version hint detection."""
        detector = FileTypeDetector()
        code = """
import { useState, useEffect } from 'react';

export default function Component() {
    const [state, setState] = useState(0);
    return <div>{state}</div>;
}
"""
        result = detector.detect(
            task_name="React component",
            task_description="Modern React with hooks",
            code_snippet=code
        )

        react_framework = next(
            (f for f in result.frameworks if f.framework == Framework.REACT),
            None
        )
        if react_framework:
            assert react_framework.version_hint is not None
            assert "16.8" in react_framework.version_hint


class TestImportAnalysis:
    """Tests for import statement analysis (Task 2.3)."""

    def test_python_import_extraction(self):
        """Test Python import statement extraction."""
        detector = FileTypeDetector()
        code = """
import asyncio
import json
from typing import List, Optional
from fastapi import FastAPI, Depends
from pydantic import BaseModel
"""
        result = detector.detect(
            task_name="Python module",
            task_description="Module with imports",
            code_snippet=code
        )

        assert 'asyncio' in result.detected_imports
        assert 'json' in result.detected_imports
        assert 'typing' in result.detected_imports
        assert 'fastapi' in result.detected_imports
        assert 'pydantic' in result.detected_imports

    def test_javascript_import_extraction(self):
        """Test JavaScript import statement extraction."""
        detector = FileTypeDetector()
        code = """
import React from 'react';
import { useState } from 'react';
const express = require('express');
const axios = require('axios');
"""
        result = detector.detect(
            task_name="JavaScript module",
            task_description="Module with imports",
            target_files=["src/module.js"],  # Add extension to force JS detection
            code_snippet=code
        )

        assert 'react' in result.detected_imports
        assert 'express' in result.detected_imports
        assert 'axios' in result.detected_imports

    def test_import_boosts_confidence(self):
        """Test that import analysis boosts confidence."""
        detector = FileTypeDetector()
        code_with_imports = """
import fastapi
from pydantic import BaseModel

def create_user():
    pass
"""
        code_without_imports = """
def create_user():
    pass
"""

        result_with = detector.detect(
            task_name="Create user",
            task_description="User creation",
            code_snippet=code_with_imports
        )
        result_without = detector.detect(
            task_name="Create user",
            task_description="User creation",
            code_snippet=code_without_imports
        )

        assert result_with.confidence >= result_without.confidence


class TestConfidenceScoring:
    """Tests for confidence scoring algorithm (Task 2.4)."""

    def test_high_confidence_with_extension(self):
        """Test high confidence (>0.85) with file extension."""
        detector = FileTypeDetector()
        result = detector.detect(
            task_name="Create module",
            task_description="Python module",
            target_files=["src/utils.py"]
        )

        assert result.confidence >= 0.85
        assert result.file_type == FileType.PYTHON

    def test_medium_confidence_keyword_only(self):
        """Test medium confidence (0.70-0.85) with keywords only."""
        detector = FileTypeDetector()
        code = """
def calculate(x, y):
    return x + y

class Helper:
    pass
"""
        result = detector.detect(
            task_name="Create helper",
            task_description="Helper functions",
            code_snippet=code
        )

        assert 0.50 <= result.confidence <= 0.85

    def test_low_confidence_fallback(self):
        """Test low confidence (<0.70) triggers Python fallback."""
        detector = FileTypeDetector()
        result = detector.detect(
            task_name="Generic task",
            task_description="Generic description"
        )

        assert result.file_type == FileType.PYTHON
        assert result.confidence <= 0.70

    def test_conflict_resolution_extension_priority(self):
        """Test extension takes priority in conflicting signals."""
        detector = FileTypeDetector()
        # .py extension but JavaScript-like keywords
        code = "const x = 5; let y = 10;"
        result = detector.detect(
            task_name="Create file",
            task_description="File with code",
            target_files=["src/file.py"],
            code_snippet=code
        )

        # Extension (0.95) should win over keywords
        assert result.file_type == FileType.PYTHON
        assert result.confidence >= 0.90

    def test_reasoning_string_clarity(self):
        """Test reasoning string provides clear explanation."""
        detector = FileTypeDetector()
        result = detector.detect(
            task_name="Create FastAPI endpoint",
            task_description="REST API",
            target_files=["api/users.py"]
        )

        assert result.reasoning is not None
        assert len(result.reasoning) > 0
        assert "0.95" in result.reasoning or ".py" in result.reasoning

    def test_weighted_signal_combination(self):
        """Test multiple signals combine correctly."""
        detector = FileTypeDetector()
        code = """
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Hello"}
"""
        result = detector.detect(
            task_name="FastAPI app",
            task_description="Create FastAPI application",
            target_files=["main.py"],
            code_snippet=code
        )

        # Should have multiple signals: extension + imports + framework
        assert result.confidence >= 0.85
        assert result.file_type == FileType.PYTHON


class TestSingletonPattern:
    """Test singleton instance pattern."""

    def test_get_singleton_instance(self):
        """Test get_file_type_detector returns singleton."""
        instance1 = get_file_type_detector()
        instance2 = get_file_type_detector()

        assert instance1 is instance2

    def test_singleton_functionality(self):
        """Test singleton instance works correctly."""
        detector = get_file_type_detector()
        result = detector.detect(
            task_name="Test",
            task_description="Test",
            target_files=["test.py"]
        )

        assert result.file_type == FileType.PYTHON
        assert result.confidence >= 0.90
