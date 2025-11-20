# DevMatrix + Agent-OS Integration Blueprint

**Date**: 2025-11-20
**Objective**: Integrate Agent-OS architecture INTO DevMatrix pipeline WITHOUT commands
**Approach**: Native pipeline integration with agent-os task structure

---

## 🎯 EXECUTIVE SUMMARY

Transform DevMatrix pipeline to natively generate and execute agent-os style masterplans:
- **Input**: Markdown spec → **Output**: Implemented code with tasks.md tracking
- **No commands needed**: Everything runs through the 10-phase pipeline
- **Task-driven execution**: Generate tasks.md → execute task-by-task
- **Skills integration**: Apply standards during generation
- **Orchestration support**: Parallel execution via DAG waves

---

## 📐 INTEGRATION ARCHITECTURE

### Current DevMatrix Pipeline (10 Phases)
```
1. Spec Ingestion → 2. Requirements Analysis → 3. Multi-Pass Planning
→ 4. Atomization → 5. DAG Construction → 6. Code Generation
→ 6.5. Code Repair → 7. Validation → 8. Deployment → 9. Health → 10. Learning
```

### Enhanced Pipeline with Agent-OS Integration
```
1. SPEC INGESTION++ (spec-shaper + spec-writer logic)
2. REQUIREMENTS ANALYSIS++ (domain → skills mapping)
3. TASK PLANNING (tasks.md generation)
4. TASK ATOMIZATION (break tasks into subtasks)
5. ORCHESTRATION (orchestration.yml + DAG)
6. TASK EXECUTION (task-by-task generation)
6.5. TASK REPAIR (per-task compliance)
7. TASK VERIFICATION (implementation-verifier logic)
8-10. [Unchanged]
```

---

## 🔄 PHASE-BY-PHASE TRANSFORMATION

### PHASE 1: Spec Ingestion → Spec Ingestion++

**Current**: Parses markdown, extracts entities/endpoints/requirements
**Enhanced**: Add agent-os spec structure generation

```python
class EnhancedSpecParser(SpecParser):
    """
    Extended parser that generates agent-os compatible outputs
    """

    def parse(self, spec_path: Path) -> SpecRequirements:
        # 1. Original parsing
        spec_requirements = super().parse(spec_path)

        # 2. Generate agent-os structure
        self._create_agent_os_structure(spec_requirements)

        # 3. Shape requirements (spec-shaper logic)
        self._shape_requirements(spec_requirements)

        # 4. Write formal spec (spec-writer logic)
        self._write_formal_spec(spec_requirements)

        return spec_requirements

    def _create_agent_os_structure(self, spec_requirements):
        """Create agent-os folder structure"""
        date = datetime.now().strftime("%Y-%m-%d")
        spec_name = self._generate_kebab_name(spec_requirements)

        base_path = Path(f"agent-os/specs/{date}-{spec_name}")
        base_path.mkdir(parents=True, exist_ok=True)

        # Create subfolders
        (base_path / "planning").mkdir(exist_ok=True)
        (base_path / "planning/visuals").mkdir(exist_ok=True)
        (base_path / "implementation").mkdir(exist_ok=True)
        (base_path / "verifications").mkdir(exist_ok=True)

        # Save raw spec
        raw_idea_path = base_path / "planning/raw-idea.md"
        raw_idea_path.write_text(spec_requirements.metadata.get('original_spec', ''))

        spec_requirements.metadata['agent_os_path'] = str(base_path)

    def _shape_requirements(self, spec_requirements):
        """Extract requirements Q&A style (spec-shaper logic)"""
        requirements_doc = []

        # Generate clarifying questions and infer answers from spec
        questions = [
            ("What is the primary goal?", self._extract_goal(spec_requirements)),
            ("Who are the target users?", self._extract_users(spec_requirements)),
            ("What are the core features?", self._extract_features(spec_requirements)),
            ("What existing code can be reused?", self._search_reusable_patterns()),
            ("Are there visual designs?", self._check_visual_assets()),
            ("What are the technical constraints?", self._extract_constraints(spec_requirements)),
            ("What is out of scope?", self._extract_out_of_scope(spec_requirements)),
            ("What are the success criteria?", self._extract_success_criteria(spec_requirements))
        ]

        for i, (question, answer) in enumerate(questions, 1):
            requirements_doc.append(f"**{i}. {question}**")
            requirements_doc.append(f"   {answer}")
            requirements_doc.append("")

        # Save requirements.md
        req_path = Path(spec_requirements.metadata['agent_os_path']) / "planning/requirements.md"
        req_path.write_text("\n".join(requirements_doc))

    def _write_formal_spec(self, spec_requirements):
        """Generate formal spec.md (spec-writer logic)"""
        spec_doc = []

        spec_doc.append(f"# {spec_requirements.metadata.get('spec_name', 'API Specification')}")
        spec_doc.append("")
        spec_doc.append("## Goal")
        spec_doc.append(self._extract_goal(spec_requirements))
        spec_doc.append("")

        spec_doc.append("## User Stories")
        for story in self._generate_user_stories(spec_requirements):
            spec_doc.append(f"- {story}")
        spec_doc.append("")

        spec_doc.append("## Core Requirements")
        for req in spec_requirements.requirements:
            if req.type == "functional":
                spec_doc.append(f"- **{req.id}**: {req.description}")
        spec_doc.append("")

        spec_doc.append("## Reusable Components")
        for component in self._search_reusable_patterns():
            spec_doc.append(f"- {component}")
        spec_doc.append("")

        spec_doc.append("## Technical Approach")
        spec_doc.append(self._generate_technical_approach(spec_requirements))
        spec_doc.append("")

        spec_doc.append("## Out of Scope")
        spec_doc.append(self._extract_out_of_scope(spec_requirements))
        spec_doc.append("")

        spec_doc.append("## Success Criteria")
        for criteria in self._extract_success_criteria(spec_requirements):
            spec_doc.append(f"- {criteria}")

        # Save spec.md
        spec_path = Path(spec_requirements.metadata['agent_os_path']) / "spec.md"
        spec_path.write_text("\n".join(spec_doc))
```

---

### PHASE 2: Requirements Analysis → Requirements Analysis++

**Current**: Classifies requirements by domain
**Enhanced**: Map domains to skills and standards

```python
class EnhancedRequirementsClassifier(RequirementsClassifier):
    """
    Extended classifier with skills mapping
    """

    DOMAIN_TO_SKILLS_MAP = {
        'crud': ['backend-api', 'backend-models', 'global-validation'],
        'authentication': ['backend-api', 'global-validation', 'global-error-handling'],
        'payment': ['backend-api', 'global-validation', 'global-error-handling'],
        'workflow': ['backend-models', 'backend-queries', 'global-conventions'],
        'search': ['backend-queries', 'backend-api', 'global-validation'],
        'custom': ['global-coding-style', 'global-conventions']
    }

    def classify(self, requirements: List[Requirement]) -> Dict[str, Any]:
        # 1. Original classification
        classified = super().classify(requirements)

        # 2. Map to skills
        skills_needed = set()
        for req in requirements:
            domain = req.domain  # Already classified
            skills_needed.update(self.DOMAIN_TO_SKILLS_MAP.get(domain, []))

        # 3. Load standards for each skill
        standards = {}
        for skill in skills_needed:
            standard_path = Path(f"agent-os/standards/{self._get_standard_path(skill)}")
            if standard_path.exists():
                standards[skill] = standard_path.read_text()

        classified['skills'] = list(skills_needed)
        classified['standards'] = standards

        return classified

    def _get_standard_path(self, skill: str) -> str:
        """Map skill name to standard file path"""
        skill_paths = {
            'global-coding-style': 'global/coding-style.md',
            'global-commenting': 'global/commenting.md',
            'global-conventions': 'global/conventions.md',
            'global-error-handling': 'global/error-handling.md',
            'global-validation': 'global/validation.md',
            'backend-api': 'backend/api.md',
            'backend-models': 'backend/models.md',
            'backend-queries': 'backend/queries.md',
            'backend-migrations': 'backend/migrations.md',
            'frontend-components': 'frontend/components.md',
            'frontend-css': 'frontend/css.md',
            'frontend-responsive': 'frontend/responsive.md',
            'frontend-accessibility': 'frontend/accessibility.md',
            'testing-test-writing': 'testing/test-writing.md'
        }
        return skill_paths.get(skill, f'{skill}.md')
```

---

### PHASE 3: Multi-Pass Planning → Task Planning

**Current**: Creates DAG from requirements
**Enhanced**: Generate tasks.md with agent-os hierarchy

```python
class TaskPlanGenerator:
    """
    Generates tasks.md in agent-os format
    Replaces MultiPassPlanner for task generation
    """

    def generate_tasks(self,
                      spec_requirements: SpecRequirements,
                      classified_requirements: Dict) -> str:
        """
        Generate tasks.md with full hierarchy
        """
        tasks_doc = []

        # Header
        tasks_doc.append(f"# Task Breakdown: {spec_requirements.metadata['spec_name']}")
        tasks_doc.append("")
        tasks_doc.append(f"**Total Estimated Effort**: {self._estimate_total_effort(spec_requirements)} hours")
        tasks_doc.append(f"**Priority**: P0 Critical")
        tasks_doc.append(f"**Generated**: {datetime.now().isoformat()}")
        tasks_doc.append("")

        # Group requirements into phases
        phases = self._group_into_phases(spec_requirements, classified_requirements)

        # Generate each phase
        for phase_num, phase in enumerate(phases):
            tasks_doc.extend(self._generate_phase(phase_num, phase))

        # Save tasks.md
        tasks_path = Path(spec_requirements.metadata['agent_os_path']) / "tasks.md"
        tasks_path.write_text("\n".join(tasks_doc))

        # Also return for pipeline
        return "\n".join(tasks_doc)

    def _group_into_phases(self, spec_requirements, classified_requirements):
        """Group requirements into execution phases"""
        phases = []

        # Phase 0: Setup (if needed)
        if self._needs_setup(spec_requirements):
            phases.append({
                'name': 'Setup & Preparation',
                'effort': 2,
                'task_groups': [
                    self._create_setup_task_group(spec_requirements)
                ]
            })

        # Phase 1: Core Implementation
        core_groups = []

        # Group by entity
        for entity in spec_requirements.entities:
            core_groups.append({
                'name': f'{entity.name} Implementation',
                'effort': self._estimate_entity_effort(entity),
                'dependencies': [],
                'tasks': self._create_entity_tasks(entity, classified_requirements)
            })

        # Group by endpoint
        endpoint_groups = self._group_endpoints(spec_requirements.endpoints)
        for group_name, endpoints in endpoint_groups.items():
            core_groups.append({
                'name': f'{group_name} Endpoints',
                'effort': self._estimate_endpoints_effort(endpoints),
                'dependencies': self._get_endpoint_dependencies(endpoints),
                'tasks': self._create_endpoint_tasks(endpoints, classified_requirements)
            })

        phases.append({
            'name': 'Core Implementation',
            'effort': sum(g['effort'] for g in core_groups),
            'task_groups': core_groups
        })

        # Phase 2: Integration & Testing
        phases.append({
            'name': 'Integration & Testing',
            'effort': self._estimate_testing_effort(spec_requirements),
            'task_groups': [
                self._create_testing_task_group(spec_requirements)
            ]
        })

        return phases

    def _generate_phase(self, phase_num: int, phase: Dict) -> List[str]:
        """Generate markdown for a phase"""
        lines = []

        # Phase header
        lines.append(f"## PHASE {phase_num} - {phase['name']} ({phase['effort']} hours)")
        lines.append("")

        # Task groups
        for group_num, task_group in enumerate(phase['task_groups'], 1):
            lines.extend(self._generate_task_group(phase_num, group_num, task_group))

        return lines

    def _generate_task_group(self, phase_num: int, group_num: int, task_group: Dict) -> List[str]:
        """Generate markdown for a task group"""
        lines = []

        # Task group header
        lines.append(f"### Task Group {phase_num}.{group_num}: {task_group['name']}")
        lines.append("")

        # Dependencies
        if task_group.get('dependencies'):
            lines.append(f"**Dependencies**: {', '.join(task_group['dependencies'])}")
            lines.append("")

        # Effort
        lines.append(f"**Effort**: {task_group['effort']} hours")
        lines.append("")

        # Tasks
        for task_num, task in enumerate(task_group['tasks'], 1):
            lines.append(f"#### Task {phase_num}.{group_num}.{task_num}: {task['name']} ({task['effort']}h)")
            lines.append("")

            # Subtasks
            for subtask_num, subtask in enumerate(task['subtasks'], 1):
                lines.append(f"- [ ] {phase_num}.{group_num}.{task_num}.{subtask_num} {subtask['description']}")

                # Sub-bullets
                for bullet in subtask.get('bullets', []):
                    lines.append(f"  - {bullet}")

            lines.append("")

            # Acceptance criteria
            lines.append("**Acceptance Criteria**:")
            for criteria in task['acceptance_criteria']:
                lines.append(f"- ✅ {criteria}")
            lines.append("")

            # Unit tests
            lines.append("**Unit Tests** (2-8 focused tests):")
            for test in task['unit_tests']:
                lines.append(f"- {test}")
            lines.append("")

        return lines

    def _create_entity_tasks(self, entity: Entity, classified_requirements: Dict) -> List[Dict]:
        """Create tasks for an entity"""
        tasks = []

        # Task 1: Model Implementation
        tasks.append({
            'name': f'Implement {entity.name} Model',
            'effort': 2,
            'subtasks': [
                {
                    'description': f'Create {entity.name} Pydantic model',
                    'bullets': [
                        f'Define fields: {", ".join(f.name for f in entity.fields)}',
                        'Add field validators for constraints',
                        'Implement relationships if needed'
                    ]
                },
                {
                    'description': 'Add validation rules',
                    'bullets': [
                        f'Implement {v.field} validation: {v.rule}'
                        for v in entity.validations
                    ]
                }
            ],
            'acceptance_criteria': [
                f'{entity.name} model has all required fields',
                'All validators working correctly',
                'Model serialization/deserialization works'
            ],
            'unit_tests': [
                f'test_{entity.name.lower()}_creation',
                f'test_{entity.name.lower()}_validation',
                f'test_{entity.name.lower()}_serialization'
            ]
        })

        # Task 2: Storage Implementation
        tasks.append({
            'name': f'Implement {entity.name} Storage',
            'effort': 1.5,
            'subtasks': [
                {
                    'description': f'Create storage for {entity.name}',
                    'bullets': [
                        'In-memory dict or database table',
                        'CRUD operations support',
                        'Thread-safe if needed'
                    ]
                }
            ],
            'acceptance_criteria': [
                'Storage initialized correctly',
                'CRUD operations working',
                'Data persistence verified'
            ],
            'unit_tests': [
                f'test_{entity.name.lower()}_storage_crud',
                f'test_{entity.name.lower()}_storage_persistence'
            ]
        })

        return tasks

    def _create_endpoint_tasks(self, endpoints: List[Endpoint], classified_requirements: Dict) -> List[Dict]:
        """Create tasks for endpoints"""
        tasks = []

        for endpoint in endpoints:
            task = {
                'name': f'Implement {endpoint.method} {endpoint.path}',
                'effort': 1.5,
                'subtasks': [
                    {
                        'description': f'Create {endpoint.method} route handler',
                        'bullets': [
                            f'Path: {endpoint.path}',
                            f'Operation: {endpoint.operation}',
                            'Request/response models',
                            'Error handling'
                        ]
                    }
                ],
                'acceptance_criteria': [
                    f'{endpoint.method} {endpoint.path} responds correctly',
                    f'Returns {endpoint.response.status_code} on success',
                    'Handles errors gracefully'
                ],
                'unit_tests': [
                    f'test_{endpoint.operation}_{endpoint.entity.lower()}',
                    f'test_{endpoint.operation}_{endpoint.entity.lower()}_errors'
                ]
            }

            # Add business logic if present
            if endpoint.business_logic:
                task['subtasks'].append({
                    'description': 'Implement business logic',
                    'bullets': endpoint.business_logic
                })

            tasks.append(task)

        return tasks
```

---

### PHASE 4: Atomization → Task Atomization

**Current**: Breaks DAG into atomic units
**Enhanced**: Break tasks.md into executable atoms

```python
class TaskAtomizer:
    """
    Atomize tasks.md into executable units
    """

    def atomize_tasks(self, tasks_content: str) -> List[Dict]:
        """
        Parse tasks.md and create atomic execution units
        """
        atoms = []
        task_parser = TaskParser(tasks_content)

        for phase in task_parser.get_phases():
            for task_group in phase['task_groups']:
                for task in task_group['tasks']:
                    atom = {
                        'id': self._generate_atom_id(phase, task_group, task),
                        'name': task['name'],
                        'type': 'task_implementation',
                        'phase': phase['number'],
                        'group': task_group['number'],
                        'task': task['number'],
                        'effort_hours': task['effort'],
                        'dependencies': task.get('dependencies', []),
                        'subtasks': task['subtasks'],
                        'acceptance_criteria': task['acceptance_criteria'],
                        'unit_tests': task['unit_tests'],
                        'skills': self._identify_skills(task),
                        'status': 'pending',
                        'implementation': None
                    }
                    atoms.append(atom)

        return atoms

    def _identify_skills(self, task: Dict) -> List[str]:
        """Identify which skills apply to this task"""
        skills = []

        task_text = str(task).lower()

        if 'model' in task_text or 'pydantic' in task_text:
            skills.append('backend-models')
        if 'endpoint' in task_text or 'route' in task_text:
            skills.append('backend-api')
        if 'validation' in task_text:
            skills.append('global-validation')
        if 'test' in task_text:
            skills.append('testing-test-writing')
        if 'storage' in task_text or 'database' in task_text:
            skills.append('backend-queries')

        # Always include global skills
        skills.extend(['global-coding-style', 'global-conventions'])

        return list(set(skills))
```

---

### PHASE 5: DAG Construction → Orchestration

**Current**: Builds execution DAG
**Enhanced**: Generate orchestration.yml + parallel waves

```python
class OrchestrationEngine:
    """
    Generate orchestration.yml and execution waves
    """

    def generate_orchestration(self, atoms: List[Dict]) -> Dict:
        """
        Create orchestration plan with agent assignments
        """
        # Group atoms by specialization
        groups = self._group_by_specialization(atoms)

        # Create orchestration.yml content
        orchestration = {
            'task_groups': [],
            'execution_waves': [],
            'estimated_duration': self._estimate_duration(atoms)
        }

        # Assign subagents to groups
        for group_name, group_atoms in groups.items():
            orchestration['task_groups'].append({
                'name': group_name,
                'claude_code_subagent': self._select_subagent(group_atoms),
                'atoms': [atom['id'] for atom in group_atoms],
                'estimated_hours': sum(atom['effort_hours'] for atom in group_atoms)
            })

        # Create execution waves (parallel groups)
        waves = self._create_execution_waves(atoms)
        orchestration['execution_waves'] = waves

        # Save orchestration.yml
        self._save_orchestration(orchestration)

        return orchestration

    def _group_by_specialization(self, atoms: List[Dict]) -> Dict[str, List]:
        """Group atoms by their primary skill domain"""
        groups = {}

        for atom in atoms:
            primary_skill = self._get_primary_skill(atom)

            if primary_skill.startswith('backend'):
                group = 'Backend Implementation'
            elif primary_skill.startswith('frontend'):
                group = 'Frontend Implementation'
            elif primary_skill == 'testing-test-writing':
                group = 'Testing Implementation'
            elif 'security' in atom['name'].lower():
                group = 'Security Implementation'
            else:
                group = 'General Implementation'

            if group not in groups:
                groups[group] = []
            groups[group].append(atom)

        return groups

    def _select_subagent(self, atoms: List[Dict]) -> str:
        """Select best subagent for atom group"""
        skills = set()
        for atom in atoms:
            skills.update(atom['skills'])

        # Map skills to subagents
        if 'backend-api' in skills or 'backend-models' in skills:
            return 'python-expert'
        elif 'frontend-components' in skills:
            return 'frontend-architect'
        elif 'testing-test-writing' in skills:
            return 'quality-engineer'
        elif 'global-validation' in skills and 'security' in str(atoms):
            return 'security-engineer'
        else:
            return 'python-expert'  # default

    def _create_execution_waves(self, atoms: List[Dict]) -> List[Dict]:
        """Create parallel execution waves respecting dependencies"""
        waves = []
        completed = set()
        remaining = atoms.copy()

        while remaining:
            # Find atoms that can execute (dependencies met)
            wave_atoms = []
            for atom in remaining:
                deps = set(atom['dependencies'])
                if deps.issubset(completed):
                    wave_atoms.append(atom)

            if not wave_atoms:
                # Deadlock - force sequential for remaining
                wave_atoms = remaining[:1]

            waves.append({
                'wave_number': len(waves) + 1,
                'parallel_atoms': [a['id'] for a in wave_atoms],
                'estimated_duration': max(a['effort_hours'] for a in wave_atoms)
            })

            # Update state
            for atom in wave_atoms:
                completed.add(atom['id'])
                remaining.remove(atom)

        return waves

    def _save_orchestration(self, orchestration: Dict):
        """Save orchestration.yml to agent-os structure"""
        import yaml

        # Assume spec path is in metadata
        spec_path = Path("agent-os/specs/[current-spec]/")
        orch_path = spec_path / "orchestration.yml"

        with open(orch_path, 'w') as f:
            yaml.dump(orchestration, f, default_flow_style=False)
```

---

### PHASE 6: Code Generation → Task Execution

**Current**: Generates all code at once
**Enhanced**: Execute task-by-task with skill awareness

```python
class TaskAwareCodeGenerator(CodeGenerationService):
    """
    Generate code task-by-task using tasks.md structure
    """

    def generate_from_tasks(self,
                           atoms: List[Dict],
                           spec_requirements: SpecRequirements,
                           orchestration: Dict) -> Dict[str, str]:
        """
        Generate code for each task atom
        """
        generated_code = {}
        implementation_reports = []

        # Execute by waves for parallel efficiency
        for wave in orchestration['execution_waves']:
            wave_results = []

            # Execute atoms in parallel (simulated)
            for atom_id in wave['parallel_atoms']:
                atom = self._get_atom_by_id(atoms, atom_id)

                # Generate code for this specific task
                code = self._generate_task_code(atom, spec_requirements)

                # Apply skill standards
                code = self._apply_skill_standards(code, atom['skills'])

                # Run unit tests
                test_results = self._run_task_tests(atom, code)

                # Update atom status
                atom['status'] = 'completed' if test_results['passed'] else 'failed'
                atom['implementation'] = code

                # Create implementation report
                report = self._create_implementation_report(atom, code, test_results)
                implementation_reports.append(report)

                # Store code
                if atom['status'] == 'completed':
                    file_name = self._determine_file_name(atom)
                    generated_code[file_name] = code

                # Update tasks.md with [x] marks
                self._update_tasks_md(atom, completed=test_results['passed'])

                wave_results.append({
                    'atom_id': atom_id,
                    'status': atom['status'],
                    'tests_passed': test_results['passed']
                })

            # Log wave completion
            logger.info(f"Wave {wave['wave_number']} complete", extra={'results': wave_results})

        # Save implementation reports
        self._save_implementation_reports(implementation_reports)

        return generated_code

    def _generate_task_code(self, atom: Dict, spec_requirements: SpecRequirements) -> str:
        """
        Generate code for a specific task atom
        """
        # Build task-specific prompt
        prompt = []

        prompt.append(f"# Task: {atom['name']}")
        prompt.append(f"# Phase {atom['phase']}, Group {atom['group']}, Task {atom['task']}")
        prompt.append("")

        prompt.append("## Subtasks to implement:")
        for subtask in atom['subtasks']:
            prompt.append(f"- {subtask['description']}")
            for bullet in subtask.get('bullets', []):
                prompt.append(f"  - {bullet}")
        prompt.append("")

        prompt.append("## Acceptance Criteria:")
        for criteria in atom['acceptance_criteria']:
            prompt.append(f"- {criteria}")
        prompt.append("")

        prompt.append("## Unit Tests to write:")
        for test in atom['unit_tests']:
            prompt.append(f"- {test}")
        prompt.append("")

        # Add relevant spec context
        prompt.append("## Spec Context:")

        # Find relevant entities/endpoints for this task
        task_entities = self._find_relevant_entities(atom, spec_requirements)
        task_endpoints = self._find_relevant_endpoints(atom, spec_requirements)

        if task_entities:
            prompt.append("### Relevant Entities:")
            for entity in task_entities:
                prompt.append(f"- {entity.name}: {', '.join(f.name for f in entity.fields)}")

        if task_endpoints:
            prompt.append("### Relevant Endpoints:")
            for endpoint in task_endpoints:
                prompt.append(f"- {endpoint.method} {endpoint.path}")

        prompt.append("")
        prompt.append("Generate COMPLETE code for this task including:")
        prompt.append("1. Implementation of all subtasks")
        prompt.append("2. Unit tests (2-8 focused tests)")
        prompt.append("3. Follow all acceptance criteria")

        prompt_text = "\n".join(prompt)

        # Call LLM
        response = self.llm_client.generate_with_caching(
            task_type="task_execution",
            complexity="medium",
            cacheable_context={"system_prompt": self._get_task_system_prompt()},
            variable_prompt=prompt_text,
            temperature=0.0,
            max_tokens=3000
        )

        return self._extract_code(response.get("content", ""))

    def _apply_skill_standards(self, code: str, skills: List[str]) -> str:
        """
        Apply skill-based standards to generated code
        """
        for skill in skills:
            standard_path = Path(f"agent-os/standards/{self._get_standard_path(skill)}")
            if standard_path.exists():
                standard = standard_path.read_text()

                # Apply standard rules (simplified)
                if skill == 'global-coding-style':
                    code = self._apply_coding_style(code, standard)
                elif skill == 'global-validation':
                    code = self._enhance_validation(code, standard)
                elif skill == 'backend-api':
                    code = self._apply_api_standards(code, standard)
                # ... more skill applications

        return code

    def _run_task_tests(self, atom: Dict, code: str) -> Dict:
        """
        Run the unit tests for this task
        """
        # Save code to temp file
        temp_file = Path(f"/tmp/task_{atom['id']}.py")
        temp_file.write_text(code)

        # Extract test names from code
        test_names = self._extract_test_names(code)

        # Run pytest on specific tests
        import subprocess
        result = subprocess.run(
            ["pytest", str(temp_file), "-v"],
            capture_output=True,
            text=True
        )

        # Parse results
        passed = result.returncode == 0
        test_output = result.stdout + result.stderr

        return {
            'passed': passed,
            'output': test_output,
            'tests_run': len(test_names),
            'tests_passed': test_output.count(" PASSED")
        }

    def _update_tasks_md(self, atom: Dict, completed: bool):
        """
        Update tasks.md with [x] marks for completed tasks
        """
        # Read current tasks.md
        tasks_path = Path("agent-os/specs/[current]/tasks.md")
        content = tasks_path.read_text()

        # Find the task line and mark with [x]
        task_id = f"{atom['phase']}.{atom['group']}.{atom['task']}"

        if completed:
            # Replace [ ] with [x]
            content = content.replace(f"[ ] {task_id}", f"[x] {task_id}")

        # Save updated tasks.md
        tasks_path.write_text(content)

    def _create_implementation_report(self, atom: Dict, code: str, test_results: Dict) -> str:
        """
        Create implementation report for this task
        """
        report = []

        report.append(f"# Implementation Report: {atom['name']}")
        report.append(f"**Date**: {datetime.now().isoformat()}")
        report.append(f"**Task ID**: {atom['id']}")
        report.append(f"**Status**: {atom['status']}")
        report.append("")

        report.append("## Subtasks Completed")
        for subtask in atom['subtasks']:
            report.append(f"- ✅ {subtask['description']}")
        report.append("")

        report.append("## Acceptance Criteria")
        for criteria in atom['acceptance_criteria']:
            status = "✅" if test_results['passed'] else "❌"
            report.append(f"- {status} {criteria}")
        report.append("")

        report.append("## Test Results")
        report.append(f"- Tests Run: {test_results['tests_run']}")
        report.append(f"- Tests Passed: {test_results['tests_passed']}")
        report.append(f"- Overall: {'PASSED' if test_results['passed'] else 'FAILED'}")
        report.append("")

        report.append("## Code Statistics")
        report.append(f"- Lines of Code: {len(code.splitlines())}")
        report.append(f"- Functions: {code.count('def ')}")
        report.append(f"- Classes: {code.count('class ')}")

        return "\n".join(report)
```

---

### PHASE 6.5: Code Repair → Task Repair

**Current**: Repairs entire codebase
**Enhanced**: Repair per-task with skill awareness

```python
class TaskAwareRepairAgent:
    """
    Repair code at task level
    """

    def repair_task(self,
                    atom: Dict,
                    compliance_report: ComplianceReport,
                    spec_requirements: SpecRequirements) -> str:
        """
        Repair a specific task's code
        """
        # Build repair context
        repair_context = []

        repair_context.append(f"# TASK REPAIR: {atom['name']}")
        repair_context.append("")
        repair_context.append("## Compliance Issues:")

        # Identify task-specific issues
        task_issues = self._identify_task_issues(atom, compliance_report)
        for issue in task_issues:
            repair_context.append(f"- {issue}")

        repair_context.append("")
        repair_context.append("## Skills to Apply:")
        for skill in atom['skills']:
            repair_context.append(f"- {skill}")

        repair_context.append("")
        repair_context.append("## Acceptance Criteria Not Met:")
        for criteria in atom['acceptance_criteria']:
            if not self._criteria_met(criteria, atom['implementation']):
                repair_context.append(f"- ❌ {criteria}")

        repair_context.append("")
        repair_context.append("## Current Implementation:")
        repair_context.append("```python")
        repair_context.append(atom['implementation'])
        repair_context.append("```")

        repair_context.append("")
        repair_context.append("Generate REPAIRED code that:")
        repair_context.append("1. Fixes all compliance issues")
        repair_context.append("2. Meets all acceptance criteria")
        repair_context.append("3. Follows skill standards")
        repair_context.append("4. Passes all unit tests")

        repair_prompt = "\n".join(repair_context)

        # Generate repair
        repaired_code = self.code_generator.generate_from_requirements(
            spec_requirements,
            repair_context=repair_prompt
        )

        return repaired_code
```

---

### PHASE 7: Validation → Task Verification

**Current**: Validates entire codebase
**Enhanced**: implementation-verifier logic per task

```python
class TaskVerificationEngine(ComplianceValidator):
    """
    Verify task implementation completeness
    Implements implementation-verifier agent logic
    """

    def verify_all_tasks(self,
                        atoms: List[Dict],
                        generated_code: Dict[str, str],
                        spec_requirements: SpecRequirements) -> Dict:
        """
        Complete task verification (implementation-verifier logic)
        """
        verification_report = {
            'timestamp': datetime.now().isoformat(),
            'spec_name': spec_requirements.metadata['spec_name'],
            'total_tasks': len(atoms),
            'tasks_completed': 0,
            'tasks_failed': 0,
            'test_results': {},
            'regressions': [],
            'quality_assessment': {}
        }

        # Step 1: Verify task completion
        for atom in atoms:
            if atom['status'] == 'completed':
                verification_report['tasks_completed'] += 1
            else:
                verification_report['tasks_failed'] += 1

        # Step 2: Update roadmap.md
        self._update_roadmap(spec_requirements)

        # Step 3: Run FULL test suite (not just new tests)
        test_results = self._run_full_test_suite()
        verification_report['test_results'] = test_results

        # Step 4: Detect regressions
        regressions = self._detect_regressions(test_results)
        verification_report['regressions'] = regressions

        # Step 5: Quality assessment
        quality = self._assess_quality(atoms, generated_code, test_results)
        verification_report['quality_assessment'] = quality

        # Step 6: Create final report
        self._create_final_verification_report(verification_report)

        # Step 7: Sign-off decision
        verification_report['sign_off'] = self._determine_sign_off(verification_report)

        return verification_report

    def _update_roadmap(self, spec_requirements: SpecRequirements):
        """Update roadmap.md with completed features"""
        roadmap_path = Path("agent-os/product/roadmap.md")
        if roadmap_path.exists():
            content = roadmap_path.read_text()

            # Find features from this spec
            spec_name = spec_requirements.metadata['spec_name']

            # Mark as completed
            content = content.replace(f"[ ] {spec_name}", f"[x] {spec_name}")

            # Add completion date
            today = datetime.now().strftime("%Y-%m-%d")
            content = content.replace(
                f"[x] {spec_name}",
                f"[x] {spec_name} ✅ Completed: {today}"
            )

            roadmap_path.write_text(content)

    def _run_full_test_suite(self) -> Dict:
        """Run entire test suite, not just new tests"""
        import subprocess

        # Run ALL tests
        result = subprocess.run(
            ["pytest", "-v", "--tb=short"],
            capture_output=True,
            text=True,
            cwd="/home/kwar/code/agentic-ai"
        )

        output = result.stdout + result.stderr

        # Parse results
        total_tests = output.count(" PASSED") + output.count(" FAILED")
        passed_tests = output.count(" PASSED")
        failed_tests = output.count(" FAILED")

        return {
            'total': total_tests,
            'passed': passed_tests,
            'failed': failed_tests,
            'pass_rate': passed_tests / total_tests if total_tests > 0 else 0,
            'output': output
        }

    def _detect_regressions(self, test_results: Dict) -> List[str]:
        """Detect any regressions from previous runs"""
        regressions = []

        # Load previous test results if available
        prev_results_path = Path("agent-os/test_results_baseline.json")
        if prev_results_path.exists():
            import json
            prev_results = json.loads(prev_results_path.read_text())

            # Compare
            if test_results['passed'] < prev_results.get('passed', 0):
                regressions.append(f"Test regression: {prev_results['passed']} → {test_results['passed']} passed")

            # Find specific failing tests that used to pass
            # (parse from output)

        return regressions

    def _assess_quality(self, atoms: List[Dict], code: Dict, test_results: Dict) -> Dict:
        """Comprehensive quality assessment"""
        return {
            'task_completion_rate': sum(1 for a in atoms if a['status'] == 'completed') / len(atoms),
            'test_pass_rate': test_results['pass_rate'],
            'code_coverage': self._estimate_coverage(code),
            'skill_compliance': self._check_skill_compliance(atoms, code),
            'acceptance_criteria_met': self._check_acceptance_criteria(atoms),
            'overall_score': self._calculate_quality_score(atoms, test_results)
        }

    def _create_final_verification_report(self, verification_report: Dict):
        """Create final-verification.md"""
        report = []

        report.append("# Final Verification Report")
        report.append(f"**Date**: {verification_report['timestamp']}")
        report.append(f"**Spec**: {verification_report['spec_name']}")
        report.append("")

        report.append("## Task Completion")
        report.append(f"- Total Tasks: {verification_report['total_tasks']}")
        report.append(f"- Completed: {verification_report['tasks_completed']} ✅")
        report.append(f"- Failed: {verification_report['tasks_failed']} ❌")
        report.append("")

        report.append("## Test Results")
        test_results = verification_report['test_results']
        report.append(f"- Total Tests: {test_results['total']}")
        report.append(f"- Passed: {test_results['passed']} ✅")
        report.append(f"- Failed: {test_results['failed']} ❌")
        report.append(f"- Pass Rate: {test_results['pass_rate']:.1%}")
        report.append("")

        if verification_report['regressions']:
            report.append("## ⚠️ REGRESSIONS DETECTED")
            for regression in verification_report['regressions']:
                report.append(f"- {regression}")
            report.append("")

        report.append("## Quality Assessment")
        quality = verification_report['quality_assessment']
        report.append(f"- Task Completion: {quality['task_completion_rate']:.1%}")
        report.append(f"- Test Pass Rate: {quality['test_pass_rate']:.1%}")
        report.append(f"- Code Coverage: {quality['code_coverage']:.1%}")
        report.append(f"- Skill Compliance: {quality['skill_compliance']:.1%}")
        report.append(f"- Acceptance Criteria: {quality['acceptance_criteria_met']:.1%}")
        report.append(f"- **Overall Score**: {quality['overall_score']:.1%}")
        report.append("")

        report.append("## Sign-Off")
        if verification_report['sign_off']:
            report.append("✅ **APPROVED FOR PRODUCTION**")
            report.append("All quality gates passed. Ready for deployment.")
        else:
            report.append("❌ **NOT READY FOR PRODUCTION**")
            report.append("Quality gates failed. See issues above.")

        # Save report
        report_path = Path(f"agent-os/specs/[current]/verifications/final-verification.md")
        report_path.parent.mkdir(exist_ok=True)
        report_path.write_text("\n".join(report))
```

---

## 🔧 IMPLEMENTATION PLAN

### Step 1: Extend Existing Components

1. **Extend SpecParser**
   - Add `EnhancedSpecParser` with agent-os structure creation
   - Generate planning/, requirements.md, spec.md

2. **Extend RequirementsClassifier**
   - Add `EnhancedRequirementsClassifier` with skills mapping
   - Load and apply standards

3. **Replace MultiPassPlanner**
   - Create `TaskPlanGenerator` for tasks.md generation
   - Use agent-os task hierarchy format

4. **Create TaskAtomizer**
   - Parse tasks.md into atomic units
   - Identify skills per task

5. **Create OrchestrationEngine**
   - Generate orchestration.yml
   - Create parallel execution waves

6. **Extend CodeGenerationService**
   - Add `TaskAwareCodeGenerator` for task-by-task generation
   - Apply skill standards
   - Run task-specific tests

7. **Create TaskAwareRepairAgent**
   - Repair at task level
   - Use skill context

8. **Create TaskVerificationEngine**
   - Implement implementation-verifier logic
   - Update roadmap
   - Run full test suite

### Step 2: Integration Points

```python
# In real_e2e_full_pipeline.py

async def run(self):
    # Phase 1: Enhanced spec parsing with agent-os structure
    spec_requirements = await self._phase_1_spec_ingestion_enhanced()

    # Phase 2: Requirements analysis with skills
    classified = await self._phase_2_requirements_analysis_enhanced()

    # Phase 3: Generate tasks.md instead of DAG
    tasks_content = await self._phase_3_task_planning()

    # Phase 4: Atomize tasks
    atoms = await self._phase_4_task_atomization(tasks_content)

    # Phase 5: Generate orchestration
    orchestration = await self._phase_5_orchestration(atoms)

    # Phase 6: Task-by-task execution
    generated_code = await self._phase_6_task_execution(atoms, orchestration)

    # Phase 6.5: Task-level repair if needed
    repaired_code = await self._phase_6_5_task_repair(atoms, generated_code)

    # Phase 7: Task verification (implementation-verifier)
    verification = await self._phase_7_task_verification(atoms, repaired_code)

    # Phase 8-10: Existing deployment, health, learning
    await self._phase_8_deployment(repaired_code)
    await self._phase_9_health_verification()
    await self._phase_10_learning()
```

### Step 3: Feature Flags

```python
# Configuration flags
USE_AGENT_OS_STRUCTURE = True  # Generate agent-os folders
USE_TASK_BASED_EXECUTION = True  # Execute task-by-task
USE_SKILL_STANDARDS = True  # Apply skill-based standards
USE_ORCHESTRATION = True  # Generate orchestration.yml
USE_TASK_VERIFICATION = True  # Use implementation-verifier logic
```

---

## 📊 BENEFITS OF INTEGRATION

### 1. **Better Task Tracking**
- tasks.md provides clear progress visibility
- [x] marks show exactly what's done
- Implementation reports per task

### 2. **Parallel Execution**
- orchestration.yml enables multi-agent work
- Specialized subagents for different domains
- Faster completion through parallelization

### 3. **Quality Standards**
- Skills framework ensures consistency
- Standards applied automatically
- Skill-specific validation

### 4. **Incremental Progress**
- Task-by-task execution allows partial completion
- Can pause and resume
- Clear checkpoints

### 5. **Better Testing**
- 2-8 focused tests per task (manageable)
- Full test suite at end (regression detection)
- Test results per task

### 6. **Complete Documentation**
- requirements.md captures all decisions
- spec.md documents what to build
- tasks.md shows how to build
- final-verification.md proves it works

---

## 🚀 NEXT STEPS

1. **Prototype Integration**
   - Start with EnhancedSpecParser
   - Test with simple_task_api.md

2. **Incremental Rollout**
   - Phase 1-3: Spec → Tasks generation
   - Phase 4-6: Task execution
   - Phase 7: Verification

3. **Testing Strategy**
   - Unit tests for each new component
   - Integration test with full pipeline
   - Compare with original pipeline results

4. **Performance Monitoring**
   - Measure task execution time
   - Track parallelization benefits
   - Monitor quality metrics

---

## 💡 KEY INSIGHTS

### The Magic Formula

```
Spec → Requirements → Tasks → Atoms → Orchestration → Parallel Execution → Verification
```

Each phase produces **concrete artifacts**:
- `requirements.md`: What users want
- `spec.md`: What to build
- `tasks.md`: How to build it
- `orchestration.yml`: Who builds what
- `implementation/`: Proof of building
- `final-verification.md`: Proof it works

### Why This Works

1. **Clarity**: Every decision documented
2. **Modularity**: Tasks are independent units
3. **Parallelization**: Multiple agents work simultaneously
4. **Quality**: Multiple verification gates
5. **Learning**: Patterns extracted and reused

### The DevMatrix Advantage

By integrating agent-os INTO DevMatrix:
- Keep existing pipeline benefits (repair, learning, metrics)
- Add agent-os benefits (tasks, skills, orchestration)
- No commands needed - all automatic
- Full observability and tracking
- Production-ready from day one

---

**This is the blueprint for seamless DevMatrix + Agent-OS integration!**