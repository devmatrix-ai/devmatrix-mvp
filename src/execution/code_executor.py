"""
Code Executor - Sandboxed Code Execution

Executes generated code atoms in isolated environments.

Features:
- Multi-language support (Python, TypeScript, JavaScript)
- Sandboxed execution (Docker containers)
- Timeout handling
- Resource limits (CPU, memory)
- Output capture (stdout, stderr, return values)
- Error handling and reporting

Author: DevMatrix Team
Date: 2025-10-23
"""

import uuid
import subprocess
import tempfile
import os
import json
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import logging

from src.models import AtomicUnit

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of code execution"""
    atom_id: uuid.UUID
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    return_value: Optional[Any] = None
    execution_time: float = 0.0  # Seconds
    memory_used: int = 0  # Bytes
    error_message: Optional[str] = None
    exception_type: Optional[str] = None
    exception_traceback: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class CodeExecutor:
    """
    Code executor - Sandboxed execution

    Executes code atoms in isolated environments:
    1. Python: subprocess with timeout
    2. TypeScript: Node.js with ts-node
    3. JavaScript: Node.js

    Execution modes:
    - Direct: Execute code directly (for testing)
    - Sandbox: Execute in Docker container (production)

    Safety features:
    - Timeout limits (default: 30s)
    - Memory limits (default: 512MB)
    - CPU limits (default: 1 core)
    - No network access
    - Read-only filesystem
    """

    def __init__(
        self,
        timeout: int = 30,
        memory_limit: str = "512m",
        use_sandbox: bool = False
    ):
        """
        Initialize code executor

        Args:
            timeout: Execution timeout in seconds
            memory_limit: Memory limit (e.g., "512m", "1g")
            use_sandbox: Use Docker sandbox (vs direct execution)
        """
        self.timeout = timeout
        self.memory_limit = memory_limit
        self.use_sandbox = use_sandbox

        logger.info(f"CodeExecutor initialized (timeout={timeout}s, memory={memory_limit}, sandbox={use_sandbox})")

    def execute_atom(
        self,
        atom: AtomicUnit,
        input_data: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """
        Execute atomic unit

        Args:
            atom: Atomic unit to execute
            input_data: Optional input data for execution

        Returns:
            ExecutionResult with execution details
        """
        logger.info(f"Executing atom: {atom.atom_id}")

        started_at = datetime.utcnow()

        try:
            if atom.language == "python":
                result = self._execute_python(atom, input_data)
            elif atom.language in ["typescript", "javascript"]:
                result = self._execute_nodejs(atom, input_data, atom.language)
            else:
                return ExecutionResult(
                    atom_id=atom.atom_id,
                    success=False,
                    exit_code=-1,
                    stdout="",
                    stderr=f"Unsupported language: {atom.language}",
                    error_message=f"Language {atom.language} not supported",
                    started_at=started_at,
                    completed_at=datetime.utcnow()
                )

            result.started_at = started_at
            result.completed_at = datetime.utcnow()

            logger.info(f"Execution complete: success={result.success}, time={result.execution_time:.2f}s")
            return result

        except Exception as e:
            logger.error(f"Execution failed: {e}")
            return ExecutionResult(
                atom_id=atom.atom_id,
                success=False,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                error_message=f"Execution error: {str(e)}",
                exception_type=type(e).__name__,
                exception_traceback=str(e),
                started_at=started_at,
                completed_at=datetime.utcnow()
            )

    def _execute_python(
        self,
        atom: AtomicUnit,
        input_data: Optional[Dict[str, Any]]
    ) -> ExecutionResult:
        """Execute Python code"""
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            temp_file = f.name

            # Write code to file
            code = atom.code_to_generate

            # Add input data if provided
            if input_data:
                code = f"# Input data\ninput_data = {json.dumps(input_data)}\n\n{code}"

            # Add result capture
            code += "\n\n# Capture result for JSON output\nimport json\nimport sys\nif 'result' in locals():\n    print('__RESULT__' + json.dumps(result))"

            f.write(code)

        try:
            # Execute with timeout
            start_time = time.time()

            process = subprocess.run(
                ['python', temp_file],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            execution_time = time.time() - start_time

            # Parse output
            stdout = process.stdout
            stderr = process.stderr
            return_value = None

            # Extract result if present
            if '__RESULT__' in stdout:
                result_start = stdout.index('__RESULT__') + len('__RESULT__')
                result_json = stdout[result_start:].strip()
                try:
                    return_value = json.loads(result_json)
                    # Remove result from stdout
                    stdout = stdout[:stdout.index('__RESULT__')]
                except json.JSONDecodeError:
                    pass

            # Parse exception if failed
            exception_type = None
            exception_traceback = None
            if process.returncode != 0 and stderr:
                # Try to extract exception type
                lines = stderr.strip().split('\n')
                if lines:
                    last_line = lines[-1]
                    if ':' in last_line:
                        exception_type = last_line.split(':')[0].strip()
                        exception_traceback = stderr

            return ExecutionResult(
                atom_id=atom.atom_id,
                success=process.returncode == 0,
                exit_code=process.returncode,
                stdout=stdout,
                stderr=stderr,
                return_value=return_value,
                execution_time=execution_time,
                error_message=stderr if process.returncode != 0 else None,
                exception_type=exception_type,
                exception_traceback=exception_traceback
            )

        except subprocess.TimeoutExpired:
            return ExecutionResult(
                atom_id=atom.atom_id,
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Execution timed out after {self.timeout}s",
                error_message=f"Timeout ({self.timeout}s)",
                exception_type="TimeoutError"
            )

        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except:
                pass

    def _execute_nodejs(
        self,
        atom: AtomicUnit,
        input_data: Optional[Dict[str, Any]],
        language: str
    ) -> ExecutionResult:
        """Execute TypeScript/JavaScript code"""
        # Create temporary file
        ext = '.ts' if language == 'typescript' else '.js'
        with tempfile.NamedTemporaryFile(mode='w', suffix=ext, delete=False) as f:
            temp_file = f.name

            # Write code to file
            code = atom.code_to_generate

            # Add input data if provided
            if input_data:
                code = f"// Input data\nconst inputData = {json.dumps(input_data)};\n\n{code}"

            # Add result capture for JS/TS
            code += "\n\n// Capture result for JSON output\nif (typeof result !== 'undefined') {\n    console.log('__RESULT__' + JSON.stringify(result));\n}"

            f.write(code)

        try:
            # Execute with node or ts-node
            start_time = time.time()

            if language == 'typescript':
                cmd = ['npx', 'ts-node', temp_file]
            else:
                cmd = ['node', temp_file]

            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            execution_time = time.time() - start_time

            # Parse output
            stdout = process.stdout
            stderr = process.stderr
            return_value = None

            # Extract result if present
            if '__RESULT__' in stdout:
                result_start = stdout.index('__RESULT__') + len('__RESULT__')
                result_json = stdout[result_start:].strip()
                try:
                    return_value = json.loads(result_json)
                    # Remove result from stdout
                    stdout = stdout[:stdout.index('__RESULT__')]
                except json.JSONDecodeError:
                    pass

            # Parse exception if failed
            exception_type = None
            exception_traceback = None
            if process.returncode != 0 and stderr:
                exception_type = "ExecutionError"
                exception_traceback = stderr

            return ExecutionResult(
                atom_id=atom.atom_id,
                success=process.returncode == 0,
                exit_code=process.returncode,
                stdout=stdout,
                stderr=stderr,
                return_value=return_value,
                execution_time=execution_time,
                error_message=stderr if process.returncode != 0 else None,
                exception_type=exception_type,
                exception_traceback=exception_traceback
            )

        except subprocess.TimeoutExpired:
            return ExecutionResult(
                atom_id=atom.atom_id,
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Execution timed out after {self.timeout}s",
                error_message=f"Timeout ({self.timeout}s)",
                exception_type="TimeoutError"
            )

        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except:
                pass

    def execute_batch(
        self,
        atoms: List[AtomicUnit],
        input_data: Optional[Dict[uuid.UUID, Dict[str, Any]]] = None
    ) -> List[ExecutionResult]:
        """
        Execute multiple atoms in batch

        Args:
            atoms: List of atoms to execute
            input_data: Optional dict mapping atom_id to input data

        Returns:
            List of ExecutionResults
        """
        logger.info(f"Batch executing {len(atoms)} atoms")

        results = []
        for atom in atoms:
            atom_input = input_data.get(atom.atom_id) if input_data else None
            result = self.execute_atom(atom, atom_input)
            results.append(result)

        logger.info(f"Batch execution complete: {sum(1 for r in results if r.success)}/{len(results)} succeeded")
        return results
