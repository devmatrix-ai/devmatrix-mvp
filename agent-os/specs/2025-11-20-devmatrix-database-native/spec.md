# DevMatrix Database-Native Transformation Specification

## Overview

Transform DevMatrix into a database-native system that behaves like agent-os, replacing markdown file storage with enterprise databases (PostgreSQL, Neo4j, Qdrant) while maintaining the same workflow patterns and task hierarchy.

## ⚠️ IMPORTANT: Development Branch Strategy

**ALL DEVELOPMENT MUST BE IN A FEATURE BRANCH:**
```bash
# Create and work in feature branch
git checkout main
git pull origin main
git checkout -b feature/devmatrix-database-native

# Regular commits during development
git add .
git commit -m "feat: implement DatabaseContext with enriched context"

# When ready, create PR to merge to main
git push origin feature/devmatrix-database-native
# Then create PR in GitHub/GitLab
```

**NEVER commit directly to main branch**

## Goals

1. **Database-Native Architecture**: Replace all markdown storage with databases
2. **Agent-OS Workflow Compatibility**: Maintain task hierarchy and execution patterns
3. **Scalable Orchestration**: Support parallel execution with dependency management
4. **Pattern Learning**: Leverage Qdrant for semantic pattern reuse
5. **Real-Time Monitoring**: Database-driven progress tracking

## Non-Goals

- Integration with agent-os codebase
- Markdown file generation
- Backward compatibility with file-based storage
- Migration of existing markdown specs

## Architecture

### Three-Database Strategy

#### PostgreSQL (Transactional Data)
- **Purpose**: ACID-compliant storage for specs, tasks, reports
- **Tables**:
  ```sql
  specs (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    content JSONB,
    status VARCHAR(50),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
  )

  tasks (
    id UUID PRIMARY KEY,
    spec_id UUID REFERENCES specs(id),
    parent_id UUID REFERENCES tasks(id),
    task_type VARCHAR(50), -- PHASE, TASK_GROUP, TASK, SUBTASK
    name VARCHAR(255),
    description TEXT,
    status VARCHAR(50),
    effort_estimate INTEGER,
    assigned_to VARCHAR(100),
    dependencies JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
  )

  reports (
    id UUID PRIMARY KEY,
    task_id UUID REFERENCES tasks(id),
    report_type VARCHAR(50),
    content JSONB,
    created_at TIMESTAMP
  )

  audit_log (
    id UUID PRIMARY KEY,
    entity_type VARCHAR(50),
    entity_id UUID,
    action VARCHAR(50),
    changes JSONB,
    user_id VARCHAR(100),
    timestamp TIMESTAMP
  )
  ```

#### Neo4j (Graph Dependencies)
- **Purpose**: Model and analyze task dependencies for orchestration
- **Schema**:
  ```cypher
  // Nodes
  (:Task {
    id: String,
    name: String,
    type: String,
    status: String,
    effort: Integer,
    phase: Integer
  })

  (:Skill {
    name: String,
    domain: String,
    description: String
  })

  (:Agent {
    name: String,
    specialization: String,
    capabilities: [String]
  })

  (:Wave {
    number: Integer,
    status: String
  })

  // Relationships
  (:Task)-[:DEPENDS_ON]->(:Task)
  (:Task)-[:REQUIRES_SKILL]->(:Skill)
  (:Task)-[:ASSIGNED_TO]->(:Agent)
  (:Task)-[:IN_WAVE]->(:Wave)
  (:Task)-[:PARENT_OF]->(:Task)
  ```

#### Qdrant (Semantic Search & Pattern Learning)
- **Purpose**: Store embeddings for similarity search and pattern reuse
- **Collections**:
  ```json
  {
    "task_embeddings": {
      "vectors": {
        "size": 768,
        "distance": "Cosine"
      },
      "payload": {
        "task_id": "string",
        "task_type": "string",
        "description": "text",
        "success_rate": "float"
      }
    },
    "code_patterns": {
      "vectors": {
        "size": 768,
        "distance": "Cosine"
      },
      "payload": {
        "pattern_type": "string",
        "language": "string",
        "framework": "string",
        "code": "text",
        "usage_count": "integer"
      }
    },
    "success_patterns": {
      "vectors": {
        "size": 768,
        "distance": "Cosine"
      },
      "payload": {
        "spec_type": "string",
        "task_sequence": "array",
        "success_metrics": "object"
      }
    }
  }
  ```

### Task Hierarchy

```
PHASE (1-5)
├── Planning & Analysis
├── Design & Architecture
├── Implementation
├── Testing & Validation
└── Deployment & Documentation

Task Group (Deliverable-focused)
├── Authentication System
├── API Endpoints
├── Database Models
└── Frontend Components

Task (Atomic unit of work)
├── Implement login endpoint
├── Create user model
└── Add JWT validation

Subtask (Implementation detail)
├── Define schema
├── Write validation logic
└── Add error handling
```

## Core Components

### 1. DatabaseContext (Foundation Layer)

**Purpose**: Enriched context retrieval from databases optimized for agent understanding

**IMPORTANT**: Context should be rich enough for agents (especially Haiku) to understand the full task requirements. Haiku can handle significant context, so we optimize for clarity over extreme minimization.

```python
class DatabaseContext:
    """Enriched context provider from PostgreSQL, Neo4j, Qdrant"""

    def __init__(self, spec_id: UUID):
        self.spec_id = spec_id
        self.pg_conn = PostgreSQLConnection()
        self.neo4j_conn = Neo4jConnection()
        self.qdrant_conn = QdrantConnection()
        self.cache = RedisCache()

    def get_enriched_context(self, task_id: UUID, context_level: str = 'standard') -> str:
        """
        Returns enriched context optimized for agent comprehension.

        Context Levels:
        - 'minimal': 2-3KB - Only for simple, well-defined tasks
        - 'standard': 5-8KB - Default, includes patterns, examples, and clear requirements
        - 'extended': 10-15KB - For complex tasks needing full context

        Includes (standard level):
        - Complete task details with acceptance criteria
        - Top 5 similar patterns with full code examples
        - All dependencies (completed and pending status)
        - Required skills with application guidelines
        - Parent task context for understanding bigger picture
        - Related tasks in same wave for coherence
        - Spec-level requirements and constraints
        - Tech stack and framework preferences

        Result: 5-8KB standard (vs 15-70KB full markdown)
        Token usage: Optimized but comprehensive
        Query time: <150ms (with Redis caching)
        """
        # Check cache first
        cache_key = f"context:{task_id}:{context_level}"
        if cached := self.cache.get(cache_key):
            return cached

        # Fetch comprehensive data from databases
        task = self.pg_conn.get_task(task_id)
        spec = self.pg_conn.get_spec(task.spec_id)
        patterns = self.qdrant_conn.find_top_patterns(task_id, limit=5, threshold=0.75)
        all_dependencies = self.neo4j_conn.get_all_dependencies(task_id)
        related_tasks = self.neo4j_conn.get_wave_siblings(task_id)
        skills = self.pg_conn.get_required_skills(task_id)
        parent_task = self.pg_conn.get_parent_task(task_id)

        # Build enriched context
        context = f"""
        ## Task Information
        Name: {task.name}
        Type: {task.type}
        Phase: {task.phase}
        Priority: {task.priority}

        ## Description
        {task.description}

        ## Acceptance Criteria
        {task.acceptance_criteria}

        ## Parent Context
        Parent Task: {parent_task.name if parent_task else 'Root level task'}
        Parent Goal: {parent_task.description[:200] if parent_task else 'N/A'}

        ## Spec Requirements
        Project: {spec.title}
        Tech Stack: {spec.tech_stack}
        Constraints: {', '.join(spec.constraints)}

        ## Required Skills and Standards
        {self._format_skills_with_guidelines(skills)}

        ## Dependencies Status
        Completed:
        {self._format_dependencies(all_dependencies['completed'])}

        Pending (for awareness):
        {self._format_dependencies(all_dependencies['pending'])}

        ## Related Tasks in Current Wave
        {self._format_related_tasks(related_tasks)}

        ## Similar Successful Patterns (Top 5)
        {self._format_patterns_detailed(patterns)}

        ## Expected Output Format
        {task.expected_output}

        ## Implementation Guidelines
        - Follow the patterns from similar successful tasks
        - Apply all required skills and standards
        - Ensure compatibility with completed dependencies
        - Consider impact on pending dependencies
        - Maintain consistency with related tasks in wave
        """

        # Cache for 10 minutes (longer for richer context)
        self.cache.set(cache_key, context, ttl=600)
        return context

    def get_task_with_dependencies(self, task_id: UUID) -> Dict:
        """Full task data with dependency graph"""
        return {
            'task': self.pg_conn.get_task(task_id),
            'dependencies': self.neo4j_conn.get_dependency_graph(task_id),
            'dependents': self.neo4j_conn.get_dependent_tasks(task_id),
            'parent': self.pg_conn.get_parent_task(task_id)
        }

    def get_similar_patterns(self, task_id: UUID, limit: int = 3) -> List[Pattern]:
        """Retrieve top-K similar patterns from Qdrant"""
        task = self.pg_conn.get_task(task_id)
        embedding = self._generate_embedding(task.description)
        return self.qdrant_conn.search_similar(
            collection="code_patterns",
            vector=embedding,
            limit=limit,
            threshold=0.8
        )

    def _format_patterns(self, patterns: List[Pattern]) -> str:
        """Format patterns for context inclusion"""
        formatted = []
        for i, pattern in enumerate(patterns, 1):
            formatted.append(f"{i}. Similarity: {pattern.similarity:.2f}")
            formatted.append(f"   Type: {pattern.type}")
            formatted.append(f"   Code: {pattern.code[:200]}...")
            formatted.append(f"   Success Rate: {pattern.success_rate:.1%}")
        return "\n".join(formatted)
```

### 2. GraphOrchestrator (Orchestration Engine)

**Purpose**: Neo4j-based wave generation and parallel execution planning

```python
class GraphOrchestrator:
    """Wave-based parallel task orchestration using Neo4j graph analysis"""

    def __init__(self):
        self.neo4j = Neo4jConnection()
        self.pg = PostgreSQLConnection()

    def import_tasks_to_graph(self, spec_id: UUID) -> None:
        """
        Import PostgreSQL tasks into Neo4j graph for dependency analysis

        Creates:
        - Task nodes with properties
        - DEPENDS_ON relationships
        - REQUIRES_SKILL relationships
        - PARENT_OF relationships
        """
        tasks = self.pg.get_all_tasks(spec_id)

        with self.neo4j.session() as session:
            for task in tasks:
                # Create task node
                session.run("""
                    CREATE (t:Task {
                        id: $id,
                        spec_id: $spec_id,
                        name: $name,
                        type: $type,
                        status: $status,
                        effort: $effort,
                        phase: $phase
                    })
                """, **task.dict())

                # Create dependency relationships
                for dep_id in task.dependencies:
                    session.run("""
                        MATCH (t:Task {id: $task_id})
                        MATCH (d:Task {id: $dep_id})
                        CREATE (t)-[:DEPENDS_ON]->(d)
                    """, task_id=task.id, dep_id=dep_id)

                # Create skill requirements
                for skill in task.required_skills:
                    session.run("""
                        MATCH (t:Task {id: $task_id})
                        MERGE (s:Skill {name: $skill_name})
                        CREATE (t)-[:REQUIRES_SKILL]->(s)
                    """, task_id=task.id, skill_name=skill)

    def generate_execution_waves(self, spec_id: UUID) -> List[Wave]:
        """
        Generate execution waves using Cypher graph analysis

        Algorithm:
        1. Find tasks with no dependencies → Wave 0
        2. Iteratively find tasks whose dependencies are in earlier waves
        3. Group by wave number for parallel execution

        Returns: List of Wave objects with parallel tasks
        Performance: <500ms for graphs with 1000+ tasks
        """
        with self.neo4j.session() as session:
            result = session.run("""
                // Wave 0: Tasks with no dependencies
                MATCH (t:Task {spec_id: $spec_id})
                WHERE NOT (t)-[:DEPENDS_ON]->()
                RETURN t.id as task_id, 0 as wave

                UNION

                // Subsequent waves: Tasks whose dependencies are resolved
                MATCH path = (t:Task {spec_id: $spec_id})-[:DEPENDS_ON*]->(d:Task)
                WHERE NOT (t)-[:DEPENDS_ON]->(:Task)-[:DEPENDS_ON*]->()
                WITH t, max(length(path)) as max_depth
                RETURN t.id as task_id, max_depth as wave

                ORDER BY wave
            """, spec_id=spec_id)

            # Group tasks by wave
            waves_dict = {}
            for record in result:
                wave_num = record["wave"]
                task_id = record["task_id"]
                if wave_num not in waves_dict:
                    waves_dict[wave_num] = []
                waves_dict[wave_num].append(task_id)

            # Create Wave objects
            waves = []
            for wave_num, task_ids in sorted(waves_dict.items()):
                tasks = [self.pg.get_task(tid) for tid in task_ids]
                waves.append(Wave(
                    number=wave_num,
                    tasks=tasks,
                    status='pending'
                ))

            return waves

    def execute_wave(self, wave: Wave, context: DatabaseContext) -> WaveResult:
        """
        Execute all tasks in a wave concurrently

        Uses ThreadPoolExecutor with max 5 concurrent agents
        Each agent receives minimal context from DatabaseContext
        Results stored in PostgreSQL immediately
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        # Assign agents to tasks based on skills
        assignments = self._assign_agents_to_tasks(wave.tasks)

        results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {}

            # Submit all tasks in parallel
            for task, agent in assignments.items():
                minimal_context = context.get_minimal_context(task.id)
                future = executor.submit(
                    self._execute_single_task,
                    task=task,
                    agent=agent,
                    context=minimal_context
                )
                futures[future] = task

            # Collect results as they complete
            for future in as_completed(futures):
                task = futures[future]
                try:
                    result = future.result(timeout=300)  # 5 min timeout
                    results.append(result)

                    # Update PostgreSQL immediately
                    self.pg.update_task_status(task.id, result.status)
                    self.pg.save_task_output(task.id, result.code)

                except Exception as e:
                    results.append(TaskResult(
                        task_id=task.id,
                        status='failed',
                        error=str(e)
                    ))

        return WaveResult(
            wave_number=wave.number,
            tasks_executed=len(results),
            successes=sum(1 for r in results if r.status == 'completed'),
            failures=sum(1 for r in results if r.status == 'failed'),
            results=results
        )

    def _assign_agents_to_tasks(self, tasks: List[Task]) -> Dict[Task, Agent]:
        """Assign specialized agents based on required skills"""
        assignments = {}
        for task in tasks:
            # Match agent to task based on skills
            if 'backend-api' in task.required_skills:
                agent = BackendAPIAgent()
            elif 'frontend-components' in task.required_skills:
                agent = FrontendAgent()
            elif 'backend-models' in task.required_skills:
                agent = DatabaseAgent()
            else:
                agent = GeneralistAgent()

            assignments[task] = agent

        return assignments

    def _execute_single_task(self, task: Task, agent: Agent, context: str) -> TaskResult:
        """Execute a single task with an agent"""
        return agent.execute(task=task, context=context)
```

### 3. HybridCodeGenerator (Code Generation Engine)

**Purpose**: Combines DevMatrix CodeGenerationService with agent-os patterns

```python
class HybridCodeGenerator:
    """
    Intelligent code generation combining:
    - Existing CodeGenerationService for structured tasks (API, MODEL, CRUD)
    - Direct agent execution for generic tasks
    - Pattern matching from Qdrant
    - Skills framework validation
    """

    def __init__(self):
        self.code_gen_service = CodeGenerationService()  # DevMatrix existing
        self.pattern_store = SemanticPatternStore()      # Qdrant
        self.skill_framework = SkillsFramework()         # Agent-OS skills
        self.llm_client = LLMClient()

    async def generate_code_for_task(
        self,
        task: Task,
        context: DatabaseContext
    ) -> CodeGenerationResult:
        """
        Main generation method with hybrid approach

        Process:
        1. Search for similar patterns in Qdrant
        2. Identify applicable skills
        3. Build enhanced prompt
        4. Route to appropriate generator (CodeGenService vs Agent)
        5. Validate with skills framework
        6. Store successful patterns

        Returns: Generated code with metadata
        """

        # 1. Fetch similar patterns from Qdrant
        similar_patterns = await self.pattern_store.find_similar(
            task=task,
            limit=3,
            threshold=0.8
        )

        # 2. Map applicable skills from framework
        applicable_skills = self.skill_framework.map_task_to_skills(task)

        # 3. Build enhanced prompt with patterns and skills
        enhanced_prompt = self._build_enhanced_prompt(
            task=task,
            patterns=similar_patterns,
            skills=applicable_skills,
            context=context.get_minimal_context(task.id)
        )

        # 4. Route to appropriate generator
        if task.type in ['API', 'MODEL', 'CRUD']:
            # Use existing CodeGenerationService for structured tasks
            spec_requirements = self._task_to_requirements(task)
            code = await self.code_gen_service.generate_from_requirements(
                spec_requirements=spec_requirements,
                spec_content=enhanced_prompt,
                use_patterns=True
            )
        else:
            # Use direct agent execution for generic tasks
            code = await self.llm_client.generate(
                prompt=enhanced_prompt,
                temperature=0.2,
                max_tokens=4000
            )

        # 5. Validate and enhance with skills
        for skill in applicable_skills:
            validation_result = self.skill_framework.validate_with_skill(
                code=code,
                skill=skill
            )
            if not validation_result.passed:
                # Apply skill standards to fix issues
                code = self.skill_framework.apply_skill_standards(code, skill)

        # 6. If successful, store pattern in Qdrant
        if self._validate_code(code):
            await self.pattern_store.store_success_pattern(
                task=task,
                code=code,
                success_metrics={'validation_passed': True}
            )

        return CodeGenerationResult(
            code=code,
            task_id=task.id,
            patterns_used=len(similar_patterns),
            skills_applied=len(applicable_skills),
            validation_passed=True
        )

    def _build_enhanced_prompt(
        self,
        task: Task,
        patterns: List[Pattern],
        skills: List[Skill],
        context: str
    ) -> str:
        """Build enhanced prompt with patterns and skills"""
        prompt_parts = [
            f"# Task: {task.name}",
            f"Type: {task.type}",
            f"\n## Description",
            task.description,
            f"\n## Context",
            context,
            f"\n## Applicable Skills",
            "Apply the following quality standards:",
        ]

        for skill in skills:
            prompt_parts.append(f"- {skill.name}: {skill.description}")

        if patterns:
            prompt_parts.append(f"\n## Similar Successful Patterns")
            prompt_parts.append("Reference these proven patterns:")
            for i, pattern in enumerate(patterns, 1):
                prompt_parts.append(f"\n### Pattern {i} (Similarity: {pattern.similarity:.2%})")
                prompt_parts.append(f"```{pattern.language}")
                prompt_parts.append(pattern.code)
                prompt_parts.append("```")

        prompt_parts.append(f"\n## Requirements")
        prompt_parts.append("Generate production-ready code that:")
        prompt_parts.append("- Follows all applicable skill standards")
        prompt_parts.append("- Incorporates patterns from similar successful tasks")
        prompt_parts.append("- Includes proper error handling and validation")
        prompt_parts.append("- Is well-documented and maintainable")

        return "\n".join(prompt_parts)

    def _task_to_requirements(self, task: Task) -> SpecRequirements:
        """Convert Task to SpecRequirements for CodeGenerationService"""
        return SpecRequirements(
            title=task.name,
            description=task.description,
            requirements=[
                Requirement(
                    type=task.type,
                    description=task.description,
                    priority='high'
                )
            ],
            tech_stack=task.tech_stack or {},
            constraints=task.constraints or []
        )

    def _validate_code(self, code: str) -> bool:
        """Basic code validation"""
        return (
            len(code) > 50 and
            'def ' in code or 'class ' in code or 'function ' in code
        )
```

### 4. DatabaseTaskManager
```python
class DatabaseTaskManager:
    def create_spec(spec_content: Dict) -> UUID
    def create_task_hierarchy(spec_id: UUID, tasks: List[Task]) -> None
    def update_task_status(task_id: UUID, status: str) -> None
    def get_pending_tasks() -> List[Task]
    def get_task_dependencies(task_id: UUID) -> List[Task]
```

### 5. SemanticPatternStore
```python
class SemanticPatternStore:
    def store_task_embedding(task: Task) -> None
    def find_similar_tasks(task: Task, threshold: float) -> List[Task]
    def store_success_pattern(spec_id: UUID, metrics: Dict) -> None
    def get_recommended_patterns(spec_type: str) -> List[Pattern]
```

### 6. SkillsFramework
```python
class SkillsFramework:
    def map_task_to_skills(task: Task) -> List[Skill]
    def validate_with_skill(task: Task, skill: Skill) -> ValidationResult
    def apply_skill_standards(code: str, skill: Skill) -> str
    def get_skill_metrics(skill: Skill) -> SkillMetrics
```

### 7. TaskExecutor
```python
class TaskExecutor:
    def execute_task(task: Task) -> TaskResult
    def execute_wave(wave: Wave) -> WaveResult
    def handle_task_failure(task: Task, error: Exception) -> None
    def retry_task(task: Task, strategy: RetryStrategy) -> TaskResult
```

### 8. ProgressMonitor
```python
class ProgressMonitor:
    def get_spec_progress(spec_id: UUID) -> ProgressReport
    def get_wave_status(wave: int) -> WaveStatus
    def get_agent_workload() -> Dict[Agent, List[Task]]
    def generate_dashboard_data() -> DashboardData
```

## Workflows

### Spec Processing Workflow
1. Parse spec → Store in PostgreSQL
2. Generate task hierarchy → Store in PostgreSQL
3. Import tasks to Neo4j graph
4. Analyze dependencies → Generate waves
5. Store task embeddings in Qdrant
6. Find similar patterns → Optimize execution
7. Execute waves in parallel
8. Track progress in PostgreSQL
9. Store success patterns in Qdrant

### Task Execution Workflow
1. Get next wave from Neo4j
2. Retrieve parallel tasks
3. Assign agents based on skills
4. Execute tasks concurrently
5. Update status in PostgreSQL
6. Log to audit trail
7. Store results and patterns
8. Trigger next wave

### Pattern Learning Workflow
1. Complete task successfully
2. Generate embedding for task
3. Store in Qdrant with metadata
4. On new task, search similar patterns
5. Reuse successful approaches
6. Track pattern effectiveness
7. Promote high-value patterns

## Skills Mapping

### Agent-OS Skills → Database Model

| Skill | Domain | Storage | Application |
|-------|---------|---------|------------|
| frontend-responsive | UI | Neo4j node | Task assignment |
| global-coding-style | Quality | PostgreSQL rules | Validation |
| backend-models | Database | Neo4j relationships | Dependency |
| backend-migrations | Database | PostgreSQL versions | Tracking |
| frontend-components | UI | Qdrant patterns | Reuse |
| testing-test-writing | Testing | PostgreSQL metrics | Coverage |
| global-validation | Security | Neo4j constraints | Enforcement |
| global-commenting | Docs | PostgreSQL standards | Compliance |
| global-conventions | Standards | All databases | Consistency |
| backend-queries | Database | Qdrant optimization | Performance |
| frontend-accessibility | UI | PostgreSQL checks | Validation |
| global-error-handling | Reliability | Neo4j flows | Resilience |
| backend-api | API | Neo4j endpoints | Mapping |
| global-tech-stack | Architecture | PostgreSQL config | Compatibility |
| frontend-css | UI | Qdrant styles | Consistency |

## Integration Points

### With Existing DevMatrix Pipeline

Detailed integration showing how database-native architecture fits into the 10-phase pipeline:

```python
class DevMatrixDatabaseNativeOrchestrator:
    """Complete integration with DevMatrix 10-phase pipeline"""

    async def process_spec_end_to_end(self, spec_content: str) -> ExecutionResult:
        """
        Full E2E execution with database-native architecture

        Phases 1-10 enhanced with database storage and wave-based orchestration
        """

        # PHASE 1: Spec Ingestion
        spec_parser = SpecParser()
        spec_data = spec_parser.parse(spec_content)

        # Store in PostgreSQL (NEW)
        spec_id = self.db_manager.create_spec(spec_data)
        print(f"✅ Phase 1 Complete: Spec stored in PostgreSQL (ID: {spec_id})")

        # PHASE 2: Requirements Analysis
        classifier = RequirementsClassifier()
        classified_reqs = classifier.classify(spec_data)

        # Store requirements in PostgreSQL (NEW)
        self.db_manager.store_requirements(spec_id, classified_reqs)
        print(f"✅ Phase 2 Complete: Requirements classified and stored")

        # PHASE 3: Multi-Pass Planning
        # Generate task hierarchy (agent-os style)
        task_hierarchy_builder = TaskHierarchyBuilder()
        task_hierarchy = task_hierarchy_builder.build(classified_reqs)

        # Store in PostgreSQL with parent-child relationships (NEW)
        self.db_manager.create_task_hierarchy(spec_id, task_hierarchy)
        print(f"✅ Phase 3 Complete: {len(task_hierarchy)} tasks created in database")

        # PHASE 4: Atomization
        # Tasks already atomic from Phase 3
        print(f"✅ Phase 4 Complete: Tasks are atomic units")

        # PHASE 5: DAG Construction (NEW - Neo4j Wave Analysis)
        graph_orchestrator = GraphOrchestrator()

        # Import tasks to Neo4j
        graph_orchestrator.import_tasks_to_graph(spec_id)

        # Generate execution waves using Cypher
        waves = graph_orchestrator.generate_execution_waves(spec_id)
        print(f"✅ Phase 5 Complete: {len(waves)} execution waves generated")
        print(f"   Wave breakdown: {[len(w.tasks) for w in waves]} tasks per wave")

        # PHASE 6: Code Generation (NEW - Wave-based Parallel Execution)
        hybrid_generator = HybridCodeGenerator()
        context = DatabaseContext(spec_id)

        for wave in waves:
            print(f"\n🌊 Executing Wave {wave.number} with {len(wave.tasks)} parallel tasks")

            # Execute wave with parallel agents
            wave_result = graph_orchestrator.execute_wave(wave, context)

            print(f"   ✅ Wave {wave.number}: {wave_result.successes} succeeded, "
                  f"{wave_result.failures} failed")

            # For each successful task, store pattern in Qdrant (NEW)
            for result in wave_result.results:
                if result.status == 'completed':
                    await self.pattern_store.store_success_pattern(
                        task_id=result.task_id,
                        code=result.code,
                        metrics={'wave': wave.number}
                    )

        print(f"✅ Phase 6 Complete: All waves executed")

        # PHASE 6.5: Code Repair (if needed)
        compliance_validator = ComplianceValidator()
        compliance_score = compliance_validator.check_compliance(spec_id)

        if compliance_score < 0.8:
            print(f"⚠️  Compliance: {compliance_score:.1%} - Running repairs...")
            repair_orchestrator = CodeRepairOrchestrator()
            await repair_orchestrator.repair_low_compliance_tasks(spec_id)
            print(f"✅ Phase 6.5 Complete: Code repairs applied")
        else:
            print(f"✅ Phase 6.5 Skipped: Compliance {compliance_score:.1%} exceeds threshold")

        # PHASE 7-8: Validation & Deployment
        semantic_validator = SemanticValidator()
        validation_result = semantic_validator.validate_all_tasks(spec_id)

        # Store validation results in reports table (NEW)
        self.db_manager.store_validation_results(spec_id, validation_result)

        # Deploy to disk
        deployer = DiskDeployer()
        deployment_path = deployer.deploy_from_database(spec_id)
        print(f"✅ Phase 7-8 Complete: Validated and deployed to {deployment_path}")

        # PHASE 9: Health Check
        health_checker = HealthChecker()
        health_status = health_checker.verify_deployment(deployment_path)

        # Store health status in PostgreSQL (NEW)
        self.db_manager.store_health_check(spec_id, health_status)
        print(f"✅ Phase 9 Complete: Health check {health_status.status}")

        # PHASE 10: Learning (NEW - Enhanced Pattern Feedback)
        pattern_feedback = PatternFeedbackIntegration()

        # Update Qdrant patterns with execution metrics
        execution_metrics = self.db_manager.get_execution_metrics(spec_id)
        await pattern_feedback.learn_from_execution(
            spec_id=spec_id,
            metrics=execution_metrics,
            patterns_used=self.pattern_store.get_patterns_for_spec(spec_id)
        )

        # Update Neo4j with task performance data
        graph_orchestrator.update_task_performance(spec_id, execution_metrics)

        print(f"✅ Phase 10 Complete: Patterns updated in Qdrant and Neo4j")

        return ExecutionResult(
            spec_id=spec_id,
            deployment_path=deployment_path,
            validation_result=validation_result,
            health_status=health_status,
            total_waves=len(waves),
            total_tasks=sum(len(w.tasks) for w in waves)
        )
```

### Database Operation Mapping

| Pipeline Phase | PostgreSQL Operations | Neo4j Operations | Qdrant Operations |
|----------------|----------------------|------------------|-------------------|
| **1. Spec Ingestion** | INSERT specs | - | - |
| **2. Requirements Analysis** | INSERT requirements | - | - |
| **3. Multi-Pass Planning** | INSERT tasks (hierarchy) | - | - |
| **4. Atomization** | UPDATE tasks (atomic flag) | - | - |
| **5. DAG Construction** | SELECT tasks | CREATE nodes + relationships | - |
| **5. Wave Generation** | - | MATCH dependency paths | - |
| **6. Code Generation** | UPDATE tasks (status, output) | UPDATE node status | SEARCH similar patterns |
| **6. Pattern Storage** | - | - | INSERT successful patterns |
| **6.5. Code Repair** | UPDATE tasks (repaired code) | - | - |
| **7. Validation** | INSERT reports | - | - |
| **8. Deployment** | UPDATE specs (deployed path) | - | - |
| **9. Health Check** | INSERT health_checks | - | - |
| **10. Learning** | SELECT execution metrics | UPDATE performance data | UPDATE pattern metrics |

### Context Strategy Comparison

#### Agent-OS Approach (Full Markdown)
```yaml
Context Size: 15-70KB per agent invocation
Source: Complete spec.md + tasks.md files
Token Usage: HIGH (full document parsing)
Query Time: N/A (file read)
Caching: File system cache only
```

#### DevMatrix Database-Native (Minimal Optimized)
```yaml
Context Size: 2-3KB per agent invocation
Source: Targeted database queries
Token Usage: LOW (30-50% reduction)
Query Time: <100ms (with Redis cache)
Caching: Redis + query result caching
```

**Example Context Breakdown**:
```python
# Full Markdown (Agent-OS)
Total Size: ~50KB
- spec.md: 20KB (entire spec)
- tasks.md: 25KB (all tasks)
- Current task: 5KB (embedded in markdown)

# Minimal Database (DevMatrix)
Total Size: ~2.5KB
- Task details: 0.5KB (name, type, description)
- Top 3 patterns: 1.5KB (code snippets from Qdrant)
- Dependencies: 0.3KB (completed tasks only)
- Skills: 0.2KB (required skills list)

# Savings: 95% size reduction, 30-50% token reduction
```

### API Endpoints
```python
POST   /api/specs                    # Create new spec
GET    /api/specs/{id}/tasks        # Get task hierarchy
POST   /api/tasks/{id}/execute      # Execute specific task
GET    /api/tasks/{id}/status       # Get task status
GET    /api/waves/current            # Get current wave
POST   /api/orchestration/analyze   # Analyze dependencies
GET    /api/patterns/similar        # Find similar patterns
GET    /api/progress/{spec_id}      # Get progress report
```

## Testing Strategy

### Unit Tests
- DatabaseTaskManager CRUD operations
- GraphOrchestrator wave generation
- SemanticPatternStore similarity search
- SkillsFramework mapping logic

### Integration Tests
- PostgreSQL → Neo4j task import
- Neo4j → Qdrant pattern storage
- End-to-end spec processing
- Parallel wave execution

### Performance Tests
- Database query optimization
- Neo4j graph traversal speed
- Qdrant similarity search performance
- Concurrent task execution

## Success Metrics

1. **Performance**
   - Task query: <100ms
   - Wave analysis: <500ms
   - Pattern search: <200ms
   - Status update: <50ms

2. **Scalability**
   - Handle 1000+ tasks per spec
   - Support 10+ concurrent agents
   - Process 100+ specs/day

3. **Quality**
   - 90%+ pattern reuse rate
   - 95%+ task success rate
   - 100% audit trail coverage

4. **Compatibility**
   - Match agent-os task structure
   - Support all 17 skills
   - Enable parallel orchestration

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Database connection failures | Connection pooling, circuit breakers |
| Neo4j query performance | Query optimization, indexing |
| Qdrant embedding quality | Model fine-tuning, quality metrics |
| Data consistency | Transactions, eventual consistency |
| Schema evolution | Migration scripts, versioning |

## Timeline

- **Week 1**: Database schemas and connections
- **Week 2**: DatabaseTaskManager implementation
- **Week 3**: GraphOrchestrator and wave generation
- **Week 4**: SemanticPatternStore integration
- **Week 5**: SkillsFramework porting
- **Week 6**: TaskExecutor and monitoring
- **Week 7**: Integration testing
- **Week 8**: Performance optimization