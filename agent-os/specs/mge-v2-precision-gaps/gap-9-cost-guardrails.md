# Gap 9: Cost Guardrails

**Status**: 🔴 P0 CRITICAL - 0% implementado
**Effort**: 3-4 días
**Owner**: Dany
**Dependencies**: Prometheus metrics `v2_cost_per_project_usd` (existente)

---

## Executive Summary

**Problema**: No hay enforcement de cost limits. Métrica `v2_cost_per_project_usd` existe pero sin:
- Soft caps (70% budget) → alertas
- Hard caps (100% budget) → auto-pause + confirmación
- Tracking granular por atom
- Alertas automáticas en Grafana

**Solución**: Sistema de guardrails con:
- Budget tracking real-time por masterplan
- Soft cap (70%) → warning alerts
- Hard cap (100%) → PAUSE execution + require user confirmation
- Cost prediction based on atoms remaining
- Grafana alerting integration

**Impacto**: Garantiza <$200 per project + previene cost overruns + visibility.

---

## Requirements

### Functional Requirements

**FR1: Budget Configuration**
- Default budget: $200 per masterplan
- Configurable per project (override default)
- Soft cap: 70% ($140 default)
- Hard cap: 100% ($200 default)

**FR2: Real-Time Cost Tracking**
- Track cost per atom execution (LLM API calls)
- Aggregate cost per masterplan
- Update Prometheus metric `v2_cost_per_project_usd` after each atom
- Store historical cost data

**FR3: Soft Cap Enforcement**
- When cost ≥ soft_cap → emit warning log
- Send Grafana alert notification
- Continue execution (no blocking)
- Log warning in masterplan audit trail

**FR4: Hard Cap Enforcement**
- When cost ≥ hard_cap → PAUSE execution immediately
- Set masterplan status = 'paused_budget'
- Require explicit user confirmation to continue
- Log hard cap event
- Notify via Grafana critical alert

**FR5: Cost Prediction**
- Estimate remaining cost based on:
  - Atoms remaining in waves
  - Average cost per atom (historical)
- Warn if projected cost > budget

### Non-Functional Requirements

**NFR1: Performance**
- Cost check latency: <50ms per atom
- Prometheus metric update: <100ms
- Real-time tracking (no batching delays)

**NFR2: Reliability**
- Cost tracking survives system restart
- No cost leakage (every LLM call tracked)
- Audit trail for cost events

---

## Architecture

### Component Diagram

```
┌──────────────────────────────────────────────────┐
│              Cost Guardrails System              │
├──────────────────────────────────────────────────┤
│                                                    │
│  ┌───────────────┐       ┌──────────────────┐   │
│  │ CostTracker   │──────▶│ cost_events (DB) │   │
│  │ (per atom)    │       └──────────────────┘   │
│  └───────────────┘                 │             │
│         │                           ▼             │
│         ▼                  ┌──────────────────┐  │
│  ┌───────────────┐        │ Prometheus       │  │
│  │CostGuardrails │◀───────│ (metrics)        │  │
│  │ (soft/hard cap│        └──────────────────┘  │
│  └───────────────┘                 │             │
│         │                           ▼             │
│         ▼                  ┌──────────────────┐  │
│  ┌───────────────┐        │ Grafana Alerts   │  │
│  │ExecutionGate  │◀───────│ (notifications)  │  │
│  │ (allow/pause) │        └──────────────────┘  │
│  └───────────────┘                               │
│                                                    │
└──────────────────────────────────────────────────┘
```

---

## Database Schema

### cost_events Table

```sql
CREATE TABLE cost_events (
    event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    masterplan_id UUID NOT NULL REFERENCES masterplans(masterplan_id) ON DELETE CASCADE,
    atom_id UUID REFERENCES atomic_units(atom_id),
    event_type VARCHAR(20) NOT NULL CHECK (event_type IN ('atom_execution', 'soft_cap_warning', 'hard_cap_reached', 'budget_override')),
    cost_usd DECIMAL(10, 4) NOT NULL,
    cumulative_cost_usd DECIMAL(10, 4) NOT NULL,
    budget_limit_usd DECIMAL(10, 2),
    soft_cap_usd DECIMAL(10, 2),
    hard_cap_usd DECIMAL(10, 2),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB,

    INDEX idx_cost_events_masterplan (masterplan_id),
    INDEX idx_cost_events_timestamp (timestamp),
    INDEX idx_cost_events_type (event_type)
);

COMMENT ON TABLE cost_events IS 'Cost tracking and guardrail events';
COMMENT ON COLUMN cost_events.cumulative_cost_usd IS 'Running total cost for masterplan';
```

### masterplans Table (add columns)

```sql
ALTER TABLE masterplans
ADD COLUMN budget_limit_usd DECIMAL(10, 2) DEFAULT 200.00,
ADD COLUMN soft_cap_percentage DECIMAL(5, 2) DEFAULT 70.00,
ADD COLUMN hard_cap_percentage DECIMAL(5, 2) DEFAULT 100.00,
ADD COLUMN current_cost_usd DECIMAL(10, 4) DEFAULT 0.0,
ADD COLUMN budget_override_approved_by UUID REFERENCES users(user_id),
ADD COLUMN budget_override_approved_at TIMESTAMP WITH TIME ZONE;

COMMENT ON COLUMN masterplans.budget_limit_usd IS 'Budget limit for this masterplan (default $200)';
COMMENT ON COLUMN masterplans.current_cost_usd IS 'Real-time cumulative cost';
```

---

## Implementation

### Phase 1: Cost Tracking (Day 1)

**src/mge/v2/cost/cost_tracker.py**

```python
"""
Real-time cost tracking per atom execution
"""
from uuid import UUID
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import CostEvent, Masterplan
import tiktoken

class CostTracker:
    """
    Track LLM API costs per atom execution

    Cost calculation:
    - GPT-4: $0.03 / 1K input tokens, $0.06 / 1K output tokens
    - GPT-3.5: $0.0015 / 1K input tokens, $0.002 / 1K output tokens
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.gpt4_input_cost_per_1k = Decimal('0.03')
        self.gpt4_output_cost_per_1k = Decimal('0.06')
        self.encoding = tiktoken.encoding_for_model("gpt-4")

    async def track_atom_cost(
        self,
        masterplan_id: UUID,
        atom_id: UUID,
        prompt_tokens: int,
        completion_tokens: int,
        model: str = "gpt-4"
    ) -> Decimal:
        """
        Track cost for single atom execution

        Args:
            masterplan_id: Masterplan UUID
            atom_id: Atom UUID
            prompt_tokens: Input tokens used
            completion_tokens: Output tokens used
            model: Model name (gpt-4, gpt-3.5-turbo)

        Returns:
            Cost in USD for this execution
        """
        # Calculate cost
        input_cost = (Decimal(prompt_tokens) / 1000) * self.gpt4_input_cost_per_1k
        output_cost = (Decimal(completion_tokens) / 1000) * self.gpt4_output_cost_per_1k
        total_cost = input_cost + output_cost

        # Get current cumulative cost
        masterplan = await self.db.get(Masterplan, masterplan_id)
        cumulative_cost = masterplan.current_cost_usd + total_cost

        # Update masterplan cost
        masterplan.current_cost_usd = cumulative_cost
        await self.db.commit()

        # Record cost event
        cost_event = CostEvent(
            masterplan_id=masterplan_id,
            atom_id=atom_id,
            event_type='atom_execution',
            cost_usd=total_cost,
            cumulative_cost_usd=cumulative_cost,
            budget_limit_usd=masterplan.budget_limit_usd,
            soft_cap_usd=masterplan.budget_limit_usd * (masterplan.soft_cap_percentage / 100),
            hard_cap_usd=masterplan.budget_limit_usd * (masterplan.hard_cap_percentage / 100),
            metadata={
                'prompt_tokens': prompt_tokens,
                'completion_tokens': completion_tokens,
                'model': model
            }
        )

        self.db.add(cost_event)
        await self.db.commit()

        # Update Prometheus metric
        COST_PER_PROJECT_USD.labels(masterplan_id=str(masterplan_id)).set(float(cumulative_cost))

        logger.info(
            f"Atom {atom_id} cost: ${total_cost:.4f}, "
            f"cumulative: ${cumulative_cost:.4f} / ${masterplan.budget_limit_usd:.2f}"
        )

        return total_cost

    async def get_current_cost(self, masterplan_id: UUID) -> Decimal:
        """Get current cumulative cost for masterplan"""
        masterplan = await self.db.get(Masterplan, masterplan_id)
        return masterplan.current_cost_usd if masterplan else Decimal('0.0')

    async def predict_remaining_cost(self, masterplan_id: UUID) -> Decimal:
        """
        Predict cost for remaining atoms

        Uses historical average cost per atom
        """
        # Get completed atoms count and cost
        result = await self.db.execute(
            select(func.count(CostEvent.event_id), func.sum(CostEvent.cost_usd))
            .where(
                CostEvent.masterplan_id == masterplan_id,
                CostEvent.event_type == 'atom_execution'
            )
        )
        completed_atoms, total_cost = result.one()

        if completed_atoms == 0:
            return Decimal('0.0')

        avg_cost_per_atom = total_cost / completed_atoms

        # Get remaining atoms count
        remaining_atoms = await self._count_remaining_atoms(masterplan_id)

        predicted_cost = avg_cost_per_atom * remaining_atoms

        logger.info(
            f"Cost prediction for {masterplan_id}: "
            f"avg=${avg_cost_per_atom:.4f}/atom × {remaining_atoms} atoms = ${predicted_cost:.2f}"
        )

        return predicted_cost
```

### Phase 2: Guardrails Logic (Day 2)

**src/mge/v2/cost/cost_guardrails.py**

```python
"""
Cost guardrails enforcement: soft cap warnings, hard cap pauses
"""
from uuid import UUID
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import Masterplan, CostEvent

class BudgetHardCapReached(Exception):
    """Raised when hard cap reached, requires user confirmation"""
    pass

class CostGuardrails:
    """
    Enforce budget guardrails

    - Soft cap (70%) → warning, continue execution
    - Hard cap (100%) → PAUSE execution, require user confirmation
    """

    def __init__(self, db_session: AsyncSession, masterplan_id: UUID):
        self.db = db_session
        self.masterplan_id = masterplan_id
        self._masterplan_cache = None

    async def check_before_execution(self, atom_id: UUID) -> dict:
        """
        Check guardrails before atom execution

        Returns:
            {
                'can_proceed': bool,
                'status': 'ok' | 'soft_cap_warning' | 'hard_cap_reached',
                'current_cost': Decimal,
                'budget_limit': Decimal,
                'action_required': None | 'USER_CONFIRMATION'
            }

        Raises:
            BudgetHardCapReached: If hard cap exceeded
        """
        masterplan = await self._get_masterplan()

        current_cost = masterplan.current_cost_usd
        budget_limit = masterplan.budget_limit_usd
        soft_cap = budget_limit * (masterplan.soft_cap_percentage / 100)
        hard_cap = budget_limit * (masterplan.hard_cap_percentage / 100)

        # Check hard cap
        if current_cost >= hard_cap:
            logger.critical(
                f"Hard cap reached for masterplan {self.masterplan_id}: "
                f"${current_cost:.2f} >= ${hard_cap:.2f}"
            )

            await self._trigger_hard_cap_pause(current_cost, hard_cap)

            return {
                'can_proceed': False,
                'status': 'hard_cap_reached',
                'current_cost': current_cost,
                'budget_limit': budget_limit,
                'hard_cap': hard_cap,
                'action_required': 'USER_CONFIRMATION'
            }

        # Check soft cap
        if current_cost >= soft_cap:
            logger.warning(
                f"Soft cap exceeded for masterplan {self.masterplan_id}: "
                f"${current_cost:.2f} >= ${soft_cap:.2f}"
            )

            await self._trigger_soft_cap_warning(current_cost, soft_cap)

            return {
                'can_proceed': True,
                'status': 'soft_cap_warning',
                'current_cost': current_cost,
                'budget_limit': budget_limit,
                'soft_cap': soft_cap,
                'action_required': None
            }

        # All good
        return {
            'can_proceed': True,
            'status': 'ok',
            'current_cost': current_cost,
            'budget_limit': budget_limit,
            'action_required': None
        }

    async def _trigger_soft_cap_warning(self, current_cost: Decimal, soft_cap: Decimal):
        """
        Trigger soft cap warning (log + Grafana alert)
        """
        # Record event
        event = CostEvent(
            masterplan_id=self.masterplan_id,
            event_type='soft_cap_warning',
            cost_usd=Decimal('0.0'),
            cumulative_cost_usd=current_cost,
            soft_cap_usd=soft_cap,
            metadata={
                'percentage': float((current_cost / soft_cap) * 100),
                'alert_severity': 'warning'
            }
        )
        self.db.add(event)
        await self.db.commit()

        # Emit Prometheus metric
        COST_GUARDRAIL_TRIGGERED.labels(
            masterplan_id=str(self.masterplan_id),
            cap_type='soft'
        ).inc()

        logger.warning(f"Soft cap event recorded for {self.masterplan_id}")

    async def _trigger_hard_cap_pause(self, current_cost: Decimal, hard_cap: Decimal):
        """
        Trigger hard cap: PAUSE execution + require user confirmation
        """
        masterplan = await self._get_masterplan()

        # PAUSE masterplan
        masterplan.status = 'paused_budget'
        await self.db.commit()

        # Record event
        event = CostEvent(
            masterplan_id=self.masterplan_id,
            event_type='hard_cap_reached',
            cost_usd=Decimal('0.0'),
            cumulative_cost_usd=current_cost,
            hard_cap_usd=hard_cap,
            metadata={
                'percentage': float((current_cost / hard_cap) * 100),
                'alert_severity': 'critical',
                'masterplan_paused': True
            }
        )
        self.db.add(event)
        await self.db.commit()

        # Emit Prometheus metric
        COST_GUARDRAIL_TRIGGERED.labels(
            masterplan_id=str(self.masterplan_id),
            cap_type='hard'
        ).inc()

        MASTERPLAN_PAUSED_BUDGET.labels(
            masterplan_id=str(self.masterplan_id)
        ).set(1)

        logger.critical(
            f"Hard cap reached: masterplan {self.masterplan_id} PAUSED at ${current_cost:.2f}"
        )

        # Raise exception to stop execution
        raise BudgetHardCapReached(
            f"Budget hard cap reached: ${current_cost:.2f} >= ${hard_cap:.2f}. "
            f"Masterplan paused, user confirmation required to continue."
        )

    async def approve_budget_override(self, approved_by_user_id: UUID, new_budget: Decimal):
        """
        User approves budget override to continue execution

        Args:
            approved_by_user_id: User who approved override
            new_budget: New budget limit (must be > current cost)
        """
        masterplan = await self._get_masterplan()

        if new_budget <= masterplan.current_cost_usd:
            raise ValueError(
                f"New budget ${new_budget:.2f} must be > current cost ${masterplan.current_cost_usd:.2f}"
            )

        # Update masterplan
        old_budget = masterplan.budget_limit_usd
        masterplan.budget_limit_usd = new_budget
        masterplan.budget_override_approved_by = approved_by_user_id
        masterplan.budget_override_approved_at = datetime.utcnow()
        masterplan.status = 'executing'  # Resume execution
        await self.db.commit()

        # Record event
        event = CostEvent(
            masterplan_id=self.masterplan_id,
            event_type='budget_override',
            cost_usd=Decimal('0.0'),
            cumulative_cost_usd=masterplan.current_cost_usd,
            budget_limit_usd=new_budget,
            metadata={
                'old_budget': float(old_budget),
                'new_budget': float(new_budget),
                'approved_by': str(approved_by_user_id)
            }
        )
        self.db.add(event)
        await self.db.commit()

        # Clear pause metric
        MASTERPLAN_PAUSED_BUDGET.labels(
            masterplan_id=str(self.masterplan_id)
        ).set(0)

        logger.info(
            f"Budget override approved for {self.masterplan_id}: "
            f"${old_budget:.2f} → ${new_budget:.2f} by user {approved_by_user_id}"
        )

    async def _get_masterplan(self) -> Masterplan:
        """Get masterplan with caching"""
        if not self._masterplan_cache:
            self._masterplan_cache = await self.db.get(Masterplan, self.masterplan_id)
        return self._masterplan_cache
```

### Phase 3: WaveExecutor Integration (Day 3)

**Modified src/mge/v2/execution/wave_executor.py**

```python
from ..cost.cost_tracker import CostTracker
from ..cost.cost_guardrails import CostGuardrails, BudgetHardCapReached

class WaveExecutor:
    """Execute wave with cost guardrails"""

    async def execute_atom(self, atom_id: UUID, masterplan_id: UUID):
        """Execute atom with cost tracking + guardrails"""

        # NEW: Check cost guardrails BEFORE execution
        guardrails = CostGuardrails(self.db, masterplan_id)

        try:
            check_result = await guardrails.check_before_execution(atom_id)

            if not check_result['can_proceed']:
                logger.error(
                    f"Cannot execute atom {atom_id}: {check_result['status']}"
                )
                raise BudgetHardCapReached(f"Budget limit reached")

            if check_result['status'] == 'soft_cap_warning':
                logger.warning(
                    f"Soft cap warning for atom {atom_id}: "
                    f"${check_result['current_cost']:.2f} / ${check_result['budget_limit']:.2f}"
                )

        except BudgetHardCapReached as e:
            logger.critical(f"Hard cap reached, stopping execution: {e}")
            raise

        # Execute atom with LLM
        prompt = await self._build_prompt(atom_id)
        response = await self.llm_client.generate(
            prompt=prompt,
            model="gpt-4",
            temperature=0.7
        )

        # NEW: Track cost after execution
        cost_tracker = CostTracker(self.db)
        cost = await cost_tracker.track_atom_cost(
            masterplan_id=masterplan_id,
            atom_id=atom_id,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            model="gpt-4"
        )

        logger.info(f"Atom {atom_id} executed, cost: ${cost:.4f}")

        return response
```

### Phase 4: Grafana Alerts (Day 4)

**Grafana Alert Rules**

```yaml
# config/grafana/alerts/cost_guardrails.yml

groups:
  - name: cost_guardrails
    interval: 30s
    rules:
      # Soft cap warning
      - alert: CostSoftCapExceeded
        expr: |
          v2_cost_per_project_usd >= (v2_budget_limit_usd * 0.70)
          and
          v2_cost_per_project_usd < (v2_budget_limit_usd * 1.00)
        for: 1m
        labels:
          severity: warning
          component: cost_guardrails
        annotations:
          summary: "Cost soft cap exceeded for masterplan {{ $labels.masterplan_id }}"
          description: |
            Masterplan {{ $labels.masterplan_id }} has exceeded 70% budget.
            Current: ${{ $value | printf "%.2f" }}
            Budget: ${{ with query "v2_budget_limit_usd{masterplan_id='{{ $labels.masterplan_id }}'}" }}{{ . | first | value | printf "%.2f" }}{{ end }}

      # Hard cap critical
      - alert: CostHardCapReached
        expr: |
          v2_cost_per_project_usd >= v2_budget_limit_usd
        for: 10s
        labels:
          severity: critical
          component: cost_guardrails
        annotations:
          summary: "Cost hard cap REACHED for masterplan {{ $labels.masterplan_id }}"
          description: |
            Masterplan {{ $labels.masterplan_id }} has REACHED budget limit!
            Current: ${{ $value | printf "%.2f" }}
            Budget: ${{ with query "v2_budget_limit_usd{masterplan_id='{{ $labels.masterplan_id }}'}" }}{{ . | first | value | printf "%.2f" }}{{ end }}
            Execution has been PAUSED. User confirmation required.

      # Projected cost warning
      - alert: CostProjectedExceedsBudget
        expr: |
          (v2_cost_per_project_usd + v2_predicted_remaining_cost_usd) > v2_budget_limit_usd
        for: 2m
        labels:
          severity: warning
          component: cost_guardrails
        annotations:
          summary: "Projected cost exceeds budget for masterplan {{ $labels.masterplan_id }}"
          description: |
            Projected final cost will exceed budget!
            Current: ${{ with query "v2_cost_per_project_usd{masterplan_id='{{ $labels.masterplan_id }}'}" }}{{ . | first | value | printf "%.2f" }}{{ end }}
            Predicted remaining: ${{ $value | printf "%.2f" }}
            Budget: ${{ with query "v2_budget_limit_usd{masterplan_id='{{ $labels.masterplan_id }}'}" }}{{ . | first | value | printf "%.2f" }}{{ end }}
```

---

## API Endpoints

### 1. GET /api/v2/cost/{masterplan_id}

```python
@router.get("/cost/{masterplan_id}")
async def get_cost_status(
    masterplan_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get current cost status and guardrails state

    Returns:
        {
            "masterplan_id": "...",
            "current_cost_usd": 145.32,
            "budget_limit_usd": 200.00,
            "soft_cap_usd": 140.00,
            "hard_cap_usd": 200.00,
            "utilization_percentage": 72.66,
            "status": "soft_cap_exceeded",
            "predicted_remaining_cost_usd": 38.50,
            "projected_total_cost_usd": 183.82,
            "will_exceed_budget": false
        }
    """
    masterplan = await db.get(Masterplan, masterplan_id)
    if not masterplan:
        raise HTTPException(404, "Masterplan not found")

    cost_tracker = CostTracker(db)
    predicted_remaining = await cost_tracker.predict_remaining_cost(masterplan_id)

    soft_cap = masterplan.budget_limit_usd * (masterplan.soft_cap_percentage / 100)
    hard_cap = masterplan.budget_limit_usd * (masterplan.hard_cap_percentage / 100)

    projected_total = masterplan.current_cost_usd + predicted_remaining

    # Determine status
    if masterplan.current_cost_usd >= hard_cap:
        status = "hard_cap_reached"
    elif masterplan.current_cost_usd >= soft_cap:
        status = "soft_cap_exceeded"
    else:
        status = "ok"

    return {
        "masterplan_id": str(masterplan_id),
        "current_cost_usd": float(masterplan.current_cost_usd),
        "budget_limit_usd": float(masterplan.budget_limit_usd),
        "soft_cap_usd": float(soft_cap),
        "hard_cap_usd": float(hard_cap),
        "utilization_percentage": float((masterplan.current_cost_usd / masterplan.budget_limit_usd) * 100),
        "status": status,
        "predicted_remaining_cost_usd": float(predicted_remaining),
        "projected_total_cost_usd": float(projected_total),
        "will_exceed_budget": projected_total > masterplan.budget_limit_usd
    }
```

### 2. POST /api/v2/cost/{masterplan_id}/override

```python
@router.post("/cost/{masterplan_id}/override")
async def approve_budget_override(
    masterplan_id: UUID,
    new_budget: float,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Approve budget override to resume execution after hard cap

    Requires:
        - User must be superuser
        - new_budget > current_cost
    """
    if not current_user.is_superuser:
        raise HTTPException(403, "Only superusers can approve budget overrides")

    guardrails = CostGuardrails(db, masterplan_id)

    try:
        await guardrails.approve_budget_override(
            approved_by_user_id=current_user.user_id,
            new_budget=Decimal(str(new_budget))
        )

        return {
            "status": "approved",
            "new_budget_usd": new_budget,
            "approved_by": str(current_user.user_id),
            "masterplan_resumed": True
        }

    except ValueError as e:
        raise HTTPException(400, str(e))
```

### 3. GET /api/v2/cost/{masterplan_id}/events

```python
@router.get("/cost/{masterplan_id}/events")
async def get_cost_events(
    masterplan_id: UUID,
    event_type: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Get cost event history for masterplan
    """
    query = select(CostEvent).where(CostEvent.masterplan_id == masterplan_id)

    if event_type:
        query = query.where(CostEvent.event_type == event_type)

    query = query.order_by(CostEvent.timestamp.desc()).limit(limit)

    results = await db.execute(query)
    events = results.scalars().all()

    return {
        "masterplan_id": str(masterplan_id),
        "event_count": len(events),
        "events": [
            {
                "event_id": str(e.event_id),
                "event_type": e.event_type,
                "cost_usd": float(e.cost_usd),
                "cumulative_cost_usd": float(e.cumulative_cost_usd),
                "timestamp": e.timestamp.isoformat(),
                "metadata": e.metadata
            }
            for e in events
        ]
    }
```

---

## Prometheus Metrics

```python
# Budget limit gauge
BUDGET_LIMIT_USD = Gauge(
    'v2_budget_limit_usd',
    'Budget limit for masterplan',
    ['masterplan_id']
)

# Predicted remaining cost
PREDICTED_REMAINING_COST = Gauge(
    'v2_predicted_remaining_cost_usd',
    'Predicted cost for remaining atoms',
    ['masterplan_id']
)

# Guardrail triggers
COST_GUARDRAIL_TRIGGERED = Counter(
    'v2_cost_guardrail_triggered_total',
    'Cost guardrail triggers (soft/hard cap)',
    ['masterplan_id', 'cap_type']
)

# Masterplan paused due to budget
MASTERPLAN_PAUSED_BUDGET = Gauge(
    'v2_masterplan_paused_budget',
    'Masterplan paused due to budget (1=paused, 0=active)',
    ['masterplan_id']
)
```

---

## Testing Strategy

**Unit Tests**: 15+ tests for cost calculation, guardrails logic
**Integration Tests**: 5+ tests for E2E flow (execution → soft cap → hard cap → override)

---

## Deliverables

✅ **Code**: CostTracker, CostGuardrails, integration with WaveExecutor
✅ **Database**: cost_events table, masterplans columns
✅ **API**: 3 endpoints
✅ **Tests**: 20+ tests
✅ **Monitoring**: 4 Prometheus metrics + 3 Grafana alerts

---

## Definition of Done

- [ ] Real-time cost tracking per atom
- [ ] Soft cap warnings emitted (70%)
- [ ] Hard cap PAUSE execution (100%)
- [ ] Budget override API working
- [ ] Grafana alerts configured and firing
- [ ] 20+ tests passing
- [ ] Tested on 3 masterplans (1 under budget, 1 soft cap, 1 hard cap)

---

## Success Metrics

**Target**:
- ✅ Item 9 alignment: 0% → 100%
- ✅ No masterplan exceeds budget without approval
- ✅ Soft cap alerts fire within 1 min
- ✅ Hard cap PAUSE within 10s
- ✅ 100% cost tracking accuracy (no leakage)

