# Gap 8: Concurrency Controller Adaptativo

**Status**: 🔴 P0 CRITICAL - 0% implementado
**Effort**: 4-5 días
**Owner**: Eng2
**Dependencies**: Prometheus metrics (existentes)

---

## Executive Summary

**Problema**: WaveExecutor usa límite fijo (100 concurrent atoms). No hay adaptación dinámica basada en p95 LLM/DB, causando:
- Latency spikes cuando system overload
- Thundering herd al inicio de waves grandes
- No respeta budget constraints

**Solución**: Controller adaptativo que ajusta concurrency limits based on:
- LLM API p95 latency (<2s target)
- DB p95 query time (<100ms target)
- Budget availability
- Backpressure queuing
- Gradual ramp-up (thundering herd prevention)

**Impacto**: Garantiza p95 estable + previene cost overruns + smooth scaling.

---

## Requirements

### Functional Requirements

**FR1: Adaptive Limit Adjustment**
- Monitor LLM API p95 latency cada 30s
- Monitor DB p95 query time cada 30s
- Si p95 > target → decrease limit 10%
- Si p95 < target y healthy → increase limit 5%
- Min limit: 10, Max limit: 200

**FR2: Backpressure Queuing**
- Cuando concurrency limit reached → queue atoms
- FIFO queue con priority support (high priority atoms first)
- Queue size limit: 1000 atoms
- Timeout waiting in queue: 5 minutes

**FR3: Thundering Herd Prevention**
- Wave start: begin with 10% of concurrent limit
- Gradual ramp-up: +10% cada 10s hasta limit
- Monitor error rate during ramp-up
- Rollback if error rate >5%

**FR4: Budget-Aware Throttling**
- Check remaining budget before allowing execution
- If budget <10% remaining → reduce concurrency 50%
- If budget <5% → reduce to minimum (10)
- If budget exhausted → pause all execution

### Non-Functional Requirements

**NFR1: Performance**
- Limit adjustment latency: <1s
- Queue operations: O(1) enqueue/dequeue
- Memory overhead: <100MB for queue

**NFR2: Reliability**
- Controller crash → fallback to fixed limit 50
- Metrics unavailable → use cached values (5min TTL)
- Zero downtime during limit adjustments

---

## Architecture

### Component Diagram

```
┌──────────────────────────────────────────────────────┐
│          Adaptive Concurrency Controller             │
├──────────────────────────────────────────────────────┤
│                                                        │
│  ┌─────────────────────┐     ┌──────────────────┐   │
│  │ MetricsMonitor      │────▶│ LimitAdjuster    │   │
│  │ (p95 LLM/DB)        │     │ (increase/decrease│   │
│  └─────────────────────┘     └──────────────────┘   │
│           │                          │                │
│           ▼                          ▼                │
│  ┌─────────────────────┐     ┌──────────────────┐   │
│  │ BackpressureQueue   │◀────│ ExecutionGate    │   │
│  │ (FIFO + priority)   │     │ (allow/block)    │   │
│  └─────────────────────┘     └──────────────────┘   │
│           │                          │                │
│           ▼                          ▼                │
│  ┌─────────────────────┐     ┌──────────────────┐   │
│  │ThunderingHerdPrev   │────▶│ WaveExecutor     │   │
│  │ (gradual ramp-up)   │     │ (atom execution) │   │
│  └─────────────────────┘     └──────────────────┘   │
│                                                        │
└──────────────────────────────────────────────────────┘
```

---

## Implementation

### Phase 1: Metrics Monitoring (Day 1)

**src/mge/v2/concurrency/metrics_monitor.py**

```python
"""
Monitor Prometheus metrics for adaptive decision making
"""
import asyncio
from dataclasses import dataclass
from typing import Optional
import aiohttp

@dataclass
class SystemMetrics:
    """Current system health metrics"""
    llm_p95_ms: float
    db_p95_ms: float
    error_rate: float
    active_atoms: int
    timestamp: float

class MetricsMonitor:
    """
    Query Prometheus for p95 metrics every 30s
    """

    def __init__(self, prometheus_url: str = "http://localhost:9090"):
        self.prometheus_url = prometheus_url
        self.llm_p95_target_ms = 2000  # 2s target
        self.db_p95_target_ms = 100    # 100ms target
        self.cache: Optional[SystemMetrics] = None
        self.cache_ttl = 300  # 5min

    async def get_current_metrics(self) -> SystemMetrics:
        """
        Query Prometheus for current system metrics
        """
        try:
            async with aiohttp.ClientSession() as session:
                # LLM p95 latency
                llm_query = 'histogram_quantile(0.95, llm_request_duration_seconds_bucket)'
                llm_p95 = await self._query_prometheus(session, llm_query)

                # DB p95 query time
                db_query = 'histogram_quantile(0.95, db_query_duration_seconds_bucket)'
                db_p95 = await self._query_prometheus(session, db_query)

                # Error rate
                error_query = 'rate(v2_atom_execution_errors_total[5m])'
                error_rate = await self._query_prometheus(session, error_query)

                # Active atoms
                active_query = 'v2_atoms_executing_now'
                active_atoms = await self._query_prometheus(session, active_query)

                metrics = SystemMetrics(
                    llm_p95_ms=llm_p95 * 1000,  # Convert to ms
                    db_p95_ms=db_p95 * 1000,
                    error_rate=error_rate,
                    active_atoms=int(active_atoms),
                    timestamp=asyncio.get_event_loop().time()
                )

                self.cache = metrics
                return metrics

        except Exception as e:
            logger.error(f"Prometheus query failed: {e}")

            # Return cached metrics if available
            if self.cache and (asyncio.get_event_loop().time() - self.cache.timestamp) < self.cache_ttl:
                logger.warning("Using cached metrics")
                return self.cache

            # Fallback to default healthy metrics
            return SystemMetrics(
                llm_p95_ms=1500, db_p95_ms=80, error_rate=0.0,
                active_atoms=50, timestamp=asyncio.get_event_loop().time()
            )

    async def _query_prometheus(self, session: aiohttp.ClientSession, query: str) -> float:
        """Execute Prometheus query"""
        url = f"{self.prometheus_url}/api/v1/query"
        params = {'query': query}

        async with session.get(url, params=params) as resp:
            data = await resp.json()

            if data['status'] == 'success' and data['data']['result']:
                return float(data['data']['result'][0]['value'][1])

            return 0.0

    def is_system_healthy(self, metrics: SystemMetrics) -> bool:
        """Check if system is within healthy thresholds"""
        return (
            metrics.llm_p95_ms < self.llm_p95_target_ms and
            metrics.db_p95_ms < self.db_p95_target_ms and
            metrics.error_rate < 0.05  # <5% error rate
        )
```

### Phase 2: Adaptive Limit Adjuster (Day 2)

**src/mge/v2/concurrency/limit_adjuster.py**

```python
"""
Dynamically adjust concurrency limits based on system health
"""
import asyncio
from .metrics_monitor import MetricsMonitor, SystemMetrics

class LimitAdjuster:
    """
    Adjust concurrency limits adaptively

    Strategy:
    - If system unhealthy (p95 high) → decrease limit 10%
    - If system healthy + headroom → increase limit 5%
    - Clamp to [min_limit, max_limit]
    """

    def __init__(self, initial_limit: int = 100):
        self.current_limit = initial_limit
        self.min_limit = 10
        self.max_limit = 200
        self.metrics_monitor = MetricsMonitor()
        self.adjustment_interval = 30  # seconds
        self._running = False

    async def start_monitoring(self):
        """Start background monitoring loop"""
        self._running = True

        while self._running:
            try:
                await self._adjust_limit_based_on_metrics()
                await asyncio.sleep(self.adjustment_interval)
            except Exception as e:
                logger.error(f"Limit adjustment failed: {e}")
                await asyncio.sleep(self.adjustment_interval)

    async def _adjust_limit_based_on_metrics(self):
        """Query metrics and adjust limit"""
        metrics = await self.metrics_monitor.get_current_metrics()

        old_limit = self.current_limit

        # Check if system is unhealthy
        if not self.metrics_monitor.is_system_healthy(metrics):
            # Decrease limit
            reason = self._get_unhealthy_reason(metrics)
            new_limit = int(self.current_limit * 0.9)  # Decrease 10%
            self.current_limit = max(new_limit, self.min_limit)

            logger.warning(
                f"System unhealthy ({reason}), decreasing limit: "
                f"{old_limit} → {self.current_limit}"
            )

            # Emit metric
            CONCURRENCY_LIMIT.set(self.current_limit)
            CONCURRENCY_LIMIT_CHANGES.labels(direction='decrease', reason=reason).inc()

        else:
            # System healthy, consider increasing
            utilization = metrics.active_atoms / self.current_limit

            if utilization > 0.8 and self.current_limit < self.max_limit:
                # High utilization + healthy → increase limit
                new_limit = int(self.current_limit * 1.05)  # Increase 5%
                self.current_limit = min(new_limit, self.max_limit)

                logger.info(
                    f"System healthy + high utilization, increasing limit: "
                    f"{old_limit} → {self.current_limit}"
                )

                CONCURRENCY_LIMIT.set(self.current_limit)
                CONCURRENCY_LIMIT_CHANGES.labels(direction='increase', reason='healthy').inc()

    def _get_unhealthy_reason(self, metrics: SystemMetrics) -> str:
        """Determine why system is unhealthy"""
        reasons = []

        if metrics.llm_p95_ms > self.metrics_monitor.llm_p95_target_ms:
            reasons.append(f"llm_p95={metrics.llm_p95_ms:.0f}ms")

        if metrics.db_p95_ms > self.metrics_monitor.db_p95_target_ms:
            reasons.append(f"db_p95={metrics.db_p95_ms:.0f}ms")

        if metrics.error_rate > 0.05:
            reasons.append(f"error_rate={metrics.error_rate:.1%}")

        return ", ".join(reasons) if reasons else "unknown"

    def get_current_limit(self) -> int:
        """Get current concurrency limit"""
        return self.current_limit

    async def stop_monitoring(self):
        """Stop background monitoring"""
        self._running = False
```

### Phase 3: Backpressure Queue (Day 3)

**src/mge/v2/concurrency/backpressure_queue.py**

```python
"""
Priority queue with backpressure for atom execution
"""
import asyncio
from typing import Optional
from dataclasses import dataclass, field
from uuid import UUID
from heapq import heappush, heappop

@dataclass(order=True)
class QueuedAtom:
    """Atom waiting for execution"""
    priority: int = field(compare=True)  # Lower = higher priority
    atom_id: UUID = field(compare=False)
    enqueued_at: float = field(compare=False)

class BackpressureQueue:
    """
    Priority queue for atoms when concurrency limit reached

    Features:
    - Priority-based: high priority atoms execute first
    - Timeout: atoms waiting >5min are dropped
    - Size limit: max 1000 queued atoms
    """

    def __init__(self, max_size: int = 1000, timeout_seconds: int = 300):
        self._queue = []
        self._semaphore_map = {}  # atom_id → semaphore
        self.max_size = max_size
        self.timeout_seconds = timeout_seconds
        self._lock = asyncio.Lock()

    async def enqueue(self, atom_id: UUID, priority: int = 5) -> bool:
        """
        Enqueue atom for execution

        Args:
            atom_id: Atom UUID
            priority: 0 (highest) to 10 (lowest)

        Returns:
            True if enqueued, False if queue full
        """
        async with self._lock:
            if len(self._queue) >= self.max_size:
                logger.error(f"Queue full ({self.max_size}), dropping atom {atom_id}")
                BACKPRESSURE_QUEUE_DROPS.inc()
                return False

            queued_atom = QueuedAtom(
                priority=priority,
                atom_id=atom_id,
                enqueued_at=asyncio.get_event_loop().time()
            )

            heappush(self._queue, queued_atom)
            self._semaphore_map[atom_id] = asyncio.Semaphore(0)

            BACKPRESSURE_QUEUE_SIZE.set(len(self._queue))

            logger.info(f"Atom {atom_id} enqueued (priority={priority}, queue_size={len(self._queue)})")
            return True

    async def dequeue(self) -> Optional[UUID]:
        """
        Dequeue highest priority atom

        Returns:
            Atom UUID or None if queue empty
        """
        async with self._lock:
            while self._queue:
                queued_atom = heappop(self._queue)

                # Check timeout
                wait_time = asyncio.get_event_loop().time() - queued_atom.enqueued_at
                if wait_time > self.timeout_seconds:
                    logger.warning(
                        f"Atom {queued_atom.atom_id} timed out in queue "
                        f"(waited {wait_time:.0f}s)"
                    )
                    BACKPRESSURE_QUEUE_TIMEOUTS.inc()
                    del self._semaphore_map[queued_atom.atom_id]
                    continue

                BACKPRESSURE_QUEUE_SIZE.set(len(self._queue))
                BACKPRESSURE_QUEUE_WAIT_TIME.observe(wait_time)

                return queued_atom.atom_id

            return None

    async def wait_for_slot(self, atom_id: UUID, timeout: Optional[float] = None) -> bool:
        """
        Wait until atom can execute (released from queue)

        Returns:
            True if slot available, False if timeout
        """
        if atom_id not in self._semaphore_map:
            return True  # Not queued, can execute immediately

        semaphore = self._semaphore_map[atom_id]

        try:
            await asyncio.wait_for(
                semaphore.acquire(),
                timeout=timeout or self.timeout_seconds
            )
            return True
        except asyncio.TimeoutError:
            logger.error(f"Atom {atom_id} timed out waiting for execution slot")
            return False
        finally:
            if atom_id in self._semaphore_map:
                del self._semaphore_map[atom_id]

    async def release_slot(self, atom_id: UUID):
        """Release execution slot for atom"""
        if atom_id in self._semaphore_map:
            self._semaphore_map[atom_id].release()

    def size(self) -> int:
        """Current queue size"""
        return len(self._queue)
```

### Phase 4: Thundering Herd Prevention (Day 4)

**src/mge/v2/concurrency/thundering_herd_prevention.py**

```python
"""
Gradual ramp-up to prevent thundering herd at wave start
"""
import asyncio
from typing import List
from uuid import UUID

class ThunderingHerdPrevention:
    """
    Start wave execution gradually instead of all-at-once

    Strategy:
    1. Start with 10% of concurrency limit
    2. Add 10% more every 10 seconds
    3. Monitor error rate during ramp-up
    4. Rollback if error rate exceeds 5%
    """

    def __init__(self, limit_adjuster):
        self.limit_adjuster = limit_adjuster
        self.rampup_interval = 10  # seconds
        self.initial_percentage = 0.1  # 10%
        self.increment_percentage = 0.1  # 10%
        self.error_rate_threshold = 0.05  # 5%

    async def gradual_wave_start(
        self,
        wave_atoms: List[UUID],
        execute_atom_func
    ):
        """
        Execute wave with gradual ramp-up

        Args:
            wave_atoms: List of atom UUIDs to execute
            execute_atom_func: Async function to execute single atom
        """
        if not wave_atoms:
            return

        max_concurrent = self.limit_adjuster.get_current_limit()

        # Calculate batches
        initial_batch_size = max(1, int(max_concurrent * self.initial_percentage))
        increment_size = max(1, int(max_concurrent * self.increment_percentage))

        logger.info(
            f"Starting wave with gradual ramp-up: "
            f"initial_batch={initial_batch_size}, "
            f"increment={increment_size}, "
            f"total_atoms={len(wave_atoms)}"
        )

        executed_count = 0
        current_batch_size = initial_batch_size

        while executed_count < len(wave_atoms):
            # Get next batch
            batch_end = min(executed_count + current_batch_size, len(wave_atoms))
            batch = wave_atoms[executed_count:batch_end]

            logger.info(
                f"Executing batch: size={len(batch)}, "
                f"progress={executed_count}/{len(wave_atoms)}"
            )

            # Execute batch
            tasks = [execute_atom_func(atom_id) for atom_id in batch]
            await asyncio.gather(*tasks, return_exceptions=True)

            executed_count = batch_end

            # Check error rate
            error_rate = await self._get_recent_error_rate()
            if error_rate > self.error_rate_threshold:
                logger.error(
                    f"High error rate detected during ramp-up: {error_rate:.1%}, "
                    f"pausing for 30s..."
                )
                await asyncio.sleep(30)

                # Reduce batch size
                current_batch_size = max(1, int(current_batch_size * 0.5))
            else:
                # Healthy, increase batch size
                if executed_count < len(wave_atoms):
                    await asyncio.sleep(self.rampup_interval)
                    current_batch_size = min(
                        current_batch_size + increment_size,
                        max_concurrent
                    )

        logger.info(f"Wave ramp-up complete: {executed_count} atoms executed")

    async def _get_recent_error_rate(self) -> float:
        """Query recent error rate from Prometheus"""
        try:
            monitor = self.limit_adjuster.metrics_monitor
            metrics = await monitor.get_current_metrics()
            return metrics.error_rate
        except:
            return 0.0
```

### Phase 5: Integration with WaveExecutor (Day 5)

**Modified src/mge/v2/execution/wave_executor.py**

```python
from ..concurrency.limit_adjuster import LimitAdjuster
from ..concurrency.backpressure_queue import BackpressureQueue
from ..concurrency.thundering_herd_prevention import ThunderingHerdPrevention

class WaveExecutor:
    """Execute wave with adaptive concurrency control"""

    def __init__(self, db_session):
        self.db = db_session

        # NEW: Adaptive concurrency components
        self.limit_adjuster = LimitAdjuster(initial_limit=100)
        self.backpressure_queue = BackpressureQueue(max_size=1000)
        self.thundering_herd_prev = ThunderingHerdPrevention(self.limit_adjuster)

        # Start monitoring
        asyncio.create_task(self.limit_adjuster.start_monitoring())

    async def execute_wave(self, wave_id: UUID):
        """Execute wave with adaptive concurrency"""

        # Get wave atoms
        atoms = await self._get_wave_atoms(wave_id)
        atom_ids = [a.atom_id for a in atoms]

        logger.info(f"Starting wave {wave_id} with {len(atom_ids)} atoms")

        # NEW: Use gradual ramp-up
        await self.thundering_herd_prev.gradual_wave_start(
            atom_ids,
            self._execute_single_atom_with_backpressure
        )

        logger.info(f"Wave {wave_id} execution complete")

    async def _execute_single_atom_with_backpressure(self, atom_id: UUID):
        """Execute atom with adaptive concurrency control"""

        # Check if we're at concurrency limit
        current_limit = self.limit_adjuster.get_current_limit()
        active_atoms = await self._count_active_atoms()

        if active_atoms >= current_limit:
            # At limit → enqueue with backpressure
            logger.info(f"Concurrency limit reached ({current_limit}), enqueuing atom {atom_id}")

            enqueued = await self.backpressure_queue.enqueue(atom_id, priority=5)
            if not enqueued:
                raise Exception(f"Failed to enqueue atom {atom_id}: queue full")

            # Wait for slot
            slot_available = await self.backpressure_queue.wait_for_slot(atom_id)
            if not slot_available:
                raise Exception(f"Atom {atom_id} timed out waiting for execution slot")

        # Execute atom
        try:
            await self._execute_atom_implementation(atom_id)
        finally:
            # Release next atom from queue if any
            next_atom = await self.backpressure_queue.dequeue()
            if next_atom:
                await self.backpressure_queue.release_slot(next_atom)
```

---

## API Endpoints

### 1. GET /api/v2/concurrency/status

```python
@router.get("/concurrency/status")
async def get_concurrency_status():
    """
    Get current concurrency controller status

    Returns:
        {
            "current_limit": 120,
            "active_atoms": 95,
            "utilization": 0.79,
            "queue_size": 15,
            "system_health": {
                "llm_p95_ms": 1800,
                "db_p95_ms": 85,
                "error_rate": 0.02,
                "is_healthy": true
            }
        }
    """
    limit_adjuster = get_limit_adjuster()
    backpressure_queue = get_backpressure_queue()
    metrics_monitor = limit_adjuster.metrics_monitor

    current_limit = limit_adjuster.get_current_limit()
    queue_size = backpressure_queue.size()
    metrics = await metrics_monitor.get_current_metrics()

    return {
        "current_limit": current_limit,
        "active_atoms": metrics.active_atoms,
        "utilization": metrics.active_atoms / current_limit if current_limit > 0 else 0,
        "queue_size": queue_size,
        "system_health": {
            "llm_p95_ms": metrics.llm_p95_ms,
            "db_p95_ms": metrics.db_p95_ms,
            "error_rate": metrics.error_rate,
            "is_healthy": metrics_monitor.is_system_healthy(metrics)
        }
    }
```

---

## Prometheus Metrics

```python
# Concurrency limit
CONCURRENCY_LIMIT = Gauge(
    'v2_concurrency_limit',
    'Current adaptive concurrency limit'
)

# Limit changes
CONCURRENCY_LIMIT_CHANGES = Counter(
    'v2_concurrency_limit_changes_total',
    'Concurrency limit adjustments',
    ['direction', 'reason']
)

# Backpressure queue
BACKPRESSURE_QUEUE_SIZE = Gauge(
    'v2_backpressure_queue_size',
    'Current backpressure queue size'
)

BACKPRESSURE_QUEUE_WAIT_TIME = Histogram(
    'v2_backpressure_queue_wait_seconds',
    'Time atoms spend waiting in backpressure queue'
)

BACKPRESSURE_QUEUE_DROPS = Counter(
    'v2_backpressure_queue_drops_total',
    'Atoms dropped due to queue full'
)

BACKPRESSURE_QUEUE_TIMEOUTS = Counter(
    'v2_backpressure_queue_timeouts_total',
    'Atoms timed out waiting in queue'
)
```

---

## Testing Strategy

### Unit Tests

**tests/mge/v2/concurrency/test_limit_adjuster.py**

```python
@pytest.mark.asyncio
async def test_limit_decrease_on_high_p95():
    """Test limit decreases when LLM p95 too high"""
    adjuster = LimitAdjuster(initial_limit=100)
    adjuster.metrics_monitor = MockMetricsMonitor(llm_p95_ms=3000)  # Above 2s target

    await adjuster._adjust_limit_based_on_metrics()

    assert adjuster.current_limit == 90  # 10% decrease

@pytest.mark.asyncio
async def test_limit_increase_on_high_utilization():
    """Test limit increases when system healthy + high utilization"""
    adjuster = LimitAdjuster(initial_limit=100)
    adjuster.metrics_monitor = MockMetricsMonitor(
        llm_p95_ms=1500,  # Healthy
        active_atoms=85   # 85% utilization
    )

    await adjuster._adjust_limit_based_on_metrics()

    assert adjuster.current_limit == 105  # 5% increase
```

**tests/mge/v2/concurrency/test_backpressure_queue.py**

```python
@pytest.mark.asyncio
async def test_priority_ordering():
    """Test high priority atoms execute first"""
    queue = BackpressureQueue()

    await queue.enqueue(UUID('...'), priority=8)  # Low priority
    await queue.enqueue(UUID('...'), priority=2)  # High priority

    first_atom = await queue.dequeue()
    assert first_atom.priority == 2  # High priority dequeued first
```

### Integration Tests

**tests/mge/v2/concurrency/test_adaptive_execution.py**

```python
@pytest.mark.asyncio
async def test_wave_execution_with_backpressure():
    """Test wave execution respects concurrency limits"""
    executor = WaveExecutor(db_session)
    executor.limit_adjuster.current_limit = 10  # Small limit

    wave_id = create_test_wave(atom_count=50)

    await executor.execute_wave(wave_id)

    # Verify all atoms executed
    assert await count_completed_atoms(wave_id) == 50

    # Verify concurrency never exceeded limit
    max_concurrent = await get_max_concurrent_atoms(wave_id)
    assert max_concurrent <= 10
```

---

## Deliverables

✅ **Code**:
- MetricsMonitor (Prometheus queries)
- LimitAdjuster (adaptive algorithm)
- BackpressureQueue (priority queue)
- ThunderingHerdPrevention (gradual ramp-up)
- WaveExecutor integration

✅ **API**: 1 endpoint (concurrency status)

✅ **Tests**: 15+ unit tests, 5+ integration tests

✅ **Monitoring**: 6 Prometheus metrics

---

## Definition of Done

- [ ] Adaptive limit adjustment working (30s intervals)
- [ ] Backpressure queue with priority support
- [ ] Thundering herd prevention (gradual ramp-up)
- [ ] WaveExecutor integration complete
- [ ] 20+ tests passing
- [ ] Prometheus metrics emitting
- [ ] Tested on 3 large waves (>100 atoms each)
- [ ] p95 stays <2s LLM, <100ms DB under load
- [ ] No thundering herd observed

---

## Success Metrics

**Target**:
- ✅ Item 8 alignment: 0% → 100%
- ✅ p95 LLM <2s stable under load
- ✅ p95 DB <100ms stable under load
- ✅ No thundering herd at wave start
- ✅ Backpressure queue prevents overload
- ✅ Zero OOM crashes under load

