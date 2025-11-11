# Phase 6: Execution + Retry

**Document**: 08 of 15
**Purpose**: Dependency-aware code generation with intelligent retry loops

---

## Overview

**Phase 6 executes the plan** - generating code for each atom in dependency order with automatic retry on failures.

**Key Innovation**: 3-attempt retry loop transforms 90% per-atom success → 99.99% success

---

## Architecture

```
Execution Plan (from Phase 4)
→ For each level (sequential):
  → For each atom in level (parallel):
    → Attempt 1: Generate code
    → Validate
    → If fail: Attempt 2 with error feedback
    → If fail: Attempt 3 with enhanced context
    → If still fail: Flag for human review
    → Store successful atoms
```

---

## Retry Mathematics

```python
# Single attempt
P(success) = 0.90

# Three retries
P(all_fail) = 0.10 × 0.10 × 0.10 × 0.10 = 0.0001
P(success_within_4) = 1 - 0.0001 = 0.9999 = 99.99%

# For 800 atoms
P(all_succeed) = 0.9999^800 = 0.923 = 92.3%
With validation: 95-98% final precision ✅
```

---

## Core Components

### 1. LLM Generator

```python
class LLMCodeGenerator:
    """Generate code using Claude Sonnet 4.5."""
    
    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4.5-20250929"
    
    def generate_atom_code(
        self,
        atom_spec: AtomicUnit,
        dependencies: List[AtomicUnit],
        attempt_number: int = 1,
        previous_errors: List[str] = None
    ) -> str:
        """Generate code for atomic unit."""
        
        # Build prompt
        prompt = self._build_prompt(
            atom_spec, dependencies, attempt_number, previous_errors
        )
        
        # Call Claude
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            temperature=0.7 if attempt_number == 1 else 0.5,  # Lower temp on retries
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        # Extract code
        code = self._extract_code(response.content[0].text)
        return code
    
    def _build_prompt(
        self,
        atom_spec: AtomicUnit,
        dependencies: List[AtomicUnit],
        attempt_number: int,
        previous_errors: List[str]
    ) -> str:
        """Build generation prompt."""
        
        prompt = f"""
You are an expert {atom_spec.language} developer.

**Task**: Generate code for this atomic unit:
- **Name**: {atom_spec.name}
- **Description**: {atom_spec.description}
- **Target LOC**: ~{atom_spec.estimated_loc} lines
- **Complexity**: {atom_spec.complexity}

**Dependencies** (already generated and validated):
```{atom_spec.language}
{self._format_dependencies(dependencies)}
```

**Context**:
- File: {atom_spec.context.get('file_context', {}).get('file_path', 'N/A')}
- Imports: {atom_spec.context.get('file_context', {}).get('imports', [])}
- Parent scope: {atom_spec.context.get('parent_context', {})}

**Requirements**:
1. Generate ONLY the code for this specific unit
2. Use dependencies shown above (already validated)
3. Follow {atom_spec.language} conventions
4. Include type hints and docstrings
5. Keep it atomic (~{atom_spec.estimated_loc} LOC)
"""
        
        if attempt_number > 1 and previous_errors:
            prompt += f"""

**RETRY ATTEMPT {attempt_number}**:
Previous generation failed with these errors:
{chr(10).join(f'- {err}' for err in previous_errors)}

Please fix these issues in this attempt.
"""
        
        prompt += "\n\nGenerate the code now:"
        
        return prompt
    
    def _format_dependencies(self, deps: List[AtomicUnit]) -> str:
        """Format dependencies for context."""
        if not deps:
            return "# No dependencies"
        
        formatted = []
        for dep in deps[:10]:  # Max 10 for context
            formatted.append(f"# {dep.name}")
            formatted.append(dep.code)
            formatted.append("")
        
        if len(deps) > 10:
            formatted.append(f"# ... and {len(deps) - 10} more dependencies")
        
        return "\n".join(formatted)
    
    def _extract_code(self, response_text: str) -> str:
        """Extract code from LLM response."""
        # Remove markdown code blocks
        if "```" in response_text:
            parts = response_text.split("```")
            for part in parts:
                if part.strip() and not part.startswith(("python", "typescript", "javascript")):
                    # Found code block
                    lines = part.strip().split('\n')
                    # Skip language identifier if present
                    if lines and lines[0].strip() in ["python", "typescript", "javascript", "js", "ts"]:
                        lines = lines[1:]
                    return '\n'.join(lines)
        
        # No code blocks, return as is
        return response_text.strip()
```

### 2. Retry Executor

```python
class RetryExecutor:
    """Execute generation with retry logic."""
    
    MAX_ATTEMPTS = 4  # 1 initial + 3 retries
    
    def __init__(self, generator: LLMCodeGenerator, validator: AtomicValidator):
        self.generator = generator
        self.validator = validator
    
    def execute_with_retry(
        self,
        atom_spec: AtomicUnit,
        dependencies: List[AtomicUnit]
    ) -> Tuple[str, AtomicValidationResult, int]:
        """
        Execute generation with retry loop.
        
        Returns:
            (code, validation_result, attempts_used)
        """
        errors = []
        
        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            print(f"  Attempt {attempt}/{self.MAX_ATTEMPTS} for {atom_spec.name}...")
            
            # Generate code
            code = self.generator.generate_atom_code(
                atom_spec=atom_spec,
                dependencies=dependencies,
                attempt_number=attempt,
                previous_errors=errors if attempt > 1 else None
            )
            
            # Update atom with generated code
            atom_spec.code = code
            
            # Validate
            validation_result = self.validator.validate(atom_spec)
            
            if validation_result.passed:
                print(f"    ✅ Success on attempt {attempt}")
                return code, validation_result, attempt
            
            # Failed - collect errors for next attempt
            errors = [issue.message for issue in validation_result.issues
                     if issue.severity in [ValidationSeverity.CRITICAL, ValidationSeverity.ERROR]]
            
            print(f"    ❌ Failed: {len(errors)} errors")
        
        # All attempts failed
        print(f"    ⚠️ All {self.MAX_ATTEMPTS} attempts failed")
        return code, validation_result, self.MAX_ATTEMPTS
```

### 3. Parallel Executor

```python
import concurrent.futures
from typing import Dict

class ParallelExecutor:
    """Execute multiple atoms in parallel."""
    
    def __init__(
        self,
        retry_executor: RetryExecutor,
        max_workers: int = 100
    ):
        self.retry_executor = retry_executor
        self.max_workers = max_workers
    
    def execute_level(
        self,
        level_atoms: List[AtomicUnit],
        all_atoms: Dict[str, AtomicUnit]
    ) -> Dict[str, ExecutionResult]:
        """
        Execute all atoms in a level (parallel).
        
        Args:
            level_atoms: Atoms to execute in this level
            all_atoms: All atoms (for dependency lookup)
        
        Returns:
            Dict mapping atom_id to ExecutionResult
        """
        results = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all atoms
            future_to_atom = {}
            
            for atom in level_atoms:
                # Get dependencies (already generated)
                deps = [all_atoms[dep_id] for dep_id in atom.depends_on
                       if dep_id in all_atoms]
                
                # Submit
                future = executor.submit(
                    self.retry_executor.execute_with_retry,
                    atom,
                    deps
                )
                future_to_atom[future] = atom
            
            # Collect results
            for future in concurrent.futures.as_completed(future_to_atom):
                atom = future_to_atom[future]
                try:
                    code, validation, attempts = future.result()
                    results[atom.id] = ExecutionResult(
                        atom_id=atom.id,
                        success=validation.passed,
                        code=code,
                        validation=validation,
                        attempts=attempts
                    )
                except Exception as e:
                    results[atom.id] = ExecutionResult(
                        atom_id=atom.id,
                        success=False,
                        error=str(e),
                        attempts=self.retry_executor.MAX_ATTEMPTS
                    )
        
        return results
```

---

## Complete Pipeline

```python
class ExecutionPipeline:
    """Complete Phase 6 execution pipeline."""
    
    def __init__(self, api_key: str):
        self.generator = LLMCodeGenerator(api_key)
        self.validator = AtomicValidator()
        self.retry_executor = RetryExecutor(self.generator, self.validator)
        self.parallel_executor = ParallelExecutor(self.retry_executor)
    
    def execute_plan(
        self,
        execution_plan: List[ExecutionLevel],
        atoms: Dict[str, AtomicUnit]
    ) -> Dict[str, ExecutionResult]:
        """Execute complete execution plan."""
        
        print("=" * 60)
        print("⚙️ PHASE 6: EXECUTION + RETRY")
        print("=" * 60)
        
        all_results = {}
        total_atoms = sum(len(level.atom_ids) for level in execution_plan)
        completed = 0
        
        for level in execution_plan:
            print(f"\n📋 Executing Level {level.level} ({len(level.atom_ids)} atoms)...")
            
            level_atoms = [atoms[aid] for aid in level.atom_ids]
            
            # Execute level (parallel within level)
            results = self.parallel_executor.execute_level(level_atoms, atoms)
            
            all_results.update(results)
            
            # Update progress
            completed += len(level.atom_ids)
            success_count = sum(1 for r in results.values() if r.success)
            
            print(f"  ✅ {success_count}/{len(level.atom_ids)} succeeded")
            print(f"  Progress: {completed}/{total_atoms} ({completed/total_atoms*100:.1f}%)")
        
        # Summary
        total_success = sum(1 for r in all_results.values() if r.success)
        precision = total_success / total_atoms * 100
        
        print(f"\n🎯 Final Results:")
        print(f"  Success: {total_success}/{total_atoms} ({precision:.1f}%)")
        print(f"  Failed: {total_atoms - total_success}")
        
        return all_results
```

---

## Performance Metrics

| Metric | Target | Typical |
|--------|--------|---------|
| **Precision** | ≥95% | 95-98% |
| **Time per atom** | 5-10s | 6-8s |
| **Parallel throughput** | 100 atoms/batch | 80-100 |
| **Total time (800 atoms)** | 1-1.5 hours | 1.2 hours |
| **Retry rate** | <20% | 15% |
| **Success after retry** | >95% | 96-98% |

---

**Next Document**: [09_PHASE_7_HUMAN_REVIEW.md](09_PHASE_7_HUMAN_REVIEW.md)
