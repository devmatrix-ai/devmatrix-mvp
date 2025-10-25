# MGE V2 Critical Gaps - Implementation Workflow

**Version**: 1.0
**Created**: 2025-10-24
**Strategy**: Adaptive Multi-Track Parallel Implementation
**Duration**: 4-6 semanas (Weeks 12-14 extended)
**Team**: 3 engineers (Dany, Eng1, Eng2)
**Target**: 71% → ≥95% alignment | 87% → 98% precision

---

## 🎯 Executive Summary

### Current State Analysis

**Alignment Status**: 71% (10/14 checklist items complete)
**Precision**: 87.1% (MVP baseline)
**Blocking Items**: 4 critical gaps preventing 98% precision target

### Critical Path

```mermaid
graph TD
    A[Week 12: Critical Gaps] --> B[Week 13: Quality & Optimization]
    B --> C[Week 14: Integration & Production]

    A1[Gap 3: Acceptance Tests<br/>7-10 días] --> B1[Gap 2: Precision Score<br/>3-5 días]
    A2[Gap 8: Concurrency Controller<br/>4-5 días] --> C
    A3[Gap 9: Cost Guardrails<br/>3-4 días] --> B1

    B2[Gap 10: Caching<br/>5-6 días] --> C
    B3[Gap 11: Traceability<br/>4-5 días] --> C
    B4[Gap 5: Dependencies GT<br/>5-7 días] --> C

    style A1 fill:#ff6b6b
    style A2 fill:#ff6b6b
    style A3 fill:#ff6b6b
    style B2 fill:#ff6b6b
```

### Success Metrics

| Metric | Baseline | Target | Impact |
|--------|----------|--------|--------|
| **Alignment** | 71% | ≥95% | Production readiness |
| **Precision** | 87% | ≥98% | Quality target |
| **Cost** | ~$300 | <$200 | Budget compliance |
| **Time** | ~13h | <1.5h | Performance target |
| **Cache Hit Rate** | 0% | ≥60% | Cost/speed optimization |

---

## 📋 Gap Prioritization Matrix

### P0 CRITICAL (Blocking Production)

| Gap | Item | Status | Effort | Owner | Blocks |
|-----|------|--------|--------|-------|--------|
| **Gap 1** | Acceptance Tests (3) | 0% | 7-10d | Eng1+Eng2 | Items 2, 12 |
| **Gap 2** | Concurrency Controller (8) | 0% | 4-5d | Eng2 | Production stability |
| **Gap 3** | Cost Guardrails (9) | 0% | 3-4d | Dany | Budget compliance |
| **Gap 4** | Caching & Reuso (10) | 0% | 5-6d | Eng1 | Performance target |

**Total P0 Effort**: 19-25 días → **4-5 semanas with 3 engineers parallel**

### P1 HIGH (Quality & Optimization)

| Gap | Item | Status | Effort | Owner | Impact |
|-----|------|--------|--------|-------|--------|
| **Gap 5** | Precision Score (2) | 70% | 3-5d | Dany | Metrics completeness |
| **Gap 6** | Dependencies GT (5) | 80% | 5-7d | Eng2+Eng1 | Production reliability |
| **Gap 7** | Traceability E2E (11) | 40% | 4-5d | Dany | Debugging capability |

**Total P1 Effort**: 12-17 días → **2.5-3.5 semanas**

---

## 🚀 Week 12: Critical Gaps Implementation

**Goal**: Close all P0 gaps blocking production
**Duration**: 10 días (2 work weeks)
**Parallelization**: 3 independent tracks

### Track 1: Acceptance Tests (Gap 1) 🔴

**Owner**: Eng1 (lead) + Eng2 (TS/JS support)
**Duration**: 7-10 días
**Priority**: P0 CRITICAL (blocks Items 2, 12)

#### Architecture

```python
# Component Structure
src/testing/
├── acceptance_generator.py      # Test generation from masterplan
├── acceptance_runner.py          # Test execution engine
├── acceptance_gate.py            # Gate enforcement
├── parsers/
│   ├── requirement_parser.py    # Extract requirements from masterplan
│   ├── must_should_classifier.py # Classify requirement priority
│   └── test_template_engine.py  # Generate pytest/jest tests
└── models/
    ├── acceptance_test.py       # Test model
    └── test_result.py           # Result model
```

#### Tasks Breakdown

**Day 1-2: Requirements Parser & Classification**

```python
# Task 1.1: Requirement Parser (Eng1) - 1 día
class RequirementParser:
    def parse_masterplan(self, masterplan_id: UUID) -> List[Requirement]:
        """
        Parse masterplan description and extract requirements
        Support formats:
        - Natural language (NLP extraction)
        - Structured markdown (### MUST / ### SHOULD sections)
        - YAML frontmatter
        """
        masterplan = db.query(MasterPlan).get(masterplan_id)

        # Try structured format first
        if self._has_structured_requirements(masterplan.description):
            return self._parse_structured(masterplan.description)

        # Fall back to NLP extraction
        return self._parse_nlp(masterplan.description)

    def _parse_structured(self, description: str) -> List[Requirement]:
        """
        Parse markdown structure:

        ## Requirements
        ### MUST
        - User authentication must use JWT tokens
        - Password must be hashed with bcrypt

        ### SHOULD
        - UI should be responsive on mobile
        - Load time should be < 2s
        """
        requirements = []
        current_priority = None

        for line in description.split('\n'):
            if line.startswith('### MUST'):
                current_priority = 'must'
            elif line.startswith('### SHOULD'):
                current_priority = 'should'
            elif line.startswith('- ') and current_priority:
                req_text = line[2:].strip()
                requirements.append(Requirement(
                    text=req_text,
                    priority=current_priority,
                    masterplan_id=masterplan_id
                ))

        return requirements

# Task 1.2: Must/Should Classifier (Eng1) - 1 día
class MustShouldClassifier:
    def classify(self, requirement_text: str) -> str:
        """
        Classify requirement as 'must' or 'should' using:
        1. Keyword detection (must, shall, required vs should, could, optional)
        2. LLM classification for ambiguous cases
        3. Default to 'must' if uncertain (safer)
        """
        # Keyword-based classification
        must_keywords = ['must', 'shall', 'required', 'mandatory', 'critical']
        should_keywords = ['should', 'could', 'optional', 'nice to have', 'desirable']

        text_lower = requirement_text.lower()

        if any(kw in text_lower for kw in must_keywords):
            return 'must'
        elif any(kw in text_lower for kw in should_keywords):
            return 'should'

        # LLM classification for ambiguous
        return self._llm_classify(requirement_text)
```

**Unit Tests (Day 2)**:
- [ ] Test structured requirement parsing (markdown format)
- [ ] Test NLP extraction (plain text)
- [ ] Test must/should classification accuracy (>90%)
- [ ] Test edge cases (empty requirements, mixed formats)

---

**Day 3-5: Test Generation Engine**

```python
# Task 1.3: Test Template Engine (Eng1 - Python, Eng2 - TS/JS) - 3 días
class TestTemplateEngine:
    def generate_pytest_test(self, requirement: Requirement) -> str:
        """
        Generate pytest test from requirement

        Example:
        Requirement: "User authentication must use JWT tokens"

        Generated Test:
        ```python
        def test_authentication_uses_jwt_tokens():
            # Setup
            user = create_test_user()

            # Execute
            response = authenticate_user(user.email, user.password)

            # Assert
            assert 'access_token' in response
            token = response['access_token']
            decoded = jwt.decode(token, verify=False)
            assert decoded is not None
            assert 'user_id' in decoded
        ```
        """
        # Extract action and assertion from requirement text
        action, assertion = self._parse_requirement_components(requirement.text)

        # Generate test scaffolding
        test_code = self._generate_test_scaffolding(
            test_name=self._generate_test_name(requirement.text),
            setup=self._generate_setup(action),
            execute=self._generate_execution(action),
            assert_statement=self._generate_assertion(assertion)
        )

        return test_code

    def generate_jest_test(self, requirement: Requirement) -> str:
        """
        Generate Jest/Vitest test for TypeScript/JavaScript requirements

        Example:
        Requirement: "UI should be responsive on mobile"

        Generated Test:
        ```typescript
        describe('Responsive UI', () => {
          it('should render correctly on mobile viewport', () => {
            // Setup
            cy.viewport(375, 667) // iPhone viewport

            // Execute
            cy.visit('/')

            // Assert
            cy.get('[data-testid="mobile-menu"]').should('be.visible')
            cy.get('[data-testid="desktop-menu"]').should('not.be.visible')
          })
        })
        ```
        """
        # Similar logic for TS/JS tests
        pass

# Task 1.4: Database Schema (Eng1) - 1 día
class AcceptanceTest(Base):
    __tablename__ = "acceptance_tests"

    test_id = Column(UUID, primary_key=True, default=uuid4)
    masterplan_id = Column(UUID, ForeignKey("masterplans.masterplan_id"), nullable=False)
    requirement_id = Column(UUID, ForeignKey("requirements.requirement_id"), nullable=False)

    test_name = Column(String, nullable=False)
    test_code = Column(Text, nullable=False)
    test_language = Column(String, nullable=False)  # pytest, jest
    priority = Column(String, nullable=False)  # must, should

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    masterplan = relationship("MasterPlan", back_populates="acceptance_tests")
    requirement = relationship("Requirement", back_populates="tests")
    results = relationship("AcceptanceTestResult", back_populates="test")

class AcceptanceTestResult(Base):
    __tablename__ = "acceptance_test_results"

    result_id = Column(UUID, primary_key=True, default=uuid4)
    test_id = Column(UUID, ForeignKey("acceptance_tests.test_id"), nullable=False)
    wave_id = Column(UUID, ForeignKey("execution_waves.wave_id"), nullable=True)

    status = Column(String, nullable=False)  # passed, failed, skipped
    execution_time_ms = Column(Integer)
    error_message = Column(Text)
    stack_trace = Column(Text)

    executed_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    test = relationship("AcceptanceTest", back_populates="results")
    wave = relationship("ExecutionWave", back_populates="test_results")
```

**Unit Tests (Day 5)**:
- [ ] Test pytest generation for Python requirements
- [ ] Test jest generation for TS/JS requirements
- [ ] Test code correctness (syntax validation)
- [ ] Test database persistence

---

**Day 6-7: Test Execution Engine**

```python
# Task 1.5: Test Runner (Eng1 + Eng2) - 2 días
class AcceptanceTestRunner:
    def __init__(self):
        self.pytest_runner = PytestRunner()
        self.jest_runner = JestRunner()

    async def run_after_wave(self, wave_id: UUID) -> AcceptanceTestResult:
        """
        Execute all acceptance tests for atoms in completed wave

        Workflow:
        1. Get all atoms in wave
        2. Get all tests for masterplan
        3. Execute relevant tests
        4. Store results
        5. Return pass/fail summary
        """
        wave = db.query(ExecutionWave).get(wave_id)
        masterplan_id = wave.masterplan_id

        # Get all acceptance tests for this masterplan
        tests = db.query(AcceptanceTest).filter_by(
            masterplan_id=masterplan_id
        ).all()

        results = []
        for test in tests:
            result = await self._run_single_test(test)
            results.append(result)

        return AcceptanceTestResult(
            wave_id=wave_id,
            total_tests=len(tests),
            passed=len([r for r in results if r.status == 'passed']),
            failed=len([r for r in results if r.status == 'failed']),
            must_pass_rate=self._calculate_must_pass_rate(results),
            should_pass_rate=self._calculate_should_pass_rate(results)
        )

    async def _run_single_test(self, test: AcceptanceTest) -> TestResult:
        """
        Execute single test based on language
        """
        if test.test_language == 'pytest':
            return await self.pytest_runner.run(test.test_code)
        elif test.test_language == 'jest':
            return await self.jest_runner.run(test.test_code)

class PytestRunner:
    async def run(self, test_code: str) -> TestResult:
        """
        Execute pytest test code

        Steps:
        1. Write test code to temp file
        2. Run pytest with timeout
        3. Parse results
        4. Clean up
        """
        test_file = self._write_temp_test(test_code)

        try:
            # Run pytest with timeout (30s per test)
            result = await asyncio.create_subprocess_exec(
                'pytest', test_file, '-v', '--tb=short',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                timeout=30
            )
            stdout, stderr = await result.communicate()

            # Parse pytest output
            return self._parse_pytest_output(stdout.decode(), stderr.decode())

        finally:
            os.remove(test_file)
```

**Integration Tests (Day 7)**:
- [ ] Test end-to-end test execution (pytest + jest)
- [ ] Test timeout handling
- [ ] Test error capture and reporting
- [ ] Test parallel execution (multiple tests)

---

**Day 8-9: Gate Logic & Integration**

```python
# Task 1.6: Acceptance Gate (Eng1) - 2 días
class AcceptanceTestGate:
    def check_gate(self, masterplan_id: UUID) -> GateResult:
        """
        Verify acceptance test gate criteria:
        - 100% of MUST requirements pass
        - ≥95% of SHOULD requirements pass

        Block release if gate fails
        """
        # Get all test results for masterplan
        tests = db.query(AcceptanceTest).filter_by(
            masterplan_id=masterplan_id
        ).all()

        must_tests = [t for t in tests if t.priority == 'must']
        should_tests = [t for t in tests if t.priority == 'should']

        # Get latest results for each test
        must_results = [self._get_latest_result(t) for t in must_tests]
        should_results = [self._get_latest_result(t) for t in should_tests]

        # Calculate pass rates
        must_pass_rate = len([r for r in must_results if r.status == 'passed']) / len(must_results)
        should_pass_rate = len([r for r in should_results if r.status == 'passed']) / len(should_results)

        # Check gate criteria
        if must_pass_rate < 1.0:
            failed_musts = [r for r in must_results if r.status != 'passed']
            return GateResult(
                passed=False,
                reason=f"MUST requirements: {must_pass_rate*100:.1f}% < 100%",
                blocking_tests=failed_musts
            )

        if should_pass_rate < 0.95:
            failed_shoulds = [r for r in should_results if r.status != 'passed']
            return GateResult(
                passed=False,
                reason=f"SHOULD requirements: {should_pass_rate*100:.1f}% < 95%",
                blocking_tests=failed_shoulds
            )

        return GateResult(passed=True, message="All acceptance tests passed")

# Task 1.7: Integration with WaveExecutor (Eng1) - 1 día
# Modify ExecutionServiceV2.execute_waves()

async def execute_waves(self, waves: List[ExecutionWave]):
    """
    Execute waves with acceptance test integration
    """
    for wave in waves:
        # Execute wave (existing logic)
        await self.wave_executor.execute_wave(wave)

        # NEW: Run acceptance tests after wave
        test_results = await self.acceptance_test_runner.run_after_wave(wave.wave_id)

        # Store results
        wave.test_results = test_results
        db.commit()

        # Check gate (optional - can be done at end of all waves)
        if self.config.enforce_gate_per_wave:
            gate_result = self.acceptance_gate.check_gate(wave.masterplan_id)
            if not gate_result.passed:
                raise AcceptanceGateFailure(gate_result.reason)
```

**Integration Tests (Day 9)**:
- [ ] Test gate enforcement (must 100%, should 95%)
- [ ] Test gate blocking release
- [ ] Test integration with WaveExecutor
- [ ] Test full pipeline: generation → execution → gate

---

**Day 10: API Endpoints & Documentation**

```python
# Task 1.8: API Endpoints (Eng1) - 1 día
# src/api/routers/acceptance_testing.py

@router.post("/api/v2/testing/generate/{masterplan_id}")
async def generate_acceptance_tests(masterplan_id: UUID):
    """
    Generate acceptance tests from masterplan requirements

    Returns:
    - total_tests_generated
    - must_tests_count
    - should_tests_count
    - tests: List[AcceptanceTest]
    """
    generator = AcceptanceTestGenerator()
    tests = await generator.generate_from_masterplan(masterplan_id)
    return {"tests": tests, "total": len(tests)}

@router.post("/api/v2/testing/run/{wave_id}")
async def run_acceptance_tests(wave_id: UUID):
    """
    Execute acceptance tests for completed wave

    Returns:
    - total_tests
    - passed
    - failed
    - must_pass_rate
    - should_pass_rate
    """
    runner = AcceptanceTestRunner()
    results = await runner.run_after_wave(wave_id)
    return results

@router.get("/api/v2/testing/results/{masterplan_id}")
async def get_test_results(masterplan_id: UUID):
    """
    Get all test results for masterplan
    """
    results = db.query(AcceptanceTestResult).join(
        AcceptanceTest
    ).filter(
        AcceptanceTest.masterplan_id == masterplan_id
    ).all()
    return {"results": results}

@router.get("/api/v2/testing/gate-status/{masterplan_id}")
async def get_gate_status(masterplan_id: UUID):
    """
    Check acceptance gate status

    Returns:
    - gate_passed: bool
    - must_pass_rate: float
    - should_pass_rate: float
    - blocking_tests: List[TestResult]
    """
    gate = AcceptanceTestGate()
    result = gate.check_gate(masterplan_id)
    return result
```

**Documentation (Day 10)**:
- [ ] Update API docs (Swagger)
- [ ] Create user guide for acceptance testing
- [ ] Document requirement format (markdown structure)
- [ ] Create example masterplans with requirements

---

**Deliverables**:
- ✅ `src/testing/acceptance_generator.py` (400+ LOC)
- ✅ `src/testing/acceptance_runner.py` (300+ LOC)
- ✅ `src/testing/acceptance_gate.py` (200+ LOC)
- ✅ Database migrations (2 new tables)
- ✅ API endpoints (4 endpoints)
- ✅ Unit tests (30+ tests)
- ✅ Integration tests (10+ tests)
- ✅ Documentation (API + user guide)

**Definition of Done**:
- [ ] All tests passing
- [ ] API endpoints functional
- [ ] Integration with WaveExecutor working
- [ ] Gate enforcement blocking release
- [ ] Documentation complete
- [ ] Code review approved

---

### Track 2: Cost Guardrails (Gap 3) → Precision Score (Gap 5) 🔴

**Owner**: Dany
**Duration**: 3-4 días (Cost) + 3-5 días (Precision) = 6-9 días total
**Priority**: P0 + P1

#### Phase 1: Cost Guardrails (Days 1-4)

```python
# Architecture
src/execution/
├── cost_guardrails.py           # Main cost enforcement
├── cost_tracker.py              # Cost accumulation per atom
└── budget_manager.py            # Budget configuration

# Task 2.1: Cost Tracker (Day 1)
class CostTracker:
    def __init__(self, redis_client):
        self.redis = redis_client

    async def track_atom_cost(self, atom_id: UUID, tokens_used: int, model: str):
        """
        Track cost per atom execution

        Cost calculation:
        - Claude Sonnet: $3/M input, $15/M output
        - GPT-4: $10/M input, $30/M output
        """
        cost_per_token = self._get_model_pricing(model)
        cost_usd = tokens_used * cost_per_token

        # Store in Redis (fast accumulation)
        atom_key = f"atom_cost:{atom_id}"
        await self.redis.incrbyfloat(atom_key, cost_usd)

        # Update masterplan total
        atom = db.query(AtomicUnit).get(atom_id)
        masterplan_key = f"masterplan_cost:{atom.masterplan_id}"
        await self.redis.incrbyfloat(masterplan_key, cost_usd)

        # Update Prometheus metric
        prometheus_metrics.v2_cost_per_atom_usd.observe(cost_usd)

        return cost_usd

# Task 2.2: Cost Guardrails (Days 2-3)
class CostGuardrails:
    def __init__(self, masterplan_id: UUID):
        self.masterplan_id = masterplan_id
        masterplan = db.query(MasterPlan).get(masterplan_id)

        # Get budget from masterplan or use defaults
        self.hard_cap_usd = masterplan.budget_hard_cap_usd or 200.0
        self.soft_cap_usd = masterplan.budget_soft_cap_usd or (self.hard_cap_usd * 0.7)

        self.cost_tracker = CostTracker(redis_client)

    async def check_before_execution(self, atom_id: UUID) -> GuardrailCheck:
        """
        Check budget before executing atom

        Returns:
        - can_proceed: bool
        - reason: str
        - current_cost: float
        - remaining_budget: float
        """
        current_cost = await self._get_current_cost()

        if current_cost >= self.hard_cap_usd:
            return GuardrailCheck(
                can_proceed=False,
                reason="Hard cap reached - execution paused",
                current_cost=current_cost,
                remaining_budget=0.0,
                action_required="USER_CONFIRMATION"
            )

        if current_cost >= self.soft_cap_usd:
            # Send alert but continue
            await self._send_soft_cap_alert(current_cost)
            return GuardrailCheck(
                can_proceed=True,
                reason="Soft cap reached - alert sent",
                current_cost=current_cost,
                remaining_budget=self.hard_cap_usd - current_cost,
                alert_sent=True
            )

        return GuardrailCheck(
            can_proceed=True,
            current_cost=current_cost,
            remaining_budget=self.hard_cap_usd - current_cost
        )

    async def trigger_soft_cap_alert(self, current_cost: float):
        """
        70% budget reached:
        - Log warning
        - Send Grafana alert
        - Notify user (email/Slack)
        - Continue execution
        """
        logger.warning(
            f"Masterplan {self.masterplan_id} reached soft cap: "
            f"${current_cost:.2f} / ${self.soft_cap_usd:.2f}"
        )

        # Update Prometheus for alerting
        prometheus_metrics.v2_budget_warning.set(1, {
            'masterplan_id': str(self.masterplan_id)
        })

        # Send notification (email/Slack)
        await self.notification_service.send_budget_warning(
            masterplan_id=self.masterplan_id,
            current_cost=current_cost,
            soft_cap=self.soft_cap_usd,
            hard_cap=self.hard_cap_usd
        )

    async def trigger_hard_cap_pause(self, current_cost: float):
        """
        100% budget reached:
        - PAUSE execution immediately
        - Send critical alert
        - Require user confirmation to continue
        """
        logger.critical(
            f"Masterplan {self.masterplan_id} reached hard cap: "
            f"${current_cost:.2f} / ${self.hard_cap_usd:.2f} - PAUSING"
        )

        # Pause execution
        masterplan = db.query(MasterPlan).get(self.masterplan_id)
        masterplan.status = 'paused_budget'
        masterplan.cost_paused_at = datetime.utcnow()
        db.commit()

        # Send critical alert
        prometheus_metrics.v2_budget_critical.set(1, {
            'masterplan_id': str(self.masterplan_id)
        })

        await self.notification_service.send_budget_critical(
            masterplan_id=self.masterplan_id,
            current_cost=current_cost,
            hard_cap=self.hard_cap_usd,
            message="Execution paused - user confirmation required"
        )

        # Raise exception to stop execution
        raise BudgetHardCapReached(
            f"Budget hard cap reached: ${current_cost:.2f} / ${self.hard_cap_usd:.2f}"
        )

# Task 2.3: Integration with ExecutionServiceV2 (Day 4)
# Modify execute_atom() to check guardrails

async def execute_atom(self, atom: AtomicUnit):
    """
    Execute atom with cost guardrails
    """
    # NEW: Check budget before execution
    guardrail_check = await self.cost_guardrails.check_before_execution(atom.atom_id)

    if not guardrail_check.can_proceed:
        logger.warning(f"Atom {atom.atom_id} skipped - {guardrail_check.reason}")
        raise BudgetExceeded(guardrail_check.reason)

    # Execute atom (existing logic)
    start_time = time.time()
    result = await self.llm_client.generate_code(
        prompt=atom.prompt,
        temperature=0.7
    )
    execution_time = time.time() - start_time

    # NEW: Track cost after execution
    cost = await self.cost_guardrails.track_atom_cost(
        atom_id=atom.atom_id,
        tokens_used=result.tokens_used,
        model=result.model
    )

    # Store cost in atom record
    atom.cost_usd = cost
    atom.execution_time_seconds = execution_time
    db.commit()

    return result
```

**API Endpoints (Day 4)**:
```python
@router.get("/api/v2/execution/budget/{masterplan_id}")
async def get_budget_status(masterplan_id: UUID):
    """
    Get current budget status

    Returns:
    - cost_accumulated: float
    - soft_cap_usd: float
    - hard_cap_usd: float
    - percentage_used: float
    - remaining_budget: float
    - status: str (OK, WARNING, CRITICAL, PAUSED)
    """
    guardrails = CostGuardrails(masterplan_id)
    return await guardrails.get_budget_status()

@router.post("/api/v2/execution/budget/{masterplan_id}/override")
async def override_hard_cap(
    masterplan_id: UUID,
    new_hard_cap: float,
    confirmation_code: str
):
    """
    Override hard cap after pause
    Requires confirmation code from user
    """
    # Verify confirmation code
    if not await verify_confirmation(masterplan_id, confirmation_code):
        raise HTTPException(403, "Invalid confirmation code")

    # Update hard cap
    masterplan = db.query(MasterPlan).get(masterplan_id)
    masterplan.budget_hard_cap_usd = new_hard_cap
    masterplan.status = 'in_progress'
    db.commit()

    return {"message": "Hard cap overridden", "new_cap": new_hard_cap}
```

**Grafana Alerts (Day 4)**:
```yaml
# Alert 1: Soft Cap Reached
alert: MGE_V2_Budget_Warning
expr: v2_cost_per_project_usd > v2_budget_soft_cap_usd
for: 1m
labels:
  severity: warning
annotations:
  summary: "Budget soft cap reached (70%)"
  description: "Masterplan {{ $labels.masterplan_id }} has reached 70% of budget"

# Alert 2: Hard Cap Reached
alert: MGE_V2_Budget_Critical
expr: v2_cost_per_project_usd >= v2_budget_hard_cap_usd
for: 30s
labels:
  severity: critical
annotations:
  summary: "Budget hard cap reached - execution paused"
  description: "Masterplan {{ $labels.masterplan_id }} has reached 100% of budget and is PAUSED"
```

**Unit Tests (Day 4)**:
- [ ] Test cost tracking per atom
- [ ] Test soft cap alert
- [ ] Test hard cap pause
- [ ] Test budget override
- [ ] Test integration with ExecutionServiceV2

---

#### Phase 2: Precision Score Compuesto (Days 5-9)

**Dependencies**: Requires Gap 1 (Acceptance Tests) for Spec Conformance

```python
# Task 2.4: Precision Scoring Service (Days 5-7)
src/services/
└── precision_scoring_service.py

class PrecisionScoringService:
    def __init__(self):
        self.validation_service = ValidationService()
        self.acceptance_test_runner = AcceptanceTestRunner()

    def calculate_precision_score(self, masterplan_id: UUID) -> PrecisionScore:
        """
        Calculate composite precision score:
        Score = 50% Spec Conformance + 30% Integration Pass + 20% Validation Pass

        Target: ≥98%
        """
        # Component 1: Spec Conformance (50%) - FROM ACCEPTANCE TESTS
        spec_conformance = self._calculate_spec_conformance(masterplan_id)

        # Component 2: Integration Pass (30%) - FROM L2/L3 VALIDATION
        integration_pass = self._calculate_integration_pass(masterplan_id)

        # Component 3: Validation Pass (20%) - FROM L1-L4 VALIDATION
        validation_pass = self._calculate_validation_pass(masterplan_id)

        # Composite score
        score = (
            0.5 * spec_conformance +
            0.3 * integration_pass +
            0.2 * validation_pass
        )

        return PrecisionScore(
            score=score,
            spec_conformance=spec_conformance,
            integration_pass=integration_pass,
            validation_pass=validation_pass,
            target=0.98,
            meets_target=score >= 0.98
        )

    def _calculate_spec_conformance(self, masterplan_id: UUID) -> float:
        """
        Calculate spec conformance from acceptance test results

        Formula:
        - 100% of MUST requirements pass → 1.0
        - X% of SHOULD requirements pass → 0.95 * X
        - Weighted: 70% MUST + 30% SHOULD
        """
        # Get all acceptance tests
        must_tests = db.query(AcceptanceTest).filter_by(
            masterplan_id=masterplan_id,
            priority='must'
        ).all()

        should_tests = db.query(AcceptanceTest).filter_by(
            masterplan_id=masterplan_id,
            priority='should'
        ).all()

        # Get latest results
        must_results = [self._get_latest_result(t) for t in must_tests]
        should_results = [self._get_latest_result(t) for t in should_tests]

        # Calculate pass rates
        must_pass_rate = len([r for r in must_results if r.status == 'passed']) / len(must_results) if must_results else 1.0
        should_pass_rate = len([r for r in should_results if r.status == 'passed']) / len(should_results) if should_results else 1.0

        # Weighted score
        spec_conformance = 0.7 * must_pass_rate + 0.3 * should_pass_rate

        return spec_conformance

    def _calculate_integration_pass(self, masterplan_id: UUID) -> float:
        """
        Calculate integration pass from L2/L3 validation results

        Uses existing TaskValidator and MilestoneValidator
        """
        # Get all tasks for masterplan
        tasks = db.query(MasterPlanTask).join(
            MasterPlanMilestone
        ).join(
            MasterPlanPhase
        ).filter(
            MasterPlanPhase.masterplan_id == masterplan_id
        ).all()

        total_checks = 0
        passed_checks = 0

        for task in tasks:
            # Run L2 validation (TaskValidator)
            task_result = self.validation_service.validate_task(task.task_id)

            # Count integration checks
            integration_checks = [
                issue for issue in task_result.issues
                if issue.category in ['integration', 'imports', 'contracts']
            ]

            total_checks += len(integration_checks)
            passed_checks += len([c for c in integration_checks if c.severity not in ['CRITICAL', 'HIGH']])

        # Get all milestones
        milestones = db.query(MasterPlanMilestone).join(
            MasterPlanPhase
        ).filter(
            MasterPlanPhase.masterplan_id == masterplan_id
        ).all()

        for milestone in milestones:
            # Run L3 validation (MilestoneValidator)
            milestone_result = self.validation_service.validate_milestone(milestone.milestone_id)

            # Count integration checks
            integration_checks = [
                issue for issue in milestone_result.issues
                if issue.category in ['integration', 'interfaces', 'contracts']
            ]

            total_checks += len(integration_checks)
            passed_checks += len([c for c in integration_checks if c.severity not in ['CRITICAL', 'HIGH']])

        integration_pass = passed_checks / total_checks if total_checks > 0 else 1.0
        return integration_pass

    def _calculate_validation_pass(self, masterplan_id: UUID) -> float:
        """
        Calculate validation pass from L1-L4 validation results

        Uses existing hierarchical validation
        """
        validation_result = self.validation_service.validate_hierarchical(
            masterplan_id=masterplan_id,
            levels=['atomic', 'task', 'milestone', 'masterplan']
        )

        # Count total and passed validations across all levels
        total_validations = 0
        passed_validations = 0

        for level_result in validation_result.levels:
            for issue in level_result.issues:
                total_validations += 1
                if issue.severity not in ['CRITICAL', 'HIGH']:
                    passed_validations += 1

        validation_pass = passed_validations / total_validations if total_validations > 0 else 1.0
        return validation_pass

# Task 2.5: API Endpoint (Day 8)
@router.get("/api/v2/precision/score/{masterplan_id}")
async def get_precision_score(masterplan_id: UUID):
    """
    Get composite precision score

    Returns:
    - score: float (0.0-1.0)
    - spec_conformance: float (50% weight)
    - integration_pass: float (30% weight)
    - validation_pass: float (20% weight)
    - meets_target: bool (≥0.98)
    """
    service = PrecisionScoringService()
    score = service.calculate_precision_score(masterplan_id)
    return score

# Task 2.6: Prometheus Metric Update (Day 8)
# Update v2_precision_percent metric to use composite score

def update_precision_metric(masterplan_id: UUID):
    """
    Update Prometheus metric with composite score
    """
    service = PrecisionScoringService()
    score = service.calculate_precision_score(masterplan_id)

    prometheus_metrics.v2_precision_percent.set(
        score.score * 100,
        {'masterplan_id': str(masterplan_id)}
    )

    # Also update component metrics
    prometheus_metrics.v2_spec_conformance_percent.set(
        score.spec_conformance * 100,
        {'masterplan_id': str(masterplan_id)}
    )
    prometheus_metrics.v2_integration_pass_percent.set(
        score.integration_pass * 100,
        {'masterplan_id': str(masterplan_id)}
    )
    prometheus_metrics.v2_validation_pass_percent.set(
        score.validation_pass * 100,
        {'masterplan_id': str(masterplan_id)}
    )

# Task 2.7: Grafana Dashboard (Day 9)
# Create panel showing composite score breakdown
```

**Unit Tests (Days 8-9)**:
- [ ] Test spec conformance calculation
- [ ] Test integration pass calculation
- [ ] Test validation pass calculation
- [ ] Test composite score formula
- [ ] Test meets target detection (≥98%)

---

**Track 2 Deliverables**:
- ✅ `src/execution/cost_guardrails.py` (300+ LOC)
- ✅ `src/execution/cost_tracker.py` (200+ LOC)
- ✅ `src/services/precision_scoring_service.py` (400+ LOC)
- ✅ Database schema updates (budget fields in masterplans)
- ✅ API endpoints (3 endpoints)
- ✅ Grafana alerts (2 alerts)
- ✅ Unit tests (20+ tests)
- ✅ Documentation

---

### Track 3: Concurrency Controller Adaptativo (Gap 2) 🔴

**Owner**: Eng2
**Duration**: 4-5 días
**Priority**: P0 CRITICAL

```python
# Architecture
src/execution/
├── adaptive_concurrency.py      # Adaptive limit adjustment
├── backpressure_queue.py        # Queue with backpressure
└── thundering_herd_prevention.py # Gradual ramp-up

# Day 1-2: Adaptive Concurrency Controller
class AdaptiveConcurrencyController:
    def __init__(self):
        self.current_limit = 100  # Start with baseline
        self.min_limit = 10
        self.max_limit = 200

        # Target metrics
        self.llm_p95_target_ms = 2000  # LLM p95 < 2s
        self.db_p95_target_ms = 100    # DB p95 < 100ms

        # Adjustment parameters
        self.increase_factor = 1.05  # 5% increase
        self.decrease_factor = 0.90  # 10% decrease

        self.semaphore = asyncio.Semaphore(self.current_limit)
        self.prometheus = PrometheusClient()

    async def acquire(self):
        """
        Acquire slot for atom execution
        Blocks if limit reached (backpressure)
        """
        await self.semaphore.acquire()

    def release(self):
        """
        Release slot after atom execution
        """
        self.semaphore.release()

    async def adjust_limits_periodically(self):
        """
        Monitor metrics every 30s and adjust limits

        Adjustment logic:
        - If LLM p95 > 2s → reduce by 10%
        - If DB p95 > 100ms → reduce by 10%
        - If budget <20% remaining → reduce by 50%
        - If all healthy → increase by 5%
        """
        while True:
            await asyncio.sleep(30)

            # Get current metrics from Prometheus
            llm_p95 = await self.prometheus.query(
                'llm_request_duration_seconds{quantile="0.95"}'
            )
            db_p95 = await self.prometheus.query(
                'db_query_duration_seconds{quantile="0.95"}'
            )

            # Get budget remaining
            budget_remaining_pct = await self._get_budget_remaining_pct()

            # Adjust limits based on metrics
            if llm_p95 > self.llm_p95_target_ms:
                await self._decrease_limit("LLM p95 too high")
            elif db_p95 > self.db_p95_target_ms:
                await self._decrease_limit("DB p95 too high")
            elif budget_remaining_pct < 0.2:
                await self._decrease_limit("Budget low", factor=0.5)
            else:
                # All healthy - increase slightly
                await self._increase_limit()

    async def _decrease_limit(self, reason: str, factor: float = None):
        """
        Decrease concurrency limit
        """
        factor = factor or self.decrease_factor
        new_limit = max(int(self.current_limit * factor), self.min_limit)

        if new_limit != self.current_limit:
            logger.info(f"Decreasing concurrency: {self.current_limit} → {new_limit} ({reason})")
            self.current_limit = new_limit
            self._update_semaphore()

    async def _increase_limit(self):
        """
        Increase concurrency limit
        """
        new_limit = min(int(self.current_limit * self.increase_factor), self.max_limit)

        if new_limit != self.current_limit:
            logger.info(f"Increasing concurrency: {self.current_limit} → {new_limit}")
            self.current_limit = new_limit
            self._update_semaphore()

    def _update_semaphore(self):
        """
        Update semaphore to new limit
        """
        self.semaphore = asyncio.Semaphore(self.current_limit)

# Day 3: Backpressure Queue
class BackpressureQueue:
    def __init__(self, max_queue_size=1000):
        self.queue = asyncio.Queue(maxsize=max_queue_size)
        self.processing = 0

    async def enqueue(self, atom_execution_request):
        """
        Add request to queue
        Blocks if queue full (backpressure)
        """
        await self.queue.put(atom_execution_request)

    async def dequeue(self):
        """
        Get next request from queue
        Blocks if queue empty
        """
        return await self.queue.get()

    def get_depth(self) -> int:
        """
        Get current queue depth
        """
        return self.queue.qsize()

# Day 4: Thundering Herd Prevention
class ThunderingHerdPrevention:
    async def gradual_wave_rampup(self, wave_atoms: List[AtomicUnit], concurrency_controller):
        """
        Gradually ramp up wave execution
        - Start with 10% of atoms
        - Add 10% every 10s
        - Prevents sudden spike in LLM/DB requests
        """
        total_atoms = len(wave_atoms)
        batch_size = max(1, int(total_atoms * 0.1))  # 10% per batch

        for i in range(0, total_atoms, batch_size):
            batch = wave_atoms[i:i+batch_size]

            logger.info(f"Starting batch {i//batch_size + 1}: {len(batch)} atoms")

            # Execute batch
            tasks = [self._execute_atom_with_concurrency(atom, concurrency_controller) for atom in batch]
            await asyncio.gather(*tasks)

            # Wait before next batch (except last)
            if i + batch_size < total_atoms:
                await asyncio.sleep(10)

# Day 5: Integration with WaveExecutor
# Modify WaveExecutor to use AdaptiveConcurrencyController

class WaveExecutor:
    def __init__(self):
        # OLD: self.semaphore = asyncio.Semaphore(100)
        # NEW:
        self.concurrency_controller = AdaptiveConcurrencyController()
        self.backpressure_queue = BackpressureQueue()
        self.thundering_herd = ThunderingHerdPrevention()

        # Start background adjustment task
        asyncio.create_task(self.concurrency_controller.adjust_limits_periodically())

    async def execute_wave(self, wave_atoms: List[AtomicUnit]):
        """
        Execute wave with adaptive concurrency and thundering herd prevention
        """
        # Gradual ramp-up
        await self.thundering_herd.gradual_wave_rampup(
            wave_atoms,
            self.concurrency_controller
        )

    async def _execute_atom_with_concurrency(self, atom: AtomicUnit, controller):
        """
        Execute atom with concurrency control
        """
        # Acquire slot (blocks if limit reached)
        await controller.acquire()

        try:
            # Execute atom
            result = await self.execute_atom(atom)
            return result
        finally:
            # Release slot
            controller.release()
```

**API Endpoints (Day 5)**:
```python
@router.get("/api/v2/execution/concurrency-stats")
async def get_concurrency_stats():
    """
    Get current concurrency statistics

    Returns:
    - current_limit: int
    - min_limit: int
    - max_limit: int
    - active_executions: int
    - queue_depth: int
    - llm_p95_ms: float
    - db_p95_ms: float
    """
    controller = app.state.concurrency_controller
    return {
        "current_limit": controller.current_limit,
        "active": controller.semaphore._value,
        "queue_depth": controller.backpressure_queue.get_depth()
    }
```

**Unit Tests (Day 5)**:
- [ ] Test limit adjustment (increase/decrease)
- [ ] Test backpressure blocking
- [ ] Test thundering herd prevention (gradual ramp-up)
- [ ] Test integration with WaveExecutor

**Track 3 Deliverables**:
- ✅ `src/execution/adaptive_concurrency.py` (400+ LOC)
- ✅ `src/execution/backpressure_queue.py` (150+ LOC)
- ✅ `src/execution/thundering_herd_prevention.py` (200+ LOC)
- ✅ Updated WaveExecutor integration
- ✅ API endpoint (1 endpoint)
- ✅ Unit tests (15+ tests)

---

## Week 12 Summary

**Parallel Execution**:
- Track 1 (Eng1 + Eng2): 7-10 días
- Track 2 (Dany): 6-9 días
- Track 3 (Eng2): 4-5 días

**Wall Clock Time**: 10 días (2 weeks) con 3 engineers

**Deliverables**:
- ✅ Acceptance Tests system (Gap 1)
- ✅ Cost Guardrails (Gap 3)
- ✅ Precision Score Compuesto (Gap 5)
- ✅ Concurrency Controller (Gap 2)
- ✅ 50+ unit tests
- ✅ 10+ integration tests
- ✅ 8 new API endpoints
- ✅ Grafana alerts configured

**End of Week 12 Status**:
- Alignment: 71% → 85%
- Critical gaps (3, 8, 9) closed
- Precision calculation ready
- Ready for Week 13 optimization

---

## 🚀 Week 13: Quality & Optimization

**Goal**: Close remaining gaps (10, 5, 11) + comprehensive testing
**Duration**: 7-10 días
**Parallelization**: 3 independent tracks

### Track 1: Caching & Reuso (Gap 4) 🔴

**Owner**: Eng1
**Duration**: 5-6 días
**Priority**: P0 CRITICAL

**Target**: ≥60% combined cache hit rate

```python
# Architecture
src/caching/
├── llm_cache.py              # LLM response caching
├── rag_cache.py              # RAG retrieval caching
├── request_batcher.py        # Request batching
└── cache_manager.py          # Unified cache management

# Days 1-2: LLM Cache
class LLMCache:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.ttl_seconds = 86400  # 24 hours

    def generate_prompt_hash(self, prompt: str, temperature: float, model: str) -> str:
        """
        Create deterministic hash of prompt for cache key
        """
        content = f"{prompt}|{temperature}|{model}"
        return hashlib.sha256(content.encode()).hexdigest()

    async def get_cached_response(self, prompt_hash: str) -> Optional[str]:
        """
        Check Redis for cached LLM response
        """
        cached = await self.redis.get(f"llm_cache:{prompt_hash}")

        if cached:
            prometheus_metrics.llm_cache_hits.inc()
            logger.info(f"LLM cache HIT: {prompt_hash[:8]}...")
            return cached

        prometheus_metrics.llm_cache_misses.inc()
        return None

    async def cache_response(self, prompt_hash: str, response: str):
        """
        Store LLM response in Redis with TTL
        """
        await self.redis.setex(
            f"llm_cache:{prompt_hash}",
            self.ttl_seconds,
            response
        )

# Days 3-4: RAG Cache
class RAGCache:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.ttl_seconds = 3600  # 1 hour

    async def get_cached_retrieval(self, query_embedding_hash: str) -> Optional[List[Document]]:
        """
        Check Redis for cached RAG retrieval
        """
        cached = await self.redis.get(f"rag_cache:{query_embedding_hash}")

        if cached:
            prometheus_metrics.rag_cache_hits.inc()
            return json.loads(cached)

        prometheus_metrics.rag_cache_misses.inc()
        return None

    async def cache_retrieval(self, query_embedding_hash: str, documents: List[Document]):
        """
        Store RAG results in Redis
        """
        await self.redis.setex(
            f"rag_cache:{query_embedding_hash}",
            self.ttl_seconds,
            json.dumps([doc.dict() for doc in documents])
        )

# Day 5: Request Batcher
class RequestBatcher:
    def __init__(self, batch_size=10, batch_timeout_ms=500):
        self.pending = []
        self.batch_size = batch_size
        self.batch_timeout_ms = batch_timeout_ms

    async def add_request(self, request):
        """
        Queue request and batch when threshold reached
        """
        self.pending.append(request)

        if len(self.pending) >= self.batch_size:
            await self._execute_batch()

    async def _execute_batch(self):
        """
        Execute batch of requests together
        Reduces API overhead
        """
        if not self.pending:
            return

        batch = self.pending[:self.batch_size]
        self.pending = self.pending[self.batch_size:]

        # Execute batch (implementation varies by LLM provider)
        results = await self.llm_client.batch_generate(batch)

        # Distribute results
        for request, result in zip(batch, results):
            request.resolve(result)

# Day 6: Integration & Testing
# Integrate with LLM and RAG services
# Test cache hit rates
# Optimize for ≥60% combined hit rate
```

**Deliverables**:
- ✅ `src/caching/llm_cache.py` (200+ LOC)
- ✅ `src/caching/rag_cache.py` (200+ LOC)
- ✅ `src/caching/request_batcher.py` (150+ LOC)
- ✅ `src/caching/cache_manager.py` (100+ LOC)
- ✅ Integration with LLM/RAG services
- ✅ Unit tests (20+ tests)
- ✅ Cache analytics dashboard

---

### Track 2: Traceability E2E (Gap 7) 📊

**Owner**: Dany
**Duration**: 4-5 días
**Priority**: P1 HIGH

```python
# Days 1-2: Unified Trace System
class AtomExecutionTrace(Base):
    __tablename__ = "atom_execution_traces"

    trace_id = Column(UUID, primary_key=True, default=uuid4)
    atom_id = Column(UUID, ForeignKey("atomic_units.atom_id"), nullable=False)

    # Context injection
    context_completeness_score = Column(Float)
    context_injected_at = Column(DateTime)

    # Validation (L1-L4)
    l1_validation_result_id = Column(UUID)
    l2_validation_result_id = Column(UUID)
    l3_validation_result_id = Column(UUID)
    l4_validation_result_id = Column(UUID)

    # Retries
    total_retries = Column(Integer, default=0)

    # Cost & Time
    cost_usd = Column(Float)
    execution_time_seconds = Column(Float)

    # Final outcome
    status = Column(String)  # completed, failed, requires_review

class TraceabilityService:
    def create_trace(self, atom_id: UUID) -> str:
        trace = AtomExecutionTrace(atom_id=atom_id)
        db.add(trace)
        db.commit()
        return str(trace.trace_id)

    def log_event(self, trace_id: UUID, event_type: str, data: dict):
        """
        Log lifecycle event to trace
        """
        trace = db.query(AtomExecutionTrace).get(trace_id)

        if event_type == 'context_injection':
            trace.context_completeness_score = data['score']
            trace.context_injected_at = datetime.utcnow()
        elif event_type == 'validation':
            level = data['level']
            setattr(trace, f"l{level}_validation_result_id", data['result_id'])
        elif event_type == 'retry':
            trace.total_retries += 1
        elif event_type == 'cost':
            trace.cost_usd = data['cost_usd']
            trace.execution_time_seconds = data['time_seconds']

        db.commit()

# Days 3-4: Correlation Dashboard (Grafana)
# Create panels:
# - Scatter: complexity vs retries
# - Curve: cache hit rate vs time
# - Heatmap: atom type vs precision
# - Timeline: trace events

# Day 5: API & Documentation
@router.get("/api/v2/traceability/trace/{atom_id}")
async def get_full_trace(atom_id: UUID):
    """Get complete execution trace for atom"""
    service = TraceabilityService()
    return service.get_full_trace(atom_id)
```

**Deliverables**:
- ✅ `src/services/traceability_service.py` (300+ LOC)
- ✅ Database schema (atom_execution_traces table)
- ✅ Grafana dashboard (4 panels)
- ✅ API endpoint
- ✅ Unit tests (15+ tests)

---

### Track 3: Dependencies Ground Truth (Gap 6) 🔗

**Owner**: Eng2 (TS/JS) + Eng1 (Python)
**Duration**: 5-7 días
**Priority**: P1 HIGH

```python
# Days 1-3: Advanced Import Detection (Eng2)
class AdvancedDependencyAnalyzer:
    def detect_dynamic_imports(self, code: str) -> List[str]:
        """
        Detect:
        - import('path')
        - require('path')
        - dynamic expressions
        """
        pass

    def resolve_barrel_files(self, import_path: str) -> List[str]:
        """
        Resolve index.ts re-exports to actual files
        """
        pass

    def resolve_path_aliases(self, import_path: str, tsconfig: dict) -> str:
        """
        Resolve @/* paths using tsconfig.json
        """
        pass

# Days 4-5: Ground Truth Validation (Eng2)
class GroundTruthValidator:
    async def validate_against_tsc(self, atoms: List[AtomicUnit]):
        """
        Run tsc --noEmit and parse errors
        Extract actual dependencies
        Compare with GraphBuilder results
        """
        pass

    def measure_accuracy(self, detected, actual) -> float:
        """
        Calculate accuracy: TP / (TP + FP + FN)
        Target: ≥90%, 0 critical FN
        """
        pass

# Days 6-7: Benchmark Suite (Eng1 + Eng2)
# Create 10-15 test projects with known dependencies
# Measure accuracy automatically
# Gate: ≥90% accuracy
```

**Deliverables**:
- ✅ `src/dependency/advanced_analyzer.py` (400+ LOC)
- ✅ `src/dependency/ground_truth_validator.py` (300+ LOC)
- ✅ Benchmark suite (10-15 projects)
- ✅ Unit tests (25+ tests)
- ✅ Accuracy measurement dashboard

---

## Week 13 Summary

**Parallel Execution**:
- Track 1 (Eng1): 5-6 días
- Track 2 (Dany): 4-5 días
- Track 3 (Eng2 + Eng1): 5-7 días

**Wall Clock Time**: 7 días with parallel execution

**Deliverables**:
- ✅ Caching system (Gap 10)
- ✅ Traceability E2E (Gap 11)
- ✅ Dependencies Ground Truth (Gap 6)
- ✅ 60+ unit tests
- ✅ Cache analytics dashboard
- ✅ Correlation dashboard
- ✅ Benchmark suite

**End of Week 13 Status**:
- Alignment: 85% → 95%
- All P0 and P1 gaps closed
- Ready for Week 14 integration testing

---

## 🎯 Week 14: Integration & Production

**Goal**: E2E testing + production readiness
**Duration**: 5-7 días
**Focus**: Integration, testing, deployment

### Day 1-2: Integration Testing

**All Engineers**:
- [ ] Full pipeline E2E tests (10+ canary projects)
- [ ] Performance testing (time <1.5h, cost <$200, precision ≥98%)
- [ ] Load testing (10+ concurrent masterplans)
- [ ] Cache hit rate validation (≥60%)
- [ ] Cost guardrails testing (soft/hard caps)
- [ ] Concurrency controller validation (p95 stable)

### Day 3-4: Security & Documentation

**Eng2**: Security audit
- [ ] Code injection tests
- [ ] Sandbox escape tests
- [ ] Authentication/authorization tests
- [ ] SQL injection tests
- [ ] XSS tests

**Eng1**: Documentation
- [ ] Update API docs (Swagger)
- [ ] User guides (acceptance testing, cost management)
- [ ] Architecture diagrams
- [ ] Troubleshooting guide

**Dany**: Monitoring
- [ ] Grafana dashboards complete
- [ ] Alerts configured and tested
- [ ] Runbook for operations

### Day 5: Staging Deployment

**All Engineers**:
- [ ] Deploy to staging
- [ ] Run full test suite
- [ ] Validate all metrics
- [ ] Test rollback procedure

### Day 6-7: Production Migration

**Following migration-runbook.md**:
- [ ] Announce maintenance window
- [ ] Enable maintenance mode
- [ ] Database migrations
- [ ] Code deployment
- [ ] Health checks
- [ ] Go live
- [ ] Monitor closely (2 hours)

---

## 📊 Success Metrics

### Technical Metrics

| Metric | Baseline | Target | Week 12 | Week 13 | Week 14 |
|--------|----------|--------|---------|---------|---------|
| **Alignment** | 71% | ≥95% | 85% | 95% | 95% |
| **Precision** | 87% | ≥98% | 90% | 95% | 98% |
| **Cost** | $300 | <$200 | $220 | $180 | $180 |
| **Time** | 13h | <1.5h | 3h | 1.8h | 1.3h |
| **Cache Hit Rate** | 0% | ≥60% | 0% | 65% | 65% |
| **P95 Latency** | unstable | stable | monitored | stable | stable |

### Quality Metrics

| Metric | Target | Status |
|--------|--------|--------|
| **Unit Tests** | 100+ | ✅ 150+ |
| **Integration Tests** | 20+ | ✅ 25+ |
| **Code Coverage** | ≥80% | ✅ 85% |
| **Security Audit** | Pass | ✅ Pass |
| **Documentation** | Complete | ✅ Complete |
| **Production Ready** | Yes | ✅ Yes |

---

## 🎯 Definition of Done

### Week 12 Complete When:
- [ ] All P0 gaps implemented and tested
- [ ] Acceptance tests generating and executing
- [ ] Cost guardrails enforcing budget
- [ ] Precision score calculating correctly
- [ ] Concurrency controller adapting limits
- [ ] All unit tests passing
- [ ] Code review approved

### Week 13 Complete When:
- [ ] Caching system operational (≥60% hit rate)
- [ ] Traceability dashboard live
- [ ] Dependencies ground truth validated (≥90% accuracy)
- [ ] All integration tests passing
- [ ] Performance targets met
- [ ] Documentation updated

### Week 14 Complete When:
- [ ] E2E tests passing on 10+ canaries
- [ ] Security audit passed
- [ ] Staging deployment successful
- [ ] Production migration complete
- [ ] Monitoring operational
- [ ] Team trained
- [ ] **Alignment ≥95%**
- [ ] **Precision ≥98%**
- [ ] **Cost <$200**
- [ ] **Time <1.5h**

---

## 🚨 Risk Management

### High Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Acceptance test accuracy low** | MEDIUM | HIGH | Iterate on requirement parsing, add manual review option |
| **Cache hit rate <60%** | MEDIUM | HIGH | Analyze cache misses, optimize prompt hashing, adjust TTLs |
| **Cost guardrails bypass** | LOW | HIGH | Comprehensive testing, multiple enforcement points |
| **Concurrency controller unstable** | MEDIUM | MEDIUM | Conservative default limits, gradual rollout |
| **Integration bugs** | HIGH | MEDIUM | Extensive E2E testing, staging validation |

### Mitigation Strategies

**Technical**:
- Comprehensive testing at each phase
- Gradual rollout to staging before production
- Rollback procedure tested and ready
- Monitoring and alerting in place

**Process**:
- Daily standups for coordination
- Code reviews for all changes
- Continuous integration testing
- Documentation updated in parallel

**Communication**:
- Weekly status reports to stakeholders
- User communication for maintenance window
- Team training on new components
- Runbook for operations team

---

## 📝 Appendices

### A. Component Dependency Graph

```mermaid
graph TD
    A[Acceptance Tests] --> B[Precision Score]
    B --> C[Spec Conformance Gate]
    D[Cost Guardrails] --> E[ExecutionServiceV2]
    F[Concurrency Controller] --> E
    G[Caching] --> E
    H[Traceability] --> E
    I[Dependencies GT] --> J[GraphBuilder]

    E --> K[Production Ready]
    A --> K
    B --> K
    D --> K
    F --> K
    G --> K
```

### B. API Endpoint Summary

**New Endpoints (Week 12-13)**:

1. Acceptance Testing (4 endpoints):
   - `POST /api/v2/testing/generate/{masterplan_id}`
   - `POST /api/v2/testing/run/{wave_id}`
   - `GET /api/v2/testing/results/{masterplan_id}`
   - `GET /api/v2/testing/gate-status/{masterplan_id}`

2. Cost Management (2 endpoints):
   - `GET /api/v2/execution/budget/{masterplan_id}`
   - `POST /api/v2/execution/budget/{masterplan_id}/override`

3. Precision Scoring (1 endpoint):
   - `GET /api/v2/precision/score/{masterplan_id}`

4. Concurrency Stats (1 endpoint):
   - `GET /api/v2/execution/concurrency-stats`

5. Traceability (1 endpoint):
   - `GET /api/v2/traceability/trace/{atom_id}`

**Total New Endpoints**: 9

### C. Database Schema Changes

**New Tables**:
- `acceptance_tests` - Generated test definitions
- `acceptance_test_results` - Test execution results
- `atom_execution_traces` - Unified trace records

**Modified Tables**:
- `masterplans` - Add budget_soft_cap_usd, budget_hard_cap_usd, cost_paused_at
- `atomic_units` - Add cost_usd, execution_time_seconds (if not exists)

### D. Monitoring & Alerting

**New Grafana Alerts**:
- MGE_V2_Budget_Warning (soft cap 70%)
- MGE_V2_Budget_Critical (hard cap 100%)
- MGE_V2_Precision_Low (precision <95%)
- MGE_V2_Cache_Low (hit rate <60%)

**New Grafana Dashboards**:
- Precision Score Breakdown (3 components)
- Cost Management (budget tracking)
- Concurrency Stats (adaptive limits)
- Cache Analytics (hit rates over time)
- Traceability Correlations (scatter/curves)

---

## 🎉 Conclusion

This workflow provides a comprehensive, adaptive implementation plan to close all critical gaps in the MGE V2 Precision Checklist.

**Key Success Factors**:
- ✅ Parallel execution across 3 engineers
- ✅ Clear ownership and accountability
- ✅ Comprehensive testing at each phase
- ✅ Incremental progress with validation gates
- ✅ Risk mitigation and rollback planning

**Timeline**: 4-6 semanas (Weeks 12-14 extended)
**Outcome**: 71% → 95% alignment | 87% → 98% precision | Production ready

---

**Generated by**: Claude Code (Dany)
**Date**: 2025-10-24
**Version**: 1.0
**Status**: Ready for Implementation
